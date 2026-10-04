#!/usr/bin/env bash
# One-time setup of the experiment lab on an always-on Linux host (e.g. agentmaco).
# Uses a separate checkout (~/projects/gaia-lab), never the live server's checkout.
#   bash setup-host.sh <git remote url>
set -euo pipefail
remote="${1:?usage: setup-host.sh <git remote url, e.g. from: git -C ~/projects/gaia remote get-url origin>}"
branch=claude/epic-goodall-0ot55w
dir="$HOME/projects/gaia-lab"

command -v python3.12 >/dev/null || { echo "python3.12 이 필요합니다"; exit 1; }
command -v cargo >/dev/null || [ -x "$HOME/.cargo/bin/cargo" ] || {
  echo "Rust가 필요합니다: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y"; exit 1; }
export PATH="$HOME/.cargo/bin:$PATH"

[ -d "$dir/.git" ] || git clone --branch "$branch" "$remote" "$dir"
cd "$dir/gaia-rl"
git pull --ff-only origin "$branch"

[ -x .venv/bin/python ] || python3.12 -m venv .venv
.venv/bin/pip install -q --upgrade pip "maturin>=1.15,<2.0"
VIRTUAL_ENV="$PWD/.venv" .venv/bin/maturin develop --release
PYTHONPATH=tools .venv/bin/python -m unittest tools/test_lab.py

[ -f lab/lab.env ] || cp lab/lab.env.example lab/lab.env
git push --dry-run origin "HEAD:$branch" >/dev/null 2>&1 \
  || echo "⚠️  이 체크아웃에서 push 권한이 없습니다. 결과를 올리려면 토큰/SSH 키를 설정하세요."

mkdir -p "$HOME/.config/systemd/user"
cp lab/gaia-lab.service "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable --now gaia-lab
loginctl show-user "$USER" -p Linger | grep -q yes \
  || echo "로그아웃 후에도 돌게 하려면: sudo loginctl enable-linger $USER"
echo "완료. 상태: systemctl --user status gaia-lab   로그: journalctl --user -u gaia-lab -f"
