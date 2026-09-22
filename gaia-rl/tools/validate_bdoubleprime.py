"""Paired state checks for Bprime/Bdoubleprime; no teachers, matches or tuning."""
import argparse
import ast
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path

from validate_bprime import (ROOT, EPSILON, CONVERSIONS, compare, fixtures,
                             evaluation_successor_json, opportunity_fixture)
import state_evaluation_bprime as bprime
import state_evaluation_bdoubleprime as bdoubleprime

MODELS = {'Bprime': bprime, 'Bdoubleprime': bdoubleprime}
FREE = {'PowerToQic': '4파워→QIC', 'PowerToKnowledge': '4파워→지식',
        'PowerToOre': '3파워→광석', 'PowerToCredit': '1파워→크레딧'}
PUBLIC = ((4, '7돈', None, 'positive'), (3, '2광석', None, 'positive'),
          (5, '2지식', None, 'positive'), (6, '1테라+광산', '1,0', 'positive'),
          (2, '2테라+광산', '0,1', None), (1, '3지식', None, None),
          (7, '2토큰', None, None))


def source_check():
    trees = []
    for model in MODELS.values():
        tree = ast.parse(Path(model.__file__).read_text())
        tree.body = [node for node in tree.body
                     if not isinstance(node, ast.FunctionDef) or node.name != 'power_value']
        trees.append(ast.dump(tree, include_attributes=False))
    assert trees[0] == trees[1], 'Changes outside power_value'
    assert bprime.PRICES == bdoubleprime.PRICES


def successor(state, actor, action):
    return json.loads(evaluation_successor_json(json.dumps(state), actor, json.dumps(action)))


def representative(round_number):
    state, actor = opportunity_fixture(target='Volcanic', distance=1, count=1)
    state['round'] = round_number
    state['board']['spaceship_tiles'] = {}
    state['board']['hexes']['0,1']['planet'] = {
        'planet_type': 'Oxide', 'owner': None, 'is_gaia_formed': False}
    state['used_power_actions'] = []
    p = state['players'][actor]
    p.update(booster=None, vp=20)
    p['resources'].update(ore=6, credits=10, knowledge=3, qic=1)
    p['resources']['power'].update(bowl1=4, bowl2=4, bowl3=8, brainstone=None, gaia_forming=0)
    return state, actor


def action_cases():
    for round_number in (1, 3, 6):
        state, actor = representative(round_number)
        for kind, label in FREE.items():
            yield '프리', label, 'negative', state, actor, {'type': 'FreeAction', 'kind': kind, 'count': 1}
        for slot, label, coord, expected in PUBLIC:
            yield '공용', label, expected, state, actor, {'type': 'PowerAction', 'id': slot, 'coord': coord}
        yield '소각', '일반 토큰 소각 1회', 'nonpositive', state, actor, {
            'type': 'FreeAction', 'kind': 'BurnPower', 'count': 1}
        for amount in (2, 3, 4):
            pending = copy.deepcopy(state)
            pending['phase'] = {'ChargePowerPending': {
                'queue': [{'player': actor, 'hex': '0,0', 'max_power': amount}],
                'resume_active_player': actor}}
            yield '리치', f'{amount}충전 수락', None, pending, actor, {'type': 'ChargePower', 'accept': True}


def expected_sign(delta, expected):
    if expected == 'negative':
        return delta < -EPSILON
    if expected == 'positive':
        return delta > EPSILON
    if expected == 'nonpositive':
        return delta <= EPSILON
    return None


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def validate(output):
    source_check()
    output.mkdir(parents=True, exist_ok=True)
    invariants = {name: [] for name in MODELS}
    for scenario, before, actor in fixtures():
        for conserve in (True, False):
            actions = [(f'add:{resource}', None) for resource in bprime.PRICES]
            actions += [(kind, {'type': 'FreeAction', 'kind': kind, 'count': 1}) for kind in CONVERSIONS]
            for name, action in actions:
                if action is None:
                    after = copy.deepcopy(before)
                    after['players'][actor]['resources'][name[4:]] += 1
                else:
                    after = successor(before, actor, action)
                for model_name, model in MODELS.items():
                    invariants[model_name].append(compare(before, after, actor, name, scenario, conserve, model=model))
    counts = {name: dict(Counter(r['status'] for r in rows)) for name, rows in invariants.items()}
    representatives = []
    for category, label, expected, before, actor, action in action_cases():
        after = successor(before, actor, action)
        values = {}
        for name, model in MODELS.items():
            row = compare(before, after, actor, action.get('kind', action['type']), 'representative', True, model=model)
            for key in ('passed', 'status', 'exception'):
                row.pop(key)  # Resource-gaining public actions use their own sign expectation.
            row['expected_sign'] = expected
            row['sign_ok'] = expected_sign(row['delta'], expected)
            values[name] = row
        representatives.append({'category': category, 'label': label, 'round': before['round'],
                                'action': action, 'before_state': before, 'after_state': after, 'values': values})
    write_json(output/'comparison.json', {'counts': counts, 'invariants': invariants,
        'representative_actions': representatives, 'games_run': 0,
        'power_prices': {'Bprime': {'normal': [1/9, 2/9, 1/3], 'brainstone': [1/3, 2/3, 1]},
                         'Bdoubleprime': {'normal': [0, .6, 1.2], 'brainstone': [0, 1.8, 3.6]}},
        'unchanged_token_values': {
            'independent_stock_term': 0,
            'normal_gaia_direct_stock': 0,
            'brainstone_gaia': '0.5 * Bprime return-bowl value in R1/R3; zero in R6',
            'income_per_new_token': 1/3,
            'income_discount': bprime.INCOME_DISCOUNT,
            'note': 'Token count still affects Gaia capacity and federation readiness, not a flat per-token stock price.'},
        'source_sha256': {name: hashlib.sha256(Path(model.__file__).read_bytes()).hexdigest()
                          for name, model in MODELS.items()},
        'scope': 'Same 624 synthetic-state invariants per variant, four factions, rounds 1/3/6, ON/OFF. '
                 'Representative actions use Xenos, same board/resources across rounds, conservation ON. '
                 'Terraform power actions include native paid mine construction. No universal proof.'})
    lines = ['| 불변식(각624건) | B′ | B″ |', '|---|---:|---:|']
    for key, label in (('pass', '통과'), ('exception', '승인된 타클론 예외'), ('fail', '실패')):
        lines.append(f'| {label} | {counts["Bprime"].get(key,0)} | {counts["Bdoubleprime"].get(key,0)} |')
    lines += ['', '| 행동 ΔVP (B′ / B″) | 1R | 3R | 6R |', '|---|---:|---:|---:|']
    for label in dict.fromkeys(r['label'] for r in representatives):
        cells = []
        for row in (r for r in representatives if r['label'] == label):
            cells.append(' / '.join(f'{v["delta"]:+.6f}' for v in row['values'].values()))
        lines.append(f'| {label} | {" | ".join(cells)} |')
    (output/'comparison.md').write_text('\n'.join(lines)+'\n')
    failure_lines = ['| 종류·변환 | 라운드 | 종족·상태·보존 | B′ 전→후 | B″ 전→후 | B″ 변화 breakdown |',
                     '|---|---:|---|---|---|---|']
    failing = []
    for a, b in zip(invariants['Bprime'], invariants['Bdoubleprime']):
        if not b['passed']:
            failing.append(('불변식 '+b['action'], a, b))
    for row in representatives:
        a, b = row['values'].values()
        if b['sign_ok'] is False:
            failing.append(('부호 '+row['label'], a, b))
    for label, a, b in failing:
        parts = '; '.join(f'{k} {v["delta"]:+.6f}' for k, v in b['changed_breakdown'].items())
        failure_lines.append(f'| {label} | {b["round"]} | {b["faction"]}·{b["scenario"]}·{b["conservation"]} | '
                             f'{a["before"]:.6f}→{a["after"]:.6f} | {b["before"]:.6f}→{b["after"]:.6f} | {parts} |')
    (output/'failures.md').write_text('\n'.join(failure_lines)+'\n')
    print('\n'.join(lines))
    print(json.dumps({'unexpected_cases_Bdoubleprime': len(failing), 'games_run': 0}))
    return bool(failing)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    raise SystemExit(int(validate(parser.parse_args().output)))
