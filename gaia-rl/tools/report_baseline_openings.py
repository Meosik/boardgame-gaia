"""Replay existing decision indices only; never call a teacher or start a match."""
import argparse
from collections import Counter
from dataclasses import asdict
import gzip
import json
from pathlib import Path
import sys

import teacher_ab as ab
from build_opening_teacher import ALLOWED


def label(counts):
    symbols = (('planetary_institute', 'PI'), ('academy', 'AC'), ('research_lab', 'RL'),
               ('trading_station', 'TS'), ('mine', 'M'))
    return '+'.join(f'{counts[key]}{symbol}' for key, symbol in symbols if counts[key]) or '0'


def report(output):
    from gaia_rl import Environment
    from gaia_rl.versions import runtime_versions
    baseline = ab.resolve_teacher('baseline')
    assert not ab.frozen_problems(baseline)
    sys.path.insert(0, baseline['source'])
    from bgg_openings.inventory import building_counts
    current_engine = runtime_versions()['engine_build_id']
    fingerprint = ab.fingerprint(baseline)
    rows, excluded = [], []
    for manifest in sorted((ab.ROOT/'gaia-rl/runs').glob('*/manifest.json')):
        record = json.loads(manifest.read_text())
        signature = record.get('signature', record)
        teacher = signature.get('teachers', {}).get('A', {})
        if teacher.get('name') != 'baseline':
            continue
        if (teacher.get('fingerprint') != fingerprint or teacher.get('kwargs') != baseline['kwargs']
                or teacher.get('factory') != baseline['factory']):
            excluded.append({'path': str(manifest), 'reason': 'A source/configuration differs'})
            continue
        if signature.get('versions', {}).get('engine_build_id') != current_engine:
            excluded.append({'path': str(manifest), 'reason': 'native build differs; cannot certify index replay'})
            continue
        for trace in sorted(manifest.parent.rglob('decisions.jsonl.gz')):
            result_path = trace.with_name('result.json')
            if not result_path.exists():
                excluded.append({'path': str(trace), 'reason': 'missing seed/seat result metadata'})
                continue
            result = json.loads(result_path.read_text())
            env = Environment(result['seed'], ab.MAX_DECISIONS)
            before = json.loads(env.snapshot_json())
            boundary = None
            try:
                with gzip.open(trace, 'rt') as stream:
                    for line in stream:
                        decision = json.loads(line)
                        assert decision['decision_id'] == before['decision_id']
                        assert decision['step'] == before['steps']
                        assert decision['seat'] == before['player']
                        assert decision['arm'] == ('A' if before['player'] in result['a_seats'] else 'B')
                        env.step(decision['decision_id'], decision['index'])
                        after = json.loads(env.snapshot_json())
                        if before['state']['round'] == 1 and after['state']['round'] == 2:
                            boundary = before
                            break
                        before = after
            except (AssertionError, EOFError, OSError, ValueError, RuntimeError) as error:
                excluded.append({'path': str(trace), 'reason': f'replay failed: {type(error).__name__}: {error}'})
                continue
            if boundary is None:
                excluded.append({'path': str(trace), 'reason': 'R1 not finished in recorded prefix'})
                continue
            for player in boundary['state']['players']:
                if player['player_id'] not in result['a_seats'] or player['faction'] not in ALLOWED:
                    continue
                counts = asdict(building_counts(player))
                opening = label(counts)
                rows.append({'game': str(trace.parent.relative_to(ab.ROOT)), 'seed': result['seed'],
                             'seat': player['player_id'], 'faction': player['faction'],
                             'opening': opening, 'allowed': opening in ALLOWED[player['faction']],
                             'r1_decision_id': boundary['decision_id'], 'counts': counts,
                             'whole_game_complete': result['complete']})
    summary = {}
    for faction in ALLOWED:
        observations = [row for row in rows if row['faction'] == faction]
        hits = sum(row['allowed'] for row in observations)
        summary[faction] = {'n': len(observations), 'distribution': dict(Counter(r['opening'] for r in observations)),
                            'allowed_count': hits, 'allowed_rate': hits/len(observations) if observations else None}
    output.mkdir(parents=True, exist_ok=True)
    ab.write_json(output/'baseline-r1.json', {'summary': summary, 'observations': rows,
                  'excluded': excluded, 'baseline_fingerprint': fingerprint, 'engine_build_id': current_engine,
                  'games_run': 0, 'scope': 'A seats only; matching frozen A and native build; recorded R1 fully replayed'})
    lines = ['| 기존 A 종족(참고용) | 관측 수 | R1 종료 조합 분포 | 지정 목록 비율 | 70% 이상 |',
             '|---|---:|---|---:|---|']
    for faction, row in summary.items():
        n, rate = row['n'], row['allowed_rate']
        distribution = '; '.join(f'{key}: {count}/{n} ({count/n:.1%})' for key, count in sorted(row['distribution'].items()))
        lines.append(f'| {faction} | {n} | {distribution or "—"} | '
                     f'{rate:.1%} | {"해당" if rate >= .7 else "아니오"} |' if rate is not None else
                     f'| {faction} | 0 | — | — | 판정 불가 |')
    (output/'baseline-r1.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))
    print(json.dumps({'recorded_games': len({r['game'] for r in rows}), 'excluded': excluded}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    report(parser.parse_args().output)
