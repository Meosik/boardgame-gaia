"""Discord → Codex: the second model as its own bot, next to the Claude bot (lab/discord_claude.py).

User 2026-10-22 "봇을 하나 새로 더 만드는 방식으로 가자" → "claude는 내부에서 codex 호출하는건 없애되, codex봇이 claude의 말에
반박하는 체계는 유지": Codex has its own Discord identity and process; the Claude bot calls no Codex at all.
Everything here is one read-only `codex exec` in GAIA_WORKDIR: it never edits files, commits or runs experiments.

In the Claude bot's channels (DISCORD_CHANNEL_IDS) and the owner's DMs:
  - a message addressed to this bot — a mention (`@Codex 질문`) or the `!codex ` prefix — gets an answer with the
    last CODEX_CONTEXT channel messages (owner, Claude, itself) as context; `!status`, `!stop`, `!new` addressed
    the same way are this bot's commands. The Claude bot skips every message addressed here.
  - the conversation watch: when the Claude bot's reply to an owner message has been quiet for CODEX_WATCH_DELAY
    seconds, Codex reviews the owner's message, Claude's reply and the commits made meanwhile (HEAD before/after)
    and posts `🔍 코덱스(<model>) 검수 지적 …` (or one line `이상 없음`); the Claude bot reads the 🔍 messages
    since its last reply and puts them in front of the owner's next message. The Claude bot's `!q` answers
    (`일회성 답`) and its answers to `!`-commands are not reviewed.

Icons and commands follow the table in lab/README.md ("두 봇의 명령·아이콘"): 👀 received, ⏳ queued behind a
running task, `🧠 <model> · <note>` as the last line of every model answer, ⚠️ a failure, 🔍 a review.

Environment (~/.config/gaia/discord-bots.env, shared with the Claude bot): CODEX_BOT_TOKEN, DISCORD_OWNER_ID,
DISCORD_CHANNEL_IDS, GAIA_WORKDIR, CODEX_BIN (default: codex on PATH), CODEX_MODEL (default gpt-6-astra),
CODEX_WATCH (0 turns the watch off), CODEX_WATCH_MINUTES (default 5), CODEX_WATCH_DELAY (seconds of silence after
Claude's reply, default 20), CODEX_TURN_MINUTES (default 10, direct questions), CODEX_CONTEXT (default 12 messages),
CLAUDE_BOT_ID (optional: only this bot's messages count as Claude's; default: any other bot that is not a webhook).
"""
import asyncio
import hashlib
import os
from pathlib import Path
import py_compile
import re
import shutil
import sys
import tempfile

import discord_claude as shared

SELF = Path(__file__).resolve()
MENTION = re.compile(r'<@!?(\d+)>')
HEADER = '🔍 코덱스'
CONTINUED = '🔍 (계속)'
FOOTER_ONE_OFF = '일회성 답'   # the Claude bot's `!q` answers end with this; they are not reviewed
COMMANDS = ('!status', '!stop', '!new')

QUESTION_NOTE = ('(디스코드에서 사용자가 Codex에게 직접 한 질문이다. 한국어로, 휴대폰에서 읽을 수 있게 짧게 답한다. 저장소는 읽기 '
                 '전용이다: 파일을 고치지 말고 실험을 돌리지 마라. 맥락이 필요하면 gaia-rl/lab/HANDOFF.md의 5장만 읽는다.)\n\n')

# User 2026-10-22 "내가 말한건 이런 대화 중간중간에 codex가 개입하는거였는데, 오히려 실험은 냅두고": the second model watches
# the conversation itself, not only lab's commits and verdicts. Objections are posted verbatim and given to Claude at the
# start of the owner's next message, so the owner sees both sides before deciding.
WATCH_NOTE = ('(대화 검수. 아래는 사용자의 질문, Claude의 답, 이 턴에 Claude가 만든 커밋 범위다. 저장소는 읽기 전용이다: '
              '파일을 고치지 말고 실험을 돌리지 마라. 너는 두 번째 의견이다: 답의 사실 주장·추론·결정(코드 변경, 실험 설계, '
              '판정, 반박)에 반박할 것이 있거나, 사용자의 질문에 더 나은 다른 제안이 있으면 번호를 붙여 짧게 말하고 근거'
              '(파일:줄, 숫자, 명령)를 적는다. 동의하는 부분은 반복하지 않고, 문체·형식·사소한 표현은 보지 않는다. 커밋이 있으면 '
              '`git diff <범위>`로 변경을 읽는다. 맥락이 필요하면 gaia-rl/lab/HANDOFF.md 5장·6장만 읽는다. 반박도 다른 제안도 '
              f'없으면 정확히 "{shared.CLEAN}" 한 줄만 쓴다. 한국어, 휴대폰에서 읽을 길이.)\n\n')


def codex_model():
    return os.environ.get('CODEX_MODEL') or 'gpt-6-astra'


def codex_bin():
    return os.environ.get('CODEX_BIN') or shutil.which('codex')


def codex_command(codex, workdir, out_path):
    """`codex exec` reading the prompt from stdin, read-only, last message written to out_path."""
    return [codex, 'exec', '--model', codex_model(), '--sandbox', 'read-only', '-c', 'approval_policy="never"',
            '--cd', str(workdir), '--color', 'never', '--output-last-message', str(out_path), '-']


def question_of(text, bot_id):
    """The owner's text addressed to this bot: a message mentioning it, or `!codex` prefixed; else None."""
    text = (text or '').strip()
    mentioned = any(int(m) == bot_id for m in MENTION.findall(text))
    stripped = MENTION.sub('', text).strip()
    if mentioned:
        return stripped or None
    return shared.codex_request(stripped)


def command_of(text):
    """'!status' / '!stop' / '!new' when the addressed text is one of this bot's commands, else None."""
    text = (text or '').strip()
    return text if text in COMMANDS else None


def context_block(rows, each=600, total=6000):
    """'## 최근 대화' from (speaker, text) rows, oldest first, trimmed so the prompt stays small."""
    lines, used = [], 0
    for speaker, text in rows:
        text = ' '.join((text or '').split())[:each]
        if not text:
            continue
        line = f'- {speaker}: {text}'
        if used + len(line) > total:
            break
        lines.append(line)
        used += len(line)
    return '## 최근 대화 (오래된 것부터)\n' + '\n'.join(lines) + '\n\n' if lines else ''


def question_prompt(question, context):
    return (f'{QUESTION_NOTE}{context}## 질문\n{question.strip()}\n\n'
            '(위 대화의 Claude 답에 반박할 것이 있으면 근거(파일:줄, 숫자, 명령)와 함께 말한다.)\n')


def watch_prompt(user_text, reply, before, after, log):
    """The review request for one finished turn; the commit range lets Codex read the diff itself."""
    if before and after and before != after:
        commits = f'## 커밋 {before[:7]}..{after[:7]} (`git diff {before[:7]}..{after[:7]}`)\n{log.strip()}'
    else:
        commits = '## 커밋 없음'
    return f'{WATCH_NOTE}## 사용자\n{user_text.strip()}\n\n## Claude\n{reply.strip()}\n\n{commits}\n'


def watch_findings(text):
    """Codex's objections, or '' when it answered "결론: 이상 없음" (or nothing)."""
    text = (text or '').strip()
    return '' if not text or shared.CLEAN in text else text


def findings_messages(findings, model):
    """The watch's objections as channel messages: every part starts with 🔍 so the Claude bot can collect them."""
    parts = shared.chunks(findings.strip(), size=1800)
    return [(f'{HEADER}({model}) 검수 지적 — 다음 메시지에서 Claude가 받는다\n' if i == 0 else f'{CONTINUED}\n') + part
            for i, part in enumerate(parts)]


def is_one_off(text):
    return FOOTER_ONE_OFF in (text or '')


def watch_enabled():
    return os.environ.get('CODEX_WATCH', '1').strip().lower() not in ('0', '', 'false', 'no', 'off')


def watch_minutes():
    return float(os.environ.get('CODEX_WATCH_MINUTES') or 5)


def watch_delay():
    return float(os.environ.get('CODEX_WATCH_DELAY') or 20)


def turn_minutes():
    return float(os.environ.get('CODEX_TURN_MINUTES') or 10)


def context_size():
    return int(os.environ.get('CODEX_CONTEXT') or 12)


def digest():
    return hashlib.sha256(SELF.read_bytes() + Path(shared.SELF).read_bytes()).hexdigest()


def main():
    import discord

    token = os.environ['CODEX_BOT_TOKEN']
    owner = int(os.environ['DISCORD_OWNER_ID'])
    channels = [int(c) for c in os.environ.get('DISCORD_CHANNEL_IDS', '').split(',') if c.strip()]
    claude_bot = int(os.environ.get('CLAUDE_BOT_ID') or 0)
    workdir = Path(os.path.expanduser(os.environ.get('GAIA_WORKDIR', '~/projects/gaia-work')))
    turns = {}      # channel key -> {'user': text, 'before': sha, 'claude': [texts], 'timer': task, 'skip': bool}
    busy = set()    # codex tasks running (a restart would kill them)
    running = {}    # 'proc': the codex process of the current direct question (the `!stop` target)
    source = [digest()]

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    async def send(channel, text):
        for part in shared.chunks(text):
            await channel.send(part)

    @client.event
    async def on_ready():
        print(f'connected as {client.user}; channels {channels}; workdir {workdir}; '
              f'watch {"on" if watch_enabled() else "off"}', flush=True)

    def restart_if_changed():
        """Continue as the new version when a turn edited this file or discord_claude.py; only when idle."""
        if busy:
            return
        current = digest()
        if current == source[0]:
            return
        source[0] = current
        try:
            py_compile.compile(str(SELF), doraise=True)
            py_compile.compile(str(shared.SELF), doraise=True)
        except py_compile.PyCompileError as error:
            print(f'bot source changed but does not compile; keeping the running version: {error}', flush=True)
            return
        print('discord_codex.py or discord_claude.py changed: restarting', flush=True)
        os.execv(sys.executable, [sys.executable, *sys.argv])

    def track(coro):
        task = asyncio.create_task(coro)
        busy.add(task)

        def finished(done, _task=task):
            busy.discard(_task)
            if not done.cancelled() and done.exception() is not None:
                print(f'codex task failed: {done.exception()!r}', flush=True)
            restart_if_changed()
        task.add_done_callback(finished)
        return task

    async def codex_exec(prompt, seconds, stoppable=False):
        """(last message, error text, exit code) of one read-only `codex exec` without the bots' secrets in its env."""
        binary = codex_bin()
        if not binary:
            return '', 'codex 미설치: `npm install -g @openai/codex` 뒤 `codex login` (봇 기계에서)', None
        fd, out_path = tempfile.mkstemp(prefix='codex-bot-', suffix='.md')
        os.close(fd)
        out_path = Path(out_path)
        try:
            proc = await asyncio.create_subprocess_exec(
                *codex_command(binary, workdir, out_path), cwd=workdir, env=shared.clean_env(),
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            if stoppable:
                running['proc'] = proc
            try:
                out, err = await asyncio.wait_for(proc.communicate(prompt.encode()), seconds)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                out, err = b'', f'{seconds/60:.0f}분 제한 초과로 중단'.encode()
            finally:
                if stoppable:
                    running.pop('proc', None)
            text = out_path.read_text(errors='replace').strip() if out_path.exists() else ''
        finally:
            out_path.unlink(missing_ok=True)
        error = (err.decode(errors='replace') or out.decode(errors='replace')).strip()[-1200:]
        return text, error, proc.returncode

    async def git(*args):
        proc = await asyncio.create_subprocess_exec('git', *args, cwd=workdir, stdout=asyncio.subprocess.PIPE,
                                                    stderr=asyncio.subprocess.DEVNULL)
        out, _ = await proc.communicate()
        return out.decode(errors='replace').strip()

    def speaker(message):
        if message.author.id == owner:
            return '사용자'
        if client.user and message.author.id == client.user.id:
            return 'Codex'
        return 'Claude' if message.author.bot else message.author.display_name

    async def recent_context(message):
        rows = []
        try:
            async for m in message.channel.history(limit=context_size(), before=message):
                if m.webhook_id is None and (m.author.id == owner or m.author.bot):
                    rows.append((speaker(m), m.content))
        except discord.DiscordException as error:
            print(f'history failed: {error!r}', flush=True)
        return context_block(reversed(rows))

    async def answer(message, question):
        async with message.channel.typing():
            context = await recent_context(message)
            text, error, code = await codex_exec(question_prompt(question, context), turn_minutes()*60, stoppable=True)
        reply = text or f'⚠️ Codex 실행 실패 (종료 코드 {code})\n```\n{error}\n```'
        await send(message.channel, f'{reply}\n🧠 {codex_model()} · 읽기 전용')

    async def run_command(message, command):
        if command == '!status':
            state = '실행 중' if running or busy else '대기'
            watch = '켜짐' if watch_enabled() else '꺼짐'
            await message.channel.send(f'상태: {state} · 검수 {watch} · 모델 {codex_model()} · 작업 폴더 {workdir}')
        elif command == '!stop':
            proc = running.get('proc')
            if proc and proc.returncode is None:
                proc.terminate()
                await message.channel.send('실행 중인 작업을 중단했습니다.')
            else:
                await message.channel.send('실행 중인 작업이 없습니다.')
        elif command == '!new':
            await message.channel.send('Codex는 대화를 이어 가지 않습니다(질문마다 최근 메시지를 맥락으로 읽음). 바꿀 것이 없습니다.')

    def is_claude(message):
        if message.webhook_id is not None or not message.author.bot:
            return False
        if client.user and message.author.id == client.user.id:
            return False
        return not claude_bot or message.author.id == claude_bot

    async def review(channel, key):
        """The watch for one finished Claude turn, started when Claude's reply went quiet."""
        turn = turns.pop(key, None)
        if not turn or turn.get('skip') or not turn.get('claude'):
            return
        reply = '\n'.join(turn['claude'])
        if is_one_off(reply):
            return
        user_text = turn.get('user') or '(사용자 메시지 없음: lab 알림이 연 자동 턴)'
        before = turn.get('before') or ''
        after = await git('rev-parse', 'HEAD')
        log = await git('log', '--oneline', f'{before}..{after}') if before and after and before != after else ''
        text, error, code = await codex_exec(watch_prompt(user_text, reply, before, after, log), watch_minutes()*60)
        if not text:
            await send(channel, f'⚠️ Codex 대화 검수 실패 (종료 코드 {code})\n```\n{error}\n```')
            return
        findings = watch_findings(text)
        if not findings:
            await channel.send(f'{HEADER}({codex_model()}): 이상 없음')
            return
        for part in findings_messages(findings, codex_model()):
            await channel.send(part)

    async def later(channel, key):
        await asyncio.sleep(watch_delay())
        await review(channel, key)

    def cancel_timer(key):
        timer = turns.get(key, {}).get('timer')
        if timer and not timer.done():
            timer.cancel()

    def schedule(channel, key):
        cancel_timer(key)
        turns.setdefault(key, {})['timer'] = track(later(channel, key))

    @client.event
    async def on_message(message):
        is_dm = isinstance(message.channel, discord.DMChannel)
        if message.webhook_id is not None or (not is_dm and message.channel.id not in channels):
            return
        key = str(message.channel.id)
        if client.user and message.author.id == client.user.id:
            return
        if message.author.id == owner:
            text = message.content.strip()
            addressed = question_of(text, client.user.id if client.user else 0)
            if addressed:
                command = command_of(addressed)
                if command:
                    await run_command(message, command)
                    return
                await message.add_reaction('⏳' if busy else '👀')
                await track(answer(message, addressed))
                return
            # An ordinary message: Claude will answer it; remember it (and HEAD) for the watch.
            cancel_timer(key)
            turns[key] = {'user': text, 'before': await git('rev-parse', 'HEAD'), 'claude': [],
                          'skip': text.startswith('!') or (not text and not message.attachments)}
            return
        if is_claude(message) and watch_enabled():
            turn = turns.setdefault(key, {'claude': []})
            if not turn.get('before'):
                turn['before'] = await git('rev-parse', 'HEAD')   # an automatic turn (lab notice): no owner message
            turn.setdefault('claude', []).append(message.content)
            schedule(message.channel, key)

    client.run(token)


if __name__ == '__main__':
    main()
