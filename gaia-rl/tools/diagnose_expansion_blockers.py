"""Replay an existing game and diagnose expansion access without changing it."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path

from gaia_rl import Environment
from gaia_rl._native import evaluation_facts_json, evaluation_successor_json
import state_evaluation_bef as evaluator


TRACKS = ('navigation', 'terraforming', 'gaia', 'economy', 'science', 'ai')
MINE_ACTIONS = {'Build', 'TwilightRangeBuild', 'RoundBoosterRangeBuild'}
EVALUATION_OPTIONS = dict(
    token_shortfall=True, remaining_income=True, distributed_research=True,
    round_resource_prices=True, discounted_expansion=False,
    booster_one_income=True, gaia_token_return=True,
    fixed_income_and_planets=True, direct_stock_prices=True,
    federation_satellite_tokens=True, density_bonus=False,
    token_ore_price=False,
)


def _facts(state: dict, actor: int) -> dict:
    return json.loads(evaluation_facts_json(json.dumps(state), actor))


def _range_and_cost(state: dict, actor: int) -> list[dict]:
    player = state['players'][actor]
    facts = _facts(state, actor)
    base = evaluator.base.base
    modifier = base.faction_modifier(state, player, facts=facts)
    reach = base._reach(player, facts)
    resources = player['resources']
    mine_count = sum(structure['kind'] == 'Mine' for structure in player['structures'])
    own = {structure['hex'] for structure in player['structures']}
    rows = []
    for coord, distance in base._distances(state, player).items():
        cell = state['board']['hexes'][coord]
        planet = cell['planet']
        if not planet or coord in own:
            continue
        owner = planet['owner']
        reserved = owner == actor and planet['planet_type'] == 'Transdim'
        if cell['structures'] or (owner is not None and not reserved):
            continue
        kind = planet['planet_type']
        if kind == 'Transdim' and not planet['is_gaia_formed']:
            continue
        if not (kind in base.RING or kind in ('ProtoPlanet', 'Gaia', 'Asteroid')
                or planet['is_gaia_formed'] or reserved):
            continue
        range_qic = max(0, (distance-reach+1)//2)
        ore, credits, entry_qic, formers, terraform_ore = 1, 2, 0, 0, 0
        if kind == 'Gaia' or planet['is_gaia_formed'] or reserved:
            ore += modifier.gaia_ore
            entry_qic = 0 if reserved else modifier.gaia_qic
        elif kind == 'Asteroid':
            ore, credits, formers = 0, 0, 1
        else:
            steps = 3 if kind == 'ProtoPlanet' else modifier.terraform_steps[kind]
            terraform_ore = steps * facts['terraform_ore_per_step'][
                player['research_tracks']['terraforming']]
            ore += terraform_ore
        in_range = range_qic <= resources['qic']
        enough = {
            'mine': mine_count < 8,
            'qic': range_qic+entry_qic <= resources['qic'],
            'ore': ore <= resources['ore'],
            'credits': credits <= resources['credits'],
            'former': formers <= max(0, player['gaiaformers_total']
                - player['gaiaformers_deployed'] - player['gaiaformers_in_gaia_area']
                - resources['spent_gaia_formers']),
        }
        affordable = in_range and all(enough.values())
        if not enough['mine']:
            blocker = 'mine_inventory'
        elif not in_range:
            blocker = 'range'
        elif (not enough['ore'] and terraform_ore
              and resources['ore'] >= ore-terraform_ore):
            blocker = 'terraforming_cost'
        elif not affordable:
            blocker = 'resources'
        else:
            blocker = 'affordable'
        rows.append({
            'coord': coord, 'distance': distance, 'reach': reach,
            'range_qic': range_qic, 'ore': ore, 'credits': credits,
            'entry_qic': entry_qic, 'terraform_ore': terraform_ore,
            'in_range': in_range, 'affordable': affordable, 'blocker': blocker,
        })
    return rows


def _track_delta(state: dict, actor: int, action: dict) -> float:
    after = json.loads(evaluation_successor_json(json.dumps(state), actor, json.dumps(action)))
    before_value = evaluator.evaluate_state(state, actor, **EVALUATION_OPTIONS).total_vp
    after_value = evaluator.evaluate_state(after, actor, **EVALUATION_OPTIONS).total_vp
    return after_value-before_value


def _research_ranking(snapshot: dict) -> dict[str, dict]:
    actor = snapshot['player']
    by_track = {}
    for candidate in snapshot['candidates']:
        action = candidate['action']
        if action['type'] != 'ResearchAdvance':
            continue
        delta = _track_delta(snapshot['state'], actor, action)
        old = by_track.get(action['track'])
        if old is None or delta > old['delta_vp']:
            by_track[action['track']] = {'delta_vp': delta, 'action': action}
    ordered = sorted(by_track, key=lambda track: (-by_track[track]['delta_vp'], track))
    for rank, track in enumerate(ordered, 1):
        by_track[track]['rank'] = rank
    return by_track


def _is_mine_build(action: dict) -> bool:
    return (action['type'] in MINE_ACTIONS
            or action['type'] == 'PowerAction' and action.get('coord') is not None
            and action.get('id') in (2, 6))


def diagnose(trace: Path, output: Path, seed: str) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(line) for line in gzip.open(trace, 'rt')]
    env = Environment(seed, 2000)
    first_states = {}
    end_states = {}
    qic_used = defaultdict(Counter)
    builds = defaultdict(Counter)
    research_distribution = Counter()
    research_choices = []
    for recorded in rows:
        snapshot = json.loads(env.snapshot_json())
        state = snapshot['state']
        round_number = state['round']
        actor = snapshot['player']
        faction = state['players'][actor]['faction']
        phase = state['phase']
        if (round_number >= 1 and isinstance(phase, dict) and 'ActionPhase' in phase
                and (round_number, faction) not in first_states):
            first_states[(round_number, faction)] = {
                'state': json.loads(json.dumps(state)),
                'native_legal_build_candidates': sum(
                    candidate['action']['type'] == 'Build'
                    for candidate in snapshot['candidates']),
            }
        action = recorded['action']
        if action['type'] == 'ResearchAdvance':
            ranking = _research_ranking(snapshot)
            research_distribution[action['track']] += 1
            research_choices.append({
                'step': snapshot['steps'], 'round': round_number, 'faction': faction,
                'chosen': action['track'],
                'chosen_rank': ranking[action['track']]['rank'],
                'navigation': ranking.get('Navigation'),
                'terraforming': ranking.get('Terraforming'),
                'ranking': {track: {'delta_vp': value['delta_vp'], 'rank': value['rank']}
                            for track, value in ranking.items()},
            })
        if _is_mine_build(action):
            builds[round_number][faction] += 1
        matches = [index for index, candidate in enumerate(snapshot['candidates'])
                   if candidate['action'] == action]
        if len(matches) != 1:
            raise RuntimeError(f'expected one replay match at step {snapshot["steps"]}, got {len(matches)}')
        before_qic = state['players'][actor]['resources']['qic']
        env.step(snapshot['decision_id'], matches[0])
        after = json.loads(env.snapshot_json())
        after_qic = after['state']['players'][actor]['resources']['qic']
        qic_used[round_number][faction] += max(0, before_qic-after_qic)
        if after['state']['round'] != round_number:
            end_states[round_number] = json.loads(json.dumps(state))
    terminal = json.loads(env.snapshot_json())
    if terminal['state']['round'] >= 1:
        end_states[terminal['state']['round']] = terminal['state']

    round_factions = []
    availability = []
    blocker_counts = Counter()
    for (round_number, faction), observation in sorted(first_states.items()):
        state = observation['state']
        actor = next(p['player_id'] for p in state['players'] if p['faction'] == faction)
        opportunities = _range_and_cost(state, actor)
        blocker_counts.update(row['blocker'] for row in opportunities if row['blocker'] != 'affordable')
        availability.append({
            'round': round_number, 'faction': faction,
            'suitable_planets': len(opportunities),
            'in_range_planets': sum(row['in_range'] for row in opportunities),
            'affordable_planets': sum(row['affordable'] for row in opportunities),
            'native_legal_build_candidates': observation['native_legal_build_candidates'],
            'actual_builds': builds[round_number][faction],
            'details': opportunities,
        })
        end = end_states[round_number]
        player = next(p for p in end['players'] if p['faction'] == faction)
        round_factions.append({
            'round': round_number, 'faction': faction,
            'research': {track: player['research_tracks'][track] for track in TRACKS},
            'qic_held_end': player['resources']['qic'],
            'qic_used': qic_used[round_number][faction],
        })
    blocked_total = sum(blocker_counts.values())
    result = {
        'source_trace': str(trace), 'seed': seed, 'games': 1,
        'modified_game': False,
        'round_factions': round_factions,
        'availability_at_first_action': availability,
        'research_advance_distribution': dict(sorted(research_distribution.items())),
        'research_choices': research_choices,
        'blocker_counts': dict(blocker_counts),
        'blocker_ratios': {key: value/blocked_total for key, value in blocker_counts.items()},
        'blocker_observations': blocked_total,
    }
    (output/'diagnosis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({
        'round_faction_rows': len(round_factions),
        'research_advances': sum(research_distribution.values()),
        'blocker_counts': dict(blocker_counts),
    }, ensure_ascii=False))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', default='state-evaluation-ab-20260917-1580')
    args = parser.parse_args()
    diagnose(args.trace, args.output, args.seed)
