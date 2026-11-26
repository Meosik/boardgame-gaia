"""146 (user 11-27 「언제 패스할지 모르나?」): when each seat passed and what it still held.

Replays with the lab checkout modules (verified 291/291 in scratch_146_budget.py) and at every chosen Pass prints the
round, pass order, own main turns that round, resources, power bowls and the legal non-pass main actions left
(by type). Read only.

  scratch_146_pass.py <game dir>
"""
import gzip
import json
import os
import sys
from collections import Counter
from pathlib import Path

LAB = Path.home()/'projects/gaia-lab/gaia-rl'
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(LAB/'python'), str(LAB/'baseline-teacher-20260917'), str(LAB/'tools')]


def main():
    game = Path(sys.argv[1])
    result = json.loads((game/'result.json').read_text())
    from gaia_rl import Environment
    env = Environment(result['seed'], 2000)
    with gzip.open(game/'decisions.jsonl.gz', 'rt') as f:
        rows = [json.loads(line) for line in f]
    turns, order = Counter(), Counter()
    for row in rows:
        snap = json.loads(env.snapshot_json())
        state, seat = snap['state'], snap.get('player')
        types = [c['action'].get('type') for c in snap['candidates']]
        if 'ActionPhase' in str(state['phase']) and 'Pass' in types:
            turns[(seat, state['round'])] += 1
            if types[row['index']] == 'Pass':
                order[state['round']] += 1
                p = state['players'][seat]
                r, pw = p['resources'], p['resources']['power']
                left = Counter(t for t in types if t not in ('Pass', 'FreeAction'))
                print(f"R{state['round']} pass#{order[state['round']]} seat {seat} {p['faction']} turns {turns[(seat, state['round'])]}"
                      f" | c{r.get('credits')} o{r.get('ore')} k{r.get('knowledge')} q{r.get('qic')}"
                      f" pw {pw['bowl1']}/{pw['bowl2']}/{pw['bowl3']} | left {dict(left)}")
        env.step(row['decision_id'], row['index'])


if __name__ == '__main__':
    main()
