# 132c-decision-probe-98ADBD-actions — 완료

E273 제안 (ㄱ)(= E272에서 먼저 하기로 한 rollout 행동 기록), 사용자 2026-11-23 「다음」: 132·132b와 같은 결정(사용자 방 98ADBD 5라운드, 130 대조 판 move-0의 하이브 첫 행동 = 5번째 결정)을 rollout 행동 기록이 든 도구(tools/decision_probe.py 186b0c4: 끝난 rollout마다 값·목표 달성 여부 goal_acquired·남은 목표·끝난 라운드·하이브 자신의 행동 목록(라운드, 행동, 행동 전후 VP))로 상한 없이 다시 물음. 교사는 그대로(rollout이 돌려준 결과를 읽어 기록만 함). 대국 없음. 상태·앞 5결정 재생·교사(all_tier cap60-p2, 병렬 2)·관심 수 셋(move 0 사용자의 수 = 연구소 -2,4 → 정보 큐브 아카데미 + 「행성의회/아카데미 파워 가치 +1」 타일 / move 1 우주정거장 -1,3 / move 2 같은 아카데미 + 「가이아 광산 3점」 타일)은 132b와 같음. 물음 둘: front-nocap-1·2(상한 없음, 비교 9, 세 수를 root 목록 맨 앞 — 132b의 front-nocap과 같은 물음을 차례로 두 번). 탐색적 진단, 판정 없음(한 결정; rollout은 교사의 싼 이어 두기이고 평가 창은 사이클 132에 적은 대로 수입 1회 앞까지). 읽는 법(사전 등록): (a) root-사용자 수(root-312) rollout — 하이브 행동 목록에 FormFederation이 있는지, 있으면 몇 번째 자기 행동·몇 라운드·그 행동의 VP 변화. 사용자의 실제 수순은 아카데미 바로 다음 수에 연방(+7)이었음(사이클 132 흐름 대조 표). 있으면 「교사의 이어 두기도 사용자 수 뒤에 연방을 둠 — 133.60은 그 연방이 든 값」, 없으면 「133.60은 연방 없이 매긴 값 — 사용자의 흐름(아카데미 → 연방)은 이 평가에 안 들어감」으로 적음. (b) 정거장 → 연방 계획 rollout — 행동 순서, FormFederation의 위치·라운드·VP 변화, goal_acquired·남은 목표, 정거장과 연방 사이에 자기 행동이 몇 개 끼는지. (c) 현재 수(연방 토큰 다시 받기) rollout — 행동 순서를 대조로 그대로 적음. (d) 넷째 비교(아카데미 + 가이아 광산 3점 타일 → 식민; 132b에서 식민 좌표가 물음마다 달라짐)는 그 작업의 기록으로만 적음. (e) 값·선택이 132·132b와 같은지(현재 수 131.46 · 정거장 계획 138.60 · root-사용자 수 133.60, 선택 = 정거장) — 다르면 기록 추가가 결정을 바꾼 것일 수 있어 행동 목록을 결과로 쓰지 않고 원인부터 봄. (f) 두 물음의 행동 목록이 (a)–(c) 세 비교에서 서로 같은지 — 다르면 다른 지점을 그대로 적고 한 번의 목록을 대표로 쓰지 않음. 한정: 어느 값이 높든 뜻은 상한 없는 평가의 선호까지(E272 둘째 토론) — 60초 상한의 발표·선택은 이 실행이 묻지 않음(132b에 기록 있음); 「아카데미 + 파워 가치 타일 → 연방」 계획 대 계획 비교는 이 실행 뒤 따로. 건강 기준: 종료 코드 0, failures 빈 목록(물음 둘 모두 답), digest_matches_log true, 폴백 타임아웃 0, 두 물음 모두 끝난 rollout의 comparison_times에 actions가 있음. 예상 ≈ 3–10분(132b의 front-nocap 한 번이 85초), 제한 2시간.

종료 코드 0

```
        R5 vp 34→49 {"type":"Pass","booster_id":12}
        R5 vp 49→49 {"type":"ChooseIncomeOrder","charge_first":false}
    rollout     root-312                                 started  13.029 s: 11.73 s, 62 decisions, rank 11.628 s in 61 calls (3674 candidates), select_goal 0.001 s in 8 calls
        value 133.6, goal acquired False, end round 6, 9 own actions:
        R5 vp 26→26 {"type":"Upgrade","coord":"-2,4","to":{"Academy":"Qic"},"tech_tile_choice":{"kind":"Standard","tile…
        R5 vp 26→26 {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_coord":null,"bonus_tech_tile":…
        R5 vp 26→34 {"type":"FormFederation","hexes":["-8,5","-7,4"],"satellite_hexes":["-7,3"],"token":{"source":"Supp…
        R5 vp 34→34 {"type":"ResearchAdvance","track":"ArtificialIntelligence"}
        R5 vp 34→34 {"type":"ResearchAdvance","track":"Science"}
        R5 vp 34→34 {"type":"AcademyQicAction"}
        R5 vp 34→34 {"type":"IvitsPlaceSpaceStation","coord":"-1,3"}
        R5 vp 34→46 {"type":"Pass","booster_id":12}
        R5 vp 46→46 {"type":"ChooseIncomeOrder","charge_first":false}
    rollout     tile-action-314-then-colony@-4,-3        started  24.763 s: 47.2 s, 62 decisions, rank 46.859 s in 135 calls (14124 candidates), select_goal 37.566 s in 8 calls
        value 120.64761904761903, goal acquired False, end round 6, 9 own actions:
        R5 vp 26→26 {"type":"Upgrade","coord":"-2,4","to":{"Academy":"Qic"},"tech_tile_choice":{"kind":"Standard","tile…
        R5 vp 26→26 {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_coord":null,"bonus_tech_tile":…
        R5 vp 26→26 {"type":"ResearchAdvance","track":"GaiaProject"}
        R5 vp 26→26 {"type":"TwilightRangeGaiaFormation","coord":"-4,-3"}
        R5 vp 26→26 {"type":"ResearchAdvance","track":"ArtificialIntelligence"}
        R5 vp 26→26 {"type":"AcademyQicAction"}
        R5 vp 26→26 {"type":"IvitsPlaceSpaceStation","coord":"-1,3"}
        R5 vp 26→35 {"type":"Pass","booster_id":12}
        R5 vp 35→35 {"type":"ChooseIncomeOrder","charge_first":false}
    rollout     flip-229                                 started  71.967 s: 10.242 s, 61 decisions, rank 10.142 s in 60 calls (3170 candidates), select_goal 0.0 s in 8 calls
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
    rollout     root-56                                  started  82.213 s: not finished (cut)
    rollout     tile-action-314-then-Rebellion-Rebellion started  84.366 s: not finished (cut)
    front move [312]: started True, finished True, compared True
    front move [56]: started True, finished False, compared False
    front move [314]: started False, finished False, compared False
```

지표

```json
{
 "created_at": "2026-11-23T21:29:48.562607+09:00",
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
   "label": "front-nocap-1",
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
   "wall_seconds": 85.773,
   "index": 56,
   "action": {
    "type": "IvitsPlaceSpaceStation",
    "coord": "-1,3"
   },
   "chose_move": 1,
   "selected": "Ivits-
```

<sub>agentmaco · 커밋 e70fcb6 · 2026-11-23T21:29:48+09:00 → 2026-11-23T21:32:39+09:00</sub>
