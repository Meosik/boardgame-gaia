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
| `install.sh` | 설치 스크립트(`set -e`): env 파일을 임시 파일에 모아 토큰 줄 1개를 확인하고 600으로 설치 → Node 봇 중단 → 서비스 등록·시작 → 로그 3줄. 한 단계라도 실패하면 거기서 멈춘다(코덱스 토론 10-31: 줄별 붙여넣기는 실패해도 다음 줄이 실행됨) |

허용 목록은 **직접 호출 제한**이다: `python3`·`node`·`scripts/*.sh` 안에서는 어떤 파일이든 읽고 지울 수 있다(코덱스 토론 10-31).
gaia 파일까지 보호하려면 별도 계정이나 파일시스템 격리가 필요하고, 그것은 사용자 결정.

## 설치 (사용자, 한 번)

```sh
cd ~/projects/gaia-work && git pull --rebase origin claude/epic-goodall-0ot55w
bash gaia-rl/lab/agentmaco/install.sh    # 마지막에 OK 가 나와야 한다; 중간에 멈추면 그 줄의 오류를 보고 다시 실행
```

Codex 리뷰는 기본 `~/.codex` 로그인(gaia Codex 봇과 같은 것)을 쓴다. 되돌리기: `systemctl --user disable --now discord-agentmaco`
뒤 `cd ~/projects/multi-ai && python3 scripts/agent.py start`.

## 첫 TODO (새 봇에게 채널에서 시킴)

1. `.workflow/MASTER.md` 역할을 바꾼다(마스터 Fable, 작업자 Sonnet 서브에이전트, 리뷰어 Codex gpt-6-astra 읽기 전용; Sol·Codex 스레드 관련 문장 삭제)
   + `.workflow/STATUS.md` 색인 생성(30줄 이하: 열린 TODO 한 줄씩, 마지막 결정, 이어가는 법).
   **리뷰 없음(설계상)**: `scripts/workflow.py:80–81`이 `.workflow/` 파일을 리뷰 diff에 넣지 못하게 막는다(리뷰 관리 파일의 자기 수정 방지).
   관리 문서 변경은 지금까지처럼 `review.sh` 없이 하되, 봇이 `git diff`를 디스코드에 보여 사용자가 승인한 뒤 커밋한다(코덱스 토론 10-31).
2. `scripts/workflow.py:170–177`의 Claude 리뷰 명령을 `codex exec --model gpt-6-astra --sandbox read-only -c approval_policy="never" --cd <inputs> --color never --output-last-message <파일> -`
   (프롬프트는 stdin)로 바꾸고 판정은 그 파일의 첫 줄에서 읽는다. VERDICT 검사·REJECT 횟수·반복 지적 중단(:185–208)은 그대로. `tests/test_workflow.py`의 가짜 CLI를 codex 인자에 맞춘다.
   **검수 순서**: `review.sh`는 바뀐 `workflow.py`를 실행하므로 그대로 두면 새 Codex 실행기가 자기 변경을 검수한다. 편집 **전에** `cp scripts/workflow.py scripts/workflow_prev.py`
   (같은 폴더라 `ROOT`가 같음, `workflow.py:16`; 커밋하지 않음)로 옛 실행기를 보존하고, 이 TODO만 `python3 scripts/workflow_prev.py review T-nnn`으로 옛 Claude 리뷰어가 검수한다.
   APPROVE 뒤 복사본은 사용자가 지운다(`rm`은 봇 거부 목록) — 그다음 TODO부터 Astra.
3. `bot/`·`scripts/agent.py`·`docs/DISCORD.md`를 "옛 Node 봇, 중단됨"으로 표시하고 이 폴더의 파일을 `multi-ai/bot/claude/`로 옮긴다(서비스·env 경로도 함께).

## 검증한 것 / 안 한 것

- 봇 코드의 env 분리(36674f5·d584932)는 gaia 봇 테스트 23+10으로 확인. 이 폴더의 JSON은 파싱 확인.
- 서비스 가동 확인(10-31 23:46, 사용자 설치 뒤): `journalctl --user -u discord-agentmaco`에 `connected as Agentmaco#4330; channels [1554144240127442945]; workdir ~/projects/multi-ai` — env 파일이 읽혔다는 뜻(토큰 줄 1개 확인, 값은 읽지 않음).
- 아직 확인 안 한 것(코덱스 토론 10-31): 토큰 절약 설정은 env·system.md에 준비만 됨 — `.workflow/STATUS.md`는 첫 TODO ①에서 만들어지기 전까지 없고(새 대화가 색인 없이 시작), 10턴 자르기·Sonnet 작업자·`!q`는 이 봇에서 한 번도 돌지 않았다. 첫 메시지 뒤 `journalctl --user -u discord-agentmaco -n 10`과 채널 답으로 확인. Node 봇 중단 여부도 미확인(답이 두 번 오면 `python3 scripts/agent.py stop`).
