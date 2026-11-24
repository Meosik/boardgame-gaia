# 132j-decision-probe-98ADBD-rootscores — 완료

사용자 2026-11-24 「내 수가 230위인거면 우선 순위가 잘못된거잖아」 → 토론 1/1 수정 1건 뒤 코덱스 이상 없음(사용자 2026-11-13 상시 지시), HANDOFF E292: 132i와 같은 결정·상태·관심 수 셋·물음 하나(front-nocap: 상한 없음, 비교 9, 세 수를 root 목록 맨 앞)·스펙(…-all-tier-passlast-shipnow-cap60-p2)으로 한 번 더, 바꾼 것은 도구의 기록뿐(27af00b: tools/decision_probe.py install_root_scores + tools/rank_terms.py) — root 기본 순위의 모든 후보 점수·사유·순위와, 관심 수 셋·상위 20개·정보 큐브 아카데미 변형 가운데 최고 3개의 「상태 값 항목별 차」(수를 둔 뒤 − 두기 전; guide_potential의 항목을 그대로 따라 더한 거울, 이름 없는 몫은 other = 전체 − 이름 붙은 항목; score_minus_delta = 순위 점수 − 상태 값 차 = 점수 패치가 더한 몫). 대국 없음. 탐색적 진단, 판정 없음(한 결정). 읽는 법(사전 등록): (a) 기록이 탐색을 안 바꿨는지 먼저 — 후보 350·순위(move_ranks 230 · 15 · 260)·끝난 rollout의 값(현재 수 143.40 · 정거장 → 연방 계획 143.40 · root-56 143.40 · root-사용자 수 146.16 · flip-229 133.12 · 314 → Rebellion 계획 134.73 · 과학 연구 계획 141.40 · root-314 134.73; 식민 비교는 목표 칸이 달라 뺌)이 132i와 같아야 함. 다르면 기록이 탐색에 닿은 것 → 분해를 결과로 쓰지 않고 원인부터. (b) 분해가 온전한지 — 행마다 other의 차가 절댓값 0.01 이하면 온전, 넘으면 그 행은 「불완전」이라 적고 넘은 크기를 적음. (c) 읽을 것: 사용자 수(230위)의 항목별 차를 정거장(15위)·상위 20개·아카데미 변형 최고 3개와 나란히 — 무엇이 깎고 무엇이 더하는지, 특히 federation_progress(다음 연방 진척) 항목과 tiles(기술 타일) 항목의 차. 이 분해는 **항목별 기여의 관찰**까지만 읽음(토론 1/1, 코덱스 지적 수용 — 결과 전에 고침, 가지 ①·②와 0.5 표시는 없앰): 두 항목의 차가 작으면 「그 두 항목의 기여가 작다」까지, 크면 「그만큼 들어 있다」까지이고 어느 쪽도 원인 확정이 아님 — 연방 가치를 일부만 반영하고 크게 저평가할 수 있으므로 「낮은 순위는 다른 항목 몫」으로 돌리지 않음. 후속 연방 가치가 빠졌는지는 따로 확인: 132i의 root-사용자 수 rollout이 실제로 둔 연방(26 → 34, +8점과 토큰)을 기준으로 놓고 사용자 수의 federation_progress·tiles 차를 나란히 적어 얼마가 들어 있고 얼마가 빠졌는지를 보고, 코드 자리(tools/teacher_patches.py 456–487행 federation_progress는 건물 파워 값을 고정표(의회·아카데미 3)로 세고 「행성의회/아카데미 파워 가치 +1」 타일을 안 봄, 533–542행 standard_tiles_value는 그 타일에 값 0, four_factions/teacher.py 120 · 136–154행은 한 수 뒤 상태 차 + 자유 행동만 후속 한 수 표본)와 대조. 설계 제안은 그 대조 뒤(이 실행은 설계하지 않음). (d) own_federations_after는 차례가 넘어가는 수(업그레이드)에서는 None — 「다음 수에 연방을 둠」은 132i의 root-사용자 수 rollout(아카데미 → 연방 토큰 다시 받기 → 연방 26 → 34)으로만 읽음. (e) 230위만으로 순위 오류라 확정하지 않음; 이 실행 뒤에도 순위 수정의 효과는 A/B 전까지 미확정. 참고(결과 아님): 작업 트리 빌드 스모크(후보 412, 다른 빌드)에서 사용자 수 −12.20 = 자원 −20.80 · 연구 +10.67 · 부스터 −9.80 · 파워 +6.40 …, federation_progress 차 0 · tiles 차 0. 한정: 한 결정·한 상태; 거울 분해는 진단용이고 교사가 쓰지 않음; 실제 대국에서의 빈도·효과는 묻지 않음. 건강 기준: 종료 코드 0, failures 빈 목록, digest_matches_log true, 폴백 타임아웃 0, asks[0].root_scores에 error 없음·breakdown 행에 error 없음, 끝난 rollout 모두 own_decisions 있음. 예상 ≈ 3–5분, 제한 2시간.

종료 코드 0

```
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
root ranking (front-nocap): 340 unblocked; rank, score, score − state delta, largest parts of the state delta
    #230 [312]   -12.20  +0.00 | stock -20.80 research +10.67 booster -9.80 power +6.40 colony_options +4.00 income -2.67 | {"type":"Upgrade","coord":"-2,4","to":{"Academy":"Qic"},"tech_tile_ch…
    #15 [56]     4.00  +0.00 | structures +4.00 | {"type":"IvitsPlaceSpaceStation","coord":"-1,3"}
    #260 [314]   -14.93  -0.00 | stock -16.13 research +10.67 booster -9.80 tiles +3.00 income -2.67 | {"type":"Upgrade","coord":"-2,4","to":{"Academy":"Qic"},"tech_tile_ch…
    #1 [272]    19.47  -0.00 | research +10.67 stock +6.00 research_options +2.80 | {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_…
    #2 [274]    17.73  +0.00 | research +10.67 power +6.40 colony_options +4.00 stock -3.33 | {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_…
    #3 [281]    15.80  -0.00 | research +10.67 vp +7.00 stock -4.67 research_options +2.80 | {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_…
    #4 [273]    14.80  +0.00 | research +10.67 stock +9.47 research_options -4.67 ships -2.00 power +1.33 | {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_…
    #5 [283]    14.80  +0.00 | research +10.67 stock +9.47 research_options -4.67 ships -2.00 power +1.33 | {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_…
    #6 [228]    12.13  +0.00 | research +10.67 research_options +2.80 stock -1.33 | {"type":"ResearchAdvance","track":"ArtificialIntelligence"}
    #7 [275]    12.00  +0.00 | research +10.67 stock +1.33 | {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_…
    #8 [230]    10.40  -0.00 | research +10.67 stock -10.67 power +6.40 colony_options +4.00 | {"type":"ResearchAdvance","track":"GaiaProject"}
    #9 [276]     8.67  -0.00 | research +10.67 stock -3.33 research_options +1.33 | {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_…
    #10 [229]     7.47  -0.00 | research +10.67 research_options -4.67 stock +2.13 ships -2.00 power +1.33 | {"type":"ResearchAdvance","track":"Economy"}
    #11 [277]     7.33  +0.00 | research +10.67 stock -3.33 | {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_…
    #12 [280]     7.07  -0.00 | stock -14.00 research +10.67 power +6.40 colony_options +4.00 | {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_…
    #13 [231]     4.67  -0.00 | research +10.67 stock -6.00 | {"type":"ResearchAdvance","track":"Navigation"}
    #14 [282]     4.33  +0.00 | research +10.67 stock -9.33 tiles +3.00 | {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_…
    #16 [57]     4.00  +0.00 | structures +4.00 | {"type":"IvitsPlaceSpaceStation","coord":"-1,4"}
    #17 [58]     4.00  +0.00 | structures +4.00 | {"type":"IvitsPlaceSpaceStation","coord":"-1,5"}
    #18 [81]     4.00  +0.00 | structures +4.00 | {"type":"IvitsPlaceSpaceStation","coord":"-2,3"}
    #19 [82]     4.00  +0.00 | structures +4.00 | {"type":"IvitsPlaceSpaceStation","coord":"-2,6"}
    #20 [88]     4.00  +0.00 | structures +4.00 | {"type":"IvitsPlaceSpaceStation","coord":"-3,2"}
    #43 [346]     1.53  +4.67 | research +10.67 booster -9.80 research_options -4.67 stock +2.67 income -2.67 ships -2.00 power +1.33 | {"type":"Upgrade","coord":"-2,5","to":{"Academy":"Qic"},"tech_tile_ch…
    #51 [315]     0.20  +4.67 | research +10.67 booster -9.80 research_options -4.67 stock +2.67 income -2.67 ships -2.00 power +1.33 | {"type":"Upgrade","coord":"-2,4","to":{"Academy":"Qic"},"tech_tile_ch…
    #55 [337]    -0.20  +0.00 | research +10.67 stock -10.13 booster -9.80 power +6.40 colony_options +4.00 income -2.67 leech +1.33 | {"type":"Upgrade","coord":"-2,5","to":{"Academy":"Qic"},"tech_tile_ch…
```

지표

```json
{
 "created_at": "2026-11-24T13:45:29.283134+09:00",
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
   "wall_seconds": 119.275,
   "index": 312,
   "action": {
    "type": "Upgrade",
    "coord": "-2,4",
    "to": {
     "Academy": "Qic"
    },
    
```

<sub>agentmaco · 커밋 5ec28da · 2026-11-24T13:45:28+09:00 → 2026-11-24T13:47:28+09:00</sub>
