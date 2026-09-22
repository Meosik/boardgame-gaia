from copy import deepcopy
import json
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from faction_teachers.clock import AdaptiveClock, converged, fast_reason
from faction_teachers.teacher import SharedTeacher
from four_factions.preparation import search
from four_factions.test_preparation import PREFIX, SEED, root


def progress(snapshot, values=(100, 90, 80)):
    return {'index': 0, 'scores': [(3, 'eligible')]*len(snapshot['candidates']),
            'selected': 'current-choice', 'coverage_complete': False,
            'plans': [{'first': i, 'family': 'current' if i == 0 else 'root',
                       'complete': True, 'value': value} for i, value in enumerate(values)]}


class ClockTests(unittest.TestCase):
    def setUp(self):
        _, self.s = root()
        self.s['candidates'] = [{'action': {'type': 'PlaceStartingStructure', 'coord': str(i)}}
                                for i in range(3)]

    def test_six_uses_are_per_seat_persist_and_never_reset_at_round_boundary(self):
        clock = AdaptiveClock()
        actor = self.s['player']
        for i in range(6):
            self.s['decision_id'] = i
            self.assertTrue(clock.spend(self.s))
            self.assertTrue(clock.spend(self.s))  # Same decision is not charged twice.
        self.s['state']['round'] = 6
        self.s['decision_id'] = 10
        self.assertFalse(clock.spend(self.s))
        self.assertEqual(clock.remaining(actor), 0)
        restored = AdaptiveClock(state=clock.state())
        self.assertEqual(restored.remaining(actor), 0)
        self.s['player'] = (actor+1) % 4
        self.assertEqual(restored.remaining(self.s['player']), 6)
        self.assertTrue(restored.spend(self.s))

    def test_invalid_clock_state_and_limits_fail_closed(self):
        for args in ({'target_seconds': 0}, {'target_seconds': 121}, {'long_seconds': float('inf')},
                     {'uses': -1}, {'state': {'spent': [['4', 1]]}},
                     {'state': {'spent': [['0', 1], ['0', 1]]}}):
            with self.assertRaises(ValueError):
                AdaptiveClock(**args)

    def test_basic_budget_for_forced_reaction_and_normal_decisions(self):
        clock = AdaptiveClock()
        self.assertEqual(clock.base_seconds(self.s, {}), 10)
        reaction = deepcopy(self.s)
        reaction['candidates'] = [{'action': {'type': 'ChargePower', 'accept': True}},
                                  {'action': {'type': 'ChargePower', 'accept': False}}]
        self.assertEqual(clock.base_seconds(reaction, {}), 3)
        reaction['candidates'] = reaction['candidates'][:1]
        self.assertEqual(clock.base_seconds(reaction, {}), 1)
        self.assertIsNone(clock.extension_reason(reaction, {}, None))

    def test_important_unresolved_plan_can_extend_but_clear_choice_does_not(self):
        clock = AdaptiveClock()
        self.assertIsNotNone(clock.extension_reason(self.s, {}, progress(self.s, (100,))))
        self.assertIsNone(clock.extension_reason(self.s, {}, progress(self.s)))
        self.assertIsNotNone(clock.extension_reason(self.s, {}, progress(self.s, (100, 99, 80))))

    def test_scarce_uses_raise_the_bar_without_round_quotas(self):
        clock = AdaptiveClock()
        self.s['state']['round'] = 1
        disputed = progress(self.s, (100, 98, 80))
        self.assertIsNotNone(clock.extension_reason(self.s, {}, disputed))
        for i in range(5):
            self.s['decision_id'] = i
            clock.spend(self.s)
        self.s['decision_id'] = 10
        self.assertIsNone(clock.extension_reason(self.s, {}, disputed))
        self.assertIsNotNone(clock.extension_reason(self.s, {}, progress(self.s, (100, 99.9, 80))))

    def test_early_finish_needs_three_distinct_completed_alternatives_and_stability(self):
        p = progress(self.s)
        self.assertTrue(converged(self.s, p, [0, 0, 0]))
        self.assertFalse(converged(self.s, p, [1, 0, 0]))
        p['plans'][2]['first'] = 1
        self.assertFalse(converged(self.s, p, [0, 0, 0]))
        p = progress(self.s)
        p['plans'][1]['complete'] = False
        self.assertFalse(converged(self.s, p, [0, 0, 0]))
        p = progress(self.s)
        p['bgg_opening'] = {'status': 'fallback-no-verified-route'}
        self.assertFalse(converged(self.s, p, [0, 0, 0]))

    def test_only_verified_committed_execution_is_fast(self):
        from current_actions.conservation import identity
        p = progress(self.s)
        self.assertIsNone(fast_reason(self.s, {}, p))
        memory = {str(self.s['player']): {identity(self.s): [identity(self.s['candidates'][0]['action'])]}}
        self.assertEqual(fast_reason(self.s, memory, p), 'verified resource follow-up')
        p['index'] = 1
        self.assertIsNone(fast_reason(self.s, memory, p))

    def test_adaptive_is_explicit_and_legacy_defaults_are_unchanged(self):
        old = SharedTeacher('old')
        self.assertEqual((old.target_seconds, old.maximum_seconds), (60, 300))
        new = SharedTeacher('new', adaptive_clock=AdaptiveClock())
        self.assertEqual((new.target_seconds, new.maximum_seconds), (10, 120))


class SupervisionTests(unittest.TestCase):
    def run_child(self, *, exhausted=False, finish_on_extension=False, finish_immediately=False):
        env, s = root()
        clock = AdaptiveClock(target_seconds=.25, long_seconds=.8)
        if exhausted:
            for i in range(6):
                past = deepcopy(s); past['decision_id'] = 100+i; clock.spend(past)
        teacher = SharedTeacher(SEED, prefix=PREFIX, adaptive_clock=clock).bind(env)
        value = {'decision_id': s['decision_id'], 'index': 0, 'memory': {},
                 'scores': [(1, 'evaluated')]*len(s['candidates']), 'plans': [], 'selected': 'test-incumbent'}
        script = '''import json,sys,time
from pathlib import Path
p=Path(sys.argv[1]).parent
value=json.loads(sys.argv[2]);value['published_at']=time.monotonic()
t=p/'candidate.tmp';t.write_text(json.dumps(value));t.replace(p/'candidate.json')
time.sleep(60)
'''
        if finish_on_extension:
            script = script.replace('time.sleep(60)',
                "while not (p/'allocation.json').exists(): time.sleep(.005)")
        elif finish_immediately:
            script = script.replace('time.sleep(60)', '')
        popen, children = subprocess.Popen, []
        def launch(args, **kwargs):
            child = popen([sys.executable, '-c', script, args[-1], json.dumps(value)], **kwargs)
            children.append(child)
            return child
        original = env.snapshot_json()
        start = time.monotonic()
        with patch('four_factions.timed.subprocess.Popen', side_effect=launch):
            teacher.choose(s)
        elapsed = time.monotonic()-start
        self.assertEqual(original, env.snapshot_json())
        self.assertIsNotNone(children[0].poll())
        self.assertLess(elapsed, 1.4)
        self.assertEqual(teacher.last_audit['selected'], 'test-incumbent')
        self.assertFalse(teacher.last_audit['timing']['quick_fallback_used'])
        return teacher, clock, s, elapsed

    def test_granted_extension_is_one_use_with_a_total_not_additive_cap(self):
        teacher, clock, s, elapsed = self.run_child()
        self.assertGreater(elapsed, .45)
        self.assertEqual(clock.remaining(s['player']), 5)
        self.assertTrue(teacher.last_audit['timing']['long_think_used'])
        self.assertEqual(teacher.memory['_clock'], clock.state())

    def test_exhausted_clock_keeps_basic_deadline_and_incumbent(self):
        teacher, clock, s, elapsed = self.run_child(exhausted=True)
        self.assertLess(elapsed, .6)
        self.assertEqual(clock.remaining(s['player']), 0)
        self.assertFalse(teacher.last_audit['timing']['long_think_used'])

    def test_extended_worker_can_finish_early_without_filling_two_minutes(self):
        teacher, clock, s, elapsed = self.run_child(finish_on_extension=True)
        self.assertLess(elapsed, .6)
        self.assertTrue(teacher.last_audit['timing']['long_think_used'])
        self.assertEqual(clock.remaining(s['player']), 5)

    def test_finished_worker_returns_immediately_without_spending_an_extension(self):
        teacher, clock, s, elapsed = self.run_child(finish_immediately=True)
        self.assertLess(elapsed, .25)
        self.assertFalse(teacher.last_audit['timing']['long_think_used'])
        self.assertEqual(clock.remaining(s['player']), 6)


class SearchAllocationTests(unittest.TestCase):
    def test_granted_allocation_continues_past_basic_target_then_stops_on_stable_evidence(self):
        snapshot = {'decision_id': 0, 'state': {'phase': {'Setup': {}}, 'round': 0}, 'player': 0,
                    'candidates': [{'action': {'type': 'PlaceStartingStructure', 'coord': str(i)}}
                                   for i in range(5)]}
        now, count = [0], [0]
        def forecast(*args):
            count[0] += 1
            now[0] += 10
            return {'complete': True, 'value': 110-count[0]*10, 'actions': []}
        with patch('four_factions.preparation.Policies.rank', return_value=[(1, 'eligible')]*5), \
                patch('four_factions.preparation.goals_for', return_value=[]), \
                patch('four_factions.preparation.scoring_pairs', return_value=[]), \
                patch('four_factions.preparation.time.monotonic', side_effect=lambda: now[0]), \
                patch('four_factions.preparation.rollout', side_effect=forecast):
            result = search(object(), snapshot, {}, lambda value: None,
                            soft_deadline=10, hard_deadline=120, adaptive=True, allocation=lambda: 120)
        self.assertEqual(count[0], 3)
        self.assertEqual(now[0], 30)
        self.assertEqual(result['index'], 0)
        self.assertEqual(result['unsearched_comparisons'], 2)
        self.assertFalse(result['coverage_complete'])
        self.assertIn('stable completed alternatives', result['stop_reason'])


if __name__ == '__main__':
    unittest.main()
