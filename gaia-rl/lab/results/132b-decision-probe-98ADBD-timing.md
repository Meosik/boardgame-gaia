# 132b-decision-probe-98ADBD-timing — 완료

132 정리(E270) 제안 (ㄱ), 코덱스 이상 없음(사용자 2026-11-13 상시 지시): 132와 같은 결정(사용자 방 98ADBD 5라운드, 130 대조 판 move-0의 하이브 첫 행동 = 5번째 결정)을 구간 계측이 든 새 도구(tools/decision_probe.py 7e055ee + stop_reason 기록 d2d05ac)로 다시 묻는 보충 실행. 132는 옛 도구(4d15291)로 돌아 comparison_times·앞에 둔 수의 시작/끝 기록이 없었음. 대국 없음. 상태·앞 5결정 재생·교사(all_tier cap60-p2, 병렬 2)·관심 수 셋(move 0 사용자의 수 = 연구소 -2,4 → 정보 큐브 아카데미 + 「행성의회/아카데미 파워 가치 +1」 타일 / move 1 우주정거장 -1,3 / move 2 같은 아카데미 + 「가이아 광산 3점」 타일)은 132와 같음. 물음 다섯: ① front-nocap(상한 없음, 비교 9, 세 수를 root 목록 맨 앞 — 132와 같은 물음) ② 60초 상한·네 물음 동시(132·130과 같은 부하): user-cap60-1·2(사용자 수의 root 비교를 셋째 자리에) + asis-cap60-1·2(교사 그대로; 구간 기록은 앞에 둔 수가 있는 물음에만 남으므로 이 둘은 부하를 132와 같게 하려는 것이고 선택·끝난 비교 수만 읽음). 132의 asis-nocap은 뺌(앞에 둔 수가 없어 구간 기록이 안 남고 값은 132에 있음). 탐색적 진단, 판정 없음(한 결정; 시간은 부하·기계에 따라 달라지고 상한 물음은 두 번씩; 계측 자체가 시간을 늘릴 수 있음 — 132의 같은 물음 시간과 나란히 적음). 읽는 법(사전 등록): (a) front-nocap의 비교별 시간 — 정거장 계획 비교(132: 약 82–89초)에서 select_goal과 rollout이 각각 몇 초인지, rollout 안의 순위 매기기(Policies.rank) 호출 수·시간·순위 매긴 후보 수, select_goal 호출 수·시간. 순위 매기기가 그 비교 시간의 대부분(작업 트리 스모크: 99%, 후보 1개당 약 3.3ms, select_goal 9번 88.5초)이면 「계획 비교가 느린 것은 자기 차례마다 순위를 여러 번 다시 매겨서」가 lab 빌드에서도 성립 → 다음은 한 비교 안에서 순위 재사용 설계(E270 (ㄴ)); 아니면 그 가설은 lab 빌드에서 성립 안 함으로 적고 시간이 든 구간을 그대로 적은 뒤 (ㄴ)을 다시 설계. 「대부분」의 기준값은 두지 않음 — 비율을 그대로 적음. (b) user-cap60 두 번 — 사용자 수(root-312) 비교가 60초 안에 시작됐는지·워커에서 끝났는지(front_comparisons의 started·finished)와 비교 결과에 들었는지(compared). 끝났는데 결과에 없으면 132의 읽기(「결과를 순서대로 받기 때문에 정거장 계획 뒤의 비교는 끝나도 읽히지 않음」)가 확인됨; 끝나지 못했으면 그 읽기는 이 부하에서 확인 안 됨(뒤 비교도 60초 안에 못 끝남)으로 적음; 두 번이 갈리면 부하 의존으로 적음. (c) front-nocap의 stop_reason과 예측 작업 순서(앞 12개) — 132에서 비교 9개 예정이 4개에서 끝난 이유가 수렴 중단(stable completed alternatives)인지(132는 코드로만 추정). (d) 값·선택이 132와 같은지(현재 수 131.46 · 정거장 계획 138.60 · root-사용자 수 133.60 · 아카데미 + 가이아 광산 타일 → 식민 125.83, 선택 = 정거장; 상한 물음은 끝난 비교 1개·연방 토큰 다시 받기) — 다르면 계측이 결정을 바꾼 것일 수 있어 구간 시간을 결과로 쓰지 않고 원인을 먼저 봄. 건강 기준: 종료 코드 0, failures 빈 목록(물음 다섯 모두 답), digest_matches_log true, 폴백 타임아웃 0, 앞에 둔 수가 있는 세 물음에 comparison_times가 있음. 예상 ≈ 5–15분(132는 여섯 물음에 3분 55초; 계측 부담 포함), 제한 2시간.

종료 코드 0

```
move 2: [314] rank 260 of 340 {"type":"Upgrade","coord":"-2,4","to":{"Academy":"Qic"},"tech_tile_choice":{"kind":"Standard","tile":8,"advance_track":…
ask front-nocap: budget 9, cap None, front [312, 56, 314] → [56] {"type":"IvitsPlaceSpaceStation","coord":"-1,3"} (Ivits-station-then-extend-federation; move 1; 4 compared, 84.972 s, capped False, published at [1.464, 13.053, 84.934, 84.935, 84.937, 84.938], stages {'bind_check': 0.002, 'root_rank': 1.357, 'planned_tasks': 0.105, 'prefetch': 1.462, 'drop_unfinished': 0.025, 'parallel_search': 84.964, 'search_call': 84.964, 'state_check': 0.002}, stop 'stable completed alternatives; no artificial wait')
    current-choice                                 131.46 done [272] {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_…
    Ivits-station-then-extend-federation           138.60 done [56] = move 1 {"type":"IvitsPlaceSpaceStation","coord":"-1,3"}
    root-312                                       133.60 done [312] = move 0 {"type":"Upgrade","coord":"-2,4","to":{"Academy":"Qic"},"tech_tile_ch…
    tile-action-314-then-colony@-9,-2              120.65 done [314] = move 2 {"type":"Upgrade","coord":"-2,4","to":{"Academy":"Qic"},"tech_tile_ch…
    task order (522 planned): current-choice | Ivits-station-then-extend-federation | root-312 | tile-action-314-then-colony@-9,-2 | flip-229 | root-56 | tile-action-314-then-Rebellion-RebellionGainTechTile-then-expand | track-plan-Science-2 | root-314 | tile-action-314-then-colony@-1,0 | Qic@-8,1 | root-274
    rollout     current-choice                           started   1.479 s: 11.576 s, 61 decisions, rank 11.484 s in 60 calls (3664 candidates), select_goal 0.001 s in 8 calls
    select_goal Ivits-station-then-extend-federation     started   1.484 s: 0.0 s
    rollout     Ivits-station-then-extend-federation     started   1.484 s: 83.452 s, 62 decisions, rank 82.902 s in 177 calls (24785 candidates), select_goal 72.962 s in 9 calls
    rollout     root-312                                 started  13.059 s: 11.54 s, 62 decisions, rank 11.44 s in 61 calls (3674 candidates), select_goal 0.001 s in 8 calls
    rollout     tile-action-314-then-colony@-9,-2        started  24.603 s: 46.696 s, 62 decisions, rank 46.366 s in 135 calls (14124 candidates), select_goal 37.125 s in 8 calls
    rollout     flip-229                                 started  71.303 s: 10.127 s, 61 decisions, rank 10.028 s in 60 calls (3170 candidates), select_goal 0.0 s in 8 calls
    rollout     root-56                                  started  81.433 s: not finished (cut)
    rollout     tile-action-314-then-Rebellion-Rebellion started   84.94 s: not finished (cut)
    front move [312]: started True, finished True, compared True
    front move [56]: started True, finished False, compared False
    front move [314]: started False, finished False, compared False
ask asis-cap60-1: budget 4, cap 60.0, front [] → [272] {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_coord":null,"bonus_tech_tile":13,"bonus_research_t… (current-choice; move None; 1 compared, 60.04 s, capped True, published at [1.89, 16.492, 60.0], stages {'bind_check': 0.001, 'root_rank': 1.229, 'planned_tasks': 0.659, 'prefetch': 1.889, 'drop_unfinished': 0.033, 'parallel_search': 60.033, 'search_call': 60.033, 'state_check': 0.002}, stop 'deadline; partially evaluated route remains unknown')
    current-choice                                 131.46 done [272] {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_…
ask asis-cap60-2: budget 4, cap 60.0, front [] → [272] {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_coord":null,"bonus_tech_tile":13,"bonus_research_t… (current-choice; move None; 1 compared, 60.038 s, capped True, published at [1.875, 16.435, 60.0], stages {'bind_check': 0.002, 'root_rank': 1.226, 'planned_tasks': 0.647, 'prefetch': 1.873, 'drop_unfinished': 0.031, 'parallel_search': 60.031, 'search_call': 60.031, 'state_check': 0.002}, stop 'deadline; partially evaluated route remains unknown')
    current-choice                                 131.46 done [272] {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_…
ask user-cap60-1: budget 4, cap 60.0, front [312] → [272] {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_coord":null,"bonus_tech_tile":13,"bonus_research_t… (current-choice; move None; 1 compared, 60.039 s, capped True, published at [1.326, 16.329, 60.0], stages {'bind_check': 0.001, 'root_rank': 1.219, 'planned_tasks': 0.105, 'prefetch': 1.325, 'drop_unfinished': 0.033, 'parallel_search': 60.033, 'search_call': 60.033, 'state_check': 0.002}, stop 'deadline; partially evaluated route remains unknown')
    current-choice                                 131.46 done [272] {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_…
    task order (522 planned): current-choice | Ivits-station-then-extend-federation | root-312 | tile-action-314-then-colony@-8,-2 | flip-229 | root-274 | tile-action-314-then-Rebellion-RebellionGainTechTile-then-expand | track-plan-Science-2 | root-228 | tile-action-314-then-colony@-9,-2 | Qic@-8,1 | root-56
    rollout     current-choice                           started   1.344 s: 14.985 s, 61 decisions, rank 14.87 s in 60 calls (3664 candidates), select_goal 0.001 s in 8 calls
    select_goal Ivits-station-then-extend-federation     started   1.349 s: 0.0 s
    rollout     Ivits-station-then-extend-federation     started   1.349 s: not finished (cut)
    rollout     root-312                                 started  16.335 s: 14.45 s, 62 decisions, rank 14.326 s in 61 calls (3674 candidates), select_goal 0.001 s in 8 calls
    rollout     tile-action-314-then-colony@-8,-2        started  30.788 s: not finished (cut)
    front move [312]: started True, finished True, compared False
ask user-cap60-2: budget 4, cap 60.0, front [312] → [272] {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_coord":null,"bonus_tech_tile":13,"bonus_research_t… (current-choice; move None; 1 compared, 60.038 s, capped True, published at [1.335, 16.213, 60.0], stages {'bind_check': 0.001, 'root_rank': 1.228, 'planned_tasks': 0.105, 'prefetch': 1.334, 'drop_unfinished': 0.032, 'parallel_search': 60.032, 'search_call': 60.033, 'state_check': 0.002}, stop 'deadline; partially evaluated route remains unknown')
    current-choice                                 131.46 done [272] {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_…
    task order (522 planned): current-choice | Ivits-station-then-extend-federation | root-312 | tile-action-314-then-colony@-9,-2 | flip-229 | root-274 | tile-action-314-then-Rebellion-RebellionGainTechTile-then-expand | track-plan-Science-2 | root-228 | tile-action-314-then-colony@-1,0 | Qic@-8,1 | root-56
    rollout     current-choice                           started   1.347 s: 14.866 s, 61 decisions, rank 14.746 s in 60 calls (3664 candidates), select_goal 0.001 s in 8 calls
    select_goal Ivits-station-then-extend-federation     started   1.353 s: 0.0 s
    rollout     Ivits-station-then-extend-federation     started   1.353 s: not finished (cut)
    rollout     root-312                                 started  16.218 s: 15.14 s, 62 decisions, rank 15.01 s in 61 calls (3674 candidates), select_goal 0.001 s in 8 calls
    rollout     tile-action-314-then-colony@-9,-2        started  31.362 s: not finished (cut)
    front move [312]: started True, finished True, compared False
```

지표

```json
{
 "created_at": "2026-11-23T17:11:45.220462+09:00",
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
   "wall_seconds": 84.972,
   "index": 56,
   "action": {
    "type": "IvitsPlaceSpaceStation",
    "coord": "-1,3"
   },
   "chose_move": 1,
   "selected": "Ivits-st
```

<sub>agentmaco · 커밋 0e227e8 · 2026-11-23T17:11:42+09:00 → 2026-11-23T17:14:10+09:00</sub>
