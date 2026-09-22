"""Conditional guide comparisons, never faction bonuses or unconditional scripts.

Existing quartet source paths remain in four_factions.source_paths. These cover
the other ten original factions using the repository's B04-B19 source summaries.
Expansion factions use native-effect baselines, not fabricated opening books.
"""
from strategy_teacher import kind


def action_matches(goal, action):
    action_type, _, subtype = goal.target.partition(':')
    return (action['type'] == action_type and (not subtype or subtype in (action.get('kind'), action.get('track')))
            and (goal.coord is None or action.get('coord', action.get('mine_coord')) == goal.coord))


def goals(snapshot):
    from four_factions.preparation import Goal, achieved
    from four_factions.source_paths import colony_count
    from federation.teacher import formations
    state, actor = snapshot['state'], snapshot['player']
    player = state['players'][actor]
    faction = player['faction']
    sources = {'Ambas': 'B06', 'Gleens': 'B05', 'Itars': 'B07', 'Nevlas': 'B08',
               'Firaks': 'B09', 'BalTaks': 'B11', 'Ivits': 'B12', 'Bescods': 'B13',
               'Geodens': 'B14', 'Lantids': 'B16'}
    if faction not in sources:
        return []
    source = (sources[faction],)
    result = []
    structures = player['structures']
    sites = [s['hex'] for s in structures if kind(s['kind']) in ('Mine', 'TradingStation', 'ResearchLab')]
    pi_present = any(s['kind'] == 'PlanetaryInstitute' for s in structures)
    pi_sites = [s['hex'] for s in structures if s['kind'] in ('Mine', 'TradingStation')]
    if faction == 'Bescods':
        pi_sites = sites

    def upgrade(site, target):
        return Goal(f'{target}@{site}', 'upgrade', site, target)

    def action(target, coord=None):
        return Goal(f'{target}@{coord}', 'faction-action', coord, target, sources=source)

    def add(name, steps):
        # Remove only satisfied leading prerequisites, not a future rebuild that
        # happens to be present before its preceding downgrade.
        steps = list(steps)
        while steps and achieved(snapshot, actor, steps[0]):
            steps.pop(0)
        if steps:
            result.append(Goal(f'{faction}-{name}', 'ordered', steps=tuple(steps), sources=source))

    def with_pi(name, followups):
        if pi_present:
            add(name, followups)
        else:
            for site in pi_sites:
                add(f'PI@{site}-{name}', (upgrade(site, 'PlanetaryInstitute'), *followups))

    expand = Goal('one-new-colony', 'expansion', level=colony_count(state, player)+1)
    federation = Goal('next-federation-token', 'federation-race', level=formations(player)+1)
    if faction == 'Ambas':
        with_pi('relocate-then-federate', (action('AmbasSwapPlanetaryInstitute'), federation))
    elif faction == 'Ivits':
        add('station-then-extend-federation', (action('IvitsPlaceSpaceStation'), federation))
        add('station-then-expand', (action('IvitsPlaceSpaceStation'), expand))
    elif faction == 'Firaks':
        for site in sites:
            lab = upgrade(site, 'ResearchLab')
            work = (lab, action('FiraksDowngradeResearchLab', site), lab)
            if pi_present:
                add(f'lab-downgrade-rebuild@{site}', work)
            else:
                for pi_site in pi_sites:
                    if pi_site != site:
                        add(f'PI@{pi_site}-lab-cycle@{site}', (upgrade(pi_site, 'PlanetaryInstitute'), *work))
    elif faction == 'Bescods':
        add('lowest-research-then-expand', (action('BescodsLowestResearchAdvance'), expand))
    elif faction == 'BalTaks':
        add('former-QIC-then-expand', (action('FreeAction:GaiaformerToQic'), expand))
    elif faction == 'Nevlas':
        for track in ('Economy', 'Science'):
            level = player['research_tracks'][track.lower()]
            if level < 5:
                work = (action('FreeAction:PowerToGaiaKnowledge'),
                        Goal(f'{track}-next', 'research', target=track, level=level+1))
                add(f'knowledge-then-{track}', work)
                with_pi(f'knowledge-then-{track}', work)
    elif faction == 'Itars':
        for coord, cell in state['board']['hexes'].items():
            planet = cell['planet']
            if planet and planet['planet_type'] == 'Transdim' and planet['owner'] in (None, actor):
                with_pi(f'Gaia-tech@{coord}', (action('GaiaFormation', coord), action('ItarsGaiaTechChoice')))
    elif faction == 'Gleens':
        for coord, cell in state['board']['hexes'].items():
            planet = cell['planet']
            if planet and planet['planet_type'] == 'Gaia' and planet['owner'] is None:
                colony = Goal(f'natural-Gaia@{coord}', 'colony', coord)
                for site in [s['hex'] for s in structures if s['kind'] in ('Mine', 'TradingStation')]:
                    add(f'credits-then-natural-Gaia@{site}/{coord}', (upgrade(site, 'TradingStation'), colony))
                add(f'natural-Gaia@{coord}', (colony,))
    elif faction in ('Geodens', 'Lantids'):
        own_types = {state['board']['hexes'][s['hex']]['planet']['planet_type'] for s in structures
                     if state['board']['hexes'][s['hex']]['planet']}
        for coord, cell in state['board']['hexes'].items():
            planet = cell['planet']
            eligible = planet and (planet['owner'] not in (None, actor) if faction == 'Lantids' else
                                   planet['owner'] is None and planet['planet_type'] not in own_types)
            if eligible:
                with_pi(f'{"cohabit" if faction == "Lantids" else "new-type"}@{coord}', (action('Build', coord),))
    return result
