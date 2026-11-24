# 132g-decision-probe-98ADBD-passfrom — 완료

E283 추천 (ㄱ), 토론 1/1 수정 2건 뒤 코덱스 이상 없음(사용자 2026-11-13 상시 지시): 132f와 같은 결정·상태·교사(pass_last 플래그 켠 스펙 …-all-tier-passlast-cap60-p2)·관심 수 셋·물음 하나(front-nocap: 상한 없음, 비교 9, 세 수를 root 목록 맨 앞)·도구(tools/decision_probe.py)로 한 번 더. 바뀐 것은 기록뿐(49fa9cd): pass_last_scores가 내린 패스의 사유 꼬리에 내리기 전 점수를 「(from 점수)」로 적고, decision_probe.py가 사유를 200자로 자르기 전에 읽어 그 후보 기록의 pass_last_from 칸에 넣음; 순위·점수는 그대로. 대국 없음. 탐색적 진단, 판정 없음(한 결정). 읽는 법(사전 등록): (e) 먼저 132f와 같은지 — 여덟 rollout의 값(현재 수 143.40 · 정거장 → 연방 계획 143.40 · root-56 143.40 · root-사용자 수 146.16 · flip-229 131.59 · 과학 연구 계획 141.40 · 314 → Rebellion 계획 134.73 · root-314 134.73)·root 선택(root-사용자 수 146.16)·하이브 행동 목록·root 순위가 132f와 같아야 함(식민 비교는 132–132f에서 매번 목표 칸이 달라 뺌); 다르면 새 기록을 결과로 쓰지 않고 원인부터. (a) 기록: 사유에 pass_last가 붙은 결정(132f 47개)의 best_pass 모두에 pass_last_from이 있는지(누락 0). 132e와 대조: 현재 수·root-56 rollout의 첫 플래그 결정 = 47.53, flip-229의 첫 플래그 결정 = 39.27 — 다르면 기록 오류로 적고 (b)를 결과로 쓰지 않음. (b) 좁힌 규칙 「둔 수의 점수 + 그 수 뒤 패스 점수 > 지금 패스 점수일 때만 둠」을 구현 없이 셈, 두 묶음으로 나눠 적음: ① 플래그가 걸린 결정 가운데 바로 다음 하이브 결정에 패스 후보 점수가 있는 것 — 합 = 고른 수의 점수 + 다음 결정의 패스 점수(다음 결정도 플래그가 걸렸으면 그 pass_last_from, 아니면 best_pass 점수) 대 지금 결정의 pass_last_from; 합 ≤ 지금이면 「좁힌 규칙이 막았을 결정」. ② 바로 다음 결정이 후속 선택이라 패스 후보 점수가 없는 것(132f에 6건, 예: 기술 타일 뒤 연구 고르기) — ①과 섞지 않고 따로: 고른 수 + 후속 선택의 점수 + 그 뒤 첫 패스 점수 대 지금, 참고로만 적음. (c) 결론 가지: flip-229의 우주선 탐사 결정(①에 듦)이 「막았을 결정」이면 → 좁힌 규칙을 opt-in 플래그로 구현해 같은 결정을 다시 묻는 것을 다음 일로, 그때 값이 오른 rollout(현재 수·root-56·정거장 계획·root-사용자 수)에서 ①이 막았을 결정이 몇 개이고 무엇인지 함께 적음(오른 rollout의 행동을 막으면 좁힘의 값 효과는 다시 물어야 앎). 「안 막았을 결정」이면 → 사전 등록한 좁힘이 그 자리를 못 거르므로 좁힘은 접고, 단순 플래그 끔 대 켬 A/B 설계(시드 수·라운드는 사용자 수치) + 우주선 탐사 점수 읽기(봇 턴)를 따로. 주의: 한 rollout 안에서 좁힌 규칙이 어느 결정을 막으면 그 뒤 결정들은 일어나지 않으므로 「막았을 결정」의 수는 서로 독립이 아님 — rollout마다 첫 막힘만 확정으로 읽음. 한정: 한 결정·한 상태, rollout은 교사의 싼 이어 두기, 실제 대국에서의 빈도·효과는 묻지 않음(그건 A/B). 건강 기준: 종료 코드 0, failures 빈 목록, digest_matches_log true, 폴백 타임아웃 0, 끝난 rollout 모두 own_decisions가 있고 기록 오류(error 항목, pass_after·federation_after의 error 포함) 0, pass_last_from 누락 0. 물음 시간은 132f(112.62초)와의 차이만 적음. 예상 ≈ 3–5분, 제한 2시간.

종료 코드 0

```
        decide R5: chose RebellionGainTechTile (7.780952380952385) | top RebellionGainTechTile (7.780952380952385) | 132 candidates, FormFederation 0 (blocked 0) | best fed - | best pass -3.0 | others passed 2/3 | after pass R5 | 37 positive
        decide R5: chose FormFederation (15.37142857142851) | top FormFederation (15.37142857142851) | 36 candidates, FormFederation 7 (blocked 0) | best fed 15.37142857142851/2 sat native faction preview: paid state delta + explicit soft opp | best pass -3.0 | others passed 2/3 | after pass R5 | 10 positive
        decide R5: chose Build (3.3999999999999773) | top Build (3.3999999999999773) | 23 candidates, FormFederation 0 (blocked 0) | best fed - | best pass 0.5 | others passed 3/3 | after pass R5 | 3 positive
        decide R5: chose TechTileSpecialAction (2.6666666666667425) | top TechTileSpecialAction (2.6666666666667425) | 12 candidates, FormFederation 0 (blocked 0) | best fed - | best pass 1.3333333333333712 | others passed 3/3 | after pass R5 | 1 positive
        decide R5: chose Pass (46.46666666666664) | top Pass (46.46666666666664) | 13 candidates, FormFederation 0 (blocked 0) | best fed - | best pass 46.46666666666664 | others passed 3/3 | after pass R5 | 0 positive
        decide R5: chose ChooseIncomeOrder (2.6666666666666288) | top ChooseIncomeOrder (2.6666666666666288) | 2 candidates, FormFederation 0 (blocked 0) | best fed - | best pass - | others passed 3/3 | after pass R- | 2 positive
    rollout     root-314                                 started  87.463 s: 12.541 s, 68 decisions, rank 12.411 s in 67 calls (3908 candidates), select_goal 0.001 s in 14 calls
        value 134.73333333333332, goal acquired False, end round 6, 15 own actions:
        R5 vp 26→26 {"type":"Upgrade","coord":"-2,4","to":{"Academy":"Qic"},"tech_tile_choice":{"kind":"Standard","tile…
        R5 vp 26→26 {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_coord":null,"bonus_tech_tile":…
        R5 vp 26→26 {"type":"ResearchAdvance","track":"GaiaProject"}
        R5 vp 26→26 {"type":"ResearchAdvance","track":"ArtificialIntelligence"}
        R5 vp 26→26 {"type":"AcademyQicAction"}
        R5 vp 26→26 {"type":"IvitsPlaceSpaceStation","coord":"-1,3"}
        R5 vp 26→26 {"type":"Build","coord":"-7,0"}
        R5 vp 26→21 {"type":"ExploreSpaceship","ship":"Rebellion"}
        R5 vp 21→21 {"type":"RebellionGainTechTile","tile":11,"track":"GaiaProject","bonus_build_coord":"-8,7"}
        R5 vp 21→29 {"type":"FormFederation","hexes":["-8,5","-8,7","-7,4"],"satellite_hexes":["-8,6","-7,3"],"token":{…
        R5 vp 29→29 {"type":"Build","coord":"-9,8"}
        R5 vp 29→29 {"type":"TechTileSpecialAction","tile":{"pool":"Standard","tile":10}}
        R5 vp 29→29 {"type":"RebellionCreditsAndQic"}
        R5 vp 29→44 {"type":"Pass","booster_id":12}
        R5 vp 44→44 {"type":"ChooseIncomeOrder","charge_first":false}
        decide R5: chose TwilightReplayFederationToken (19.46666666666664) | top TwilightReplayFederationToken (19.46666666666664) | 199 candidates, FormFederation 0 (blocked 0) | best fed - | best pass None | others passed 0/3 | after pass R- | 49 positive
        decide R5: chose ResearchAdvance (10.399999999999977) | top ResearchAdvance (10.399999999999977) | 224 candidates, FormFederation 0 (blocked 0) | best fed - | best pass None | others passed 0/3 | after pass R- | 38 positive
        decide R5: chose ResearchAdvance (9.200000000000045) | top ResearchAdvance (9.200000000000045) | 284 candidates, FormFederation 0 (blocked 0) | best fed - | best pass None | others passed 1/3 | after pass R- | 45 positive
        decide R5: chose AcademyQicAction (4.666666666666686) | top AcademyQicAction (4.666666666666686) | 311 candidates, FormFederation 0 (blocked 0) | best fed - | best pass -3.0 | others passed 1/3 | after pass R5 | 41 positive
        decide R5: chose IvitsPlaceSpaceStation (4.0) | top IvitsPlaceSpaceStation (4.0) | 310 candidates, FormFederation 0 (blocked 0) | best fed - | best pass -3.0 | others passed 1/3 | after pass R5 | 39 positive
        decide R5: chose Build (3.6666666666666856) | top Build (3.6666666666666856) | 166 candidates, FormFederation 0 (blocked 0) | best fed - | best pass -3.0 | others passed 2/3 | after pass R5 | 12 positive
        decide R5: chose ExploreSpaceship (3.266666666666538) | top ExploreSpaceship (3.266666666666538) | 101 candidates, FormFederation 0 (blocked 0) | best fed - | best pass 0.2999999999999545 | others passed 3/3 | after pass R5 | 5 positive
        decide R5: chose RebellionGainTechTile (7.780952380952385) | top RebellionGainTechTile (7.780952380952385) | 198 candidates, FormFederation 0 (blocked 0) | best fed - | best pass 0.06666666666666288 | others passed 3/3 | after pass R5 | 27 positive
        decide R5: chose FormFederation (15.371428571428567) | top FormFederation (15.371428571428567) | 103 candidates, FormFederation 7 (blocked 0) | best fed 15.371428571428567/2 sat native faction preview: paid state delta + explicit soft opp | best pass 0.46666666666666856 | others passed 3/3 | after pass R5 | 13 
        decide R5: chose Build (3.3999999999999773) | top Build (3.3999999999999773) | 87 candidates, FormFederation 0 (blocked 0) | best fed - | best pass 0.36666666666667425 | others passed 3/3 | after pass R5 | 6 positive
        decide R5: chose TechTileSpecialAction (2.6666666666667425) | top TechTileSpecialAction (2.6666666666667425) | 31 candidates, FormFederation 0 (blocked 0) | best fed - | best pass 0.466666666666697 | others passed 3/3 | after pass R5 | 2 positive
        decide R5: chose RebellionCreditsAndQic (0.9333333333332803) | top RebellionCreditsAndQic (0.9333333333332803) | 33 candidates, FormFederation 0 (blocked 0) | best fed - | best pass 0.46666666666664014 | others passed 3/3 | after pass R5 | 1 positive
        decide R5: chose Pass (41.13333333333338) | top Pass (41.13333333333338) | 31 candidates, FormFederation 0 (blocked 0) | best fed - | best pass 41.13333333333338 | others passed 3/3 | after pass R5 | 0 positive
        decide R5: chose ChooseIncomeOrder (1.3333333333333712) | top ChooseIncomeOrder (1.3333333333333712) | 2 candidates, FormFederation 0 (blocked 0) | best fed - | best pass - | others passed 3/3 | after pass R- | 1 positive
    front move [312]: started True, finished True, compared True
    front move [56]: started True, finished True, compared True
    front move [314]: started True, finished True, compared True
```

지표

```json
{
 "created_at": "2026-11-24T11:14:39.912025+09:00",
 "state": "runs/lab-130-room-first-move-98ADBD/states/round-5.json",
 "prefix_log": "runs/lab-130-room-first-move-98ADBD/round-5/move-0/game-0/decisions.jsonl.gz",
 "prefix_steps": 5,
 "teacher": "teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-menu1-all-tier-passlast-cap60-p2",
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
   "wall_seconds": 100.012,
   "index": 312,
   "action": {
    "type": "Upgrade",
    "coord": "-2,4",
    "to": {
     "Academy": "Qic"
    },
    "tech_ti
```

<sub>agentmaco · 커밋 e344c5f · 2026-11-24T11:14:39+09:00 → 2026-11-24T11:16:20+09:00</sub>
