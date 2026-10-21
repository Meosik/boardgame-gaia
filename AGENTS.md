# gaia — AGENTS.md (Codex CLI 지시; Claude Code는 CLAUDE.md를 읽는다. 둘은 같은 내용을 가리킨다)

이 저장소는 Gaia Project 보드게임 엔진(`gaia-engine`, Rust)·서버(`gaia-server`)·프런트(`gaia-frontend`)·AI 교사와 실험실(`gaia-rl`)이다.
Codex는 주로 **두 번째 의견**으로 호출된다: lab의 코드 검수(`review-code-*`)·A/B 설계 검수, 디스코드의 대화 검수와 `@Codex` 질문.
이때 저장소는 **읽기 전용**이다(`--sandbox read-only`): 파일을 고치지 말고 실험을 돌리지 마라. 반박·대안은 근거(파일:줄, 숫자, 명령)와 함께 쓴다.

## 규칙과 맥락이 있는 곳
- 실험실 규칙·현재 상태: `gaia-rl/lab/HANDOFF.md` — 6장(디스코드 세션 안전 규칙)이 최우선, 5장이 "진행 중", 5a가 최근 결정(E번호).
  옛 기록은 `gaia-rl/lab/HANDOFF-archive.md`(크다: 필요한 절만).
- 실험 결과: `gaia-rl/lab/results/<이름>.md`만 읽는다(`.json`은 수백 KB). 사이클 문서 `gaia-rl/research/strategy/cycles/`.
- A/B 판정은 1–3라운드 충전 수치(`charge_rounds.py`)로만 본다. 최종 VP는 참고.
- 룰북: `docs/EN_Gaia_rulebook_lo.pdf`, 확장(Lost Fleet) `docs/GP_Exp_Rule_EN_V1_Web.pdf`. 규칙 관련 코드 판단은 룰북을 근거로.

## 코드 탐색
- 저장소는 `codegraph init`으로 색인돼 있다(`.codegraph/`). 코드 질문은 `codegraph explore "<질문>"` → `codegraph node <심볼|파일>`,
  `codegraph callers|callees|impact <심볼>`, `codegraph query <검색어>` 순으로(grep·Read 연쇄 대신).
- `research/`·`lab/` 문서는 색인에 없다: `qmd search "<낱말>" -n 5`(BM25, 1초)로 찾고, 적중의 `:줄` 앵커로 `qmd get "qmd://lab/x.md:120:40"`을
  읽은 뒤 말한다. `qmd query`(확장·재순위)는 이 CPU에서 2분 넘게 걸리니 쓰지 않는다.

## 스킬 (Claude와 공유)
절차는 `gaia-rl/lab/skills/<이름>/SKILL.md`에 있고 `.agents/skills`(Codex)·`.claude/skills`(Claude)가 같은 폴더를 가리킨다:
`lab-review`(실험 결과 정리), `lab-queue`(큐 파일 작성), `explain`(수 하나 분석). 검수할 때는 해당 절차를 기준으로 본다.

## 출력
- 한국어, 휴대폰에서 읽을 길이. 비밀(.env 값, 토큰, 웹훅 URL)은 절대 출력하지 않는다.
- 반박도 다른 제안도 없으면 정확히 `결론: 이상 없음` 한 줄.
