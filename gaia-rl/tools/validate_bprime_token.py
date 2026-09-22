"""Validate b-prime token pricing and the ore/token/burn/credit cycle."""
import argparse
from collections import Counter
import copy
from dataclasses import dataclass
import json
from pathlib import Path

from diagnose_research_bc import token_rows
from validate_bc import cap_state, compare, invariants
from validate_bdoubleprime import representative, successor, write_json
from validate_bprime import CONVERSIONS, EPSILON, fixtures
import state_evaluation_bef as variant


FACTIONS = ('Terrans', 'HadschHallas', 'Taklons', 'Xenos')
OPTIONS = dict(token_shortfall=True, remaining_income=True, distributed_research=True,
               round_resource_prices=True, booster_one_income=True, gaia_token_return=True,
               fixed_income_and_planets=True, direct_stock_prices=True,
               federation_satellite_tokens=True, density_bonus=False)


@dataclass(frozen=True)
class Configured:
    def evaluate_state(self, state: dict, actor: int, **kwargs):
        return variant.evaluate_state(
            state, actor, token_ore_price=True, **OPTIONS, **kwargs)


MODEL = Configured()


def _delta(before: dict, after: dict, actor: int) -> tuple[float, dict]:
    left = MODEL.evaluate_state(before, actor)
    right = MODEL.evaluate_state(after, actor)
    changes = {
        key: right.breakdown[key]-left.breakdown[key]
        for key in left.breakdown
        if abs(right.breakdown[key]-left.breakdown[key]) > EPSILON
    }
    return right.total_vp-left.total_vp, changes


def _state(round_number: int, faction: str, *, bowl1: int, bowl2: int = 0) -> tuple[dict, int]:
    state, actor = representative(round_number)
    player = state['players'][actor]
    player['faction'] = faction
    player['resources'].update(ore=6, credits=6, knowledge=3, qic=2)
    player['resources']['power'].update(
        bowl1=bowl1, bowl2=bowl2, bowl3=0, gaia_forming=0, gaia_bowl=0,
        brainstone=None,
    )
    return state, actor


def validate(output: Path) -> bool:
    output.mkdir(parents=True, exist_ok=True)
    full_invariants = []
    cases = list(invariants())
    for scenario, state, actor in fixtures():
        if state['round'] == 3:
            late = copy.deepcopy(state)
            late['round'] = 5
            cases.append(('existing', scenario, late, actor, CONVERSIONS))
    state, actor = cap_state(5, 4, stress=True)
    cases.append(('cap-boundary', 'cap-boundary', state, actor, CONVERSIONS[:-1]))
    for suite, scenario, before, actor, conversions in cases:
        operations = [(f'add:{key}', None) for key in variant.base.base.PRICES]
        operations.extend((kind, {'type': 'FreeAction', 'kind': kind, 'count': 1})
                          for kind in conversions)
        for conserve in (True, False):
            for label, action in operations:
                if action is None:
                    after = copy.deepcopy(before)
                    after['players'][actor]['resources'][label[4:]] += 1
                else:
                    after = successor(before, actor, action)
                row = compare(before, after, actor, label, scenario,
                              conserve, model=MODEL)
                row['suite'] = suite
                full_invariants.append(row)
    for token in token_rows():
        before, after = token['before_state'], token['after_state']
        actor = next(p['player_id'] for p in before['players'] if p['faction'] == 'Xenos')
        row = compare(before, after, actor, 'OreToPower',
                      f'tokens:{token["active_tokens"]}', token['conservation'], model=MODEL)
        row['suite'] = 'token-shortfall'
        full_invariants.append(row)
    for count in (3, 7):
        before, actor = cap_state(5, count, stress=True)
        after = successor(before, actor, {
            'type': 'FreeAction', 'kind': 'OreToPower', 'count': 1})
        for conserve in (True, False):
            row = compare(before, after, actor, 'OreToPower', f'tokens:{count}',
                          conserve, model=MODEL)
            row['suite'] = 'token-shortfall'
            full_invariants.append(row)
    ore_to_token = []
    cycles = []
    for faction in FACTIONS:
        for round_number in range(1, 7):
            for tokens in range(0, 11):
                before, actor = _state(round_number, faction, bowl1=tokens)
                after = successor(before, actor, {
                    'type': 'FreeAction', 'kind': 'OreToPower', 'count': 1})
                delta, changes = _delta(before, after, actor)
                ore_to_token.append({
                    'faction': faction, 'round': round_number,
                    'active_tokens': tokens, 'delta_vp': delta,
                    'passed': delta < -EPSILON, 'changed_breakdown': changes,
                })
            for tokens in range(2, 11):
                before, actor = _state(round_number, faction,
                                       bowl1=tokens-2, bowl2=2)
                token = successor(before, actor, {
                    'type': 'FreeAction', 'kind': 'OreToPower', 'count': 1})
                burned = successor(token, actor, {
                    'type': 'FreeAction', 'kind': 'BurnPower', 'count': 1})
                credited = successor(burned, actor, {
                    'type': 'FreeAction', 'kind': 'PowerToCredit', 'count': 1})
                delta, changes = _delta(before, credited, actor)
                cycles.append({
                    'faction': faction, 'round': round_number,
                    'active_tokens': tokens, 'delta_vp': delta,
                    'passed': delta < -EPSILON, 'changed_breakdown': changes,
                })
    failures = [row for row in ore_to_token+cycles if not row['passed']]
    full_failures = [row for row in full_invariants if not row['passed']]
    full_counts = dict(Counter(row['status'] for row in full_invariants))
    exception_reasons = sorted({row['exception'] for row in full_invariants
                                if row['exception'] is not None})
    summary = {
        'flag': {'GAIA_TOKEN_ORE_PRICE': '1'},
        'formula': 'shortfall * (f-prime round ore price * 0.8)',
        'ore_to_token': {
            'cases': len(ore_to_token), 'failures': sum(not row['passed'] for row in ore_to_token),
            'delta_vp_min': min(row['delta_vp'] for row in ore_to_token),
            'delta_vp_max': max(row['delta_vp'] for row in ore_to_token),
        },
        'three_step_cycle': {
            'actions': ['OreToPower', 'BurnPower', 'PowerToCredit'],
            'cases': len(cycles), 'failures': sum(not row['passed'] for row in cycles),
            'delta_vp_min': min(row['delta_vp'] for row in cycles),
            'delta_vp_max': max(row['delta_vp'] for row in cycles),
        },
        'full_invariants': {
            'cases': len(full_invariants), 'counts': full_counts,
            'failures': len(full_failures),
        },
        'rounds': list(range(1, 7)),
        'active_token_states': list(range(0, 11)),
        'factions': list(FACTIONS),
        'approved_exceptions': exception_reasons,
        'r5_r6_ore_to_power_exceptions': 0,
    }
    write_json(output/'summary.json', summary)
    write_json(output/'cases.json', {
        'summary': summary, 'full_invariants': full_invariants,
        'ore_to_token': ore_to_token, 'three_step_cycle': cycles,
        'failures': full_failures+failures,
    })
    print(json.dumps(summary, ensure_ascii=False))
    return bool(full_failures or failures)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    raise SystemExit(int(validate(parser.parse_args().output)))
