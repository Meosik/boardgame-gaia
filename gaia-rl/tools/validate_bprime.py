"""Report price-only Bprime counterexamples; never tune weights or run matches."""
import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'gaia-rl/experiments'))
from gaia_rl._native import evaluation_successor_json
import state_evaluation_bprime as evaluator
from test_state_evaluation import opportunity_fixture

FACTIONS = ('Xenos', 'HadschHallas', 'Terrans', 'Taklons')
CONVERSIONS = ('PowerToQic', 'PowerToKnowledge', 'PowerToOre', 'PowerToCredit',
               'OreToCredit', 'KnowledgeToCredit', 'QicToOre', 'OreToPower', 'BurnPower')
EPSILON = 1e-9


def brainstone_burn_exception(before, after, actor, action):
    """Approved exception: discard one normal II token, move the stone II -> III.

    No other faction, burn outcome or simultaneous resource gain is exempt.
    """
    player = next(p for p in before['players'] if p['player_id'] == actor)
    power = player['resources']['power']
    if (action != 'BurnPower' or player['faction'] != 'Taklons'
            or power['brainstone'] != 'Area2' or power['bowl2'] < 1):
        return False
    expected = copy.deepcopy(before)
    expected_player = next(p for p in expected['players'] if p['player_id'] == actor)
    expected_power = expected_player['resources']['power']
    expected_power['bowl2'] -= 1
    expected_power['brainstone'] = 'Area3'
    return after == expected


def fixtures():
    for faction in FACTIONS:
        for round_number in (1, 3, 6):
            for scenario, count in (('isolated', 0), ('expansion-budget', 3)):
                state, actor = opportunity_fixture(target='Desert', distance=2, count=count)
                state['round'] = round_number
                state['board']['spaceship_tiles'] = {}
                p = state['players'][actor]
                p.update(faction=faction, booster=None)
                p['resources'].update(ore=1, credits=2, knowledge=3, qic=1)
                p['resources']['power'].update(bowl1=2, bowl2=4, bowl3=4,
                    brainstone='Area2' if faction == 'Taklons' else None, gaia_forming=0)
                yield scenario, state, actor


def compare(before, after, actor, action, scenario, conserve, *, model=evaluator):
    original = copy.deepcopy(before)
    left = model.evaluate_state(before, actor, conserve_resources=conserve)
    right = model.evaluate_state(after, actor, conserve_resources=conserve)
    assert before == original, 'Evaluator mutated input'
    for value in (left, right):
        assert abs(value.total_vp-sum(value.breakdown.values())) < EPSILON
    delta = right.total_vp-left.total_vp
    additions = action.startswith('add:')
    exception = brainstone_burn_exception(before, after, actor, action)
    passed = exception or (delta >= -EPSILON if additions else delta <= EPSILON)
    changes = {key: {'before': left.breakdown[key], 'after': right.breakdown[key],
                     'delta': right.breakdown[key]-left.breakdown[key]}
               for key in left.breakdown
               if abs(left.breakdown[key]-right.breakdown[key]) > EPSILON}
    return {'scenario': scenario, 'faction': before['players'][actor]['faction'],
            'round': before['round'], 'conservation': 'ON' if conserve else 'OFF',
            'action': action, 'before': left.total_vp, 'after': right.total_vp,
            'delta': delta, 'passed': passed,
            'status': 'exception' if exception else 'pass' if passed else 'fail',
            'exception': 'Taklons: one normal II token discarded, Brainstone II -> III' if exception else None,
            'changed_breakdown': changes, 'before_breakdown': left.breakdown,
            'after_breakdown': right.breakdown,
            'power_before': before['players'][actor]['resources']['power'],
            'power_after': after['players'][actor]['resources']['power']}


def validate(output):
    output.mkdir(parents=True, exist_ok=True)
    source = ROOT/'gaia-rl/experiments/state_evaluation.py'
    variant = ROOT/'gaia-rl/experiments/state_evaluation_bprime.py'
    expected = source.read_text().replace(
        "PRICES = {'ore': 1.0, 'credits': 0.5, 'knowledge': 2.0, 'qic': 1.0}",
        "PRICES = {'ore': 2.67, 'credits': 0.8, 'knowledge': 2.67, 'qic': 4.67}")
    assert variant.read_text() == expected, 'Bprime changed more than four prices'
    cases = []
    states = []
    for scenario, state, actor in fixtures():
        states.append({'scenario': scenario, 'actor': actor, 'state': state})
        for conserve in (True, False):
            for resource in evaluator.PRICES:
                after = copy.deepcopy(state)
                after['players'][actor]['resources'][resource] += 1
                cases.append(compare(state, after, actor, 'add:'+resource, scenario, conserve))
            for conversion in CONVERSIONS:
                action = {'type': 'FreeAction', 'kind': conversion, 'count': 1}
                after = json.loads(evaluation_successor_json(json.dumps(state), actor, json.dumps(action)))
                cases.append(compare(state, after, actor, conversion, scenario, conserve))
    counts = Counter(row['status'] for row in cases)
    record = {'prices': evaluator.PRICES, 'cases': cases, 'counts': counts,
              'games_run': 0, 'scope': 'Synthetic native-paid active states, four factions, rounds 1/3/6; not a universal proof',
              'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'variant_sha256': hashlib.sha256(variant.read_bytes()).hexdigest(),
              'power_unit_vp': {'bowl1': 1/9, 'bowl2': 2/9, 'bowl3': 1/3,
                  'brainstone_Area1': 1/3, 'brainstone_Area2': 2/3, 'brainstone_Area3': 1,
                  'brainstone_Gaia': '0.5 * native return bowl value before R6; 0 in R6'}}
    (output/'cases.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n')
    (output/'fixtures.json').write_text(json.dumps(states, ensure_ascii=False, indent=2)+'\n')
    lines = ['| 변환 | 라운드 | 종족·상태·보존 | 전후 평가값(VP) | 변화 breakdown(VP) |',
             '|---|---:|---|---|---|']
    # Identical ON/OFF results occupy one row; all counterexamples remain in cases.json.
    failures = [r for r in cases if not r['passed']]
    groups = {}
    for row in failures:
        key = tuple(row[k] for k in ('action', 'round', 'faction', 'scenario', 'before', 'after'))
        groups.setdefault(key, []).append(row)
    for rows in groups.values():
        r = rows[0]
        parts = '; '.join(f'{key} {v["before"]:.6f}→{v["after"]:.6f} ({v["delta"]:+.6f})'
                          for key, v in r['changed_breakdown'].items())
        modes = '/'.join(row['conservation'] for row in rows)
        lines.append(f'| {r["action"]} | {r["round"]} | {r["faction"]}·{r["scenario"]}·{modes} | '
                     f'{r["before"]:.6f}→{r["after"]:.6f} | {parts} |')
    (output/'failures.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'counts': counts, 'failure_table': str(output/'failures.md'), 'games_run': 0}))
    return bool(failures)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    raise SystemExit(int(validate(parser.parse_args().output)))
