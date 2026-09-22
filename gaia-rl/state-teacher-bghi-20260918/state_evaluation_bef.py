"""Opt-in stock-price experiment layered on the unchanged Bquadrupleprime."""
from dataclasses import replace
from collections import OrderedDict
import copy
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path

from gaia_rl._native import evaluation_successor_json

import state_evaluation_bquadrupleprime as base

# TODO(tune): user-approved round multipliers; round zero preserves setup prices.
ROUND_MULTIPLIERS = (1.0, 1.0, 1.0, 1.0, 0.8, 0.6, 0.4)
# TODO(tune): explicit held-resource prices for the independent (f-prime) arm.
F_PRIME_ORE_KNOWLEDGE = (2.67, 2.67, 2.67, 2.3, 1.7, 1.0, 0.4)
RESOURCE_FLOOR = 1/3
POWER_FLOORS = {'bowl1': 0.0, 'bowl2': 0.0, 'bowl3': 1/3}
STONE_BOWLS = {'Area1': 'bowl1', 'Area2': 'bowl2', 'Area3': 'bowl3'}
# TODO(tune): discounted value of normal power tokens returning after the Gaia phase.
GAIA_TOKEN_RETURN_DISCOUNT = 0.8
N_INCOME_HORIZON = 3.5  # TODO(tune): one next income, independent of the live round.
PASS_REALIZED_INCOME_HORIZON = N_INCOME_HORIZON - 1
N_SECURED_PLANET_VP = (0.0, 4.0, 4.0, 4.0, 3.0, 2.0, 1.0)  # TODO(tune)
# TODO(tune): B18-03/B19-06; prioritize at most four currently fundable colonies.
R_REACHABLE_WEIGHTS = (1.0, 0.6, 0.4, 0.2)
# TODO(tune): one low-cost route per planet class and terraforming-step group.
FAST_EXPANSION_PER_GROUP = 1
I_PRIME_SCAN_LIMIT = 5
I_PRIME_CACHE_LIMIT = 4096
_i_prime_cache: OrderedDict[tuple, tuple[str, tuple[dict, ...]]] = OrderedDict()
INCOME_FIELDS = ('ore', 'credits', 'knowledge', 'qic', 'power_charge', 'power_tokens', 'vp')
BOOSTER_INCOME = json.loads((Path(__file__).resolve().parents[2] /
    'gaia-frontend/src/data/income.json').read_text())['boosters']


@lru_cache(maxsize=4096)
def _reachable_planets(state_json: str, actor: int) -> tuple[float, tuple[str, ...]]:
    state = json.loads(state_json)
    if not state['round'] or 'Ended' in state['phase']:
        return 0.0, ()
    player = next(p for p in state['players'] if p['player_id'] == actor)
    if player['passed'] or sum(s['kind'] == 'Mine' for s in player['structures']) >= 8:
        return 0.0, ()
    facts = base.base.engine_facts(state, player)
    reach = base.base._reach(player, facts)
    resources = player['resources']
    candidates = []
    for option in base.base.planet_opportunities(state, player, facts=facts):
        planet = state['board']['hexes'][option.coord]['planet']
        kind = planet['planet_type']
        if kind == 'Transdim' and not planet['is_gaia_formed']:
            continue
        suitable = (option.category == 'gaia'
                    or kind in base.base.RING and option.terraform_steps <= 1)
        range_qic = max(0, (option.distance-reach+1)//2)
        if (not suitable or range_qic > 1 or option.ore > resources['ore']
                or option.credits > resources['credits'] or option.qic > resources['qic']):
            continue
        candidates.append(option.coord)
    coords = tuple(sorted(candidates)[:len(R_REACHABLE_WEIGHTS)])
    mine_value = N_SECURED_PLANET_VP[state['round']]
    return mine_value * sum(R_REACHABLE_WEIGHTS[:len(coords)]), coords


def reachable_planet_value(state: dict, actor: int) -> tuple[float, tuple[str, ...]]:
    """Fundable home/one-step/Gaia colonies within native range plus one QIC jump."""
    return _reachable_planets(json.dumps(state, sort_keys=True), actor)


def _booster_income_vp(player: dict) -> float:
    row = BOOSTER_INCOME.get(str(player['booster']))
    if row is None:
        return 0.0
    income = dict(zip(INCOME_FIELDS, row))
    return (base.base._payout_vp(income) + income['power_charge'] * base.base.INCOME_CHARGE_VP
            + income['power_tokens'] / 3)


def stock_prices(round_number: int, *, direct_stock_prices: bool = False) -> dict[str, float]:
    if direct_stock_prices:
        unit = F_PRIME_ORE_KNOWLEDGE[round_number]
        return {'ore': unit, 'credits': unit * 0.3, 'knowledge': unit, 'qic': unit * 1.75}
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
                   distributed_research: bool = False, round_resource_prices: bool = False,
                   booster_one_income: bool = False, gaia_token_return: bool = False,
                   fast_expansion: bool = False, fixed_income_and_planets: bool = False,
                   direct_stock_prices: bool = False,
                   federation_satellite_tokens: bool = False,
                   density_bonus: bool = False,
                   token_ore_price: bool = False,
                   pass_realized_income: bool = False,
                   reachable_planets: bool = False) -> base.base.Evaluation:
    income_horizon = (PASS_REALIZED_INCOME_HORIZON
                      if fixed_income_and_planets and pass_realized_income
                      else N_INCOME_HORIZON)
    result = base.evaluate_state(state, actor, top_n=top_n, conserve_resources=conserve_resources,
        secured_planets=secured_planets or fixed_income_and_planets, token_shortfall=token_shortfall,
        remaining_income=remaining_income, distributed_research=distributed_research,
        income_horizon=income_horizon if fixed_income_and_planets else None,
        density_bonus=density_bonus)
    if 'ore_stock' not in result.breakdown or not (
            round_resource_prices or booster_one_income or gaia_token_return or fixed_income_and_planets
            or direct_stock_prices or token_ore_price or reachable_planets):
        return result
    player = next(p for p in state['players'] if p['player_id'] == actor)
    resources = player['resources']
    breakdown = dict(result.breakdown)
    power = resources['power']
    if booster_one_income and remaining_income and (state['round'] < 6 or fixed_income_and_planets):
        # A held booster is guaranteed for the next income, not every later round.
        surplus_horizon = (income_horizon-(1 if state['round'] < 6 else 0) if fixed_income_and_planets
                           else (5-state['round']) * base.base.REMAINING_INCOME_DISCOUNT)
        breakdown['future_income'] -= (surplus_horizon
                                       * _booster_income_vp(player))
    if fixed_income_and_planets:
        breakdown['secured_planets'] = (len(base.base.secured_planet_coords(state, actor))
                                        * N_SECURED_PLANET_VP[state['round']])
    if gaia_token_return:
        gaia_tokens = power['gaia_forming'] + power['gaia_bowl']
        returning = gaia_tokens + int(power.get('brainstone') == 'Gaia')
        if token_shortfall:
            target = base.base.faction_modifier(state, player).token_target
            active = base.base.active_token_count(power) + returning
            breakdown['token_shortfall'] = -base.base.TOKEN_SHORTFALL_VP * max(0, target-active)
        destination_value = 0.6 if player['faction'] == 'Terrans' else 0.0
        breakdown['power_stock'] += gaia_tokens * destination_value * GAIA_TOKEN_RETURN_DISCOUNT
    if federation_satellite_tokens and token_shortfall:
        # A satellite has already paid its one-time stock value by leaving a bowl. Do not also
        # treat that same physical token as permanently missing from the structural token pool.
        satellites = sum(cell.get('satellites', []).count(actor)
                         for cell in state['board']['hexes'].values())
        returning = (power['gaia_forming'] + power['gaia_bowl']
                     + int(power.get('brainstone') == 'Gaia') if gaia_token_return else 0)
        target = base.base.faction_modifier(state, player).token_target
        structural = base.base.active_token_count(power) + returning + satellites
        breakdown['token_shortfall'] = (-base.base.TOKEN_SHORTFALL_VP
                                        * max(0, target-structural))
    if round_resource_prices or direct_stock_prices:
        for key, price in stock_prices(state['round'], direct_stock_prices=direct_stock_prices).items():
            breakdown[key+'_stock'] = resources[key]*price
        prices = bowl_prices(state['round'])
        active = sum(power[key]*price for key, price in prices.items())
        # Preserve the established 3x Brainstone ratio and the separate Gaia return value.
        if power.get('brainstone') in STONE_BOWLS:
            active += 3*prices[STONE_BOWLS[power['brainstone']]]
        original_active = base.base.power_value(power, None, future=False)
        breakdown['power_stock'] += active-original_active
        breakdown['token_shortfall'] *= ROUND_MULTIPLIERS[state['round']]
    if token_ore_price and token_shortfall:
        target = base.base.faction_modifier(state, player).token_target
        returning = (power['gaia_forming'] + power['gaia_bowl']
                     + int(power.get('brainstone') == 'Gaia') if gaia_token_return else 0)
        satellites = (sum(cell.get('satellites', []).count(actor)
                          for cell in state['board']['hexes'].values())
                      if federation_satellite_tokens else 0)
        structural = base.base.active_token_count(power) + returning + satellites
        # TODO(tune): LF01 prices a new token at 3.2 charge versus 4 charge per ore.
        token_price = F_PRIME_ORE_KNOWLEDGE[state['round']] * 0.8
        breakdown['token_shortfall'] = -token_price * max(0, target-structural)
    if reachable_planets:
        breakdown['reachable_planets'] = reachable_planet_value(state, actor)[0]
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
    return (stock_prices(state['round'], direct_stock_prices=options['direct_stock_prices']),
            bowl_prices(state['round'])) if options['round_resource_prices'] or options['direct_stock_prices'] else (
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
    if options['fast_expansion']:
        free_formers = max(0, player['gaiaformers_total']-player['gaiaformers_deployed']
            -player['gaiaformers_in_gaia_area']-player['resources']['spent_gaia_formers'])
        groups = {}
        for option in opportunities:
            if (state['board']['hexes'][option.coord]['planet']['planet_type'] == 'Transdim'
                    or option.formers > free_formers):
                continue
            group = (option.category, option.terraform_steps)
            groups.setdefault(group, []).append(option)
        opportunities = tuple(option for group in sorted(groups)
            for option in sorted(groups[group], key=lambda item: (-item.value_vp, item.coord))
                [:FAST_EXPANSION_PER_GROUP])
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


def _i_prime_key(state: dict, player: dict, actor: int) -> tuple:
    structures = tuple(sorted((item['hex'], str(item['kind'])) for item in player['structures']))
    buildings_hash = sha256(repr(structures).encode()).hexdigest()
    tracks = tuple(player['research_tracks'][key] for key in base.base.TRACK_IDS)
    resources = player['resources']
    # Unit-width intervals retain exact affordability boundaries while still
    # sharing results among identical resource states reached through a search.
    ore_interval = (resources['ore'], resources['ore'] + 1)
    credit_interval = (resources['credits'], resources['credits'] + 1)
    return (actor, state['round'], buildings_hash, tracks, resources['qic'],
            ore_interval, credit_interval)


def _i_prime_guard(state: dict, player: dict, options: dict) -> str:
    """Reject cache collisions when a requested coarse key omits board or powers."""
    relevant = (state['board']['hexes'], state['used_power_actions'],
                player['resources']['power'], player['gaiaformers_total'],
                player['gaiaformers_deployed'], player['gaiaformers_in_gaia_area'],
                player['resources']['spent_gaia_formers'], player['tech_tiles'],
                player['covered_tech_tiles'], player['booster'], player['passed'], options)
    return sha256(repr(relevant).encode()).hexdigest()


def _i_prime_route(state: dict, actor: int, opportunity, action: dict,
                   prices: dict, bowls: dict, before_facts: dict,
                   before_federation: float) -> dict | None:
    funded = copy.deepcopy(state)
    funded['phase'] = {'ActionPhase': {'active_player': actor}}
    player = next(p for p in funded['players'] if p['player_id'] == actor)
    player['passed'] = False
    resources = player['resources']
    for key in ('ore', 'credits', 'qic'):
        resources[key] += max(0, getattr(opportunity, key)-resources[key])
    if action['type'] == 'PowerAction':
        resources['power']['bowl3'] += max(0, 8-resources['power']['bowl3'])
    funded_stock = _stock_value(resources, prices, bowls)
    try:
        after = json.loads(evaluation_successor_json(json.dumps(funded), actor, json.dumps(action)))
    except RuntimeError:
        return None
    final = next(p for p in after['players'] if p['player_id'] == actor)
    cost = funded_stock-_stock_value(final['resources'], prices, bowls)
    after_facts = base.base.engine_facts(after, final)
    income_before, income_after = before_facts['income'], after_facts['income']
    income_delta = (base.base._payout_vp(income_after)-base.base._payout_vp(income_before)
                    + (income_after.get('power_charge', 0)-income_before.get('power_charge', 0))
                    * base.base.INCOME_CHARGE_VP
                    + (income_after.get('power_tokens', 0)-income_before.get('power_tokens', 0))/3)
    future_delta = income_delta * max(0, 5-state['round']) * base.base.REMAINING_INCOME_DISCOUNT
    modifier = base.base.faction_modifier(after, final, facts=after_facts)
    federation_delta = (base.base.federation_values(after, final, modifier)['federation_readiness']
                        - before_federation)
    delta = -cost + future_delta + federation_delta
    return {'action': action, 'legal': True, 'cost_vp': cost, 'delta_vp': delta,
            'breakdown': {'construction_cost': -cost, 'future_income': future_delta,
                          'federation_readiness': federation_delta}}


def i_prime_expansion_details(state: dict, actor: int, *, discounted: bool,
                              **options) -> tuple[dict, ...]:
    player = next(p for p in state['players'] if p['player_id'] == actor)
    if (not state['round'] or player['passed'] or 'Ended' in state['phase']
            or (discounted and state['round'] >= 6)):
        return ()
    key = _i_prime_key(state, player, actor)
    guard = _i_prime_guard(state, player, options)
    cached = _i_prime_cache.get(key)
    if cached is not None and cached[0] == guard:
        _i_prime_cache.move_to_end(key)
        return copy.deepcopy(cached[1])
    facts = base.base.engine_facts(state, player)
    funded_player = copy.deepcopy(player)
    funded_player['resources']['qic'] = 255
    free_formers = max(0, player['gaiaformers_total']-player['gaiaformers_deployed']
                       -player['gaiaformers_in_gaia_area']-player['resources']['spent_gaia_formers'])
    opportunities = [option for option in base.base.planet_opportunities(
        state, funded_player, facts=facts)
        if state['board']['hexes'][option.coord]['planet']['planet_type'] != 'Transdim'
        and option.formers <= free_formers]
    opportunities.sort(key=lambda option: (option.qic, option.terraform_steps,
                                           option.ore, option.distance, option.coord))
    prices, bowls = _prices(state, options)
    modifier = base.base.faction_modifier(state, player, facts=facts)
    federation = base.base.federation_values(state, player, modifier)['federation_readiness']
    rows = []
    for opportunity in opportunities[:I_PRIME_SCAN_LIMIT]:
        actions = [{'type': 'Build', 'coord': opportunity.coord}]
        actions.extend({'type': 'PowerAction', 'id': slot, 'coord': opportunity.coord}
                       for slot in (6, 2) if slot not in state['used_power_actions'])
        paths = [path for action in actions if (path := _i_prime_route(
            state, actor, opportunity, action, prices, bowls, facts, federation)) is not None]
        if paths:
            cheapest = min(paths, key=lambda path: path['cost_vp'])
            rows.append({'coord': opportunity.coord,
                         'value_vp': max(0.0, cheapest['delta_vp'])
                                     * (NEXT_ROUND_REALIZATION if discounted else 1.0),
                         'cheapest': cheapest, 'paths': paths})
    rows.sort(key=lambda row: (-row['value_vp'], row['coord']))
    result = tuple(rows)
    _i_prime_cache[key] = (guard, result)
    _i_prime_cache.move_to_end(key)
    if len(_i_prime_cache) > I_PRIME_CACHE_LIMIT:
        _i_prime_cache.popitem(last=False)
    return copy.deepcopy(result)


def evaluate_state(state: dict, actor: int, *, top_n: int = base.base.TOP_N,
                   conserve_resources: bool = True, secured_planets: bool = False,
                   token_shortfall: bool = False, remaining_income: bool = False,
                   distributed_research: bool = False, round_resource_prices: bool = False,
                   expansion_rescale: bool = False,
                   discounted_expansion: bool = False,
                   booster_one_income: bool = False,
                   gaia_token_return: bool = False,
                   fast_expansion: bool = False,
                   cached_expansion: bool = False,
                   fixed_income_and_planets: bool = False,
                   direct_stock_prices: bool = False,
                   federation_satellite_tokens: bool = False,
                   density_bonus: bool = False,
                   token_ore_price: bool = False,
                   pass_realized_income: bool = False,
                   reachable_planets: bool = False) -> base.base.Evaluation:
    options = dict(top_n=top_n, conserve_resources=conserve_resources, secured_planets=secured_planets,
        token_shortfall=token_shortfall, remaining_income=remaining_income,
        distributed_research=distributed_research, round_resource_prices=round_resource_prices,
        booster_one_income=booster_one_income, gaia_token_return=gaia_token_return,
        fast_expansion=fast_expansion, fixed_income_and_planets=fixed_income_and_planets,
        direct_stock_prices=direct_stock_prices,
        federation_satellite_tokens=federation_satellite_tokens,
        density_bonus=density_bonus, token_ore_price=token_ore_price,
        pass_realized_income=pass_realized_income,
        reachable_planets=reachable_planets)
    result = _evaluate_stock(state, actor, **options)
    if not (expansion_rescale or discounted_expansion) or 'expansion_opportunity' not in result.breakdown:
        return result
    result = _without_expansion(state, actor, options)
    rows = (i_prime_expansion_details(state, actor, discounted=discounted_expansion, **options)
            if cached_expansion else expansion_details(state, actor,
                discounted=discounted_expansion, **options))
    parts = dict(result.breakdown)
    parts['expansion_opportunity'] = sum(row['value_vp']*weight for row, weight in
        zip(rows[:top_n], EXPANSION_WEIGHTS))
    return replace(result, total_vp=sum(parts.values()), breakdown=parts)
