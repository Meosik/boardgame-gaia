"""Common-endpoint forecast utility, not a reward or a predicted final score."""
from integrated.features import (active, advanced_value, income, remaining,
                                 resource_value, sector_at, PASS, EVENT, RESOURCE_ACTIONS)
from strategy_teacher import distance, kind
from research_context.teacher import knowledge_stream, material_capacity, track_room


def final_metric(state, player, condition):
    """Current-board standings; same metric contract as the Rust/TS shared fixture."""
    actor = player['player_id']
    structures = {s['hex'] for s in player['structures']}
    planets = [(c, h['planet']) for c, h in state['board']['hexes'].items()
               if h['planet'] and (h['planet']['owner'] == actor or c in structures)]
    own = [(c, p) for c, p in planets if not (player['faction'] == 'Lantids'
           and c in structures and p['owner'] is not None and p['owner'] != actor)]
    artifacts = player.get('artifact_mines', [])
    lost = state['board'].get('lost_planet')
    lost_planet = state['board']['hexes'].get(lost, {}).get('planet')
    untracked = bool(lost not in structures and lost_planet and lost_planet['owner'] == actor)
    if condition == 'MostStructuresInFederation':
        formed = set()
        for event in state.get('event_log', []):
            payload = event.get('FederationFormed')
            if payload and payload['player'] == actor:
                formed.update(payload['hexes'])
        return sum(kind(s['kind']) not in ('Satellite', 'SpaceStation') and s['hex'] in formed
                   for s in player['structures']) + int(untracked and lost in formed)
    if condition == 'MostBuildings':
        return sum(kind(s['kind']) not in ('Satellite', 'SpaceStation')
                   for s in player['structures']) + int(untracked) + len(artifacts)
    if condition == 'MostPlanetTypes':
        return len({('Gaia' if p['is_gaia_formed'] else p['planet_type']) for _, p in own}
                   | set(artifacts))
    if condition == 'MostGaiaPlanets':
        return sum(p['is_gaia_formed'] or p['planet_type'] == 'Gaia' for _, p in own)
    if condition in ('MostSectors', 'MostDeepSpaceSectors'):
        deep = condition == 'MostDeepSpaceSectors'
        sectors = {sector_at(state, c) for c, _ in planets}
        return len({s for s in sectors if s is not None and (11 <= s <= 18) == deep})
    if condition == 'MostSatellites':
        return sum(h.get('satellites', []).count(actor) for h in state['board']['hexes'].values()) + sum(
            s['kind'] == 'SpaceStation' for s in player['structures'])
    if condition == 'MostAsteroids':
        return sum(p['planet_type'] == 'Asteroid' for _, p in planets) + artifacts.count('Asteroid')
    if condition == 'GreatestDistancePiAcademy':
        return max((distance(a['hex'], b['hex']) for a in player['structures']
                    if a['kind'] == 'PlanetaryInstitute' for b in player['structures']
                    if kind(b['kind']) == 'Academy'), default=0)
    raise ValueError(f'Unmapped final scoring condition: {condition}')


def standing_points(state, actor):
    score = 0
    for tile in state['final_scoring_tiles']:
        values = [final_metric(state, p, tile['condition']) for p in state['players']]
        focal = values[next(i for i, p in enumerate(state['players']) if p['player_id'] == actor)]
        first, tied = sum(v > focal for v in values), values.count(focal)
        awards = (tile.get('vp_1st', 18), tile.get('vp_2nd', 12), tile.get('vp_3rd', 6), 0)
        score += sum(awards[first:first+tied]) // tied
    return score


def endpoint_value(state, actor, reference, teacher, *, guide_tracks=False):
    """Only the tail is estimated; all earlier transitions/caps/payments are native.

    Freeze resource prices at the root so crossing a scarcity threshold cannot
    make a richer leaf appear poorer. Do not revalue immediate tech rewards.
    """
    phase = state['phase']
    if isinstance(phase, dict) and 'Ended' in phase:
        return float(dict(phase['Ended']['final_scores'])[actor])
    player = next(p for p in state['players'] if p['player_id'] == actor)
    horizon = remaining(state)
    resources = {k: player['resources'][k] for k in ('ore', 'credits', 'qic')}
    result = player['vp'] + standing_points(state, actor)
    result += 4 * sum(max(0, min(5, level)-2) for level in player['research_tracks'].values())
    result += resource_value(reference, resources)
    recurring = income(player, state)
    result += .7 * horizon * resource_value(reference, {k: recurring[k] for k in ('ore', 'credits')})
    # Preserve the contextual teacher's single usable-knowledge stream, rather
    # than reintroducing its old resource-plus-research double valuation.
    result += knowledge_stream(player['resources']['knowledge'], recurring['knowledge'],
                               horizon, track_room(state, player)) * material_capacity(state, player)
    # The VictoryPoints overlay's income was missing from the old research value.
    if player['research_tracks']['economy'] in (3, 4) and state['research_board']['economy_research_tile_side'] == 'VictoryPoints':
        result += .7 * horizon
    power = player['resources']['power']
    result += .8 * (power['bowl2'] + 2 * power['bowl3'])
    # Same soft circulation shortfall as the existing reserve adjustment.
    circulating = sum(power[k] for k in ('bowl1', 'bowl2', 'bowl3'))
    if horizon:
        result -= 3 * max(0, (6 if horizon >= 3 else 4)-circulating) + 5 * max(0, 4-circulating)
    for tile in active(player) - {2, 3, 5}:
        result += teacher.standard_retained_value(state, player, tile)
    for tile in player['advanced_tech_tiles']:
        if tile in PASS or tile in EVENT or tile in RESOURCE_ACTIONS:
            result += advanced_value(state, player, tile)
    if guide_tracks:
        from four_factions.track_guidance import expansion_potential
        result += expansion_potential(state, player)
    return result
