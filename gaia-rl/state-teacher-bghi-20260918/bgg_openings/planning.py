"""Optimistic building topology and selection of actually completed R1 forecasts.

Topology only orders proposals. Native forks, existing conservation constraints,
and paid continuations decide whether any proposed route can actually work.
"""
from collections import deque
from dataclasses import asdict
from functools import lru_cache
import json
import math

from .catalog import Buildings, LIMITS, Opening, load_catalog
from .inventory import building_counts

def _edges(faction):
    edges = [('mine', 'trading_station'), ('trading_station', 'research_lab')]
    edges += ([('trading_station', 'academy'), ('research_lab', 'planetary_institute')]
              if faction == 'Bescods' else
              [('trading_station', 'planetary_institute'), ('research_lab', 'academy')])
    if faction == 'Firaks':
        edges.append(('research_lab', 'trading_station'))
    return edges


@lru_cache(maxsize=64)
def _distances(target: Buildings, faction: str):
    # Reverse BFS over bounded physical inventories. Costs, map access, one-use
    # abilities and research choices are deliberately NOT feasibility claims.
    result = {target: 0}
    pending = deque([target])
    while pending:
        state = pending.popleft()
        counts = asdict(state)
        previous = []
        if counts['mine']:
            previous.append(Buildings(**{**counts, 'mine': counts['mine'] - 1}))
        for old, new in _edges(faction):
            if counts[new] and counts[old] < LIMITS[old]:
                previous.append(Buildings(**{**counts, old: counts[old] + 1, new: counts[new] - 1}))
        for value in previous:
            if value not in result:
                result[value] = result[state] + 1
                pending.append(value)
    return result


def distance_to(current: Buildings, target: Buildings, faction: str) -> int | None:
    return _distances(target, faction).get(current)


def select_forecast(rows: tuple[Opening, ...], remembered: str | None, comparisons: list[dict]):
    """Keep a proven target; otherwise select the existing teacher's best forecast.

    Source score/frequency remain provenance, not fabricated reward coefficients.
    A missing proof means unknown/no route found, never mathematical impossibility.
    """
    by_counts = {row.buildings: row for row in rows}
    choices = []
    for order, comparison in enumerate(comparisons):
        counts = comparison.get('r1_buildings')
        value = comparison.get('value')
        if (not comparison.get('complete') or counts is None
                or not isinstance(value, (int, float)) or not math.isfinite(value)):
            continue
        opening = by_counts.get(Buildings(**counts))
        if opening is not None:
            choices.append((opening.label == remembered, value, -order, comparison, opening))
    if not choices:
        return None
    chosen = max(choices, key=lambda choice: choice[:3])
    return chosen[3], chosen[4]


def goals(snapshot, remembered=None):
    from four_factions.preparation import Goal
    if snapshot['state']['round'] > 1:
        return []
    player = snapshot['state']['players'][snapshot['player']]
    rows = load_catalog().get(player['faction'], ())
    current = building_counts(player)
    # Preserve printed source order; do not rank small samples as verified winners.
    ordered = sorted(rows, key=lambda row: row.label != remembered)
    return [Goal(f'BGG-R1-{row.label}', 'bgg-opening', target=row.label, sources=('BGG-O2',))
            for row in ordered if distance_to(current, row.buildings, player['faction']) is not None]


def select_action(env, snapshot, scores, target: Buildings, policies, deadline):
    """A native-paid move toward the inventory, or an existing teacher fallback."""
    from four_factions.preparation import Goal, check_time, funding_need, select_goal
    from current_actions.conservation import blocked
    from research_plans.teacher import best_index
    from strategy_teacher import kind
    fallback = best_index(scores, range(len(scores)))
    if snapshot['state']['round'] != 1 or 'ActionPhase' not in snapshot['state']['phase']:
        return fallback
    actor = snapshot['player']
    player = snapshot['state']['players'][actor]
    faction = player['faction']
    current = building_counts(player)
    distance = distance_to(current, target, faction)
    if distance is None:
        return fallback
    direct = []
    for i, candidate in enumerate(snapshot['candidates']):
        if blocked(scores[i]):
            continue
        check_time(deadline)
        after = json.loads(env.fork(snapshot['decision_id'], i).snapshot_json())
        resulting = building_counts(after['state']['players'][actor])
        remaining = distance_to(resulting, target, faction)
        # All compound actions use their true native effect, not guessed fields.
        if remaining is not None and (remaining < distance or distance == remaining == 0):
            direct.append(i)
    selected = best_index(scores, direct)
    if selected is not None:
        return selected

    # Reuse the existing quartet's paid upgrade funding search. It never inserts
    # hypothetical resources, relaxes conservation, or changes native costs.
    proposals = []
    for structure in player['structures']:
        old = {'Mine': 'mine', 'TradingStation': 'trading_station',
               'ResearchLab': 'research_lab'}.get(kind(structure['kind']))
        if old is None:
            continue
        for a, b in _edges(faction):
            if a != old or getattr(current, b) == LIMITS[b]:
                continue
            counts = asdict(current)
            counts[a] -= 1
            counts[b] += 1
            remaining = distance_to(Buildings(**counts), target, faction)
            if remaining is None or remaining >= distance:
                continue
            names = {'trading_station': ('TradingStation',), 'research_lab': ('ResearchLab',),
                     'planetary_institute': ('PlanetaryInstitute',), 'academy': ('Science', 'Qic')}
            for name in names[b]:
                proposals.append(Goal(f'BGG-funding-{name}@{structure["hex"]}',
                                      'upgrade', structure['hex'], name))
    funded = set()
    for goal in proposals:
        check_time(deadline)
        i = select_goal(env, snapshot, scores, goal, policies, deadline)
        if i is None or snapshot['candidates'][i]['action']['type'] not in (
                'FreeAction', 'PowerAction', 'AcademyQicAction', 'TechTileSpecialAction'):
            continue
        after = json.loads(env.fork(snapshot['decision_id'], i).snapshot_json())
        resources = after['state']['players'][actor]['resources']
        need = funding_need(snapshot, goal)
        if any(player['resources'][key] < amount and resources[key] > player['resources'][key]
               for key, amount in need.items()):
            funded.add(i)
    return best_index(scores, funded) if funded else fallback
