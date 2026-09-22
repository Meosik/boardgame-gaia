"""Controller unit fixtures and one independently replayed native R1 continuation."""
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from bgg_openings.catalog import parse_buildings
from bgg_openings.inventory import building_counts, round_one_result
from current_actions.conservation import identity
from four_factions.preparation import Goal, Policies, search, select_goal
from four_factions.test_preparation import PREFIX, SEED, root
from four_factions.timed import TimedPreparationTeacher, worker
from research_plans.teacher import best_index


class ControllerTests(unittest.TestCase):
    def controlled_search(self, remembered=None, *, round_number=1, matching=True, enabled=True):
        env, snapshot = root()
        snapshot['state']['round'] = round_number
        snapshot['candidates'] = snapshot['candidates'][:2]  # Synthetic controller fixture only.
        actor = str(snapshot['player'])
        memory = {'_bgg_targets': {actor: remembered}} if remembered else {}
        goals = [Goal('PI', 'bgg-opening', target='1PI+2M'),
                 Goal('AC', 'bgg-opening', target='1AC+2M')]
        def forecast(env, snap, first, goal, policies, deadline, **kwargs):
            return {'complete': True, 'value': 10 + first if goal.family == 'bgg-opening' else 100,
                'r1_buildings': asdict(parse_buildings(goal.target))
                    if matching and goal.family == 'bgg-opening' else None}
        with patch('four_factions.preparation.Policies.rank', return_value=[(0, 'test'), (1, 'test')]), \
             patch('four_factions.preparation.goals_for', return_value=[]), \
             patch('four_factions.preparation.scoring_pairs', return_value=[]), \
             patch('bgg_openings.planning.goals', return_value=goals), \
             patch('four_factions.preparation.select_goal', side_effect=lambda e, s, sc, g, p, d: int(g.target == '1AC+2M')), \
             patch('four_factions.preparation.rollout', side_effect=forecast):
            return search(env, snapshot, memory, lambda result: None,
                          soft_deadline=time.monotonic()+10, hard_deadline=time.monotonic()+20,
                          bgg_openings=enabled)

    def test_lower_leaf_matching_opening_beats_unmatched_ordinary_forecast(self):
        result = self.controlled_search()
        self.assertEqual(result['index'], 1)
        self.assertEqual(result['bgg_opening']['target'], '1AC+2M')
        self.assertEqual(result['bgg_opening']['status'], 'selected')
        self.assertFalse(result['bgg_opening']['observed_completion'])

    def test_keeps_a_verified_goal_and_switches_when_only_another_route_is_found(self):
        result = self.controlled_search('1PI+2M')
        self.assertEqual(result['index'], 0)
        self.assertEqual(result['bgg_opening']['status'], 'kept')
        result = self.controlled_search('1RL+2M')
        self.assertEqual(result['bgg_opening']['status'], 'switched')
        self.assertEqual(result['bgg_opening']['target'], '1AC+2M')

    def test_fallback_is_original_teacher_not_an_invented_pass(self):
        result = self.controlled_search(matching=False)
        original = self.controlled_search(matching=False, enabled=False)
        self.assertEqual(result['bgg_opening']['status'], 'fallback-no-verified-route')
        self.assertEqual((result['index'], result['selected']), (original['index'], original['selected']))

    def test_round_two_disables_guidance_and_clears_target(self):
        result = self.controlled_search('1PI+2M', round_number=2)
        original = self.controlled_search(round_number=2, enabled=False)
        self.assertEqual(result['bgg_opening']['status'], 'outside-r1-or-source-scope')
        self.assertNotIn('_bgg_targets', result['memory'])
        self.assertEqual((result['index'], result['selected']), (original['index'], original['selected']))

    def test_worker_forwards_opt_in_after_exact_native_prefix_reconstruction(self):
        from hashlib import sha256
        _, snapshot = root()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'request.json'
            path.write_text(json.dumps({'seed': SEED, 'prefix': PREFIX, 'memory': {}, 'bgg_openings': True,
                'snapshot_sha256': sha256(identity(snapshot).encode()).hexdigest(),
                'soft_deadline': time.monotonic()+10, 'hard_deadline': time.monotonic()+20}))
            with patch('four_factions.preparation.search') as run:
                worker(path)
                self.assertTrue(run.call_args.kwargs['bgg_openings'])

    def test_real_paid_r1_goal_replaces_known_premature_pass_and_replays(self):
        env, initial = root()
        actor = initial['player']
        target = Goal('BGG-R1-1RL+1M', 'bgg-opening', target='1RL+1M', sources=('BGG-O2',))
        policies = Policies()
        scores = policies.rank(env, initial)
        original = best_index(scores, range(len(scores)))
        self.assertEqual(initial['candidates'][original]['action']['type'], 'Pass')
        first = select_goal(env, initial, scores, target, policies, time.monotonic()+30)
        self.assertEqual(initial['candidates'][first]['action']['type'], 'Upgrade')
        self.assertEqual(json.loads(env.snapshot_json()), initial)
        before = initial
        trace = []
        observer = TimedPreparationTeacher(SEED, prefix=PREFIX, bgg_openings=True)
        observer.memory = {'_bgg_targets': {str(actor): target.target}}
        observer.last_audit = {}
        for _ in range(192):
            scores = policies.rank(env, before)
            index = (select_goal(env, before, scores, target, policies, time.monotonic()+30)
                     if before['player'] == actor else best_index(scores, range(len(scores))))
            env.step(before['decision_id'], index)
            after = json.loads(env.snapshot_json())
            observer.observe(before, index, after)
            trace.append((before, index, after))
            if before['state']['round'] == 1 and after['state']['round'] == 2:
                self.assertIn(target.target, [o.label for o in round_one_result(before, after, actor)])
                self.assertEqual(building_counts(before['state']['players'][actor]), parse_buildings(target.target))
                self.assertTrue(observer.last_audit['bgg_r1_observed']['Terrans']['target_met'])
                self.assertNotIn('_bgg_targets', observer.memory)
                break
            before = after
        else:
            self.fail('Native R1 continuation did not reach its boundary')
        replay, snapshot = root()
        for before, index, after in trace:
            self.assertEqual(json.loads(replay.snapshot_json()), before)
            replay.step(before['decision_id'], index)
            self.assertEqual(json.loads(replay.snapshot_json()), after)
        # Snapshot fixtures above do not stand in for this actual replay evidence.
        self.assertGreater(len(trace), 1)
        self.assertEqual(trace[0][0]['state']['players'][actor]['resources']['ore']
                         - trace[0][2]['state']['players'][actor]['resources']['ore'], 2)


if __name__ == '__main__':
    unittest.main()
