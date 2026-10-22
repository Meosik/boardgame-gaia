"""Parallel comparisons must not change a single decision (and should save time)."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

GAIA_RL = Path(__file__).resolve().parents[1]
SCRIPT = r'''
import json, sys, time
import fast_teacher; fast_teacher.install()
import budget_teacher, teacher_patches, parallel_search
from gaia_rl import Environment
budget_teacher.install(4); budget_teacher.set_horizon(1)
env = Environment(sys.argv[1], 2000)
factory = getattr(teacher_patches, sys.argv[4])
teacher = factory(sys.argv[1], bgg_openings=True, shared_factions=True)
teacher.bind(env)
parallel_search.install(int(sys.argv[2]))
# A second AI room: the factory re-installs its wrappers, then the worker re-installs parallel.
factory('another-room', bgg_openings=True, shared_factions=True)
parallel_search.install(int(sys.argv[2]))
budget_teacher.set_horizon(1)
s = json.loads(env.snapshot_json()); out = []; started = time.monotonic()
while not env.is_terminal() and len(out) < int(sys.argv[3]):
    d, i = teacher.choose(s)
    audit = teacher.last_audit or {}
    out.append([s['steps'], i, audit.get('selected'), [round(p.get('value') or 0, 9) for p in audit.get('plans', [])]])
    b = s; env.step(d, i); s = json.loads(env.snapshot_json()); teacher.observe(b, i, s)
print(json.dumps({'decisions': out, 'seconds': time.monotonic() - started}))
'''


def run(processes, decisions, seed='geo-quartet-9840', factory='geodens_guide'):
    env = {**os.environ, 'GAIA_ENGINE_FIXES_2': '1',
           'PYTHONPATH': os.pathsep.join(str(GAIA_RL/p) for p in ('python', 'baseline-teacher-20260917', 'tools'))}
    out = subprocess.run([sys.executable, '-c', SCRIPT, seed, str(processes), str(decisions), factory], cwd=GAIA_RL,
                         env=env, capture_output=True, text=True, check=True)
    return json.loads(out.stdout.strip().splitlines()[-1])


class ParallelSearchTests(unittest.TestCase):
    def test_parallel_comparisons_make_identical_decisions(self):
        sequential = run(1, 90)
        parallel = run(3, 90)
        self.assertEqual(parallel['decisions'], sequential['decisions'])
        searched = sum(bool(d[3]) for d in sequential['decisions'])
        self.assertGreater(searched, 10)
        print(f"\nsequential {sequential['seconds']:.1f} s, parallel {parallel['seconds']:.1f} s, "
              f"{searched} searched decisions", file=sys.stderr)


class DeadlineTests(unittest.TestCase):
    def setUp(self):
        sys.path[:0] = [str(GAIA_RL/p) for p in ('python', 'baseline-teacher-20260917', 'tools')]
        import parallel_search
        self.ps = parallel_search
        self.saved = dict(parallel_search._state)

    def tearDown(self):
        self.ps._state.clear()
        self.ps._state.update(self.saved)

    def test_drop_unfinished_replaces_pool_only_when_a_job_is_pending(self):
        from unittest import mock
        ready, pending = mock.Mock(), mock.Mock()
        ready.ready.return_value = True
        pending.ready.return_value = False
        old = mock.Mock()
        self.ps._state.update(pool=old, processes=2, prefetch=('k', 'm', {'a': ready}))
        self.ps._drop_unfinished()
        self.assertIs(self.ps._state['pool'], old)
        old.terminate.assert_not_called()
        self.ps._state['prefetch'] = ('k', 'm', {'a': ready, 'b': pending})
        with mock.patch('multiprocessing.get_context') as ctx:
            self.ps._drop_unfinished()
        old.terminate.assert_called_once()
        old.join.assert_called_once()
        ctx.assert_called_with('fork')
        ctx.return_value.Pool.assert_called_with(2)
        self.assertIs(self.ps._state['pool'], ctx.return_value.Pool.return_value)

    def test_select_goal_wrapper_raises_search_expired_at_the_deadline(self):
        import math
        import multiprocessing
        import time
        from unittest import mock
        import budget_teacher
        import four_factions.preparation as p
        saved = (p.Policies.rank, p.select_goal, p.rollout, p.search, budget_teacher.set_horizon)
        self.addCleanup(lambda: (setattr(p.Policies, 'rank', saved[0]), setattr(p, 'select_goal', saved[1]),
                                 setattr(p, 'rollout', saved[2]), setattr(p, 'search', saved[3]),
                                 setattr(budget_teacher, 'set_horizon', saved[4])))
        with mock.patch('multiprocessing.get_context'):
            self.ps.install(2)
        future = mock.Mock()
        future.get.side_effect = multiprocessing.TimeoutError()
        with mock.patch.object(self.ps, '_lookup', return_value=future):
            with self.assertRaises(p.SearchExpired):
                p.select_goal(None, {}, [], None, None, time.monotonic() - 1)
            wait = future.get.call_args[0][0]
            self.assertEqual(wait, 0.0)
            with self.assertRaises(p.SearchExpired):
                p.select_goal(None, {}, [], None, None, math.inf)
            self.assertIsNone(future.get.call_args[0][0])


if __name__ == '__main__':
    unittest.main()
