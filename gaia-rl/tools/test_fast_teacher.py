"""fast_teacher's native preview must not change a single decision (and should save time)."""
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
from four_factions.teacher import NativeFactionTeacher
if sys.argv[2] == 'off':
    NativeFactionTeacher.bind = NativeFactionTeacher.bind.__wrapped__
import budget_teacher, teacher_patches
from gaia_rl import Environment
budget_teacher.install(2); budget_teacher.set_horizon(1)
env = Environment(sys.argv[1], 2000)
teacher = teacher_patches.geodens_guide(sys.argv[1], bgg_openings=True, shared_factions=True)
teacher.bind(env)
s = json.loads(env.snapshot_json()); out = []; started = time.monotonic()
while not env.is_terminal() and len(out) < int(sys.argv[3]):
    d, i = teacher.choose(s)
    audit = teacher.last_audit or {}
    out.append([s['steps'], i, audit.get('selected'), [round(p.get('value') or 0, 9) for p in audit.get('plans', [])]])
    b = s; env.step(d, i); s = json.loads(env.snapshot_json()); teacher.observe(b, i, s)
print(json.dumps({'decisions': out, 'seconds': time.monotonic() - started}))
'''


def run(modes, decisions, seed):
    """Play the same game once per mode, concurrently; return each mode's decisions."""
    env = {**os.environ, 'GAIA_ENGINE_FIXES_2': '1',
           'PYTHONPATH': os.pathsep.join(str(GAIA_RL/p) for p in ('python', 'baseline-teacher-20260917', 'tools'))}
    procs = [subprocess.Popen([sys.executable, '-c', SCRIPT, seed, mode, str(decisions)], cwd=GAIA_RL,
                              env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
             for mode in modes]
    results = []
    for proc in procs:
        out, err = proc.communicate()
        if proc.returncode:
            raise RuntimeError(err)
        results.append(json.loads(out.strip().splitlines()[-1]))
    return results


class NativePreviewTests(unittest.TestCase):
    def test_native_preview_makes_identical_decisions(self):
        # 160 decisions reach the federation-heavy middle rounds.
        for seed in ('geo-quartet-9840',):
            off, on = run(('off', 'on'), 160, seed)
            self.assertEqual(on['decisions'], off['decisions'], seed)
            print(f"\n{seed}: forks {off['seconds']:.1f} s, previews {on['seconds']:.1f} s", file=sys.stderr)


if __name__ == '__main__':
    unittest.main()
