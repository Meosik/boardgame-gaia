"""Validate the opt-in 3.5-to-2.5 pass income-horizon correction."""
import argparse
from collections import defaultdict
import copy
import gzip
import json
from pathlib import Path
import statistics

from gaia_rl import Environment
from gaia_rl._native import evaluation_pass_next_round_json, evaluation_successor_json
from diagnose_pass_choices import _stock_projection
import state_evaluation_bef as evaluator


OPTIONS = dict(token_shortfall=True, remaining_income=True, distributed_research=True,
               round_resource_prices=True, booster_one_income=True, gaia_token_return=True,
               fixed_income_and_planets=True, direct_stock_prices=True,
               federation_satellite_tokens=True, density_bonus=False,
               token_ore_price=True, reachable_planets=False)


def _player(state: dict, actor: int) -> dict:
    return next(player for player in state['players'] if player['player_id'] == actor)


def _successor(state: dict, actor: int, action: dict) -> dict:
    return json.loads(evaluation_successor_json(json.dumps(state), actor, json.dumps(action)))


def _project(state: dict, actor: int) -> dict:
    return json.loads(evaluation_pass_next_round_json(json.dumps(state), actor))


def _evaluate(state: dict, actor: int, *, realized: bool = False):
    return evaluator.evaluate_state(
        state, actor, pass_realized_income=realized, **OPTIONS)


def validate(trace: Path, seed: str, prior: dict) -> list[dict]:
    env = Environment(seed, 2000)
    results = []
    for line in gzip.open(trace, 'rt'):
        recorded = json.loads(line)
        snapshot = json.loads(env.snapshot_json())
        action = recorded['action']
        matches = [index for index, candidate in enumerate(snapshot['candidates'])
                   if candidate['action'] == action]
        if len(matches) != 1:
            raise RuntimeError(f'expected one replay match at step {snapshot["steps"]}')
        if action['type'] == 'Pass' and recorded['path'] == 'normal':
            actor = snapshot['player']
            before = _evaluate(snapshot['state'], actor)
            raw = _successor(snapshot['state'], actor, action)
            projected = _project(raw, actor)
            control = _evaluate(projected, actor)
            enabled = _evaluate(
                projected, actor, realized=snapshot['state']['round'] < 6)

            old_booster_raw = copy.deepcopy(raw)
            _player(old_booster_raw, actor)['booster'] = _player(
                snapshot['state'], actor)['booster']
            old_booster_projected = _project(old_booster_raw, actor)
            old_booster_value = _evaluate(
                old_booster_projected, actor,
                realized=snapshot['state']['round'] < 6)

            no_booster = copy.deepcopy(projected)
            no_booster_player = _player(no_booster, actor)
            no_booster_player['booster'] = None
            facts = evaluator.base.base.engine_facts(no_booster, no_booster_player)
            projected_income_value = evaluator.base.base.income_vp(facts['income'])
            flag_adjustment = enabled.total_vp - control.total_vp
            income_residual = (projected_income_value + flag_adjustment
                               if snapshot['state']['round'] < 6 else 0.0)

            previous = prior[(seed, snapshot['steps'])]['normal_evaluation']
            build = previous['best_by_group'].get('Build')
            new_pass_delta = enabled.total_vp - before.total_vp
            results.append({
                'seed': seed, 'step': snapshot['steps'],
                'round': snapshot['state']['round'],
                'faction': _player(snapshot['state'], actor)['faction'],
                'old_pass_delta_vp': previous['pass_delta_vp'],
                'new_pass_delta_vp': new_pass_delta,
                'best_build_delta_vp': build['delta_vp'] if build is not None else None,
                'build_beats_new_pass': (build is not None
                    and build['delta_vp'] > new_pass_delta + 1e-9),
                'decomposition': {
                    'booster_replacement_delta_vp': (
                        enabled.total_vp - old_booster_value.total_vp),
                    'round_price_delta_vp': _stock_projection(
                        raw, projected, actor)['total_round_repricing'],
                    'projected_nonbooster_income_vp': projected_income_value,
                    'future_income_horizon_adjustment_vp': flag_adjustment,
                    'income_related_residual_vp': income_residual,
                },
                'r6_unchanged': (snapshot['state']['round'] != 6
                                 or abs(enabled.total_vp-control.total_vp) < 1e-9),
            })
        env.step(snapshot['decision_id'], matches[0])
    if not env.is_terminal():
        raise RuntimeError('trace did not reach a terminal state')
    return results


def _mean(rows: list[dict], getter) -> float:
    return statistics.mean(getter(row) for row in rows) if rows else 0.0


def summarize(rows: list[dict]) -> dict:
    builds = [row for row in rows if row['best_build_delta_vp'] is not None]
    rounds = defaultdict(list)
    for row in rows:
        rounds[row['round']].append(row)
    by_round = {}
    for round_number, selected in sorted(rounds.items()):
        decomposition = selected[0]['decomposition'].keys()
        by_round[str(round_number)] = {
            'normal_passes': len(selected),
            'old_pass_delta_vp_mean': _mean(
                selected, lambda row: row['old_pass_delta_vp']),
            'new_pass_delta_vp_mean': _mean(
                selected, lambda row: row['new_pass_delta_vp']),
            'build_available': sum(
                row['best_build_delta_vp'] is not None for row in selected),
            'build_beats_new_pass': sum(row['build_beats_new_pass'] for row in selected),
            'decomposition_mean': {key: _mean(
                selected, lambda row, key=key: row['decomposition'][key])
                for key in decomposition},
        }
    nonterminal = [row for row in rows if row['round'] < 6]
    residuals = [abs(row['decomposition']['income_related_residual_vp'])
                 for row in nonterminal]
    summary = {
        'normal_passes': len(rows),
        'build_recheck': {
            'cases': len(builds),
            'build_beats_pass': sum(row['build_beats_new_pass'] for row in builds),
            'ratio': (sum(row['build_beats_new_pass'] for row in builds) / len(builds)
                      if builds else 0.0),
        },
        'income_related_residual': {
            'mean_absolute_vp': statistics.mean(residuals),
            'max_absolute_vp': max(residuals),
        },
        'r6_unchanged': all(row['r6_unchanged'] for row in rows),
        'by_round': by_round,
    }
    summary['checks'] = {
        'income_related_mean_absolute_vp_at_most_0_25': (
            summary['income_related_residual']['mean_absolute_vp'] <= 0.25),
        'r6_unchanged': summary['r6_unchanged'],
        'build_recheck_complete': summary['build_recheck']['cases'] == 17,
    }
    summary['passed'] = all(summary['checks'].values())
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace', type=Path, action='append', required=True)
    parser.add_argument('--seed', action='append', required=True)
    parser.add_argument('--prior-diagnosis', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if len(args.trace) != len(args.seed):
        parser.error('--trace and --seed counts must match')
    prior_rows = json.loads(args.prior_diagnosis.read_text())['passes']
    prior = {(row['seed'], row['step']): row for row in prior_rows}
    all_rows = []
    for trace, seed in zip(args.trace, args.seed):
        all_rows.extend(validate(trace, seed, prior))
    result = {'summary': summarize(all_rows), 'passes': all_rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['summary']))
