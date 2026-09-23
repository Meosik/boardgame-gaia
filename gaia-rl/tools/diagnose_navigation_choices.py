"""Replay adopted traces and audit Navigation at actual research decisions."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path

from gaia_rl import Environment
from gaia_rl._native import evaluation_successor_json
import state_evaluation_bef as evaluator


OPTIONS = dict(
    token_shortfall=True,
    remaining_income=True,
    distributed_research=True,
    round_resource_prices=True,
    discounted_expansion=False,
    booster_one_income=True,
    gaia_token_return=True,
    fixed_income_and_planets=True,
    direct_stock_prices=True,
    federation_satellite_tokens=True,
    density_bonus=False,
    token_ore_price=True,
    reachable_planets=True,
)


def _value(state: dict, actor: int) -> float:
    return evaluator.evaluate_state(state, actor, **OPTIONS).total_vp


def _delta(state: dict, actor: int, action: dict, baseline: float) -> float:
    after = json.loads(evaluation_successor_json(json.dumps(state), actor, json.dumps(action)))
    return _value(after, actor) - baseline


def _research_scores(snapshot: dict) -> list[dict]:
    state, actor = snapshot['state'], snapshot['player']
    actions = [candidate['action'] for candidate in snapshot['candidates']
               if candidate['action']['type'] == 'ResearchAdvance']
    if not actions:
        return []
    baseline = _value(state, actor)
    rows = [{'track': action['track'], 'delta_vp': _delta(state, actor, action, baseline)}
            for action in actions]
    for row in rows:
        row['rank'] = 1 + sum(other['delta_vp'] > row['delta_vp'] + 1e-9 for other in rows)
    return sorted(rows, key=lambda row: (row['rank'], -row['delta_vp'], row['track']))


def diagnose(trace: Path, seed: str) -> dict:
    recorded_rows = [json.loads(line) for line in gzip.open(trace, 'rt')]
    env = Environment(seed, 2000)
    research_choices = []
    offered_states = []
    knowledge_spend = []
    for recorded in recorded_rows:
        snapshot = json.loads(env.snapshot_json())
        state, actor = snapshot['state'], snapshot['player']
        action = recorded['action']
        matches = [index for index, candidate in enumerate(snapshot['candidates'])
                   if candidate['action'] == action]
        if len(matches) != 1:
            raise RuntimeError(f'expected one replay match at step {snapshot["steps"]}')

        research = _research_scores(snapshot)
        legal_mines = sum(candidate['action']['type'] == 'Build'
                          for candidate in snapshot['candidates'])
        player = state['players'][actor]
        navigation = next((row for row in research if row['track'] == 'Navigation'), None)
        science = next((row for row in research if row['track'] == 'Science'), None)
        common = {
            'seed': seed,
            'step': snapshot['steps'],
            'round': state['round'],
            'seat': actor,
            'faction': player['faction'],
            'path': recorded['path'],
            'selected_action': action,
            'legal_mine_candidates': legal_mines,
            'navigation_level': player['research_tracks']['navigation'],
            'research_scores': research,
            'navigation_delta_vp': navigation['delta_vp'] if navigation else None,
            'navigation_rank': navigation['rank'] if navigation else None,
            'science_delta_vp': science['delta_vp'] if science else None,
            'direction_case': bool(legal_mines <= 1
                                   and player['research_tracks']['navigation'] < 2
                                   and navigation is not None and science is not None),
            'navigation_beats_science': (navigation['delta_vp'] > science['delta_vp'] + 1e-9
                                         if navigation is not None and science is not None else None),
        }
        if research:
            offered_states.append(common)
        if action['type'] == 'ResearchAdvance':
            research_choices.append({**common, 'selected_track': action['track']})

        knowledge_before = player['resources']['knowledge']
        env.step(snapshot['decision_id'], matches[0])
        after = json.loads(env.snapshot_json())['state']['players'][actor]['resources']['knowledge']
        spent = max(0, knowledge_before - after)
        if spent:
            knowledge_spend.append({
                'seed': seed,
                'step': snapshot['steps'],
                'round': state['round'],
                'faction': player['faction'],
                'action': action,
                'amount': spent,
                'research_action': action['type'] == 'ResearchAdvance',
            })
    if not env.is_terminal():
        raise RuntimeError('trace did not reach a terminal state')
    return {
        'seed': seed,
        'decisions': len(recorded_rows),
        'research_offered_states': offered_states,
        'research_choices': research_choices,
        'knowledge_spend': knowledge_spend,
    }


def _direction(rows: list[dict]) -> dict:
    cases = [row for row in rows if row['direction_case']]
    holds = sum(row['navigation_beats_science'] for row in cases)
    return {
        'eligible_cases': len(cases),
        'navigation_beats_science': holds,
        'fails': len(cases) - holds,
        'rate': holds / len(cases) if cases else None,
    }


def summarize(games: list[dict]) -> dict:
    decisions = sum(game['decisions'] for game in games)
    offered = [row for game in games for row in game['research_offered_states']]
    choices = [row for game in games for row in game['research_choices']]
    spending = [row for game in games for row in game['knowledge_spend']]
    navigation_ranks = Counter(str(row['navigation_rank']) if row['navigation_rank'] is not None
                               else 'unavailable' for row in choices)
    chosen_tracks = Counter(row['selected_track'] for row in choices)
    spend_by_action = defaultdict(lambda: {'events': 0, 'knowledge': 0})
    for row in spending:
        action = row['action']
        label = action['type']
        if action['type'] == 'ResearchAdvance':
            label += ':' + action['track']
        elif 'kind' in action:
            label += ':' + str(action['kind'])
        spend_by_action[label]['events'] += 1
        spend_by_action[label]['knowledge'] += row['amount']
    nonresearch = [row for row in spending if not row['research_action']]
    mine_counts = [row['legal_mine_candidates'] for row in choices]
    return {
        'games': len(games),
        'decisions': decisions,
        'research_offered_decisions': len(offered),
        'research_offered_rate': len(offered) / decisions if decisions else None,
        'research_selected_decisions': len(choices),
        'research_selected_rate_of_all': len(choices) / decisions if decisions else None,
        'research_selected_rate_when_offered': len(choices) / len(offered) if offered else None,
        'selected_tracks': dict(sorted(chosen_tracks.items())),
        'navigation_rank_at_research_choices': dict(sorted(navigation_ranks.items())),
        'legal_mine_candidates_at_research_choices': {
            'mean': sum(mine_counts) / len(mine_counts) if mine_counts else None,
            'zero_or_one': sum(value <= 1 for value in mine_counts),
            'total': len(mine_counts),
        },
        'direction_test_all_offered_states': _direction(offered),
        'direction_test_selected_research_states': _direction(choices),
        'knowledge_spend': {
            'events': len(spending),
            'total': sum(row['amount'] for row in spending),
            'nonresearch_events': len(nonresearch),
            'nonresearch_total': sum(row['amount'] for row in nonresearch),
            'by_action': dict(sorted(spend_by_action.items())),
        },
    }


def run(traces: list[Path], seeds: list[str], output: Path) -> dict:
    games = [diagnose(trace, seed) for trace, seed in zip(traces, seeds)]
    result = {'summary': summarize(games), 'games': games}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result['summary'], ensure_ascii=False))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace', type=Path, action='append', required=True)
    parser.add_argument('--seed', action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if len(args.trace) != len(args.seed):
        parser.error('--trace and --seed counts must match')
    run(args.trace, args.seed, args.output)
