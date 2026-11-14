"""115e smoke: a real worker (all_tier cap60-p2) answers the first decisions of the seed; print the reply 'timing'."""
import json
import sys
import time

import teacher_ab
from gaia_rl import Environment

SEED = 'quartet-d-75189@order=1,2,0,3'
SPEC = 'gaia-rl/tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-menu1-all-tier-cap60-p2.json'
teacher = teacher_ab.resolve_teacher(SPEC)
clock = {**teacher_ab.budget_clock(4), 'fast_copy': True}
env = Environment(SEED, 2000)
snapshot = json.loads(env.snapshot_json())
worker = teacher_ab.Worker(teacher, SEED, clock, sys.stderr)
try:
    assert worker.request(None, 300)['digest'] == teacher_ab.digest(snapshot)
    for _ in range(int(sys.argv[1]) if len(sys.argv) > 1 else 2):
        tick = time.monotonic()
        reply = worker.request({'op': 'choose', 'digest': teacher_ab.digest(snapshot)}, 300)
        print('step', snapshot['steps'], 'runner seconds', round(time.monotonic()-tick, 3), 'compared',
              reply.get('completed_comparisons'), 'fallback', reply.get('fallback_timeout'))
        print('  timing', json.dumps(reply.get('timing')))
        env.step(reply['decision_id'], reply['index'])
        snapshot = json.loads(env.snapshot_json())
        assert worker.request({'op': 'step', 'decision_id': reply['decision_id'], 'index': reply['index']},
                              300)['digest'] == teacher_ab.digest(snapshot)
finally:
    worker.close()
