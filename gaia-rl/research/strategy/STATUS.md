# AI 구현·검증 상태

## 2026-09-28 승인 — 최신 교사 동일 조건 1판 재검증

- 사용자 선택 **1**: 최신 교사로 `shared-teacher-base-38` 1판만 새로 실행한다.
  좌석 Itars/Moweyds/Terrans/Ambas, 기술 계획 ON, 기준 엔진 ON, 기존 adaptive
  목표10초·좌석당120초 긴 탐색 최대6회 유지. 이전 대국 이어하기가 아닌 동일 초기 상태의 새 대국이다.
- 사전검사: native 초기 상태가 9월24일 기록과 정확히 일치하고 현재253개 소스/버전 가드 통과.
  이전 대국 파일 해시는 별도 보존했다. 기록: `runs/tech-plan-recheck-20260928-shared-38`,
  검사/로그: `runs/tech-plan-recheck-20260928-shared-38-evidence`.
- 완료 기준: 정상 종결, 독립 native 전수 재생·체크포인트 검사, 기술 취득→활용 및
  목표 연방 연결의 실제 관측과 계획 선택/예측을 분리한 보고. 1판으로 강도 개선을 판정하지 않는다.
- 새 학습·튜닝·추가 대국·모델 채택·서비스 변경·배포 없음. 기존 기록/동결A 보존.
  승인된 한 판 실행과 검증 전이며, 완료 결과는 아래에 별도 기록한다.

| 항목 | 상태 |
|---|---|
| 담당 | **Astra 구현 → Sol 독립 테스트**; 승인 과제만 인계 |
| 자동화 | `scripts/handoff_loop.sh --background`; 10초 확인, CLI 6회/8시간 제한, 연속 실패 2회 → human |
| 기준 엔진 | `GAIA_ENGINE_FIXES_2` **기본 ON**; 서순·12VP 토큰 수정 채택, 잘못 섞인 충전량 변경 제거 |
| 엔진 검증 | Rust workspace 596 통과/28 제외(DB·doc), xfail 두 건 정상 테스트 전환; lib/tests Clippy 통과 |
| 자동화 검증 | 모의 CLI 14/14, 두 역할 sandbox 경계 통과. Sol 서버 4+pilot 15=19/19, Python 핵심 19/19 통과 |
| 현재 과제 | **연방 준비·계획 검사 보완 완료**: 기존 목표는 자기 연방과 인접하여 새 연방 불가였음. 불가능 목표 취소 및 미래 목표를 막는 경로 제외; 사용 가능한 건물 파워만 보충. 시간·가격·기본 OFF 유지 |
| 환경 복구 | Sol 명령만 127.0.0.1 허용. 외부/사설망 직접접속·외부 프록시·외부 쓰기 차단 검증; Astra·전역 설정 유지 |
| 최신 전체 회귀 | **424건: 423 통과·기존 실패 1·오류 0**. 신규 연방 준비13건 포함 대상55건·Python 핵심19건 통과. 미구현 종족 조언 요구 실패는 유지; 전체 green 아님 |
| 평가 검증 | 불변식 944건: 928 통과·승인 예외 16·실패 0; Python 핵심 19 통과 |
| A + `(p)` | **판정 보류(4시드 잡음 범위)** −18.50; 기본 OFF, 재측정 승인 시 최소 12시드 |
| A + 원문 단가 | **판정 보류(4시드 잡음 범위)** −51.50; 기본 OFF, 재측정 승인 시 최소 12시드 |
| 과거 엔진 점수 | −8.25는 구분 한계 137.56 이내; 교정 전 충전량 오류가 섞인 결과이므로 새 엔진 점수로 사용 금지 |
| 기존 기보·재생 | 85개/14,789프레임 검증, 파일 변경 0. 관련 행동 재적용 44건 중 11건 변화(서순 9·불법 토큰 2); 양쪽 공통 QIC 오류 3건 별도 |
| 재생 영향 | 저장 화면/점수 유지. 새 엔진 재계산은 달라질 수 있음; 전판 재시뮬레이션 미실행, 과거 버전 재계산은 버전 가드로 차단 |
| 동결·경계 | A·기존 평가/가격 유지. 이번 기능 시험 1판만 승인; B 튜닝·(r) 수정/A/B/(e′)/학습·재측정 보류 |

<!-- HANDOFF LOOP START -->

## Handoff 자동화

| 상태 | CLI 실행 | 연속 실패 | PID | 갱신(UTC) |
|---|---:|---:|---:|---|
| 자동 중단: 실행 횟수 또는 시간 한도 | 1/6 | 0/2 | 2747568 | 2026-09-24T08:10:35+00:00 |

<!-- HANDOFF LOOP END -->

## Astra — fix-missing-faction-guidance-20260923 (2026-09-23)

- 상태: **human — 신규 전략 결정 필요**. 승인 과제의 오류 재현·원인 확인까지 완료; 구현·테스트 기대값은 변경하지 않았다.
- 재현: `cd gaia-rl && GAIA_ENGINE_FIXES_2=1 PYTHONPATH=python:experiments .venv/bin/python -m unittest faction_teachers.test_guidance -v` → exit 1, `ModuleNotFoundError: No module named 'faction_teachers.guidance'` (수집 오류 1건, 실제 7개 테스트 미실행). 최신 Sol 결과 `handoff/logs/20260923T064038022002Z-02-sol.result.json`의 bwrap 장애와 달리 이번에는 Python 테스트 수집까지 실행됐다.
- 원인 근거: `test_guidance.py`는 `bc6f612`에서 추가됐으나 `git log --all --name-status -- ':(glob)**/guidance.py'`에는 구현 이력이 없다. `teacher-application.md` §3–4와 기존 계획 `gaia-rl-training-evaluation.md`의 2026-09-15 기록도 미구현 모듈을 참조하는 테스트 초안임을 명시한다. 이동된 기존 함수로 연결할 대상은 확인되지 않았다.
- 범위 경계: 기존 `faction_teachers/paths.py`는 건물·능력 수순이며 `advice_goals`의 대체 구현이 아니다. `four_factions/preparation.py`에는 표준 `technology` 목표 처리가 없고, 중첩 득점 연결·ordered 후속 연구 연결도 빠져 있다. 테스트는 기본 14종족 모두의 기술/연구 조언을 요구하지만 문서의 정성적 대안만으로 각 목표 단계·적용 조건을 확정할 수 없다. 단순 import 복구를 넘어 이를 임의 결정하지 않았다.
- 확인 질문: `teacher-application.md` §3의 기본 14종족 조언에 대해 목표 단계·적용 조건을 정하는 설계 재량과 필요한 공통 탐색 연결의 신규 구현까지 승인할까요? 새 튜닝·대국 실험은 포함하지 않는다.
- 검증: 조사 후 `git diff --check` 통과. 동결 A `baseline-teacher-20260917/`의 추적 파일 195개는 `git diff HEAD --name-only` 기준 변경 없음. 전체 experiments/Python 회귀·엔진/평가 게이트는 이번에 실행하지 않았으며 통과로 주장하지 않는다.
- 이번 수정 파일: 이 문서의 Astra 구역만. QUEUE/감독 상태/HANDOFF LOOP 자동 관리 구역·엔진·동결 A·기보·재생은 수정하지 않았다.

## 테란·앰바스 pilot — 한도 체크포인트 (2026-09-24)

- 승인 범위: 자료 대조→명세→기존 종족별 실험 AI의 독립 OFF 기능 구현→Sol 검증. 동결 A·서비스 AI·평가/자원 단가 불변.
- Astra 4번째 호출은 전략 주장 DB/출처 기록, 기존 계획·기술 취득·네이티브 효과·worker/기록 연결을 조사했다. 해당 호출의 최종 결과 JSON은 없으며 조사 이후 구현 완료 증거도 없다.
- 최초 자동화 시작부터 대기 포함 8시간 기한이 지나 감독 프로세스가 중단했다. 사용 횟수 4/6, 현재 실행 프로세스 없음. 기한 연장·자동 초기화 없음.
- 신규 계획/구현 파일 변경 없음. Sol 검증 미실행. 승인 과제 전체와 조사 로그는 handoff/QUEUE.md 및 handoff/logs/20260923T085811115905Z-04-astra.log에 보존되어 있다.
- 재개에는 새 제한 세션 승인이 필요하다. 미완료 작업을 완료라고 보고하지 않는다.

### 2026-09-24 재개 승인

- 사용자가 동일 과제의 새 6회/8시간 사이클 재개를 승인했다. 이전 세션 상태와 로그를 보존하고 새 감독 세션을 시작한다.
- 이전 한도 체크포인트는 역사 기록이며 현재는 승인 범위 작업 재개 상태다. 구현 완료·검증 통과를 뜻하지 않는다.

## Astra — faction-tech-pilot-terrans-ambas-20260923 (2026-09-24)

- 상태: **pass — 승인 구현·대상 테스트 완료, Sol 독립 검증 대기**. 새 대국/튜닝이나 나머지 종족 구현은 하지 않았다. 최신 Sol의 `20260923T064038022002Z-02-sol.result.json` 실패는 복구 전 bwrap 오류였으며 이번 native 테스트는 정상 실행됐다.
- 명세: `teacher-application.md`의 2026-09-24 절에 B04/B06 원본 부재, 보존 요약/CSV B4-01·B4-03·A01·A02의 근거 범위, 실제 기술10/8/6 효과·취득 경로·비용·취소 조건을 기록했다. 연구 단계/라운드 우선순위/평가 계수는 추가하지 않았다.
- 구현: SharedTeacher의 `GAIA_FACTION_TECH_PLANS=1`(기본 OFF), 테란 기술10→8→표적 개척, 앰바스 기술6→의회→지정 광산 이동→해당 자리 연방 후보. 표준 기술 취득/준비, 고정·자유 연구 진보, 중첩 득점 연결, 품절/가림/표적 상실 취소, worker·캐시·감사·기록·체크포인트 전달을 연결했다. 기존 체크포인트의 필드 부재는 OFF이며 재개는 저장 설정을 유지한다.
- 변경 파일(9): `experiments/faction_teachers/{guidance.py,test_tech_pilot.py,teacher.py,__main__.py,continuation.py}`, `experiments/four_factions/{preparation.py,timed.py}`, `research/strategy/{teacher-application.md,STATUS.md}` (모두 `gaia-rl/` 아래).
- 대상 테스트: `cd gaia-rl && GAIA_ENGINE_FIXES_2=1 PYTHONPATH=python:experiments .venv/bin/python -m unittest faction_teachers.test_tech_pilot -v` → **15/15 통과**, 9.489초. 로그 `/tmp/gaia-astra-pilot-final-targeted.log`. 테란 기술10·앰바스 기술6 실제 유료 취득, 자원/선행 부족, 부모 불변, 비대상 종족, 표적 상실, 중첩 목표, 저장/재개, deadline, 실제 SharedTeacher→worker 계획 평가 연결을 검사했다.
- 기존 회귀: 같은 환경으로 `-m unittest faction_teachers.test_continuation faction_teachers.test_paths four_factions.test_preparation four_factions.test_source_paths four_factions.test_preparation_cache four_factions.test_provenance -v` → **39/39 통과**, 114.490초(`/tmp/gaia-astra-pilot-regression.log`); `-m unittest four_factions.test_outcomes -v` → **3/3 통과**. 최초 묶음 실행의 새 테스트 오류(필수 정책 이름 누락), 후속 JSON tuple/list 준비 데이터 불일치는 테스트 fixture를 실제 기록 형식으로 교정했고 위 최종 대상 테스트로 재확인했다. 기존 테스트 기대값/skip은 변경하지 않았다.
- 원래 초안: 같은 환경으로 `-m unittest faction_teachers.test_guidance -v` → **7개 실행, 6 통과·1 실패(exit 1)**. `test_every_original_faction_has_technology_or_track_advice`가 14종족 모두를 요구하여 실패(최종 실행 첫 미지원 종족 Gleens). QUEUE에 명시된 범위 밖 잔여이며 삭제/skip/12종족 임의 구현 없음. 로그 `/tmp/gaia-astra-guidance-original.log`. **전체 green 아님.**
- OFF 추가 대조: 변경 전 HEAD의 preparation 모듈과 현재 OFF를 동일 native fixture에서 비교했다. 순위·메모리, 135개 목표, 전체 후보 predicate, 득점 연결, 첫 계획 선택 및 부모 snapshot 동일. 정적 AST와 `git diff --check` 통과. 동결 A `FROZEN.json` 200개 파일 해시 모두 일치(누락/불일치 0), 추적 diff 없음. 엔진 파일·QUEUE는 시작 시점 해시와 동일; 평가/기보/재생/감독 상태/자동 관리 구역은 수정하지 않았다.
- 검증 한계: worker 연결 테스트는 **한 수 종료 조건을 주입**해 실제 native fork·비용·기존 leaf 평가까지 검사했다. 새 두 기술/이동 연계의 두 수입 경계 전체 달성이나 점수 향상 입증은 아니다. 변경 없는 production horizon의 단일 결정 probe(15초 목표/18초 상한)는 17.644초에 정상 baseline 반환, 완성된 비교 0개였다. 탐색 미완료를 성공/열등 판정으로 바꾸지 않았다. 전체 experiments/Python·Rust·Clippy·불변식 게이트는 이번에 실행하지 않았으며 이전 증거만 유지한다. Sol은 QUEUE의 전체 독립 검증을 수행해야 한다.

### Astra — Sol 실패 인계 확인 (2026-09-24)

- 현재 상태: **gate_failed — 로컬 소켓 환경 게이트 재현**. 위 Astra pass는 Sol 검증 전 기록이다. 최신 Sol 결과 `handoff/logs/20260923T214549007001Z-02-sol.result.json`과 `/tmp/gaia-sol-experiments.log`의 실패 증거를 확인했다. pilot 15/15·Python 핵심 19/19 통과는 기존 Sol 증거이며 이번에 재실행하지 않았다.
- 이번 대상 재현: `cd gaia-rl && GAIA_ENGINE_FIXES_2=1 PYTHONPATH=python:experiments .venv/bin/python -m unittest coaching.test_server -v` → **4개 실행·오류 4, exit 1**, 0.094초. 모두 `coaching/test_server.py:20`의 `setUp`에서 `ThreadingHTTPServer(('127.0.0.1', 0), ...)`가 소켓을 생성할 때 `PermissionError: [Errno 1] Operation not permitted`로 중단했다. 테스트 본문 실행 전 환경 오류이며 승인 pilot의 구현 결함 증거는 아니다.
- 제품 코드·테스트 수정 없음. 사용자 지시상 권한 변경은 금지되어 있으며 테스트 삭제/skip/mock으로 이 게이트를 우회하지 않았다. 로컬 소켓이 허용된 검증 환경에서 Sol의 전체 experiments 명령을 다시 실행해야 한다. 14종족 조언 요구의 범위 밖 잔여는 그대로 유지한다.
- 이번 변경은 `STATUS.md`의 Astra 구역뿐이다. 전체 experiments·엔진·Clippy·불변식은 재실행하지 않았으며 통과로 주장하지 않는다. QUEUE/감독 상태/HANDOFF LOOP 자동 관리 구역·동결 A·기보·재생은 수정하지 않았다.

## Sol 독립 검증 — faction-tech-pilot-terrans-ambas-20260923 (2026-09-24)

- 상태: **gate_failed**. 승인 pilot 전용 테스트는 통과했지만, QUEUE가 요구한 전체 experiments 회귀가 실패했다. 제품 코드·테스트·기대값·권한은 수정하지 않았다. 이번 Sol 수정 파일은 `STATUS.md`뿐이다.
- 대상: `cd gaia-rl && GAIA_ENGINE_FIXES_2=1 PYTHONPATH=python:experiments .venv/bin/python -m unittest faction_teachers.test_tech_pilot -v` → **15/15 통과**. 독립 재현에서 OFF/비대상 경계, native 유료 기술 취득, 부모 상태·시간 제한, 저장/재개, worker 평가 연결을 확인했다. worker 테스트의 한 수 종료 조건과 실제 장기 탐색/점수 향상 미검증 한계는 Astra 기록과 같다.
- 기존 초안: 같은 환경에서 `-m unittest faction_teachers.test_guidance -v` → **7개 중 6 통과·1 실패**. `test_every_original_faction_has_technology_or_track_advice`가 미승인 14종족 전체 조언을 요구하며 이번 단독 실행의 첫 미지원 종족은 Geodens였다. Astra 실행에서는 Gleens, 전체 discover에서는 HadschHallas가 처음 나왔다. 테스트 자체는 변경되지 않은 **기존 범위 밖 잔여**다.
- 전체 experiments 재현: `cd gaia-rl && GAIA_ENGINE_FIXES_2=1 PYTHONPATH=python:experiments .venv/bin/python -m unittest discover -s experiments -v` → **384개, 실패 1·오류 4, exit 1**. 실패 1개는 위의 기존 초안. 추가 오류 4개는 `coaching.test_server.ServerTests`의 네 테스트가 `setUp`에서 `ThreadingHTTPServer(('127.0.0.1', 0), ...)` 소켓 생성 시 `PermissionError: [Errno 1] Operation not permitted`로 중단한 것이다. 테스트 본문 이전의 **이번 전체 실행에서 새로 관측된 환경 게이트**이며 해당 서버/테스트 파일은 Astra diff에 없다. 로그: `/tmp/gaia-sol-experiments.log`. 로컬 소켓 허용 환경에서 동일 명령 재검증이 필요하다. 권한 변경이나 테스트 약화는 하지 않았다.
- Python 핵심: `cd gaia-rl && GAIA_ENGINE_FIXES_2=1 PYTHONPATH=python .venv/bin/python -m unittest discover -s python/tests -v` → **19/19 통과**, 로그 `/tmp/gaia-sol-python.log`.
- 정적·불변 경계: pilot 관련 Python 7개 파일 AST 파싱과 `git diff --check` 통과. 동결 A `FROZEN.json`의 **200개 파일 해시 일치, 누락/불일치 0**. `test_guidance.py`·`coaching/test_server.py`의 HEAD diff 없음. 기존 엔진/평가 변경은 Sol 시작 시 이미 작업 트리에 있었고 이번 검증 중 수정하지 않았다. 기존 기보·재생 및 HANDOFF LOOP 자동 관리 구역도 수정하지 않았다. 엔진 전체·Clippy·불변식 게이트는 이번 Sol 단계에서 실행하지 않았으며 이전 증거만 유효하다.
- Astra/감독 인계: pilot 전용 기능 실패는 확인되지 않았다. 소켓 제한 해소 후 전체 experiments를 재실행하여 14종족 범위 밖 잔여 외 오류가 남는지 확인해야 한다. QUEUE `next`·감독 상태는 Sol이 변경하지 않는다.

## Sol 재검증 — 로컬 통신 복구 후 (2026-09-24)

- 상태: **human — 이번 승인 검증 완료**. 이전 소켓 오류 4건은 재발하지 않았다. 전체 experiments는 기존 14종족 조언 초안 실패 1건 때문에 green이 아니다. 새 pilot 실패나 새 오류는 관측되지 않았다.
- 대상: `cd gaia-rl && GAIA_ENGINE_FIXES_2=1 PYTHONPATH=python:experiments .venv/bin/python -m unittest coaching.test_server faction_teachers.test_tech_pilot -v` → **19/19 통과**, exit 0. 로컬 서버 4건과 pilot 15건. 로그 `handoff/logs/20260924-sol-recheck-targeted.log`.
- 전체 experiments: 같은 cwd/환경에서 `.venv/bin/python -m unittest discover -s experiments -v` → **384건 중 383 통과·실패 1·오류 0**, exit 1. `faction_teachers.test_guidance.GuidanceTests.test_every_original_faction_has_technology_or_track_advice`가 `Xenos`의 조언 부재로 실패했다. 기존 초안은 승인된 테란·앰바스 2종족 밖의 기본 14종족 모두를 요구한다. 로그 `handoff/logs/20260924-sol-recheck-experiments.log`. 기존 실패로 분리하며 기대값·skip·제품 코드를 변경하지 않았다.
- Python 핵심: `cd gaia-rl && GAIA_ENGINE_FIXES_2=1 PYTHONPATH=python .venv/bin/python -m unittest discover -s python/tests -v` → **19/19 통과**, exit 0. 로그 `handoff/logs/20260924-sol-recheck-python.log`.
- 정적·불변 경계: `git diff --check` 통과. 동결 A `FROZEN.json`의 200개 파일 중 누락 0·해시 불일치 0; 동결 A·기존 재생의 추적 diff 없음. 이번 Sol의 제품 코드·테스트·기대값·권한 변경 없음. 엔진 전체·Clippy·평가 불변식은 이번 단계에서 실행하지 않았다. 기존 결과만 위 표에 남긴다. `QUEUE.md`의 `next`·감독 상태·HANDOFF LOOP 자동 관리 구역은 수정하지 않았다.

### 로컬 통신 복구 변경·검증 근거

- 변경: `scripts/handoff_loop.py`의 Sol 전용 네트워크 설정, `scripts/test_handoff_loop.py` 회귀, 새 `scripts/check_handoff_sandbox.py` 실제 경계 검사, `handoff/README.md`·`handoff/sandbox-validation.json`·QUEUE 및 이 상태 기록. 제품/테스트 기대값/전역 Codex/AppArmor 설정은 이번 복구에서 변경하지 않았다.
- 검증 결과 JSON: `handoff/sandbox-validation.json`. stdout/stderr 및 독립 검증 원본은 `handoff/logs/20260924-sol-*`. 기존 한도·실패 이력을 초기화하지 않고 4번째 호출로 Sol 재검증을 마쳤다. 이번 human은 장애가 아니라 **승인 범위 검증 종료**를 뜻한다.

## 기술 계획 ON 시험 대국 1판 — 2026-09-24 승인

- seed `shared-teacher-base-38`, 순서 Itars/Moweyds/Terrans/Ambas. 기존 seed 계열에서 두 대상 종족이 함께 나오는 첫 시드이며 점수 결과를 보고 선택하지 않았다.
- 기존 승인 adaptive clock(기본10초, 좌석당 120초 긴 탐색 최대6회), 기존 평가·생산 horizon 그대로. 실행 프로세스에만 계획/엔진 플래그 ON.
- 새 승인 과제의 별도 8시간·Sol1회 한도. 기록 경로 `gaia-rl/runs/tech-plan-pilot-20260924-shared-38`. 실제 취득→활용과 계획 선택 근거를 구분하며, 단독1판의 점수 우열·실력 향상은 판정하지 않는다.

## Sol 완료 — 기술 계획 ON 시험 대국 1판 (2026-09-24)

| 항목 | 이번 판에서 확인한 결과 |
|---|---|
| 고정 조건·종결 | seed `shared-teacher-base-38`, 좌석 Itars/Moweyds/Terrans/Ambas, 엔진·pilot ON, adaptive clock 목표10초·긴 탐색 최대120초/좌석6회. 정상 종료 144수, 6라운드 |
| pilot 계획 | 테란 평가 후보 14·완성된 horizon 비교 14, 앰바스 9·9. 두 종족 모두 예측 목표 달성 0, 실제 pilot 선택 0, 평가 후보 취소 0. 미탐색 슬롯은 다른 목표까지 포함하므로 pilot 불가능/열등으로 판정하지 않음 |
| 실제 연계 | 테란 기술10/8 미취득; 초차원 포밍 2회, 가이아 광산 건설·기술8 득점 미관측. 앰바스 기술6·의회 건설·의회 이동 미관측; 1회 연방은 별도 기본 경로 선택. 기술 취득 비용과 목표 효과는 이번 판에서 측정 불가 |
| 최종 관측치 | 최종 점수 Itars 107 / Moweyds 62 / Terrans 82 / Ambas 83. 건물·연방·기술·연구·fallback·결정 시간·비교 수는 `cycles/010-tech-plan-pilot-1game.json`에 종족별 기록. 단독 1판 점수 우열 판정 없음 |
| 독립 검증 | `GAIA_ENGINE_FIXES_2=1`로 144수 네이티브 재생, 행동·전후 상태 해시·감사 행·최종 상태/점수·체크포인트·소스/버전 가드 일치. `git diff --check` 통과, 동결 A 200개 해시 일치. 기존 기보/재생 변경 없음 |
| 경계 | 새 대국·튜닝·학습·배포·push 없음. 전체 엔진/Clippy/Python/불변식 게이트는 이번 1판 단계에서 재실행하지 않았음. 승인 과제 종료, 후속 결정은 사람 대기 |

상세 근거: `gaia-rl/research/strategy/cycles/010-tech-plan-pilot-1game.json`. 원시 기록: `gaia-rl/runs/tech-plan-pilot-20260924-shared-38`; 실행 로그: `handoff/logs/20260924-tech-plan-pilot-shared-38-run.log`.

## 2026-09-24 후속 — 계획 결과 집계 교정

- 승인 실행 범위 중 명확한 집계 오류를 수정했다. 최초 `goal_spec.payoff`가 아니라
  탐색 후 `remaining_goal.payoff`로 취소를 센다. 과거 임시 분석기의 취소 0건은 잘못이며,
  `cycles/010-tech-plan-pilot-1game.json`에 앰바스 취소 3건과 정정 이력을 기록했다.
- `tools/audit_tech_plan_outcomes.py`는 저장 감사 JSONL만 읽는다. 비교 완료/목표 달성/
  계획 취소/미확인을 분리하고, BGG 선택 이름과 실제 행동 인덱스를 함께 확인한다.
  원시 기록 23건과 체크인한 필드 발췌 fixture의 집계 일치·원본 SHA-256 불변 확인.
- 검증: 회귀 5건 통과. 테란 비교14/목표완료0/취소0, 앰바스 비교9/목표완료0/취소3.
  이 테스트는 저장 결과 집계 검증이며, 계획 실행 성공 또는 AI 실력 향상 증거가 아니다.
- 실행: `python3 gaia-rl/tools/audit_tech_plan_outcomes.py gaia-rl/runs/tech-plan-pilot-20260924-shared-38/teacher-audit.jsonl`
- 미정: 기존 승인 사양은 계획이 막히면 일반 대안으로 복귀한다. 계획 보존 경로와
  기존 포기 경로를 둘 다 비교하는 확장은 제안 상태이며 사용자 답변 전 구현하지 않는다.
  자원 가격·horizon·플래그 기본값·A·엔진·원시 기보 변경 및 새 대국/외부 AI 호출 없음.

## 2026-09-24 후속 승인 — 보존/기존 두 경로 비교

위 미정 사항은 사용자의 **두 경로 비교 승인**으로 해소됐다. 기본 OFF인
`GAIA_FACTION_TECH_PLANS=1` 범위에서만 보존 대안을 추가했다. 일반 경로는 그대로
남고, 같은 평가 기준에서 더 나을 때만 보존 대안이 선택된다. 실제 게임의 합법 행동을
막거나 계획 실행을 강제하지 않는다. 가격·horizon·시간 상한·다른 종족·A/엔진은 유지.

| 저장 상태의 native 분기 비교 | 기존 경로 | 보존 경로 |
|---|---:|---:|
| 동일 종료 경계 | R5 행동 단계 | R5 행동 단계 |
| 기존 leaf 평가값(최종 점수 아님) | 135.1733 | 142.5500 |
| 계획 취소 | 이동 광산을 먼저 연방에 넣어 취소 | 취소 없음 |
| 의회 건설 / 지정 광산으로 이동 | 없음 / 없음 | 실행 / 실행 |
| 목표 위치를 포함한 연방 | 미완료 | 미완료 |
| 분기 계산 시간(각 최대60초 진단) | 22.17초 | 30.94초 |

- 저장 대국 67수에서 기존 continuation으로 재현한 분기 77수 상태를 native prefix와
  정규화 상태 해시로 고정했다. 실제 대국에서 선택된 77수라는 뜻은 아니다.
- 첫 시도는 보존 경로가 60초 만료였다. 향후 이동 광산을 포함하는 동등한 연방 변형
  18개를 함께 제외하고 실제 검색과 같은 캐시를 적용한 뒤, 같은 60초 한도에서 양쪽 완료.
  첫 실패 기록은 보존하며, 실패를 열등 평가로 바꾸지 않았다.
- 최신 근거: `cycles/011-plan-preservation-comparison-verified.json` (시작/종료 소스 해시
  동일, native root 불변). `tools/compare_plan_preservation.py`로 짧은 분기만 재현 가능.
- 검증 완료: 신규12건 통과, 기존 관련58건 통과(신규11건 포함, 이후 오류 은폐 방지1건 추가).
  전체 experiments **396건 중395 통과·기존 실패1·오류0**, Python 핵심19건 통과,
  저장 집계5건·py_compile·diff 검사 통과. 동결 A 200개 해시 불일치0, 원시 감사 로그 불변.
  실패는 `test_every_original_faction_has_technology_or_track_advice`이며 미구현 종족
  조언을 요구한다. 테스트를 삭제/완화하지 않았다. Rust/Clippy/944불변식은 이번에 재실행하지 않았다.
  명령·로그·변경 파일: `cycles/011-plan-preservation-validation.json`.
- 한계: 이 위치의 계획 진행 개선만 확인했다. 실제 전체 검색에서의 선택 빈도/승률/
  마지막 목표 연방 성공은 미검증이다. 후보 추가로 같은 시간 내 미탐색 후보가 늘 수 있다.
  새 전판·학습·배포·A/B·튜닝·추가 종족 확대는 하지 않았다.

## 2026-09-24 후속 진단 — 마지막 연방과 실제 검색 경로

| 확인 항목 | 저장 native 분기의 결과 |
|---|---|
| 연방 준비 | 의회 이동 후 다음 자기 결정(분기99수/R4): 미편입 의회4 + 연구소2 = **6**, 필요7. 합법 연방0, 목표 연방0, 연방 후보 생성 제한 적중0 |
| 당시 자원/건설 | 광석0·크레딧7·QIC0·파워III 0. 일반 `Build` 후보0. 장기적으로 불가능하다는 뜻은 아님 |
| 예측 경계 | R5 수입에서 광석4로 회복하지만 기존 비교는 R5 행동 단계 진입 시 끝난다. 마지막 연방의 R5 이후 달성 여부는 미평가 |
| 전체 검색 | 같은 시작 상태(분기77수), 승인된 adaptive 10/120초·6회. 원 기록67수까지의 지출을 이어받으면 앰바스 긴 탐색 잔여0 → 실제 상한10초 |
| worker 관측 | 보존 후보2개와 기존 후보2개 생성. `current-choice`만 비교 시작, 완료0. 보존 비교 시작0. 약9.91초 후 `local-baseline` 연방 선택; **quick fallback 아님** |
| 판정 범위 | 계획에 연방 파워 보충 건설 단계가 없고, 이 상태의 검색에서는 기준 경로 계산이 대안 평가를 막는다. 모든 종족/상태에 일반화하지 않는다 |

- `tools/diagnose_plan_completion.py`로 기존 보존 분기를 재현해 행동·평가·남은 계획·종료
  상태가 이전 receipt와 일치함을 확인했다. 이어 실제 `SharedTeacher` worker 한 결정을
  관측했다. 후보/점수/시간 정책은 바꾸지 않았고, worker의 생성·비교 시작/완료만 기록했다.
- 전체 검색의 계획/변환 증명 메모리는 기존 단독 분기 비교와 같이 비워 두었다. 시계만
  원 기록67수까지 계승했으며, 과거 실제 controller 메모리 전체를 복원한 재생은 아니다.
  분기77/99수는 가상 continuation의 수 번호이지 원 대국의 같은 번호 행동이 아니다.
- 근거: `cycles/012-plan-completion-diagnosis.json`. 진단 도구5건·native 관측 assertion·
  py_compile·diff 검사 통과. 원시 감사 로그 SHA-256 불변. 전체396건/Rust/불변식은 재실행하지 않았다.
- 다음 수정은 아직 미승인: 연방 파워를 보충하는 건설 준비 경로, 그리고 같은 제한 시간 안에
  대안끼리 공정하게 비교할 검색 방식. 보너스 점수/연방 강제/시간 증가/새 대국은 적용하지 않았다.


## 2026-09-24 후속 승인 — 같은 깊이의 단계별 검색

| 저장 분기77수·동일 10초 한도 | 이전 전체 검색(012) | 단계별 검색(013) |
|---|---:|---:|
| 완료된 경로 비교 | 0 | 깊이1: 115 / 깊이2: 115 / 깊이4: 3 |
| 핵심 기존/보존 대안 | 생성4·시작0 | 깊이1·2에서 모두 완료 |
| 마지막 게시된 비교 깊이 | 없음 | native 전이4개 상한 |
| 실제 선택 | 기존 일수 평가의 연방 | 같은 연방 |
| 계산 시간 | 약9.91초 | 9.919초 |
| 긴 탐색 잔여 / quick fallback | 0 / 미사용 | 0 / 미사용 |

- 승인 구현: pilot ON 테란·앰바스에서만 native 전이 1→2→4→8→…→128→기존 두 수입
  경계로 심화한다. 최초에는 기준/기존/보존을 먼저 비교하고, 이후에는 직전 선택·기준과
  유망 경로 순으로 평가한다. 후보를 삭제하거나 미탐색을 열등으로 바꾸지 않는다.
- 새 깊이의 **기준과 직전 선택 경로가 모두 완료된 뒤에만** 그 깊이 결과로 교체한다.
  중단/불완료 시 직전 동일 깊이의 결과를 유지한다. 선택·BGG·시간 배분에는 게시된 깊이의
  값만 사용하고 다른 깊이 기록은 별도 보존한다. 실제 선택된 BGG 경로의 계획을 기억한다.
- 가격/leaf 평가/자원 보존/총 시간/긴 탐색 횟수/기본 OFF/다른 종족/A/엔진은 유지했다.
  시간 증가·가산점·계획 강제·새 전판·외부 AI 호출·배포는 하지 않았다.
- native 근거: `cycles/013-progressive-search-probe.json`, 재현 도구
  `tools/probe_progressive_search.py`. 012와 동일한 고정 root 및67수까지 지출한 시계,
  계획·변환 메모리 없는 격리 설정을 사용했다. 원시 대국의 정확한 controller 재생이 아니다.
  시작/종료 소스 해시와 부모 native 상태가 동일하다. 관측 로그 비용도10초 안에 포함했다.
- **강도 개선 입증 아님**: 깊이1·2에서 대상 보존 경로152.22, 기존157.92로 기존이 높았다.
  서로 다른 깊이 또는 이전 두 수입 경계 값135.17/142.55와 섞어 승패를 판정하지 않는다.
  깊이4에서도 기준 연방 선택을 유지했다. 마지막 연방 파워6→7 건설 준비는 아직 미구현이다.
- 검증 완료: 대상55건(신규15건 포함) 통과, 전체 experiments **411건 중410 통과·기존 실패1·오류0**,
  Python 핵심19건 통과. 추가 합성 BGG 선택/메모리 대조2건, py_compile·diff 검사 통과.
  기존 실패는 14종족 모두의 기술/연구 조언 요구이며 삭제/완화하지 않았다.
  동결 A 200파일 해시 불일치0, native probe의251소스 해시 일치, 원시 대국 감사 로그 불변.
  Rust/Clippy/944불변식은 재실행하지 않았다. 파일·명령·로그는
  `cycles/013-progressive-search-validation.json`에 기록했다.

## 2026-09-25 — 연방 건설 준비와 목표 적법성 보완

| 항목 | 확인 결과 |
|---|---|
| 파워 준비 | pilot ON 앰바스 보존 경로에 유료 건설/업그레이드 및 최대32개 자금조달 미리보기 연결. 기존 평가·보존 제약·시간·기본 OFF 유지 |
| 추가 누락 수정 | 목표 `3,-2`는 기존 자기 연방 `2,-2`, `3,-3`과 인접하여 새 연방 불가. 기존 취소/복귀 계약에 이 native 조건을 반영하고, 보존 경로가 자기 행동으로 미래 목표를 막는 것도 제외 |
| 기존 진단 정정 | ‘미편입 파워6’은 사실이나 그중 의회4는 인접 제한으로 새 연방에 쓸 수 없었음. 실제 사용 가능한 건물 파워는2. 따라서 단순6→7 문제만은 아니었음 |
| 건설 기능 검사 | 같은 native R5 보드에 **별도로 지정한 합법 목표**에서 파워4 지불→광석2→유료 아카데미를 확인. 사용 가능한 파워2→4(전체 미편입6→8). 이는 실제 과거 pilot 목표 달성이나 자원 조작 사례가 아님 |
| 원래 분기77수 재비교 | 기존135.1733 / 보존133.4100, 양쪽 같은R5 경계 완료. **목표 연방은 양쪽 미완료**. 기존 경로는 계획 취소, 보존 경로는 불가능한 인접 연방을 피했으나 PI/이동/연방까지 못 감. 값은 leaf 평가이며 실제 대국 점수 아님 |
| 실제 worker 연결 | 긴 탐색 잔여0 유지, 9.922초. 깊이1·2 각각115개, 깊이4는34개 완료. 기존 연방 선택 유지·quick fallback 미사용. 깊이4 증가를 재현된 속도 향상으로 일반화하지 않음 |
| 판정 | 기능 및 누락된 적법성 검사 보완. **연방 완성·승률 향상 입증 아님**. 불가능한 계획을 유망한 경로로 보고하지 않음 |

- 근거: `cycles/014-target-legality.json`, `014-federation-preparation-comparison.json`,
  `014-progressive-integration.json`. 동일 native root/시작·종료 소스 해시 불변.
  기존 R5 기보는 수정하지 않고, 문제가 생기기 전 분기77수로 돌아가 새 코드를 비교했다.
- 초기 `014-federation-preparation-initial-comparison.json`의 R5→종료87/100 결과는
  **적법성 누락 발견 전 시도**로 보존한다. 최종 코드의 성능/성공 증거로 사용하지 않는다.
- 회귀: 신규13건 포함 대상55건 통과. 최초 새 테스트의 파워 소비 기대값3은 native
  `power_action_cost(3)=4`를 확인해 교정했고, 업그레이드 직후에는 상대 충전 단계임을
  실제 native 응답으로 처리했다. 기존 테스트를 삭제/완화하지 않았다. 최종 전체 회귀는 **424건 중423 통과·기존 실패1·오류0**,
  Python 핵심19건 통과, py_compile·diff 검사 통과. 동결A 200파일·원시 대국 감사 로그 불변,
  최종 native 비교/worker receipt의253소스 해시가 현재 코드와 일치한다. Rust/Clippy/
  944불변식은 재실행하지 않았다. 파일·명령·로그: `cycles/014-federation-preparation-validation.json`.
- 이번 수정은 teacher 계획층/검증 도구/기록에 한정한다. 엔진·가격·동결A·원 기보·배포·
  외부 AI·새 전판/A/B/학습 실험·나머지 종족 확대는 변경/실행하지 않았다.

## 2026-09-28 — A02 라운드 투자 비교 (격리·기본 OFF)

- 승인 범위 구현: 횟수 제한/소비 강제 없이 합법 건설·업그레이드 연속 경로를 즉시 패스와
  같은 다음 라운드 시작 경계에서 비교. 원래 평가·가격·시간과 동결 A는 유지했다.
  도구4개와 별도 파생 소스만 추가했으며 최신 teacher에는 설치/적용하지 않았다.
- seed5140/step28 테란 R1: OFF는 패스, ON은 **교역소→연구소→광산 예측 경로의 첫 교역소**를
  선택(각9.91초). native 재검증 완료17경로, 최대3회 투자; 합성 회귀에서는4회도 가능.
  즉시 패스139.60 / 광산2개153.82 / 그 뒤 교역소 추가148.50 / 연구소 연결 경로167.16.
  값은 기존 leaf 예측이지 실제 획득VP/대국 점수가 아니다. 미탐색39개, 최적성 주장 없음.
- **남은 문제:** R3 자원 불균형 상태 step86·91은 완료0, step106은 패스 기준만 완료1.
  투자 우열을 확인하지 못해 패스를 유지했으므로, 조기 패스·과잉 교역소 문제 해결로 판정하지 않는다.
- 검증: 신규16/16·Python 핵심19/19·파생 관련36/36. 최신 experiments424건 중423 통과,
  기존 네블라 조언 실패1 유지. Rust596+RL8 통과/28 제외, lib/tests Clippy 통과,
  기존 평가944불변식928 통과/승인 예외16/실패0. 파생 전체 discovery 경로 충돌은 별도 기록.
  동결A200파일·파생167 Python파일 해시 불일치0. 새 전판·A/B·학습·배포·채택 없음.
- 근거/재현: `cycles/015-a02-round-investment.md`, `cycles/015-a02-round-investment.json`.
