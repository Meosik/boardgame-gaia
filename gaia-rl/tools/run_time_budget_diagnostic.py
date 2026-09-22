"""Run one time-budget diagnostic game with candidate-coverage telemetry."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
import os
from pathlib import Path
import time

from gaia_rl import Environment
from faction_teachers.clock import AdaptiveClock
from state_teacher import StateTeacher


def _fallback(audit: dict) -> bool:
    return bool(audit.get('timing', {}).get('quick_fallback_used', False)
                or audit.get('ranking_mode') == 'shared-quick-fallback')


def _candidate_metrics(snapshot: dict, audit: dict) -> dict[str, int]:
    mine_indices = {
        index for index, candidate in enumerate(snapshot['candidates'])
        if candidate['action']['type'] == 'Build'
    }
    fallback = _fallback(audit)
    if fallback:
        evaluated_indices = set(audit.get('quick_evaluated_indices', ()))
    else:
        # The normal path's initial policy ranking assigns every native legal
        # candidate a score before deeper route comparisons begin.
        evaluated_indices = set(range(len(snapshot['candidates'])))
    plans = audit.get('plans', ())
    compared_indices = {
        plan['first'] for plan in plans
        if isinstance(plan.get('first'), int)
    }
    return {
        'legal_candidates': len(snapshot['candidates']),
        'completed_comparisons': len(plans),
        'unique_compared_candidates': len(compared_indices),
        'legal_mine_candidates': len(mine_indices),
        'evaluated_mine_candidates': len(mine_indices & evaluated_indices),
    }


def _nested_counts(rows: list[dict], *, path_key: str) -> dict:
    counts = defaultdict(lambda: defaultdict(Counter))
    for row in rows:
        action = row['action']
        if action['type'] != 'FreeAction':
            continue
        path = path_key if isinstance(path_key, str) else path_key(row)
        counts[str(row['round'])][path][action['kind']] += action.get('count', 1)
    return {
        round_number: {
            path: dict(sorted(kinds.items()))
            for path, kinds in sorted(paths.items())
        }
        for round_number, paths in sorted(counts.items(), key=lambda item: int(item[0]))
    }


def run(output: Path, seed: str, target_seconds: float, maximum_seconds: float) -> dict:
    if os.environ.get('GAIA_DENSITY_BONUS') != '0':
        raise RuntimeError('This diagnostic requires GAIA_DENSITY_BONUS=0')
    token_ore_price = os.environ.get('GAIA_TOKEN_ORE_PRICE') == '1'
    reachable_planets = os.environ.get('GAIA_REACHABLE_PLANETS') == '1'
    federation_fallback_stable = os.environ.get('GAIA_FEDERATION_FALLBACK_STABLE') == '1'
    pass_realized_income = os.environ.get('GAIA_PASS_REALIZED_INCOME') == '1'
    output.mkdir(parents=True, exist_ok=False)
    env = Environment(seed, 2000)
    teacher = StateTeacher(
        seed,
        target_seconds=target_seconds,
        maximum_seconds=maximum_seconds,
        adaptive_clock=AdaptiveClock(
            target_seconds=target_seconds,
            long_seconds=maximum_seconds,
            uses=0,
        ),
    ).bind(env)
    conversions = Counter()
    rows = []
    started = time.monotonic()
    with gzip.open(output/'decisions.jsonl.gz', 'wt') as stream:
        while not env.is_terminal():
            snapshot = json.loads(env.snapshot_json())
            tick = time.monotonic()
            decision, index = teacher.choose(snapshot)
            elapsed = time.monotonic()-tick
            audit = teacher.last_audit
            action = snapshot['candidates'][index]['action']
            fallback = _fallback(audit)
            if action['type'] == 'FreeAction':
                conversions[action['kind']] += action.get('count', 1)
            faction = snapshot['state']['players'][snapshot['player']]['faction']
            row = {
                'step': snapshot['steps'],
                'round': snapshot['state']['round'],
                'seat': snapshot['player'],
                'faction': faction,
                'action': action,
                'seconds': round(elapsed, 4),
                'path': 'fallback' if fallback else 'normal',
                'candidate_metrics': _candidate_metrics(snapshot, audit),
            }
            stream.write(json.dumps(row)+'\n')
            stream.flush()
            rows.append(row)
            env.step(decision, index)
            after = json.loads(env.snapshot_json())
            teacher.observe(snapshot, index, after)
            if len(rows) % 10 == 0:
                print('step', len(rows), 'round', row['round'],
                      'elapsed', round(time.monotonic()-started, 1), flush=True)
            if len(rows) >= 2000:
                raise RuntimeError('decision cap reached')

    final_state = json.loads(env.snapshot_json())['state']
    scores = dict(env.final_scores())
    factions = {
        player['faction']: {
            'buildings': len(player['structures']),
            'federations': (len(player['federation_tokens'])
                            + len(player.get('gray_federation_tokens', []))),
            'score': scores[player['player_id']],
            'research_tracks': dict(player['research_tracks']),
        }
        for player in final_state['players']
    }
    metric_names = tuple(rows[0]['candidate_metrics'])
    candidate_means = {
        name: sum(row['candidate_metrics'][name] for row in rows)/len(rows)
        for name in metric_names
    }
    fallback_count = sum(row['path'] == 'fallback' for row in rows)
    result = {
        'seed': seed,
        'games': 1,
        'mode': ('B-lite+k+n+f-prime+g+h+o+p'
                 + ('+b-prime' if token_ore_price else '')
                 + ('+r' if reachable_planets else '')
                 + ('+p-fix' if federation_fallback_stable else '')
                 + ('+k-income' if pass_realized_income else '')),
        'density_bonus': False,
        'token_ore_price': token_ore_price,
        'reachable_planets': reachable_planets,
        'federation_fallback_stable': federation_fallback_stable,
        'pass_realized_income': pass_realized_income,
        'target_seconds': target_seconds,
        'maximum_seconds': maximum_seconds,
        'complete': env.is_terminal(),
        'decisions': len(rows),
        'elapsed_seconds': round(time.monotonic()-started, 2),
        'fallback_timeouts': fallback_count,
        'fallback_ratio': fallback_count/len(rows),
        'decision_seconds_mean': sum(row['seconds'] for row in rows)/len(rows),
        'decision_seconds_max': max(row['seconds'] for row in rows),
        'candidate_means_per_decision': candidate_means,
        'candidate_metric_definition': {
            'completed_comparisons': 'number of completed deep-search plan rows; fallback has zero',
            'evaluated_mine_candidates': ('native-legal Build candidates scored by the normal root '
                                          'ranking, or explicitly scored by the quick fallback'),
        },
        'free_action_conversions': dict(sorted(conversions.items())),
        'free_action_conversion_count': sum(conversions.values()),
        'free_action_by_round_path_type': _nested_counts(
            rows, path_key=lambda row: row['path']),
        'factions': factions,
    }
    (output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print('DONE', json.dumps(result, ensure_ascii=False), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', default='state-evaluation-ab-20260917-1580')
    parser.add_argument('--target-seconds', type=float, required=True)
    parser.add_argument('--maximum-seconds', type=float, required=True)
    args = parser.parse_args()
    run(args.output, args.seed, args.target_seconds, args.maximum_seconds)
