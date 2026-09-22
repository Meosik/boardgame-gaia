"""Paired (d) diagnostics; no A/B matches and no automatic weight tuning."""
import argparse
from collections import Counter
import copy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from validate_bc import Configured, invariants, representative, successor, compare, write_json
from diagnose_research_bc import research_rows, tech_rows, token_rows
import state_evaluation_bquadrupleprime as variant


@dataclass(frozen=True)
class Distributed:
    def evaluate_state(self, state, actor, **kwargs):
        return variant.evaluate_state(state, actor, token_shortfall=True, remaining_income=True,
                                      distributed_research=True, **kwargs)


MODELS = {'B″+b+c': Configured(b=True, c=True), 'B⁗': Distributed()}


def pair(before, after, actor, label, conserve=True):
    return {name: compare(before, after, actor, label, 'diagnostic', conserve, model=model)
            for name, model in MODELS.items()}


def step_rows():
    rows = []
    for r in (1, 3, 6):
        for track in variant.base.TRACK_IDS:
            state, actor = representative(r)
            p = state['players'][actor]
            p['research_tracks'] = dict.fromkeys(p['research_tracks'], 0)
            p['resources']['knowledge'] = 4
            p['federation_tokens'] = [1]
            stages = []
            for level in range(6):
                p['research_tracks'][track] = level
                facts = variant.base.engine_facts(state, p)
                details = next(row for row in variant.research_progress_details(state, p, facts)
                               if row['track'] == track)
                values = {}
                for name, model in MODELS.items():
                    value = model.evaluate_state(state, actor)
                    values[name] = {'final': value.breakdown['research_final_vp'],
                                    'progress': value.breakdown['research_progress']}
                    values[name]['track_value'] = sum(values[name].values())
                stages.append({'level': level, 'details': details, 'values': values})
            for old, new in zip(stages, stages[1:]):
                threshold = next(t for t in old['details']['thresholds'] if t['next_unreached'])
                # Immediate VP belongs to current_vp, not the track-value slope.
                expected = threshold['terminal_increment']/threshold['spaces']
                actual = new['values']['B⁗']['track_value']-old['values']['B⁗']['track_value']
                rows.append({'round': r, 'track': track, 'before': old, 'after': new,
                             'expected': expected, 'actual': actual,
                             'passed': abs(expected-actual) < 1e-9 and actual >= -1e-9,
                             'controlled_level_change_only': True})
    return rows


def concentration_rows():
    rows = []
    for r in (1, 3):
        state, actor = representative(r)
        p = state['players'][actor]
        p['research_tracks'].update(terraforming=2, navigation=2, economy=2, ai=0, gaia=0, science=0)
        p['resources']['knowledge'] = 4
        for track in ('terraforming', 'navigation', 'economy', 'ai', 'gaia'):
            action = {'type': 'ResearchAdvance', 'track': variant.base.TRACK_IDS[track]}
            after = successor(state, actor, action)
            rows.append({'round': r, 'track': track, 'existing': p['research_tracks'][track] >= 2,
                         'before_state': state, 'after_state': after,
                         'values': pair(state, after, actor, track)})
    return rows


def changed_text(row):
    return '; '.join(f'{k} {v["delta"]:+.6f}' for k,v in row['changed_breakdown'].items())


def run(output):
    output.mkdir(parents=True, exist_ok=True)
    source = Path(variant.base.__file__)
    before_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    results = {name: [] for name in MODELS}
    for suite, scenario, before, actor, conversions in invariants():
        operations = [(f'add:{resource}', None) for resource in variant.base.PRICES]
        operations += [(kind, {'type':'FreeAction', 'kind':kind, 'count':1}) for kind in conversions]
        for conserve in (True, False):
            for label, action in operations:
                if action is None:
                    after = copy.deepcopy(before)
                    after['players'][actor]['resources'][label[4:]] += 1
                else:
                    after = successor(before, actor, action)
                for name, model in MODELS.items():
                    row = compare(before, after, actor, label, scenario, conserve, model=model)
                    row['suite'] = suite
                    results[name].append(row)
    for token in token_rows():
        before, after = token['before_state'], token['after_state']
        actor = next(p['player_id'] for p in before['players'] if p['faction'] == 'Xenos')
        for name, row in pair(before, after, actor, 'OreToPower', token['conservation']).items():
            row['suite'] = 'token-shortfall'
            results[name].append(row)
    actions = []
    for kind, diagnostic in [('research', row) for row in research_rows()] + [('tech', row) for row in tech_rows()]:
        before, after = diagnostic['before_state'], diagnostic['after_state']
        actor = next(p['player_id'] for p in before['players'] if p['faction'] == 'Xenos')
        label = diagnostic['track'] if kind == 'research' else f'std-{diagnostic["tile"]:02d}+{diagnostic["advance"][0]}'
        values = pair(before, after, actor, label)
        actions.append({'kind': kind, 'label': label, 'round': before['round'],
                        'main_case': diagnostic.get('main_case', True),
                        'before_state': before, 'after_state': after, 'values': values})
    steps, concentration = step_rows(), concentration_rows()
    breadth = []
    for r in (1,3):
        for name in MODELS:
            same_round = [row for row in concentration if row['round'] == r]
            def track_delta(row):
                changes = row['values'][name]['changed_breakdown']
                return sum(changes.get(key, {}).get('delta', 0.0)
                           for key in ('research_final_vp', 'research_progress'))
            existing_min = min(track_delta(row) for row in same_round if row['existing'])
            for row in same_round:
                if not row['existing']:
                    breadth.append({'round': r, 'model': name, 'track': row['track'],
                                    'fourth_delta': track_delta(row),
                                    'comparison_basis': 'research_final_vp + research_progress only',
                                    'existing_min_delta': existing_min,
                                    'passed': track_delta(row) < existing_min-1e-9})
    counts = {name: dict(Counter(row['status'] for row in values)) for name, values in results.items()}
    assert before_hash == hashlib.sha256(source.read_bytes()).hexdigest()
    record = {'counts': counts, 'invariants': results, 'actions': actions, 'steps': steps,
              'concentration': concentration, 'breadth_checks': breadth, 'games_run': 0,
              'source_unchanged_sha256': before_hash, 'a_enabled': False,
              'flags': {'b': True, 'c': True, 'd': [False, True]},
              'notes': ['All transitions native-paid except isolated step_rows: only research level changes.',
                        'At ties retain native track order; select by level, never by residual value.',
                        'Resource rewards excluded from threshold value; direct VP reward retained per requested formula.',
                        'Reached thresholds contribute only banked track points, never retained instant-reward shares.',
                        'Track slope excludes immediate VP; breadth compares banked plus fractional research only.']}
    write_json(output/'comparison.json', record)
    lines = ['| 불변식 통과/승인예외/실패 | R | B″+b+c | B⁗ |', '|---|---:|---:|---:|']
    for suite in ('existing','cap-boundary','token-shortfall'):
        for r in (1,3,6):
            cells=[]
            for name, values in results.items():
                c=Counter(row['status'] for row in values if row['suite']==suite and row['round']==r)
                cells.append(f'{c["pass"]}/{c["exception"]}/{c["fail"]}')
            lines.append(f'| {suite} | {r} | '+' | '.join(cells)+' |')
    lines += ['', '| 행동 ΔVP | R | B″+b+c | B⁗ | B⁗ 변화 breakdown |', '|---|---:|---:|---:|---|']
    for row in actions:
        left,right=row['values'].values()
        lines.append(f'| {row["label"]} | {row["round"]} | {left["delta"]:+.6f} | {right["delta"]:+.6f} | {changed_text(right)} |')
    lines += ['', '| 집중/분산 ΔVP | R | B″+b+c | B⁗ | B⁗ 변화 breakdown |','|---|---:|---:|---:|---|']
    for row in concentration:
        left,right=row['values'].values()
        lines.append(f'| {row["track"]} {"2→3" if row["existing"] else "0→1"} | {row["round"]} | '
                     f'{left["delta"]:+.6f} | {right["delta"]:+.6f} | {changed_text(right)} |')
    lines += ['', '| 단계 단독 변경 | R | 단계 | B″+b+c 트랙 Δ | B⁗ 트랙 Δ | 기대 | 판정 | B⁗ 확정/진행 전→후 |',
              '|---|---:|---|---:|---:|---:|---|---|']
    for row in steps:
        old,new=row['before'],row['after']
        prev=old['values']['B⁗'];cur=new['values']['B⁗']
        delta=new['values']['B″+b+c']['track_value']-old['values']['B″+b+c']['track_value']
        lines.append(f'| {row["track"]} | {row["round"]} | {old["level"]}→{new["level"]} | {delta:+.6f} | '
                     f'{row["actual"]:+.6f} | {row["expected"]:+.6f} | {"통과" if row["passed"] else "실패"} | '
                     f'{prev["final"]:.6f}/{prev["progress"]:.6f}→{cur["final"]:.6f}/{cur["progress"]:.6f} |')
    (output/'comparison.md').write_text('\n'.join(lines)+'\n')
    summary = {'counts':counts,'step_failures':sum(not row['passed'] for row in steps),
               'breadth_failures':sum(not row['passed'] for row in breadth),
               'tech_sign_failures':{name:sum(row['values'][name]['delta']<=0 for row in actions
                    if row['kind']=='tech' and row['main_case']) for name in MODELS},'games_run':0}
    write_json(output/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False))
    return any(c.get('fail',0) for c in counts.values()) or summary['step_failures']>0 or any(summary['tech_sign_failures'].values())


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    raise SystemExit(int(run(parser.parse_args().output)))
