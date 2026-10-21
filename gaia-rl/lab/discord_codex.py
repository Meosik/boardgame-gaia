"""Discord → Codex: the second model as its own bot, next to the Claude bot (lab/discord_claude.py).

User 2026-10-22 "봇을 하나 새로 더 만드는 방식으로 가자": Codex gets its own Discord identity and process, so it
answers while Claude is busy with a long turn, survives the Claude bot's restarts, and can be addressed directly.
Everything it runs is one read-only `codex exec` in GAIA_WORKDIR; it never edits files, commits or runs experiments.

What it does, in the Claude bot's channels (DISCORD_CHANNEL_IDS) and the owner's DMs:
  - answers the owner's messages that mention it (`@Codex 질문`) or start with `!codex ` / `!gpt `, with the last
    CODEX_CONTEXT channel messages (owner, Claude, itself) as context; the Claude bot skips those messages;
  - watches the conversation: after the Claude bot's reply to an owner message goes quiet for CODEX_WATCH_DELAY
    seconds, it reviews the owner's message, Claude's reply and the commits made meanwhile (HEAD before/after) and
    posts objections as `🔍 코덱스(<model>) 검수 지적 …` (or one line `이상 없음`); the Claude bot reads those
    messages from the channel and puts them in front of the owner's next message. The Claude bot's in-process
    watch is off while CODEX_BOT_TOKEN is set.

Environment (lab/discord_claude.env, shared with the Claude bot): CODEX_BOT_TOKEN (this bot's token),
DISCORD_OWNER_ID, DISCORD_CHANNEL_IDS, GAIA_WORKDIR, CODEX_BIN, CODEX_MODEL, CODEX_WATCH (0 turns the watch off),
CODEX_WATCH_MINUTES (default 5), CODEX_WATCH_DELAY (seconds of silence after Claude's reply, default 20),
CODEX_TURN_MINUTES (default 10, direct questions), CODEX_CONTEXT (default 12 messages), CLAUDE_BOT_ID (optional:
only this bot's messages count as Claude's; default: any other bot that is not a webhook).
"""
import asyncio
import hashlib
import os
from pathlib import Path
import py_compile
import re
import sys

import discord_claude as shared

SELF = Path(__file__).resolve()
MENTION = re.compile(r'<@!?(\d+)>')
HEADER = '🔍 코덱스'
CONTINUED = '🔍 (계속)'
FOOTER_ONE_OFF = '일회성 답'   # the Claude bot's `!q` answers end with this; they are not reviewed


def question_of(text, bot_id):
    """The owner's question to Codex: a message mentioning the bot, or `!codex`/`!gpt` prefixed; else None."""
    text = (text or '').strip()
    mentioned = any(int(m) == bot_id for m in MENTION.findall(text))
    stripped = MENTION.sub('', text).strip()
    if mentioned:
        return stripped or None
    return shared.codex_request(stripped)


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
    return (f'{shared.CODEX_NOTE}{context}## 질문\n{question.strip()}\n\n'
            '(위 대화의 Claude 답에 반박할 것이 있으면 근거(파일:줄, 숫자, 명령)와 함께 말한다.)\n')


def findings_messages(findings, model):
    """The watch's objections as channel messages: every part starts with 🔍 so the Claude bot can collect them."""
    parts = shared.chunks(findings.strip(), size=1800)
    return [(f'{HEADER}({model}) 검수 지적 — 다음 메시지에서 Claude가 받는다\n' if i == 0 else f'{CONTINUED}\n') + part
            for i, part in enumerate(parts)]


def is_one_off(text):
    return FOOTER_ONE_OFF in (text or '')


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
              f'watch {"on" if shared.watch_enabled() else "off"}', flush=True)

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
            if done.exception() is not None:
                print(f'codex task failed: {done.exception()!r}', flush=True)
            restart_if_changed()
        task.add_done_callback(finished)
        return task

    async def codex_exec(prompt, seconds):
        binary = shared.codex_bin()
        if not binary:
            return '', 'codex 미설치: `npm install -g @openai/codex` 뒤 `codex login` (봇 기계에서)', None
        import tempfile
        fd, out_path = tempfile.mkstemp(prefix='codex-bot-', suffix='.md')
        os.close(fd)
        out_path = Path(out_path)
        try:
            proc = await asyncio.create_subprocess_exec(
                *shared.codex_command(binary, workdir, out_path), cwd=workdir, stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            try:
                out, err = await asyncio.wait_for(proc.communicate(prompt.encode()), seconds)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                out, err = b'', f'{seconds/60:.0f}분 제한 초과로 중단'.encode()
            text = out_path.read_text(errors='replace').strip() if out_path.exists() else ''
        finally:
            out_path.unlink(missing_ok=True)
        error = (err.decode(errors='replace') or out.decode(errors='replace')).strip()[-1200:]
        return text, error, proc.returncode

    async def git_head():
        proc = await asyncio.create_subprocess_exec('git', 'rev-parse', 'HEAD', cwd=workdir,
                                                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        out, _ = await proc.communicate()
        return out.decode(errors='replace').strip()

    async def git_log(before, after):
        if not (before and after) or before == after:
            return ''
        proc = await asyncio.create_subprocess_exec('git', 'log', '--oneline', f'{before}..{after}', cwd=workdir,
                                                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
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
            text, error, code = await codex_exec(question_prompt(question, context), turn_minutes()*60)
        reply = text or f'⚠️ codex 실행 실패 (종료 코드 {code})\n```\n{error}\n```'
        await send(message.channel, f'{reply}\n🧠 {shared.codex_model()} · 읽기 전용')

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
        after = await git_head()
        log = await git_log(before, after)
        text, error, code = await codex_exec(shared.watch_prompt(user_text, reply, before, after, log),
                                             shared.watch_minutes()*60)
        if not text:
            await send(channel, f'⚠️ 코덱스 대화 검수 실패 (종료 코드 {code})\n```\n{error}\n```')
            return
        findings = shared.watch_findings(text)
        if not findings:
            await channel.send(f'{HEADER}({shared.codex_model()}): 이상 없음')
            return
        for part in findings_messages(findings, shared.codex_model()):
            await channel.send(part)

    async def later(channel, key):
        await asyncio.sleep(watch_delay())
        await review(channel, key)

    def schedule(channel, key):
        turn = turns.setdefault(key, {})
        timer = turn.get('timer')
        if timer and not timer.done():
            timer.cancel()
        turn['timer'] = track(later(channel, key))

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
            question = question_of(text, client.user.id if client.user else 0)
            if question:
                await message.add_reaction('👀')
                await track(answer(message, question))
                return
            # An ordinary message: Claude will answer it; remember it (and HEAD) for the watch.
            timer = turns.get(key, {}).get('timer')
            if timer and not timer.done():
                timer.cancel()
            turns[key] = {'user': text, 'before': await git_head(), 'claude': [],
                          'skip': text.startswith('!') or (not text and not message.attachments)}
            return
        if is_claude(message) and shared.watch_enabled():
            turn = turns.setdefault(key, {'claude': []})
            if not turn.get('before'):
                turn['before'] = await git_head()   # an automatic turn (lab notice): no owner message before it
            turn.setdefault('claude', []).append(message.content)
            schedule(message.channel, key)

    client.run(token)


if __name__ == '__main__':
    main()
