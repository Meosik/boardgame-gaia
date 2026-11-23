# 129-room-handover-98ADBD — 완료

사용자 2026-11-23 「내 플레이로 하이브 교사의 실력을 높일 수 있나? 테스트 해봐」 → 「ㄱ」 → 「진행해」(HANDOFF E258·E259·E261 (ㄱ)·E262): 이어 두기 본 실험. 사용자 판 98ADBD(하이브 187점, 상대 실서버 AI 3좌석)의 1·4·5·6라운드 첫 행동 결정 자리에서 4좌석을 같은 교사 ships_menu1_all_tier cap60-p2 비교 4가 끝까지 둠, 시작 자리당 1판 = 4판(--jobs로 동시). 맵·종족·좌석·시작 자리까지의 판은 방 기록 그대로(시드 없음, E259: 교사는 같은 자리에서 같은 수 — 달라질 수 있는 것은 60초 상한에 걸린 결정뿐). 128 스모크(6라운드 시작 1판, 통과)와 같은 명령에 --rounds만 1 4 5 6. 방 기록은 lab과 같은 기계의 ~/gaia-media/rooms/98ADBD-snapshots.jsonl. 봇 턴 점검(4개 시작 자리 로드 + 각 1결정, --max-steps 1)은 통과: 시작 VP(하이브) 1R 10·4R 11·5R 27·6R 64. 엔진은 lab HEAD 빌드라 방을 둔 실서버 엔진과 다름(E252 하이브 연방 편입, E257 종료 때 환전) — 방의 187점과 직접 비교하지 않음. 탐색적 진단, 판정 없음(한 방·시작 자리당 1판; 실력 향상 입증 아님 — 입증은 그 뒤 같은 조건 짝 비교). 읽는 법(E258 코덱스 토론으로 정함): 대조군 = 1라운드 시작 판(같은 맵·종족·좌석, 교사가 사용자·실서버 AI의 셋업에서 시작). 하이브 최종 점수(4·5·6라운드 시작) − 1라운드 대조군 = 사용자가 그 라운드까지 만든 자리(상대 자리 포함)의 값. 4라운드 스냅샷에는 실서버 AI 상대의 초반 운영도 들어 있어 사용자 오프닝만의 효과로 분리되지 않고, 낮게 끝나도 후반 운영 탓으로 확정되지 않음 → 어느 구간을 explain으로 볼지 고르는 용도. 다른 맵의 교사 평균(≈97점)과 비교하지 않음. 건강 기준: 4/4판 완주(metrics.json games_complete 4, failures 빈 목록), 오류 0, 폴백 타임아웃 0. 같이 볼 것: 팔별 60초 상한에 끊긴 결정 수(재현 안 되는 결정은 그것뿐)·최대 결정 시간·100초 초과 결정 수, 팔별 상대 3좌석 최종 점수, 좌석별 연방 행동 수, 6라운드 팔 재현 — 128과 같은 자리라 185/69/93/121이 다시 나와야 함(128은 상한에 끊긴 결정 0); 다르면 「시작 자리당 1판」이 고정값이 아니라는 뜻이라 읽기에 그대로 적음. 예상 ≈ 1–1.5시간(1라운드 팔이 6라운드 전체 한 판, lab 123 판당 ≈ 76분; 4팔 동시), 제한 3시간. 리플레이 게시 없음.

종료 코드 0

```
{"start_round": 6, "repeat": 0, "complete": true, "failure": null, "scores": {"0": 185, "1": 69, "2": 93, "3": 121}, "stopped_at_round": null, "max_seconds": 57.24}
{"start_round": 4, "repeat": 0, "complete": true, "failure": null, "scores": {"0": 134, "1": 74, "2": 84, "3": 118}, "stopped_at_round": null, "max_seconds": 60.032}
{"start_round": 5, "repeat": 0, "complete": true, "failure": null, "scores": {"0": 155, "1": 66, "2": 85, "3": 114}, "stopped_at_round": null, "max_seconds": 60.069}
{"start_round": 1, "repeat": 0, "complete": true, "failure": null, "scores": {"0": 103, "1": 104, "2": 86, "3": 106}, "stopped_at_round": null, "max_seconds": 60.059}
Ivits in room 98ADBD: the room's own final 187
start round 1: VP then 10, teacher finals [103] mean 103 vs round-1 start 0 (1/1 finished)
start round 4: VP then 11, teacher finals [134] mean 134 vs round-1 start 31 (1/1 finished)
start round 5: VP then 27, teacher finals [155] mean 155 vs round-1 start 52 (1/1 finished)
start round 6: VP then 64, teacher finals [185] mean 185 vs round-1 start 82 (1/1 finished)
```

지표

```json
{
 "room": "98ADBD",
 "focus": "Ivits",
 "focus_seat": 0,
 "factions": [
  "Ivits",
  "SpaceGiants",
  "Tinkeroids",
  "Itars"
 ],
 "room_final_scores": {
  "0": 187,
  "1": 71,
  "2": 88,
  "3": 103
 },
 "room_focus_final": 187,
 "games_planned": 4,
 "games_complete": 4,
 "failures": [],
 "max_steps": null,
 "by_start_round": {
  "1": {
   "games": 1,
   "finished": 1,
   "start_vp": 10,
   "focus_scores": [
    103
   ],
   "mean": 103,
   "mean_minus_round1": 0
  },
  "4": {
   "games": 1,
   "finished": 1,
   "start_vp": 11,
   "focus_scores": [
    134
   ],
   "mean": 134,
   "mean_minus_round1": 31
  },
  "5": {
   "games": 1,
   "finished": 1,
   "start_vp": 27,
   "focus_scores": [
    155
   ],
   "mean": 155,
   "mean_minus_round1": 52
  },
  "6": {
   "games": 1,
   "finished": 1,
   "start_vp": 64,
   "focus_scores": [
    185
   ],
   "mean": 185,
   "mean_minus_round1": 82
  }
 },
 "games": [
  {
   "start_round": 1,
   "repeat": 0,
   "game": "game-0",
   "complete": true,
   "failure": null,
   "error": null,
   "steps": 249,
   "stopped_at_round": null,
   "scores": {
    "0": 103,
    "1": 104,
    "2": 86,
    "3": 106
   },
   "federations_formed": [
    3,
    1,
    1,
    1
   ],
   "decisions": 249,
   "max_seconds": 60.059,
   "at_or_over_60_seconds": 11,
   "over_100_seconds": 0,
   "fallback_timeouts": 0,
   "focus_score": 103,
   "focus_rank": 3
  },
  {
   "start_round": 4,
   "repeat": 0,
   "game": "game-0",
   "complete": true,
   "failure": null,
   "error": null,
   "steps": 187,
   "stopped_at_round": null,
   "scores": {
    "0": 134,
    "1": 74,
    "2": 84,
    "3": 118
   },
   "federations_formed": [
    2,
    1,
    0,
    1
   ],
   "decisions": 187,
   "max_seconds": 60.032,
   "at_or_over_60_seconds": 2,
   "over_100_seconds": 0,
   "fallback_timeouts": 0,
   "focus_score": 134,
   "focus_rank": 1
  },
  {
   "start_round": 5,
   "repeat": 0,
   "game": "game-0",
   "complete": true,
   "failure": null,
   "error": null,
   "steps": 139,
   "stopped_at_round": null,
   "scores": {
    "0": 155,
    "1": 66,
    "2": 85,
    "3": 114
   },
   "federations_formed": [
    1,
    0,
    0,
    0
   ],
   "decisions": 139,
   "max_seconds": 60.069,
   "at_or_over_60_seconds": 9,
   "over_100_seconds": 0,
   "fallback_timeouts": 0,
   "focus_score": 155,
   "focus_rank": 1
  },
  {
   "start_round": 6,
   "repeat": 0,
   "game": "game-0",
   "complete": true,
   "failure": null,
   "error": null,
   "steps": 76,
   "stopped_at_round": null,
   "scores": {
    "0": 185,
    "1": 69,
    "2": 93,
    "3": 121
   },
   "federations_formed": [
    1,
    0,
    0,
    1
   ],
   "decisions": 76,
   "max_seconds": 57.24,
   "at_or_over_60_seconds": 0,
   "over_100_seconds": 0,
   "fallback_timeouts": 0,
   "focus_score": 185,
   "focus_rank": 1
  }
 ]
}
```

<sub>agentmaco · 커밋 a388cb2 · 2026-11-23T13:04:26+09:00 → 2026-11-23T13:57:50+09:00</sub>
