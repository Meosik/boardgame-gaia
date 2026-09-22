"""Contextual research experiment; keeps the integrated-v1 control immutable.

No fixed 'always Science' or forced track balance. Two supported factions inherit
actual structures, permanent income, home type, starting tracks and PI benefits.
"""
import copy
from economy.teacher import construction_cost, range_qic, RING, origins, path_distance
from strategy_teacher import TRACK_KEYS
from integrated.teacher import IntegratedTeacher, prospective
from integrated.features import income, remaining, TRACKS, resource_value, knowledge_budget_value, active, advanced_value
from integrated.boosters import next_income, round_vp, funded


def track_room(state, player):
    return sum(max(0, (4 if not player['federation_tokens'] or any(
        p['player_id']!=player['player_id'] and p['research_tracks'][key]==5
        for p in state['players']) else 5)-level)
        for key,level in player['research_tracks'].items())


def knowledge_stream(stock, recurring, rounds, room, immediate=0):
    """Single value for usable knowledge, not resource value PLUS research value.

Discount the timing of additional paid advances; cap by remaining track room.
Future free upgrades, leech, knowledge cap and exact turn budgets are not simulated.
"""
    total=stock+immediate
    spent=min(room,total//4)
    value=4*spent
    for t in range(1,rounds+1):
        total+=recurring
        advances=min(room,total//4)
        value+=(advances-spent)*4*.8**t
        spent=advances
    if spent<room:
        value+=(total%4)*.35*.8**rounds
    return value


def material_capacity(state, player):
    r=next_income(state,player)['resources']
    # Material-rich expansion can support research; knowledge cannot replace ore/money.
    return .6+.6*min(1,min(r['ore']/6,r['credits']/9))


def advance(player, track, steps=1):
    result=copy.deepcopy(player)
    key=TRACK_KEYS[track]
    for _ in range(steps):
        result['research_tracks'][key]+=1
        effect=TRACKS[track][result['research_tracks'][key]]
        if track=='GaiaProject':
            result['gaiaformers_total']+=effect.get('gaiaformers',0)
            result['resources']['power']['bowl1']+=effect.get('power_tokens',0)
    return result


def gaia_opportunity(state, player):
    """Funded reachable conversion+mine opportunity, including temporary power cost."""
    if not remaining(state):
        return 0.0
    level=player['research_tracks']['gaia']
    if not level:
        return 0.0
    available=max(0,player['gaiaformers_total']-player['gaiaformers_deployed']
                  -player['gaiaformers_in_gaia_area']-player['resources']['spent_gaia_formers'])
    r=next_income(state,player)['resources']
    tokens=sum(r['power'][k] for k in ('bowl1','bowl2','bowl3'))
    required=(255,6,6,4,3,3)[level]
    capacity=min(available,tokens//required,r['ore'],r['credits']//2,
                 max(0,8-sum(s['kind']=='Mine' for s in player['structures'])),remaining(state),2)
    if not capacity:
        return 0.0
    values=[]
    rnd=min(6,state['round']+1)
    for coord,cell in state['board']['hexes'].items():
        p=cell['planet']
        if not p or p['planet_type']!='Transdim' or p['owner'] is not None or p['is_gaia_formed']:
            continue
        qic=range_qic(state,player,coord)
        if qic>r['qic']:
            continue
        scoring=state['round_tiles'][rnd-1]
        bonus=scoring['vp_per_unit'] if scoring['condition'] in ('BuildMine','BuildMineOnGaia') else 0
        goal=2 if any(t['condition']=='MostGaiaPlanets' for t in state['final_scoring_tiles']) else 0
        tile=3 if 8 in active(player) else 0
        values.append(max(0,6+bonus+goal+tile-qic*2.5-.5*max(0,4-(tokens-required))))
    # Discount second colony; not a promise of two jointly legal project sequences.
    best=sorted(values,reverse=True)[:int(capacity)]
    return sum(v*(.7 if i==0 else .25) for i,v in enumerate(best))


def expansion_gain(state, before, after):
    r=next_income(state,before)['resources']
    available=copy.deepcopy(after);available['resources']=copy.deepcopy(r)
    gains=[]
    if sum(s['kind']=='Mine' for s in before['structures'])>=8:
        return 0.0
    for coord,cell in state['board']['hexes'].items():
        p=cell['planet']
        if not p or p['owner'] is not None or p['planet_type'] not in (*RING,'Gaia'):
            continue
        a={'type':'Build','coord':coord}
        old=construction_cost(state,before,a);new=construction_cost(state,available,a)
        if not funded(available,new):
            continue
        gain=(old.ore-new.ore)*2.5+(old.qic-new.qic)*2.5
        old_funded=all(getattr(old,k)<=r[k] for k in ('ore','credits','qic'))
        if not old_funded:
            gain+=5+.5*round_vp(state,after,coord,'Mine',max(1,state['round']))
        if gain>0:gains.append(gain)
    gains.sort(reverse=True)
    return sum(v*(1 if i==0 else .35) for i,v in enumerate(gains[:2]))


class ContextResearchTeacher(IntegratedTeacher):
    def legacy_expansion_gain(self,state,player,after):
        before_options=self.construction_options(state,player)
        gains=[];recurring=income(player,state)
        for coord,cost in self.construction_options(state,after).items():
            if cost.ore>player['resources']['ore']+recurring['ore'] or cost.credits>player['resources']['credits']+recurring['credits']:
                continue
            old=before_options.get(coord)
            gain=6 if old is None else (old.ore-cost.ore)*3+(old.qic-cost.qic)*4
            if gain>0:gains.append(gain)
        return sum(sorted(gains,reverse=True)[:2])

    def research(self,state,player,track):
        level=player['research_tracks'][TRACK_KEYS[track]]
        if level>=5:return 0.0
        base=super().research(state,player,track)
        after=advance(player,track)
        h=remaining(state);stock=player['resources']['knowledge']
        if track=='Science':
            old_income,new_income=income(player,state),income(after,state)
            delta={k:new_income[k]-old_income[k] for k in old_income}
            # Remove both old ways of rewarding the same additional knowledge.
            base-=resource_value(player,delta)*h*.7
            base-=knowledge_budget_value(stock,new_income['knowledge'],h)-knowledge_budget_value(stock,old_income['knowledge'],h)
            immediate=9 if level==4 else 0
            if immediate:base-=resource_value(player,{'knowledge':9})
            room=track_room(state,after)
            value=knowledge_stream(stock,new_income['knowledge'],h,room,immediate)
            value-=knowledge_stream(stock,old_income['knowledge'],h,room)
            base+=value*material_capacity(state,player)
        if track in ('Navigation','Terraforming'):
            base-=self.legacy_expansion_gain(state,player,after)
            base+=expansion_gain(state,player,after)
        if track=='Navigation':
            starts=origins(state,player)
            ships=max((self.ship_value(state,after,ship,starts)-self.ship_value(state,player,ship,starts)
                       for ship in state['board']['spaceship_tiles']),default=0)
            base+=max(0,ships)+max(0,gaia_opportunity(state,after)-gaia_opportunity(state,player))
            # 0->1 alone adds no range. Look ahead to2 only when the follow-up is fundable.
            candidate=getattr(self,'_candidate',None) or {}
            followup_budget=4 if candidate.get('type') in ('Upgrade','TwilightFreeResearchLab') else 8
            if level==0 and h and stock+income(player,state)['knowledge']>=followup_budget:
                two=advance(player,track,2)
                base+=.55*(expansion_gain(state,player,two)
                           +max(0,gaia_opportunity(state,two)-gaia_opportunity(state,player)))
        if track=='GaiaProject':
            if level==0 and h:
                nearby=any(c['planet'] and c['planet']['planet_type']=='Transdim' and c['planet']['owner'] is None
                           and path_distance(state,origins(state,player),coord)<=2
                           for coord,c in state['board']['hexes'].items())
                base-=5*nearby
            base+=gaia_opportunity(state,after)-gaia_opportunity(state,player)
            tokens=TRACKS[track][level+1].get('power_tokens',0)
            circulating=sum(player['resources']['power'][k] for k in ('bowl1','bowl2','bowl3'))
            base+=min(tokens,max(0,6-circulating))*1.5
        return base

    def score(self,snapshot,action):
        value,reason=super().score(snapshot,action)
        if action['type']=='ResearchAdvance':
            state,player,_=self.context(snapshot)
            # A paid advance consumes4knowledge; free tile advances do not.
            cost=knowledge_stream(player['resources']['knowledge'],0,0,track_room(state,player))
            cost-=knowledge_stream(max(0,player['resources']['knowledge']-4),0,0,track_room(state,player))
            value-=cost
            reason+=f'; paid knowledge opportunity={cost:.2f}'
        if action['type'] in ('ResearchAdvance','EclipseResearchBoost'):
            state,player,_=self.context(snapshot)
            level=player['research_tracks'][TRACK_KEYS[action['track']]]
            replenishes=action['track']=='Terraforming' and state['research_board']['terraforming_level_5_token'] is not None
            if level==4 and len(player['federation_tokens'])==1 and not replenishes:
                opportunity=0.0
                for candidate in snapshot['candidates']:
                    a=candidate['action'];choice=a.get('tech_tile_choice')
                    if not choice or choice['kind'] not in ('Advanced','LostFleetAdvanced'):
                        continue
                    tile=(state['research_board']['lost_fleet_advanced_tech_tile'] if choice['kind']=='LostFleetAdvanced'
                          else state['research_board']['advanced_tech_tiles'][list(TRACK_KEYS).index(choice['track'])])
                    if tile is not None:
                        p=prospective(player,a)
                        net=advanced_value(state,p,tile)-self.standard_retained_value(state,p,choice['covered_tile'])
                        opportunity=max(opportunity,min(8,max(0,net)))
                value-=opportunity
                reason+=f'; last-green available-tech opportunity={opportunity:.2f}'
            reason+='; contextual research: material income, usable knowledge, reachable colonies/ships'
        return value,reason
