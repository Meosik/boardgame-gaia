# 144-test-fedplan-budget — 실패

사용자 11-27 「광산 만들기 할때 썻던거 그대로 연방 계획에 재활용」(코덱스 이상 없음): ① _plan_cost가 광산 단계마다 가상 광산을 더함(다음 광산의 사거리 QIC 중복 계산 수정 — 광산 2개 이상 계획 전부에 적용) ② 예산 검사(E86 plan_affordable) 대상에 federation-plan-* 추가 ③ 143 실패 3건 원인(_guide에 fed_plan 기본값이 없어 테스트 사이에 켜진 채 남음) 수정 + 143 이후 차원 변형 기준 변경(533652b) 확인. 봇 턴에서 python 실행이 막혀 단위 테스트만 lab에서 돌린다(실험 아님, 판정 없음). 건강 기준: 종료 코드 0, test_teacher_patches 전부 통과(164 예상, 새 test_plan_cost_measures_the_next_mine_from_the_planned_one · test_plan_affordable_drops_a_federation_plan_the_budget_cannot_pay 포함). 실패하면 정리 턴에 고친다. 예상 1분, 제한 0.25시간.

종료 코드 1

```
test_unchanged_without_a_positive_non_pass_candidate (test_teacher_patches.PassLastTests.test_unchanged_without_a_positive_non_pass_candidate) ... ok
test_blocked_before_and_open_after_counts_like_a_new_one (test_teacher_patches.ShipNowTests.test_blocked_before_and_open_after_counts_like_a_new_one) ... ok
test_high_before_and_after_is_not_counted (test_teacher_patches.ShipNowTests.test_high_before_and_after_is_not_counted) ... ok
test_install_wraps_once (test_teacher_patches.ShipNowTests.test_install_wraps_once) ... ok
test_lowered_to_the_best_opened_action (test_teacher_patches.ShipNowTests.test_lowered_to_the_best_opened_action) ... ok
test_negative_raise_stays_negative (test_teacher_patches.ShipNowTests.test_negative_raise_stays_negative) ... ok
test_nothing_opened_above_zero (test_teacher_patches.ShipNowTests.test_nothing_opened_above_zero) ... ok
test_partial_rise_counts (test_teacher_patches.ShipNowTests.test_partial_rise_counts) ... ok
test_raised_candidate_above_the_share_leaves_the_score (test_teacher_patches.ShipNowTests.test_raised_candidate_above_the_share_leaves_the_score) ... ok
test_rank_before_is_used_and_asked_once (test_teacher_patches.ShipNowTests.test_rank_before_is_used_and_asked_once) ... ok
test_rank_before_not_asked_when_another_seat_moves_next (test_teacher_patches.ShipNowTests.test_rank_before_not_asked_when_another_seat_moves_next) ... ok
test_rise_bigger_than_the_after_score_counts_the_after_score (test_teacher_patches.ShipNowTests.test_rise_bigger_than_the_after_score_counts_the_after_score) ... ok
test_share_without_lf_tables (test_teacher_patches.ShipNowTests.test_share_without_lf_tables) ... ok
test_spec_file_names_the_factory_and_matches_the_base_spec (test_teacher_patches.ShipNowTests.test_spec_file_names_the_factory_and_matches_the_base_spec) ... ok
test_unchanged_outside_the_action_phase (test_teacher_patches.ShipNowTests.test_unchanged_outside_the_action_phase) ... ok
test_unchanged_when_an_opened_action_scores_the_share (test_teacher_patches.ShipNowTests.test_unchanged_when_an_opened_action_scores_the_share) ... ok
test_unchanged_when_another_seat_moves_next (test_teacher_patches.ShipNowTests.test_unchanged_when_another_seat_moves_next) ... ok
test_unchanged_when_the_entry_scores_nothing_or_is_blocked (test_teacher_patches.ShipNowTests.test_unchanged_when_the_entry_scores_nothing_or_is_blocked) ... ok
test_unchanged_when_the_next_phase_is_not_the_action_phase (test_teacher_patches.ShipNowTests.test_unchanged_when_the_next_phase_is_not_the_action_phase) ... ok
test_unchanged_when_the_round_changes (test_teacher_patches.ShipNowTests.test_unchanged_when_the_round_changes) ... ok
test_unchanged_with_the_flag_off (test_teacher_patches.ShipNowTests.test_unchanged_with_the_flag_off) ... ok
test_booster_pass_vp_matches_native_passes (test_teacher_patches.SymmetricPassTests.test_booster_pass_vp_matches_native_passes) ... ok
test_charge_phase_keeps_the_pass_terms_while_a_charge_is_pending (test_teacher_patches.SymmetricPassTests.test_charge_phase_keeps_the_pass_terms_while_a_charge_is_pending) ... ok
test_factory_rebinds_every_user_of_potential (test_teacher_patches.SymmetricPassTests.test_factory_rebinds_every_user_of_potential) ... ok
test_only_unpassed_action_phase_states_gain_the_pass_terms (test_teacher_patches.SymmetricPassTests.test_only_unpassed_action_phase_states_gain_the_pass_terms) ... ok

======================================================================
FAIL: test_fed_plan_goals_count_transdim_and_asteroid_when_former_or_eclipse_is_planned (test_teacher_patches.OpeningBudgetTests.test_fed_plan_goals_count_transdim_and_asteroid_when_former_or_eclipse_is_planned)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/sohegi/projects/gaia-lab/gaia-rl/tools/test_teacher_patches.py", line 881, in test_fed_plan_goals_count_transdim_and_asteroid_when_former_or_eclipse_is_planned
    self.assertEqual(colonies('Terrans', menu=[plan1], knowledge=4), {'2,1'})   # plan to Gaia 1, payable now
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Items in the second set but not the first:
'2,1'

----------------------------------------------------------------------
Ran 164 tests in 9.985s

FAILED (failures=1)
```

<sub>agentmaco · 커밋 583acd7 · 2026-11-27T02:05:57+09:00 → 2026-11-27T02:06:08+09:00</sub>
