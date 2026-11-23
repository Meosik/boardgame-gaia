# 132-decision-probe-98ADBD — 완료

130 정리(E268) 제안 (ㄱ), 코덱스 토론 1/1 수용 뒤 이상 없음(사용자 2026-11-13 상시 지시), 사용자 2026-11-23 「AI가 불필요한 수를 너무 많이 고민하는게 아닌가?」의 집계 포함: 사용자 방 98ADBD 5라운드에서 130 대조 판(move-0)의 하이브 첫 행동 결정(5번째 결정, 실제로는 60초 상한에 끊겨 대안 비교 0개 → 연방 토큰 다시 받기)을 lab 빌드에서 다시 묻는다. 대국 없음. 도구 tools/decision_probe.py: 130의 states/round-5.json + move-0 판의 앞 결정 5개 재생으로 그 결정에 온 뒤(상태 digest를 130 로그의 그 줄과 비교), 물음마다 새 교사 워커(teacher_ab.Worker, 130과 같은 교사 all_tier cap60-p2·병렬 2·시드 라벨)가 한 번 고른다. 관심 수 셋: move 0 사용자의 수(연구소 -2,4 → 정보 큐브 아카데미 + 「행성의회/아카데미 파워 가치 +1」 타일) / move 1 우주정거장 -1,3 / move 2 같은 아카데미 + 「가이아 광산 3점」 타일. 물음 여섯: ① 상한 없음 — asis-nocap(비교 4, 교사 그대로 = 기존 비교 후보의 같은 빌드 평가값) · front-nocap(비교 9, 세 수의 root 비교를 root 목록 맨 앞에 = 비교 순서 3·6·9번째; 기존 control·계획 목표·점수 짝은 그대로) ② 60초 상한, 네 물음 동시(130의 네 판 동시와 같은 부하) — asis-cap60-1·2(교사 그대로 두 번) · user-cap60-1·2(사용자 수의 root 비교를 root 목록 맨 앞 = 셋째 비교, 두 번) ③ 그 결정의 후보를 행동 종류별로 세고, 물음마다 비교가 끝난 시각(published_at)·구간 시간. 탐색적 진단, 판정 없음(한 결정, 값은 수입 1회 앞까지의 계획 예측이지 대국 결과가 아님; 상한 물음은 부하에 따라 달라지고 두 번씩뿐). 읽는 법(사전 등록): ① 후보 누락 확인 — front-nocap에서 root-사용자 수의 값이 control·정거장 계획·다른 비교보다 높으면(그 물음의 선택이 사용자 수) 「비교에 오르면 뽑힌다 = 후보 순위에서 밀린 것」 단서; 낮으면 이 빌드의 평가가 사용자 수를 선호하지 않음 → 130의 181은 평가(롤아웃이 「다음 수에 연방」을 따라가지 못함)의 문제이거나 잡음이라 순위 수정 대상 아님 → 다음은 그 롤아웃 explain 또는 흩어짐 측정(반복 수는 사용자 수치). 세 수의 기본 순위(move rank)도 같이 적는다. ② 60초에서 — asis-cap60이 130의 실제 결정(연방 토큰 다시 받기, 끝난 비교 1)을 재현하는지; user-cap60 두 번에서 root-사용자 수 비교가 60초 안에 끝났는지(compared에 있는지)·선택됐는지. ①에서 최고 + ②에서 두 번 다 선택 → 순위 수정 후보; ①에서 최고지만 ②에서 평가를 못 끝냄 → 순위만 고쳐서는 부족, 상한(첫 비교가 끝나는 시간)이 함께 문제; 두 번이 갈리면 부하 의존으로 적음. 주의: root 목록 맨 앞은 「root 중 2위」에 해당(셋째 비교) — 순위 수정이 사용자 수를 전체 1위로 만들면 그 수가 control이 되어 비교 1개로도 뽑히는데 그 경우는 이 실행이 재지 않음. ③ 후보 종류별 수와 비교 한 번의 시간은 사용자 질문의 자료로 적음(판정 아님). 봇 턴 스모크(작업 트리 빌드, lab 빌드와 다름 — 결과 아님, 예상으로만): 후보 412개(업그레이드 127 = 정보 큐브 아카데미 62 + 지식 아카데미 62 + 교역소 3, 우주정거장 125, 파워 행동 50, 자유 행동 33, 그 외 77), 사용자 수 기본 순위 247/402위·정거장 15위; 상한 없이 비교 3개(control 131.46 / 정거장 계획 138.60 / root-사용자 수 122.65)에 95초 — 그 빌드에서는 사용자 수가 가장 낮았으나 그 빌드는 아카데미 뒤 연방 후보가 0개(E267)라 lab 빌드는 다를 수 있음 = ①이 확인할 것; 상한 25초 물음 둘은 control 하나만 끝남. 건강 기준: 종료 코드 0, metrics.json failures 빈 목록(물음 여섯 모두 답), digest_matches_log true(false면 130의 그 결정이 아니라 「이 빌드의 그 자리」로만 읽음), 폴백 타임아웃 0. 예상 ≈ 15–30분(상한 없는 물음 둘이 대부분), 제한 2시간.

종료 코드 0

```
{"label": "asis-nocap", "index": 56, "chose_move": 1, "selected": "Ivits-station-then-extend-federation", "completed_comparisons": 4, "wall_seconds": 84.246, "error": null}
{"label": "front-nocap", "index": 56, "chose_move": 1, "selected": "Ivits-station-then-extend-federation", "completed_comparisons": 4, "wall_seconds": 89.925, "error": null}
{"label": "asis-cap60-1", "index": 272, "chose_move": null, "selected": "current-choice", "completed_comparisons": 1, "wall_seconds": 60.036, "error": null}
{"label": "asis-cap60-2", "index": 272, "chose_move": null, "selected": "current-choice", "completed_comparisons": 1, "wall_seconds": 60.04, "error": null}
{"label": "user-cap60-2", "index": 272, "chose_move": null, "selected": "current-choice", "completed_comparisons": 1, "wall_seconds": 60.04, "error": null}
{"label": "user-cap60-1", "index": 272, "chose_move": null, "selected": "current-choice", "completed_comparisons": 1, "wall_seconds": 60.037, "error": null}
round 5 seat 0 Ivits: 350 candidates, digest matches the log: True
candidates by type: IvitsPlaceSpaceStation 125, Upgrade 65, PowerAction 50, FreeAction 33, SpaceshipCreditTerraform 19, TwilightRangeBuild 15, TwilightReplayFederationToken 13, Build 11, ResearchAdvance 6, ExamineArtifact 4, Pass 3, ExploreSpaceship 2, TwilightRangeExploreSpaceship 2, TFMarsTechBonus 1, TechTileSpecialAction 1
upgrades by target: {"Academy": "Qic"} 62, TradingStation 3
logged choice: [272] {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_coord":null,"bonus_tech_tile":13,"bonus_research_t… (current-choice, 60.035 s, 1 compared)
move 0: [312] rank 230 of 340 {"type":"Upgrade","coord":"-2,4","to":{"Academy":"Qic"},"tech_tile_choice":{"kind":"Standard","tile":6,"advance_track":…
move 1: [56] rank 15 of 340 {"type":"IvitsPlaceSpaceStation","coord":"-1,3"}
move 2: [314] rank 260 of 340 {"type":"Upgrade","coord":"-2,4","to":{"Academy":"Qic"},"tech_tile_choice":{"kind":"Standard","tile":8,"advance_track":…
ask asis-nocap: budget 4, cap None, front [] → [56] {"type":"IvitsPlaceSpaceStation","coord":"-1,3"} (Ivits-station-then-extend-federation; move 1; 4 compared, 84.246 s, capped False, published at [1.898, 13.61, 84.239, 84.24, 84.241, 84.242], stages {'bind_check': 0.002, 'root_rank': 1.306, 'planned_tasks': 0.589, 'prefetch': 1.896, 'drop_unfinished': 0.0, 'parallel_search': 84.241, 'search_call': 84.241, 'state_check': 0.001})
    current-choice                                 131.46 done [272] {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_…
    Ivits-station-then-extend-federation           138.60 done [56] = move 1 {"type":"IvitsPlaceSpaceStation","coord":"-1,3"}
    root-274                                       131.46 done [274] {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_…
    tile-action-314-then-colony@-8,-2              123.98 done [314] = move 2 {"type":"Upgrade","coord":"-2,4","to":{"Academy":"Qic"},"tech_tile_ch…
ask front-nocap: budget 9, cap None, front [312, 56, 314] → [56] {"type":"IvitsPlaceSpaceStation","coord":"-1,3"} (Ivits-station-then-extend-federation; move 1; 4 compared, 89.925 s, capped False, published at [1.285, 13.592, 89.892, 89.893, 89.894, 89.895], stages {'bind_check': 0.001, 'root_rank': 1.178, 'planned_tasks': 0.105, 'prefetch': 1.283, 'drop_unfinished': 0.024, 'parallel_search': 89.918, 'search_call': 89.919, 'state_check': 0.002})
    current-choice                                 131.46 done [272] {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_…
    Ivits-station-then-extend-federation           138.60 done [56] = move 1 {"type":"IvitsPlaceSpaceStation","coord":"-1,3"}
    root-312                                       133.60 done [312] = move 0 {"type":"Upgrade","coord":"-2,4","to":{"Academy":"Qic"},"tech_tile_ch…
    tile-action-314-then-colony@3,3                125.83 done [314] = move 2 {"type":"Upgrade","coord":"-2,4","to":{"Academy":"Qic"},"tech_tile_ch…
ask asis-cap60-1: budget 4, cap 60.0, front [] → [272] {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_coord":null,"bonus_tech_tile":13,"bonus_research_t… (current-choice; move None; 1 compared, 60.036 s, capped True, published at [1.964, 16.726, 60.0], stages {'bind_check': 0.001, 'root_rank': 1.288, 'planned_tasks': 0.673, 'prefetch': 1.962, 'drop_unfinished': 0.029, 'parallel_search': 60.029, 'search_call': 60.029, 'state_check': 0.002})
    current-choice                                 131.46 done [272] {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_…
ask asis-cap60-2: budget 4, cap 60.0, front [] → [272] {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_coord":null,"bonus_tech_tile":13,"bonus_research_t… (current-choice; move None; 1 compared, 60.04 s, capped True, published at [2.038, 17.624, 60.0], stages {'bind_check': 0.002, 'root_rank': 1.303, 'planned_tasks': 0.732, 'prefetch': 2.036, 'drop_unfinished': 0.033, 'parallel_search': 60.032, 'search_call': 60.033, 'state_check': 0.002})
    current-choice                                 131.46 done [272] {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_…
ask user-cap60-1: budget 4, cap 60.0, front [312] → [272] {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_coord":null,"bonus_tech_tile":13,"bonus_research_t… (current-choice; move None; 1 compared, 60.037 s, capped True, published at [1.419, 16.32, 60.0], stages {'bind_check': 0.001, 'root_rank': 1.298, 'planned_tasks': 0.118, 'prefetch': 1.417, 'drop_unfinished': 0.031, 'parallel_search': 60.031, 'search_call': 60.031, 'state_check': 0.002})
    current-choice                                 131.46 done [272] {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_…
ask user-cap60-2: budget 4, cap 60.0, front [312] → [272] {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_coord":null,"bonus_tech_tile":13,"bonus_research_t… (current-choice; move None; 1 compared, 60.04 s, capped True, published at [1.405, 16.188, 60.0], stages {'bind_check': 0.001, 'root_rank': 1.291, 'planned_tasks': 0.112, 'prefetch': 1.404, 'drop_unfinished': 0.033, 'parallel_search': 60.033, 'search_call': 60.033, 'state_check': 0.002})
    current-choice                                 131.46 done [272] {"type":"TwilightReplayFederationToken","token_kind":12,"bonus_build_…
```

지표

```json
{
 "created_at": "2026-11-23T16:52:39.086014+09:00",
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
   "label": "asis-nocap",
   "comparisons": 4,
   "cap": null,
   "front": [],
   "front_indices": [],
   "wall_seconds": 84.246,
   "index": 56,
   "action": {
    "type": "IvitsPlaceSpaceStation",
    "coord": "-1,3"
   },
   "chose_move": 1,
   "selected": "Ivits-station-then-extend-federation",
   "completed_compariso
```

<sub>agentmaco · 커밋 2410845 · 2026-11-23T16:52:38+09:00 → 2026-11-23T16:56:33+09:00</sub>
