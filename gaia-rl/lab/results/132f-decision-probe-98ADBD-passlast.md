# 132f-decision-probe-98ADBD-passlast — 완료

E281 추천 (ㄱ), 토론 1/1 수정(다른 좌석이 모두 패스한 결정에 한함) 뒤 코덱스 이상 없음(사용자 2026-11-13 상시 지시): 132e와 같은 결정·상태·관심 수 셋·물음 하나(front-nocap: 상한 없음, 비교 9, 세 수를 root 목록 맨 앞)·같은 도구(tools/decision_probe.py, 132e의 기록 그대로)를 교사만 바꿔 한 번 물음. 교사 = 132e의 것 + pass_last 플래그(tools/teacher_patches.py pass_last_scores, 228c8de; 스펙 …-all-tier-passlast-cap60-p2): 행동 단계에서 다른 좌석이 모두 패스했고 막히지 않은 가장 높은 점수가 패스이고 막히지 않은 패스 아닌 후보에 점수 > 0이 있으면 패스 후보를 가장 낮은 양수 후보 아래로 내림, 다른 좌석이 하나라도 남았으면 순위 그대로. 대국 없음. 탐색적 진단, 판정 없음(한 결정). 읽는 법(사전 등록): 비교 대상 = 132e의 같은 rollout(현재 수 131.46 · root-56 131.46 · 정거장 → 연방 계획 138.60 · root-사용자 수 133.60 · flip-229 133.12). 식민 비교(넷째)는 132–132e에서 매번 목표 칸이 달라 값 비교에서 뺌. (a) 발동: 현재 수·root-56 rollout이 다른 좌석 3/3 패스 결정에서 FormFederation을 두는지(132e에서는 패스 47.53을 둠) — 두면 「플래그가 적힌 대로 걸림」, 안 두면 구현·조건부터 봄. 사유에 pass_last가 붙은 결정의 others_passed가 모두 3/3인지 — 아닌 결정이 하나라도 있으면 조건 위반(구현 오류)으로 적고 나머지를 결과로 쓰지 않음. (b) 값: 현재 수·root-56 rollout 값이 132e의 131.46보다 오르는지, 정거장 계획 138.60과 견줘 어디인지(연방 뒤 남는 작은 양수 행동 — 132e에서 우주선 탐사 3.27 · 기술 타일 행동 1.33 · Twilight 범위 탐사 0.60 — 까지 두게 되므로 138.60과 다를 수 있음). (c) 작은 양수만 남았던 rollout: flip-229(132e 133.12, 남은 것 우주선 탐사 1.93 하나) · root-사용자 수(133.60, 광산 3.67 등 13개)의 값이 132e보다 오르는지 내리는지. 다섯 rollout 가운데 하나라도 132e보다 내리면 「양수 점수 행동을 모두 먼저」는 과함으로 적고 수정안을 「그 수 뒤 패스 점수까지 더한 합이 바로 패스보다 클 때만」으로 좁히는 것을 다음 일로; 모두 같거나 오르면 끔 대 켬 A/B 설계(시드 수·라운드는 사용자 수치)로. (d) root: root 순위(move_ranks)와 후보 수가 132e와 같은지(root 결정은 다른 좌석이 남아 있어 플래그가 걸리지 않아야 함 — 다르면 원인부터). root 선택이 132e(정거장 계획 138.60)와 같은지 — rollout 값이 바뀌므로 달라질 수 있음, 달라지면 무엇이 얼마로 이겼는지 적음. (e) rollout마다 마지막 패스 전에 더 둔 행동의 수와 종류, rollout이 6라운드까지 끝나는지(end_round 6, 패스가 결국 두어지는지). 한정: 한 결정·한 상태, rollout은 교사의 싼 이어 두기, 실제 대국에서의 빈도·효과는 묻지 않음(그건 A/B). 건강 기준: 종료 코드 0, failures 빈 목록, digest_matches_log true, 폴백 타임아웃 0, 끝난 rollout 모두 own_decisions가 있고 기록 오류(error 항목, pass_after·federation_after의 error 포함) 0. 물음 시간은 132e(86.00초)와의 차이만 적음(행동이 늘어 rollout이 길어질 수 있어 ±10% 기준은 두지 않음). 예상 ≈ 3–5분, 제한 2시간.

종료 코드 0

```
        decide R5: chose RebellionGainTechTile (7.780952380952385) | top RebellionGainTechTile (7.780952380952385) | 132 candidates, FormFederation 0 (blocked 0) | best fed - | best pass -3.0 | others passed 2/3 | after pass R5 | 37 positive
        decide R5: chose FormFederation (15.37142857142851) | top FormFederation (15.37142857142851) | 36 candidates, FormFederation 7 (blocked 0) | best fed 15.37142857142851/2 sat native faction preview: paid state delta + explicit soft opp | best pass -3.0 | others passed 2/3 | after pass R5 | 10 positive
        decide R5: chose Build (3.3999999999999773) | top Build (3.3999999999999773) | 23 candidates, FormFederation 0 (blocked 0) | best fed - | best pass 0.5 | others passed 3/3 | after pass R5 | 3 positive
        decide R5: chose TechTileSpecialAction (2.6666666666667425) | top TechTileSpecialAction (2.6666666666667425) | 12 candidates, FormFederation 0 (blocked 0) | best fed - | best pass 1.3333333333333712 | others passed 3/3 | after pass R5 | 1 positive
        decide R5: chose Pass (46.46666666666664) | top Pass (46.46666666666664) | 13 candidates, FormFederation 0 (blocked 0) | best fed - | best pass 46.46666666666664 | others passed 3/3 | after pass R5 | 0 positive
        decide R5: chose ChooseIncomeOrder (2.6666666666666288) | top ChooseIncomeOrder (2.6666666666666288) | 2 candidates, FormFederation 0 (blocked 0) | best fed - | best pass - | others passed 3/3 | after pass R- | 2 positive
    rollout     root-314                                 started 100.302 s: 12.315 s, 68 decisions, rank 12.196 s in 67 calls (3908 candidates), select_goal 0.001 s in 14 calls
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
 "created_at": "2026-11-23T23:41:06.987040+09:00",
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
   "wall_seconds": 112.624,
   "index": 312,
   "action": {
    "type": "Upgrade",
    "coord": "-2,4",
    "to": {
     "Academy": "Qic"
    },
    "tech_ti
```

<sub>agentmaco · 커밋 cf6af1a · 2026-11-23T23:41:06+09:00 → 2026-11-23T23:42:59+09:00</sub>
