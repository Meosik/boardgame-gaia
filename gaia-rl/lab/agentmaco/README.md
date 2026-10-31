# agentmaco 봇 — multi-ai 프로젝트용 두 번째 Claude 봇 (2026-10-31)

`~/projects/multi-ai`의 Node 봇(`bot/main.mjs`: Codex Astra 마스터 + Sol 작업자 + Claude 리뷰)을
gaia 봇 코드(`lab/discord_claude.py`)의 두 번째 서비스로 바꾼다. 사용자 결정: 마스터 Fable(Opus 대체),
작업자 Sonnet 서브에이전트, 리뷰 Astra 읽기 전용, 실행자 `claude -p`, 기존 multi-ai 토큰, systemd,
푸시는 origin master 직접(전용 브랜치 없음), 작업 기록은 TODO 본체 + `.workflow/STATUS.md` 30줄 색인.

이 폴더의 파일은 봇이 쓸 수 있는 곳이 `~/projects/gaia-work` 뿐이라 여기 두었고, 서비스가 절대 경로로 가리킨다.
agentmaco 봇이 뜬 뒤 자기 저장소(`multi-ai/bot/`)로 옮기는 것은 그 봇의 TODO로 한다.

| 파일 | 역할 |
|---|---|
| `system.md` | 시스템 프롬프트(`CLAUDE_BOT_SYSTEM_FILE`): 역할, 작업 폴더, STATUS 색인, TODO → Sonnet → evidence → `review.sh` 절차, 셸 규칙, 비밀 |
| `claude-bot-settings.json` | 허용 목록(`CLAUDE_BOT_SETTINGS`): 수정은 `~/projects/multi-ai/**`만, 푸시는 `git push origin HEAD:master`만, `rm`·`sudo`·force push·`scripts/agent.py`·`docker compose`·서비스 stop/restart 거부 |
| `discord-agentmaco.service` | systemd user 서비스(코드는 gaia-work의 `discord_claude.py`, env는 `~/.config/gaia/discord-agentmaco.env`) |
| `discord-agentmaco.env.example` | env 키(토큰만 비어 있음) |

허용 목록은 **직접 호출 제한**이다: `python3`·`node`·`scripts/*.sh` 안에서는 어떤 파일이든 읽고 지울 수 있다(코덱스 토론 10-31).
gaia 파일까지 보호하려면 별도 계정이나 파일시스템 격리가 필요하고, 그것은 사용자 결정.

## 설치 (사용자, 한 번)

```sh
cd ~/projects/gaia-work && git pull --rebase origin claude/epic-goodall-0ot55w
cp gaia-rl/lab/agentmaco/discord-agentmaco.env.example ~/.config/gaia/discord-agentmaco.env && chmod 600 ~/.config/gaia/discord-agentmaco.env
nano ~/.config/gaia/discord-agentmaco.env        # DISCORD_BOT_TOKEN= 에 multi-ai .env의 토큰(봇은 그 파일을 못 읽음)
mkdir -p ~/projects/multi-ai/.workflow/inbox && printf '.workflow/inbox/\n' >> ~/projects/multi-ai/.gitignore
cd ~/projects/multi-ai && python3 scripts/agent.py stop          # Node 봇 중단(같은 토큰이라 둘이 같이 뜨면 두 번 답함)
cp ~/projects/gaia-work/gaia-rl/lab/agentmaco/discord-agentmaco.service ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now discord-agentmaco
journalctl --user -u discord-agentmaco -n 3                        # "connected as …; channels [1554144240127442945]"
```

Codex 리뷰는 기본 `~/.codex` 로그인(gaia Codex 봇과 같은 것)을 쓴다. 되돌리기: `systemctl --user disable --now discord-agentmaco`
뒤 `cd ~/projects/multi-ai && python3 scripts/agent.py start`.

## 첫 TODO (새 봇에게 채널에서 시킴)

1. `.workflow/MASTER.md` 역할을 바꾼다(마스터 Fable, 작업자 Sonnet 서브에이전트, 리뷰어 Codex gpt-6-astra 읽기 전용; Sol·Codex 스레드 관련 문장 삭제)
   + `.workflow/STATUS.md` 색인 생성(30줄 이하: 열린 TODO 한 줄씩, 마지막 결정, 이어가는 법).
2. `scripts/workflow.py:170–177`의 Claude 리뷰 명령을 `codex exec --model gpt-6-astra --sandbox read-only -c approval_policy="never" --cd <inputs> --color never --output-last-message <파일> -`
   (프롬프트는 stdin)로 바꾸고 판정은 그 파일의 첫 줄에서 읽는다. VERDICT 검사·REJECT 횟수·반복 지적 중단(:185–208)은 그대로. `tests/test_workflow.py`의 가짜 CLI를 codex 인자에 맞춘다.
   이 TODO의 리뷰는 아직 옛 Claude 리뷰어가 한다(바꾸기 전이므로) — 그다음부터 Astra.
3. `bot/`·`scripts/agent.py`·`docs/DISCORD.md`를 "옛 Node 봇, 중단됨"으로 표시하고 이 폴더의 파일을 `multi-ai/bot/claude/`로 옮긴다(서비스·env 경로도 함께).

## 검증한 것 / 안 한 것

- 봇 코드의 env 분리(36674f5·d584932)는 gaia 봇 테스트 23+10으로 확인. 이 폴더의 JSON은 파싱 확인.
- 실제로 두 번째 서비스를 띄워 보지는 못함(토큰·env 파일은 사용자 몫). 첫 메시지 뒤 `journalctl --user -u discord-agentmaco -n 10`으로 확인.
