# 115a-federation-one-route-check — 완료

사용자 2026-11-13 「진행해」(HANDOFF E136 (ㄱ), E137): 115 재검증 — 엔진 966e9ea: 플래그 켬이면 건물 묶음마다 최소 길 하나만 복원(그 모양이 불법이면 전체 열거로 돌아감), 두 모드 공통으로 모양을 일반 토큰으로 한 번 검증한 뒤에만 토큰·보너스를 시도(플래그 끔의 후보 목록·탐색 예산은 불변이어야 함). 판정 없음, 대국 없음. 도구는 115와 같고 73262aa(④ 속도 검사)·917d4f5(크래시 상태 자유 행동 fork도 불변식 비교)가 들어감. 사전 등록 통과 기준(도구가 PASS여야 통과): ① 엔진 재빌드 성공·flag_effective 참(실패면 컴파일 오류 — 봇 턴에서 수정) ② 불변식 (a)(b)(c)(d) 위반 0 — 기록된 548결정과 pair-012 크래시 상태 자유 행동 44개 fork 모두(final_free checked = n) ③ fork 오류 0 ④ pair-012 자유 행동 fork 합 켬 10초 미만(115: 15.0초), 잘림 없음 ⑤ 플래그 끔 후보 수가 115와 같음: 크래시 상태 최대 17,318, 기록된 진행 pair-012 최대 204·합 340, pair-001 최대 12·합 46(다르면 끔 목록이 바뀐 것 = 실패). 볼 것(기준 아님): 끔 fork 합(115: 66.8초), 켬 후보 최대(115: 476). 예상 2–5분.

종료 코드 0

```
runs/lab-114-all-tier-selfplay-18f-full/pair-012/game-0-A02: steps=224 fed_states=8 max_fed off/on=204/34 total_fed off/on=340/114 fork_s off/on=0.2/0.2 final_free n=44 checked=44 off/on=51.4/2.1s truncated=False
runs/lab-114-all-tier-selfplay-18f-full/pair-001/game-0-A01: steps=324 fed_states=5 max_fed off/on=12/8 total_fed off/on=46/34 fork_s off/on=0.2/0.2 final_free n=0 checked=0 off/on=0.0/0.0s truncated=False
violations: a=0 b=0 c=0 d=0 fork_errors=0 flag_effective=True speed_failures=0
PASS
```

지표

```json
{
 "games": {
  "runs/lab-114-all-tier-selfplay-18f-full/pair-012/game-0-A02": {
   "steps_checked": 224,
   "states_with_federation_off": 8,
   "max_fed_off": 204,
   "max_fed_off_step": 160,
   "max_fed_on": 34,
   "max_fed_on_step": 160,
   "total_fed_off": 340,
   "total_fed_on": 114,
   "fork_seconds_off": 0.22098879679106176,
   "fork_seconds_on": 0.20409236708655953,
   "max_fork_seconds_off": 0.018114137987140566,
   "max_fork_seconds_on": 0.005301614000927657,
   "final_free_actions": 44,
   "final_free_checked": 44,
   "final_free_truncated": {},
   "final_free_fork_seconds_off": 51.41438186512096,
   "final_free_max_fed_off": 17318,
   "final_free_fork_seconds_on": 2.1292965027387254,
   "final_free_max_fed_on": 476
  },
  "runs/lab-114-all-tier-selfplay-18f-full/pair-001/game-0-A01": {
   "steps_checked": 324,
   "states_with_federation_off": 5,
   "max_fed_off": 12,
   "max_fed_off_step": 71,
   "max_fed_on": 8,
   "max_fed_on_step": 122,
   "total_fed_off": 46,
   "total_fed_on": 34,
   "fork_seconds_off": 0.18400848720921203,
   "fork_seconds_on": 0.18170931609347463,
   "max_fork_seconds_off": 0.005295773968100548,
   "max_fork_seconds_on": 0.005106377997435629,
   "final_free_actions": 0,
   "final_free_checked": 0,
   "final_free_truncated": {},
   "final_free_fork_seconds_off": 0.0,
   "final_free_max_fed_off": 0,
   "final_free_fork_seconds_on": 0.0,
   "final_free_max_fed_on": 0
  }
 },
 "violations": {
  "a": 0,
  "b": 0,
  "c": 0,
  "d": 0
 },
 "violation_examples": {},
 "fork_errors": [],
 "flag_effective": true,
 "max_final_free_seconds_on": 10.0,
 "speed_failures": [],
 "passed": true
}
```

<sub>agentmaco · 커밋 419898a · 2026-11-13T13:12:07+09:00 → 2026-11-13T13:13:05+09:00</sub>
