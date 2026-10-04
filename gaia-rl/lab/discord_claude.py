"""Discord → Claude Code on demand: a small always-on bot that runs `claude -p` per message.

Only the owner's messages in the configured channels (or the owner's DMs) reach Claude.
Each message runs one non-interactive Claude Code turn in GAIA_WORKDIR with the permission
rules in lab/claude-bot-settings.json and permission mode dontAsk: tools outside the allow
list are refused instead of prompting, and the reply lists what was refused so the owner can
run it by hand. A channel keeps one conversation (`--resume`) until `!new`.

Commands (owner only): `!new` start a fresh conversation, `!status` show state, `!stop` cancel
the running turn. Turns run one at a time; later messages wait in order.

Environment (lab/discord_claude.env, git-ignored; see lab/discord_claude.env.example):
  DISCORD_BOT_TOKEN, DISCORD_OWNER_ID, DISCORD_CHANNEL_IDS (comma-separated),
  GAIA_WORKDIR (default ~/projects/gaia-work), CLAUDE_BIN (default: claude on PATH),
  CLAUDE_TURN_MINUTES (default 30), GAIA_BOT_STATE (default ~/.gaia-claude-bot.json).
"""
import asyncio
import json
import os
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
SETTINGS = HERE/'claude-bot-settings.json'
SYSTEM = (
    'You are reached from Discord through an on-demand bot (one `claude -p` turn per message). '
    'Answer in Korean, briefly: replies are read on a phone. Before substantive work read '
    'gaia-rl/lab/HANDOFF.md and follow its rules (section 6 above all). You cannot ask for '
    'permission mid-turn: a refused tool is reported to the owner, so when an action needs '
    'confirmation or is outside your allowed tools, stop and give the exact command for the '
    'owner to run instead. Never print secrets (.env values, tokens, webhook URLs). '
    'Your working directory is the work tree ~/projects/gaia-work (branch work): start each topic '
    'with `git pull --rebase origin claude/epic-goodall-0ot55w` to see new lab results, push with '
    '`git push origin HEAD:claude/epic-goodall-0ot55w`. Keep shell commands simple: run git in the '
    'working directory (no -C), one command per call, and prefer the Read/Grep/Glob tools for '
    'files; a pipe or && chain is refused if any part is outside the allow list. A command '
    'containing a newline is refused too: write commit messages on one line with repeated -m '
    'flags (git commit -m "subject" -m "body" -m "trailer"), never a multi-line string.')


def chunks(text, size=1900):
    """Discord's 2000-character limit, split on lines, keeping code fences balanced."""
    parts, current, fenced = [], [], False
    for line in text.splitlines() or ['(빈 응답)']:
        if current and sum(len(l)+1 for l in current)+len(line) > size:
            parts.append('\n'.join(current+(['```'] if fenced else [])))
            current = ['```'] if fenced else []
        current.append(line[:size])
        if line.lstrip().startswith('```'):
            fenced = not fenced
    if current:
        parts.append('\n'.join(current))
    return parts


def command(claude, session_id):
    argv = [claude, '-p', '--output-format', 'json', '--permission-mode', 'dontAsk',
            '--settings', str(SETTINGS), '--append-system-prompt', SYSTEM]
    if session_id:
        argv += ['--resume', session_id]
    return argv


def summarize(stdout, stderr, code):
    """(reply text, session id or None) from one `claude -p --output-format json` run."""
    try:
        result = json.loads(stdout)
    except ValueError:
        tail = (stderr or stdout).strip()[-1500:]
        return f'⚠️ Claude 실행 실패 (종료 코드 {code})\n```\n{tail}\n```', None
    text = result.get('result') or ''
    if result.get('is_error') or result.get('subtype', 'success') != 'success':
        text = f"⚠️ {result.get('subtype', 'error')}\n{text}".strip()
    denied = result.get('permission_denials') or []
    if denied:
        names = []
        for d in denied:
            tool = d.get('tool_name', '?')
            detail = (d.get('tool_input') or {}).get('command') or (d.get('tool_input') or {}).get('file_path') or ''
            names.append(f'- {tool} `{detail[:150]}`' if detail else f'- {tool}')
        text += '\n\n🔒 허용 목록 밖이라 거부됨 (필요하면 직접 실행):\n' + '\n'.join(dict.fromkeys(names))
    return text, result.get('session_id')


def load_state(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def main():
    import discord

    token = os.environ['DISCORD_BOT_TOKEN']
    owner = int(os.environ['DISCORD_OWNER_ID'])
    channels = {int(c) for c in os.environ.get('DISCORD_CHANNEL_IDS', '').split(',') if c.strip()}
    workdir = Path(os.path.expanduser(os.environ.get('GAIA_WORKDIR', '~/projects/gaia-work')))
    claude = os.environ.get('CLAUDE_BIN') or shutil.which('claude') or 'claude'
    turn_seconds = float(os.environ.get('CLAUDE_TURN_MINUTES', '30'))*60
    state_path = Path(os.path.expanduser(os.environ.get('GAIA_BOT_STATE', '~/.gaia-claude-bot.json')))
    state = load_state(state_path)  # {channel id: session id}
    lock = asyncio.Lock()
    running = {}

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    def save():
        state_path.write_text(json.dumps(state))

    async def send(channel, text):
        for part in chunks(text):
            await channel.send(part)

    @client.event
    async def on_ready():
        print(f'connected as {client.user}; channels {sorted(channels)}; workdir {workdir}', flush=True)

    @client.event
    async def on_message(message):
        if message.author.id != owner or message.webhook_id is not None:
            return
        is_dm = isinstance(message.channel, discord.DMChannel)
        if not is_dm and message.channel.id not in channels:
            return
        key = str(message.channel.id)
        text = message.content.strip()
        if text == '!new':
            state.pop(key, None)
            save()
            await message.channel.send('새 대화로 시작합니다.')
            return
        if text == '!status':
            busy = '실행 중' if running else '대기'
            await message.channel.send(f'상태: {busy} · 대화 {state.get(key, "(새 대화)")} · 작업 폴더 {workdir}')
            return
        if text == '!stop':
            proc = running.get('proc')
            if proc and proc.returncode is None:
                proc.terminate()
                await message.channel.send('실행 중인 작업을 중단했습니다.')
            else:
                await message.channel.send('실행 중인 작업이 없습니다.')
            return
        if not text:
            return
        if lock.locked():
            await message.add_reaction('⏳')
        async with lock:
            await message.add_reaction('👀')
            async with message.channel.typing():
                proc = await asyncio.create_subprocess_exec(
                    *command(claude, state.get(key)), cwd=workdir,
                    stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE)
                running['proc'] = proc
                try:
                    out, err = await asyncio.wait_for(proc.communicate(text.encode()), turn_seconds)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                    out, err = b'', f'{turn_seconds/60:.0f}분 제한 초과로 중단'.encode()
                finally:
                    running.pop('proc', None)
            reply, session = summarize(out.decode(errors='replace'), err.decode(errors='replace'), proc.returncode)
            if session:
                state[key] = session
                save()
            await send(message.channel, reply)

    client.run(token)


if __name__ == '__main__':
    main()
