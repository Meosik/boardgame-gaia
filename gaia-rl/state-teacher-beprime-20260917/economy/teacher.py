"""Opt-in economic teacher; retains the original pilot and does not alter rewards.

Scoped cost estimates mirror current engine rules for Xenos/Hadsch Hallas only.
Ranking coefficients are experimental hypotheses, not prohibitions or learned values.
"""
from collections import deque
from dataclasses import dataclass
from functools import lru_cache

from strategy_teacher import StrategyTeacher, distance, kind
from scoring_cache import memoized, reuse

RING = ('Terra', 'Oxide', 'Volcanic', 'Desert', 'Swamp', 'Titanium', 'Ice')
HOME = {'Xenos': 'Desert', 'HadschHallas': 'Oxide'}
ORE_PER_STEP = (3, 3, 2, 1, 1, 1)
NAV_RANGE = (1, 1, 2, 2, 3, 4)
SHIP_IDS = {'Twilight': 0, 'Rebellion': 1, 'TFMars': 2, 'Eclipse': 3}
BUILD_TYPES = {'Build', 'RoundBoosterRangeBuild', 'TwilightRangeBuild',
               'SpaceshipCreditTerraform', 'EclipseAsteroidMine'}


@lru_cache(maxsize=2048)
def paths(cells, start):
    """Engine range uses board-only BFS; straight hex distance can cross missing cells."""
    result = {start: 0}
    queue = deque([start])
    while queue:
        coord = queue.popleft()
        q, r = map(int, coord.split(','))
        for dq, dr in ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)):
            neighbor = f'{q+dq},{r+dr}'
            if neighbor in cells and neighbor not in result:
                result[neighbor] = result[coord] + 1
                queue.append(neighbor)
    return result


@memoized('origins', lambda player: player['player_id'])
def origins(state, player):
    return [coord for coord, cell in state['board']['hexes'].items()
            if any(s['owner'] == player['player_id'] for s in cell['structures'])
            or (cell['planet'] and cell['planet']['owner'] == player['player_id']
                and cell['planet']['planet_type'] == 'LostPlanet')]


def path_distance(state, starts, target):
    starts = tuple(starts)
    cells = reuse(state, 'board-cells', (), lambda: frozenset(state['board']['hexes']))
    return reuse(state, 'path-distance', (starts, target),
                 lambda: min((paths(cells, start).get(target, 999) for start in starts), default=999))


def navigation(player, bonus=0):
    active = set(player['tech_tiles']) - set(player['covered_tech_tiles'])
    return NAV_RANGE[player['research_tracks']['navigation']] + bonus + (12 in active)


def range_qic(state, player, target, bonus=0, starts=None):
    dist = path_distance(state, origins(state, player) if starts is None else starts, target)
    return max(0, (dist - navigation(player, bonus) + 1) // 2)


def steps_for(player, planet):
    if planet['is_gaia_formed'] or planet['planet_type'] in ('Gaia', 'Asteroid', 'LostPlanet'):
        return 0
    if planet['planet_type'] == 'ProtoPlanet':
        return 3
    if planet['planet_type'] not in RING:
        return None
    gap = abs(RING.index(HOME[player['faction']]) - RING.index(planet['planet_type']))
    return min(gap, 7-gap)


def neighbors(state, player, coord):
    return [(c, s) for c, h in state['board']['hexes'].items() if distance(c, coord) <= 2
            for s in h['structures'] if s['owner'] != player['player_id']]


@dataclass(frozen=True)
class Cost:
    ore: int = 0
    credits: int = 0
    qic: int = 0
    power: int = 0
    terraform_steps: int = 0
    terraform_ore: int = 0


def _cost_key(player, action):
    # Board/ownership are fixed by the scope; these are all prospective-player
    # inputs used by construction_cost, steps_for, navigation and range_qic.
    tracks = player.get('research_tracks', {})
    return (player.get('faction'), player.get('player_id'), tracks.get('terraforming'),
            tracks.get('navigation'), repr(player.get('tech_tiles')),
            repr(player.get('covered_tech_tiles')), repr(action))


@memoized('construction-cost', _cost_key)
def construction_cost(state, player, action):
    """None means outside this estimator's scope, not a free action."""
    if player['faction'] not in HOME:
        raise ValueError('Economic cost estimator is scoped to Xenos/Hadsch Hallas')
    t = action['type']
    if t == 'Upgrade':
        target = kind(action['to'])
        if target == 'TradingStation':
            return Cost(ore=2, credits=3 if neighbors(state, player, action['coord']) else 6)
        ore, credits = {'ResearchLab': (3, 5), 'PlanetaryInstitute': (4, 6), 'Academy': (6, 6)}[target]
        return Cost(ore=ore, credits=credits)
    if t == 'RebellionFreeTradingStation':
        return Cost(ore=1, power=3)
    if t == 'TwilightFreeResearchLab':
        return Cost(ore=2, power=3)
    if t not in BUILD_TYPES and not (t == 'PowerAction' and action.get('coord')):
        return None
    coord = action['coord']
    planet = state['board']['hexes'][coord]['planet']
    steps = steps_for(player, planet)
    if steps is None:
        return None
    free = 1 if t == 'SpaceshipCreditTerraform' else 0
    power = 0
    if t == 'PowerAction':
        free, power = {2: (2, 5), 6: (1, 3)}[action['id']]
    bonus = 3 if t in ('RoundBoosterRangeBuild', 'TwilightRangeBuild') else 0
    qic = range_qic(state, player, coord, bonus)
    formed_own = (planet['is_gaia_formed'] and planet['planet_type'] == 'Transdim'
                  and planet['owner'] == player['player_id'])
    # Mirror the pinned engine, including its current raw-Gaia/formed-Gaia distinction.
    # Raw Gaia with is_gaia_formed=False currently pays no entry QIC (reported separately).
    if planet['is_gaia_formed'] and not formed_own:
        qic += 1
    if planet['planet_type'] == 'Asteroid' and not planet['is_gaia_formed']:
        activation = {'SpaceshipCreditTerraform': 3, 'EclipseAsteroidMine': 6}.get(t, 0)
        return Cost(qic=qic, power=power, credits=activation)
    paid_steps = max(0, steps-free)
    terra_ore = paid_steps * ORE_PER_STEP[player['research_tracks']['terraforming']]
    return Cost(ore=1+terra_ore, credits=5 if t == 'SpaceshipCreditTerraform' else 2,
                qic=qic, power=power, terraform_steps=paid_steps, terraform_ore=terra_ore)


class EconomyTeacher(StrategyTeacher):
    def rank(self, snapshot):
        # Many technology choices share a construction coordinate in one decision.
        self._locations = {}
        try:
            return super().rank(snapshot)
        finally:
            self._locations = None

    def charge_potential(self, state, player, coord):
        """Discount opportunity and possible future charging, not guaranteed income."""
        nearby = neighbors(state, player, coord)
        if not nearby:
            return 0.0
        by_owner = {}
        for _, structure in nearby:
            potential = {'Mine': 1.0, 'TradingStation': .8, 'ResearchLab': .5}.get(kind(structure['kind']), .2)
            by_owner[structure['owner']] = max(by_owner.get(structure['owner'], 0), potential)
        power = player['resources']['power']
        circulating = sum(power[k] for k in ('bowl1', 'bowl2', 'bowl3'))
        horizon = max(0, 6-max(1, state['round'])) / 5
        return 2*horizon + 5*horizon*min(1, circulating/4)*sum(by_owner.values())

    def opportunity(self, state, player, starts, target):
        planet = state['board']['hexes'][target]['planet']
        if not planet or planet['owner'] is not None or target in starts:
            return 0.0
        steps = steps_for(player, planet)
        if steps not in (0, 1) or planet['planet_type'] not in RING:
            return 0.0
        dist = path_distance(state, starts, target)
        if not 1 <= dist <= 3:
            return 0.0
        qic = range_qic(state, player, target, starts=starts)
        if qic > player['resources']['qic']:
            return 0.0
        ore = 1 + steps*ORE_PER_STEP[player['research_tracks']['terraforming']]
        return (6 if steps == 0 else 4) / (1 + .3*(dist-1) + .2*(ore-1) + .4*qic)

    def ship_value(self, state, player, ship, starts):
        coord = state['board']['spaceship_tiles'][ship]
        board = next(b for b in state['spaceship_boards'] if b['id'] == ship)
        if SHIP_IDS[ship] in player['explored_ships'] or all(p is not None for p in board['explorers']):
            return 0.0
        dist = path_distance(state, starts, coord)
        if dist > 5 or player['exploration_shuttles_available'] == 0 or player['vp'] < 5:
            return 0.0
        qic_cost = range_qic(state, player, coord, starts=starts)
        resources = player['resources']
        if qic_cost > resources['qic']:
            return 0.0
        qic = resources['qic']-qic_cost
        # LF04: source-informed suitability, conditional on an actual resource/target path.
        if ship == 'Rebellion':
            available = set(state['research_board']['tech_tiles'] + board['tech_tiles']) - set(player['tech_tiles'])
            useful = bool(available) and any(v < 4 for v in player['research_tracks'].values())
            value = (9 if player['faction'] == 'Xenos' else 6) * useful * (1 if qic >= 3 else .4)
        elif ship == 'TFMars':
            one_step = any(self.opportunity(state, player, starts, c) > 0
                           and steps_for(player, h['planet']) == 1 for c, h in state['board']['hexes'].items() if h['planet'])
            value = (9 if player['faction'] == 'HadschHallas' else 6) * one_step * min(1, resources['credits']/5, resources['ore'])
        elif ship == 'Eclipse':
            former = player['gaiaformers_total'] > player['gaiaformers_deployed'] + player['gaiaformers_in_gaia_area'] + resources.get('spent_gaia_formers', 0)
            asteroid = any(h['planet'] and h['planet']['planet_type'] == 'Asteroid' and h['planet']['owner'] is None
                           and path_distance(state, starts, c) <= 3 for c, h in state['board']['hexes'].items())
            value = (8 if player['faction'] == 'HadschHallas' else 5) * former * asteroid * min(1, resources['credits']/6)
        else:
            power = resources['power']
            tokens = sum(power[k] for k in ('bowl1', 'bowl2', 'bowl3'))
            value = 5*min(1, max(0, tokens-5)/4)
        return value / (1 + .4*max(0, dist-1) + .5*qic_cost)

    def location(self, state, player, coord):
        cache = getattr(self, '_locations', None)
        if cache is not None and coord in cache:
            return cache[coord]
        value = self._location(state, player, coord)
        if cache is not None:
            cache[coord] = value
        return value

    def _location(self, state, player, coord):
        starts = origins(state, player)
        # Marginal opportunities: a third starting mine should not recount the same cluster.
        expansion = sum(max(0, self.opportunity(state, player, starts+[coord], c)
                               - self.opportunity(state, player, starts, c))
                        for c in state['board']['hexes'])
        fleet = max((max(0, self.ship_value(state, player, ship, starts+[coord])
                             - self.ship_value(state, player, ship, starts))
                     for ship in state['board']['spaceship_tiles']), default=0)
        return min(18, expansion) + self.charge_potential(state, player, coord) + fleet

    def score(self, snapshot, action):
        base, reason = super().score(snapshot, action)
        state, player, resources = self.context(snapshot)
        cost = construction_cost(state, player, action)
        if cost is None:
            return base, reason
        # Prices reflect scarcity, not a blanket ban: strong technology/round benefits remain.
        credit_price = 1.2 if resources['credits'] >= 12 else 1.8
        ore_price = 2.5 if resources['ore'] >= 5 else 3.5
        penalty = cost.credits*credit_price + cost.ore*ore_price + cost.qic*4 + cost.power
        if action['type'] in ('Upgrade', 'RebellionFreeTradingStation', 'TwilightFreeResearchLab'):
            base += self.charge_potential(state, player, action['coord'])
        return base-penalty, f'{reason}; cost={cost}; penalty={penalty:.2f}'
