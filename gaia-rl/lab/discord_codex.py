"""Discord → Codex: the second model as its own bot, next to the Claude bot (lab/discord_claude.py).

User 2026-10-22 "봇을 하나 새로 더 만드는 방식으로 가자" → "claude는 내부에서 codex 호출하는건 없애되, codex봇이 claude의 말에
반박하는 체계는 유지": Codex has its own Discord identity and process; the Claude bot calls no Codex at all.
Everything here is one read-only `codex exec` in GAIA_WORKDIR: it never edits files, commits or runs experiments.

In the Claude bot's channels (DISCORD_CHANNEL_IDS) and the owner's DMs:
  - a message addressed to this bot — a mention (`@Codex 질문`) or the `!codex ` prefix — gets an answer with the
    last CODEX_CONTEXT channel messages (owner, Claude, itself) as context; `!status`, `!stop`, `!new` addressed
    the same way are this bot's commands. The Claude bot skips every message addressed here.
  - debate mode (DEBATE_ROUNDS, default 1; user 2026-10-22 "둘이 따로 생각하고, 나온 의견을 가지고 토론하는 모습"):
    an ordinary owner message gets this bot's own answer at once (`💭 코덱스(<model>) 독립 답`, written while Claude
    is still answering, so neither sees the other); when Claude's reply has been quiet for CODEX_WATCH_DELAY seconds,
    round 1: Codex reads the owner's message, both answers and the commits made meanwhile (HEAD before/after) and
    posts `🔍 코덱스(<model>) 토론 1/N …` (rebuttals or a better proposal) or one line `토론 1/N: 이상 없음`; the Claude
    bot answers a round at once (`🗣️ 토론 r/N`), and after its answer round r+1 follows while r < N. `!solo <text>`
    (any `!` message) keeps Codex out. DEBATE_ROUNDS=0 is the plain watch: `🔍 코덱스(<model>) 검수 지적 …` after
    Claude's reply, read by the Claude bot in front of the owner's next message. The Claude bot's `!q` answers
    (`일회성 답`) and its answers to `!`-commands are never reviewed.

Icons and commands follow the table in lab/README.md ("두 봇의 명령·아이콘"): 👀 received, ⏳ queued behind a
running task, `🧠 <model> · <note>` as the last line of every model answer, ⚠️ a failure, 🔍 a review.

Environment (~/.config/gaia/discord-bots.env, shared with the Claude bot): CODEX_BOT_TOKEN, DISCORD_OWNER_ID,
DISCORD_CHANNEL_IDS, GAIA_WORKDIR, CODEX_BIN (default: codex on PATH), CODEX_MODEL (default gpt-6-astra),
CODEX_WATCH (0 turns the watch and the debate rounds off), CODEX_WATCH_MINUTES (default 5, one round or watch),
CODEX_WATCH_DELAY (seconds of silence after Claude's reply, default 20), CODEX_TURN_MINUTES (default 10, direct
questions and independent answers), CODEX_CONTEXT (default 12 messages), DEBATE_ROUNDS (default 1, shared with the
Claude bot), CLAUDE_BOT_ID (optional: only this bot's messages count as Claude's; default: any other bot that is not
a webhook).
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
OWN_HEADER = '💭 코덱스'   # the independent answer of debate mode (not an objection: the Claude bot ignores 💭)
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

# User 2026-10-22 "둘이 따로 생각하고, 나온 의견을 가지고 토론하는 모습": the independent answer and the debate rounds.
OWN_NOTE = ('(사용자가 채널에 올린 메시지다. Claude 봇도 같은 메시지에 지금 따로 답하고 있다 — 너는 Claude의 답을 보지 않고 '
            '독립적으로 답한다. 저장소는 읽기 전용이다: 파일을 고치지 말고 실험을 돌리지 마라. 실행·수정이 필요한 요청이면 Claude가 '
            '하므로, 너는 무엇을 어떻게 해야 하는지와 주의할 점을 적는다; 질문이면 답한다. 맥락이 필요하면 gaia-rl/lab/HANDOFF.md '
            '5장·6장만 읽는다. 한국어, 휴대폰에서 읽을 길이.)\n\n')
DEBATE_NOTE = ('(토론 {round}/{rounds}. 아래는 사용자의 메시지, 같은 메시지에 대한 네 독립 답, Claude의 답과 지금까지의 토론, '
               '이 턴에 Claude가 만든 커밋 범위다. 저장소는 읽기 전용이다: 파일을 고치지 말고 실험을 돌리지 마라. Claude의 사실 '
               '주장·추론·결정(코드 변경, 실험 설계, 판정, 반박)에 반박할 것이 있거나 더 나은 다른 제안이 있으면 번호를 붙여 짧게 '
               '말하고 근거(파일:줄, 숫자, 명령)를 적는다; Claude가 네 앞 지적을 반박했으면 수긍하거나 근거를 들어 재반박한다. '
               '동의하는 부분은 반복하지 않고, 문체·형식·사소한 표현은 보지 않는다. 커밋이 있으면 `git diff <범위>`로 변경을 읽는다. '
               f'반박도 다른 제안도 없으면 정확히 "{shared.CLEAN}" 한 줄만 쓴다. 한국어, 휴대폰에서 읽을 길이.)\n\n')


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


def commits_block(before, after, log):
    if before and after and before != after:
        return f'## 커밋 {before[:7]}..{after[:7]} (`git diff {before[:7]}..{after[:7]}`)\n{log.strip()}'
    return '## 커밋 없음'


def watch_prompt(user_text, reply, before, after, log):
    """The review request for one finished turn; the commit range lets Codex read the diff itself."""
    return f'{WATCH_NOTE}## 사용자\n{user_text.strip()}\n\n## Claude\n{reply.strip()}\n\n{commits_block(before, after, log)}\n'


def own_prompt(text, context):
    """The independent answer of debate mode: the owner's message with the conversation before it."""
    return f'{OWN_NOTE}{context}## 사용자\n{text.strip()}\n'


def debate_prompt(user_text, own, exchange, round_no, rounds, before, after, log):
    """Round `round_no`: the owner's message, this bot's independent answer, the exchange (Claude first) and commits.

    exchange: (speaker, text) in order — Claude's reply, then this bot's earlier rounds and Claude's answers."""
    talk = '\n\n'.join(f'## {speaker}\n{text.strip()}' for speaker, text in exchange if text and text.strip())
    return (DEBATE_NOTE.format(round=round_no, rounds=rounds) + f'## 사용자\n{user_text.strip()}\n\n'
            f'## 네 독립 답\n{own.strip() or "(없음)"}\n\n{talk}\n\n{commits_block(before, after, log)}\n')


def debate_messages(findings, model, round_no, rounds):
    """One round's objections as channel messages: the first part's header carries `토론 r/N` for the Claude bot."""
    parts = shared.chunks(findings.strip(), size=1800)
    return [(f'{HEADER}({model}) 토론 {round_no}/{rounds} — Claude가 바로 답한다\n' if i == 0 else f'{CONTINUED}\n') + part
            for i, part in enumerate(parts)]


def own_message(text, model):
    return f'{OWN_HEADER}({model}) 독립 답\n{text.strip()}\n🧠 {model} · 읽기 전용'


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


def recovered_turn(rows):
    """The turn an owner message began when Claude's reply finds no turn in memory (this bot restarted in between).

    rows: (is_owner, is_claude, content) newest first, the channel before Claude's reply. The nearest owner message
    gives {'user', 'skip'}; a Claude 🤖 notice first means an automatic lab turn (no owner message): {}."""
    for is_owner, is_claude, content in rows:
        content = (content or '').strip()
        if is_owner:
            return {'user': content, 'skip': content.startswith('!') or not content}
        if is_claude and content.startswith('🤖'):
            return {}
    return {}


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
    turns = {}      # channel key -> {'user': text, 'before': sha, 'claude': [texts], 'timer': task, 'skip': bool,
                    #                 'own': task of the independent answer, 'exchange': [(speaker, text)], 'round': n}
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
              f'watch {"on" if watch_enabled() else "off"}; debate rounds {shared.debate_rounds()}', flush=True)

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
            except asyncio.CancelledError:   # the task was cancelled: do not leave the codex process running
                proc.kill()
                await proc.wait()
                raise
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

    async def own_answer(message, text):
        """Debate mode: this bot's own answer to the owner's message, posted as soon as it is ready; returns it."""
        async with message.channel.typing():
            context = await recent_context(message)
            answer_text, error, code = await codex_exec(own_prompt(text, context), turn_minutes()*60, stoppable=True)
        if not answer_text:
            await send(message.channel, f'⚠️ Codex 독립 답 실패 (종료 코드 {code})\n```\n{error}\n```')
            return ''
        await send(message.channel, own_message(answer_text, codex_model()))
        return answer_text

    async def run_command(message, command):
        if command == '!status':
            state = '실행 중' if running or busy else '대기'
            watch = '켜짐' if watch_enabled() else '꺼짐'
            rounds = shared.debate_rounds()
            debate = f'토론 {rounds}라운드' if rounds else '토론 꺼짐(검수만)'
            await message.channel.send(f'상태: {state} · 검수 {watch} · {debate} · 모델 {codex_model()} · 작업 폴더 {workdir}')
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

    async def recover_turn(message):
        """The owner's message before Claude's reply, from the channel, when memory has no turn for it."""
        rows = []
        try:
            async for m in message.channel.history(limit=10, before=message):
                if m.webhook_id is None:
                    rows.append((m.author.id == owner, is_claude(m), m.content))
        except discord.DiscordException as error:
            print(f'history failed: {error!r}', flush=True)
        return recovered_turn(rows)

    async def review(channel, key):
        """The watch (DEBATE_ROUNDS=0) or the next debate round, started when Claude's reply went quiet."""
        rounds = shared.debate_rounds()
        turn = turns.get(key)
        if not turn or turn.get('skip') or not turn.get('claude'):
            turns.pop(key, None)
            return
        round_no = turn.get('round', 0) + 1
        if rounds and round_no > rounds:
            turns.pop(key, None)   # the debate is over: Claude's answer to the last round stands
            return
        if not rounds:
            turns.pop(key, None)   # the plain watch reviews a turn once
        reply = '\n'.join(turn['claude'])
        if is_one_off(reply):
            turns.pop(key, None)
            return
        user_text = turn.get('user') or '(사용자 메시지 없음: lab 알림이 연 자동 턴)'
        before = turn.get('before') or ''
        after = await git('rev-parse', 'HEAD')
        log = await git('log', '--oneline', f'{before}..{after}') if before and after and before != after else ''
        if rounds:
            own = ''
            if turn.get('own'):
                try:
                    # The independent answer, when it is still being written. Shielded: cancelling this round
                    # (a new Claude part or owner message resets the timer) must not cancel the answer itself.
                    own = await asyncio.shield(turn['own'])
                except Exception as error:   # noqa: BLE001 — a failed answer is just absent from the round
                    print(f'independent answer failed: {error!r}', flush=True)
            prompt = debate_prompt(user_text, own, turn.get('exchange') or [('Claude', reply)], round_no, rounds,
                                   before, after, log)
            label = f'토론 {round_no}/{rounds}'
        else:
            prompt = watch_prompt(user_text, reply, before, after, log)
            label = '검수'
        text, error, code = await codex_exec(prompt, watch_minutes()*60)
        if not text:
            await send(channel, f'⚠️ Codex 대화 {label} 실패 (종료 코드 {code})\n```\n{error}\n```')
            turns.pop(key, None)
            return
        findings = watch_findings(text)
        if not findings:
            await channel.send(f'{HEADER}({codex_model()}){" " + label if rounds else ""}: 이상 없음')
            turns.pop(key, None)
            return
        if rounds:
            turn['round'] = round_no
            turn.setdefault('exchange', []).append(('Codex', findings))
            parts = debate_messages(findings, codex_model(), round_no, rounds)
        else:
            parts = findings_messages(findings, codex_model())
        for part in parts:
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
            # An ordinary message: Claude will answer it; remember it (and HEAD) for the watch or the debate.
            # `!` messages (`!q`, `!solo`, commands) are Claude's alone.
            cancel_timer(key)
            skip = text.startswith('!') or (not text and not message.attachments)
            turns[key] = {'user': text, 'before': await git('rev-parse', 'HEAD'), 'claude': [], 'exchange': [],
                          'round': 0, 'skip': skip, 'own': None}
            if not skip and text and watch_enabled() and shared.debate_rounds():
                await message.add_reaction('⏳' if busy else '👀')
                turns[key]['own'] = track(own_answer(message, text))
            return
        if is_claude(message) and watch_enabled() and not message.content.startswith('🤖'):
            # (a 🤖 line only announces an automatic turn; the reply itself follows minutes later)
            turn = turns.get(key)
            if turn is None:
                # No turn in memory: an automatic turn (lab notice), or this bot restarted after the owner's message
                # (2026-10-22 12:30: the restart to the debate-mode code lost "자동 토론 방식인가?" and reviewed the
                # reply as an automatic turn, without an independent answer). The channel says which.
                turn = turns[key] = {'claude': [], 'exchange': [], 'round': 0, **await recover_turn(message)}
            if not turn.get('before'):
                turn['before'] = await git('rev-parse', 'HEAD')
            turn.setdefault('claude', []).append(message.content)
            turn.setdefault('exchange', []).append(('Claude', message.content))
            schedule(message.channel, key)

    client.run(token)


if __name__ == '__main__':
    main()
