"""Opt-in source-route pilot. No new actions, learned weights, or fixed faction script."""
from economy.teacher import SHIP_IDS, origins, path_distance, range_qic, construction_cost
from integrated.features import active, remaining, advanced_value, counters, income, resource_value
from integrated.teacher import prospective
from research_context.teacher import ContextResearchTeacher, advance, gaia_opportunity
from strategy_teacher import TRACK_KEYS, kind
from source_routes.planning import (asteroid_opportunity, best_route, available_standard,
                                  rebellion_funding, immediate_funding)


class SourceRouteTeacher(ContextResearchTeacher):
    def rank(self, snapshot):
        self._route_cache = {}
        try:
            scores = super().rank(snapshot)
            # An already funded, useful advanced acquisition carries opportunity
            # cost versus optional conversions; this is a soft ranking hypothesis.
            advanced = [(i, value) for i, (value, _) in enumerate(scores)
                        if self.advanced_net(snapshot['state'], self.context(snapshot)[1],
                                             snapshot['candidates'][i]['action']) >= 8]
            if advanced:
                best = max(value for _, value in advanced)
                for i, candidate in enumerate(snapshot['candidates']):
                    action = candidate['action']
                    if action['type'] == 'FreeAction' and action['kind'] != 'OreToPowerBowl3':
                        # Only a bounded opportunity adjustment, not a prohibition.
                        value, reason = scores[i]
                        scores[i] = (value - min(8, max(0, value-best+1)), reason+'; available advanced opportunity')
            return scores
        finally:
            self._route_cache = None

    def route(self, state, player):
        cache = getattr(self, '_route_cache', None)
        key = repr(player)
        if cache is None:
            return best_route(state, player, self.standard_retained_value)
        if key not in cache:
            cache[key] = best_route(state, player, self.standard_retained_value)
        return cache[key]

    def research(self, state, player, track):
        value = super().research(state, player, track)
        level = player['research_tracks'][TRACK_KEYS[track]]
        if level >= 5:
            return value
        after = advance(player, track)
        if track in ('GaiaProject', 'Navigation'):
            # One newly unlocked former cannot fund both colonies simultaneously.
            before_colonies = max(gaia_opportunity(state, player), asteroid_opportunity(state, player))
            after_colonies = max(gaia_opportunity(state, after), asteroid_opportunity(state, after))
            old_gaia = gaia_opportunity(state, after) - gaia_opportunity(state, player)
            previous_credit = max(0, old_gaia) if track == 'Navigation' else old_gaia
            value += after_colonies - before_colonies - previous_credit
            # Navigation0 ->2 can enable an asteroid, but needs a paid follow-up budget.
            if track == 'Navigation' and level == 0 and player['resources']['knowledge'] + income(player, state)['knowledge'] >= 8:
                value += .55*max(0, asteroid_opportunity(state, advance(player, track, 2))-asteroid_opportunity(state, player))
        # Replace the old disconnected track bonus, not stack another copy on top.
        tile = state['research_board']['advanced_tech_tiles'][list(TRACK_KEYS).index(track)]
        if tile is not None and level < 4 and active(player):
            rivals = max((p['research_tracks'][TRACK_KEYS[track]] for p in state['players']
                          if p['player_id'] != player['player_id']), default=0)
            old = min(12, max(0, advanced_value(state, after, tile)-4)/(4-level))
            value -= old*(1 if player['federation_tokens'] else .3)*(.5 if rivals >= 4 else 1)
        route = self.route(state, player)
        if route and route.track == track and level < 4:
            value += min(14, route.utility)/(max(1, 4-level))
        return value

    def ship_value(self, state, player, ship, starts):
        # Old teacher's Eclipse forecast encoded the now-corrected former requirement.
        if ship == 'Eclipse':
            board = next(b for b in state['spaceship_boards'] if b['id'] == ship)
            if (3 in player['explored_ships'] or all(p is not None for p in board['explorers'])
                    or not player['exploration_shuttles_available'] or player['vp'] < 5):
                return 0.0
            coord = state['board']['spaceship_tiles'][ship]
            distance = path_distance(state, starts, coord)
            qic = range_qic(state, player, coord, starts=starts)
            if distance > 5 or qic > player['resources']['qic']:
                return 0.0
            targets = any(h['planet'] and h['planet']['planet_type'] == 'Asteroid'
                          and h['planet']['owner'] is None
                          and range_qic(state, player, c, starts=starts) <= player['resources']['qic']-qic
                          for c, h in state['board']['hexes'].items())
            value = 8*targets*min(1, player['resources']['credits']/6)
            return value/(1+.4*max(0, distance-1)+.5*qic)
        value = super().ship_value(state, player, ship, starts)
        # Printed tech-token cargo is more valuable when it addresses a real tile gap.
        board = next(b for b in state['spaceship_boards'] if b['id'] == ship)
        if value > 0 and board['federation_token'] == 12 and available_standard(state, player):
            value += 3
        return value

    def technology(self, state, player, choice):
        value = super().technology(state, player, choice)
        if not choice or choice['kind'] != 'Standard':
            return value
        candidate = getattr(self, '_candidate', None)
        p = prospective(player, candidate)
        # Rewards arrive AFTER paying the upgrade/3QIC cost.
        cost = construction_cost(state, player, candidate) if candidate else None
        if cost:
            for key in ('ore', 'credits', 'qic'):
                p['resources'][key] = max(0, p['resources'][key]-getattr(cost, key))
        if candidate and candidate['type'] == 'RebellionGainTechTile':
            p['resources']['qic'] = max(0, p['resources']['qic']-3)
        tile = choice['tile']
        reward = {4: {'ore': 1, 'qic': 1}, 9: {'knowledge': counters(state, p)['types']},
                  13: {'ore': 1, 'knowledge': 3}}.get(tile)
        if reward:
            value += immediate_funding(state, p, reward)
        return value

    def advanced_net(self, state, player, action):
        choice = action.get('tech_tile_choice')
        if not choice or choice['kind'] not in ('Advanced', 'LostFleetAdvanced'):
            return 0.0
        tile = (state['research_board']['lost_fleet_advanced_tech_tile'] if choice['kind'] == 'LostFleetAdvanced'
                else state['research_board']['advanced_tech_tiles'][list(TRACK_KEYS).index(choice['track'])])
        if tile is None:
            return 0.0
        p = prospective(player, action)
        return advanced_value(state, p, tile)-self.standard_retained_value(state, p, choice['covered_tile'])-4

    def score(self, snapshot, action):
        value, reason = super().score(snapshot, action)
        state, player, resources = self.context(snapshot)
        adjustment = 0.0
        t = action['type']
        if t in ('Upgrade', 'TwilightFreeResearchLab'):
            route = self.route(state, player)
            target = kind(action['to']) if t == 'Upgrade' else 'ResearchLab'
            if route and route.first_coord == action['coord'] and route.first_kind == target:
                adjustment += min(10, route.utility)
            if t == 'Upgrade' and action['to'] == {'Academy': 'Qic'} and rebellion_funding(state, player):
                adjustment += 10
            # Actual advanced net, rather than a constant "get any advanced" bonus.
            adjustment += min(12, max(0, self.advanced_net(state, player, action))*.5)
        if t in ('ExploreSpaceship', 'RoundBoosterRangeExploreSpaceship', 'TwilightRangeExploreSpaceship'):
            adjustment += self.ship_value(state, player, action['ship'], origins(state, player))
        if t == 'FormFederation':
            route = self.route(state, player)
            if route and route.federation_needed:
                adjustment += min(10, route.utility)
        if t == 'TFMarsTechBonus':
            value = 48 + 2*(2+len(player['tech_tiles'])) - resource_value(player, {'qic': 2})
        elif t == 'EclipsePlanetTypeBonus':
            value = 48 + 2*(2+counters(state, player)['types']) - resource_value(player, {'qic': 2})
        elif t == 'RebellionCreditsAndQic':
            adjustment += 8 if rebellion_funding(state, player) else -8
        if action.get('bonus_tech_tile') is not None:
            choice = {'kind': 'Standard', 'tile': action['bonus_tech_tile'],
                      'advance_track': action.get('bonus_research_track')}
            adjustment += self.technology(state, player, choice)
        return value+adjustment, reason+f'; source-route adjustment={adjustment:.2f}'
