"""One-round booster forecasts for Xenos/HH, not synthetic legal candidates.

B03: early resources, later scoring; value range only with a usable destination.
Current engine IDs/effects override the older article's base-game tile numbering.
"""
import copy
from dataclasses import dataclass

from economy.teacher import construction_cost, range_qic, RING, SHIP_IDS
from strategy_teacher import kind
from integrated.features import active, income, resource_value, knowledge_budget_value, sector_at, TRACKS

# rules/engine.rs apply_round_booster_income / round_booster_pass_vp.
INCOME = {1: {'knowledge': 1}, 2: {'ore': 1}, 3: {'ore': 1}, 4: {}, 5: {},
          6: {'ore': 1}, 7: {'ore': 1}, 8: {}, 9: {'credits': 2, 'qic': 1},
          10: {'ore': 1}, 11: {'credits': 4}, 12: {'credits': 2},
          13: {'ore': 1, 'knowledge': 1}, 14: {'credits': 3}}
CHARGE = {4: 4, 5: 2, 8: 2}


def charge(power, amount):
    first = min(amount, power['bowl1'])
    power['bowl1'] -= first
    power['bowl2'] += first
    second = min(amount-first, power['bowl2'])
    power['bowl2'] -= second
    power['bowl3'] += second


def next_income(state, player):
    """Known permanent income; no future leech, conversions or opponent actions."""
    result = copy.deepcopy(player)
    r = result['resources']
    for key, amount in income(player, state).items():
        r[key] += amount
    pi = any(s['kind']=='PlanetaryInstitute' for s in player['structures'])
    if pi:
        if player['faction']=='Xenos':
            r['qic'] += 1
        else:
            r['power']['bowl1'] += 1
    if 2 in player['artifacts']:
        r['power']['bowl3'] += 2
    economy = player['research_tracks']['economy']
    amount = TRACKS['Economy'].get(economy, {}).get('power_charge', 0) if economy < 5 else 0
    if economy in (3, 4):
        amount = (3 if economy==3 else 2) if state['research_board']['economy_research_tile_side']=='Power' else 0
    charge(r['power'], amount + 4*pi + int(2 in active(player)))
    return result


def pass_vp(state, player, booster):
    """Current board only. Newly selected booster does NOT score at the current pass."""
    buildings = [kind(s['kind']) for s in player['structures']]
    coords = {s['hex'] for s in player['structures']}
    planets = [(c,h['planet']) for c,h in state['board']['hexes'].items()
               if h['planet'] and (h['planet']['owner']==player['player_id'] or c in coords)]
    if booster==1:
        return 3*buildings.count('ResearchLab')
    if booster==3:
        lost = state['board']['lost_planet']
        untracked = any(c==lost and c not in coords for c,_ in planets)
        return buildings.count('Mine') + len(player['artifact_mines']) + int(untracked)
    if booster==4:
        return 4*(buildings.count('PlanetaryInstitute')+buildings.count('Academy'))
    if booster==6:
        return 3*max(0, player['gaiaformers_total']-player['resources']['spent_gaia_formers'])
    if booster==7:
        return 2*buildings.count('TradingStation')
    if booster==10:
        return len({('Gaia' if p['is_gaia_formed'] else p['planet_type']) for _,p in planets}
                   | set(player['artifact_mines']))
    if booster==11:
        return sum(p['is_gaia_formed'] or p['planet_type']=='Gaia' for _,p in planets)
    if booster==14:
        return 2*len({sector_at(state,c) for c,_ in planets if sector_at(state,c) in range(11,19)})
    return 0


def funded(player, cost):
    return cost is not None and all(getattr(cost,k)<=player['resources'][k] for k in ('ore','credits','qic'))


def round_vp(state, player, coord, target, rnd):
    tile = state['round_tiles'][rnd-1]
    condition = tile['condition']
    event = {'TradingStation':'UpgradeTradingStation', 'ResearchLab':'UpgradeResearchLab',
             'Academy':'UpgradeLargeBuilding', 'PlanetaryInstitute':'UpgradeLargeBuilding'}.get(kind(target))
    if target=='Mine':
        planet = state['board']['hexes'][coord]['planet']
        current = [state['board']['hexes'][s['hex']]['planet'] for s in player['structures']]
        types = {('Gaia' if p['is_gaia_formed'] else p['planet_type']) for p in current if p} | set(player['artifact_mines'])
        new_type = 'Gaia' if planet['is_gaia_formed'] else planet['planet_type']
        if condition=='BuildMineOnGaia':
            return tile['vp_per_unit']*int(new_type=='Gaia')
        if condition=='BuildMineOnNewPlanetType':
            return tile['vp_per_unit']*int(new_type not in types)
        if condition=='BuildMineInNewSector':
            sector = sector_at(state,coord)
            return tile['vp_per_unit']*int(sector is not None and sector not in {sector_at(state,s['hex']) for s in player['structures']})
        if condition=='TerraformingStep':
            cost = construction_cost(state,player,{'type':'Build','coord':coord})
            return tile['vp_per_unit']*cost.terraform_steps if cost else 0
        event = 'BuildMine'
    return tile['vp_per_unit'] if condition==event else 0


def growth_plans(state, player):
    """One funded ordinary build/upgrade. No multistep financing or free-action stacking."""
    buildings = [s['kind'] for s in player['structures']]
    if buildings.count('Mine') < 8:
        for coord, cell in state['board']['hexes'].items():
            p = cell['planet']
            if not p or p['owner'] is not None or p['planet_type'] not in (*RING,'Gaia'):
                continue
            action = {'type':'Build','coord':coord}
            cost = construction_cost(state,player,action)
            if funded(player,cost):
                yield action, cost, None, 'Mine'
    for structure in player['structures']:
        old = structure['kind']
        targets = {'Mine':['TradingStation'], 'TradingStation':['ResearchLab','PlanetaryInstitute'],
                   'ResearchLab':[{'Academy':'Science'},{'Academy':'Qic'}]}.get(kind(old), [])
        for target in targets:
            limit = {'TradingStation':4,'ResearchLab':3}.get(kind(target),1)
            if buildings.count(target) >= limit:
                continue
            action = {'type':'Upgrade','coord':structure['hex'],'to':target}
            cost = construction_cost(state,player,action)
            if funded(player,cost):
                yield action, cost, old, target


def growth_value(state, player, booster, rnd):
    current = pass_vp(state,player,booster)
    best = 0.0
    for action,cost,old,target in growth_plans(state,player):
        after = copy.deepcopy(player)
        if old is None:
            after['structures'].append({'hex':action['coord'],'kind':target})
        else:
            next(s for s in after['structures'] if s['hex']==action['coord'])['kind'] = target
        # One plausible extra score, discounted; it is not a forecast of every build.
        delta = pass_vp(state,after,booster)-current
        bonus = round_vp(state,player,action['coord'],target,rnd)
        best = max(best, .6*(delta+bonus)-.15*resource_value(player,{'ore':cost.ore,'credits':cost.credits,'qic':cost.qic}))
    return best


def action_value(state, player, booster, rnd):
    """Only the best use of a once-per-round action, never all reachable destinations."""
    best = 0.0
    r = player['resources']
    former = max(0,player['gaiaformers_total']-player['gaiaformers_deployed']
                 -player['gaiaformers_in_gaia_area']-r['spent_gaia_formers'])
    if booster not in (5,8):
        return best
    for coord,cell in state['board']['hexes'].items():
        p = cell['planet']
        if not p or p['owner'] is not None:
            continue
        normal_qic = range_qic(state,player,coord)
        if booster==5 and former and p['planet_type']=='Transdim' and not p['is_gaia_formed'] and normal_qic<=r['qic']:
            # Immediate Gaia needs no power payment; allow a subsequent funded mine.
            mine = r['ore']>=1 and r['credits']>=2 and sum(s['kind']=='Mine' for s in player['structures'])<8
            bonus = state['round_tiles'][rnd-1]
            scoring = bonus['vp_per_unit'] if bonus['condition'] in ('BuildMine','BuildMineOnGaia') and mine else 0
            best = max(best, 3+2*mine+.5*scoring-.5*normal_qic)
        if booster!=8:
            continue
        boosted_qic = range_qic(state,player,coord,3)
        if boosted_qic > r['qic'] or boosted_qic>=normal_qic:
            continue
        if p['planet_type'] in (*RING,'Gaia') and sum(s['kind']=='Mine' for s in player['structures'])<8:
            boosted = construction_cost(state,player,{'type':'RoundBoosterRangeBuild','coord':coord})
            normal = construction_cost(state,player,{'type':'Build','coord':coord})
            if funded(player,boosted):
                gain = (normal.qic-boosted.qic)*2.5
                if not funded(player,normal):
                    gain += 2+.5*round_vp(state,player,coord,'Mine',rnd)
                # Retain the actual terraforming charge; range is not a free shovel.
                best = max(best,gain-.5*boosted.terraform_ore)
        if p['planet_type']=='Transdim' and not p['is_gaia_formed'] and former and rnd<6:
            level=player['research_tracks']['gaia']
            if level and sum(r['power'][k] for k in ('bowl1','bowl2','bowl3')) >= (255,6,6,4,3,3)[level]:
                best=max(best,(normal_qic-boosted_qic)*2.5)
    if booster==8 and player['exploration_shuttles_available'] and player['vp']>=5:
        for board in state['spaceship_boards']:
            if SHIP_IDS[board['id']] in player['explored_ships'] or all(p is not None for p in board['explorers']):
                continue
            coord=state['board']['spaceship_tiles'][board['id']]
            normal, boosted = range_qic(state,player,coord), range_qic(state,player,coord,3)
            if boosted<=r['qic']:
                best=max(best,(normal-boosted)*2.5)
    return best


@dataclass(frozen=True)
class BoosterValue:
    resources: float = 0
    power: float = 0
    knowledge: float = 0
    pass_points: float = 0
    growth: float = 0
    action: float = 0

    @property
    def total(self):
        return sum((self.resources,self.power,self.knowledge,self.pass_points,self.growth,self.action))


def evaluate_booster(state, player, booster, *, starting=False):
    rnd = 1 if starting else state['round']+1
    if booster is None or rnd>6:
        return BoosterValue()
    if booster not in INCOME:
        raise ValueError(f'Unmapped booster: {booster}')
    baseline = next_income(state,player)
    after = copy.deepcopy(baseline)
    for key,amount in INCOME[booster].items():
        after['resources'][key] += amount
    power = baseline['resources']['power']
    total = sum(power[k] for k in ('bowl1','bowl2','bowl3'))
    power_value = min(CHARGE.get(booster,0),2*power['bowl1']+power['bowl2'])*.8
    charge(after['resources']['power'],CHARGE.get(booster,0))
    if booster==2:
        after['resources']['power']['bowl1'] += 2
        power_value += .5 + 2*min(2,max(0,6-total))
    stock = baseline['resources']['knowledge']
    knowledge = knowledge_budget_value(after['resources']['knowledge'],0,0)-knowledge_budget_value(stock,0,0)
    pass_weight = .55 if rnd<=3 else 1.0
    # Subtract baseline round-goal opportunities common to every available booster.
    growth = max(0,growth_value(state,after,booster,rnd)-growth_value(state,baseline,None,rnd))
    return BoosterValue(resource_value(baseline,INCOME[booster]),power_value,knowledge,
                        pass_weight*pass_vp(state,player,booster),growth,action_value(state,after,booster,rnd))
