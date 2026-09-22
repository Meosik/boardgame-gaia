"""Conditional source proposals for the approved quartet, never scripted moves.

Sources and edition conflicts are mapped in research/strategy/teacher-application.md.
Milestones receive no score bonus. Native paid continuations and the unchanged
two-income leaf decide whether a proposal is better than ordinary play.
"""
from itertools import combinations

from strategy_teacher import kind


def colony_count(state, player):
    initial = 3 if player['faction'] == 'Xenos' else 1 if player['faction'] == 'Ivits' else 2
    if player['faction'] not in ('Xenos', 'HadschHallas', 'Terrans', 'Taklons'):
        from faction_teachers.profiles import profiles
        initial = profiles()[player['faction']].starting_structures
    # The remaining free setup placements are not the requested paid +1/+2 mines.
    return max(initial, len(player['structures'])) if state['round'] == 0 else len(player['structures'])


def opening_goals(snapshot):
    from four_factions.preparation import Goal

    state, actor = snapshot['state'], snapshot['player']
    if state['round'] > 2:
        return []
    player = state['players'][actor]
    faction = player['faction']
    structures = player['structures']
    colonies = colony_count(state, player)
    cores = []

    def upgrade(site, target):
        return Goal(f'{target}@{site}', 'upgrade', site, target)

    def research(track, level):
        return Goal(f'{track}-{level}', 'research', target=track, level=level)

    def add(name, steps, sources):
        cores.append(Goal(name, 'sequence', steps=tuple(steps), sources=tuple(sources)))

    academy_sites = [s['hex'] for s in structures if kind(s['kind']) in ('Mine', 'TradingStation', 'ResearchLab')]
    pi_sites = [s['hex'] for s in structures if s['kind'] in ('Mine', 'TradingStation')]
    for site in academy_sites:
        academy = upgrade(site, 'Science')
        if faction == 'HadschHallas':
            add(f'HH-academy-economy@{site}', (academy, research('Economy', 4)), ('PG19', 'B17'))
        elif faction == 'Xenos':
            add(f'Xenos-academy-range@{site}', (academy, research('Navigation', 2)), ('PG15', 'B15'))
            add(f'Xenos-academy-QIC@{site}', (academy, Goal('Rebellion-use', 'ship', target='Rebellion')),
                ('PG15', 'LF04'))
        elif faction == 'Terrans':
            # PG18 favours PI/Lab. B04 preserves Academy as a competing alternative.
            add(f'Terrans-academy-Gaia@{site}', (academy, research('GaiaProject', 2)), ('B04', 'PG18'))
            for pi_site in pi_sites:
                if pi_site != site:
                    add(f'Terrans-lab-Gaia-PI@{site}/{pi_site}',
                        (upgrade(site, 'ResearchLab'), research('GaiaProject', 2), upgrade(pi_site, 'PlanetaryInstitute')),
                        ('PG18', 'B04'))
        elif faction == 'Taklons':
            for track in ('Economy', 'Science'):
                add(f'Taklons-academy-{track}@{site}', (academy, research(track, 3)), ('PG21', 'B10'))
    for site in pi_sites:
        if faction == 'Terrans':
            for track, level in (('GaiaProject', 2), ('Science', 4)):
                add(f'Terrans-PI-{track}@{site}', (upgrade(site, 'PlanetaryInstitute'), research(track, level)),
                    ('PG18', 'B04'))
        elif faction == 'Taklons':
            add(f'Taklons-PI-cycle@{site}', (upgrade(site, 'PlanetaryInstitute'),), ('B10', 'PG21'))
        elif faction == 'HadschHallas':
            add(f'HH-PI-Rebellion@{site}', (upgrade(site, 'PlanetaryInstitute'),
                Goal('Rebellion-use', 'ship', target='Rebellion')), ('PG19', 'LF04'))
    if faction in ('Taklons', 'Xenos'):
        for a, b in combinations(academy_sites, 2):
            add(f'{faction}-two-labs@{a}/{b}', (upgrade(a, 'ResearchLab'), upgrade(b, 'ResearchLab')),
                ('PG21', 'B10') if faction == 'Taklons' else ('PG15', 'B15'))

    # The user's +1/+2 mines are alternatives both before and after the core.
    # Count colonies, not remaining Mine pieces: an upgrade must not reset progress.
    variants = []
    for core in cores:
        for count in (1, 2):
            expand = Goal(f'{count}-new-colonies', 'expansion', level=colonies+count)
            for early in (False, True):
                steps = (expand,)+core.steps if early else core.steps+(expand,)
                variants.append(Goal(f'{core.name}+{count}-mine-{"first" if early else "after"}',
                                     'sequence', steps=steps, sources=core.sources+('user-mine-variants',)))
    # Do not let every site variant of one core consume all early proposals.
    from four_factions.preparation import interleave_families
    cores = interleave_families(cores, lambda g: g.name.split('@')[0])
    return cores+variants


def expansion_goals(snapshot):
    from four_factions.preparation import Goal

    state, actor = snapshot['state'], snapshot['player']
    player = state['players'][actor]
    goals = []
    # In Lost Fleet a ship has several payoffs, not just the old single example.
    payoffs = {'Rebellion': ('RebellionGainTechTile', 'RebellionFreeTradingStation'),
               'Twilight': ('TwilightRangeBuild', 'TwilightFreeResearchLab', 'TwilightReplayFederationToken', 'ExamineArtifact'),
               'TFMars': ('SpaceshipCreditTerraform', 'TFMarsGaiaFormation'),
               'Eclipse': ('EclipseAsteroidMine', 'EclipseResearchBoost')}
    for ship in state['spaceship_boards']:
        for payoff in dict.fromkeys(payoffs.get(ship['id'], ())+('SpaceshipCreditTerraform',)):
            use = Goal(f'{ship["id"]}-{payoff}', 'ship', target=ship['id'], payoff=payoff,
                       sources=('LF04', 'video-opening-20260913'))
            goals.append(use)
            if payoff in ('RebellionGainTechTile', 'EclipseResearchBoost'):
                goals.append(Goal(f'{use.name}-then-expand', 'sequence', steps=(use,
                    Goal('one-new-colony', 'expansion', level=colony_count(state, player)+1)), sources=use.sources))
    for coord, cell in state['board']['hexes'].items():
        planet = cell['planet']
        if not planet or planet['owner'] not in (None, actor) or cell['structures']:
            continue
        if planet['planet_type'] not in ('Gaia', 'Transdim'):
            continue
        colony = Goal(f'colony@{coord}', 'colony', coord)
        for track in ('Navigation', 'GaiaProject'):
            if track == 'GaiaProject' and planet['planet_type'] != 'Transdim':
                continue
            if player['research_tracks']['navigation' if track == 'Navigation' else 'gaia'] < 2:
                goals.append(Goal(f'{track}-then-colony@{coord}', 'sequence', steps=(
                    Goal(f'{track}-2', 'research', target=track, level=2), colony),
                    sources=('LF01', 'LF04', 'PG14', 'video-opening-20260913')))
    from federation.teacher import formations
    from strategy_teacher import TRACK_KEYS
    for track, tile in zip(TRACK_KEYS, state['research_board']['advanced_tech_tiles']):
        if tile is not None:
            goals.append(Goal(f'early-federation-then-advanced-{tile}', 'sequence', steps=(
                Goal('next-federation', 'federation-race', level=formations(player)+1),
                Goal(f'advanced-{tile}', 'advanced', target=track, tile=tile)),
                sources=('PG15', 'PG19', 'LF04')))
    return goals
