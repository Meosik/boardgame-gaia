"""Audit persisted pairs without playing more games or changing policies."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'gaia-rl/experiments'))
from integrated.boosters import pass_vp
from integrated.features import PASS, counters
from source_routes.evaluate import hashes
from gaia_rl.versions import require_current_sources, require_compatible_versions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    run = args.run
    manifest = json.loads((run/'manifest.json').read_text())
    assert manifest['source_hashes'] == hashes()
    require_current_sources(ROOT)
    require_compatible_versions(manifest['versions'])
    for line in (run/'native-source-manifest.txt').read_text().splitlines():
        digest, name = line.split('  ', 1)
        assert hashlib.sha256((run/'native-source'/name).read_bytes()).hexdigest() == digest
    rows = []
    passes = eclipses = 0
    for arm in ('control', 'candidate'):
        for i, spec in enumerate(manifest['games']):
            result = json.loads((run/f'{arm}-{i}.json').read_text())
            assert result['complete'], result.get('error')
            replay = json.load(gzip.open(run/f'{arm}-{i}.json.gz'))
            assert replay['metadata']['versions'] == manifest['versions']
            assert replay['metadata']['scores'] == result['scores']
            assert replay['metadata']['steps'] == result['steps'] == len(replay['frames'])-1
            assert replay['frames'][-1]['event_end'] == len(replay['events'])
            seat = spec['seat']
            formations = focal_passes = asteroid_builds = eclipse_builds = 0
            for before, after in zip(replay['frames'], replay['frames'][1:]):
                assert after['decision_id'] == before['decision_id']+1
                assert before['event_end'] <= after['event_end'] <= len(replay['events'])
                old = next(p for p in before['state']['players'] if p['player_id'] == seat)
                new = next(p for p in after['state']['players'] if p['player_id'] == seat)
                count = lambda p: len(p['federation_tokens'])+len(p['gray_federation_tokens'])-int(p['research_tracks']['terraforming'] == 5)
                formations += count(new)-count(old)
                a = after['action']
                if a['type'] == 'EclipseAsteroidMine':
                    actor = after['player']
                    was = next(p for p in before['state']['players'] if p['player_id'] == actor)
                    now = next(p for p in after['state']['players'] if p['player_id'] == actor)
                    assert was['resources']['spent_gaia_formers'] == now['resources']['spent_gaia_formers']
                    assert was['resources']['credits']-now['resources']['credits'] == 6
                    assert was['resources']['ore'] == now['resources']['ore']
                    eclipses += 1
                if after['player'] != seat:
                    continue
                if a['type'] == 'Build':
                    asteroid_builds += before['state']['board']['hexes'][a['coord']]['planet']['planet_type'] == 'Asteroid'
                eclipse_builds += a['type'] == 'EclipseAsteroidMine'
                if a['type'] == 'Pass':
                    c = counters(before['state'], old)
                    tech = sum(c[PASS[t][0]]*PASS[t][1] for t in old['advanced_tech_tiles'] if t in PASS)
                    econ = int(after['state']['round'] > before['state']['round'] and new['research_tracks']['economy'] in (3, 4)
                               and after['state']['research_board']['economy_research_tile_side'] == 'VictoryPoints')
                    assert new['vp']-old['vp'] == pass_vp(before['state'], old, old['booster'])+tech+econ
                    assert new['booster'] == a.get('booster_id')
                    passes += 1
                    focal_passes += 1
            assert focal_passes == 6
            assert formations == result['metrics']['federations']
            rows.append({'arm': arm, 'game': i, 'faction': result['faction'], 'vp': result['vp'],
                         'asteroid_builds': asteroid_builds, 'eclipse_builds': eclipse_builds,
                         'research': result['research'], 'metrics': result['metrics']})
    summary = {}
    for arm in ('control', 'candidate'):
        items = [r for r in rows if r['arm'] == arm]
        summary[arm] = {'mean_vp': statistics.mean(r['vp'] for r in items),
            'faction_mean': {f: statistics.mean(r['vp'] for r in items if r['faction'] == f) for f in ('Xenos', 'HadschHallas')},
            'mean_tracks': {k: statistics.mean(r['research']['final_tracks'][k] for r in items)
                            for k in items[0]['research']['final_tracks']},
            'advanced_acquired': sum(len(r['research']['advanced_acquired']) for r in items),
            'asteroid_builds': sum(r['asteroid_builds'] for r in items),
            'eclipse_builds': sum(r['eclipse_builds'] for r in items),
            'federations': sum(r['metrics']['federations'] for r in items),
            'six_credit_ts': sum(r['metrics']['six_credit_trading_stations'] for r in items),
            'three_ore_step_builds': sum(r['metrics']['three_ore_step_builds'] for r in items),
            'known_tf_mars_anomalies': sum(r['metrics']['engine_cost_anomalies'] for r in items)}
    report = {'summary': summary, 'games': rows, 'passes_checked': passes, 'eclipse_actions_checked_all_players': eclipses,
              'verified': 'All replay scores/steps/event offsets/pass VP/formations/native-source hashes'}
    with (run/'paired_analysis.json').open('x') as f:
        json.dump(report, f, indent=2)
    print(json.dumps(summary, indent=2))
    print(report['verified'])


if __name__ == '__main__':
    main()
