"""Discover native setups only by faction/seat, never board quality or scores."""
import json
from collections import Counter
from pathlib import Path
import subprocess

from gaia_rl._native import Environment
from four_factions import FACTIONS


def lineup(seed):
    snapshot = json.loads(Environment(seed).snapshot_json())
    return [p['faction'] for p in snapshot['state']['players']]


def discover(prefix, demo_games=6, validation_games=2, limit=200000):
    if min(demo_games, validation_games, limit) < 1:
        raise ValueError('Positive setup budgets required')
    pools = {'training': [], 'validation': [], 'evaluation': []}
    occupied = {f: set() for f in FACTIONS}
    root = Path(__file__).resolve().parents[3]
    helper = root/'gaia-rl/target/release/examples/faction_lineups'
    # The caller builds/tests the native helper first. A prefilter is not a
    # replacement for the independent full-environment check on every match.
    candidates = subprocess.check_output([str(helper), prefix, str(limit)], text=True).splitlines()
    for candidate in candidates:
        predicted = json.loads(candidate)
        seed = predicted['seed']
        factions = lineup(seed)
        if factions != predicted['factions']:
            raise ValueError('Native seed prefilter differs from full setup')
        if set(factions) != set(FACTIONS):
            continue
        spec = {'seed': seed, 'factions': factions}
        if len(pools['training']) < demo_games:
            pools['training'].append(spec)
        elif len(pools['validation']) < validation_games:
            pools['validation'].append(spec)
        elif all(factions.index(f) not in occupied[f] for f in FACTIONS):
            pools['evaluation'].append(spec)
            for faction in FACTIONS:
                occupied[faction].add(factions.index(faction))
        else:
            continue
        print('setup', seed, {k: len(v) for k, v in pools.items()}, flush=True)
        if len(pools['evaluation']) == 4:
            return pools
    raise RuntimeError('Setup search exhausted; no relaxed roster/seat fallback')


def validate(pools, demo_games=6, validation_games=2):
    if [len(pools[k]) for k in ('training', 'validation', 'evaluation')] != [demo_games, validation_games, 4]:
        raise ValueError('Unexpected split sizes')
    specs = [s for key in ('training', 'validation', 'evaluation') for s in pools[key]]
    if len({s['seed'] for s in specs}) != len(specs):
        raise ValueError('Overlapping setup seeds')
    for spec in specs:
        actual = lineup(spec['seed'])
        if actual != spec['factions'] or set(actual) != set(FACTIONS):
            raise ValueError('Saved quartet differs from native setup')
    for faction in FACTIONS:
        seats = Counter(s['factions'].index(faction) for s in pools['evaluation'])
        if seats != Counter(range(4)):
            raise ValueError('Unbalanced faction evaluation seats')
