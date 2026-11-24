# 132h-decision-probe-98ADBD-shipnow — 완료

E286 추천 (ㄱ), 토론 1/1 수정 2건 뒤 코덱스 이상 없음(사용자 2026-11-13 상시 지시): 132g와 같은 결정·상태·관심 수 셋·물음 하나(front-nocap: 상한 없음, 비교 9, 세 수를 root 목록 맨 앞)·도구(tools/decision_probe.py)로 한 번 더, 바꾼 것은 교사뿐 — 132g의 교사(pass_last 켬) + ship_now(16617f8, tools/teacher_patches.py ship_now_scores, 스펙 …-all-tier-passlast-shipnow-cap60-p2): 우주선 탐사 직후 다음 결정도 자기 차례(같은 라운드 행동 단계 = 다른 좌석이 모두 패스)일 때, 탐사 점수에 든 「이번 라운드 몫」(표 값 ÷ 1.5, Rebellion 3.47)을 min(몫, 탐사가 새로 연 후보(탐사 전에 없던 후보, 패스 제외, 막히지 않은 것)의 기본 순위 점수 가운데 가장 높은 것, 0 이상)으로 바꿈; 남은 라운드 몫은 그대로, 다른 좌석이 다음에 두면 점수 그대로. 대국 없음. 탐색적 진단, 판정 없음(한 결정). 읽는 법(사전 등록) — 비교 대상은 132g의 같은 rollout(현재 수 143.40 · 정거장 → 연방 계획 143.40 · root-56 143.40 · root-사용자 수 146.16 · flip-229 131.59)과 132e의 flip-229 133.12; 과학 연구 계획 141.40 · 314 → Rebellion 계획 134.73 · root-314 134.73은 값만 적음; 식민 비교는 매번 목표 칸이 달라 뺌. (a) 발동: flip-229 rollout이 132g에서 우주선 탐사 1.93을 두던 결정(다른 좌석 3/3)에서 탐사를 두지 않는지, 값이 133.12(132e의 바로 패스)로 돌아오는지; 탐사를 그대로 두면 발동 실패 → 나머지를 결과로 쓰지 않고 원인부터. (b) 값이 올랐던 네 rollout(현재 수·root-56·정거장 계획·root-사용자 수)이 132g보다 내리지 않는지, 탐사를 둔 결정의 점수(132g 3.27)와 순서가 어떻게 바뀌는지 — 예상: 탐사 직후 새로 열리는 것이 Rebellion 돈 + QIC 0.93뿐이면 탐사는 3.27 − 3.47 + 0.93 = 0.73으로 내려가 더 늦게 두어짐. (c) 결론 가지: flip-229가 133.12 이상으로 돌아오고 네 rollout이 모두 132g 이상이면 「통과」 → 다음은 pass_last 끔 대 켬 A/B 설계(시드 수·라운드는 사용자 수치), 탐사 플래그는 두 팔에 같게 켬(토론 1/1). 네 rollout 가운데 하나라도 132g보다 내리면 먼저 「회귀·원인 미확정」으로 적음(이 플래그는 탐사 점수와 행동 순서도 바꾸므로 값 하락만으로 원인을 정하지 않음) → 내린 rollout에서 132g의 수순에 있던 환전 뒤 함선 행동이 실제로 빠졌는지, 탐사 결정의 점수·순서가 어떻게 달라졌는지 행동 열로 확인한 뒤 넓힐지(환전으로 여는 행동 포함) 다른 원인인지 정함; 그때 A/B에는 이 플래그를 넣지 않음. (이 가지는 토론 1/1에서 코덱스 지적을 받아 결과를 보기 전에 고침.) (d) root: 후보 350·root 순위(move_ranks 230 · 15 · 260)는 132g와 같아야 함(root는 다른 좌석 0/3이라 탐사 뒤 다른 좌석 차례 → 플래그가 안 걸림); 다르면 구현 오류. root 선택과 견준 값은 적기만 함. (e) 사유에 ship_now 꼬리가 붙은 기록(고른 수·top·top_others에 든 것)이 모두 다른 좌석 3/3 결정인지(아니면 구현 오류), 꼬리가 붙은 수와 그 점수. pass_last 발동(132g: pass_last_from 45개, 누락 0)과 rollout이 6라운드까지 끝나는지도 함께. 한정: 한 결정·한 상태, rollout은 교사의 싼 이어 두기, 실제 대국에서의 빈도·효과는 묻지 않음(그건 A/B); 탐사하지 않은 후보의 점수는 기록에 없을 수 있음(고른 수·top·top_others만 기록). 건강 기준: 종료 코드 0, failures 빈 목록, digest_matches_log true, 폴백 타임아웃 0, 끝난 rollout 모두 own_decisions가 있고 기록 오류(error 항목, pass_after·federation_after의 error 포함) 0, pass_last_from 누락 0. 물음 시간은 132g(100.01초)와의 차이만 적음(탐사 후보마다 fork 1회 + 기본 순위 1회가 더 듦). 예상 ≈ 3–5분, 제한 2시간.

종료 코드 0

```
        R5 vp 24→24 {"type":"TechTileSpecialAction","tile":{"pool":"Standard","tile":10}}
        R5 vp 24→36 {"type":"Pass","booster_id":12}
        R5 vp 36→36 {"type":"ChooseIncomeOrder","charge_first":false}
        decide R5: chose TwilightReplayFederationToken (19.46666666666664) | top TwilightReplayFederationToken (19.46666666666664) | 199 candidates, FormFederation 0 (blocked 0) | best fed - | best pass None | others passed 0/3 | after pass R- | 49 positive
        decide R5: chose ResearchAdvance (10.399999999999977) | top ResearchAdvance (10.399999999999977) | 224 candidates, FormFederation 0 (blocked 0) | best fed - | best pass None | others passed 0/3 | after pass R- | 38 positive
        decide R5: chose TFMarsGaiaFormation (-9.0) | top ResearchAdvance (9.200000000000045) | 284 candidates, FormFederation 0 (blocked 0) | best fed - | best pass None | others passed 1/3 | after pass R- | 45 positive
        decide R5: chose TwilightRangeBuild (-11.933333333333337) | top ResearchAdvance (9.200000000000045) | 125 candidates, FormFederation 0 (blocked 0) | best fed - | best pass None | others passed 1/3 | after pass R- | 38 positive
        decide R5: chose ResearchAdvance (9.200000000000045) | top ResearchAdvance (9.200000000000045) | 66 candidates, FormFederation 0 (blocked 0) | best fed - | best pass None | others passed 1/3 | after pass R- | 40 positive
        decide R5: chose AcademyQicAction (4.666666666666686) | top AcademyQicAction (4.666666666666686) | 199 candidates, FormFederation 0 (blocked 0) | best fed - | best pass -3.0 | others passed 2/3 | after pass R5 | 36 positive
        decide R5: chose IvitsPlaceSpaceStation (4.0) | top IvitsPlaceSpaceStation (4.0) | 199 candidates, FormFederation 0 (blocked 0) | best fed - | best pass 0.6333333333333258 | others passed 3/3 | after pass R5 | 35 positive
        decide R5: chose Build (3.6666666666666288) | top Build (3.6666666666666288) | 56 candidates, FormFederation 0 (blocked 0) | best fed - | best pass 0.6333333333333258 | others passed 3/3 | after pass R5 | 4 positive
        decide R5: chose ExploreSpaceship (3.2666666666665947) | top ExploreSpaceship (3.2666666666665947) | 25 candidates, FormFederation 0 (blocked 0) | best fed - | best pass 1.3333333333333144 | others passed 3/3 | after pass R5 | 2 positive
        decide R5: chose RebellionGainTechTile (12.447619047619071) | top RebellionGainTechTile (12.447619047619071) | 116 candidates, FormFederation 0 (blocked 0) | best fed - | best pass 0.4999999999999716 | others passed 3/3 | after pass R5 | 39 positive
        decide R5: chose TechTileSpecialAction (2.6666666666666288) | top TechTileSpecialAction (2.6666666666666288) | 20 candidates, FormFederation 0 (blocked 0) | best fed - | best pass 1.3333333333333144 | others passed 3/3 | after pass R5 | 1 positive
        decide R5: chose Pass (44.866666666666674) | top Pass (44.866666666666674) | 21 candidates, FormFederation 0 (blocked 0) | best fed - | best pass 44.866666666666674 | others passed 3/3 | after pass R5 | 0 positive
        decide R5: chose ChooseIncomeOrder (2.6666666666666856) | top ChooseIncomeOrder (2.6666666666666856) | 2 candidates, FormFederation 0 (blocked 0) | best fed - | best pass - | others passed 3/3 | after pass R- | 2 positive
    rollout     flip-229                                 started  70.035 s: 10.346 s, 61 decisions, rank 10.211 s in 60 calls (3170 candidates), select_goal 0.0 s in 8 calls
        value 133.1238095238095, goal acquired False, end round 6, 9 own actions:
        R5 vp 26→26 {"type":"ResearchAdvance","track":"Economy"}
        R5 vp 26→26 {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_coord":null,"bonus_tech_tile":…
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
        decide R5: chose Pass (39.26666666666665) | top Pass (39.26666666666665) | 58 candidates, FormFederation 0 (blocked 0) | best fed - | best pass 39.26666666666665 | others passed 3/3 | after pass R5 | 0 positive
        decide R5: chose ChooseIncomeOrder (3.466666666666697) | top ChooseIncomeOrder (3.466666666666697) | 2 candidates, FormFederation 0 (blocked 0) | best fed - | best pass - | others passed 3/3 | after pass R- | 2 positive
    rollout     root-56                                  started  80.385 s: not finished (cut)
    rollout     tile-action-314-then-Rebellion-Rebellion started  88.774 s: not finished (cut)
    front move [312]: started True, finished True, compared True
    front move [56]: started True, finished False, compared False
    front move [314]: started False, finished False, compared False
```

지표

```json
{
 "created_at": "2026-11-24T11:36:29.508981+09:00",
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
   "wall_seconds": 88.806,
   "index": 312,
   "action": {
    "type": "Upgrade",
    "coord": "-2,4",
    "to": {
     "Academy": "Qic"
    },
    "
```

<sub>agentmaco · 커밋 8512bda · 2026-11-24T11:36:28+09:00 → 2026-11-24T11:37:58+09:00</sub>
