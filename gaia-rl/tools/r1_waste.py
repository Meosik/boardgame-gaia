"""Flag round-1 "waste review candidates" per seat in a lab A/B run (candidates for human review, not defects).

Per seat in the chosen round: ship entries (ExploreSpaceship moves) with resources before/after and
whether a ship action was legal at the seat's next turn; ship actions used; at the seat's Pass move,
the legal ship-action and GaiaFormation candidates and the GaiaFormation moves made in the round.
Flags: ship-unused (entries>0, no ship action used), gaia-skipped (GaiaFormation legal at pass, none used).
Each game is replayed only until state['round'] > --round.

  GAIA_ENGINE_FIXES_2=1 PYTHONPATH=gaia-rl/python:gaia-rl/baseline-teacher-20260917:gaia-rl/tools \\
    gaia-rl/.venv/bin/python gaia-rl/tools/r1_waste.py ~/projects/gaia-lab/gaia-rl/runs/lab-108d-.../ [--round 1] [--details]
"""
import argparse
import gzip
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(ROOT/'python'), str(ROOT/'tools')]

# Lost Fleet spaceship actions (Appendix II action spaces, Credit action, artifact, ship-granted
# range/gaia actions). Source: the GameAction enum in gaia-engine/src/rules/actions.rs. Entry moves
# (types containing 'ExploreSpaceship') and the Gleens/Space Giants exploration-board actions are excluded.
SHIP_ACTION_TYPES = {
    'SpaceshipCreditTerraform', 'ExamineArtifact',
    'TwilightFreeResearchLab', 'TwilightReplayFederationToken', 'TwilightRangeBuild', 'TwilightRangeGaiaFormation',
    'RebellionFreeTradingStation', 'RebellionCreditsAndQic', 'RebellionGainTechTile',
    'TFMarsTechBonus', 'TFMarsGaiaFormation',
    'EclipsePlanetTypeBonus', 'EclipseResearchBoost', 'EclipseAsteroidMine',
}


def res(state, seat):
    """Resources of a seat: credits/ore/knowledge/qic and power bowls 1/2/3 (state['players'][seat]['resources'])."""
    r = state['players'][seat]['resources']
    p = r['power']
    return {'c': r['credits'], 'o': r['ore'], 'k': r['knowledge'], 'q': r['qic'],
            'p1': p['bowl1'], 'p2': p['bowl2'], 'p3': p['bowl3']}


def fmt(r):
    return f"c{r['c']} o{r['o']} k{r['k']} q{r['q']} p{r['p1']}/{r['p2']}/{r['p3']}"


def count(snapshot, pred):
    return sum(1 for c in snapshot['candidates'] if pred(c['action'].get('type', '')))


def is_ship(t):
    return t in SHIP_ACTION_TYPES


def replay(game_dir, rnd):
    from gaia_rl import Environment
    result = json.loads((game_dir/'result.json').read_text())
    env = Environment(result['seed'], 2000)
    with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
        rows = [json.loads(line) for line in f]
    seats = {}
    pending = []  # entries waiting for the "after" resources / next-turn legality
    def rec(seat, faction):
        return seats.setdefault(seat, {
            'faction': faction, 'arm': 'A' if seat in result['a_seats'] else 'B', 'entries': [],
            'ship_used': 0, 'gaia_used': 0, 'pass_ship': None, 'pass_gaia': None})
    def resolve(snapshot):
        state = snapshot['state']
        for e in list(pending):
            if e['after'] is None:
                e['after'] = res(state, e['seat'])
            if snapshot['player'] == e['seat']:
                e['next_ship'] = count(snapshot, is_ship)
                pending.remove(e)
    for row in rows + [None]:
        snapshot = json.loads(env.snapshot_json())
        resolve(snapshot)
        state = snapshot['state']
        if row is None or state['round'] > rnd:
            break
        seat = snapshot['player']
        if state['round'] == rnd:
            r = rec(seat, state['players'][seat]['faction'])
            t = snapshot['candidates'][row['index']]['action'].get('type', '')
            if 'ExploreSpaceship' in t:
                e = {'seat': seat, 'type': t, 'before': res(state, seat), 'after': None, 'next_ship': None}
                r['entries'].append(e)
                pending.append(e)
            elif is_ship(t):
                r['ship_used'] += 1
            elif t == 'GaiaFormation':
                r['gaia_used'] += 1
            elif t == 'Pass':
                r['pass_ship'] = count(snapshot, is_ship)
                r['pass_gaia'] = count(snapshot, lambda x: x == 'GaiaFormation')
        env.step(row['decision_id'], row['index'])
    return seats


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--round', type=int, default=1)
    parser.add_argument('--details', action='store_true')
    args = parser.parse_args()
    run_dir = args.run_dir.expanduser()
    totals = {}
    for game_dir in sorted(run_dir.glob('pair-*/game-*')):
        if not (game_dir/'result.json').exists() or not (game_dir/'decisions.jsonl.gz').exists():
            continue
        name = f'{game_dir.parent.name}/{game_dir.name}'
        for seat, r in sorted(replay(game_dir, args.round).items()):
            n = len(r['entries'])
            ship_unused = n > 0 and r['ship_used'] == 0
            gaia_skipped = bool(r['pass_gaia']) and r['gaia_used'] == 0
            t = totals.setdefault(r['arm'], {'seats': 0, 'entries': 0, 'ship': 0, 'gaia': 0})
            t['seats'] += 1
            t['entries'] += n > 0
            t['ship'] += ship_unused
            t['gaia'] += gaia_skipped
            if not (n or r['pass_ship'] or r['pass_gaia']):
                continue
            flags = ' '.join(f for f, on in (('ship-unused', ship_unused), ('gaia-skipped', gaia_skipped)) if on)
            print(f"{name} s{seat} {r['faction']} {r['arm']} entries={n} ship_used={r['ship_used']} "
                  f"pass_ship={r['pass_ship']} pass_gaia={r['pass_gaia']} gaia_used={r['gaia_used']} {flags}".rstrip())
            if args.details:
                for e in r['entries']:
                    print(f"    {e['type']} {fmt(e['before'])} -> {fmt(e['after'] or e['before'])} "
                          f"next-turn legal ship actions: {e['next_ship'] if e['next_ship'] is not None else 'n/a'}")
    print(f'summary (round {args.round})')
    for arm, t in sorted(totals.items()):
        print(f"  {arm}: seats={t['seats']} with-entries={t['entries']} ship-unused={t['ship']} gaia-skipped={t['gaia']}")


if __name__ == '__main__':
    main()
