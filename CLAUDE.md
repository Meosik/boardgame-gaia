@/home/sohegi/projects/multi-ai/CLAUDE.md

`/home/sohegi/projects/CLAUDE.md`의 AI-DLC 워크플로우를 그대로 따른다 (상위 디렉토리 CLAUDE.md로 이미 로드됨 — 중복 방지를 위해 본문을 여기서 재복사하지 않음).

## 코드 탐색은 codegraph부터 (2026-10-21)
이 저장소는 `codegraph init`으로 색인돼 있다(`.codegraph/`, 파일 감시로 자동 갱신, git 제외). 코드 질문은 grep·Read 연쇄 대신
`codegraph explore "<질문>"`(관련 소스·호출 경로·영향 범위를 한 번에) → `codegraph node <심볼|파일>`, `codegraph callers|callees|impact <심볼>`,
`codegraph query <검색어>` 순으로 쓴다. `research/`·`lab/` 문서는 색인에 없으니 Grep/Read로 본다.

## 룰북 참고 문서
- 기본 룰북: docs/EN_Gaia_rulebook_lo.pdf
- 확장팩 룰북 (Lost Fleet): docs/GP_Exp_Rule_EN_V1_Web.pdf

규칙 관련 코드 작성 시 반드시 룰북을 참조할 것.
