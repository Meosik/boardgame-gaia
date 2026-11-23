# 132d-decision-probe-98ADBD-pass — 완료

E277 수정된 추천 (ㄱ)(= E276 (ㄱ)), 코덱스 이상 없음(사용자 2026-11-13 상시 지시): 132c와 같은 결정(사용자 방 98ADBD 5라운드, 130 대조 판 move-0의 하이브 첫 행동 = 5번째 결정)을 rollout 안 하이브 결정 기록이 든 도구(tools/decision_probe.py f17e7af: rollout 안에서 하이브가 수를 고를 때마다 라운드·고른 수(종류, 점수, 사유)·막히지 않은 순위 1위·후보 종류별 수·FormFederation 후보 수와 그중 막힌 수·가장 높은 연방 후보(점수, 사유, 위성 수, 칸)·가장 높은 패스 후보(점수, 사유)를 own_decisions에 기록)로 상한 없이 한 번 물음. 교사는 그대로(select_goal이 받은 순위와 돌려준 수를 읽어 기록만 함). 대국 없음. 상태·앞 5결정 재생·교사(all_tier cap60-p2, 병렬 2)·관심 수 셋은 132c와 같음. 물음 하나: front-nocap(상한 없음, 비교 9, 세 수를 root 목록 맨 앞). 탐색적 진단, 판정 없음(한 결정). 읽는 법(사전 등록): 대상 = 연방 없이 패스한 rollout(현재 수 current-choice, 끝나면 root-56·flip-229)에서 광산 셋 뒤 패스를 고른 하이브 결정. (a) 그 결정의 후보에 FormFederation이 있는가 — 없으면 「(i) 후보에 없었음: 132c의 '같은 행동이니 같은 상태' 추정이 틀림」으로 적고, 정거장 계획 rollout이 연방을 둔 결정의 후보 종류별 수와 나란히 적음. (b) 있으면 막힌 수와 가장 높은 연방 후보의 점수·사유를 패스의 점수·사유와 나란히 적음 — 모두 막혔으면 「막는 규칙(사유 그대로)」, 안 막혔는데 패스 점수가 더 높으면 「(ii) 위 층 점수: 순위가 패스를 연방보다 위에 둠」, 연방 점수가 더 높은데 패스를 골랐으면 「select_goal의 다른 경로」로 적고 고른 수와 순위 1위가 다른지 적음. (c) 정거장 계획 rollout이 연방을 둔 결정: 연방 후보의 점수와 그때의 순위 1위(= 계획이 없었다면 뒀을 수). (d) root-사용자 수(root-312) rollout이 위성 1짜리 연방을 둔 결정: 연방 후보 수·점수·순위 1위 여부 — 위성 셋짜리와의 점수 차. (e) 값·선택·행동 목록이 132c와 같은지(현재 수 131.46 · 정거장 계획 138.60 · root-사용자 수 133.60, 선택 = 정거장; 세 비교의 행동 목록) — 다르면 기록 추가가 결정을 바꾼 것일 수 있어 결정 기록을 결과로 쓰지 않고 원인부터 봄. 한정: 한 결정·한 상태, rollout은 교사의 싼 이어 두기, 점수는 그 시점 순위 값(층별 분해는 사유 문자열에 있는 만큼만), 뜻은 상한 없는 평가까지. 후반 연방 수·3연방 달성률(E277 토론)은 대국이 없는 이 실행에는 해당 없음 — 수정 A/B 때 등록. 건강 기준: 종료 코드 0, failures 빈 목록, digest_matches_log true, 폴백 타임아웃 0, 끝난 rollout 모두 comparison_times에 own_decisions가 있고 기록 오류(error 항목) 0. 예상 ≈ 3–5분(132c 한 물음 85초), 제한 2시간.

종료 코드 0

```
        R5 vp 26→26 {"type":"ResearchAdvance","track":"ArtificialIntelligence"}
        R5 vp 26→26 {"type":"IvitsPlaceSpaceStation","coord":"-1,3"}
        R5 vp 26→26 {"type":"Build","coord":"-8,7"}
        R5 vp 26→26 {"type":"Build","coord":"-9,8"}
        R5 vp 26→26 {"type":"Build","coord":"-7,8"}
        R5 vp 26→38 {"type":"Pass","booster_id":12}
        R5 vp 38→38 {"type":"ChooseIncomeOrder","charge_first":false}
        decide R5: chose TwilightReplayFederationToken (17.73333333333335) | top TwilightReplayFederationToken (17.73333333333335) | 338 candidates, FormFederation 0 (blocked 0) | best fed - | best pass -3.0
        decide R5: chose ResearchAdvance (9.333333333333371) | top ResearchAdvance (9.333333333333371) | 148 candidates, FormFederation 0 (blocked 0) | best fed - | best pass None
        decide R5: chose IvitsPlaceSpaceStation (4.0) | top IvitsPlaceSpaceStation (4.0) | 336 candidates, FormFederation 0 (blocked 0) | best fed - | best pass -3.0
        decide R5: chose Build (3.6666666666666288) | top Build (3.6666666666666288) | 237 candidates, FormFederation 0 (blocked 0) | best fed - | best pass -3.0
        decide R5: chose Build (5.1142857142857) | top Build (5.1142857142857) | 141 candidates, FormFederation 0 (blocked 0) | best fed - | best pass -3.0
        decide R5: chose Build (3.6666666666666856) | top Build (3.6666666666666856) | 122 candidates, FormFederation 0 (blocked 0) | best fed - | best pass -3.0
        decide R5: chose Pass (39.26666666666665) | top Pass (39.26666666666665) | 58 candidates, FormFederation 0 (blocked 0) | best fed - | best pass 39.26666666666665
        decide R5: chose ChooseIncomeOrder (3.466666666666697) | top ChooseIncomeOrder (3.466666666666697) | 2 candidates, FormFederation 0 (blocked 0) | best fed - | best pass -
    rollout     root-56                                  started  64.905 s: 10.488 s, 61 decisions, rank 10.396 s in 60 calls (3273 candidates), select_goal 0.0 s in 8 calls
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
        decide R5: chose TwilightReplayFederationToken (19.46666666666664) | top TwilightReplayFederationToken (19.46666666666664) | 224 candidates, FormFederation 0 (blocked 0) | best fed - | best pass None
        decide R5: chose ResearchAdvance (10.400000000000034) | top ResearchAdvance (10.400000000000034) | 249 candidates, FormFederation 0 (blocked 0) | best fed - | best pass None
        decide R5: chose ResearchAdvance (9.199999999999989) | top ResearchAdvance (9.199999999999989) | 303 candidates, FormFederation 0 (blocked 0) | best fed - | best pass None
        decide R5: chose Build (3.6666666666666288) | top Build (3.6666666666666288) | 269 candidates, FormFederation 0 (blocked 0) | best fed - | best pass -3.0
        decide R5: chose Build (5.1142857142857565) | top Build (5.1142857142857565) | 169 candidates, FormFederation 0 (blocked 0) | best fed - | best pass -3.0
        decide R5: chose Build (3.6666666666666288) | top Build (3.6666666666666288) | 162 candidates, FormFederation 0 (blocked 0) | best fed - | best pass -3.0
        decide R5: chose Pass (47.5333333333333) | top Pass (47.5333333333333) | 107 candidates, FormFederation 14 (blocked 0) | best fed 7.276190476190436/3 sat native faction preview: paid state delta + explicit soft opp | best 
        decide R5: chose ChooseIncomeOrder (3.466666666666697) | top ChooseIncomeOrder (3.466666666666697) | 2 candidates, FormFederation 0 (blocked 0) | best fed - | best pass -
    rollout     tile-action-314-then-Rebellion-Rebellion started  75.396 s: not finished (cut)
    select_goal track-plan-Science-2                     started   84.42 s: 0.0 s
    rollout     track-plan-Science-2                     started   84.42 s: not finished (cut)
    front move [312]: started True, finished True, compared True
    front move [56]: started True, finished True, compared False
    front move [314]: started False, finished False, compared False
```

지표

```json
{
 "created_at": "2026-11-23T23:02:57.891733+09:00",
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
   "wall_seconds": 84.449,
   "index": 56,
   "action": {
    "type": "IvitsPlaceSpaceStation",
    "coord": "-1,3"
   },
   "chose_move": 1,
   "selected": "Ivits-st
```

<sub>agentmaco · 커밋 e26cf18 · 2026-11-23T23:02:57+09:00 → 2026-11-23T23:04:22+09:00</sub>
