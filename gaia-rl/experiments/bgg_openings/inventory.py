"""Part 2 counts surviving pieces, not colonies or cumulative upgrade milestones."""
from collections import Counter

from .catalog import Buildings, Opening, load_catalog

KINDS = {'Mine': 'mine', 'TradingStation': 'trading_station', 'ResearchLab': 'research_lab',
         'PlanetaryInstitute': 'planetary_institute'}


def building_counts(player: dict) -> Buildings:
    counts: Counter[str] = Counter()
    for structure in player['structures']:
        kind = structure['kind']
        if isinstance(kind, dict):
            if set(kind) != {'Academy'} or kind['Academy'] not in ('Science', 'Qic'):
                raise ValueError(f'Unexpected native structure kind: {kind}')
            counts['academy'] += 1
        elif kind in KINDS:
            counts[KINDS[kind]] += 1
        elif kind not in ('Satellite', 'SpaceStation'):
            raise ValueError(f'Unexpected native structure kind: {kind}')
    return Buildings(**counts)


def matches(player: dict, opening: Opening) -> bool:
    return player['faction'] == opening.faction and building_counts(player) == opening.buildings


def round_one_result(before: dict, after: dict, player_id: int) -> tuple[Opening, ...]:
    """Read a recorded R1->R2 boundary; caller still owes independent native replay.

    Use the last R1 state, never later R2 improvements or a hypothetical forecast.
    IDs are looked up explicitly, not treated as list offsets or modulo-four seats.
    """
    if (before['state']['round'] != 1 or after['state']['round'] != 2
            or after['steps'] != before['steps'] + 1
            or after['decision_id'] != before['decision_id'] + 1):
        raise ValueError('An adjacent native round-one boundary is required')
    players = [p for p in before['state']['players'] if p['player_id'] == player_id]
    if len(players) != 1:
        raise ValueError('Missing or ambiguous native player ID')
    player = players[0]
    # Expansion factions have no observed source opening, not invented zero-quality goals.
    return tuple(o for o in load_catalog().get(player['faction'], ()) if matches(player, o))
