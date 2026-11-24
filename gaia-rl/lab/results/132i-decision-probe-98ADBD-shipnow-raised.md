# 132i-decision-probe-98ADBD-shipnow-raised — 완료

E288 추천 (ㄱ), 토론 1/1 수정 1건 뒤 코덱스 이상 없음(사용자 2026-11-13 상시 지시): 132h와 같은 결정·상태·관심 수 셋·물음 하나(front-nocap: 상한 없음, 비교 9, 세 수를 root 목록 맨 앞)·도구(tools/decision_probe.py)·스펙(…-all-tier-passlast-shipnow-cap60-p2)으로 한 번 더, 바꾼 것은 ship_now의 상한뿐(80b7416, tools/teacher_patches.py ship_now_scores): 「이번 라운드 몫」(Rebellion 3.47)의 상한 후보에 탐사 전에도 있던 후보를 「탐사가 더한 만큼」 = min(탐사 뒤 점수, 탐사 뒤 점수 − 탐사 전 점수)로 넣음(오른 것만, 두 점수 모두 기본 순위; 탐사 전에 막혀 있던 후보는 새 후보처럼 점수 그대로; 새로 연 후보는 132h와 같음). 대국 없음. 탐색적 진단, 판정 없음(한 결정). 읽는 법(사전 등록) — 비교 대상은 132g의 같은 rollout(현재 수 143.40 · 정거장 → 연방 계획 143.40 · root-56 143.40 · root-사용자 수 146.16)과 132e·132h의 flip-229 133.12; 나머지 rollout은 값만 적음; 식민 비교는 매번 목표 칸이 달라 뺌. (a) 통과: flip-229 ≥ 133.12이고 네 rollout(현재 수·정거장 계획·root-56·root-사용자 수)이 모두 끝나서 132g 이상 → 다음은 pass_last 끔 대 켬 A/B 설계(시드 수·라운드는 사용자 수치), 탐사 플래그는 두 팔에 같게 켬. (b) 미확정: 넷 가운데 하나라도 끊겨 값이 없으면 통과 아님 — A/B 두 팔에 켜지 않고, 넷이 다 끝나게 다시 물음(132h는 탐색의 수렴 멈춤 stable completed alternatives로 5/9에서 끝남: four_factions/preparation.py 714행, faction_teachers.clock.converged; 다시 끊기면 그 규칙을 읽고 probe에서 넷을 끝까지 재는 길을 먼저 찾음). (c) 회귀: 넷 가운데 하나라도 132g보다 내리거나 flip-229 < 133.12 → 이 플래그는 A/B에 넣지 않고(두 팔 모두 끔) 내린 rollout의 행동 열에서 원인을 적음. (d) 확인할 행동 열: 현재 수·정거장 계획에서 탐사 3.27이 132g처럼 연방 바로 다음에 두어지고 파워 → QIC 환전 12.46 → Rebellion 기술 타일 17.33 → 연구 6.40이 돌아오는지(예상: 환전이 raised로 잡혀 몫 그대로, 꼬리 없음); flip-229에서 탐사가 −0.60 그대로인지(예상: 탐사 뒤 최고가 돈 + QIC 0.93). 예상과 다르면 그대로 적고 (a)–(c)는 값으로만 가름. (e) root: 후보 350·순위(move_ranks 230 · 15 · 260)는 132g·132h와 같아야 함(다르면 구현 오류). (f) 사유에 ship_now 꼬리(N opened, M raised)가 붙은 기록이 모두 다른 좌석 3/3 결정인지(아니면 구현 오류), 꼬리가 붙은 수와 그 점수. pass_last_from 누락 0과 끝난 rollout이 6라운드까지 가는지도 함께. 한정: 한 결정·한 상태, rollout은 교사의 싼 이어 두기, 실제 대국에서의 빈도·효과는 묻지 않음(그건 A/B). 건강 기준: 종료 코드 0, failures 빈 목록, digest_matches_log true, 폴백 타임아웃 0, 끝난 rollout 모두 own_decisions가 있고 기록 오류(error 항목, pass_after·federation_after의 error 포함) 0, pass_last_from 누락 0; 끝난 비교 수와 stop_reason을 적음. 물음 시간은 적기만 함(탐사가 자기 차례로 이어지는 결정마다 기본 순위 1회가 더 듦). 예상 ≈ 3–5분, 제한 2시간.

종료 코드 0

```
        decide R5: chose RebellionGainTechTile (7.780952380952385) | top RebellionGainTechTile (7.780952380952385) | 132 candidates, FormFederation 0 (blocked 0) | best fed - | best pass -3.0 | others passed 2/3 | after pass R5 | 37 positive
        decide R5: chose FormFederation (15.37142857142851) | top FormFederation (15.37142857142851) | 36 candidates, FormFederation 7 (blocked 0) | best fed 15.37142857142851/2 sat native faction preview: paid state delta + explicit soft opp | best pass -3.0 | others passed 2/3 | after pass R5 | 10 positive
        decide R5: chose Build (3.3999999999999773) | top Build (3.3999999999999773) | 23 candidates, FormFederation 0 (blocked 0) | best fed - | best pass 0.5 | others passed 3/3 | after pass R5 | 3 positive
        decide R5: chose TechTileSpecialAction (2.6666666666667425) | top TechTileSpecialAction (2.6666666666667425) | 12 candidates, FormFederation 0 (blocked 0) | best fed - | best pass 1.3333333333333712 | others passed 3/3 | after pass R5 | 1 positive
        decide R5: chose Pass (46.46666666666664) | top Pass (46.46666666666664) | 13 candidates, FormFederation 0 (blocked 0) | best fed - | best pass 46.46666666666664 | others passed 3/3 | after pass R5 | 0 positive
        decide R5: chose ChooseIncomeOrder (2.6666666666666288) | top ChooseIncomeOrder (2.6666666666666288) | 2 candidates, FormFederation 0 (blocked 0) | best fed - | best pass - | others passed 3/3 | after pass R- | 2 positive
    rollout     root-314                                 started 104.865 s: 13.82 s, 68 decisions, rank 13.691 s in 67 calls (3908 candidates), select_goal 0.001 s in 14 calls
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
        decide R5: chose ExploreSpaceship (3.266666666666538) | top ExploreSpaceship (3.266666666666538) | 101 candidates, FormFederation 0 (blocked 0) | best fed - | best pass 0.2999999999999545 | others passed 3/3 | after pass R5 | 4 positive
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
 "created_at": "2026-11-24T11:53:07.620806+09:00",
 "state": "runs/lab-130-room-first-move-98ADBD/states/round-5.json",
 "prefix_log": "runs/lab-130-room-first-move-98ADBD/round-5/move-0/game-0/decisions.jsonl.gz",
 "prefix_steps": 5,
 "teacher": "teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-menu1-all-tier-passlast-shipnow-cap60-p2",
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
   "wall_seconds": 118.692,
   "index": 312,
   "action": {
    "type": "Upgrade",
    "coord": "-2,4",
    "to": {
     "Academy": "Qic"
    },
    
```

<sub>agentmaco · 커밋 66430ad · 2026-11-24T11:53:06+09:00 → 2026-11-24T11:55:06+09:00</sub>
