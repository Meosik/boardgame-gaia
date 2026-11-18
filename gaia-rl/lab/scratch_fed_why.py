"""Why is the next federation never legal for a teacher seat (HANDOFF E174, after the debate)?

scratch_fed_third.py found: no legal federation is ever left unformed, the next one simply never becomes legal for most
seats. This replays the same games (seed + decision log, snapshots only, the engine is not touched) and, at each of a
seat's main-turn decisions (candidate list holds Pass), computes from snapshot['state'] the numbers the engine's
candidate generator starts from (gaia-engine/src/rules/ai_federation.rs:233-268, engine.rs:4837 federation_power_total,
engine.rs:4946 federation_minimum_power):
  need    7; Xenos with the planetary institute 6; Ivits with a federation 7 x (tokens owned - terraforming-5 token + 1)
  total   power value of the seat's buildings outside its federations (mine 1, trading station / lab 2, institute /
          academy 3, space station 1) + Bescods institute bonus on the home planet type + Moweyds rings (2 each) +
          large-building tech tile (id 6, not covered) + an untracked lost planet mine; Ivits growth: the existing
          federation's power + the new buildings
  funds   satellites the seat can pay: QIC for Ivits, power tokens in the three bowls for the rest; 25 - placed
  token   the federation token supply is not empty (spaceship tokens are not read: a seat with an empty supply is
          reported as "no supply token", not as proven tokenless)
  limit   snapshot['candidate_generation']['federation_limit_hits'] > 0 at that decision

Check against the engine (the classification is printed only when both are 0):
  A  a FormFederation candidate exists but the numbers say power short or no token
  B  a FormFederation action was played but its buildings' power (same rules) is below need

A stage that was never legal is put in one class:
  1 power short       total < need at every main-turn decision of the stage
  2 no supply token   power was enough at some decision, never together with a supply token
  3 search limit      power and token were there at some decision and the generator hit its limit at such a decision
  4 enough power, cause unconfirmed   the rest (connection, satellite funds, adjacency to the own federation, ... are
                      not decided here; satellite funds are printed as description only)

  scratch_fed_why.py <run dir> [<run dir> ...] [--limit N] [--output seats.json]
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

POWER = {'Mine': 1, 'TradingStation': 2, 'ResearchLab': 2, 'PlanetaryInstitute': 3, 'Academy': 3, 'SpaceStation': 1}


def kind_name(kind):
    return kind if isinstance(kind, str) else next(iter(kind))


def own_structures(hexes, coords, pid):
    for coord in coords:
        hex_ = hexes.get(coord)
        if hex_:
            for s in hex_['structures']:
                name = kind_name(s['kind'])
                if s['owner'] == pid and name != 'Satellite':
                    yield hex_, name


def power_of(state, player, coords, growth):
    """federation_power_total for `coords` (growth: the existing federation is added by the caller's coords)."""
    pid, hexes = player['player_id'], state['board']['hexes']
    structures = list(own_structures(hexes, coords, pid))
    total = sum(POWER[name] for _, name in structures)
    lost = state['board'].get('lost_planet')
    if (lost in coords and (hexes[lost].get('planet') or {}).get('owner') == pid
            and not any(s['hex'] == lost for s in player['structures'])):
        total += 1
    if growth:
        return total
    if player['faction'] == 'Bescods' and any(kind_name(s['kind']) == 'PlanetaryInstitute' for s in player['structures']):
        total += sum(1 for hex_, _ in structures
                     if (hex_.get('planet') or {}).get('planet_type') == 'Titanium' and not hex_['planet']['is_gaia_formed'])
    if player['faction'] == 'Moweyds':
        total += 2*sum(1 for c in coords if c in player['moweyds_power_ring_hexes'])
    if 6 in player['tech_tiles'] and 6 not in player['covered_tech_tiles']:
        total += sum(1 for _, name in structures if name in ('PlanetaryInstitute', 'Academy'))
    return total


def numbers(state, pid):
    player = next(p for p in state['players'] if p['player_id'] == pid)
    hexes = state['board']['hexes']
    federated = set(player['federated_hexes'])
    growth = player['faction'] == 'Ivits' and bool(federated)
    owned = [c for c, h in hexes.items() if c not in federated and (
        any(s['owner'] == pid and kind_name(s['kind']) != 'Satellite' for s in h['structures'])
        or ((h.get('planet') or {}).get('planet_type') == 'LostPlanet' and h['planet'].get('owner') == pid))]
    if growth:
        tokens = len(player['federation_tokens']) + len(player['gray_federation_tokens'])
        need = 7*(max(tokens - (player['research_tracks']['terraforming'] == 5), 0) + 1)
    elif player['faction'] == 'Xenos' and any(kind_name(s['kind']) == 'PlanetaryInstitute' for s in player['structures']):
        need = 6
    else:
        need = 7
    inside = power_of(state, player, list(federated), True)
    outside = power_of(state, player, owned, growth)
    bowls = player['resources']['power']
    funds = player['resources']['qic'] if player['faction'] == 'Ivits' else bowls['bowl1'] + bowls['bowl2'] + bowls['bowl3']
    placed = sum(1 for h in hexes.values() if pid in h['satellites'])
    return {'player': player, 'growth': growth, 'need': need, 'total': outside + (inside if growth else 0),
            'outside': outside, 'inside': inside, 'buildings': sum(1 for _ in own_structures(hexes, owned, pid)),
            'funds': min(funds, 25 - placed), 'token': bool(state['research_board']['federation_tokens'])}


def new_stage():
    return {'legal': False, 'formed': False, 'enough': False, 'enough_token': False, 'limit': False,
            'best_gap': None, 'enough_funds': []}


def replay(game_dir, result, Environment, checks):
    env = Environment(result['seed'], 2000)
    seats = [{'stages': [new_stage()], 'rounds': {}} for _ in result['factions']]
    with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
        rows = [json.loads(line) for line in f]
    for step, row in enumerate(rows):
        snapshot = json.loads(env.snapshot_json())
        state = snapshot['state']
        if 'ActionPhase' in str(state['phase']) and snapshot.get('player') is not None:
            types = [c['action'].get('type') for c in snapshot['candidates']]
            if 'Pass' in types:
                number = snapshot['player']
                seat, stage = seats[number], seats[number]['stages'][-1]
                n = numbers(state, number)
                enough, legal = n['total'] >= n['need'], 'FormFederation' in types
                if legal:
                    checks['legal decisions'] += 1
                    stage['legal'] = True
                    if not (enough and n['token']):
                        checks['A'] += 1
                        checks['examples'].append(f"A {game_dir.parent.name}/{game_dir.name} step {step} seat {number} "
                                                  f"{n['player']['faction']} total {n['total']} need {n['need']} token {n['token']}")
                gap = n['need'] - n['total']
                stage['best_gap'] = gap if stage['best_gap'] is None else min(stage['best_gap'], gap)
                if enough:
                    stage['enough'] = True
                    if n['token']:
                        stage['enough_token'] = True
                        if not legal:
                            stage['enough_funds'].append(n['funds'])
                            if snapshot['candidate_generation'].get('federation_limit_hits'):
                                stage['limit'] = True
                seat['rounds'][state['round']] = {'stage': len(seat['stages'])-1, 'need': n['need'], 'total': n['total'],
                                                  'outside': n['outside'], 'inside': n['inside'],
                                                  'buildings': n['buildings'], 'funds': n['funds']}
                action = snapshot['candidates'][row['index']]['action']
                if action.get('type') == 'FormFederation':
                    checks['formed actions'] += 1
                    player = n['player']
                    coords = list(action['hexes']) + (list(player['federated_hexes']) if n['growth'] else [])
                    if power_of(state, player, coords, n['growth']) < n['need']:
                        checks['B'] += 1
                        checks['examples'].append(f"B {game_dir.parent.name}/{game_dir.name} step {step} seat {number} "
                                                  f"{player['faction']} power {power_of(state, player, coords, n['growth'])} need {n['need']}")
                    stage['formed'] = True
                    seat['stages'].append(new_stage())
        env.step(row['decision_id'], row['index'])
    out = []
    for number, seat in enumerate(seats):
        last = seat['stages'][-1]
        if last['legal']:
            cause = 'legal, not formed'
        elif not last['enough']:
            cause = '1 power short'
        elif not last['enough_token']:
            cause = '2 no supply token'
        elif last['limit']:
            cause = '3 search limit'
        else:
            cause = '4 enough power, cause unconfirmed'
        out.append({'game': f"{game_dir.parent.parent.name[4:7]} {game_dir.parent.name}/{game_dir.name}",
                    'seed': result['seed'], 'seat': number, 'faction': result['factions'][number],
                    'formed': len(seat['stages'])-1, 'cause': cause, 'best_gap': last['best_gap'],
                    'enough_funds': last['enough_funds'], 'rounds': seat['rounds']})
    return out


def mean(values):
    values = list(values)
    return round(sum(values)/len(values), 2) if values else None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run_dirs', type=Path, nargs='+')
    parser.add_argument('--limit', type=int, help='games per run directory (timing)')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    from gaia_rl import Environment
    start = time.monotonic()
    checks = Counter()
    checks['examples'] = []
    seats, games = [], 0
    for run_dir in args.run_dirs:
        count = 0
        for game_dir in sorted(run_dir.expanduser().glob('pair-*/game-*')):
            result = json.loads((game_dir/'result.json').read_text())
            if not result.get('complete') or (args.limit and count >= args.limit):
                continue
            seats += replay(game_dir, result, Environment, checks)
            count += 1
        games += count
    print(f'games {games} | seats {len(seats)} | seconds {time.monotonic()-start:.0f}')
    print(f"check A (candidate exists, numbers say impossible): {checks['A']} of {checks['legal decisions']} decisions | "
          f"check B (formed below need): {checks['B']} of {checks['formed actions']} actions")
    for line in checks['examples'][:8]:
        print('  ', line)
    if checks['A'] or checks['B']:
        print('checks failed: no classification')
        return
    for k in range(3):
        at = [s for s in seats if s['formed'] == k]
        print(f"\nseats that stopped at {k} federations: {len(at)} | {sorted(Counter(s['cause'] for s in at).items())}")
        by_faction = defaultdict(Counter)
        for s in at:
            by_faction[s['faction']][s['cause'][0]] += 1
        print('  by faction (class 1/2/3/4): ' + ' · '.join(
            f"{f} {c['1']}/{c['2']}/{c['3']}/{c['4']}" for f, c in sorted(by_faction.items())))
        for round_ in (4, 5, 6):
            rows = [s['rounds'][str(round_)] if str(round_) in s['rounds'] else s['rounds'].get(round_) for s in at]
            rows = [r for r in rows if r and r['stage'] == k]
            if not rows:
                continue
            gaps = Counter(min(max(r['need']-r['total'], 0), 5) for r in rows)
            print(f"  R{round_} last main turn ({len(rows)} seats): power outside federations mean {mean(r['outside'] for r in rows)} "
                  f"(need mean {mean(r['need'] for r in rows)}) | short by 0/1/2/3/4/5+ = "
                  f"{'/'.join(str(gaps[g]) for g in range(6))} | buildings outside mean {mean(r['buildings'] for r in rows)} | "
                  f"power inside federations mean {mean(r['inside'] for r in rows)} | satellite funds mean {mean(r['funds'] for r in rows)}")
        four = [s for s in at if s['cause'][0] == '4']
        if four:
            print(f"  class 4 ({len(four)} seats): decisions with enough power and a token but no candidate, per seat mean "
                  f"{mean(len(s['enough_funds']) for s in four)} | satellite funds at those decisions: 0 = "
                  f"{sum(f == 0 for s in four for f in s['enough_funds'])}, 1-3 = {sum(1 <= f <= 3 for s in four for f in s['enough_funds'])}, "
                  f"4+ = {sum(f >= 4 for s in four for f in s['enough_funds'])} | seats whose funds were 0 at every such decision "
                  f"{sum(all(f == 0 for f in s['enough_funds']) for s in four)}")
    by_game = defaultdict(list)
    for s in seats:
        by_game[(s['game'], s['seed'])].append(s)
    totals = {g: sum(s['formed'] for s in rows) for g, rows in by_game.items()}
    print(f"\nfederations per game (4 seats): {sorted(Counter(totals.values()).items())} | every seat >= 2: "
          f"{sum(min(s['formed'] for s in rows) >= 2 for rows in by_game.values())} | every seat >= 3: "
          f"{sum(min(s['formed'] for s in rows) >= 3 for rows in by_game.values())} of {len(by_game)} games")
    for g in sorted(totals, key=lambda g: -totals[g])[:4] + sorted(totals, key=lambda g: totals[g])[:2]:
        print(f"  {g[0]} seed {g[1]}: " + ' · '.join(f"{s['faction']} {s['formed']}" for s in by_game[g]))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(seats))
        print('\nwritten', args.output)


if __name__ == '__main__':
    main()
