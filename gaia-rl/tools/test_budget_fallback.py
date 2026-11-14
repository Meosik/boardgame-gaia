"""Safety cap passed before the search published anything: play the root ranking instead of crashing."""
import collections
import json
import math
import unittest
from unittest import mock

import budget_teacher
import parallel_search
from four_factions import preparation
from four_factions.preparation import SearchExpired

SNAPSHOT = {'steps': 0, 'decision_id': 7, 'player': 0, 'candidates': [{}, {}]}
RESULT = {'decision_id': 7, 'index': 0, 'scores': [[1.0, 'x']], 'memory': {}, 'plans': [],
          'selected': 'local-baseline'}


class FakeEnv:
    def snapshot_json(self):
        return json.dumps(SNAPSHOT)


class FakeSelf:
    def __init__(self):
        self.env = FakeEnv()
        self.prefix = []
        self.memory = {}
        self.times = collections.defaultdict(list)
        self.bgg_openings = False
        self.shared_factions = False
        self.delta_factions = ()
        self.fixed_openings = None
        self.observed_factions = ()
        self.faction_tech_plans = None


class BudgetFallbackTest(unittest.TestCase):
    def setUp(self):
        self._saved = (budget_teacher._installed, budget_teacher._max_seconds)
        budget_teacher._installed = 4
        budget_teacher._max_seconds = 60
        self.calls = []

    def tearDown(self):
        budget_teacher._installed, budget_teacher._max_seconds = self._saved
        parallel_search._state['no_prefetch'] = False

    def run_choose(self, fake):
        def search(env, snapshot, memory, publish, **kwargs):
            self.calls.append(kwargs['hard_deadline'])
            return fake(publish, kwargs)
        me = FakeSelf()
        with mock.patch.object(preparation, 'search', search):
            return me, budget_teacher._choose(me, dict(SNAPSHOT))

    def test_falls_back_instead_of_raising(self):
        def fake(publish, kwargs):
            if math.isfinite(kwargs['hard_deadline']):
                raise SearchExpired('cap')
            publish(dict(RESULT))
        me, out = self.run_choose(fake)
        self.assertEqual(out, (7, 0))
        self.assertIs(me.last_audit['expired_before_search'], True)
        self.assertEqual(me.last_audit['selected'], 'local-baseline')
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.calls[1], math.inf)

    def test_reraises_when_retry_publishes_nothing(self):
        def fake(publish, kwargs):
            raise SearchExpired('cap')
        with self.assertRaises(SearchExpired):
            self.run_choose(fake)

    def test_normal_path_unchanged(self):
        def fake(publish, kwargs):
            publish(dict(RESULT))
        me, out = self.run_choose(fake)
        self.assertEqual(out, (7, 0))
        self.assertIs(me.last_audit['expired_before_search'], False)
        self.assertEqual(len(self.calls), 1)

    def test_timing_stages_recorded(self):
        def fake(publish, kwargs):
            budget_teacher.add_stage('root_rank', 0.25)      # what parallel_search adds during the search
            publish(dict(RESULT))
        me, _ = self.run_choose(fake)
        timing = me.last_audit['timing']
        self.assertEqual(timing['cap'], 60)
        self.assertEqual(len(timing['published_at']), 1)
        self.assertEqual(timing['stages']['root_rank'], 0.25)
        self.assertLessEqual({'bind_check', 'search_call', 'state_check'}, set(timing['stages']))
        self.assertNotIn('root_result', timing['stages'])
        json.dumps(timing, allow_nan=False)                  # goes through the worker's JSON reply

    def test_timing_of_fallback_and_next_decision(self):
        def expired(publish, kwargs):
            if math.isfinite(kwargs['hard_deadline']):
                raise SearchExpired('cap')
            publish(dict(RESULT))
        me, _ = self.run_choose(expired)
        self.assertIn('root_result', me.last_audit['timing']['stages'])
        self.assertEqual(me.last_audit['timing']['published_at'], [])
        me, _ = self.run_choose(lambda publish, kwargs: publish(dict(RESULT)))
        self.assertNotIn('root_result', me.last_audit['timing']['stages'])   # stages are per decision

    def test_decision_timing_marks_stale_audit(self):
        import time
        import teacher_ab
        me, (decision, _) = self.run_choose(lambda publish, kwargs: publish(dict(RESULT)))
        fresh = teacher_ab.decision_timing(me.last_audit, decision, time.monotonic())
        self.assertIs(fresh['audit_fresh'], True)
        self.assertIn('bind_check', fresh['stages'])
        self.assertIs(fresh['expired_before_search'], False)
        stale = teacher_ab.decision_timing(me.last_audit, decision+1, time.monotonic())
        self.assertEqual(set(stale), {'choose', 'audit_fresh'})
        self.assertIs(stale['audit_fresh'], False)
        json.dumps(fresh, allow_nan=False)

    def test_decision_timing_stages_empty_when_none_recorded(self):
        import time
        import teacher_ab
        audit = {'decision_id': 7, 'timing': {'seconds': 0.0}}      # an immediate return: no stage recorded
        timing = teacher_ab.decision_timing(audit, 7, time.monotonic())
        self.assertIs(timing['audit_fresh'], True)
        self.assertEqual(timing['stages'], {})
        self.assertEqual(timing['search'], 0.0)
        json.dumps(timing, allow_nan=False)

    def test_prefetch_skipped_when_flagged(self):
        parallel_search._state['no_prefetch'] = True
        try:
            self.assertIsNone(parallel_search._prefetch(None, None, None, 4, {}))
        finally:
            parallel_search._state['no_prefetch'] = False


if __name__ == '__main__':
    unittest.main()
