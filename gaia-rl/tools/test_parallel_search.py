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


    def test_booster_lookahead_decisions_are_identical_in_parallel(self):
        sequential = run(1, 90, factory='booster_lookahead')
        parallel = run(3, 90, factory='booster_lookahead')
        self.assertEqual(parallel['decisions'], sequential['decisions'])
        self.assertTrue(any(str(d[2]).startswith('booster-') or d[2] == 'current-choice'
                            for d in sequential['decisions']))


if __name__ == '__main__':
    unittest.main()
