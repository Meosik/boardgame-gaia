# 132e-decision-probe-98ADBD-passstate — 완료

E279 추천 (ㄱ)의 뒷부분(코드로 안 정해지면 도구 기록), 코덱스 이상 없음(사용자 2026-11-13 상시 지시): 132d와 같은 결정·상태·교사·관심 수 셋·물음 하나(front-nocap: 상한 없음, 비교 9, 세 수를 root 목록 맨 앞)를 기록이 더 든 도구(tools/decision_probe.py c9fe0af: rollout 안 하이브 결정마다 132d의 기록에 더해 다른 좌석 수와 패스한 수(others, others_passed) · 자기 점수와 자원(own: vp, ore, credits, knowledge, qic) · 막히지 않은 패스 아닌 후보 가운데 점수 > 0인 수(positive_others)와 그 종류별 수(positive_by_type)·위 셋(top_others) · 가장 높은 패스를 교사와 같은 fork로 둔 뒤 상태(pass_after: round, phase, player, own, others_passed) · 가장 높은 연방을 둔 뒤 상태(federation_after: round, own))로 한 번 물음. 교사는 그대로(읽기만; fork는 교사가 순위를 매길 때 쓰는 것과 같은 호출). 대국 없음. 탐색적 진단, 판정 없음(한 결정). 읽는 법(사전 등록): 대상 = 현재 수(current-choice)·root-56 rollout에서 패스 점수가 −3.00이던 결정들과 47.53이 된 결정(132d). (a) 그 결정들의 others_passed와 pass_after.round·phase — 47.53 결정에서 pass_after.round = 6이고 −3.00 결정들에서 5면 「패스 점수의 뜀 = 라운드 넘김: 패스 뒤 상태가 다음 라운드라 potential의 식이 바뀜」 확인으로 적고 others_passed(3/3인지)를 나란히 적음; 47.53 결정에서도 5면 그 추정은 틀림으로 적고 potential 항 분해를 다음 일로 둠. (b) 47.53 결정의 positive_by_type(양수 후보 전부의 종류별 수)과 positive_others, top_others 셋의 점수 — positive_by_type에 FormFederation만 있으면 「연방에 한한 문제」, 다른 종류도 있으면 「남은 이득 행동 전반」으로 적음(수정안 A/B 선택의 근거; 위 셋만으로는 판정하지 않음 — 토론 1/1). (c) 현재 수 rollout 패스 결정의 연방 값 = own.qic − federation_after.own.qic(두기 전 − 둔 뒤 잔액; 다른 자원도 같은 식으로), flip-229 패스 결정의 own.qic을 그 값과 나란히 적음 — flip-229의 QIC가 그 값보다 적으면 「QIC 부족 추정과 맞음」, 같거나 많으면 「QIC만으로는 설명 안 됨」까지만 적음. 어느 쪽이든 확정·기각은 아님: 두 rollout은 연구 경로·건물·파워 상태가 다를 수 있고 가장 높은 연방 하나의 값만 보기 때문(토론 1/1) — 까닭은 미확인으로 남김. (d) pass_after.own.vp − own.vp(패스가 주는 점수)와 federation_after.own.vp − own.vp, 패스 전후 자원 변화(수입이 들어왔는지). (e) 값·선택·행동 목록과 132d의 기록(현재 수 131.46 · 정거장 계획 138.60 → 선택 · root-사용자 수 133.60; 패스 결정의 연방 후보 14개·막힘 0·연방 7.28·패스 47.53)이 132d와 같은지 — 다르면 fork 기록이 결정을 바꾼 것일 수 있어 새 기록을 결과로 쓰지 않고 원인부터 봄. 한정: 한 결정·한 상태, rollout은 교사의 싼 이어 두기, 뜻은 상한 없는 평가까지; 실제 대국에서의 빈도는 묻지 않음. 건강 기준: 종료 코드 0, failures 빈 목록, digest_matches_log true, 폴백 타임아웃 0, 끝난 rollout 모두 own_decisions가 있고 기록 오류(error 항목, pass_after·federation_after의 error 포함) 0, 물음 시간이 132d(84.45초)의 ±10% 안. 예상 ≈ 3–5분, 제한 2시간.

종료 코드 0

```
        R5 vp 26→26 {"type":"ResearchAdvance","track":"ArtificialIntelligence"}
        R5 vp 26→26 {"type":"IvitsPlaceSpaceStation","coord":"-1,3"}
        R5 vp 26→26 {"type":"Build","coord":"-8,7"}
        R5 vp 26→26 {"type":"Build","coord":"-9,8"}
        R5 vp 26→26 {"type":"Build","coord":"-7,8"}
        R5 vp 26→38 {"type":"Pass","booster_id":12}
        R5 vp 38→38 {"type":"ChooseIncomeOrder","charge_first":false}
        decide R5: chose TwilightReplayFederationToken (17.73333333333335) | top TwilightReplayFederationToken (17.73333333333335) | 338 candidates, FormFederation 0 (blocked 0) | best fed - | best pass -3.0 | others passed 0/3 | after pass R5 | 39 positive
        decide R5: chose ResearchAdvance (9.333333333333371) | top ResearchAdvance (9.333333333333371) | 148 candidates, FormFederation 0 (blocked 0) | best fed - | best pass None | others passed 0/3 | after pass R- | 41 positive
        decide R5: chose IvitsPlaceSpaceStation (4.0) | top IvitsPlaceSpaceStation (4.0) | 336 candidates, FormFederation 0 (blocked 0) | best fed - | best pass -3.0 | others passed 1/3 | after pass R5 | 36 positive
        decide R5: chose Build (3.6666666666666288) | top Build (3.6666666666666288) | 237 candidates, FormFederation 0 (blocked 0) | best fed - | best pass -3.0 | others passed 1/3 | after pass R5 | 9 positive
        decide R5: chose Build (5.1142857142857) | top Build (5.1142857142857) | 141 candidates, FormFederation 0 (blocked 0) | best fed - | best pass -3.0 | others passed 1/3 | after pass R5 | 12 positive
        decide R5: chose Build (3.6666666666666856) | top Build (3.6666666666666856) | 122 candidates, FormFederation 0 (blocked 0) | best fed - | best pass -3.0 | others passed 2/3 | after pass R5 | 8 positive
        decide R5: chose Pass (39.26666666666665) | top Pass (39.26666666666665) | 58 candidates, FormFederation 0 (blocked 0) | best fed - | best pass 39.26666666666665 | others passed 3/3 | after pass R5 | 1 positive
        decide R5: chose ChooseIncomeOrder (3.466666666666697) | top ChooseIncomeOrder (3.466666666666697) | 2 candidates, FormFederation 0 (blocked 0) | best fed - | best pass - | others passed 3/3 | after pass R- | 2 positive
    rollout     root-56                                  started  65.235 s: 10.705 s, 61 decisions, rank 10.594 s in 60 calls (3273 candidates), select_goal 0.0 s in 8 calls
        value 131.45714285714286, goal acquired False, end round 6, 9 own actions:
        R5 vp 26→26 {"type":"IvitsPlaceSpaceStation","coord":"-1,3"}
        R5 vp 26→26 {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_coord":null,"bonus_tech_tile":…
        R5 vp 26→26 {"type":"ResearchAdvance","track":"GaiaProject"}
        R5 vp 26→26 {"type":"ResearchAdvance","track":"ArtificialIntelligence"}
        R5 vp 26→26 {"type":"Build","coord":"-8,7"}
        R5 vp 26→26 {"type":"Build","coord":"-9,8"}
        R5 vp 26→26 {"type":"Build","coord":"-7,8"}
        R5 vp 26→38 {"type":"Pass","booster_id":12}
        R5 vp 38→38 {"type":"ChooseIncomeOrder","charge_first":false}
        decide R5: chose TwilightReplayFederationToken (19.46666666666664) | top TwilightReplayFederationToken (19.46666666666664) | 224 candidates, FormFederation 0 (blocked 0) | best fed - | best pass None | others passed 0/3 | after pass R- | 24 positive
        decide R5: chose ResearchAdvance (10.400000000000034) | top ResearchAdvance (10.400000000000034) | 249 candidates, FormFederation 0 (blocked 0) | best fed - | best pass None | others passed 0/3 | after pass R- | 12 positive
        decide R5: chose ResearchAdvance (9.199999999999989) | top ResearchAdvance (9.199999999999989) | 303 candidates, FormFederation 0 (blocked 0) | best fed - | best pass None | others passed 1/3 | after pass R- | 17 positive
        decide R5: chose Build (3.6666666666666288) | top Build (3.6666666666666288) | 269 candidates, FormFederation 0 (blocked 0) | best fed - | best pass -3.0 | others passed 1/3 | after pass R5 | 12 positive
        decide R5: chose Build (5.1142857142857565) | top Build (5.1142857142857565) | 169 candidates, FormFederation 0 (blocked 0) | best fed - | best pass -3.0 | others passed 1/3 | after pass R5 | 15 positive
        decide R5: chose Build (3.6666666666666288) | top Build (3.6666666666666288) | 162 candidates, FormFederation 0 (blocked 0) | best fed - | best pass -3.0 | others passed 2/3 | after pass R5 | 11 positive
        decide R5: chose Pass (47.5333333333333) | top Pass (47.5333333333333) | 107 candidates, FormFederation 14 (blocked 0) | best fed 7.276190476190436/3 sat native faction preview: paid state delta + explicit soft opp | best pass 47.5333333333333 | others passed 3/3 | after pass R5 | 18 positive
        decide R5: chose ChooseIncomeOrder (3.466666666666697) | top ChooseIncomeOrder (3.466666666666697) | 2 candidates, FormFederation 0 (blocked 0) | best fed - | best pass - | others passed 3/3 | after pass R- | 2 positive
    rollout     tile-action-314-then-Rebellion-Rebellion started  75.944 s: not finished (cut)
    select_goal track-plan-Science-2                     started  85.971 s: 0.0 s
    rollout     track-plan-Science-2                     started  85.971 s: not finished (cut)
    front move [312]: started True, finished True, compared True
    front move [56]: started True, finished True, compared False
    front move [314]: started False, finished False, compared False
```

지표

```json
{
 "created_at": "2026-11-23T23:19:31.000902+09:00",
 "state": "runs/lab-130-room-first-move-98ADBD/states/round-5.json",
 "prefix_log": "runs/lab-130-room-first-move-98ADBD/round-5/move-0/game-0/decisions.jsonl.gz",
 "prefix_steps": 5,
 "teacher": "teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-menu1-all-tier-cap60-p2",
 "seed": "98ADBD-s0",
 "digest": "f56cdbc35b155ee612efcb5d970f99b49e47f5d033ffededcec9f8c8148abc6d",
 "digest_in_log": "f56cdbc35b155ee612efcb5d970f99b49e47f5d033ffededcec9f8c8148abc6d",
 "digest_matches_log": true,
 "logged_choice": {
  "index": 272,
  "action": {
   "type": "TwilightReplayFederationToken",
   "token_kind": 12,
   "bonus_build_coord": null,
   "bonus_tech_tile": 13,
   "bonus_research_track": "ArtificialIntelligence"
  },
  "selected": "current-choice",
  "seconds": 60.035,
  "completed_comparisons": 1,
  "timing": {
   "choose": 60.033,
   "audit_fresh": true,
   "search": 60.033,
   "cap": 60,
   "published_at": [
    1.906,
    16.428,
    60.0
   ],
   "stages": {
    "bind_check": 0.001,
    "root_rank": 1.242,
    "planned_tasks": 0.661,
    "prefetch": 1.904,
    "drop_unfinished": 0.027,
    "parallel_search": 60.027,
    "search_call": 60.028,
    "state_check": 0.003
   },
   "time_capped": true,
   "budget_stopped": false,
   "expired_before_search": false
  }
 },
 "round": 5,
 "seat": 0,
 "faction": "Ivits",
 "candidates": 350,
 "candidates_by_type": {
  "IvitsPlaceSpaceStation": 125,
  "Upgrade": 65,
  "PowerAction": 50,
  "FreeAction": 33,
  "SpaceshipCreditTerraform": 19,
  "TwilightRangeBuild": 15,
  "TwilightReplayFederationToken": 13,
  "Build": 11,
  "ResearchAdvance": 6,
  "ExamineArtifact": 4,
  "Pass": 3,
  "ExploreSpaceship": 2,
  "TwilightRangeExploreSpaceship": 2,
  "TFMarsTechBonus": 1,
  "TechTileSpecialAction": 1
 },
 "upgrade_candidates_by_target": {
  "{\"Academy\": \"Qic\"}": 62,
  "TradingStation": 3
 },
 "moves": [
  {
   "position": 0,
   "index": 312,
   "action": {
    "type": "Upgrade",
    "coord": "-2,4",
    "to": {
     "Academy": "Qic"
    },
    "tech_tile_choice": {
     "kind": "Standard",
     "tile": 6,
     "advance_track": null,
     "bonus_build_coord": null
    }
   },
   "rank": 230
  },
  {
   "position": 1,
   "index": 56,
   "action": {
    "type": "IvitsPlaceSpaceStation",
    "coord": "-1,3"
   },
   "rank": 15
  },
  {
   "position": 2,
   "index": 314,
   "action": {
    "type": "Upgrade",
    "coord": "-2,4",
    "to": {
     "Academy": "Qic"
    },
    "tech_tile_choice": {
     "kind": "Standard",
     "tile": 8,
     "advance_track": null,
     "bonus_build_coord": null
    }
   },
   "rank": 260
  }
 ],
 "asks": [
  {
   "label": "front-nocap",
   "comparisons": 9,
   "cap": null,
   "front": [
    0,
    1,
    2
   ],
   "front_indices": [
    312,
    56,
    314
   ],
   "wall_seconds": 86.004,
   "index": 56,
   "action": {
    "type": "IvitsPlaceSpaceStation",
    "coord": "-1,3"
   },
   "chose_move": 1,
   "selected": "Ivits-st
```

<sub>agentmaco · 커밋 7cb65a7 · 2026-11-23T23:19:29+09:00 → 2026-11-23T23:20:57+09:00</sub>
