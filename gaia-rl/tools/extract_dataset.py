"""Replay teacher_ab games and write one row per action-phase position for value learning.

Every finished game under the given run directories (`*/pair-*/game-*/` with a complete
`result.json` and `decisions.jsonl.gz`) is replayed from its seed with the recorded
choices. A replay must reproduce every recorded decision id and the recorded final scores,
otherwise the game is skipped and reported (e.g. recorded under another engine build).

Each row holds, for all four players at that position:
- `terms`: the shared teacher's `potential` split into its additive terms, plus the two
  cycle-017 pass terms (facts the learner may re-weight; no weights are stored);
- `facts`: rule facts (resources, income, buildings, research, planet types, ...);
- `potential`: the teacher's own value (sum of the original terms);
and the targets `final_vp` (all four) for later relabelling (own VP, VP minus the others'
mean, rank, ...).

Run from gaia-rl/ with the teacher tree on the path:
  GAIA_ENGINE_FIXES_2=1 PYTHONPATH=python:baseline-teacher-20260917:tools \\
    .venv/bin/python tools/extract_dataset.py runs/ab-* --output datasets/positions.jsonl.gz
"""
import argparse
import gzip
import json
from pathlib import Path
import sys

MAX_DECISIONS = 2000   # as tools/teacher_ab.py
RESOURCE_KEYS = ('ore', 'credits', 'knowledge', 'qic')
TRACKS = ('terraforming', 'navigation', 'ai', 'gaia', 'economy', 'science')
BUILDINGS = ('Mine', 'TradingStation', 'ResearchLab', 'PlanetaryInstitute', 'Academy')
INCOME_COLUMNS = ('ore', 'credits', 'knowledge', 'qic', 'power', 'tokens', 'vp')


def potential_terms(state, actor, home):
    """`four_factions.value.potential` (guide_tracks off) as named additive terms.

    The sum equals potential() exactly (tools/test_extract_dataset.py checks it).
    """
    from four_factions import value as v
    from strategy_teacher import distance
    player = state['players'][actor]
    horizon = max(0, 6-state['round'])
    income = v.production(state, player, include_booster=False)
    future = dict(zip(RESOURCE_KEYS, income[:4]))
    resources, power = player['resources'], player['resources']['power']
    t = {'vp': player['vp'], 'standings': v.standings(state, actor),
         'research_vp': 4*sum(max(0, level-2) for level in player['research_tracks'].values())}
    if horizon:
        t['materials'] = v.materials(resources)
        t['power'] = v.power_value(power)
        t['forming'] = (.6 if player['faction'] == 'Terrans' else .2)*power['gaia_forming']
    else:
        t['terminal_resources'] = sum(resources[k] for k in ('ore', 'credits', 'knowledge'))/3
        t['terminal_power'] = (power['bowl3'] + 3*(power['brainstone'] == 'Area3'))/3
    t['income'] = .7*horizon*(v.materials(future) + .5*income[4] + .4*income[5] + income[6])
    if horizon and (player['passed'] or state['round'] == 0):
        booster = v.INCOME['boosters'].get(str(player['booster']), [0]*7)
        t['passed_booster'] = .7*(v.materials(dict(zip(RESOURCE_KEYS, booster[:4])))
                                  + .5*booster[4] + .4*booster[5])
    t['structures'] = min(horizon, 2)*2*len(player['structures'])
    t['ships'] = min(horizon, 2)*2*len(player['explored_ships'])
    if player['faction'] == 'Taklons' and any(s['kind'] == 'PlanetaryInstitute' for s in player['structures']):
        owners = {b['owner'] for c, cell in state['board']['hexes'].items()
                  if any(distance(c, s['hex']) <= 2 for s in player['structures'])
                  for b in cell['structures'] if b['owner'] != actor}
        t['taklons_neighbours'] = horizon*min(2, len(owners))
    t['gaia'] = v.gaia_value(state, player)
    t['expansion'] = v.expansion_value(state, player, home=home) if horizon else 0
    t['research_options'] = v.research_options(state, player)
    t['advanced'] = sum(v.advanced_option(state, player, tile) for tile in player['advanced_tech_tiles'])
    active = set(player['tech_tiles'])-set(player['covered_tech_tiles'])
    t['tile_options'] = .5*horizon*len(active - {2, 3, 5, 4, 7, 9, 11, 13})
    return {k: float(x) for k, x in t.items()}


def pass_terms(state, actor):
    """Cycle 017's terms for an unpassed action-phase player (0 otherwise)."""
    import teacher_patches as tp
    player = state['players'][actor]
    if state['round'] < 1 or player['passed'] or not tp._action_phase(state):
        return {'pending_pass_vp': 0.0, 'pending_booster': 0.0}
    best = max((tp.booster_income_value(b) for b in state['boosters']), default=0) if 6-state['round'] > 0 else 0
    return {'pending_pass_vp': float(tp.booster_pass_vp(state, player)), 'pending_booster': float(best)}


def facts(state, actor):
    from four_factions import value as v
    from research_plans.value import final_metric
    player = state['players'][actor]
    resources, power = player['resources'], player['resources']['power']
    kinds = [s['kind'] if isinstance(s['kind'], str) else next(iter(s['kind'])) for s in player['structures']]
    income = v.production(state, player, include_booster=False)
    f = {f'res_{k}': resources[k] for k in RESOURCE_KEYS}
    f.update({f'power_{k}': power[k] for k in ('bowl1', 'bowl2', 'bowl3', 'gaia_bowl', 'gaia_forming')})
    f['brainstone_area3'] = int(power['brainstone'] == 'Area3')
    f.update({f'income_{k}': x for k, x in zip(INCOME_COLUMNS, income)})
    f.update({f'n_{b}': kinds.count(b) for b in BUILDINGS})
    f.update({f'track_{k}': player['research_tracks'][k] for k in TRACKS})
    for condition in ('MostPlanetTypes', 'MostGaiaPlanets', 'MostSectors', 'MostSatellites', 'MostBuildings'):
        f[condition] = final_metric(state, player, condition)
    f['federations'] = len(player['federation_tokens']) + len(player['gray_federation_tokens'])
    f['tech_tiles'] = len(set(player['tech_tiles']) - set(player['covered_tech_tiles']))
    f['advanced_tiles'] = len(player['advanced_tech_tiles'])
    f['ships'] = len(player['explored_ships'])
    f['artifacts'] = len(player['artifacts'])
    f['formers_free'] = max(0, player['gaiaformers_total'] - player['gaiaformers_deployed']
                            - player['gaiaformers_in_gaia_area'] - resources['spent_gaia_formers'])
    f['passed'] = int(player['passed'])
    f['turn_position'] = state['turn_order'].index(player['player_id']) if player['player_id'] in state['turn_order'] else -1
    return {k: float(x) for k, x in f.items()}


def games(run_dirs):
    for run in run_dirs:
        for result_path in sorted(Path(run).glob('pair-*/game-*/result.json')):
            result = json.loads(result_path.read_text())
            trace = result_path.with_name('decisions.jsonl.gz')
            if result.get('complete') and trace.exists():
                yield result_path.parent, result, trace


def replay(game_dir, result, trace, every):
    """Yield (snapshot) at recorded action-phase decisions; verify ids and final scores."""
    from gaia_rl import Environment
    env = Environment(result['seed'], MAX_DECISIONS)
    snapshot = json.loads(env.snapshot_json())
    with gzip.open(trace, 'rt') as rows:
        for n, line in enumerate(rows):
            row = json.loads(line)
            if row['decision_id'] != snapshot['decision_id'] or row['step'] != snapshot['steps']:
                raise ValueError(f'replay diverged at step {row["step"]}')
            if 'ActionPhase' in snapshot['state']['phase'] and n % every == 0:
                yield snapshot
            env.step(row['decision_id'], row['index'])
            snapshot = json.loads(env.snapshot_json())
    if not env.is_terminal():
        raise ValueError('trace ended before the game did')
    final = dict(snapshot['state']['phase']['Ended']['final_scores'])
    recorded = {int(k): v for k, v in result['scores'].items()}
    if {i: final[p['player_id']] for i, p in enumerate(snapshot['state']['players'])} != recorded:
        raise ValueError(f'replayed final scores {final} differ from recorded {recorded}')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('runs', nargs='+', help='teacher_ab output directories')
    parser.add_argument('--output', required=True)
    parser.add_argument('--every', type=int, default=1, help='Keep every Nth recorded decision')
    args = parser.parse_args()
    import fast_teacher
    fast_teacher.install()
    from faction_teachers.profiles import profiles
    homes = {name: profile.home for name, profile in profiles().items()}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    kept = skipped = rows = 0
    seen = set()
    with gzip.open(args.output, 'wt') as out:
        for game_dir, result, trace in games(args.runs):
            # The same seed and choices can appear in several runs (e.g. smoke reruns).
            key = (result['seed'], trace.read_bytes())
            if key in seen:
                continue
            seen.add(key)
            buffered = []
            try:
                for snapshot in replay(game_dir, result, trace, args.every):
                    state = snapshot['state']
                    players = []
                    for i, p in enumerate(state['players']):
                        terms = potential_terms(state, i, homes[p['faction']])
                        players.append({'faction': p['faction'], 'terms': {**terms, **pass_terms(state, i)},
                                        'facts': facts(state, i), 'potential': sum(terms.values())})
                    buffered.append({'game': str(game_dir), 'seed': result['seed'], 'step': snapshot['steps'],
                                     'round': state['round'], 'to_move': snapshot['player'], 'players': players})
            except ValueError as error:
                skipped += 1
                print(f'skip {game_dir}: {error}', file=sys.stderr)
                continue
            final = [result['scores'][str(i)] for i in range(4)]
            for row in buffered:
                row['final_vp'] = final
                out.write(json.dumps(row, allow_nan=False)+'\n')
            kept += 1
            rows += len(buffered)
            print(f'{game_dir}: {len(buffered)} positions', file=sys.stderr, flush=True)
    print(json.dumps({'games': kept, 'skipped': skipped, 'positions': rows, 'output': args.output}))


if __name__ == '__main__':
    main()
