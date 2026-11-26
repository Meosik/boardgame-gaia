# 143-test-fedplan-former — 실패

사용자 11-27 「이클립스 혹은 포머를 던질 예정」: fed_plan 쓸만한 땅에 차원 변형(가이드 트랙에 가이아가 있는 종족 GAIA_RIDERS, 또는 포머가 남은 종족)과 소행성(포머가 남음, 또는 이클립스 진입·맞춤 함선)을 더함; 연방 계획의 광산 단계가 소행성에서 EclipseAsteroidMine도 인정(토론 1/1: 동결본 대신 teacher_patches.install_eclipse_colony, fed_plan 부품 켠 플레이어만). 봇 턴에서 python 실행이 막혀 단위 테스트만 lab에서 돌린다(실험 아님, 판정 없음). 건강 기준: 종료 코드 0, test_teacher_patches 전부 통과(162 예상, 새 test_fed_plan_goals_count_transdim_and_asteroid_when_former_or_eclipse_is_planned · test_eclipse_colony_counts_the_eclipse_asteroid_mine_only_with_fed_plan 포함). 실패하면 정리 턴에 고친다. 예상 1분, 제한 0.25시간.

종료 코드 1

```
test_unchanged_when_the_next_phase_is_not_the_action_phase (test_teacher_patches.ShipNowTests.test_unchanged_when_the_next_phase_is_not_the_action_phase) ... ok
test_unchanged_when_the_round_changes (test_teacher_patches.ShipNowTests.test_unchanged_when_the_round_changes) ... ok
test_unchanged_with_the_flag_off (test_teacher_patches.ShipNowTests.test_unchanged_with_the_flag_off) ... ok
test_booster_pass_vp_matches_native_passes (test_teacher_patches.SymmetricPassTests.test_booster_pass_vp_matches_native_passes) ... ok
test_charge_phase_keeps_the_pass_terms_while_a_charge_is_pending (test_teacher_patches.SymmetricPassTests.test_charge_phase_keeps_the_pass_terms_while_a_charge_is_pending) ... ok
test_factory_rebinds_every_user_of_potential (test_teacher_patches.SymmetricPassTests.test_factory_rebinds_every_user_of_potential) ... ok
test_only_unpassed_action_phase_states_gain_the_pass_terms (test_teacher_patches.SymmetricPassTests.test_only_unpassed_action_phase_states_gain_the_pass_terms) ... ok

======================================================================
FAIL: test_faction_guide_parts_are_on_only_with_the_guide_flag (test_teacher_patches.OpeningBudgetTests.test_faction_guide_parts_are_on_only_with_the_guide_flag)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/sohegi/projects/gaia-lab/gaia-rl/tools/test_teacher_patches.py", line 452, in test_faction_guide_parts_are_on_only_with_the_guide_flag
    self.assertEqual(tp._faction_parts('BalTaks'), {'track_set'})
AssertionError: Items in the first set but not the second:
'fed_plan'

======================================================================
FAIL: test_faction_parts_come_from_the_tables (test_teacher_patches.OpeningBudgetTests.test_faction_parts_come_from_the_tables)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/sohegi/projects/gaia-lab/gaia-rl/tools/test_teacher_patches.py", line 394, in test_faction_parts_come_from_the_tables
    self.assertEqual(tp._faction_parts('Xenos'), set())
AssertionError: Items in the first set but not the second:
'fed_plan'

======================================================================
FAIL: test_fed_plan_goals_count_transdim_and_asteroid_when_former_or_eclipse_is_planned (test_teacher_patches.OpeningBudgetTests.test_fed_plan_goals_count_transdim_and_asteroid_when_former_or_eclipse_is_planned)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/sohegi/projects/gaia-lab/gaia-rl/tools/test_teacher_patches.py", line 874, in test_fed_plan_goals_count_transdim_and_asteroid_when_former_or_eclipse_is_planned
    self.assertEqual(colonies('Terrans'), {'2,1'})                      # (a) Gaia-track faction, Transdim only
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Items in the second set but not the first:
'2,1'

----------------------------------------------------------------------
Ran 162 tests in 10.120s

FAILED (failures=3)
```

<sub>agentmaco · 커밋 adf1a13 · 2026-11-27T02:00:42+09:00 → 2026-11-27T02:00:53+09:00</sub>
