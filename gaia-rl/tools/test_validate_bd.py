"""Tests of the user-approved research-only (d) variant, not tuned action signs."""
import copy
import unittest

from validate_bc import representative, successor
import state_evaluation_bquadrupleprime as model


def evaluate(state, actor, enabled=True):
    return model.evaluate_state(state, actor, token_shortfall=True, remaining_income=True,
                                distributed_research=enabled)


class DistributedResearchTests(unittest.TestCase):
    def test_off_equals_bc_and_on_changes_only_research_progress(self):
        for r in (1, 3, 6):
            state, actor = representative(r)
            original = copy.deepcopy(state)
            before = model.base.evaluate_state(state, actor, token_shortfall=True, remaining_income=True)
            self.assertEqual(evaluate(state, actor, False), before)
            after = evaluate(state, actor)
            for key in before.breakdown:
                if key != 'research_progress':
                    self.assertEqual(before.breakdown[key], after.breakdown[key], key)
            self.assertEqual(before.opportunities, after.opportunities)
            self.assertEqual(before.tile_values, after.tile_values)
            self.assertEqual(before.ship_values, after.ship_values)
            self.assertAlmostEqual(after.total_vp, sum(after.breakdown.values()))
            self.assertEqual(state, original)

    def test_progress_independent_of_knowledge_and_round(self):
        values = []
        for r in (1, 3, 6):
            for k in (0, 3, 4, 15):
                state, actor = representative(r)
                state['players'][actor]['resources']['knowledge'] = k
                values.append(evaluate(state, actor).breakdown['research_progress'])
        self.assertEqual(len(set(values)), 1)

    def test_uniform_shares_and_no_duplicate_banked_track_points(self):
        state, actor = representative(1)
        player = state['players'][actor]
        player['research_tracks'] = dict.fromkeys(player['research_tracks'], 0)
        facts = model.base.engine_facts(state, player)
        for level in range(5):
            player['research_tracks']['economy'] = level
            result = evaluate(state, actor)
            expected = facts['final_track_vp'][3]*level/3 if level < 3 else facts['final_track_vp'][level]
            self.assertAlmostEqual(result.breakdown['research_progress']+result.breakdown['research_final_vp'], expected)

    def test_stock_rewards_excluded_and_science_extra_beyond_top_three(self):
        state, actor = representative(1)
        player = state['players'][actor]
        player['research_tracks'].update(terraforming=2, navigation=2, economy=2, ai=1, gaia=1, science=1)
        facts = model.base.engine_facts(state, player)
        rows = {row['track']: row for row in model.research_progress_details(state, player, facts)}
        self.assertEqual({key for key, row in rows.items() if row['selected']},
                         {'terraforming', 'navigation', 'economy', 'science'})
        self.assertEqual(rows['ai']['progress_vp'], 0)
        self.assertGreater(rows['ai']['thresholds'][0]['excluded_resource_vp'], 0)
        self.assertAlmostEqual(rows['science']['progress_vp'], 4/3)
        self.assertAlmostEqual(evaluate(state, actor).breakdown['research_progress'], 3*8/3+4/3)

    def test_completed_threshold_preserved_after_federation_token_is_spent(self):
        state, actor = representative(1)
        player = state['players'][actor]
        player['research_tracks']['economy'] = 5
        player['federation_tokens'] = []
        row = next(row for row in model.research_progress_details(state, player,
            model.base.engine_facts(state, player)) if row['track'] == 'economy')
        self.assertEqual(row['banked_track_vp'], 12)
        self.assertEqual(row['fractional_vp'], 0)
        self.assertEqual(row['progress_vp'], 0)

    def test_reached_threshold_shares_are_zero_on_every_track(self):
        state, actor = representative(1)
        player = state['players'][actor]
        player['federation_tokens'] = [1]
        for track in model.base.TRACK_IDS:
            for level in (3, 4, 5):
                player['research_tracks'] = dict.fromkeys(player['research_tracks'], 0)
                player['research_tracks'][track] = level
                details = next(row for row in model.research_progress_details(state, player,
                    model.base.engine_facts(state, player)) if row['track'] == track)
                self.assertEqual(details['fractional_vp'], 0)
                self.assertEqual(evaluate(state, actor).breakdown['research_final_vp'], details['banked_track_vp'])

    def test_step_diagnostic_excludes_immediate_vp_from_track_slope(self):
        from validate_bd import step_rows
        rows = step_rows()
        self.assertEqual(len(rows), 90)
        failures = [row for row in rows if not row['passed']]
        self.assertEqual(failures, [])
        for row in rows:
            self.assertGreaterEqual(row['actual'], 0)

    def test_level_five_prospective_gate_and_terminal_native_score(self):
        state, actor = representative(1)
        player = state['players'][actor]
        player['research_tracks']['economy'] = 4
        player['federation_tokens'] = []
        row = next(row for row in model.research_progress_details(state, player,
            model.base.engine_facts(state, player)) if row['track'] == 'economy')
        self.assertFalse(row['thresholds'][-1]['allowed'])
        state['phase'] = {'Ended': {'final_scores': [[i, 100+i] for i in range(4)]}}
        self.assertEqual(evaluate(state, actor).total_vp, 100+actor)


if __name__ == '__main__':
    unittest.main()
