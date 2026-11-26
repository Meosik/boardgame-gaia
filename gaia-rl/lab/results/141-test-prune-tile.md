# 141-test-prune-tile — 실패

E370 사용자 「구현해」(E369 기본 타일 고르는 순서). 봇 턴에서 python 실행이 막혀 단위 테스트만 lab에서 돌린다(실험 아님, 판정 없음). 건강 기준: 종료 코드 0, test_prune_tile 7개 · 기존 test_prune_power_tf · test_prune_convs 모두 통과. 실패하면 정리 턴에 고친다. 예상 1분, 제한 0.25시간.

종료 코드 1

```
test_prune_tile_tier_by_track (test_prune_tile.PruneTile.test_prune_tile_tier_by_track) ... ok
test_taklons_charge4_under_gaia (test_prune_tile.PruneTile.test_taklons_charge4_under_gaia) ... ok
test_tile9_round_limit_only_where_table_says (test_prune_tile.PruneTile.test_tile9_round_limit_only_where_table_says) ... FAIL
test_blocked_candidates_pruned (test_prune_power_tf.PowerTf.test_blocked_candidates_pruned) ... ok
test_buying_extra_spade_needs_terraforming_3 (test_prune_power_tf.PowerTf.test_buying_extra_spade_needs_terraforming_3) ... ok
test_exact_fit_kept (test_prune_power_tf.PowerTf.test_exact_fit_kept) ... ok
test_family_restored_when_all_blocked (test_prune_power_tf.PowerTf.test_family_restored_when_all_blocked) ... ok
test_not_a_terraforming_power_action (test_prune_power_tf.PowerTf.test_not_a_terraforming_power_action) ... ok
test_off_ring_blocked_exact_fit_kept (test_prune_power_tf.PowerTf.test_off_ring_blocked_exact_fit_kept) ... ok
test_own_colour_blocked (test_prune_power_tf.PowerTf.test_own_colour_blocked) ... ok
test_two_qic_blocked (test_prune_power_tf.PowerTf.test_two_qic_blocked) ... ok
test_wasted_spade_blocked (test_prune_power_tf.PowerTf.test_wasted_spade_blocked) ... ok
test_legal_mine_does_not_hide_gaia_mine_qic (test_prune_convs.PayFilter.test_legal_mine_does_not_hide_gaia_mine_qic) ... ok
test_never_blocks_everything (test_prune_convs.PayFilter.test_never_blocks_everything) ... ok
test_no_shortage_blocks_every_payment (test_prune_convs.PayFilter.test_no_shortage_blocks_every_payment) ... ok
test_one_knowledge_to_credit_keeps_next_research_step (test_prune_convs.PayFilter.test_one_knowledge_to_credit_keeps_next_research_step) ... ok
test_power_action_first_for_knowledge (test_prune_convs.PayFilter.test_power_action_first_for_knowledge) ... ok
test_power_action_first_for_ore (test_prune_convs.PayFilter.test_power_action_first_for_ore) ... ok
test_research_check_counts_income_of_the_paid_structure (test_prune_convs.PayFilter.test_research_check_counts_income_of_the_paid_structure) ... ok
test_round_6_at_most_three_knowledge_to_credit (test_prune_convs.PayFilter.test_round_6_at_most_three_knowledge_to_credit) ... ok
test_short_credits_keep_credit_payments_only (test_prune_convs.PayFilter.test_short_credits_keep_credit_payments_only) ... ok
test_short_ore_keeps_power_to_ore (test_prune_convs.PayFilter.test_short_ore_keeps_power_to_ore) ... ok
test_three_knowledge_to_credit_only_in_round_6 (test_prune_convs.PayFilter.test_three_knowledge_to_credit_only_in_round_6) ... ok
test_unaffordable_even_with_conversions_blocks (test_prune_convs.PayFilter.test_unaffordable_even_with_conversions_blocks) ... ok

======================================================================
FAIL: test_tile9_round_limit_only_where_table_says (test_prune_tile.PruneTile.test_tile9_round_limit_only_where_table_says)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/sohegi/projects/gaia-lab/gaia-rl/tools/test_prune_tile.py", line 42, in test_tile9_round_limit_only_where_table_says
    self.assertEqual(tp._tile_class(state, player, 9), 'later')
AssertionError: 'good' != 'later'
- good
+ later


----------------------------------------------------------------------
Ran 30 tests in 0.008s

FAILED (failures=1)
```

<sub>agentmaco · 커밋 42fff1a · 2026-11-27T01:05:15+09:00 → 2026-11-27T01:05:16+09:00</sub>
