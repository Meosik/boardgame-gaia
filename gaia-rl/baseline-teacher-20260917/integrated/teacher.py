"""Source-informed integration candidate. Opt-in, two factions, no engine/reward edits."""
import copy
from integrated.boosters import evaluate_booster
from economy.teacher import EconomyTeacher, BUILD_TYPES, construction_cost, path_distance, origins
from federation.teacher import FederationTeacher, preparation, power, minimum
from strategy_teacher import TRACK_KEYS, kind
from integrated.features import (TRACKS, active, remaining, income, counters, advanced_value,
                                  resource_value, knowledge_budget_value)


def prospective(player, action):
    result = copy.deepcopy(player)
    if action and action['type'] in ('Upgrade', 'TwilightFreeResearchLab', 'RebellionFreeTradingStation'):
        target = action.get('to') or ('ResearchLab' if action['type']=='TwilightFreeResearchLab' else 'TradingStation')
        for s in result['structures']:
            if s['hex'] == action['coord']:
                s['kind'] = target
    return result


def reserve_adjustment(state, player, action):
    """Ordinary bowlIII spending cycles tokens; only discards/Gaia reduce circulation."""
    t = action['type']
    total = sum(player['resources']['power'][k] for k in ('bowl1', 'bowl2', 'bowl3'))
    discard = 0
    returned = 0
    if t == 'FormFederation':
        discard = len(action['satellite_hexes'])
        token = action.get('token', {})
        token_id = token.get('kind')
        if 'ship' in token:
            token_id = next((b['federation_token'] for b in state['spaceship_boards'] if b['id']==token['ship']), None)
        returned = 2 if token_id==13 else 0
    elif t == 'ExamineArtifact':
        discard = 6
    elif t == 'FreeAction' and action['kind']=='BurnPower':
        discard = action.get('count', 1)
    elif t in ('GaiaFormation', 'RoundBoosterRangeGaiaFormation', 'TwilightRangeGaiaFormation'):
        discard = (255, 6, 6, 4, 3, 3)[player['research_tracks']['gaia']]
    if not discard or not remaining(state):
        return 0.0
    target = 6 if remaining(state) >= 3 else 4
    before = max(0, target-total)
    after = max(0, target-(total-discard+returned))
    # Extra scarcity below4; soft preference, never invalidates an otherwise legal move.
    critical = max(0, 4-(total-discard+returned)) - max(0, 4-total)
    return -3*(after-before)-5*critical


class IntegratedTeacher(FederationTeacher):
    def rank(self, snapshot):
        self._snapshot = snapshot
        self._research_cache = {}
        try:
            return super().rank(snapshot)
        finally:
            self._snapshot = None
            self._research_cache = None

    def construction_options(self, state, player):
        options = {}
        starts = origins(state, player)
        if not starts or sum(s['kind']=='Mine' for s in player['structures'])>=8:
            return options
        for coord, cell in state['board']['hexes'].items():
            planet = cell['planet']
            if not planet or planet['owner'] is not None or planet['planet_type'] not in ('Terra','Oxide','Volcanic','Desert','Swamp','Titanium','Ice'):
                continue
            cost = construction_cost(state, player, {'type': 'Build', 'coord': coord})
            if cost and cost.qic <= player['resources']['qic']:
                options[coord] = cost
        return options

    def research(self, state, player, track):
        level = player['research_tracks'][TRACK_KEYS[track]]
        if level >= 5:
            return 0.0
        # Key includes actor state: technology choices may cover income/alter buildings.
        cache = getattr(self, '_research_cache', None)
        key = (track, repr(player))
        if cache is not None and key in cache:
            return cache[key]
        after = copy.deepcopy(player)
        after['research_tracks'][TRACK_KEYS[track]] += 1
        reward = TRACKS[track][level+1]
        horizon = remaining(state)
        score = 4 * int(level >= 2) + 2 * int(level == 2)
        if track in ('Economy', 'Science'):
            before_income, after_income = income(player,state), income(after,state)
            delta = {k: after_income[k]-before_income[k] for k in before_income}
            score += resource_value(player, delta)*horizon*.7
            if track == 'Science':
                stock = player['resources']['knowledge']
                score += knowledge_budget_value(stock, after_income['knowledge'], horizon) - knowledge_budget_value(stock, before_income['knowledge'], horizon)
            if level+1 == 5:
                score += resource_value(player, {k: reward.get(k, 0) for k in ('ore','credits','knowledge','qic')})
        else:
            score += resource_value(player, {k: reward.get(k, 0) for k in ('ore','credits','knowledge','qic')})
        score += reward.get('vp', 0)
        if reward.get('vp_per_gaia_planet', 0):
            occupied = {s['hex'] for s in player['structures']}
            gaia_count = sum(bool(cell['planet'] and (cell['planet']['owner']==player['player_id'] or coord in occupied)
                                  and (cell['planet']['is_gaia_formed'] or cell['planet']['planet_type']=='Gaia'))
                             for coord, cell in state['board']['hexes'].items())
            score += reward['vp_per_gaia_planet']*gaia_count
        if reward.get('federation_token'):
            token = state['research_board']['terraforming_level_5_token']
            # Setup reserves a base token (1..6); evaluate its printed reward.
            vp, resources = {1:(12,{}), 2:(8,{'qic':1}), 3:(8,{}),
                             4:(7,{'ore':2}), 5:(7,{'credits':6}),
                             6:(6,{'knowledge':2})}.get(token,(0,{}))
            score += vp + resource_value(player,resources)
            if token == 3 and horizon:
                score += 4  # Two new circulating tokens, not two power charges.
        if reward.get('lost_planet_access') and state['board']['lost_planet'] is None:
            score += 6  # Free colony proxy; exact placement/final-ranking value deferred.
        if track in ('Terraforming', 'Navigation'):
            before_options = self.construction_options(state, player)
            after_options = self.construction_options(state, after)
            gains = []
            for coord, cost in after_options.items():
                # Count only near-term funded targets; never claim all hypothetical planets.
                if cost.ore > player['resources']['ore']+income(player,state)['ore'] or cost.credits > player['resources']['credits']+income(player,state)['credits']:
                    continue
                old = before_options.get(coord)
                gain = 6 if old is None else (old.ore-cost.ore)*3 + (old.qic-cost.qic)*4
                if gain > 0:
                    gains.append(gain)
            score += sum(sorted(gains, reverse=True)[:2])
        if track == 'GaiaProject' and level == 0 and horizon:
            nearby = any(h['planet'] and h['planet']['planet_type']=='Transdim'
                         and h['planet']['owner'] is None and path_distance(state, origins(state, player), c) <= 2
                         for c,h in state['board']['hexes'].items())
            score += 5*nearby
        # Explicitly plan toward the ACTUAL advanced tile, but do not claim it is acquired.
        tile = state['research_board']['advanced_tech_tiles'][list(TRACK_KEYS).index(track)]
        if tile is not None and level < 4 and active(player):
            value = max(0, advanced_value(state, after, tile)-4)
            tokens = bool(player['federation_tokens'])
            rivals = max((p['research_tracks'][TRACK_KEYS[track]] for p in state['players'] if p['player_id']!=player['player_id']), default=0)
            distance_to_four = 4-level
            score += min(12, value/distance_to_four) * (1 if tokens else .3) * (.5 if rivals >= 4 else 1)
        if cache is not None:
            cache[key] = score
        return score

    def standard_retained_value(self, state, player, tile):
        horizon = remaining(state)
        if tile in (2, 3, 5):
            resources = {2: {'ore': 1}, 3: {'credits': 4}, 5: {'knowledge': 1, 'credits': 1}}[tile]
            return resource_value(player, resources)*horizon*.7
        if tile == 6:
            return 3*counters(state, player)['large']
        if tile == 8:
            return 2*min(3, horizon)*bool(player['research_tracks']['gaia'])
        if tile == 10:
            return (1+.6*horizon)*min(4, 2*player['resources']['power']['bowl1']+player['resources']['power']['bowl2'])
        if tile == 12:
            return 3 if horizon else 0
        return 0.0  # Immediate rewards are sunk, not lost when covered.

    def technology(self, state, player, choice):
        if not choice:
            return 0.0
        player = prospective(player, getattr(self, '_candidate', None))
        horizon = remaining(state)
        track = choice.get('advance_track')
        if choice['kind']=='Standard':
            tile = choice['tile']
            value = self.standard_retained_value(state, player, tile)
            immediate = {4: {'ore': 1, 'qic': 1}, 9: {'knowledge': counters(state, player)['types']},
                         13: {'ore': 1, 'knowledge': 3}}
            if tile in immediate:
                value += resource_value(player, immediate[tile])
            if tile == 7:
                value += 7
            if tile == 11:
                value += 10  # Validated bonus mine; detailed future colony value is deferred.
            if tile == 5:
                k = income(player,state)['knowledge']
                value += knowledge_budget_value(player['resources']['knowledge'], k+1, horizon)-knowledge_budget_value(player['resources']['knowledge'], k, horizon)
            player['tech_tiles'].append(tile)
            if not track:
                slots = state['research_board']['tech_tile_slots']
                if tile in slots and slots.index(tile) < 6:
                    track = list(TRACK_KEYS)[slots.index(tile)]
        else:
            tile = (state['research_board']['lost_fleet_advanced_tech_tile'] if choice['kind']=='LostFleetAdvanced'
                    else state['research_board']['advanced_tech_tiles'][list(TRACK_KEYS).index(choice['track'])])
            if tile is None:
                return -100.0
            covered = choice['covered_tile']
            value = advanced_value(state, player, tile)-self.standard_retained_value(state, player, covered)
            # Green tokens also enable level5 and other advanced tiles; not all equally spare.
            value -= 4 if len(player['federation_tokens']) <= 1 else 2
            before_income = income(player,state)['knowledge']
            player['covered_tech_tiles'].append(covered)
            after_income = income(player,state)['knowledge']
            value += knowledge_budget_value(player['resources']['knowledge'], after_income, horizon)-knowledge_budget_value(player['resources']['knowledge'], before_income, horizon)
        return value + (self.research(state, player, track) if track else 0)

    def waiting_value(self, state, player, action):
        """Compare with one affordable upgrade and a compact power proxy, not a solved route."""
        if state['round'] >= 6 or len(action['satellite_hexes']) <= 2:
            return 0.0
        best = 0.0
        recurring = income(player,state)
        owned = [s for s in player['structures'] if s['hex'] not in player['federated_hexes']]
        for s in owned:
            targets = {'Mine': ['TradingStation'], 'ResearchLab': [{'Academy': 'Science'}, {'Academy': 'Qic'}],
                       'TradingStation': ['PlanetaryInstitute']}.get(kind(s['kind']), [])
            for to in targets:
                if any(b['kind']==to for b in player['structures']) and kind(to) in ('Academy','PlanetaryInstitute'):
                    continue
                if to=='TradingStation' and sum(b['kind']=='TradingStation' for b in player['structures'])>=4:
                    continue
                cost = construction_cost(state, player, {'type': 'Upgrade', 'coord': s['hex'], 'to': to})
                if cost.ore > player['resources']['ore']+recurring['ore'] or cost.credits > player['resources']['credits']+recurring['credits']:
                    continue
                upgraded = prospective(player, {'type':'Upgrade','coord':s['hex'],'to':to})
                needed = minimum(upgraded)-power(player,to)
                nearby = sorted((path_distance(state, [s['hex']], other['hex']), power(player,other['kind'])) for other in owned if other!=s)
                # Star-route estimate overcounts shared links; cannot certify route legality.
                route = 0
                for d,p in nearby:
                    if needed <= 0:
                        break
                    needed -= p
                    route += max(0,d-1)
                if needed <= 0 and route < len(action['satellite_hexes']):
                    saving = len(action['satellite_hexes'])-route
                    investment = resource_value(player, {'ore':cost.ore,'credits':cost.credits})*.25
                    best = max(best, 3*saving-investment)
        for coord, cost in self.construction_options(state, player).items():
            if any(path_distance(state,[coord],c)==1 for c in player['federated_hexes']):
                continue
            if cost.ore>player['resources']['ore']+recurring['ore'] or cost.credits>player['resources']['credits']+recurring['credits']:
                continue
            needed=minimum(player)-1
            route=0
            for d,p in sorted((path_distance(state,[coord],s['hex']),power(player,s['kind'])) for s in owned):
                if needed<=0:break
                needed-=p;route+=max(0,d-1)
            if needed<=0:
                saving=len(action['satellite_hexes'])-route
                best=max(best,3*saving-resource_value(player,{'ore':cost.ore,'credits':cost.credits,'qic':cost.qic})*.25)
        # Scarce last token / current federation scoring argues against waiting.
        token = action['token']
        scarce = 'kind' in token and state['research_board']['federation_tokens'].count(token['kind']) <= 1
        scoring = self.round_bonus(state,'FormFederation')
        return max(0, min(16,best)-4*scarce-scoring)

    def score(self, snapshot, action):
        if action['type'] in ('Pass','SelectStartingBooster'):
            state,player,_ = self.context(snapshot)
            starting = action['type']=='SelectStartingBooster'
            value = evaluate_booster(state,player,action.get('booster_id'),starting=starting)
            # Preserve pass as a fallback, rather than cashing in forecast points now.
            score = value.total if starting else 3*value.total/(1+value.total)
            return score, f'booster: next-round components={value}; total={value.total:.3f}'
        self._candidate = action
        try:
            # Reuse economic cost/neighbor scoring, not all of the unpromoted federation pilot.
            base, reason = EconomyTeacher.score(self, snapshot, action)
        finally:
            self._candidate = None
        state, player, resources = self.context(snapshot)
        t = action['type']
        adjustment = reserve_adjustment(state, player, action)
        if t == 'FormFederation':
            adjustment += 8 - 2*len(action['satellite_hexes']) - self.waiting_value(state,player,action)
        elif t in ('Upgrade', 'RebellionFreeTradingStation', 'TwilightFreeResearchLab') or t in BUILD_TYPES or t=='PlaceStartingStructure' or (t=='PowerAction' and action.get('coord')):
            # Half-strength preparation after the previous HH regression; not a promoted model.
            adjustment += .5*self.adjustment(state,player,action)
            if t=='Upgrade' and kind(action['to'])=='Academy':
                after = prospective(player,action)
                delta = income(after,state)['knowledge']-income(player,state)['knowledge']
                adjustment += delta*remaining(state)*2
                if action['to']=={'Academy':'Qic'}:
                    adjustment += 5 if state['round']>=5 else 1
        if t=='ChargePower':
            queue = state['phase'].get('ChargePowerPending',{}).get('queue',[]) if isinstance(state['phase'],dict) else []
            entry = next((q for q in queue if q['player']==player['player_id']),None)
            if entry:
                p=resources['power']
                charge=min(entry['max_power'],2*p['bowl1']+p['bowl2'],max(0,player['vp'])+1)
                cost=max(0,charge-1)
                value=charge*(1.1 if state['round']<=3 else .6)-cost*(1.5 if cost>=3 else .7)
                if not player['explored_ships'] and player['vp']-cost<5:
                    value-=4
                return (value if action['accept'] else 0), 'charge: actual movable power versus VP/ship budget'
        if t=='RebellionCreditsAndQic':
            k=income(player,state)['knowledge']; stock=resources['knowledge']; horizon=remaining(state)
            lost=knowledge_budget_value(stock,k,horizon)-knowledge_budget_value(stock,k,horizon,spend=2)
            return 45+resource_value(player,{'credits':2,'qic':1})-3*lost, 'ship: compare knowledge spending with realizable future advances'
        if t=='FreeAction' and action['kind']=='OreToPowerBowl3':
            total=sum(resources['power'][k] for k in ('bowl1','bowl2','bowl3'))
            if total<4 and resources['ore']>=2:
                adjustment+=12
        return base+adjustment, f'{reason}; integrated_adjustment={adjustment:.2f}'
