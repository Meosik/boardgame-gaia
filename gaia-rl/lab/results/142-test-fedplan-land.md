# 142-test-fedplan-land — 완료

사용자 11-27 「쓸만한 땅」: fed_plan 가까운 행성을 가이아 · 모행성 · 1테라포밍으로 좁힘(소행성 특수 경우 · 가이아 트랙 종족의 차원 변환은 미구현). 봇 턴에서 python 실행이 막혀 단위 테스트만 lab에서 돌린다(실험 아님, 판정 없음). 건강 기준: 종료 코드 0, test_teacher_patches 전부 통과(새 test_fed_plan_goals_use_only_gaia_home_and_one_step_planets 포함). 실패하면 정리 턴에 고친다. 예상 1분, 제한 0.25시간.

종료 코드 0

```
test_track_steps_src_replaces_the_guide_order (test_teacher_patches.OpeningBudgetTests.test_track_steps_src_replaces_the_guide_order) ... ok
test_value_max_keeps_only_catalog_labels_as_the_saved_target (test_teacher_patches.OpeningBudgetTests.test_value_max_keeps_only_catalog_labels_as_the_saved_target) ... ok
test_weak_faction_parts_are_on_only_with_their_flag (test_teacher_patches.OpeningBudgetTests.test_weak_faction_parts_are_on_only_with_their_flag) ... ok
test_fires_when_every_other_seat_has_passed (test_teacher_patches.PassLastTests.test_fires_when_every_other_seat_has_passed) ... ok
test_lifted_reason_carries_the_pre_flag_score (test_teacher_patches.PassLastTests.test_lifted_reason_carries_the_pre_flag_score) ... ok
test_spec_file_names_the_factory_and_matches_the_base_spec (test_teacher_patches.PassLastTests.test_spec_file_names_the_factory_and_matches_the_base_spec) ... ok
test_unchanged_outside_the_action_phase (test_teacher_patches.PassLastTests.test_unchanged_outside_the_action_phase) ... ok
test_unchanged_when_a_non_pass_candidate_is_already_on_top (test_teacher_patches.PassLastTests.test_unchanged_when_a_non_pass_candidate_is_already_on_top) ... ok
test_unchanged_while_another_seat_has_not_passed (test_teacher_patches.PassLastTests.test_unchanged_while_another_seat_has_not_passed) ... ok
test_unchanged_with_the_flag_off (test_teacher_patches.PassLastTests.test_unchanged_with_the_flag_off) ... ok
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

----------------------------------------------------------------------
Ran 160 tests in 10.102s

OK
```

<sub>agentmaco · 커밋 de95f86 · 2026-11-27T01:50:26+09:00 → 2026-11-27T01:50:37+09:00</sub>
