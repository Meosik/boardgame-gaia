"""Opt-in stock-price experiment layered on the unchanged Bquadrupleprime."""
from dataclasses import replace
import copy
from functools import lru_cache
import json

from gaia_rl._native import evaluation_successor_json

import state_evaluation_bquadrupleprime as base

# TODO(tune): user-approved round multipliers; round zero preserves setup prices.
ROUND_MULTIPLIERS = (1.0, 1.0, 1.0, 1.0, 0.8, 0.6, 0.4)
RESOURCE_FLOOR = 1/3
POWER_FLOORS = {'bowl1': 0.0, 'bowl2': 0.0, 'bowl3': 1/3}
STONE_BOWLS = {'Area1': 'bowl1', 'Area2': 'bowl2', 'Area3': 'bowl3'}


def stock_prices(round_number: int) -> dict[str, float]:
    multiplier = ROUND_MULTIPLIERS[round_number]
    return {key: max(RESOURCE_FLOOR, value*multiplier) for key, value in base.base.PRICES.items()}


def bowl_prices(round_number: int) -> dict[str, float]:
    prices = {}
    for key, floor in POWER_FLOORS.items():
        power = dict.fromkeys(POWER_FLOORS, 0)
        power[key] = 1
        original = base.base.power_value(power, None, future=False)
        prices[key] = max(floor, original*ROUND_MULTIPLIERS[round_number])
    return prices


def _evaluate_stock(state: dict, actor: int, *, top_n: int = base.base.TOP_N,
                   conserve_resources: bool = True, secured_planets: bool = False,
                   token_shortfall: bool = False, remaining_income: bool = False,
                   distributed_research: bool = False, round_resource_prices: bool = False) -> base.base.Evaluation:
    result = base.evaluate_state(state, actor, top_n=top_n, conserve_resources=conserve_resources,
        secured_planets=secured_planets, token_shortfall=token_shortfall,
        remaining_income=remaining_income, distributed_research=distributed_research)
    if not round_resource_prices or 'ore_stock' not in result.breakdown:
        return result
    player = next(p for p in state['players'] if p['player_id'] == actor)
    resources = player['resources']
    breakdown = dict(result.breakdown)
    for key, price in stock_prices(state['round']).items():
        breakdown[key+'_stock'] = resources[key]*price
    power = resources['power']
    prices = bowl_prices(state['round'])
    active = sum(power[key]*price for key, price in prices.items())
    # Preserve the established 3x Brainstone ratio and the separate Gaia return value.
    if power.get('brainstone') in STONE_BOWLS:
        active += 3*prices[STONE_BOWLS[power['brainstone']]]
    original_active = base.base.power_value(power, None, future=False)
    breakdown['power_stock'] = result.breakdown['power_stock']-original_active+active
    breakdown['token_shortfall'] *= ROUND_MULTIPLIERS[state['round']]
    return replace(result, total_vp=sum(breakdown.values()), breakdown=breakdown)

# TODO(tune): user-approved diminishing weights on three independent colony options.
EXPANSION_WEIGHTS = (1.0, 0.5, 0.25)
# TODO(tune): probability that a next-round colony option is still realizable.
NEXT_ROUND_REALIZATION = 0.6


def _without_expansion(state: dict, actor: int, options: dict) -> base.base.Evaluation:
    value = _evaluate_stock(state, actor, **options)
    if 'expansion_opportunity' not in value.breakdown:
        return value
    parts = dict(value.breakdown)
    parts['expansion_opportunity'] = 0.0
    # Immediate Gaia mines move into (e); retain the old Transdim project valuation only.
    parts['gaia_opportunity'] = sum(o.value_vp for o in value.opportunities
        if o.category == 'gaia' and state['board']['hexes'][o.coord]['planet']['planet_type'] == 'Transdim')
    return replace(value, total_vp=sum(parts.values()), breakdown=parts)


def _prices(state: dict, options: dict) -> tuple[dict, dict]:
    return (stock_prices(state['round']), bowl_prices(state['round'])) if options['round_resource_prices'] else (
        dict(base.base.PRICES), bowl_prices(1))


def _stock_value(resources: dict, prices: dict, bowls: dict) -> float:
    value = sum(resources[key]*price for key, price in prices.items())
    power = resources['power']
    value += sum(power[key]*price for key, price in bowls.items())
    if power.get('brainstone') in STONE_BOWLS:
        value += 3*bowls[STONE_BOWLS[power['brainstone']]]
    return value


@lru_cache(maxsize=2048)
def _expansion_details(state_json: str, actor: int, options_json: str,
                       discounted: bool = False) -> tuple[dict, ...]:
    state, options = json.loads(state_json), json.loads(options_json)
    player = next(p for p in state['players'] if p['player_id'] == actor)
    if (not state['round'] or player['passed'] or 'Ended' in state['phase']
            or (discounted and state['round'] >= 6)):
        return ()
    facts = base.base.engine_facts(state, player)
    # Cost enumeration must not discard a coordinate just because today's QIC is short.
    funded_player = copy.deepcopy(player)
    funded_player['resources']['qic'] = 255
    opportunities = base.base.planet_opportunities(state, funded_player, facts=facts)
    original = _without_expansion(state, actor, options)
    prices, bowls = _prices(state, options)
    rows = []
    for opportunity in opportunities:
        coord = opportunity.coord
        if state['board']['hexes'][coord]['planet']['planet_type'] == 'Transdim':
            continue
        if any(s['hex'] == coord for s in player['structures']):
            continue
        actions = [{'type': 'Build', 'coord': coord}]
        actions += [{'type': 'PowerAction', 'id': slot, 'coord': coord}
                    for slot in (6, 2) if slot not in state['used_power_actions']]
        paths = []
        for action in actions:
            funded = copy.deepcopy(state)
            funded['phase'] = {'ActionPhase': {'active_player': actor}}
            focal = next(p for p in funded['players'] if p['player_id'] == actor)
            focal['passed'] = False
            resources = focal['resources']
            loans = {}
            for key in ('ore', 'credits', 'qic'):
                loans[key] = max(0, getattr(opportunity, key)-resources[key])
                resources[key] += loans[key]
            # Temporary liquidity for native cost discovery, not invented game income.
            # Eight normal III tokens cover either allowed public action; unused tokens return.
            loan_power = max(0, 8-resources['power']['bowl3']) if action['type'] == 'PowerAction' else 0
            resources['power']['bowl3'] += loan_power
            try:
                after = json.loads(evaluation_successor_json(json.dumps(funded), actor, json.dumps(action)))
            except RuntimeError as error:
                paths.append({'action': action, 'legal': False, 'error': str(error)})
                continue
            final = next(p for p in after['players'] if p['player_id'] == actor)
            cost = _stock_value(resources, prices, bowls)-_stock_value(final['resources'], prices, bowls)
            debt_vp = 0.0
            for key, amount in loans.items():
                available = final['resources'][key]-amount
                debt_vp += max(0, -available)*prices[key]
                final['resources'][key] = max(0, available)
            # Unspent borrowed charges are in III; spent borrowed tokens moved to I.
            power = final['resources']['power']
            unused = min(loan_power, power['bowl3'])
            power['bowl3'] -= unused
            spent_loan = loan_power-unused
            if power['bowl1'] < spent_loan:
                raise ValueError('Native power route changed borrowed token accounting')
            power['bowl1'] -= spent_loan
            debt_vp += spent_loan*(bowls['bowl3']-bowls['bowl1'])
            value = _without_expansion(after, actor, options)
            changes = {key: value.breakdown[key]-old for key, old in original.breakdown.items()
                       if abs(value.breakdown[key]-old) > 1e-9}
            if debt_vp:
                changes['unfunded_cost'] = -debt_vp
            delta = value.total_vp-original.total_vp-debt_vp
            if discounted:
                # Only the income horizon changes; stock prices, round tiles and
                # public-action availability stay at the current round.
                income_change = changes.get('future_income', 0.0)
                if options['remaining_income']:
                    removed_income = income_change/(6-state['round'])
                else:
                    removed_income = income_change if state['round'] == 5 else 0.0
                delta -= removed_income
                if income_change:
                    changes['future_income'] = income_change-removed_income
            paths.append({'action': action, 'legal': True, 'cost_vp': cost, 'delta_vp': delta,
                          'debt_vp': debt_vp, 'breakdown': changes})
        legal = [path for path in paths if path['legal']]
        if legal:
            cheapest = min(legal, key=lambda path: path['cost_vp'])
            rows.append({'coord': coord,
                         'value_vp': max(0.0, cheapest['delta_vp'])*
                                     (NEXT_ROUND_REALIZATION if discounted else 1.0),
                         'cheapest': cheapest, 'paths': paths})
    return tuple(sorted(rows, key=lambda row: (-row['value_vp'], row['coord'])))


def expansion_details(state: dict, actor: int, *, discounted: bool = False,
                      **options) -> tuple[dict, ...]:
    return copy.deepcopy(_expansion_details(json.dumps(state, sort_keys=True), actor,
                                           json.dumps(options, sort_keys=True), discounted))


def evaluate_state(state: dict, actor: int, *, top_n: int = base.base.TOP_N,
                   conserve_resources: bool = True, secured_planets: bool = False,
                   token_shortfall: bool = False, remaining_income: bool = False,
                   distributed_research: bool = False, round_resource_prices: bool = False,
                   expansion_rescale: bool = False,
                   discounted_expansion: bool = False) -> base.base.Evaluation:
    options = dict(top_n=top_n, conserve_resources=conserve_resources, secured_planets=secured_planets,
        token_shortfall=token_shortfall, remaining_income=remaining_income,
        distributed_research=distributed_research, round_resource_prices=round_resource_prices)
    result = _evaluate_stock(state, actor, **options)
    if not (expansion_rescale or discounted_expansion) or 'expansion_opportunity' not in result.breakdown:
        return result
    result = _without_expansion(state, actor, options)
    rows = expansion_details(state, actor, discounted=discounted_expansion, **options)
    parts = dict(result.breakdown)
    parts['expansion_opportunity'] = sum(row['value_vp']*weight for row, weight in
        zip(rows[:top_n], EXPANSION_WEIGHTS))
    return replace(result, total_vp=sum(parts.values()), breakdown=parts)
