"""Compare chosen free conversions with direct pass/build/research state deltas."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path

from gaia_rl import Environment
from gaia_rl._native import evaluation_pass_next_round_json, evaluation_successor_json
import state_evaluation_bef as evaluator


OPTIONS = dict(token_shortfall=True, remaining_income=True, distributed_research=True,
               round_resource_prices=True, booster_one_income=True, gaia_token_return=True,
               fixed_income_and_planets=True, direct_stock_prices=True,
               federation_satellite_tokens=True, density_bonus=False,
               token_ore_price=True, reachable_planets=False)
GROUPS = {'Pass': 'pass', 'Build': 'build', 'ResearchAdvance': 'research'}


def _value(state: dict, actor: int) -> float:
    return evaluator.evaluate_state(state, actor, **OPTIONS).total_vp


def _delta(state: dict, actor: int, action: dict, baseline: float) -> float:
    after = json.loads(evaluation_successor_json(json.dumps(state), actor, json.dumps(action)))
    candidate_state = after
    if action['type'] == 'Pass':
        player = next(p for p in after['players'] if p['player_id'] == actor)
        if player['passed']:
            candidate_state = json.loads(evaluation_pass_next_round_json(
                json.dumps(after), actor))
    return _value(candidate_state, actor)-baseline


def diagnose(trace: Path, seed: str) -> list[dict]:
    rows = [json.loads(line) for line in gzip.open(trace, 'rt')]
    env = Environment(seed, 2000)
    choices = []
    for recorded in rows:
        snapshot = json.loads(env.snapshot_json())
        state, actor = snapshot['state'], snapshot['player']
        action = recorded['action']
        matches = [index for index, candidate in enumerate(snapshot['candidates'])
                   if candidate['action'] == action]
        if len(matches) != 1:
            raise RuntimeError(f'expected one replay match at step {snapshot["steps"]}')
        if action['type'] == 'FreeAction':
            baseline = _value(state, actor)
            selected_delta = _delta(state, actor, action, baseline)
            alternatives = defaultdict(list)
            for candidate in snapshot['candidates']:
                other = candidate['action']
                group = GROUPS.get(other['type'])
                if group is None:
                    continue
                alternatives[group].append({
                    'action': other,
                    'delta_vp': _delta(state, actor, other, baseline),
                })
            best = {group: max(values, key=lambda row: row['delta_vp'])
                    for group, values in alternatives.items()}
            best_nonfree = max(best.values(), key=lambda row: row['delta_vp']) if best else None
            choices.append({
                'seed': seed, 'step': snapshot['steps'], 'round': state['round'],
                'faction': state['players'][actor]['faction'],
                'path': recorded['path'], 'action': action,
                'selected_delta_vp': selected_delta,
                'best_by_group': best,
                'best_nonfree_delta_vp': (best_nonfree['delta_vp']
                                          if best_nonfree is not None else None),
                'all_nonfree_worse_or_equal': (best_nonfree is None
                    or best_nonfree['delta_vp'] <= selected_delta+1e-9),
            })
        env.step(snapshot['decision_id'], matches[0])
    if not env.is_terminal():
        raise RuntimeError('trace did not reach a terminal state')
    return choices


def summarize(rows: list[dict]) -> dict:
    kinds = defaultdict(list)
    for row in rows:
        kinds[row['action']['kind']].append(row)
    by_kind = {}
    for kind, values in sorted(kinds.items()):
        by_kind[kind] = {
            'decisions': len(values),
            'units': sum(row['action'].get('count', 1) for row in values),
            'fallback_decisions': sum(row['path'] == 'fallback' for row in values),
            'all_nonfree_worse_or_equal': sum(row['all_nonfree_worse_or_equal'] for row in values),
            'pass_available': sum('pass' in row['best_by_group'] for row in values),
            'pass_better': sum('pass' in row['best_by_group'] and
                row['best_by_group']['pass']['delta_vp'] > row['selected_delta_vp']+1e-9
                for row in values),
            'build_better': sum('build' in row['best_by_group'] and
                row['best_by_group']['build']['delta_vp'] > row['selected_delta_vp']+1e-9
                for row in values),
            'research_better': sum('research' in row['best_by_group'] and
                row['best_by_group']['research']['delta_vp'] > row['selected_delta_vp']+1e-9
                for row in values),
            'selected_delta_mean': sum(row['selected_delta_vp'] for row in values)/len(values),
        }
    available = Counter()
    better = Counter()
    for row in rows:
        for group in ('pass', 'build', 'research'):
            if group in row['best_by_group']:
                available[group] += 1
                if row['best_by_group'][group]['delta_vp'] > row['selected_delta_vp']+1e-9:
                    better[group] += 1
    return {
        'conversion_decisions': len(rows),
        'conversion_units': sum(row['action'].get('count', 1) for row in rows),
        'fallback_decisions': sum(row['path'] == 'fallback' for row in rows),
        'all_nonfree_worse_or_equal': sum(row['all_nonfree_worse_or_equal'] for row in rows),
        'alternative_available': dict(available),
        'alternative_better': dict(better),
        'by_kind': by_kind,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace', type=Path, action='append', required=True)
    parser.add_argument('--seed', action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if len(args.trace) != len(args.seed):
        parser.error('--trace and --seed counts must match')
    all_rows = []
    for trace, seed in zip(args.trace, args.seed):
        all_rows.extend(diagnose(trace, seed))
    result = {'summary': summarize(all_rows), 'choices': all_rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result['summary'], ensure_ascii=False))
