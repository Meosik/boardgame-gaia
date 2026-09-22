"""Timeout recovery is an evaluated native action, never an invented pass."""
from copy import deepcopy
import json
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from gaia_rl import Environment
from current_actions.conservation import FORBIDDEN, blocked, identity
from faction_teachers.clock import AdaptiveClock
from faction_teachers.teacher import SharedTeacher
from four_factions.test_preparation import PREFIX, SEED, root


class QuickTests(unittest.TestCase):
    def test_stable_federation_priority_preserves_the_existing_order(self):
        from four_factions.quick import prioritize_federations
        candidates = [
            {'action': {'type': action_type}}
            for action_type in ('FreeAction', 'Pass', 'FormFederation', 'ResearchAdvance',
                                'FormFederation', 'Build')
        ]
        without_federation = [1, 5, 3, 0]
        prioritize_federations(without_federation, candidates, stable=True)
        self.assertEqual(without_federation, [1, 5, 3, 0])

        with_federation = [1, 4, 5, 2, 3, 0]
        prioritize_federations(with_federation, candidates, stable=True)
        self.assertEqual(with_federation, [4, 2, 1, 5, 3, 0])

        legacy = [1, 4, 5, 2, 3, 0]
        prioritize_federations(legacy, candidates, stable=False)
        self.assertEqual(legacy, [2, 4, 0, 1, 3, 5])

    def test_all_eighteen_native_factions_have_a_paid_fallback(self):
        from faction_learning import FACTIONS
        from four_factions.quick import fallback
        seen = set()
        for number in range(80):
            env = Environment(f'shared-teacher-base-{number}', 2000)
            for _ in range(12):
                snapshot = json.loads(env.snapshot_json())
                faction = snapshot['state']['players'][snapshot['player']]['faction']
                if faction not in seen:
                    original = env.snapshot_json()
                    result = fallback(env, snapshot, {}, deadline=time.monotonic()+.02)
                    self.assertEqual(env.snapshot_json(), original)
                    self.assertIn(result['index'], result['quick_evaluated_indices'])
                    env.fork(snapshot['decision_id'], result['index'])
                    seen.add(faction)
                env.step(snapshot['decision_id'], 0)  # Native setup fixture, not teacher play.
            if seen == set(FACTIONS):
                break
        self.assertEqual(seen, set(FACTIONS))

    def test_taklons_brainstone_constraint_is_not_relaxed_by_timeout(self):
        from four_factions.quick import fallback
        env = Environment('shared18-teacher-match-20260915-1', 2000)
        for index in [3, 2, 3, 0, 1, 4, 0, 1, 2, 2, 0, 0, 3, 9, 97, 1, 42, 1]:
            snapshot = json.loads(env.snapshot_json())
            env.step(snapshot['decision_id'], index)
        snapshot = json.loads(env.snapshot_json())
        self.assertEqual(snapshot['state']['players'][snapshot['player']]['faction'], 'Taklons')
        ships = [i for i, c in enumerate(snapshot['candidates']) if c['action']['type'] == 'ExploreSpaceship']
        self.assertTrue(ships)
        result = fallback(env, snapshot, {}, deadline=float('inf'))
        for i in ships:
            self.assertTrue(blocked(result['scores'][i]))
            self.assertIn('Brainstone', result['scores'][i][1])

    def test_native_fallback_is_evaluated_and_preserves_state_and_memory(self):
        from four_factions.quick import fallback
        env, snapshot = root()
        original = env.snapshot_json()
        memory = {'_plans': {}, '_clock': {'spent': []}}
        saved = deepcopy(memory)
        result = fallback(env, snapshot, memory, deadline=time.monotonic()+.2)
        self.assertEqual(env.snapshot_json(), original)
        self.assertEqual(memory, saved)
        self.assertEqual(result['memory'], saved)
        self.assertIn(result['index'], result['quick_evaluated_indices'])
        self.assertFalse(blocked(result['scores'][result['index']]))
        self.assertEqual(result['index'], max(result['quick_evaluated_indices'],
                         key=lambda i: (result['scores'][i][0], -i)))
        self.assertEqual(result['plans'], [])
        self.assertFalse(result['coverage_complete'])
        for i, candidate in enumerate(snapshot['candidates']):
            action = candidate['action']
            if action.get('kind') in FORBIDDEN | {'QicToOre'}:
                self.assertTrue(blocked(result['scores'][i]))
        env.step(snapshot['decision_id'], result['index'])

    def test_expired_quick_budget_still_evaluates_one_action_not_a_default_pass(self):
        from four_factions.quick import fallback
        env, snapshot = root()
        result = fallback(env, snapshot, {}, deadline=time.monotonic()-1)
        self.assertEqual(len(result['quick_evaluated_indices']), 1)
        self.assertGreater(len(result['quick_unevaluated_indices']), 0)
        self.assertNotEqual(snapshot['candidates'][result['index']]['action']['type'], 'Pass')

    def test_verified_followup_is_honored_even_with_expired_budget(self):
        from four_factions.quick import fallback
        env, snapshot = root()
        target = next(i for i, c in enumerate(snapshot['candidates'])
                      if c['action']['type'] == 'Upgrade')
        memory = {str(snapshot['player']): {identity(snapshot): [identity(snapshot['candidates'][target]['action'])]}}
        result = fallback(env, snapshot, memory, deadline=time.monotonic()-1)
        self.assertEqual(result['index'], target)
        self.assertEqual(result['memory'], memory)

    def test_missing_required_followup_is_an_error_not_permission_to_pass(self):
        from four_factions.quick import fallback
        env, snapshot = root()
        memory = {str(snapshot['player']): {identity(snapshot): ['not-a-native-action']}}
        with self.assertRaisesRegex(ValueError, 'No eligible'):
            fallback(env, snapshot, memory, deadline=time.monotonic()+.1)


class TimeoutFallbackTests(unittest.TestCase):
    def test_late_publication_cannot_replace_the_quick_reserve(self):
        env, snapshot = root()
        clock = AdaptiveClock(target_seconds=.3, long_seconds=.8, uses=0)
        teacher = SharedTeacher(SEED, prefix=PREFIX, adaptive_clock=clock).bind(env)
        script = '''import json,sys,time
from pathlib import Path
p=Path(sys.argv[1]).parent
value=json.loads(sys.argv[2]);value['published_at']=time.monotonic()+60
t=p/'candidate.tmp';t.write_text(json.dumps(value));t.replace(p/'candidate.json')
'''
        value = {'decision_id': snapshot['decision_id'], 'index': 0, 'memory': {},
                 'scores': [(1, 'evaluated')]*len(snapshot['candidates']), 'plans': [], 'selected': 'too-late'}
        popen = subprocess.Popen
        def launch(args, **kwargs):
            return popen([sys.executable, '-c', script, args[-1], json.dumps(value)], **kwargs)
        with patch('four_factions.timed.subprocess.Popen', side_effect=launch):
            teacher.choose(snapshot)
        self.assertTrue(teacher.last_audit['timing']['quick_fallback_used'])
        self.assertEqual(teacher.last_audit['selected'], 'quick-native-fallback')

    def test_actual_worker_error_is_not_concealed_by_quick_reserve(self):
        env, snapshot = root()
        original = env.snapshot_json()
        clock = AdaptiveClock(target_seconds=.3, long_seconds=.8, uses=0)
        teacher = SharedTeacher(SEED, prefix=PREFIX, adaptive_clock=clock).bind(env)
        script = '''import json,sys
from pathlib import Path
p=Path(sys.argv[1]).parent
(p/'error.json').write_text(json.dumps({'error':'invalid native state'}))
'''
        popen = subprocess.Popen
        def launch(args, **kwargs):
            return popen([sys.executable, '-c', script, args[-1]], **kwargs)
        with patch('four_factions.timed.subprocess.Popen', side_effect=launch):
            with self.assertRaisesRegex(RuntimeError, 'invalid native state'):
                teacher.choose(snapshot)
        self.assertEqual(env.snapshot_json(), original)

    def test_exhausted_clock_with_no_publication_returns_evaluated_native_action(self):
        env, snapshot = root()
        original = env.snapshot_json()
        clock = AdaptiveClock(target_seconds=.25, long_seconds=.8, uses=0)
        teacher = SharedTeacher(SEED, prefix=PREFIX, adaptive_clock=clock).bind(env)
        popen, children = subprocess.Popen, []

        def launch(args, **kwargs):
            child = popen([sys.executable, '-c', 'import time; time.sleep(60)'], **kwargs)
            children.append(child)
            return child

        started = time.monotonic()
        with patch('four_factions.timed.subprocess.Popen', side_effect=launch):
            decision, index = teacher.choose(snapshot)
        self.assertLess(time.monotonic()-started, 1.0)
        self.assertEqual(env.snapshot_json(), original)
        self.assertIsNotNone(children[0].poll())
        self.assertEqual(decision, snapshot['decision_id'])
        self.assertIn(index, teacher.last_audit['quick_evaluated_indices'])
        self.assertFalse(blocked(teacher.last_scores[index]))
        self.assertTrue(teacher.last_audit['timing']['quick_fallback_used'])
        self.assertEqual(clock.remaining(snapshot['player']), 0)
        env.step(decision, index)
        after = json.loads(env.snapshot_json())
        teacher.observe(snapshot, index, after)
        self.assertEqual(teacher.prefix, PREFIX+[index])


if __name__ == '__main__':
    unittest.main()
