"""146 known-bad 30: does formed_mine (work tree teacher_patches) lift QicToOre then Build -8,1 at BalTaks step 63?

  scratch_146_formed_mine.py <game dir> [step=63]
Replays with the lab engine module, then calls the work-tree formed_mine_scores on flat scores where Pass is on
top and every FreeAction is BLOCKED (worst case: pruning tables blocked the conversion). Applies the lifted move and
repeats up to 4 times. Read only (forks only after the replay point).
"""
import gzip
import importlib.util
import json
import os
import sys
from pathlib import Path

LAB = Path.home()/'projects/gaia-lab/gaia-rl'
WORK = Path(__file__).resolve().parents[1]
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(LAB/'python'), str(WORK/'baseline-teacher-20260917'), str(WORK/'tools')]


def main():
    game = Path(sys.argv[1])
    step = int(sys.argv[2]) if len(sys.argv) > 2 else 63
    spec = importlib.util.spec_from_file_location('tp_work', WORK/'tools'/'teacher_patches.py')
    tp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tp)
    from current_actions.conservation import BLOCKED, PREFIX
    result = json.loads((game/'result.json').read_text())
    from gaia_rl import Environment
    env = Environment(result['seed'], 2000)
    with gzip.open(game/'decisions.jsonl.gz', 'rt') as f:
        rows = [json.loads(line) for line in f]
    for row in rows:
        if row['step'] == step:
            break
        env.step(row['decision_id'], row['index'])
    tp._guide['formed_mine'] = True
    for k in range(4):
        snap = json.loads(env.snapshot_json())
        st, actor = snap['state'], snap.get('player')
        p = st['players'][actor]
        r = p['resources']
        print(f"[{k}] {p['faction']} ore {r['ore']} cr {r['credits']} qic {r['qic']} formed {tp._formed_gaia_hexes(st, actor)}")
        scores = []
        for c in snap['candidates']:
            t = c['action'].get('type')
            if t == 'FreeAction':
                scores.append((BLOCKED, PREFIX+'test: pruned'))
            else:
                scores.append((100.0 if t == 'Pass' else 50.0, 'test'))
        out = tp.formed_mine_scores(env, snap, scores)
        if out is scores:
            print('  unchanged')
            break
        top = max(range(len(out)), key=lambda i: out[i][0])
        print('  top', json.dumps(snap['candidates'][top]['action'], ensure_ascii=False), '|', out[top][1][-110:])
        print('  pass blocked', all(out[i][0] == BLOCKED for i, c in enumerate(snap['candidates'])
                                    if c['action'].get('type') == 'Pass'))
        env = env.fork(snap['decision_id'], top)
        if snap['candidates'][top]['action'].get('type') == 'Build':
            p2 = json.loads(env.snapshot_json())['state']['players'][actor]
            print('  after build structures', [s['hex'] for s in p2['structures']], 'resources', {
                x: p2['resources'][x] for x in ('ore', 'credits', 'qic')})
            break


if __name__ == '__main__':
    main()
