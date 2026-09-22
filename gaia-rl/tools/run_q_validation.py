"""Run one preregistered control or density game and record stop-gate metrics."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import time

from gaia_rl import Environment
from gaia_rl._native import evaluation_facts_json
from faction_teachers.clock import AdaptiveClock
from state_evaluation_btripleprime import _federation_components
from state_teacher import StateTeacher


def _fallback(audit: dict) -> bool:
    return bool(audit.get('timing', {}).get('quick_fallback_used', False)
                or audit.get('ranking_mode') == 'shared-quick-fallback')


def _round_power(state: dict) -> dict[str, int]:
    values = {}
    for player in state['players']:
        facts = json.loads(evaluation_facts_json(json.dumps(state), player['player_id']))
        components = _federation_components(facts['federation']['buildings'])
        values[player['faction']] = max((power for _, power in components), default=0)
    return values


def run(output: Path, seed: str, density: bool) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    env = Environment(seed, 2000)
    teacher = StateTeacher(
        seed,
        target_seconds=3,
        maximum_seconds=6,
        adaptive_clock=AdaptiveClock(target_seconds=3, long_seconds=6, uses=0),
    ).bind(env)
    conversions = Counter()
    round_power = defaultdict(lambda: defaultdict(int))
    federations = []
    rows = []
    started = time.monotonic()
    with gzip.open(output/'decisions.jsonl.gz', 'wt') as stream:
        while not env.is_terminal():
            snapshot = json.loads(env.snapshot_json())
            round_number = snapshot['state']['round']
            for faction, power in _round_power(snapshot['state']).items():
                round_power[round_number][faction] = max(round_power[round_number][faction], power)
            tick = time.monotonic()
            decision, index = teacher.choose(snapshot)
            elapsed = time.monotonic()-tick
            action = snapshot['candidates'][index]['action']
            audit = teacher.last_audit
            fallback = _fallback(audit)
            if action['type'] == 'FreeAction':
                conversions[action['kind']] += action.get('count', 1)
            faction = snapshot['state']['players'][snapshot['player']]['faction']
            if action['type'] == 'FormFederation':
                federations.append({
                    'step': snapshot['steps'],
                    'round': round_number,
                    'faction': faction,
                    'satellites': len(action['satellite_hexes']),
                    'token': action['token'],
                })
            row = {
                'step': snapshot['steps'],
                'round': round_number,
                'seat': snapshot['player'],
                'faction': faction,
                'action': action,
                'seconds': round(elapsed, 4),
                'fallback_timeout': fallback,
                'evaluation_arm': audit.get('evaluation_arm'),
            }
            stream.write(json.dumps(row)+'\n')
            stream.flush()
            rows.append(row)
            env.step(decision, index)
            after = json.loads(env.snapshot_json())
            teacher.observe(snapshot, index, after)
            if len(rows) % 10 == 0:
                print('step', len(rows), 'round', round_number,
                      'elapsed', round(time.monotonic()-started, 1), flush=True)
            if len(rows) >= 2000:
                raise RuntimeError('decision cap reached')

    final_state = json.loads(env.snapshot_json())['state']
    scores = dict(env.final_scores())
    factions = {}
    for player in final_state['players']:
        factions[player['faction']] = {
            'buildings': len(player['structures']),
            'federations': len(player['federation_tokens'])
                           + len(player.get('gray_federation_tokens', [])),
            'score': scores[player['player_id']],
        }
    result = {
        'seed': seed,
        'mode': 'B-lite+k+n+f-prime+g+h+o+p'+('+q' if density else ''),
        'complete': env.is_terminal(),
        'decisions': len(rows),
        'elapsed_seconds': round(time.monotonic()-started, 2),
        'fallback_timeouts': sum(row['fallback_timeout'] for row in rows),
        'fallback_ratio': sum(row['fallback_timeout'] for row in rows)/len(rows),
        'decision_seconds_mean': sum(row['seconds'] for row in rows)/len(rows),
        'decision_seconds_max': max(row['seconds'] for row in rows),
        'free_action_conversions': dict(conversions),
        'free_action_conversion_count': sum(conversions.values()),
        'round_max_adjacent_group_power': {
            str(round_number): dict(values)
            for round_number, values in sorted(round_power.items()) if round_number
        },
        'federation_declarations': federations,
        'factions': factions,
    }
    (output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print('DONE', json.dumps(result, ensure_ascii=False), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', default='state-evaluation-ab-20260917-1580')
    parser.add_argument('--density', action='store_true')
    args = parser.parse_args()
    run(args.output, args.seed, args.density)
