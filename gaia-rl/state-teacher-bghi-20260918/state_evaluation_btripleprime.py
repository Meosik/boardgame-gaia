"""Opt-in, faction-common state evaluation in VP units.

This module does not rank actions or replace any existing teacher. A caller may
compare two native successor states by their returned ``total_vp`` values.
"""

from collections import deque
from dataclasses import dataclass
from pathlib import Path
import json
import tomllib

from faction_learning import FACTIONS
from gaia_rl._native import evaluation_facts_json

ROOT = Path(__file__).resolve().parents[2]
FACTION_DATA = tomllib.loads((ROOT / 'gaia-engine/data/factions.toml').read_text())['factions']
RING = ('Terra', 'Oxide', 'Volcanic', 'Desert', 'Swamp', 'Titanium', 'Ice')
TRACK_IDS = {'terraforming': 'Terraforming', 'navigation': 'Navigation',
             'ai': 'ArtificialIntelligence', 'gaia': 'GaiaProject',
             'economy': 'Economy', 'science': 'Science'}
# TODO(tune): provisional VP prices above the 1/3 VP salvage floor.
PRICES = {'ore': 2.67, 'credits': 0.8, 'knowledge': 2.67, 'qic': 4.67}
# TODO(tune): number of near-term colony options, not a native game limit.
TOP_N = 3
# TODO(tune): option ceiling and cost attenuation scale, both expressed in VP.
COLONY_OPTION_VP = 8.0
COST_SCALE_VP = 1.0
# TODO(tune): an unfinished project cannot be mined until a later Gaia phase.
PROJECT_DISCOUNT = 0.5
# TODO(tune): one next income, discounted; never multiply by two future rounds.
INCOME_DISCOUNT = 0.5
# TODO(tune): delayed return retains half the destination bowl value.
GAIA_RETURN_DISCOUNT = 0.5
# TODO(tune): user-approved LF01 retained-planet prices; no round-zero value.
SECURED_PLANET_VP = (0.0, 4.0, 4.0, 4.0, 4.0, 3.0, 2.0)
# TODO(tune): user-approved B02/LF01 missing-token penalty in VP.
TOKEN_SHORTFALL_VP = 2.13
# TODO(tune): approved remaining-income discount and linear charge price.
REMAINING_INCOME_DISCOUNT = 0.7
INCOME_CHARGE_VP = 0.6
# TODO(tune): user-approved federation-density target and distance weights.
DENSITY_TARGET_POWER = 7
DENSITY_ADJACENT_VP = 1.0
DENSITY_DISTANCE_TWO_VP = 0.5


@dataclass(frozen=True)
class FactionModifiers:
    terraform_steps: dict[str, int]
    gaia_ore: int = 0
    gaia_qic: int = 1
    cohabit: bool = False
    navigation_research: bool = True
    vp: float = 0.0
    federation: dict | None = None
    brainstone_return: str | None = None
    token_target: int = 5  # TODO(tune): base active-token target, not a rule limit.


@dataclass(frozen=True)
class PlanetOpportunity:
    coord: str
    category: str
    distance: int
    terraform_steps: int
    ore: int
    credits: int
    qic: int
    formers: int = 0
    power_tokens: int = 0
    delayed: bool = False

    @property
    def value_vp(self) -> float:
        cost = self.ore * PRICES['ore'] + self.credits * PRICES['credits'] + self.qic * PRICES['qic']
        # Access value, not an unearned construction reward or a second resource stock.
        value = COLONY_OPTION_VP / (1 + cost / COST_SCALE_VP)
        return value * (PROJECT_DISCOUNT if self.delayed else 1)


@dataclass(frozen=True)
class Evaluation:
    total_vp: float
    breakdown: dict[str, float]
    opportunities: tuple[PlanetOpportunity, ...] = ()
    tile_values: tuple[dict, ...] = ()
    ship_values: tuple[dict, ...] = ()


def faction_modifier(state: dict, player: dict, *, facts: dict | None = None) -> FactionModifiers:
    """All faction-dependent cost/access rules live here; no action bonuses.

    Rules mirror engine.rs::terraforming_distance/gaia_qic_cost and the native
    faction abilities. No hypothetical faction ability payout is added to VP.
    """
    faction = player['faction']
    homes = {row['id']: row['home_planet'] for row in FACTION_DATA}
    home = homes[faction]
    steps = {}
    if home in RING:
        for target in RING:
            gap = abs(RING.index(home) - RING.index(target))
            steps[target] = min(gap, len(RING) - gap)
    elif faction in ('Tinkeroids', 'Moweyds'):
        expensive = player.get('expensive_terraforming_planet_types', [])
        if not expensive:
            expensive = [homes[p['faction']] for p in state['players']
                         if p['player_id'] != player['player_id'] and homes[p['faction']] in RING]
        steps = {target: 3 if target in expensive else 1 for target in RING}
    else:
        steps = dict.fromkeys(RING, 1 if faction == 'Darkanians' else 2)
    institute = any(s['kind'] == 'PlanetaryInstitute' for s in player['structures'])
    return FactionModifiers(
        steps, gaia_ore=int(faction == 'Gleens'),
        gaia_qic=(0 if faction == 'Gleens' else
                  2 if faction in ('Tinkeroids', 'Moweyds', 'SpaceGiants', 'Darkanians') else 1),
        cohabit=faction == 'Lantids',
        navigation_research=faction != 'BalTaks' or institute,
        federation=facts['federation'] if facts is not None else None,
        brainstone_return=facts['brainstone_return'] if facts is not None else None,
        token_target=4 if faction == 'Taklons' else 5,  # TODO(tune): B10; stone counts once.
    )


def _distances(state: dict, player: dict) -> dict[str, int]:
    """Board-only multi-source BFS, including the untracked Lost Planet origin."""
    cells = state['board']['hexes']
    starts = {s['hex'] for s in player['structures']}
    lost = state['board'].get('lost_planet')
    planet = cells.get(lost, {}).get('planet')
    if planet and planet['owner'] == player['player_id']:
        starts.add(lost)
    distances = {coord: 0 for coord in starts if coord in cells}
    queue = deque(distances)
    while queue:
        coord = queue.popleft()
        q, r = map(int, coord.split(','))
        for dq, dr in ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)):
            neighbor = f'{q+dq},{r+dr}'
            if neighbor in cells and neighbor not in distances:
                distances[neighbor] = distances[coord] + 1
                queue.append(neighbor)
    return distances


def engine_facts(state: dict, player: dict) -> dict:
    """Read native rule data; no fallback to copied research-level constants."""
    return json.loads(evaluation_facts_json(json.dumps(state), player['player_id']))


def _reach(player: dict, facts: dict) -> int:
    active = set(player['tech_tiles']) - set(player['covered_tech_tiles'])
    return facts['navigation_range'][player['research_tracks']['navigation']] + int(12 in active)


def _free_formers(player: dict) -> int:
    return max(0, player['gaiaformers_total'] - player['gaiaformers_deployed']
               - player['gaiaformers_in_gaia_area'] - player['resources']['spent_gaia_formers'])


def planet_opportunities(state: dict, player: dict, *, facts: dict | None = None) -> tuple[PlanetOpportunity, ...]:
    """Ordinary mines/projects only: no conversions, future income or ship actions.

    Prices match the native Build/GaiaFormation path. New Transdim projects pay
    range QIC twice (formation, then mine) with today's unchanged range/origins.
    Committed projects pay only the remaining mine cost. Policy-specific Brainstone
    availability is applied by the shared-budget selector, not by native cost rules.
    """
    facts = engine_facts(state, player) if facts is None else facts
    modifier = faction_modifier(state, player, facts=facts)
    own = {s['hex'] for s in player['structures']}
    reach = _reach(player, facts)
    options = []
    for coord, distance in _distances(state, player).items():
        cell = state['board']['hexes'][coord]
        planet = cell['planet']
        if not planet or coord in own:
            continue
        owner, kind = planet['owner'], planet['planet_type']
        cohabit = modifier.cohabit and owner is not None and owner != player['player_id']
        reserved = owner == player['player_id'] and kind == 'Transdim'
        if not cohabit and (cell['structures'] or (owner is not None and not reserved)):
            continue
        qic = max(0, (distance - reach + 1) // 2)
        if qic > player['resources']['qic']:
            continue
        ore, credits, steps, formers, power = 1, 2, 0, 0, 0
        category, delayed = 'expansion', False
        if cohabit:
            pass  # The native Lantids rule waives terraforming/Gaia entry, not range.
        elif kind == 'Transdim' and not planet['is_gaia_formed']:
            if state['round'] >= 6:
                continue
            category, delayed = 'gaia', True
            if not reserved:
                level = player['research_tracks']['gaia']
                if not level:
                    continue
                power, formers = facts['gaia_power_cost'][level], 1
                qic *= 2
                ore += modifier.gaia_ore
            else:
                ore += modifier.gaia_ore
        elif kind == 'Gaia' or planet['is_gaia_formed']:
            category = 'gaia'
            ore += modifier.gaia_ore
            if not reserved:
                qic += modifier.gaia_qic
        elif kind == 'Asteroid':
            ore, credits, formers = 0, 0, 1
        elif kind in RING or kind == 'ProtoPlanet':
            steps = 3 if kind == 'ProtoPlanet' else modifier.terraform_steps[kind]
            ore += steps * facts['terraform_ore_per_step'][player['research_tracks']['terraforming']]
        else:
            continue
        options.append(PlanetOpportunity(coord, category, distance, steps, ore, credits,
                                         qic, formers, power, delayed))
    return tuple(options)


def _hex_distance(left: str, right: str) -> int:
    lq, lr = map(int, left.split(','))
    rq, rr = map(int, right.split(','))
    dq, dr = lq-rq, lr-rr
    return max(abs(dq), abs(dr), abs(dq+dr))


def _federation_components(buildings: list[dict]) -> tuple[tuple[frozenset[str], int], ...]:
    powers = {row['coord']: int(row['power']) for row in buildings}
    remaining = set(powers)
    components = []
    while remaining:
        origin = remaining.pop()
        coords = {origin}
        pending = [origin]
        while pending:
            coord = pending.pop()
            adjacent = {other for other in remaining if _hex_distance(coord, other) == 1}
            remaining -= adjacent
            coords.update(adjacent)
            pending.extend(adjacent)
        components.append((frozenset(coords), sum(powers[coord] for coord in coords)))
    return tuple(components)


def _density_bonus(facts: dict, coord: str) -> float:
    """Reward a mine that reduces the remaining power-seven connectivity deficit."""
    federation = facts['federation']
    components = _federation_components(federation['buildings'])
    current_power = max((power for _, power in components), default=0)
    deficit = max(0, DENSITY_TARGET_POWER-current_power)
    if not deficit:
        return 0.0
    adjacent = [component for component in components
                if any(_hex_distance(coord, existing) == 1 for existing in component[0])]
    if adjacent:
        connected, weight = adjacent, DENSITY_ADJACENT_VP
    else:
        distance_two = [component for component in components
                        if any(_hex_distance(coord, existing) == 2 for existing in component[0])]
        if not distance_two:
            return 0.0
        connected, weight = distance_two, DENSITY_DISTANCE_TWO_VP
    mine_power = int(federation['mine_power'][coord])
    resulting_power = mine_power + sum(power for _, power in connected)
    remaining = max(0, DENSITY_TARGET_POWER-max(current_power, resulting_power))
    return (deficit-remaining)*weight


def _select_opportunities(state: dict, player: dict, top_n: int, facts: dict, *,
                          conserve_resources: bool = True,
                          density_bonus: bool = False) -> tuple[PlanetOpportunity, ...]:
    # One shared budget across categories: never promise the same mine/former twice.
    pool = {key: player['resources'][key] for key in ('ore', 'credits', 'qic')}
    pool['formers'] = _free_formers(player)
    pool['power_tokens'] = (sum(player['resources']['power'][key] for key in ('bowl1', 'bowl2', 'bowl3'))
                            if conserve_resources else facts['active_power_tokens'])
    supply = max(0, 8 - sum(s['kind'] == 'Mine' for s in player['structures']))
    selected = []
    if not top_n or (state['round'] == 6 and player['passed']):
        return ()
    # Greedy top-N affordable options, not an optimal multi-colony route search.
    def score(option: PlanetOpportunity) -> float:
        bonus = (_density_bonus(facts, option.coord)
                 if density_bonus and not option.delayed else 0.0)
        return option.value_vp+bonus

    for option in sorted(planet_opportunities(state, player, facts=facts),
                         key=lambda o: (-score(o), o.coord)):
        if len(selected) >= min(top_n, supply):
            break
        if all(getattr(option, key) <= amount for key, amount in pool.items()):
            selected.append(option)
            for key in pool:
                pool[key] -= getattr(option, key)
    return tuple(selected)


def research_progress(state: dict, player: dict, facts: dict) -> float:
    """Best next 3/4/5 threshold; share knowledge rather than spend it on six tracks.

    Read terminal points and immediate reward effects from the native engine.
    Future colony/income payouts are excluded. Progress and budget
    fractions are heuristic, not guaranteed research or a probability of success.
    """
    modifier = faction_modifier(state, player)
    values = []
    curve = facts['final_track_vp']
    thresholds = [level for level in range(1, len(curve)) if curve[level] > curve[level-1]]
    maximum = len(curve)-1
    for track, level in player['research_tracks'].items():
        if level == maximum or (track == 'navigation' and not modifier.navigation_research):
            continue
        target = next(threshold for threshold in thresholds if threshold > level)
        if target == maximum:
            if not player['federation_tokens'] or any(
                p['player_id'] != player['player_id'] and p['research_tracks'][track] == maximum
                for p in state['players']
            ):
                continue
            if track == 'navigation' and not _lost_planet_available(state, player, facts):
                continue
        needed = facts['research_knowledge_cost'] * (target - level)
        affordable = min(1, player['resources']['knowledge'] / needed)
        # TODO(tune): fractional progress gives proximity value without a fixed track bonus.
        reward = facts['research_rewards'][TRACK_IDS[track]][target]
        value = curve[target] - curve[target-1] + _payout_vp(reward)
        values.append(value * (level / target) * affordable)
    return max(values, default=0.0)


def _lost_planet_available(state: dict, player: dict, facts: dict) -> bool:
    board = state['board']
    if board.get('lost_planet') is not None:
        return False
    satellites = sum(cell.get('satellites', []).count(player['player_id'])
                     for cell in board['hexes'].values())
    if satellites >= 25:  # engine.rs SATELLITE_SUPPLY_PER_PLAYER
        return False
    active = set(player['tech_tiles']) - set(player['covered_tech_tiles'])
    reach = facts['navigation_range'][-1] + int(12 in active) + 2 * player['resources']['qic']
    ships = set(board['spaceship_tiles'].values())
    return any(distance <= reach and coord not in ships and not cell['planet']
               and not cell['structures'] and not cell.get('satellites')
               for coord, distance in _distances(state, player).items()
               for cell in [board['hexes'][coord]])


def _payout_vp(reward: dict) -> float:
    return reward.get('vp', 0) + sum(reward.get(key, 0) * price for key, price in PRICES.items())


def federation_values(state: dict, player: dict, modifier: FactionModifiers) -> dict[str, float]:
    """Local star connectivity proxy, not a certificate of native federation legality."""
    data = modifier.federation
    rewards = data['token_rewards']
    best_reward = max((_payout_vp(r) for r in rewards.values()), default=0.0)
    buildings = data['buildings']
    tokens = sum(player['resources']['power'][key] for key in ('bowl1', 'bowl2', 'bowl3'))
    best = 0.0
    for anchor in buildings:
        anchor_player = {**player, 'structures': [{'hex': anchor['coord']}]}
        distances = _distances(state, anchor_player)
        power, links = 0, 0
        for building in sorted(buildings, key=lambda b: distances.get(b['coord'], float('inf'))):
            if building['coord'] not in distances:
                continue
            power += building['power']
            links += max(0, distances[building['coord']] - 1)
            progress = min(1, power / data['minimum_power'])
            affordable = min(1, tokens / max(1, links)) if links else 1
            # TODO(tune): square progress and discount the unverified star-route payoff.
            best = max(best, best_reward * 0.5 * progress ** 2 * affordable)
    # Immediate token payouts are sunk; only unused research/advanced-tech access remains.
    # TODO(tune): one VP per green token, bounded by still unfinished research tracks.
    options = sum(level < 5 for level in player['research_tracks'].values())
    green = min(len(player['federation_tokens']), options)
    return {'federation_readiness': best, 'federation_green_tokens': float(green)}


def expected_events(state: dict, player: dict, options: tuple[PlanetOpportunity, ...],
                    facts: dict, federation_vp: float) -> dict[str, float]:
    """Near-term event counts from current budgets, not committed future actions."""
    own_types = set(facts['colonized_types'])
    own_sectors = {facts['sectors'].get(s['hex']) for s in player['structures']}
    new_types, new_sectors = set(), set()
    now = [o for o in options if not o.delayed]
    for option in now:
        planet = state['board']['hexes'][option.coord]['planet']
        kind = 'Gaia' if planet['is_gaia_formed'] else planet['planet_type']
        if planet['owner'] is None or planet['owner'] == player['player_id']:
            if kind not in own_types:
                new_types.add(kind)
        sector = facts['sectors'].get(option.coord)
        if sector is not None and sector not in own_sectors:
            new_sectors.add(sector)
    upgrades = {}
    for option in facts['upgrades']:
        target = option['target']
        kind = next(iter(target)) if isinstance(target, dict) else target
        count = sum((next(iter(s['kind'])) if isinstance(s['kind'], dict) else s['kind']) == kind
                    for s in player['structures'])
        capacity = {'TradingStation': 4, 'ResearchLab': 3, 'Academy': 2, 'PlanetaryInstitute': 1}[kind]
        if count >= capacity:
            continue
        if kind == 'Academy' and any(s['kind'] == target for s in player['structures']):
            continue
        if option['ore'] <= player['resources']['ore'] and option['credits'] <= player['resources']['credits']:
            upgrades[kind] = 1.0  # One alternative upgrade, never every target on the same stock.
    modifier = faction_modifier(state, player)
    room = sum(level < 5 and (track != 'navigation' or modifier.navigation_research)
               for track, level in player['research_tracks'].items())
    best_reward = max((_payout_vp(r) for r in facts['federation']['token_rewards'].values()), default=0)
    return {
        'BuildMine': float(len(now)), 'TerraformingStep': float(sum(o.terraform_steps for o in now)),
        'BuildMineOnGaia': float(sum(o.category == 'gaia' for o in now)),
        'BuildMineOnNewPlanetType': float(len(new_types)), 'BuildMineInNewSector': float(len(new_sectors)),
        'UpgradeTradingStation': upgrades.get('TradingStation', 0.0),
        'UpgradeResearchLab': upgrades.get('ResearchLab', 0.0),
        'UpgradeLargeBuilding': max(upgrades.get('Academy', 0.0), upgrades.get('PlanetaryInstitute', 0.0)),
        'ResearchAdvance': float(min(room, player['resources']['knowledge'] // facts['research_knowledge_cost'])),
        'FormFederation': min(1, federation_vp / best_reward) if best_reward else 0.0,
    }


def technology_values(state: dict, player: dict, expected: dict, facts: dict, *, remaining_income: bool = False,
                      income_horizon: float | None = None) -> tuple[dict, ...]:
    """Tile-by-tile retained value; immediate rewards are already in native stock/VP.

    Every known tile gets a row, including zero-valued/unowned/covered tiles.
    Passive range/structure-power effects are already in expansion/federation facts.
    """
    active_standard = set(player['tech_tiles']) - set(player['covered_tech_tiles'])
    rows = []
    for tile in facts['tiles']:
        tile_id, advanced = tile['id'], tile['advanced']
        active = tile_id in (player['advanced_tech_tiles'] if advanced else active_standard)
        parts = {'income': 0.0, 'pass': 0.0, 'events': 0.0, 'action': 0.0, 'qic_events': 0.0}
        if (state['round'] < 6 or income_horizon is not None) and not advanced:
            parts['income'] = future_income_value(state, tile['income'],
                remaining_income=remaining_income, active_tokens=facts['active_power_tokens'],
                income_horizon=income_horizon)
            if remaining_income:
                # Marginal contribution against total native income; counted only once.
                alternative = dict(facts['income'])
                for resource, amount in tile['income'].items():
                    alternative[resource] = alternative.get(resource, 0) + (-amount if active else amount)
                current = future_income_value(state, facts['income'], remaining_income=True,
                                              active_tokens=facts['active_power_tokens'], income_horizon=income_horizon)
                other = future_income_value(state, alternative, remaining_income=True,
                                            active_tokens=facts['active_power_tokens'], income_horizon=income_horizon)
                parts['income'] = current-other if active else other-current
        if not player['passed']:
            parts['pass'] = float(tile['pass_vp'] or 0)
            # TODO(tune): probability discount for possible near-term events.
            parts['events'] = 0.5 * sum(expected[e['condition']] * e['vp'] for e in tile['events'])
            used = player['advanced_tech_tile_special_actions_used_this_round'] if advanced else player['tech_tile_special_actions_used_this_round']
            if tile['action'] is not None and tile_id not in used:
                parts['action'] = _payout_vp(tile['action'])
                # TODO(tune): unpriced power option at the common 1/3 VP floor per movable charge.
                power = player['resources']['power']
                movable = 2 * power['bowl1'] + power['bowl2']
                parts['action'] += min(movable, tile['action']['power_charge']) / 3
            # TODO(tune): at most one possible QIC action when a ship is accessible and funded.
            parts['qic_events'] = tile['qic_vp'] * min(1, player['resources']['qic'] / 3) * bool(player['explored_ships'])
        rows.append({'tile': tile_id, 'advanced': advanced, 'active': active,
                     'expected_vp': sum(parts.values()), 'breakdown': parts})
    return tuple(rows)


def round_scoring_value(state: dict, player: dict, expected: dict) -> float:
    if not state['round'] or player['passed']:
        return 0.0
    tile = state['round_tiles'][state['round']-1]
    # TODO(tune): uncertain future triggers, not VP already scored this round.
    return 0.5 * tile['vp_per_unit'] * expected[tile['condition']]


def final_rank_value(facts: dict, actor: int) -> float:
    result = 0
    for tile in facts['final_tiles']:
        values = dict(tile['values'])
        focal = values[actor]
        higher = sum(value > focal for value in values.values())
        tied = sum(value == focal for value in values.values())
        result += sum(tile['awards'][higher:higher+tied]) // tied
    return float(result)


def income_vp(income: dict) -> float:
    # TODO(tune): each charge/token is an option, not cashable terminal VP.
    return _payout_vp(income) + (income.get('power_charge', 0) + income.get('power_tokens', 0)) / 3


def future_income_value(state: dict, income: dict, *, remaining_income: bool = False,
                        active_tokens: int | None = None, income_horizon: float | None = None) -> float:
    if remaining_income:
        phases = income_horizon if income_horizon is not None else max(0, 6-state['round'])
        # No token-count cap: current shortages are priced only by (b).
        effective_charge = income.get('power_charge', 0)
        # Preserve the old income-token coefficient; (b) prices current shortages only.
        value = (_payout_vp(income) + effective_charge*INCOME_CHARGE_VP
                 + income.get('power_tokens', 0)/3)
        return value*phases*(1.0 if income_horizon is not None else REMAINING_INCOME_DISCOUNT)
    return INCOME_DISCOUNT * income_vp(income) if state['round'] < 6 else 0.0


def active_token_count(power: dict) -> int:
    """Structural count, not current charge space; the Brainstone counts once."""
    return sum(power[key] for key in ('bowl1', 'bowl2', 'bowl3')) + int(
        power.get('brainstone') in ('Area1', 'Area2', 'Area3'))


def power_value(power: dict, return_bowl: str | None, *, future: bool = True) -> float:
    # TODO(tune): user-specified Bdoubleprime bowl prices; Brainstone is worth three tokens.
    result = sum(power[key] * weight for key, weight in (('bowl1', 0.0), ('bowl2', 0.6), ('bowl3', 1.2)))
    stone = power.get('brainstone')
    bowls = {'Area1': 0.0, 'Area2': 1.8, 'Area3': 3.6}
    result += bowls.get(stone, 0)
    if stone == 'Gaia' and future:
        # Keep Bprime's Gaia-area valuation unchanged, independently of active bowls.
        gaia_return_values = {'Area1': 1/3, 'Area2': 2/3, 'Area3': 1.0}
        result += GAIA_RETURN_DISCOUNT * gaia_return_values.get(return_bowl, 0)
    return result


def ship_values(state: dict, facts: dict, *, conserve_resources: bool,
                remaining_income: bool = False, income_horizon: float | None = None) -> tuple[dict, ...]:
    rows = []
    for ship in facts['ships']:
        alternatives = []
        for option in ship['options']:
            if (conserve_resources and option['brainstone_after'] == 'Gaia'
                    and option['power_before']['brainstone'] != 'Gaia'):
                continue
            parts = {'resources_vp': _payout_vp(option['payout']),
                     'expansion': COLONY_OPTION_VP * (option['new_colonies'] + PROJECT_DISCOUNT * option['new_gaia_projects']),
                     'power': power_value(option['power_after'], facts['brainstone_return'], future=state['round'] < 6) -
                              power_value(option['power_before'], facts['brainstone_return'], future=state['round'] < 6),
                     'income': future_income_value(state, option['income_after'], remaining_income=remaining_income,
                                   active_tokens=active_token_count(option['power_after']), income_horizon=income_horizon) -
                               future_income_value(state, ship['income_before'], remaining_income=remaining_income,
                                   active_tokens=active_token_count(option['power_before']), income_horizon=income_horizon),
                     'research': sum(facts['final_track_vp'][level] for level in option['research_after'].values()) -
                                 sum(facts['final_track_vp'][level] for level in ship['research_before'].values())}
            alternatives.append({'action': option['action'], 'breakdown': parts, 'value_vp': sum(parts.values())})
        # TODO(tune): competing players may consume a space before our next action.
        benefit = max((o['value_vp'] for o in alternatives), default=0.0)
        entry = (_payout_vp(ship['entry_payout']) +
                 power_value(ship['power_after_entry'], facts['brainstone_return'], future=state['round'] < 6) -
                 power_value(ship['power_before_entry'], facts['brainstone_return'], future=state['round'] < 6)
                 if not ship['owned'] else 0.0)
        rows.append({'ship': ship['ship'], 'owned': ship['owned'], 'entry_net_vp': entry,
                     'options': alternatives, 'expected_vp': max(0.0, 0.5 * (benefit + entry))})
    return tuple(rows)


def secured_planet_coords(state: dict, actor: int) -> frozenset[str]:
    """Built colonies, including native Lost Planet ownership; not reserved projects.

    Coordinates are unique across structures. Empty-space stations and satellites
    have no planet value. Native cohabiting mines occupy a built colony too.
    """
    return frozenset(coord for coord, cell in state['board']['hexes'].items()
                     if cell['planet'] is not None and (
                         any(s['owner'] == actor and s['kind'] != 'Satellite'
                             for s in cell['structures'])
                         or (cell['planet']['planet_type'] == 'LostPlanet'
                             and cell['planet']['owner'] == actor)))


def evaluate_state(state: dict, actor: int, *, top_n: int = TOP_N, conserve_resources: bool = True,
                   secured_planets: bool = False, token_shortfall: bool = False,
                   remaining_income: bool = False, income_horizon: float | None = None,
                   density_bonus: bool = False) -> Evaluation:
    """Evaluate one player's current state; no candidate action is an input."""
    if type(top_n) is not int or top_n < 0:
        raise ValueError('top_n must be a nonnegative integer')
    player = next(p for p in state['players'] if p['player_id'] == actor)
    if player['faction'] not in FACTIONS:
        raise ValueError(f"Unsupported faction: {player['faction']}")

    phase = state['phase']
    if isinstance(phase, dict) and 'Ended' in phase:
        score = float(dict(phase['Ended']['final_scores'])[actor])
        return Evaluation(score, {'native_final_score': score})

    resources = player['resources']
    breakdown = {
        'current_vp': float(player['vp']),
        'bid_penalty_vp': -float(player['setup_bid_vp']),
    }
    for resource in ('ore', 'credits', 'knowledge'):
        breakdown[f'{resource}_stock'] = resources[resource] * PRICES[resource]
    # QIC has no native terminal salvage; its live-game option value is provisional.
    breakdown['qic_stock'] = resources['qic'] * PRICES['qic']

    facts = engine_facts(state, player)
    breakdown['research_final_vp'] = float(sum(facts['final_track_vp'][level]
                                              for level in player['research_tracks'].values()))
    options = _select_opportunities(state, player, top_n, facts,
                                    conserve_resources=conserve_resources,
                                    density_bonus=density_bonus)
    breakdown['expansion_opportunity'] = sum(o.value_vp for o in options if o.category == 'expansion')
    breakdown['gaia_opportunity'] = sum(o.value_vp for o in options if o.category == 'gaia')
    breakdown['density_bonus'] = (sum(_density_bonus(facts, option.coord) for option in options
                                      if not option.delayed) if density_bonus else 0.0)
    breakdown['research_progress'] = research_progress(state, player, facts)
    modifier = faction_modifier(state, player, facts=facts)
    federation = federation_values(state, player, modifier)
    breakdown.update(federation)
    expected = expected_events(state, player, options, facts, federation['federation_readiness'])
    tiles = technology_values(state, player, expected, facts, remaining_income=remaining_income,
                              income_horizon=income_horizon)
    # Tile income is described per tile but counted ONLY in native total income.
    breakdown['technology_tiles'] = sum(row['expected_vp']-row['breakdown']['income']
                                         for row in tiles if row['active'])
    breakdown['future_income'] = future_income_value(state, facts['income'],
        remaining_income=remaining_income, active_tokens=facts['active_power_tokens'], income_horizon=income_horizon)
    breakdown['power_stock'] = power_value(player['resources']['power'], modifier.brainstone_return,
                                           future=state['round'] < 6)
    ships = ship_values(state, facts, conserve_resources=conserve_resources, remaining_income=remaining_income,
                        income_horizon=income_horizon)
    # Alternative ship options share today's stock; do not add every ship payoff.
    breakdown['ships'] = max((row['expected_vp'] for row in ships), default=0.0)
    breakdown['round_scoring'] = round_scoring_value(state, player, expected)
    breakdown['final_scoring_rank'] = final_rank_value(facts, actor)
    breakdown['faction_modifier'] = modifier.vp
    breakdown['secured_planets'] = (len(secured_planet_coords(state, actor)) * SECURED_PLANET_VP[state['round']]
                                     if secured_planets else 0.0)
    breakdown['token_shortfall'] = (-TOKEN_SHORTFALL_VP * max(0, modifier.token_target-facts['active_power_tokens'])
                                   if token_shortfall else 0.0)
    return Evaluation(sum(breakdown.values()), breakdown, options, tiles, ships)
