"""Opt-in Bquadrupleprime: preserve Btripleprime except research progress (d)."""
from dataclasses import replace

import state_evaluation_btripleprime as base

# TODO(tune): user-approved breadth limit; Science is counted separately.
NON_SCIENCE_TRACK_LIMIT = 3


def research_progress_details(state: dict, player: dict, facts: dict) -> tuple[dict, ...]:
    """Only the next unachieved threshold contributes fractional progress.

    Banked track points stay in base.research_final_vp, including unselected tracks.
    Priced native resource payouts, range and terraforming costs are not bonuses.
    Equal-level tracks retain the existing native track order, not a value sort.
    """
    curve = facts['final_track_vp']
    thresholds = [level for level in range(1, len(curve)) if curve[level] > curve[level-1]]
    maximum = len(curve)-1
    levels = player['research_tracks']
    eligible = [track for track in base.TRACK_IDS if track != 'science']
    selected = set(sorted(eligible, key=lambda track: -levels[track])[:NON_SCIENCE_TRACK_LIMIT])
    if levels['science'] > 0:
        selected.add('science')
    modifier = base.faction_modifier(state, player)
    rows = []
    for track, native_track in base.TRACK_IDS.items():
        level = levels[track]
        enabled = track != 'navigation' or modifier.navigation_research
        allocations = []
        previous = 0
        for target in thresholds:
            allowed = enabled
            if target == maximum and level < target:
                allowed = allowed and bool(player['federation_tokens']) and not any(
                    p['player_id'] != player['player_id'] and p['research_tracks'][track] == maximum
                    for p in state['players'])
                if track == 'navigation':
                    allowed = allowed and base._lost_planet_available(state, player, facts)
            reached = max(0, min(level, target)-previous)
            reward = facts['research_rewards'][native_track][target]
            excluded_resources = sum(reward.get(key, 0)*price for key, price in base.PRICES.items())
            terminal_increment = curve[target]-curve[target-1]
            immediate_vp = reward.get('vp', 0)
            next_unreached = previous <= level < target
            value = ((terminal_increment+immediate_vp)*reached/(target-previous)
                     if allowed and next_unreached else 0.0)
            allocations.append({'threshold': target, 'previous_threshold': previous,
                                'reached_spaces': reached, 'spaces': target-previous,
                                'allowed': allowed, 'next_unreached': next_unreached,
                                'terminal_increment': terminal_increment,
                                'immediate_vp': immediate_vp, 'excluded_resource_vp': excluded_resources,
                                'allocated_vp': value})
            previous = target
        fractional = sum(row['allocated_vp'] for row in allocations)
        rows.append({'track': track, 'level': level, 'selected': track in selected and enabled,
                     'banked_track_vp': float(curve[level]), 'fractional_vp': fractional,
                     'progress_vp': fractional if track in selected and enabled else 0.0,
                     'thresholds': allocations})
    return tuple(rows)


def research_progress(state: dict, player: dict, facts: dict) -> float:
    return sum(row['progress_vp'] for row in research_progress_details(state, player, facts))


def evaluate_state(state: dict, actor: int, *, top_n: int = base.TOP_N,
                   conserve_resources: bool = True, secured_planets: bool = False,
                   token_shortfall: bool = False, remaining_income: bool = False,
                   distributed_research: bool = False,
                   income_horizon: float | None = None) -> base.Evaluation:
    result = base.evaluate_state(state, actor, top_n=top_n, conserve_resources=conserve_resources,
        secured_planets=secured_planets, token_shortfall=token_shortfall, remaining_income=remaining_income,
        income_horizon=income_horizon)
    if not distributed_research or 'research_progress' not in result.breakdown:
        return result
    player = next(p for p in state['players'] if p['player_id'] == actor)
    facts = base.engine_facts(state, player)
    breakdown = dict(result.breakdown)
    breakdown['research_progress'] = research_progress(state, player, facts)
    return replace(result, total_vp=sum(breakdown.values()), breakdown=breakdown)
