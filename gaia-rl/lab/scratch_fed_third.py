"""Where does a teacher seat stop on the way to three federations (HANDOFF E173, the design after two debate rounds)?

federation_chances.py sums decisions with a legal federation; it does not know how many federations the seat already
has nor whether a legal one was formed in the end. This replays each game (seed + decision log, snapshots only,
nothing is written to the run) and follows every seat stage by stage: stage k = the seat has formed k federations
(FormFederation actions) and the next one is open. At each of the seat's main-turn decisions (the candidate list holds
Pass) it records whether a FormFederation candidate is legal. Per stage:
  formed          the next federation was formed: rounds from the first legal decision to forming, and how many main
                  actions (anything but FormFederation and FreeAction) were played while it was legal
  left            never formed, legal at the seat's last main-turn decision of the game
  lost            never formed, legal at some decision, not legal at the last one
  never           never legal
"Legal" is the presence of a candidate, nothing more: why a seat never had one (buildings, satellites, power value)
and whether forming was the better move are read from single decisions afterwards (explain), not from this count.

  scratch_fed_third.py <run dir> [<run dir> ...] [--limit N] [--output seats.json]
"""
import argparse
import gzip
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(ROOT/'python'), str(ROOT/'tools')]


def new_stage():
    return {'first_round': None, 'first_step': None, 'formed_round': None, 'skipped': 0, 'legal_now': False,
            'instead': Counter()}


def replay(game_dir, result, Environment):
    env = Environment(result['seed'], 2000)
    seats = [{'stages': [new_stage()], 'last_round': None} for _ in result['factions']]
    with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
        rows = [json.loads(line) for line in f]
    for step, row in enumerate(rows):
        snapshot = json.loads(env.snapshot_json())
        state = snapshot['state']
        if 'ActionPhase' in str(state['phase']) and snapshot.get('player') is not None:
            types = [c['action'].get('type') for c in snapshot['candidates']]
            if 'Pass' in types:                                    # the seat's own turn, not a charge or a follow-up
                seat = seats[snapshot['player']]
                stage = seat['stages'][-1]
                played = types[row['index']]
                legal = 'FormFederation' in types
                stage['legal_now'] = legal
                seat['last_round'] = state['round']
                if legal and stage['first_round'] is None:
                    stage['first_round'], stage['first_step'] = state['round'], step
                if played == 'FormFederation':
                    stage['formed_round'] = state['round']
                    seat['stages'].append(new_stage())
                elif legal and played != 'FreeAction':
                    stage['skipped'] += 1
                    stage['instead'][played] += 1
        env.step(row['decision_id'], row['index'])
    scores = dict(env.final_scores())
    out = []
    for number, seat in enumerate(seats):
        stages = []
        for stage in seat['stages']:
            status = ('formed' if stage['formed_round'] is not None else 'never' if stage['first_round'] is None
                      else 'left' if stage['legal_now'] else 'lost')
            stages.append({'status': status, 'first_round': stage['first_round'], 'first_step': stage['first_step'],
                           'formed_round': stage['formed_round'], 'skipped': stage['skipped'],
                           'instead': dict(stage['instead'])})
        out.append({'game': str(game_dir), 'seat': number, 'faction': result['factions'][number],
                    'final': scores[number], 'formed': len(seat['stages'])-1, 'last_round': seat['last_round'],
                    'stages': stages})
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run_dirs', type=Path, nargs='+')
    parser.add_argument('--limit', type=int, help='games per run directory (timing)')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    from gaia_rl import Environment
    start = time.monotonic()
    seats, games = [], 0
    for run_dir in args.run_dirs:
        count = 0
        for game_dir in sorted(run_dir.expanduser().glob('pair-*/game-*')):
            result = json.loads((game_dir/'result.json').read_text())
            if not result.get('complete') or (args.limit and count >= args.limit):
                continue
            seats += replay(game_dir, result, Environment)
            count += 1
        games += count
    print(f'games {games} | seats {len(seats)} | seconds {time.monotonic()-start:.0f}')
    print('federations formed per seat (FormFederation actions):', sorted(Counter(s['formed'] for s in seats).items()),
          '| mean', round(sum(s['formed'] for s in seats)/len(seats), 2),
          '| last main-turn round not 6:', sum(s['last_round'] != 6 for s in seats))
    for k in range(3):
        at = [s for s in seats if len(s['stages']) > k]
        status = Counter(s['stages'][k]['status'] for s in at)
        formed = [s['stages'][k] for s in at if s['stages'][k]['status'] == 'formed']
        delay = Counter(min(st['formed_round']-st['first_round'], 2) for st in formed)
        print(f"\nstage {k} -> {k+1}: seats {len(at)} | formed {status['formed']} | left (legal at the end) "
              f"{status['left']} | lost {status['lost']} | never legal {status['never']}")
        if formed:
            print(f"  formed: rounds from first legal to forming 0 / 1 / 2+ = {delay[0]} / {delay[1]} / {delay[2]} | "
                  f"round formed {sorted(Counter(st['formed_round'] for st in formed).items())} | "
                  f"main actions played while legal: mean {sum(st['skipped'] for st in formed)/len(formed):.2f}, "
                  f"none {sum(st['skipped'] == 0 for st in formed)}")
        for name in ('left', 'lost'):
            rows = [s['stages'][k] for s in at if s['stages'][k]['status'] == name]
            if rows:
                instead = Counter()
                for st in rows:
                    instead.update(st['instead'])
                print(f"  {name}: first legal round {sorted(Counter(st['first_round'] for st in rows).items())} | "
                      f"main actions played while legal: mean {sum(st['skipped'] for st in rows)/len(rows):.1f} | "
                      f"top {instead.most_common(6)}")
        by_faction = defaultdict(Counter)
        for s in at:
            by_faction[s['faction']][s['stages'][k]['status']] += 1
        print('  by faction (formed/left/lost/never): ' + ' · '.join(
            f"{f} {c['formed']}/{c['left']}/{c['lost']}/{c['never']}" for f, c in sorted(by_faction.items())))
        for name in ('left', 'lost', 'never'):
            rows = [s for s in at if s['stages'][k]['status'] == name]
            rows.sort(key=lambda s: -s['stages'][k]['skipped'])
            for s in rows[:3]:
                st = s['stages'][k]
                print(f"  example {name}: {Path(s['game']).parent.parent.name[4:7]} {Path(s['game']).parent.name}/"
                      f"{Path(s['game']).name} seat {s['seat']} {s['faction']} final {s['final']} first legal "
                      f"R{st['first_round']} step {st['first_step']} skipped {st['skipped']}")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(seats))
        print('\nwritten', args.output)


if __name__ == '__main__':
    main()
