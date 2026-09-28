# Sol — 기술 계획 ON 시험 대국 1판

next: human
## 사용자 승인 (2026-09-24)

사용자는 '새 계획을 켜고 시험 대국 검증 — 실제 기술 취득→활용까지 이어지는지 확인'
선택지 1을 승인했다. 테란·앰바스 pilot 구현/대상 검증은 끝났으며 이번은
**실제 1판의 기능 검증**이다. 4시드 성능 판정, A/B, 가격 튜닝, BC/PPO 학습 아님.
이 새 승인 과제는 별도 최대 8시간·Sol 1회 세션으로 실행한다. 이전 기록 보존.

## 고정 실행 조건

- seed: `shared-teacher-base-38`
- 실제 초기 종족: Itars, Moweyds, Terrans, Ambas (순서 그대로).
- 기존 test_shared.py의 seed 계열을 0부터 검사해 두 대상 종족이 함께 나오는
  첫 시드를 선택했다. 점수·결과를 보고 고른 시드가 아니며 초기 상태를 변조하지 않았다.
- 초기 표준 기술 슬롯: [10,8,5,6,3,9,2,4,7], 대상 기술10/8/6 모두 존재.
- 기존 `faction_teachers`의 승인된 adaptive clock: 기본 10초, 좌석당 최대 6번
  총120초 긴 탐색. 기존 reaction/forced 빠른 처리·자연 조기 종료·fallback 그대로.
  B 평가 시간 실험의 10/20초 경로와 혼동하지 않는다. 시간/탐색 정책 수정 금지.
- `GAIA_FACTION_TECH_PLANS=1`, `GAIA_ENGINE_FIXES_2=1`은 이번 프로세스에만 적용.
  원문 자원 가격 플래그·다른 튜닝·기본값·기존 평가/동결 A/서비스 AI 변경 금지.
- output: `gaia-rl/runs/tech-plan-pilot-20260924-shared-38`
  이미 존재하면 덮어쓰거나 2판째를 실행하지 말고 해당 기록의 소유·상태부터 확인.

## Sol 실행 — 명령 먼저, 불필요한 재조사 금지

환경 복구와 실제 sandbox 경계 검증은 `handoff/sandbox-validation.json`에 있다.
최근 Sol 대상 19/19, 핵심19/19, 전체383/384(범위 밖14종족 초안1실패)까지 완료.
이번에는 단위 테스트를 전부 다시 돌리는 대신 실제 시험 대국과 기록 검증을 한다.

`cd gaia-rl && timeout --signal=TERM --kill-after=10s 27000s env GAIA_ENGINE_FIXES_2=1 GAIA_FACTION_TECH_PLANS=1 PYTHONPATH=python:experiments .venv/bin/python -u -m faction_teachers record --seed shared-teacher-base-38 --adaptive-clock --output runs/tech-plan-pilot-20260924-shared-38 > ../handoff/logs/20260924-tech-plan-pilot-shared-38-run.log 2>&1`

- 새 게임은 이 1판만. 완료되기 전에 더 좋은 결과를 위해 재시작/시드 교체/상태 조작 금지.
- production horizon 그대로 실행. 단위 테스트의 한 수 종료 stub/mock을 사용하지 않는다.
- 기존 NativeRecorder의 실제 네이티브 비용 지불·다중 기록 일치와 버전/소스 가드를 유지한다.
- 장시간 명령은 백그라운드 세션/적절한 긴 poll로 기다린다. 촘촘한 busy polling/방대한 반복출력 금지.
  progress.json/teacher-audit.jsonl/체크포인트의 관측된 진행만 STATUS에 주기적으로 요약한다.
- 시간 한도/오류 발생 시 기존 진행·체크포인트를 보존하고 완료로 보고하지 않는다.
  이번 승인으로 제품/엔진/테스트/평가 코드를 자동 수정하거나 두 번째 대국을 실행하지 않는다.

## 기능 판정 / 기록

대국 종료 후 기존 기록만 읽어 아래를 확인한다. 추출용 임시 분석 코드는 허용하지만
새 평가/전략/게임 코드는 만들지 않는다. 확인 불가능한 항목은 '미관측/판별 불가'로 기록.

1. 실제 실행 manifest/감사/체크포인트에 ON이 전달됐는지, 고정 종족·시간 설정 일치.
2. 테란: 기술10/8 취득 시점·실제 비용, 이후 실제 가이아 개척/득점 발생 여부.
3. 앰바스: 기술6 취득·의회 이동·그 자리 연방 연결이 실제로 발생했는지.
4. pilot 계획의 후보/완료 평가/선택/취소를 구별. 우연히 같은 행동을 했다는 것만으로
   계획이 선택되어 성공했다고 주장하지 않는다. 로그 부족/탐색 미완료도 구분한다.
5. 종족별 최종 건물·연방·점수·기술·연구 단계, fallback 비율, 결정당 시간,
   완성 비교 수를 얻을 수 있는 범위에서 요약한다. 점수는 관측치이며 우열 판정 아님.
6. 종결 여부와 기록/네이티브 재생 검증. 체크포인트 또는 최종 기보에 실제 검증 가능한
   경계를 사용하고, 재검증하지 않은 부분을 검증 완료라고 하지 않는다.

정상 종료라도 연계가 나타나지 않았으면 '이번 1판에서는 미확인'이다. 후보를 억지로
선택시키지 말고, 추가 설계/수정/실험이 필요한지 근거만 보고하고 멈춘다.

## 산출물 / 종료

- 진행·최종 사용자 요약: `gaia-rl/research/strategy/STATUS.md` 한 화면 표.
- 상세 검증 결과: `gaia-rl/research/strategy/cycles/010-tech-plan-pilot-1game.json`
  (seed·종족·설정·버전·완료 여부·관측 단계·수치·검증 명령·한계·기록 경로 포함).
- 원시 기보/녹화/결정 로그는 기존 ignored runs/와 handoff/logs/에만 보존.
- 기존 기보/재생을 덮어쓰거나 frontend에 공개하지 않는다. git commit/push/배포/학습 금지.
- 성공/미관측 결과 보고 후 status=human. 실행 자체 오류는 gate_failed로 증거를 남긴다.
- 감독은 이번 호출 1회 후 종료하며 자동 후속 구현/재대국은 없다.

## 권한·소유 경계

Sol만 검증 담당. 제품·기존 테스트·전략·엔진·기본 플래그·평가 가격·설치·권한 변경 금지.
기존 타인의 수정 보존. reset/clean/추가 에이전트/추가 루프 실행 금지.
QUEUE next/감독 상태/HANDOFF LOOP 자동 관리 구역은 supervisor만 변경한다.
