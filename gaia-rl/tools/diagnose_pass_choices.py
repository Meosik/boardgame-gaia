"""Replay pass decisions and separate quick-fallback coverage from (k) valuation."""
import argparse
from collections import Counter, defaultdict
import copy
import gzip
import json
import os
from pathlib import Path
import statistics
import time

from gaia_rl import Environment
from gaia_rl._native import evaluation_pass_next_round_json, evaluation_successor_json
from four_factions.quick import fallback
import state_evaluation_bef as evaluator


OPTIONS = dict(token_shortfall=True, remaining_income=True, distributed_research=True,
               round_resource_prices=True, booster_one_income=True, gaia_token_return=True,
               fixed_income_and_planets=True, direct_stock_prices=True,
               federation_satellite_tokens=True, density_bonus=False,
               token_ore_price=True, reachable_planets=False)
RESOURCE_KEYS = ('ore', 'credits', 'knowledge', 'qic')
ALTERNATIVE_GROUPS = ('Build', 'Upgrade', 'ResearchAdvance', 'PowerAction',
                      'GaiaFormation', 'FormFederation', 'FreeAction')


def _player(state: dict, actor: int) -> dict:
    return next(player for player in state['players'] if player['player_id'] == actor)


def _evaluation(state: dict, actor: int):
    return evaluator.evaluate_state(state, actor, **OPTIONS)


def _successor(state: dict, actor: int, action: dict) -> dict:
    return json.loads(evaluation_successor_json(json.dumps(state), actor, json.dumps(action)))


def _project_pass(state: dict, actor: int) -> dict:
    return json.loads(evaluation_pass_next_round_json(json.dumps(state), actor))


def _action_delta(state: dict, actor: int, action: dict, baseline: float) -> float:
    after = _successor(state, actor, action)
    if action['type'] == 'Pass':
        after = _project_pass(after, actor)
    return _evaluation(after, actor).total_vp - baseline


def _power_stock(resources: dict, round_number: int) -> float:
    prices = evaluator.bowl_prices(round_number)
    power = resources['power']
    result = sum(power[key] * price for key, price in prices.items())
    if power.get('brainstone') in evaluator.STONE_BOWLS:
        result += 3 * prices[evaluator.STONE_BOWLS[power['brainstone']]]
    return result


def _stock_projection(raw: dict, projected: dict, actor: int) -> dict:
    before = _player(raw, actor)['resources']
    after = _player(projected, actor)['resources']
    old_round, new_round = raw['round'], projected['round']
    old_prices = evaluator.stock_prices(old_round, direct_stock_prices=True)
    new_prices = evaluator.stock_prices(new_round, direct_stock_prices=True)
    income_at_old_prices = sum(
        (after[key] - before[key]) * old_prices[key] for key in RESOURCE_KEYS)
    round_repricing = sum(
        after[key] * (new_prices[key] - old_prices[key]) for key in RESOURCE_KEYS)
    power_income = (_power_stock(after, old_round) - _power_stock(before, old_round))
    power_repricing = (_power_stock(after, new_round) - _power_stock(after, old_round))
    return {
        'resource_quantity_at_old_prices': income_at_old_prices,
        'resource_round_repricing': round_repricing,
        'power_quantity_at_old_prices': power_income,
        'power_round_repricing': power_repricing,
        'total_quantity_at_old_prices': income_at_old_prices + power_income,
        'total_round_repricing': round_repricing + power_repricing,
    }


def _pass_projection(state: dict, actor: int, action: dict) -> dict:
    before = _evaluation(state, actor)
    raw = _successor(state, actor, action)
    raw_value = _evaluation(raw, actor)
    projected = _project_pass(raw, actor)
    projected_value = _evaluation(projected, actor)
    old_booster = _player(state, actor)['booster']
    old_booster_raw = copy.deepcopy(raw)
    _player(old_booster_raw, actor)['booster'] = old_booster
    old_booster_projected = _project_pass(old_booster_raw, actor)
    old_booster_raw_value = _evaluation(old_booster_raw, actor)
    old_booster_projected_value = _evaluation(old_booster_projected, actor)
    projection_changes = {
        key: projected_value.breakdown.get(key, 0.0) - raw_value.breakdown.get(key, 0.0)
        for key in set(raw_value.breakdown) | set(projected_value.breakdown)
        if abs(projected_value.breakdown.get(key, 0.0)
               - raw_value.breakdown.get(key, 0.0)) > 1e-9
    }
    stock = _stock_projection(raw, projected, actor)
    projection_delta = projected_value.total_vp - raw_value.total_vp
    return {
        'total_delta_vp': projected_value.total_vp - before.total_vp,
        'immediate_pass_delta_vp': raw_value.total_vp - before.total_vp,
        'k_projection_delta_vp': projection_delta,
        'selected_booster': _player(raw, actor)['booster'],
        'old_booster': old_booster,
        'booster_immediate_delta_vp': raw_value.total_vp - old_booster_raw_value.total_vp,
        'booster_projected_delta_vp': (
            projected_value.total_vp - old_booster_projected_value.total_vp),
        'stock_projection': stock,
        'projection_residual_vp': (projection_delta
                                   - stock['total_quantity_at_old_prices']
                                   - stock['total_round_repricing']),
        'projection_breakdown_changes': dict(sorted(projection_changes.items())),
    }


def _remaining_resources(snapshot: dict) -> dict:
    player = _player(snapshot['state'], snapshot['player'])
    resources = player['resources']
    return {
        'ore': resources['ore'], 'credits': resources['credits'],
        'knowledge': resources['knowledge'], 'qic': resources['qic'],
        'bowl1': resources['power']['bowl1'],
        'bowl2': resources['power']['bowl2'],
        'bowl3': resources['power']['bowl3'],
    }


def _normal_pass(snapshot: dict, action: dict) -> dict:
    state, actor = snapshot['state'], snapshot['player']
    baseline = _evaluation(state, actor).total_vp
    rows = []
    for index, candidate in enumerate(snapshot['candidates']):
        candidate_action = candidate['action']
        rows.append({
            'index': index,
            'action': candidate_action,
            'delta_vp': _action_delta(state, actor, candidate_action, baseline),
        })
    selected = next(row for row in rows if row['action'] == action)
    alternatives = [row for row in rows if row['action']['type'] != 'Pass']
    best = max(alternatives, key=lambda row: row['delta_vp']) if alternatives else None
    by_group = {}
    for group in ALTERNATIVE_GROUPS:
        members = [row for row in alternatives if row['action']['type'] == group]
        if members:
            by_group[group] = max(members, key=lambda row: row['delta_vp'])
    return {
        'pass_delta_vp': selected['delta_vp'],
        'best_alternative': best,
        'best_by_group': by_group,
        'pass_beats_best_alternative': (best is None
                                        or selected['delta_vp'] >= best['delta_vp']),
        'pass_beats_best_build': ('Build' not in by_group
                                  or selected['delta_vp'] >= by_group['Build']['delta_vp']),
        'projection': _pass_projection(state, actor, action),
    }


def replay(trace: Path, seed: str, reserve_seconds: float) -> list[dict]:
    rows = [json.loads(line) for line in gzip.open(trace, 'rt')]
    env = Environment(seed, 2000)
    passes = []
    for recorded in rows:
        snapshot = json.loads(env.snapshot_json())
        action = recorded['action']
        matches = [index for index, candidate in enumerate(snapshot['candidates'])
                   if candidate['action'] == action]
        if len(matches) != 1:
            raise RuntimeError(f'expected one replay match at step {snapshot["steps"]}')
        started = time.monotonic()
        quick = fallback(env, snapshot, {}, deadline=started + reserve_seconds,
                         fixed_openings=False)
        if action['type'] == 'Pass':
            pass_index = matches[0]
            evaluated = quick['quick_evaluated_indices']
            unevaluated = quick['quick_unevaluated_indices']
            pass_score = quick['scores'][pass_index][0] if pass_index in evaluated else None
            higher = ([] if pass_score is None else [
                index for index in evaluated
                if quick['scores'][index][0] > pass_score + 1e-9
            ])
            row = {
                'seed': seed, 'step': snapshot['steps'],
                'round': snapshot['state']['round'],
                'faction': _player(snapshot['state'], snapshot['player'])['faction'],
                'path': recorded['path'], 'action': action,
                'remaining_resources': _remaining_resources(snapshot),
                'legal_build_candidates': sum(
                    candidate['action']['type'] == 'Build'
                    for candidate in snapshot['candidates']),
                'legal_research_candidates': sum(
                    candidate['action']['type'] == 'ResearchAdvance'
                    for candidate in snapshot['candidates']),
                'quick_reconstruction': {
                    'evaluated_count': len(evaluated),
                    'excluded_count': len(quick['quick_excluded_indices']),
                    'unevaluated_count': len(unevaluated),
                    'pass_was_evaluated': pass_index in evaluated,
                    'evaluated_higher_than_pass': len(higher),
                    'unevaluated_build': sum(
                        snapshot['candidates'][index]['action']['type'] == 'Build'
                        for index in unevaluated),
                    'unevaluated_research': sum(
                        snapshot['candidates'][index]['action']['type'] == 'ResearchAdvance'
                        for index in unevaluated),
                    'selected_action': snapshot['candidates'][quick['index']]['action'],
                    'matches_recorded_pass': quick['index'] == pass_index,
                    'elapsed_seconds': time.monotonic() - started,
                },
            }
            if recorded['path'] == 'normal':
                row['normal_evaluation'] = _normal_pass(snapshot, action)
            passes.append(row)
        env.step(snapshot['decision_id'], matches[0])
    if not env.is_terminal():
        raise RuntimeError('trace did not reach a terminal state')
    return passes


def _distribution(values: list[int]) -> dict:
    counts = Counter(values)
    return {
        'min': min(values), 'median': statistics.median(values), 'max': max(values),
        'mean': statistics.mean(values),
        'counts': {str(key): value for key, value in sorted(counts.items())},
    }


def _mean(rows: list[dict], getter) -> float:
    return statistics.mean(getter(row) for row in rows) if rows else 0.0


def summarize(rows: list[dict]) -> dict:
    fallback_rows = [row for row in rows if row['path'] == 'fallback']
    normal_rows = [row for row in rows if row['path'] == 'normal']
    fallback_quick = [row['quick_reconstruction'] for row in fallback_rows]
    normal = [row['normal_evaluation'] for row in normal_rows]
    by_round = {}
    normal_by_round = {}
    for round_number in range(1, 7):
        selected = [row for row in rows if row['round'] == round_number]
        normal_selected = [row['normal_evaluation'] for row in selected
                           if row['path'] == 'normal']
        alternatives = [row['best_alternative']['delta_vp'] for row in normal_selected
                        if row['best_alternative'] is not None]
        builds = [row for row in normal_selected if 'Build' in row['best_by_group']]
        resources = {key: _mean(selected, lambda row, key=key:
                     row['remaining_resources'][key]) for key in
                     ('ore', 'credits', 'knowledge', 'qic', 'bowl1', 'bowl2', 'bowl3')}
        by_round[str(round_number)] = {
            'passes': len(selected),
            'normal': sum(row['path'] == 'normal' for row in selected),
            'fallback': sum(row['path'] == 'fallback' for row in selected),
            'remaining_resources_mean': resources,
            'legal_build_candidates_mean': _mean(
                selected, lambda row: row['legal_build_candidates']),
            'legal_build_candidates_total': sum(
                row['legal_build_candidates'] for row in selected),
        }
        normal_by_round[str(round_number)] = {
            'passes': len(normal_selected),
            'pass_delta_vp_mean': _mean(
                normal_selected, lambda row: row['pass_delta_vp']),
            'best_alternative_available': len(alternatives),
            'best_alternative_delta_vp_mean': (statistics.mean(alternatives)
                                               if alternatives else None),
            'pass_beats_best_alternative': sum(
                row['pass_beats_best_alternative'] for row in normal_selected),
            'build_available': len(builds),
            'pass_beats_best_build': sum(
                row['pass_beats_best_build'] for row in builds),
            'best_build_delta_vp_mean': (_mean(
                builds, lambda row: row['best_by_group']['Build']['delta_vp'])
                if builds else None),
            'immediate_pass_delta_vp_mean': _mean(
                normal_selected,
                lambda row: row['projection']['immediate_pass_delta_vp']),
            'k_projection_delta_vp_mean': _mean(
                normal_selected,
                lambda row: row['projection']['k_projection_delta_vp']),
            'stock_quantity_at_old_prices_mean': _mean(
                normal_selected, lambda row: row['projection']['stock_projection'][
                    'total_quantity_at_old_prices']),
            'stock_round_repricing_mean': _mean(
                normal_selected, lambda row: row['projection']['stock_projection'][
                    'total_round_repricing']),
            'future_income_breakdown_change_mean': _mean(
                normal_selected, lambda row: row['projection'][
                    'projection_breakdown_changes'].get('future_income', 0.0)),
        }
    projection_keys = ('total_delta_vp', 'immediate_pass_delta_vp',
                       'k_projection_delta_vp', 'booster_immediate_delta_vp',
                       'booster_projected_delta_vp', 'projection_residual_vp')
    projection = {
        key: _mean(normal, lambda row, key=key: row['projection'][key])
        for key in projection_keys
    }
    projection['stock_quantity_at_old_prices_mean'] = _mean(
        normal, lambda row: row['projection']['stock_projection'][
            'total_quantity_at_old_prices'])
    projection['stock_round_repricing_mean'] = _mean(
        normal, lambda row: row['projection']['stock_projection'][
            'total_round_repricing'])
    return {
        'passes': len(rows),
        'by_path': {'normal': len(normal_rows), 'fallback': len(fallback_rows)},
        'fallback': {
            'evaluated_count_distribution': _distribution(
                [row['evaluated_count'] for row in fallback_quick]),
            'reconstruction_matches_recorded': sum(
                row['matches_recorded_pass'] for row in fallback_quick),
            'pass_was_evaluated': sum(row['pass_was_evaluated'] for row in fallback_quick),
            'had_evaluated_candidate_higher_than_pass': sum(
                row['evaluated_higher_than_pass'] > 0 for row in fallback_quick),
            'had_unevaluated_build': sum(row['unevaluated_build'] > 0
                                         for row in fallback_quick),
            'had_unevaluated_research': sum(row['unevaluated_research'] > 0
                                            for row in fallback_quick),
            'unevaluated_build_total': sum(row['unevaluated_build']
                                           for row in fallback_quick),
            'unevaluated_research_total': sum(row['unevaluated_research']
                                              for row in fallback_quick),
        },
        'normal': {
            'pass_beats_best_alternative': sum(
                row['pass_beats_best_alternative'] for row in normal),
            'pass_beats_best_build_when_available': sum(
                row['pass_beats_best_build'] for row in normal
                if 'Build' in row['best_by_group']),
            'build_available': sum('Build' in row['best_by_group'] for row in normal),
            'pass_delta_vp_mean': _mean(normal, lambda row: row['pass_delta_vp']),
            'best_alternative_delta_vp_mean': _mean(
                normal, lambda row: row['best_alternative']['delta_vp']
                if row['best_alternative'] is not None else row['pass_delta_vp']),
            'projection_mean': projection,
            'by_round': normal_by_round,
        },
        'by_round': by_round,
    }


def _configure_environment() -> None:
    os.environ.update(
        GAIA_FEDERATION_TOP_FIVE='1', GAIA_FEDERATION_FALLBACK_STABLE='1',
        GAIA_EXPANSION_MODE='lite', GAIA_PASS_TIMING='1',
        GAIA_FIXED_INCOME_PLANETS='1', GAIA_DIRECT_STOCK_PRICES='1',
        GAIA_FEDERATION_VALUE='1', GAIA_DENSITY_BONUS='0',
        GAIA_TOKEN_ORE_PRICE='1', GAIA_REACHABLE_PLANETS='0',
        GAIA_STATE_EVALUATION='1', GAIA_CONSERVATION_OFF='0')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace', type=Path, action='append', required=True)
    parser.add_argument('--seed', action='append', required=True)
    parser.add_argument('--reserve-seconds', type=float, default=0.5)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if len(args.trace) != len(args.seed):
        parser.error('--trace and --seed counts must match')
    _configure_environment()
    all_rows = []
    for trace, seed in zip(args.trace, args.seed):
        all_rows.extend(replay(trace, seed, args.reserve_seconds))
    result = {'summary': summarize(all_rows), 'passes': all_rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['summary']))
