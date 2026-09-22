"""Experimental source-informed rankings, NOT rules, rewards or a production opponent.

B15/B17/B19 and LF04 motivate expansion, resource bottlenecks and useful ship access.
Numeric priorities are uncalibrated pilot hypotheses. All choices come from the engine.
"""
from collections import Counter

TARGETS = ('Xenos', 'HadschHallas')
TRACK_KEYS = dict(zip(('Terraforming', 'Navigation', 'ArtificialIntelligence',
                      'GaiaProject', 'Economy', 'Science'),
                     ('terraforming', 'navigation', 'ai', 'gaia', 'economy', 'science')))


def distance(a, b):
    aq, ar = map(int, a.split(',')); bq, br = map(int, b.split(','))
    return max(abs(aq-bq), abs(ar-br), abs(aq+ar-bq-br))


def kind(value):
    return next(iter(value)) if isinstance(value, dict) else value


class StrategyTeacher:
    """Stateless deterministic candidate ranking; never edits or prunes a snapshot."""
    def choose(self, snapshot):
        scores = self.rank(snapshot)
        index = max(range(len(scores)), key=lambda i: (scores[i][0], -i))
        return snapshot['decision_id'], index

    def rank(self, snapshot):
        if snapshot['player'] is None or not snapshot['candidates']:
            raise ValueError('No live decision')
        return [self.score(snapshot, c['action']) for c in snapshot['candidates']]

    def context(self, s):
        state = s['state']
        p = next(p for p in state['players'] if p['player_id'] == s['player'])
        if p['faction'] not in TARGETS:
            raise ValueError('Teacher is scoped to Xenos and HadschHallas')
        return state, p, p['resources']

    def location(self, state, p, coord):
        """Expansion opportunities and charging neighbors; not an exact cost estimator."""
        cells = state['board']['hexes']
        home = 'Desert' if p['faction'] == 'Xenos' else 'Oxide'
        nearby = sum(1 for c, h in cells.items() if h['planet'] and
                     h['planet']['owner'] is None and c != coord and distance(coord, c) <= 2
                     and h['planet']['planet_type'] in (home, 'Gaia'))
        neighbors = sum(1 for c, h in cells.items() if distance(coord, c) <= 2 and
                        any(b['owner'] != p['player_id'] for b in h['structures']))
        ship_dist = min(distance(coord, c) for c in state['board']['spaceship_tiles'].values())
        own = [b['hex'] for b in p['structures']]
        overlap = sum(distance(coord, c) <= 1 for c in own)
        return min(nearby, 5)*1.5 + min(neighbors, 2)*2 - ship_dist*.35 - overlap

    def research(self, state, p, track):
        key = TRACK_KEYS[track]; level = p['research_tracks'][key]; rnd = state['round']
        rivals = sum(q['research_tracks'][key] >= max(2, level) for q in state['players']
                     if q['player_id'] != p['player_id'])
        score = 3 + (4 if level >= 2 else 0) - rivals
        if track == 'Economy' and rnd <= 3: score += 10 if level in (1, 3) else 6
        if track == 'Science' and rnd <= 2: score += 8
        if track == 'Navigation' and level < 2 and rnd <= 4:
            score += 9 if level == 1 else 5
        if track == 'Terraforming': score += 7 if rnd >= 3 and level < 3 else 2
        if track == 'ArtificialIntelligence': score += 9 if rnd >= 4 or p['explored_ships'] else 2
        if track == 'GaiaProject' and rnd <= 4:
            positions = [b['hex'] for b in p['structures']]
            reachable = any(h['planet'] and h['planet']['planet_type'] == 'Transdim'
                            and h['planet']['owner'] is None and
                            any(distance(c, pos) <= 2 for pos in positions)
                            for c, h in state['board']['hexes'].items())
            score += 8 if reachable and level == 0 else 0
        return score

    def technology(self, state, p, choice):
        if not choice: return 0
        rnd = state['round']; remaining = max(0, 6-rnd)
        if choice['kind'] == 'Standard':
            tile = choice['tile']
            # Existing engine IDs: 2/3/5 income, 10 charge ACTION, 13 immediate resources.
            value = {2: 3*remaining, 3: 3*remaining, 5: 3*remaining,
                     4: 6, 6: 9 if len(p['structures']) >= 5 else 3,
                     7: 7, 8: 3*remaining if p['research_tracks']['gaia'] else 1,
                     9: 5, 10: 2*(remaining+1), 11: 10, 12: 6, 13: 9}.get(tile, 2)
        else:
            # Deliberately conservative: full advanced-tech counter evaluator is deferred.
            value = 8
        track = choice.get('advance_track')
        if not track and choice['kind'] == 'Standard':
            slots = state['research_board']['tech_tile_slots']
            if tile in slots and slots.index(tile) < 6:
                track = tuple(TRACK_KEYS)[slots.index(tile)]
        return value + (self.research(state, p, track) if track else 0)

    def score(self, s, a):
        state, p, r = self.context(s); t = a['type']; rnd = state['round']
        buildings = Counter(kind(b['kind']) for b in p['structures'])
        power = r['power']; tokens = sum(power[k] for k in ('bowl1', 'bowl2', 'bowl3'))
        if t == 'PlaceStartingStructure':
            return self.location(state, p, a['coord']), 'placement: expansion/charge/ship access'
        if t in ('Pass', 'SelectStartingBooster'):
            return self.booster(a.get('booster_id'), rnd), 'booster: future income; pass fallback'
        if t == 'ChargePower':
            # Keep a small early exploration reserve instead of unconditional charging.
            accept = rnd <= 4 and (p['vp'] >= 6 or bool(p['explored_ships']))
            return (20 if a['accept'] == accept else 0), 'charge: growth with exploration VP reserve'
        if t == 'ChooseIncomeOrder':
            return int(not a['charge_first']), 'income order: token before charging'
        if t in ('ResearchAdvance', 'EclipseResearchBoost'):
            return 40 + self.research(state, p, a['track']), 'research: timing/competition'
        if t == 'FormFederation':
            token = a['token']; value = token.get('kind')
            if value is None:
                value = next(b['federation_token'] for b in state['spaceship_boards'] if b['id'] == token['ship'])
            return 90 - 2*len(a['satellite_hexes']) + self.token_value(value, r), 'federation: conserve satellites, address bottleneck'
        if t == 'Upgrade' or t in ('TwilightFreeResearchLab', 'RebellionFreeTradingStation'):
            target = kind(a.get('to')) if t == 'Upgrade' else ('ResearchLab' if t == 'TwilightFreeResearchLab' else 'TradingStation')
            if target == 'TradingStation':
                base = 57 + (10 if buildings['TradingStation'] == 0 else 0)
                base += 8 if r['credits'] < 5 else 0
                base -= 15 if buildings['Mine'] <= 1 and rnd < 5 else 0
            elif target == 'ResearchLab':
                base = 62 if buildings['ResearchLab'] == 0 else 37
            elif target == 'Academy': base = 63 if rnd <= 3 else 40
            else:
                # Not forbidden early: more attractive once expansion/federation needs it.
                base = 35 if rnd <= 2 else 60
                if p['faction'] == 'HadschHallas' and r['credits'] >= 18: base += 15
                if p['faction'] == 'Xenos' and len(p['structures']) >= 6: base += 15
            event = {'TradingStation':'UpgradeTradingStation', 'ResearchLab':'UpgradeResearchLab',
                     'Academy':'UpgradeLargeBuilding','PlanetaryInstitute':'UpgradeLargeBuilding'}.get(target)
            return base + self.technology(state, p, a.get('tech_tile_choice')) + self.round_bonus(state,event), 'upgrade: income/technology/federation timing'
        if t in ('Build','RoundBoosterRangeBuild','TwilightRangeBuild','SpaceshipCreditTerraform',
                 'EclipseAsteroidMine','PlaceLostPlanet') or (t == 'PowerAction' and a.get('coord')):
            coord = a['coord']; planet = state['board']['hexes'][coord]['planet']
            base = 65 + max(0, 5-rnd)*2 + self.location(state,p,coord)
            if planet:
                home = 'Desert' if p['faction'] == 'Xenos' else 'Oxide'
                if planet['planet_type'] == home or planet['is_gaia_formed']: base += 4
                if planet['planet_type'] == 'Gaia': base += self.round_bonus(state,'BuildMineOnGaia')
            return base + self.round_bonus(state,'BuildMine'), 'build: expansion and round scoring'
        if t in ('ExploreSpaceship','RoundBoosterRangeExploreSpaceship','TwilightRangeExploreSpaceship'):
            ship = a['ship']; board = next(b for b in state['spaceship_boards'] if b['id']==ship)
            useful = ((ship=='Rebellion' and r['qic'] >= 3 and any(x not in p['tech_tiles'] for x in state['research_board']['tech_tiles']+board['tech_tiles']))
                      or (ship=='TFMars' and r['credits'] >= 9)
                      or (ship=='Eclipse' and r['credits'] >= 10 and p['gaiaformers_total'] > p['gaiaformers_deployed'])
                      or (ship=='Twilight' and tokens >= 9))
            return (78 if useful and rnd <= 3 else 20) - 4*len(p['explored_ships']), 'explore: only prioritize a funded follow-up'
        if t == 'RebellionGainTechTile':
            return 65 + self.technology(state,p,{'kind':'Standard','tile':a['tile'],'advance_track':a['track']}), 'Rebellion: technology with research'
        if t in ('GaiaFormation','TFMarsGaiaFormation','RoundBoosterImmediateGaiaFormation',
                 'TwilightRangeGaiaFormation','RoundBoosterRangeGaiaFormation'):
            return (52 if rnd < 6 else -5) + self.location(state,p,a['coord']), 'gaia: leave time for a mine'
        if t == 'ExamineArtifact':
            if tokens < 9 and rnd < 5: return -5, 'artifact: preserve power circulation'
            # 2 and 3 are INCOME, unlike the immediate-resource artifacts 6/7/9.
            value = {2:3*(6-rnd),3:4*(6-rnd),4:3*p['research_tracks']['gaia'],
                     5:3*p['research_tracks']['science'],6:9,7:9,8:7,9:9,12:7}.get(a['artifact'],5)
            return 48 + value, 'artifact: income horizon versus immediate reward'
        if t == 'PowerAction':
            value = {1:8 if r['knowledge'] < 4 else 2,3:10 if r['ore'] < 4 else 3,
                     4:10 if r['credits'] < 8 else 2,5:8 if r['knowledge'] < 4 else 2,
                     7:8 if tokens < 5 else 0}.get(a['id'],0)
            return 54+value, 'power: resource bottleneck'
        if t == 'TechTileSpecialAction': return 79, 'use available resource action'
        if t == 'AcademyQicAction': return 79, 'use available QIC action'
        if t == 'FreeAction': return self.conversion(p,r,a), 'conversion: only address a current deficit'
        if t in ('TFMarsTechBonus','EclipsePlanetTypeBonus','TwilightReplayFederationToken'):
            return 48 + (15 if rnd >= 5 else 0), 'ship: mid/late game scoring'
        if t == 'RebellionCreditsAndQic':
            return (45 if r['knowledge']%4 >= 2 and r['qic']<3 else -4), 'ship: spare knowledge only'
        return 0, 'unmodeled: legal fallback, excluded from demonstrations'

    @staticmethod
    def round_bonus(state, event):
        if not state['round'] or not event: return 0
        tile = state['round_tiles'][state['round']-1]
        return 2*tile['vp_per_unit'] if tile['condition'] == event else 0

    @staticmethod
    def token_value(token, resources):
        if token in (5,8) and resources['credits'] < 10: return 10
        if token in (4,11) and resources['ore'] < 4: return 9
        return {1:8,9:8,12:10,6:7,10:8}.get(token,5)

    @staticmethod
    def booster(booster, rnd):
        # Tie-breaking only, far below productive main actions. No current pass VP estimate.
        return {1:2,2:3,3:3,4:2,5:2,6:2,7:2,8:2,9:2,10:2}.get(booster,0) if rnd < 6 else 0

    @staticmethod
    def conversion(p,r,a):
        if a.get('count',1) != 1: return -20
        k=a['kind']; power=r['power']; tokens=sum(power[x] for x in ('bowl1','bowl2','bowl3'))
        useful = ((k in ('PowerToOre','QicToOre') and r['ore']<2 and (k!='QicToOre' or r['qic']>1))
                  or (k=='CreditsToOre' and r['ore']<3 and r['credits']>=9)
                  or (k in ('PowerToCredit','OreToCredit') and r['credits']<3 and (k!='OreToCredit' or r['ore']>=4))
                  or (k in ('PowerToKnowledge','CreditsToKnowledge') and r['knowledge']==3 and (k!='CreditsToKnowledge' or r['credits']>=10))
                  or (k=='CreditsToQic' and r['qic']<3 and r['credits']>=14 and bool(p['explored_ships']))
                  or (k=='BurnPower' and power['bowl3']<4 and tokens>5)
                  or (k=='OreToPowerBowl3' and tokens<6 and r['ore']>=3 and power['bowl3']<3))
        return 58 if useful else -10
