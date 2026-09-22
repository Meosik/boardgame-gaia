"""One preregistered 8-pair teacher comparison. No training, promotion or UI publication."""
import argparse
import gzip
import json
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'gaia-rl/experiments'))
from economy.evaluate import digest, run_game, summary, write
from economy.teacher import EconomyTeacher
from federation.teacher import FederationTeacher, power
from gaia_rl.versions import require_current_sources, require_compatible_versions


def extra_metrics(replay, seat):
    already_power = outside_power = labs_inside = absorbed_builds = 0
    for old, new in zip(replay['frames'], replay['frames'][1:]):
        if new['player'] != seat:
            continue
        a = new['action']
        player = next(p for p in old['state']['players'] if p['player_id'] == seat)
        after = next(p for p in new['state']['players'] if p['player_id'] == seat)
        coord = a.get('coord')
        if a['type'] in ('Upgrade', 'RebellionFreeTradingStation', 'TwilightFreeResearchLab'):
            structure = next(s for s in player['structures'] if s['hex'] == coord)
            target = a.get('to') or ('TradingStation' if a['type'] == 'RebellionFreeTradingStation' else 'ResearchLab')
            delta = power(player, target) - power(player, structure['kind'])
            inside = coord in player['federated_hexes']
            already_power += int(inside and delta > 0)
            outside_power += int(not inside and delta > 0)
            labs_inside += int(inside and structure['kind'] == 'TradingStation' and target == 'ResearchLab')
        elif coord and coord not in player['federated_hexes'] and coord in after['federated_hexes']:
            absorbed_builds += 1
    return {'power_increasing_upgrades_inside': already_power,
            'power_increasing_upgrades_outside': outside_power,
            'lab_upgrades_inside': labs_inside, 'builds_absorbed_into_existing': absorbed_builds}


def summarize(rows):
    report = summary(rows)
    for faction, item in report.items():
        complete = [r for r in rows if r['faction'] == faction and r['complete']]
        item['three_or_more_federations'] = sum(r['metrics']['federations'] >= 3 for r in complete)
        item['federations_per_game'] = [r['metrics']['federations'] for r in complete]
        item['extra_totals'] = {k: sum(r['extra'][k] for r in complete) for k in (
            'power_increasing_upgrades_inside', 'power_increasing_upgrades_outside',
            'lab_upgrades_inside', 'builds_absorbed_into_existing')}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    old_dir = ROOT/'gaia-rl/runs/economy-teacher-v3'
    old_manifest = json.loads((old_dir/'manifest.json').read_text())
    versions = old_manifest['versions']
    sources = {'original': ROOT/'gaia-rl/experiments', 'economy': ROOT/'gaia-rl/experiments/economy',
               'federation': Path(__file__).parent}
    hashes = {k: digest(v.glob('*.py')) for k, v in sources.items()}
    def guard():
        require_current_sources(ROOT)
        require_compatible_versions(versions)
        if hashes != {k: digest(v.glob('*.py')) for k, v in sources.items()}:
            raise ValueError('Source changed during comparison')
        if hashes['original'] != old_manifest['original_experiment_hash'] or hashes['economy'] != old_manifest['economy_experiment_hash']:
            raise ValueError('Pinned baseline source changed')
    guard()
    if args.output.exists():
        parser.error('Output must be new')
    args.output.mkdir(parents=True)
    originals = [json.loads((old_dir/f'game-{i}.json').read_text()) for i in range(8)]
    write(args.output/'manifest.json', {'versions': versions, 'source_hashes': hashes, 'training_steps': 0,
          'source': str(old_dir), 'games': old_manifest['games'],
          'design': 'Soft local three-federation preparation, no ban/reward/model changes; lab upgrades neutral; satellite-goal exception.',
          'warning': 'Fixed coefficients before evaluation; 4 previously observed maps x 2 factions, random opponents; no generalization claim.'})
    all_rows = {'control': [], 'federation': []}
    start = time.monotonic()
    try:
        for i, original in enumerate(originals):
            for arm, policy in (('control', EconomyTeacher()), ('federation', FederationTeacher())):
                result, replay = run_game(original, policy, versions, hashes['economy' if arm == 'control' else 'federation'])
                if replay:
                    result['extra'] = extra_metrics(replay, original['seat'])
                    replay['metadata'].update(policy=f'{arm}_teacher', source_hashes=hashes)
                write(args.output/f'{arm}-{i}.json', result)
                if replay:
                    with gzip.open(args.output/f'{arm}-{i}.json.gz', 'wt') as f:
                        json.dump(replay, f, separators=(',', ':'))
                all_rows[arm].append(result)
                if arm == 'control' and (not result['complete'] or result['vp'] != original['vp'] or result['steps'] != original['steps']
                       or {str(k): v for k, v in result['scores'].items()} != original['scores']
                       or [c['action'] for c in result['choices']] != [c['action'] for c in original['choices']]):
                    raise ValueError(f'Control does not reproduce saved economic evaluation: {i}')
                print(arm, i, original['faction'], result.get('vp', result.get('error')),
                      'federations', result.get('metrics', {}).get('federations'), flush=True)
        guard()
        write(args.output/'report.json', {**{a: summarize(r) for a, r in all_rows.items()},
              'all_complete': all(r['complete'] for rows in all_rows.values() for r in rows),
              'seconds': time.monotonic()-start, 'promotion': False})
    except Exception:
        (args.output/'failure.log').write_text(traceback.format_exc())
        raise


if __name__ == '__main__':
    main()
