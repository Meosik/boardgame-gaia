"""Isolated soft three-federation hypothesis, scoped to Xenos/Hadsch Hallas.

No reward changes, bans, or fabricated actions. Geometry is a cheap planning proxy;
only the native candidate enumerator determines legal federation routes and costs.
"""
from economy.teacher import EconomyTeacher, BUILD_TYPES, path_distance
from strategy_teacher import distance, kind


def power(player, building):
    name = kind(building)
    value = {'Mine': 1, 'TradingStation': 2, 'ResearchLab': 2,
             'PlanetaryInstitute': 3, 'Academy': 3}.get(name, 0)
    active = set(player['tech_tiles']) - set(player['covered_tech_tiles'])
    return value + int(name in ('PlanetaryInstitute', 'Academy') and 6 in active)


def minimum(player):
    return 6 if player['faction'] == 'Xenos' and any(kind(s['kind']) == 'PlanetaryInstitute' for s in player['structures']) else 7


def formations(player):
    # In these two factions the only non-formation token is Terraforming level 5.
    return max(0, len(player['federation_tokens']) + len(player['gray_federation_tokens'])
               - int(player['research_tracks']['terraforming'] == 5))


def goal_weight(state, player):
    if any(t['condition'] == 'MostSatellites' for t in state['final_scoring_tiles']):
        return .35
    return 1.0 if formations(player) < 3 else .35


def preparation(state, player, coord, old, new):
    delta = power(player, new) - power(player, old)
    if delta <= 0:
        return 0.0  # Trading station -> lab has no federation-specific penalty.
    weight = goal_weight(state, player)
    used = set(player['federated_hexes'])
    absorbed = coord in used or (old is None and any(distance(coord, c) == 1 for c in used))
    if absorbed:
        return -8 * delta * weight
    own = [s for s in player['structures'] if s['hex'] not in used and s['hex'] != coord]
    nearby = [s for s in own if path_distance(state, [coord], s['hex']) <= 3]
    nearby_power = sum(power(player, s['kind']) for s in nearby)
    need = minimum(player)
    before = nearby_power + power(player, old)
    # Still a local neighborhood proxy, not a claim that these buildings form legally.
    proximity = min(1, nearby_power / max(1, need - power(player, new)))
    finish = 12 if before < need <= before + delta else 0
    return weight * (delta * (5 + 7 * proximity) + finish)


class FederationTeacher(EconomyTeacher):
    def rank(self, snapshot):
        self._preparation = {}
        try:
            return super().rank(snapshot)
        finally:
            self._preparation = None

    def adjustment(self, state, player, action):
        t = action['type']
        coord = action.get('coord')
        if t == 'FormFederation':
            satellites = len(action['satellite_hexes'])
            tokens = sum(player['resources']['power'][k] for k in ('bowl1', 'bowl2', 'bowl3'))
            committed = sum(power(player, s['kind']) for s in player['structures'] if s['hex'] in action['hexes'])
            # Baseline already charges 2 points/satellite. Add route/reserve awareness.
            reserve = 5 * max(0, 4 - (tokens - satellites)) if state['round'] < 6 else 0
            return 12 * goal_weight(state, player) - 3 * satellites - reserve - 2 * max(0, committed - minimum(player))
        old = next((s['kind'] for s in player['structures'] if s['hex'] == coord), None)
        if t == 'Upgrade':
            new = action['to']
        elif t in ('RebellionFreeTradingStation', 'TwilightFreeResearchLab'):
            new = 'TradingStation' if t == 'RebellionFreeTradingStation' else 'ResearchLab'
        elif t in BUILD_TYPES or t == 'PlaceStartingStructure' or (t == 'PowerAction' and coord):
            new = 'Mine'
        else:
            return 0.0
        key = (coord, kind(old), kind(new))
        cache = getattr(self, '_preparation', None)
        if cache is not None and key in cache:
            value = cache[key]
        else:
            value = preparation(state, player, coord, old, new)
            if cache is not None:
                cache[key] = value
        return value * (.5 if t == 'PlaceStartingStructure' else 1)

    def score(self, snapshot, action):
        base, reason = super().score(snapshot, action)
        state, player, _ = self.context(snapshot)
        adjustment = self.adjustment(state, player, action)
        return base + adjustment, f'{reason}; federation_preparation={adjustment:.2f}'
