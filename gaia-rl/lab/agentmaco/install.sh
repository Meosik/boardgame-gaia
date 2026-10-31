#!/usr/bin/env bash
# agentmaco 봇 설치 — 사용자가 한 번 실행한다. 어느 단계든 실패하면 그 자리에서 멈춘다(set -e):
# env 파일이 검증·설치된 뒤에만 기존 Node 봇을 중단하고 서비스를 올린다. 토큰 값은 화면에 나오지 않는다.
set -euo pipefail
MA=~/projects/multi-ai
HERE=~/projects/gaia-work/gaia-rl/lab/agentmaco
ENV=~/.config/gaia/discord-agentmaco.env

mkdir -p ~/.config/gaia
T=$(mktemp)
trap 'rm -f "$T"' EXIT
grep '^DISCORD_BOT_TOKEN=.' "$MA/.env" > "$T"                                    # 토큰 줄이 없으면 여기서 멈춤
grep -v '^DISCORD_BOT_TOKEN=' "$HERE/discord-agentmaco.env.example" >> "$T"       # 예시 파일이 없으면 여기서 멈춤
[ "$(grep -c '^DISCORD_BOT_TOKEN=.' "$T")" = 1 ] || { echo "토큰 줄이 1개가 아님" >&2; exit 1; }
install -m 600 "$T" "$ENV"                                                        # 기존 파일이 644여도 600으로

mkdir -p "$MA/.workflow/inbox"
grep -qx '.workflow/inbox/' "$MA/.gitignore" 2>/dev/null || printf '.workflow/inbox/\n' >> "$MA/.gitignore"

(cd "$MA" && python3 scripts/agent.py stop)   # Node 봇 중단(같은 토큰: 둘이 뜨면 두 번 답함) — env 검증 뒤에만
mkdir -p ~/.config/systemd/user
cp "$HERE/discord-agentmaco.service" ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now discord-agentmaco
sleep 3
journalctl --user -u discord-agentmaco -n 3   # "connected as …; channels [1554144240127442945]" 가 보여야 한다
echo OK
