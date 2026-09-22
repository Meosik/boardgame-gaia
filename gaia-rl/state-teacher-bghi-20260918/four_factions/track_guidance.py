"""B19 pp.10–11: expansion first, economy2 as a conditional bridge.

This first quartet slice is a soft opportunity estimate plus paid plan proposals,
not a track mask, a calibrated VP model, or all of the author's strategy. Reuse
the existing research_context expansion prices/discounts, not new track bonuses.
"""
from copy import deepcopy

from economy.teacher import Cost, NAV_RANGE, ORE_PER_STEP, RING, origins, path_distance
from integrated.boosters import round_vp
from integrated.features import active, remaining

HOME = {'Xenos': 'Desert', 'HadschHallas': 'Oxide', 'Terrans': 'Terra', 'Taklons': 'Swamp'}


def budget(state, player):
    """Stock + one permanent income, not a simulated income phase or financing.

    Caps mirror game_state::Resources. Unknown next boosters/leech/conversions
    are excluded; actual payments and phase choices remain native in the rollout.
    """
    from four_factions.value import production
    recurring = production(state, player, include_booster=False)
    caps = {'ore': 15, 'credits': 30, 'knowledge': 15, 'qic': 255}
    return {key: min(caps[key], player['resources'][key]+recurring[i])
            for i, key in enumerate(caps)}


def costs(state, player):
    """Ordinary seven-colour/natural-Gaia mines only; no invented ship actions."""
    if player['faction'] not in HOME:
        return {}
    home = RING.index(HOME[player['faction']])
    reach = NAV_RANGE[player['research_tracks']['navigation']] + int(12 in active(player))
    starts = origins(state, player)
    result = {}
    for coord, cell in state['board']['hexes'].items():
        planet = cell['planet']
        if not planet or planet['owner'] is not None or cell['structures']:
            continue
        kind = planet['planet_type']
        gaia = planet['is_gaia_formed'] or kind == 'Gaia'
        if kind not in RING and kind != 'Gaia':
            continue  # Transdim projects retain their separate Gaia evaluator.
        gap = abs(home-RING.index(kind)) if kind in RING else 0
        steps = 0 if gaia else min(gap, 7-gap)
        ore = 1 + steps*ORE_PER_STEP[player['research_tracks']['terraforming']]
        qic = max(0, (path_distance(state, starts, coord)-reach+1)//2) + int(gaia)
        result[coord] = Cost(ore=ore, credits=2, qic=qic, terraform_steps=steps)
    return result


def affordable(cost, resources):
    return all(getattr(cost, key) <= resources[key] for key in ('ore', 'credits', 'qic'))


def enabled(state, player):
    return (player['faction'] in HOME and remaining(state) > 0
            and 'Setup' not in state['phase']
            and sum(s['kind'] == 'Mine' for s in player['structures']) < 8)


def funded_colonies(state, player):
    if not enabled(state, player):
        return {}
    resources = budget(state, player)
    return {coord: cost for coord, cost in costs(state, player).items() if affordable(cost, resources)}


def _expansion(state, player, resources):
    neutral = deepcopy(player)
    neutral['research_tracks'].update(navigation=0, terraforming=0)
    old = costs(state, neutral)
    options = []
    for coord, new in costs(state, player).items():
        if not affordable(new, resources):
            continue
        previous = old[coord]
        value = 2.5*(previous.ore-new.ore + previous.qic-new.qic)
        if not affordable(previous, resources):
            tile = state['round_tiles'][max(1, state['round'])-1]
            vp = (tile['vp_per_unit']*new.terraform_steps if tile['condition'] == 'TerraformingStep'
                  else round_vp(state, player, coord, 'Mine', max(1, state['round'])))
            value += 5 + .5*vp
        if value > 0:
            options.append((value, coord, new))
    # Existing best/second discounts, but never count two mutually unfundable mines.
    pool = dict(resources)
    supply = 8-sum(s['kind'] == 'Mine' for s in player['structures'])
    result, selected = 0.0, 0
    for value, coord, cost in sorted(options, key=lambda item: (-item[0], item[1])):
        if not affordable(cost, pool):
            continue
        result += value*(1 if selected == 0 else .35)
        for key in ('ore', 'credits', 'qic'):
            pool[key] -= getattr(cost, key)
        selected += 1
        if selected >= min(2, supply):
            break
    return result


def expansion_potential(state, player):
    """State potential: fundable savings/access relative to level0 capabilities.

    The same function is used before/after actions and at rollout leaves. Range1
    receives the existing .55 bridge estimate only with knowledge for range2 and
    a concrete benefit; no fixed reward merely for approaching a recommended level.
    """
    if not enabled(state, player):
        return 0.0
    resources = budget(state, player)
    value = _expansion(state, player, resources)
    if player['research_tracks']['navigation'] == 1 and resources['knowledge'] >= 4:
        next_player = deepcopy(player)
        next_player['research_tracks']['navigation'] = 2
        value += .55*max(0, _expansion(state, next_player, resources)-value)
    return value


def guide_goals(snapshot):
    """Preserve all ordinary/faction alternatives; B19 proposals get compared first.

    No economy4 or science/AI preference is inferred from these narrow predicates.
    Strategic competition and advanced-tile races remain existing separate plans.
    """
    from four_factions.preparation import Goal
    state, actor = snapshot['state'], snapshot['player']
    player = state['players'][actor]
    if not enabled(state, player):
        return []
    goals = []
    current = funded_colonies(state, player)

    def add(name, coord, research=()):
        steps = tuple(Goal(f'{track}-{level}', 'research', target=track, level=level)
                      for track, level in research)
        steps += (Goal(f'colony@{coord}', 'colony', coord, sources=('B19',)),)
        goals.append(Goal(f'B19-{name}@{coord}', 'ordered', steps=steps, sources=('B19',)))

    nav = deepcopy(player)
    nav['research_tracks']['navigation'] = max(2, player['research_tracks']['navigation'])
    navigable = funded_colonies(state, nav)
    for coord, cost in navigable.items():
        if coord not in current or cost.qic < current[coord].qic:
            add('navigation2-expand', coord, (('Navigation', 2),))
    for coord in current:
        add('expand-now', coord)
    if player['research_tracks']['terraforming'] in (1, 2):
        terra = deepcopy(player)
        terra['research_tracks']['terraforming'] = 3
        for coord, cost in funded_colonies(state, terra).items():
            if coord not in current or cost.ore < current[coord].ore:
                add('terraforming3-expand', coord, (('Terraforming', 3),))
    if not current and not navigable and player['research_tracks']['economy'] < 2:
        economy = deepcopy(player)
        economy['research_tracks']['economy'] = 2
        ready = funded_colonies(state, economy)
        for coord in ready:
            add('economy2-bridge', coord, (('Economy', 2),))
        economy['research_tracks']['navigation'] = nav['research_tracks']['navigation']
        for coord in funded_colonies(state, economy):
            if coord not in ready:
                add('economy2-bridge-navigation2', coord, (('Economy', 2), ('Navigation', 2)))
    return goals
