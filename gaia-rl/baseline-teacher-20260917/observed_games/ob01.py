"""OB01: conditional comparisons from ONE observed human Lost Fleet game.

Source: research/strategy/observed-uiqoo-20260916.md (uiqoo, 2026-09-16, pre-final
score Bal T'aks 147 / Ivits 131 / Taklons 74 / Firaks 72). One game of unknown
player strength is a hypothesis, not evidence of a better line. These goals only
add candidates to the existing paid native search; they change no reward, price,
legality or default teacher, and an A/B match decides whether they stay.
"""

SOURCE = ('OB01',)
FACTIONS = ('BalTaks', 'Ivits', 'Taklons', 'Firaks')
TRACKS = ('Terraforming', 'Navigation', 'ArtificialIntelligence', 'GaiaProject', 'Economy', 'Science')


def goals(snapshot):
    from four_factions.preparation import Goal, achieved
    from strategy_teacher import TRACK_KEYS
    state, actor = snapshot['state'], snapshot['player']
    player = state['players'][actor]
    faction = player['faction']
    if faction not in FACTIONS or state['round'] < 1:
        return []
    levels = {track: player['research_tracks'][TRACK_KEYS[track]] for track in TRACKS}
    structures = player['structures']
    result = []

    def add(name, steps):
        steps = list(steps)
        while steps and achieved(snapshot, actor, steps[0]):
            steps.pop(0)
        if steps:
            result.append(Goal(f'{faction}-OB01-{name}', 'ordered', steps=tuple(steps), sources=SOURCE))

    def action(target):
        return Goal(target, 'faction-action', target=target, sources=SOURCE)

    def research(track):
        return Goal(f'{track}-{levels[track]+1}', 'research', target=track, level=levels[track]+1)

    def ship(target, payoff):
        return Goal(f'{target}-{payoff}', 'ship', target=target, payoff=payoff)

    formers_free = player['gaiaformers_deployed'] < player['gaiaformers_total']
    if faction == 'BalTaks':
        # Observed engine: Gaia projects -> former-to-QIC -> Rebellion 3-QIC tech,
        # then T F Mars "2 VP + 1 per standard tech" once several techs are held.
        rebellion_tech = ship('Rebellion', 'RebellionGainTechTile')
        if player['gaiaformers_in_gaia_area'] > 0:
            add('former-QIC-Rebellion-tech', (action('FreeAction:GaiaformerToQic'), rebellion_tech))
        elif formers_free:
            add('form-QIC-Rebellion-tech', (action('GaiaFormation'), action('FreeAction:GaiaformerToQic'),
                                            rebellion_tech))
        if len(player['tech_tiles']) >= 3:
            add('TFMars-tech-bonus', (ship('TFMars', 'TFMarsTechBonus'),))
    elif faction == 'Ivits':
        # Observed: six Gaia projects, Gaia/AI/Terraforming all to 5, a Rebellion tech.
        if levels['GaiaProject'] < 5:
            add('Gaia-track', (research('GaiaProject'),))
        if formers_free:
            add('Gaia-project', (action('GaiaFormation'),))
        add('Rebellion-tech', (ship('Rebellion', 'RebellionGainTechTile'),))
    elif faction == 'Taklons':
        # Observed PI only in round 6. Rounds 1-2 PI proposals already exist in
        # four_factions.source_paths; OB01 adds the round-3 comparison only.
        if state['round'] == 3 and not any(s['kind'] == 'PlanetaryInstitute' for s in structures):
            for s in structures:
                if s['kind'] in ('Mine', 'TradingStation'):
                    add(f'round3-PI@{s["hex"]}', (Goal(f'PlanetaryInstitute@{s["hex"]}', 'upgrade', s['hex'],
                                                       'PlanetaryInstitute'),))
    elif faction == 'Firaks':
        # Observed: 14 research steps spread over six tracks, only two finished in R6.
        # Propose concentrating on the two most advanced unfinished tracks.
        open_tracks = [t for t in TRACKS if 0 < levels[t] < 5]
        focus = sorted(open_tracks, key=lambda t: (-levels[t], TRACKS.index(t)))[:2]
        downgrade_ready = (any(s['kind'] == 'PlanetaryInstitute' for s in structures)
                           and any(s['kind'] == 'ResearchLab' for s in structures))
        for track in focus:
            add(f'focus-{track}', (research(track),))
            if downgrade_ready:
                add(f'downgrade-focus-{track}', (action(f'FiraksDowngradeResearchLab:{track}'),))
    return result
