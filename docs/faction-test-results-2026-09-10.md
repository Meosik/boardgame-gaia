# 종족 테스트 — 자동 검증 결과 (2026-09-10)

## 결론

**18종족에 관련된 기존 자동 검사를 재실행하고, 빈 분기 6개 테스트를 추가했다. 이번 실행에서 실패한 검사는 없다.**
종족별로 실제 사용감까지 모두 통과했다는 뜻은 아니다. 아래는 **실행한 코드 경로의 결과**이다.
사용자는 아래 규칙 검사를 반복할 필요 없이 플레이하며 이상한 점/불편한 점만 알려주면 된다.

- `cargo test -p gaia-engine`: **496 통과**, 문서 예제1개 ignored. 이 중 unit suite412개(기존406+신규6).
- `cargo test -p gaia-server --lib`: **26 통과**.
- frontend `npm test`: **46 suites / 373 통과**. TypeScript/Vite build 및 `git diff --check` 통과.
- 사용자 방·자원·행동을 변경하지 않았다. 이번 수정은 테스트/문서뿐이다. 학습 실행·서버 재시작 없음.
- 테스트는 격리된 엔진 상태와 프론트 컴포넌트를 사용했다. 이번 실행에 브라우저 실게임 E2E/DB 복구 실험은 포함하지 않았다.

## 이번에 추가한 경계 검사

| 검사 | 기대 결과 | 실제 결과 / 근거 |
|---|---|---|
| 앰바스·파이락·하이브·모웨이드 PI 없음 / 매드 안드로이드 PI 없음 | 앞4종족 거절, 매드 안드로이드 허용. 거절 시 상태 변화0 | 5종족 분기 일치. `faction_checklist::special_actions_reject_without_pi_except_bescods_without_mutation` |
| 5종족 능력 실행 → 저장 복원 → 같은 라운드 → 다음 라운드 | 복원 후 사용 표시 유지, 같은 라운드 두 번째 거절, 다음 라운드 재사용 성공 | 전부 일치. 두 번째 대상은 사용 표시를 빼면 합법인 것으로 별도 확인. 내 차례가 아니라서 거절된 것을 성공으로 오인하지 않음 |
| 하드쉬 할라 3종 교환 | PI 전 거절, 비용1 부족 시 거절/변화0, 정상 비용으로2회 실행 후 정확한 보상·턴 유지 | QIC/광석/지식 각각+2, 크레딧0, 나머지 자원 변화0. 매 실행 뒤 저장 복원 포함 |
| 팅커로이드 후반 자원 타일 | 타일4 QIC+2 / 타일6 지식+3, 저장 복원 후 재사용 거절 | 정확한 증가량과 거절 후 전체 상태 불변 확인 |
| 란티다 공생 광산2개 | PI 전 추가 지식0 / PI 후 매번+2, 광산 비용만 차감 | PI 없는/있는 상태 각각2회, 저장 복원 후 지식3 유지 / 3→5→7, 광석10→8, 크레딧15→11 |
| 스페이스 자이언트 PI 고급기술 | 업그레이드와 고급기술·덮기·연방 뒤집기·다른 연구 상승을 한 턴에 처리 | 고급20 획득, 일반3 덮음, 연방1 회색, 테라포밍4 유지/과학0→1, PI 사용 표시 유지, 다음 플레이어로 이동. 저장 복원 포함 |

새 코드: [faction_checklist.rs](../gaia-engine/tests/unit/faction_checklist.rs),
[faction_abilities.rs](../gaia-engine/tests/unit/faction_abilities.rs),
[free_actions.rs](../gaia-engine/tests/unit/free_actions.rs),
[tinkeroids.rs](../gaia-engine/tests/unit/tinkeroids.rs).

## 종족별 실제 확인 범위

아래 모두 **나열한 경로 통과**. 한 행을 종족의 모든 조합 검증 완료로 해석하지 않는다.
테스트 이름은 관련 파일에서 검색 가능하다.

| 종족 | 기대 결과와 확인한 경로 | 주요 테스트 위치 |
|---|---|---|
| 테란 | 가이아 파워 II 반환, 수입→가이아 선택 순서, PI 교환 후 남은 선택량 및 완료 처리 | `round_loop`: `gaia_phase_moves_terrans_power_to_area_two`, `terrans_planetary_institute_converts_gaia_power_then_moves_the_remainder_to_area_two` |
| 란티다 | 상대 행성 공생·소유권 유지·테라포밍 면제, 공생 가이아의 종류 집계 제외, PI 전후 반복 지식, 라운드 토큰 수입 | `faction_abilities`의 `lantids_*`, `round_loop::lantids_gain_one_power_in_area_one_per_round_lost_fleet_exploration_board` |
| 제노스 | 시작 AI 보상, PI 전7/후6 연방, 광석→III 토큰, PI QIC 수입 | `faction_abilities`의 `xenos_*`, `free_actions::lost_fleet_xenos_converts_ore_directly_to_bowl3_power`, `structure_income` |
| 글린 | QIC→광석 대체와 아카데미 해제, 가이아 광산 광석 비용/+2VP, PI 전용 연방, 항속+2 행동 공유 제한/리셋 | `faction_abilities` 및 `lost_fleet_spaceships`의 `gleens_*` |
| 타클론 | 브레인스톤 파워3 소비·가이아 이동/복귀, PI 토큰 추가 전/후 충전, 함선 탐사 시 브레인스톤 이동 | `faction_abilities` 및 `lost_fleet_spaceships`의 `taklons_*` |
| 앰바스 | 광산/PI 교환, 업그레이드 점수 없음, PI 조건·저장 후 사용 제한·다음 라운드 해제 | `faction_abilities::ambas_swap_moves_the_pi_and_mine_without_scoring_an_upgrade`, 신규5종족 행렬 |
| 하드쉬 할라 | 크레딧4/3/4 교환 비용, PI 조건, 부족 거절, 반복 지급과 저장 후 턴 유지 | `free_actions::hadsch_hallas_all_conversions_gate_pi_reject_shortfall_and_repeat_after_reload` |
| 하이브 | 첫7/확장14, 기존망 연결, 위성 QIC 비용, 정거장 조건/파워, 초록·회색 포함/TF5 보너스 제외, 저장 및 라운드 리셋 | `ivits` 전체 및 신규5종족 행렬 |
| 지오덴 | PI 전 점유 종류 제외, PI 후 새 종류만 지식3, 같은 종류 재지급 방지 | `faction_abilities::geodens_reward_only_applies_to_new_post_pi_planet_types_once` |
| 발타크 | PI 전 항법 잠금/후 해제, 가이아포머→QIC 및 다음 가이아 회수, 정보 아카데미 크레딧4, 탐사7VP | `faction_abilities`, `free_actions`, `structure_income`, `ai_decisions::ice_factions_discard_a_token_and_baltaks_pay_seven_vp` |
| 파이락 | 기본/연구소 지식 수입, 연구소 강등과 연구 상승, PI 조건·다른 연구소로도 재사용 제한·저장·라운드 리셋 | `structure_income`, `faction_abilities::firaks_downgrades_a_lab_and_advances_research_once_per_round`, 신규 행렬 |
| 매드 안드로이드 | 최저 연구 선택/다른 트랙 거절, PI 불필요, 건물 경로·수입 교환, PI 회색 파워+1, 저장·라운드 리셋 | `faction_abilities`의 `bescods_*`, `structure_income`, 신규 행렬, frontend `AppSpaceshipActions` |
| 네뷸라 | III→가이아 토큰 보존, PI 소비 효율(자유행동/함선4종), 부족 거절, 이동에는 배율 미적용, 연구소 충전 수입 | `free_actions`, `faction_abilities`, `lost_fleet_spaceships::nevlas_pi_halves_all_four_spaceship_power_spends`, `structure_income` |
| 이타르 | 연소 토큰 가이아 이동, PI 전 반환, 일반/고급 반복 기술, 조건 부족 거절, 고급만 남아도 선택 진입, 과학 아카데미 수입3 | `free_actions`, `round_loop`의 `itars_*`, `structure_income`, frontend `ActionPanel` |
| 팅커로이드 | PI/선택 타일/라운드 구간 조건, 사용 제한·미사용 타일 제거, 전후반 자원·충전, 무료 테라포밍 건설, 배정3색/가이아 비용 | `tinkeroids` 전체 |
| 모웨이드 | 시작 연구·색상 배정, 자기 건물 파워링·중복/최대6 제한, 연방/충전 파워+2, 가이아 비용, PI·저장·라운드 리셋 | `moweyds` 전체, `faction_abilities` 셋업, 신규 행렬 |
| 스페이스 자이언트 | 시작 항법·테라포밍2/가이아 QIC2, PI 일반/고급 기술 동시 획득·추가 턴 없음, 기존 저장 보상 회수, 탐사판 무료2단계/횟수 리셋, 수입6 | `faction_abilities`, `lost_fleet_spaceships`, `structure_income`, server `game_action`, frontend `AppSpaceshipActions` |
| 다카니안 | PI 전 무보상, 새 일반/깊은 섹터마다 크레딧2+지식1, 동일/기존 점유/인터스페이스 제외, 검은 행성 점유, 저장 후 재발동 | `faction_abilities`의 `darkanians_*` |

공통 연구5 조건·기술 덮기·연방·라운드 점수·최종 점수 및 속성 기반 검사도 전체 엔진 실행에 포함됐다.

## 아직 남아 있는 것 — 사용자가 전부 할 일이 아님

### 제가 추가로 자동 검증할 기술적 범위
- 18종족 각각의 **모든 기술 × 모든 함선 × 라운드 목표** 조합 전수 검사.
- 종족별 특수행동마다 실제 서버/DB를 거친 되돌리기·재접속 전체 왕복. 이번 저장 검사는 엔진 직렬화 복원이며, 서버 되돌리기는 기존 일반 경로 unit 검사다.
- 지금까지 누락됐을 수 있는 다른 분기. 테스트 통과를 오류가 전혀 없다는 보장으로 보지 않는다.

### 플레이하면서 사용자 판단이 도움이 되는 부분
- 버튼/숫자/종족 이미지가 충분히 잘 보이는가.
- 행동 시작→대상/기술 선택→취소 위치가 자연스럽고 방해되지 않는가.
- 설명과 로그를 보고 무슨 일이 일어났는지 이해하기 쉬운가.

이상하면 체크리스트 ID와 행동 전/후만 알려주면 된다. **이미 자동 통과한 규칙을 하나씩 재검사할 필요는 없다.**
