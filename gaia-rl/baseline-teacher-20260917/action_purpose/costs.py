"""Cost adaptation for the corrected engine; historical experiment sources stay frozen."""
import copy
from dataclasses import replace
from economy.teacher import construction_cost as pinned_cost, RING
from research_context.teacher import ContextResearchTeacher, expansion_gain as pinned_gain, advance
from integrated.boosters import next_income, funded, round_vp


def construction_cost(state, player, action):
    cost = pinned_cost(state, player, action)
    if cost is None or 'coord' not in action or action['type'] in ('Upgrade', 'TwilightFreeResearchLab', 'RebellionFreeTradingStation'):
        return cost
    planet = state['board']['hexes'][action['coord']]['planet']
    if planet and planet['planet_type'] == 'Gaia' and not planet['is_gaia_formed']:
        # This teacher's supported factions (Xenos/HH) both pay one entry QIC.
        return replace(cost, qic=cost.qic+1)
    return cost


def expansion_gain(state, before, after):
    resources = next_income(state, before)['resources']
    available = copy.deepcopy(after)
    available['resources'] = copy.deepcopy(resources)
    if sum(s['kind'] == 'Mine' for s in before['structures']) >= 8:
        return 0.0
    gains = []
    for coord, cell in state['board']['hexes'].items():
        planet = cell['planet']
        if not planet or planet['owner'] is not None or planet['planet_type'] not in (*RING, 'Gaia'):
            continue
        action = {'type': 'Build', 'coord': coord}
        old, new = construction_cost(state, before, action), construction_cost(state, available, action)
        if not funded(available, new):
            continue
        gain = (old.ore-new.ore)*2.5+(old.qic-new.qic)*2.5
        if not all(getattr(old, key) <= resources[key] for key in ('ore', 'credits', 'qic')):
            gain += 5+.5*round_vp(state, after, coord, 'Mine', max(1, state['round']))
        if gain > 0:
            gains.append(gain)
    return sum(value*(1 if i == 0 else .35) for i, value in enumerate(sorted(gains, reverse=True)[:2]))


class CorrectedContextTeacher(ContextResearchTeacher):
    """Unchanged control strategy plus mandatory raw-Gaia cost/forecast adaptation."""
    def score(self, snapshot, action):
        value, reason = super().score(snapshot, action)
        state, player, _ = self.context(snapshot)
        old, new = pinned_cost(state, player, action), construction_cost(state, player, action)
        if old and new and new.qic != old.qic:
            value -= 4*(new.qic-old.qic)
            reason += '; corrected natural Gaia entry QIC'
        return value, reason

    def research(self, state, player, track):
        value = super().research(state, player, track)
        if track in ('Navigation', 'Terraforming') and player['research_tracks'][track.lower()] < 5:
            after = advance(player, track)
            value += expansion_gain(state, player, after)-pinned_gain(state, player, after)
            if track == 'Navigation' and player['research_tracks']['navigation'] == 0:
                candidate = getattr(self, '_candidate', None) or {}
                budget = 4 if candidate.get('type') in ('Upgrade', 'TwilightFreeResearchLab') else 8
                from integrated.features import income, remaining
                if remaining(state) and player['resources']['knowledge']+income(player, state)['knowledge'] >= budget:
                    after = advance(player, track, 2)
                    value += .55*(expansion_gain(state, player, after)-pinned_gain(state, player, after))
        return value
