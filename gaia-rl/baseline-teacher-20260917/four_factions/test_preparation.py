import json
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from gaia_rl import Environment
from current_actions.conservation import blocked
from four_factions.preparation import (Goal, Policies, achieved, goals_for, predicate_for,
                                       interleave_families, rollout, search, select_goal)
from four_factions.timed import TimedPreparationTeacher

SEED = 'quartet-pilot-20260913-27703'
# Recorded native prefix before Terrans' premature R1 pass; no forced test income.
PREFIX = [1, 1, 1, 4, 1, 2, 0, 1, 1, 6, 2, 0, 3, 34, 14, 30, 4, 30, 1, 1, 54, 1, 1]


def root():
    env = Environment(SEED, 2000)
    for index in PREFIX:
        s = json.loads(env.snapshot_json())
        env.step(s['decision_id'], index)
    return env, json.loads(env.snapshot_json())


class PreparationTests(unittest.TestCase):
    def test_goal_families_are_not_starved_by_many_academy_locations(self):
        goals = [Goal(f'academy-{i}', 'upgrade') for i in range(8)] + [
            Goal('navigation', 'research'), Goal('gaia', 'colony'), Goal('ship', 'ship')]
        ordered = interleave_families(goals, lambda goal: goal.family)
        self.assertEqual([goal.family for goal in ordered[:4]], ['upgrade', 'research', 'colony', 'ship'])
        self.assertCountEqual(ordered, goals)
        self.assertEqual(interleave_families([], lambda goal: goal.family), [])

    def test_native_academy_path_beats_premature_pass_at_same_horizon(self):
        env, s = root()
        original = env.snapshot_json()
        policies = Policies()
        scores = policies.rank(env, s)
        deadline = time.monotonic()+180
        current = Goal('current')
        academy = Goal('academy', 'upgrade', '-3,-4', 'Science')
        first = select_goal(env, s, scores, academy, policies, deadline)
        self.assertEqual(s['candidates'][first]['action']['type'], 'Upgrade')
        self.assertFalse(blocked(scores[first]))
        wait = select_goal(env, s, scores, current, policies, deadline)
        self.assertEqual(s['candidates'][wait]['action']['type'], 'Pass')
        control = rollout(env, s, wait, current, policies, deadline)
        prepared = rollout(env, s, first, academy, policies, deadline)
        self.assertTrue(control['complete'] and prepared['complete'])
        self.assertEqual(control['end_round'], prepared['end_round'])
        self.assertGreater(prepared['value'], control['value'])
        self.assertTrue(prepared['goal_acquired'])
        actions = [a for a in prepared['actions'] if a['action']['type'] == 'Upgrade']
        self.assertEqual(len(actions), 3)
        self.assertEqual(actions[-1]['round'], 2)
        self.assertEqual(actions[-1]['action']['to'], {'Academy': 'Science'})
        self.assertEqual(actions[-1]['resources_before']['ore']-actions[-1]['resources_after']['ore'], 6)
        self.assertEqual(env.snapshot_json(), original)

    def test_all_colonies_and_each_academy_site_are_proposed(self):
        _, s = root()
        goals = goals_for(s)
        self.assertGreater(len([g for g in goals if g.family == 'colony']), 2)
        sites = {x['hex'] for x in s['state']['players'][s['player']]['structures']}
        self.assertEqual({g.coord for g in goals if g.family == 'upgrade' and g.target == 'Science'}, sites)
        self.assertTrue(any(g.family == 'federations' for g in goals))

    def test_prepared_forming_is_not_a_colonized_planet(self):
        _, s = root()
        goal = Goal('colony', 'colony', '-3,-1')
        self.assertFalse(achieved(s, s['player'], goal))
        s['state']['board']['hexes']['-3,-1']['planet']['is_gaia_formed'] = True
        self.assertFalse(achieved(s, s['player'], goal))

    def test_forecast_limit_does_not_invent_a_bad_value(self):
        env, s = root()
        policies = Policies()
        scores = policies.rank(env, s)
        first = max(range(len(scores)), key=lambda i: scores[i][0])
        result = rollout(env, s, first, Goal('current'), policies, time.monotonic()+10, limit=1)
        self.assertFalse(result['complete'])
        self.assertIsNone(result['value'])

    def test_search_keeps_baseline_if_control_horizon_is_incomplete(self):
        env, s = root()
        records = []
        with patch('four_factions.preparation.rollout', return_value={
                'complete': False, 'value': None, 'actions': []}):
            result = search(env, s, {}, records.append,
                            soft_deadline=time.monotonic()+10, hard_deadline=time.monotonic()+20)
        self.assertEqual(result['selected'], 'local-baseline')
        self.assertEqual(len(result['plans']), 1)
        self.assertFalse(result['coverage_complete'])

    def test_all_actual_factions_use_their_own_continuation_policy(self):
        env = Environment(SEED, 2000)
        policies = Policies()
        seen = set()
        for _ in range(9):
            original = env.snapshot_json()
            s = json.loads(original)
            scores = policies.rank(env, s)
            self.assertEqual(original, env.snapshot_json())
            self.assertEqual(len(scores), len(s['candidates']))
            seen.add(s['state']['players'][s['player']]['faction'])
            eligible = [i for i, score in enumerate(scores) if not blocked(score)]
            index = max(eligible, key=lambda i: (scores[i][0], -i))
            env.step(s['decision_id'], index)
        self.assertEqual(seen, {'HadschHallas', 'Xenos', 'Terrans', 'Taklons'})


class SoftDeadlineTests(unittest.TestCase):
    def run_search(self, action, clock, forecast):
        snapshot = {'decision_id': 'deadline-test', 'state': {'phase': {'Setup': {}}},
                    'candidates': [{'action': action} for _ in range(3)]}
        with patch('four_factions.preparation.Policies.rank', return_value=[
                (3, 'eligible'), (2, 'eligible'), (1, 'eligible')]), \
                patch('four_factions.preparation.goals_for', return_value=[]), \
                patch('four_factions.preparation.scoring_pairs', return_value=[]), \
                patch('four_factions.preparation.time.monotonic', side_effect=lambda: clock[0]), \
                patch('four_factions.preparation.rollout', side_effect=forecast) as rollout_mock:
            result = search(object(), snapshot, {}, lambda value: None,
                            soft_deadline=60, hard_deadline=300)
        return result, rollout_mock

    def test_complex_menus_do_not_start_more_comparisons_after_soft_deadline(self):
        for action in ({'type': 'PlaceStartingStructure'}, {'type': 'FormFederation'},
                       {'type': 'Upgrade', 'tech_tile_choice': {'kind': 'Advanced'}},
                       {'type': 'Upgrade', 'tech_tile_choice': {'kind': 'LostFleetAdvanced'}}):
            with self.subTest(action=action):
                clock = [0]

                def forecast(*args):
                    self.assertEqual(args[-1], 300)
                    clock[0] = 61
                    return {'complete': True, 'value': 20, 'actions': []}

                result, calls = self.run_search(action, clock, forecast)
                self.assertEqual(calls.call_count, 1)
                self.assertEqual(len(result['plans']), 1)
                self.assertEqual(result['unsearched_comparisons'], 2)
                self.assertEqual(result['selected'], 'current-choice')
                self.assertFalse(result['coverage_complete'])

    def test_comparison_started_before_cutoff_can_finish_and_be_selected(self):
        clock = [0]
        started = []

        def forecast(*args):
            started.append(clock[0])
            self.assertEqual(args[-1], 300)
            clock[0] = 59 if len(started) == 1 else 61
            return {'complete': True, 'value': len(started)*10, 'actions': []}

        result, calls = self.run_search({'type': 'PlaceStartingStructure'}, clock, forecast)
        self.assertEqual(started, [0, 59])
        self.assertEqual(calls.call_count, 2)
        self.assertEqual(result['index'], 1)
        self.assertEqual(result['selected'], 'root-1')
        self.assertIsNotNone(result['extended_reason'])

    def test_already_expired_soft_budget_keeps_evaluated_baseline(self):
        result, calls = self.run_search({'type': 'PlaceStartingStructure'}, [60],
                                       lambda *args: {'complete': True, 'value': 20, 'actions': []})
        calls.assert_not_called()
        self.assertEqual(result['selected'], 'local-baseline')
        self.assertEqual(result['plans'], [])
        self.assertIsNone(result['extended_reason'])


class TimedTests(unittest.TestCase):
    def test_hung_search_is_terminated_and_last_complete_incumbent_survives(self):
        env, s = root()
        teacher = TimedPreparationTeacher(SEED, target_seconds=.1, maximum_seconds=.6, prefix=PREFIX).bind(env)
        teacher.times[str(s['player'])] = [1.0, 1.0]
        script = '''import json,sys,time
from pathlib import Path
p=Path(sys.argv[1]).parent
value=json.loads(sys.argv[2]);value['published_at']=time.monotonic()
t=p/'candidate.tmp';t.write_text(json.dumps(value));t.replace(p/'candidate.json')
time.sleep(60)
'''
        incumbent = {'decision_id': s['decision_id'], 'index': 0, 'memory': {},
                     'scores': [(1, 'evaluated')]*len(s['candidates']), 'plans': [], 'selected': 'test-incumbent'}
        popen = subprocess.Popen
        children = []
        def launch(args, **kwargs):
            from pathlib import Path
            request = json.loads(Path(args[-1]).read_text())
            # Previous long placements cannot erase this turn's soft allocation.
            self.assertAlmostEqual(request['hard_deadline']-request['soft_deadline'], .44, places=6)
            child = popen([sys.executable, '-c', script, args[-1], json.dumps(incumbent)], **kwargs)
            children.append(child)
            return child
        started = time.monotonic()
        with patch('four_factions.timed.subprocess.Popen', side_effect=launch):
            self.assertEqual(teacher.choose(s), (s['decision_id'], 0))
        self.assertLess(time.monotonic()-started, 1.2)
        self.assertIsNotNone(children[0].poll())
        self.assertTrue(teacher.last_audit['timing']['deadline_reached'])

    def test_native_subprocess_returns_legal_incumbent_and_preserves_parent(self):
        env, s = root()
        original = env.snapshot_json()
        teacher = TimedPreparationTeacher(SEED, target_seconds=.05, maximum_seconds=2, prefix=PREFIX).bind(env)
        started = time.monotonic()
        decision, index = teacher.choose(s)
        elapsed = time.monotonic()-started
        self.assertLess(elapsed, 2.5)
        self.assertEqual(decision, s['decision_id'])
        self.assertFalse(blocked(teacher.last_scores[index]))
        self.assertEqual(original, env.snapshot_json())
        env.step(decision, index)
        after = json.loads(env.snapshot_json())
        teacher.observe(s, index, after)
        self.assertEqual(teacher.prefix, PREFIX+[index])

    def test_missing_prefix_and_invalid_budgets_fail_explicitly(self):
        env, s = root()
        with self.assertRaisesRegex(ValueError, 'Missing native actions'):
            TimedPreparationTeacher(SEED).bind(env).choose(s)
        for target, maximum in ((0, 2), (3, 2), (1, float('inf'))):
            with self.assertRaises(ValueError):
                TimedPreparationTeacher(SEED, target_seconds=target, maximum_seconds=maximum)

    def test_deadline_without_evaluated_incumbent_fails_without_stepping(self):
        env, s = root()
        original = env.snapshot_json()
        teacher = TimedPreparationTeacher(SEED, target_seconds=.1, maximum_seconds=.3, prefix=PREFIX).bind(env)
        popen = subprocess.Popen
        children = []

        def launch(args, **kwargs):
            child = popen([sys.executable, '-c', 'import time; time.sleep(60)'], **kwargs)
            children.append(child)
            return child

        with patch('four_factions.timed.subprocess.Popen', side_effect=launch):
            with self.assertRaisesRegex(TimeoutError, 'No eligible evaluated action'):
                teacher.choose(s)
        self.assertEqual(original, env.snapshot_json())
        self.assertIsNotNone(children[0].poll())

    def test_worker_error_does_not_silently_use_an_old_incumbent(self):
        env, s = root()
        original = env.snapshot_json()
        teacher = TimedPreparationTeacher(SEED, target_seconds=.1, maximum_seconds=1, prefix=PREFIX).bind(env)
        script = '''import json,sys,time
from pathlib import Path
p=Path(sys.argv[1]).parent
value=json.loads(sys.argv[2]);value['published_at']=time.monotonic()
t=p/'candidate.tmp';t.write_text(json.dumps(value));t.replace(p/'candidate.json')
t=p/'error.tmp';t.write_text(json.dumps({'error':'native search failed'}));t.replace(p/'error.json')
time.sleep(60)
'''
        incumbent = {'decision_id': s['decision_id'], 'index': 0, 'memory': {},
                     'scores': [(1, 'evaluated')]*len(s['candidates']), 'plans': [], 'selected': 'old'}
        popen = subprocess.Popen
        children = []

        def launch(args, **kwargs):
            child = popen([sys.executable, '-c', script, args[-1], json.dumps(incumbent)], **kwargs)
            children.append(child)
            return child

        with patch('four_factions.timed.subprocess.Popen', side_effect=launch):
            with self.assertRaisesRegex(RuntimeError, 'native search failed'):
                teacher.choose(s)
        self.assertEqual(original, env.snapshot_json())
        self.assertIsNotNone(children[0].poll())


if __name__ == '__main__':
    unittest.main()
