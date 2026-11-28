"""146: decisions where a federation-plan goal was compared (read-only): winner, gap, plan first move."""
import gzip
import json

PATH = '/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-146-fedplan-one-game/pair-000/game-0-A02/decisions.jsonl.gz'
rows = [json.loads(l) for l in gzip.open(PATH)]
for r in rows:
    comp = r.get('compared') or []
    plans = [c for c in comp if str(c.get('goal', '')).startswith('federation-plan')]
    if not plans:
        continue
    done = [c for c in comp if c.get('complete') and c.get('value') is not None]
    best = max(done, key=lambda c: c['value']) if done else None
    print(f"step {r['step']} R{r['round']} seat {r['seat']} selected={r['selected']} chosen_idx={r['index']} "
          f"best={best['goal'] if best else None}:{best['value'] if best else None} first={best['first'] if best else None}")
    for c in plans:
        same = [o['goal'] for o in comp if o is not c and o.get('first') == c.get('first')]
        gap = (c['value'] - best['value']) if best and c.get('value') is not None else None
        print(f"   {c['goal']} first={c['first']} value={c.get('value')} complete={c.get('complete')} "
              f"gap={gap if gap is None else round(gap, 2)} same_first={same}")
    print(f"   chosen: {json.dumps(r['chosen'].get('action'))[:160]}")
    print(f"   all:{[(c['goal'], c.get('first'), c.get('value')) for c in comp]}")
