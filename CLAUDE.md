# gaia — CLAUDE.md (Claude Code 지시; Codex CLI는 같은 내용의 AGENTS.md를 읽는다)

Gaia Project 보드게임 엔진(`gaia-engine`, Rust)·서버(`gaia-server`)·프런트(`gaia-frontend`)·AI 교사와 실험실(`gaia-rl`).
(2026-10-22: 이전의 `multi-ai/CLAUDE.md` 가져오기와 AI-DLC 워크플로우는 폐기됨 — 사용자 확인.)

## 규칙과 맥락이 있는 곳
- 실험실 규칙·현재 상태: `gaia-rl/lab/HANDOFF.md` — 6장(디스코드 세션 안전 규칙)이 최우선, 5장 "진행 중", 5a 최근 결정(E번호).
  옛 기록은 `gaia-rl/lab/HANDOFF-archive.md`(크다: 필요한 절만 읽는다).
- 실험 결과는 `gaia-rl/lab/results/<이름>.md`만(`.json`은 수백 KB). 사이클 문서 `gaia-rl/research/strategy/cycles/`(형식 `TEMPLATE.md`).
- A/B 판정은 1–3라운드 충전 수치(`charge_rounds.py`)로만. 최종 VP는 참고.
- 절차 스킬: `gaia-rl/lab/skills/<이름>/SKILL.md` (`.claude/skills`·`.agents/skills`가 같은 폴더) — `lab-review`, `lab-queue`, `explain`.

## 코드 탐색은 codegraph부터 (2026-10-21)
이 저장소는 `codegraph init`으로 색인돼 있다(`.codegraph/`, 파일 감시로 자동 갱신, git 제외). 코드 질문은 grep·Read 연쇄 대신
`codegraph explore "<질문>"`(관련 소스·호출 경로·영향 범위를 한 번에) → `codegraph node <심볼|파일>`, `codegraph callers|callees|impact <심볼>`,
`codegraph query <검색어>` 순으로 쓴다. `research/`·`lab/` 문서는 색인에 없으니 `qmd search "<낱말>" -n 5`로 찾고 `qmd get`으로 해당 절을 읽는다
(`qmd query`는 이 CPU에서 2분 넘게 걸리니 봇 턴에서 쓰지 않는다).

## 룰북 참고 문서
- 기본 룰북: docs/EN_Gaia_rulebook_lo.pdf
- 확장팩 룰북 (Lost Fleet): docs/GP_Exp_Rule_EN_V1_Web.pdf

규칙 관련 코드 작성 시 반드시 룰북을 참조할 것. 비밀(.env 값, 토큰, 웹훅 URL)은 절대 출력하지 않는다.
