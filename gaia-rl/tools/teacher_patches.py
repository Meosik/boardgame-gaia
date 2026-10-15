"""Opt-in correctness patches for the shared teacher trees, applied in-process.

Nothing under a teacher tree is edited; the frozen tree stays byte-identical. A teacher
spec selects a patched factory (e.g. `teacher_patches:symmetric_pass`), so results of
patched and unpatched teachers are never mixed silently.

symmetric_pass — `four_factions.value.potential` counted two things a player collects
when passing only in states where the player had *already* passed:

- the next income of the booster taken at the pass (`.7 x` its income value), and
- the held booster's pass VP (e.g. booster 6: 3 VP per unspent Gaiaformer).

An unpassed player will pass this round too and collect both, so every pass looked
2-7 points better than any other action (cycle 017: the Pass score equalled exactly that
term). The patch adds the same two terms to unpassed action-phase states: the held
booster's pass VP at the current board, and the best booster still in the pool. Both
are rule facts; no new coefficient is introduced (the income term reuses potential's own).
"""
import json

from four_factions import value as _value

_original = getattr(_value.potential, '__wrapped__', _value.potential)
RESOURCE_KEYS = ('ore', 'credits', 'knowledge', 'qic')
# Engine `round_booster_pass_vp`: booster id -> (counter, VP per unit).
BOOSTER_PASS = {1: ('labs', 3), 3: ('mines', 1), 4: ('large', 4), 6: ('formers', 3), 7: ('ts', 2),
                10: ('MostPlanetTypes', 1), 11: ('MostGaiaPlanets', 1), 14: ('MostDeepSpaceSectors', 2)}


def booster_pass_vp(state, player):
    """VP the held booster awards when `player` passes now (engine `round_booster_pass_vp`)."""
    booster = player.get('booster')
    if booster not in BOOSTER_PASS:
        return 0
    counter, per_unit = BOOSTER_PASS[booster]
    if counter == 'formers':
        count = max(0, player['gaiaformers_total']-player['resources']['spent_gaia_formers'])
    elif counter.startswith('Most'):
        from research_plans.value import final_metric
        count = final_metric(state, player, counter)
    else:
        from integrated.features import counters
        count = counters(state, player)[counter]
    return per_unit*count


def booster_income_value(booster):
    income = _value.INCOME['boosters'].get(str(booster), [0]*7)
    return .7*(_value.materials(dict(zip(RESOURCE_KEYS, income[:4]))) + .5*income[4] + .4*income[5])


def _action_phase(state):
    phase = state['phase']
    return isinstance(phase, dict) and 'ActionPhase' in phase or phase == 'ActionPhase'


def symmetric_potential(state, actor, **kwargs):
    result = _original(state, actor, **kwargs)
    player = state['players'][actor]
    if state['round'] < 1 or player['passed'] or not _action_phase(state):
        return result
    result += booster_pass_vp(state, player)
    if 6-state['round'] > 0:
        result += max((booster_income_value(b) for b in state['boosters']), default=0)
    return result


symmetric_potential.__wrapped__ = _original


def install_symmetric_pass():
    """Rebind `potential` wherever the tree imported it by name."""
    import sys
    for module in list(sys.modules.values()):
        bound = getattr(module, 'potential', None)
        if bound in (_original, symmetric_potential):
            if getattr(module, '__name__', '').split('.')[0] in ('four_factions', 'faction_teachers'):
                module.potential = symmetric_potential
    _value.potential = symmetric_potential


def symmetric_pass(seed, **kwargs):
    """Teacher factory: frozen A's TimedPreparationTeacher with the symmetric pass patch."""
    import four_factions.preparation   # noqa: F401  (import every user of `potential` first)
    import four_factions.teacher       # noqa: F401
    import four_factions.quick         # noqa: F401
    from four_factions.timed import TimedPreparationTeacher
    install_symmetric_pass()
    return TimedPreparationTeacher(seed, **kwargs)


# ── geodens_guide ──────────────────────────────────────────────────────────────────────
# Opt-in, on top of symmetric_pass. Uses the uiqoo guides B14 (Geodens) and B19 only to
# ORDER proposals and to lengthen Geodens' own look-ahead; it adds no value term, bonus,
# coefficient or prohibition. At the normal level a decision compares the current choice
# with the first proposal only, so the order decides which plan is examined at all.
#
# 1. Order (B14 §2–3, B19): once the Planetary Institute stands, Terraforming 3 and
#    Navigation 2 come before colonising (B14: "테라포밍을 시작하는 라운드에 테라포밍 3단계"),
#    then new-type colonies cheapest first (terraform steps at the current level plus the
#    QIC needed for range; a Gaia planet counts its QIC). From round 4, the next AI level
#    (B14 §3.3: QIC actions every round from round 4). Before the PI, the tree's existing
#    "PI, then a new type" plans keep their place, now cheapest target first.
# 2. Look-ahead: Geodens pays for terraforming now and is repaid by the PI's 3 knowledge per
#    new type and later incomes, so Geodens decisions compare routes at the second income
#    boundary (the frozen teacher's own horizon) while other seats keep the configured one.

GEODENS_TWO_INCOMES = frozenset({'Geodens'})
GUIDE = ('B14', 'B19')


def _colony_cost(state, player, coord):
    """(reachable now?, ore-equivalent steps + QIC) for building on `coord`; facts only."""
    from economy.teacher import RING, path_distance
    from four_factions.value import navigation
    planet = state['board']['hexes'][coord]['planet']
    starts = [s['hex'] for s in player['structures']]
    qic = max(0, (path_distance(state, starts, coord)-navigation(player)+1)//2)
    kind = planet['planet_type']
    if kind == 'Gaia':
        steps, qic = 0, qic+1
    elif kind in RING:
        from faction_teachers.profiles import profiles
        home = profiles()[player['faction']].home
        gap = abs(RING.index(home)-RING.index(kind))
        steps = min(gap, 7-gap)
    else:
        steps = 3   # Asteroid / ProtoPlanet / Lost planet: not a ring colour; examined last
    return (qic > player['resources']['qic'], steps+qic)


def _target_coord(goal):
    for step in (goal, *goal.steps):
        if step.family == 'faction-action' and step.target == 'Build' and step.coord:
            return step.coord
    return None


def geodens_goals(snapshot, original):
    from four_factions.preparation import Goal
    state, actor = snapshot['state'], snapshot['player']
    player = state['players'][actor]
    if player['faction'] != 'Geodens':
        return original
    tracks = player['research_tracks']
    pi = any(s['kind'] == 'PlanetaryInstitute' for s in player['structures'])
    colonies = [g for g in original if _target_coord(g)]
    others = [g for g in original if not _target_coord(g)]
    colonies.sort(key=lambda g: _colony_cost(state, player, _target_coord(g)))
    research = []
    if pi:
        if tracks['terraforming'] < 3:
            research.append(Goal('Geodens-Terraforming-3', 'research', target='Terraforming', level=3,
                                 sources=GUIDE))
        if tracks['navigation'] < 2:
            research.append(Goal('Geodens-Navigation-2', 'research', target='Navigation', level=2,
                                 sources=GUIDE))
    if state['round'] >= 4 and tracks['ai'] < 5:
        research.append(Goal(f'Geodens-ArtificialIntelligence-{tracks["ai"]+1}', 'research',
                             target='ArtificialIntelligence', level=tracks['ai']+1, sources=GUIDE))
    return research + colonies + others


def install_geodens_guide():
    import four_factions.preparation as preparation
    import faction_teachers.paths as paths
    original_goals = getattr(paths.goals, '__wrapped__', paths.goals)

    def goals(snapshot):
        return geodens_goals(snapshot, original_goals(snapshot))
    goals.__wrapped__ = original_goals
    paths.goals = goals

    original_rollout = getattr(preparation.rollout, '__wrapped__', preparation.rollout)

    def rollout(env, snapshot, *args, **kwargs):
        faction = snapshot['state']['players'][snapshot['player']]['faction']
        if faction not in GEODENS_TWO_INCOMES:
            return rollout.__wrapped__(env, snapshot, *args, **kwargs)
        configured = preparation.reached_horizon   # budget_teacher.set_horizon may wrap it
        preparation.reached_horizon = getattr(configured, '__wrapped__', configured)
        try:
            return rollout.__wrapped__(env, snapshot, *args, **kwargs)
        finally:
            preparation.reached_horizon = configured
    rollout.__wrapped__ = original_rollout
    preparation.rollout = rollout


def geodens_guide(seed, **kwargs):
    """Teacher factory: symmetric_pass plus the Geodens proposal order and look-ahead."""
    teacher = symmetric_pass(seed, **kwargs)
    install_geodens_guide()
    return teacher


# Rejected cycles 019 (calibrated_value), 021 (family/xenos rotation) and 022 (quartet_guide)
# were removed on 2026-10-09; their code is in git history before that date.

# ── booster_lookahead ──────────────────────────────────────────────────────────────────
# Opt-in, on top of geodens_guide. A booster is chosen when passing (and once in setup), but
# (1) at the normal level only the current choice and ONE plan are compared, so other boosters
# are never rolled out, and (2) a comparison stops at the next income, before the new booster
# is ever used, so its special action (1 terraform, +3 range, ...) and its next round's pass VP
# cannot show. When the best-ranked root move is a booster choice, this proposes the other
# boosters first (best-ranked first) and compares every route of THAT decision at the second
# income boundary, i.e. through the round played with the booster. No value is added.

_booster = {'scores': {}, 'flag': None}


def _decision_key(snapshot):
    import json
    return json.dumps([snapshot['decision_id'], snapshot['steps']])


def _booster_choice(candidate):
    action = candidate.get('action', {})
    return isinstance(action, dict) and (
        (action.get('type') == 'Pass' and action.get('booster_id') is not None)
        or action.get('type') == 'SelectStartingBooster')


def decision_horizon(snapshot):
    """2 for a booster decision prepared by booster_goals, else None (configured horizon)."""
    return 2 if _booster['flag'] == _decision_key(snapshot) else None


def booster_goals(snapshot, goals):
    from four_factions.preparation import Goal, best_index, blocked
    key = _decision_key(snapshot)
    scores = _booster['scores'].get(key)
    if scores is None:
        return goals
    control = best_index(scores, range(len(scores)))
    if control is None or not _booster_choice(snapshot['candidates'][control]):
        if _booster['flag'] == key:
            _booster['flag'] = None
        return goals
    _booster['flag'] = key
    alternatives = sorted((i for i, c in enumerate(snapshot['candidates'])
                           if i != control and _booster_choice(c) and not blocked(scores[i])),
                          key=lambda i: (-scores[i][0], i))
    return [Goal(f'booster-{i}', 'root', first=i) for i in alternatives[:3]] + goals


def install_booster_lookahead():
    import four_factions.preparation as p
    if not getattr(p.Policies.rank, '_booster', False):
        original_rank = p.Policies.rank

        def rank(self, env, snapshot):
            scores = original_rank(self, env, snapshot)
            store = _booster['scores']
            store[_decision_key(snapshot)] = scores
            while len(store) > 8:
                store.pop(next(iter(store)))
            return scores
        rank.__wrapped__ = original_rank
        rank._booster = True
        p.Policies.rank = rank
    original_goals_for = getattr(p.goals_for, '__wrapped__', p.goals_for)
    if not getattr(p.goals_for, '_booster', False):
        inner_goals_for = p.goals_for

        def goals_for(snapshot, **kwargs):
            return booster_goals(snapshot, inner_goals_for(snapshot, **kwargs))
        goals_for.__wrapped__ = original_goals_for
        goals_for._booster = True
        p.goals_for = goals_for
    if not getattr(p.rollout, '_booster', False):
        inner_rollout = p.rollout

        def rollout(env, snapshot, *args, **kwargs):
            if decision_horizon(snapshot) != 2:
                return inner_rollout(env, snapshot, *args, **kwargs)
            configured = p.reached_horizon
            p.reached_horizon = getattr(configured, '__wrapped__', configured)
            try:
                return inner_rollout(env, snapshot, *args, **kwargs)
            finally:
                p.reached_horizon = configured
        rollout.__wrapped__ = getattr(inner_rollout, '__wrapped__', inner_rollout)
        rollout._booster = True
        p.rollout = rollout


def _install_booster_search_scope():
    # Live decisions start from a fresh native environment (decision id 0, step 0), so the
    # per-decision key repeats; the flag and stored scores must not outlive one search.
    import four_factions.preparation as p
    if getattr(p.search, '_booster', False):
        return
    inner_search = p.search

    def search(*args, **kwargs):
        try:
            return inner_search(*args, **kwargs)
        finally:
            _booster['flag'] = None
            _booster['scores'].clear()
    search._booster = True
    search._parallel = getattr(inner_search, '_parallel', False)
    p.search = search


def booster_lookahead(seed, **kwargs):
    """Teacher factory: geodens_guide plus booster alternatives compared through the next round."""
    teacher = geodens_guide(seed, **kwargs)
    install_booster_lookahead()
    _install_booster_search_scope()
    return teacher


# ── distinct_search ────────────────────────────────────────────────────────────────────
# Opt-in, on top of geodens_guide. Three search-scope changes found in the lab 027 worst
# game (pair-004/game-0-A01); no value term or coefficient is added, the rollout decides.
#
# 1. Distinct first moves. Several proposals often start with the same move (frame 10:
#    three of four comparisons were booster 13), so the budget never reached another
#    candidate. A comparison whose first move was already rolled out reuses that result,
#    and the budget counts distinct first moves (budget_teacher.count_distinct_firsts).
#    The current choice is always rolled out itself.
# 2. Openings follow value. In round 1 a BGG opening route was taken even when another
#    completed comparison forecast more (frame 15: 122.8 vs 154.4). An opening is now
#    taken only when its comparison has the highest completed value.
# 3. Order of root alternatives. The root ranking prices only the immediate state change,
#    so choices whose gain comes later (a booster with an action, an action tech tile,
#    exploring a ship, an upgrade that raises power value and income) rank last and were
#    never compared. They are now compared first among root alternatives (order only).
# 4. Setup horizon. With a one-income horizon a setup decision (placement, starting booster)
#    stopped at the round-1 income, before a single round-1 move: every placement scored the
#    same and a booster was worth only its income, never its action. Setup decisions now
#    compare through round 1 (stop at the round-2 income), for every route alike.
# 5. Equal continuations. The current choice is valued as the best of every plan that starts
#    with it (BGG openings, academy and research plans), a root alternative by one default
#    continuation, so the incumbent won by construction (frame 10: 158 vs 143). A root
#    alternative is now also rolled out under the best plan found so far and keeps the better.
# 6. Opening order. A BGG row is only the end-of-round-1 inventory (e.g. 1AC+2M), not an
#    order; the tree reached it with the cheapest-looking step, so mines always came first.
#    Each opening is now also proposed "upgrades first" (an upgrade toward the inventory
#    before a new mine, so the larger building collects power sooner), and the comparison
#    decides which order to play.

UPGRADES_FIRST = 'upgrades-first'

ACTION_BOOSTERS = frozenset({5, 8, 12})   # Gaia formation, range +3, terraform step
ACTION_TECH_TILES = frozenset({10})       # engine tech_tile_special_action_effect
LATER_GAIN_TYPES = frozenset({'ExploreSpaceship', 'Upgrade'})

_distinct = {'snapshot': None, 'results': {}, 'plan': None, 'opening': {}}


def _better(a, b):
    """The completed comparison with the higher value (a on ties)."""
    if not (b and b.get('complete')):
        return a
    if not (a and a.get('complete')) or b['value'] > a['value']:
        return b
    return a


def later_gain(candidate):
    """True for a choice whose gain the immediate root ranking does not see."""
    action = candidate.get('action') or {}
    kind = action.get('type')
    if kind in ('SelectStartingBooster', 'Pass'):
        return action.get('booster_id') in ACTION_BOOSTERS
    return kind in LATER_GAIN_TYPES


def _later_gain_rank(candidate):
    tile = ((candidate.get('action') or {}).get('tech_tile_choice') or {}).get('tile')
    return (not later_gain(candidate), tile not in ACTION_TECH_TILES)


def order_roots(snapshot, roots):
    """Later-gain alternatives first, the ranking's order kept inside each group."""
    return sorted(roots, key=lambda goal: _later_gain_rank(snapshot['candidates'][goal.first]))


def upgrades_first_scores(snapshot, scores):
    """Lift unblocked upgrades above every other move; their own order is kept."""
    from current_actions.conservation import blocked
    top = max((s[0] for s in scores), default=0)
    lifted = list(scores)
    for i, candidate in enumerate(snapshot['candidates']):
        if candidate['action'].get('type') == 'Upgrade' and not blocked(scores[i]):
            lifted[i] = (scores[i][0]+abs(top)+1000, *scores[i][1:])
    return lifted


def value_first_forecast(original, rows, remembered, comparisons):
    """Pick an opening only from the comparisons with the highest completed value."""
    import math
    values = [c['value'] for c in comparisons if c.get('complete')
              and isinstance(c.get('value'), (int, float)) and math.isfinite(c['value'])]
    if not values:
        return None
    best = max(values)
    return original(rows, remembered, [c for c in comparisons if c.get('complete') and c.get('value') == best])


def install_distinct_search(value_openings=True):
    import budget_teacher
    import bgg_openings.planning as planning
    import four_factions.preparation as p
    budget_teacher.count_distinct_firsts(True)
    if value_openings and not getattr(planning.select_forecast, '_distinct', False):
        inner_forecast = planning.select_forecast

        def select_forecast(rows, remembered, comparisons):
            return value_first_forecast(inner_forecast, rows, remembered, comparisons)
        select_forecast._distinct = True
        planning.select_forecast = select_forecast
    inner_rollout = getattr(p.rollout, '_distinct_inner', p.rollout)
    if not getattr(p.select_goal, '_distinct', False):
        inner_select = p.select_goal

        def select_goal(env, snapshot, scores, goal, policies, deadline):
            from dataclasses import replace
            if goal.family == 'bgg-opening' and goal.payoff == UPGRADES_FIRST:
                scores = upgrades_first_scores(snapshot, scores)
            first = inner_select(env, snapshot, scores, goal, policies, deadline)
            if goal.family != 'bgg-opening' or goal.payoff is not None or snapshot is not _distinct['snapshot']:
                return first
            # Same inventory, upgrades first: both orders compared in one slot, the better kept.
            ordered = replace(goal, payoff=UPGRADES_FIRST)
            other = inner_select(env, snapshot, upgrades_first_scores(snapshot, scores), ordered, policies, deadline)
            if other == first:
                return first
            own = inner_rollout(env, snapshot, first, goal, policies, deadline, capture_r1=True)
            alternative = inner_rollout(env, snapshot, other, ordered, policies, deadline, capture_r1=True)
            if _better(own, alternative) is alternative:
                first, own = other, {**alternative, 'opening_order': UPGRADES_FIRST}
            _distinct['opening'][(goal.name, first)] = own
            return first
        select_goal._distinct = True
        p.select_goal = select_goal
    if not getattr(p.interleave_families, '_distinct', False):
        inner_interleave = p.interleave_families

        def interleave_families(items, family):
            snapshot = _distinct['snapshot']
            if snapshot is not None and items and all(getattr(g, 'family', None) == 'root' for g in items):
                items = order_roots(snapshot, items)
            return inner_interleave(items, family)
        interleave_families._distinct = True
        p.interleave_families = interleave_families
    if not getattr(p.rollout, '_distinct', False):
        def rollout(env, snapshot, first, goal, policies, deadline, *args, **kwargs):
            import copy
            from dataclasses import replace
            results = _distinct['results']
            opening = _distinct['opening'].pop((goal.name, first), None)
            if opening is None and goal.family != 'current' and first in results:
                return copy.deepcopy(results[first])
            configured = p.reached_horizon
            if snapshot['state']['round'] == 0:
                # Unwrapped = the tree's own two-income horizon: through round 1.
                p.reached_horizon = getattr(configured, '__wrapped__', configured)
            try:
                result = opening or inner_rollout(env, snapshot, first, goal, policies, deadline, *args, **kwargs)
                plan = _distinct['plan']
                if goal.family == 'root' and plan is not None and _distinct['snapshot'] is not None:
                    planned = inner_rollout(env, snapshot, first, replace(plan[1], first=first), policies,
                                            deadline, *args, **kwargs)
                    result = _better(result, planned)
            finally:
                p.reached_horizon = configured
            if _distinct['snapshot'] is not None:
                results.setdefault(first, copy.deepcopy(result))
                best = _distinct['plan']
                if (goal.family not in ('current', 'root') and result.get('complete')
                        and (best is None or result['value'] > best[0])):
                    _distinct['plan'] = (result['value'], goal)
            return result
        rollout.__wrapped__ = getattr(inner_rollout, '__wrapped__', inner_rollout)
        rollout._distinct_inner = inner_rollout
        rollout._distinct = True
        rollout._parallel = getattr(inner_rollout, '_parallel', False)
        p.rollout = rollout
    if not getattr(p.search, '_distinct', False):
        inner_search = p.search

        def search(env, snapshot, *args, **kwargs):
            # One decision's cache; live decisions restart at decision id 0.
            _distinct.update(snapshot=snapshot, results={}, plan=None, opening={})
            try:
                return inner_search(env, snapshot, *args, **kwargs)
            finally:
                _distinct.update(snapshot=None, results={}, plan=None, opening={})
        search._distinct = True
        search._parallel = getattr(inner_search, '_parallel', False)
        p.search = search


def distinct_search(seed, **kwargs):
    """Teacher factory: geodens_guide plus distinct first moves, value-led openings, later-gain order."""
    teacher = geodens_guide(seed, **kwargs)
    install_distinct_search()
    return teacher


def distinct_search_openings(seed, **kwargs):
    """distinct_search without change 2: a matching BGG opening still overrides the value.

    The comparisons stop at the first income, before a PI or lab opening repays its cost,
    so the value may undervalue the opening (cycle 030 checks both variants).
    """
    teacher = geodens_guide(seed, **kwargs)
    install_distinct_search(value_openings=False)
    return teacher


# ── guide_values ───────────────────────────────────────────────────────────────────────
# Opt-in, on top of geodens_guide. User decision (2026-10-05): the uiqoo guides' common
# material is applied with its numbers. `potential` (Terrans, Taklons, Geodens: root
# ranking and rollout leaves) keeps every term it had, but prices resources, power, income,
# boosters, planets and explored ships with tools/guide_value.py (LF01/LF02 charge values,
# 1 VP = 1.5 charges at rounds 4-5). Its old hand prices were: QIC 2.5 VP (guide 4.7),
# knowledge 2.0 (2.7), credits 1.2 (0.8), income x0.7 per round left, a 2-VP structure /
# ship term, and stock resources at 1/3 VP from the first decision of round 6.
# Xenos (the legacy contextual teacher) gets the same resource prices at the 1.5 anchor.


_guide = {'qic_reach': True,            # False: install_guide_r1 (QIC priced once)
          'track_income': True,         # False: install_guide_r1 (research levels priced once)
          'lf_tables': False,           # True: guide_r1_charge3_lf (ships, green tokens, pass tiles)
          'lf_tiles': False,            # True: guide_r1_charge3_lf_tiles (standard tiles 6, 8, 12)
          'charge_vp': False,           # True: guide_r1_charge3_lf_tiles (VP held kept in charge_value)
          'lf_more': False,             # True: guide_r1_charge3_lf_more (see lf_more_value)
          'academy_r1': False,          # True: guide_r1_charge3_lf_more_ac (see academy_r1)
          'sheden_r1': False,           # True: guide_r1_charge3_lf_more_sh (see SHEDEN_OPENINGS)
          'lf_frozen': False,           # True: guide_r1_charge3_lf_more_vm_lf (see install_lf_frozen)
          'ts_chain_direct': False,     # True: guide_r1_charge3_lf_more_vm_lf_ts (see ts_chain_scores)
          'knowledge_spend': False,     # True: guide_r1_charge3_lf_more_vm_lf_ts (see knowledge_spend_scores)
          'ship_setup': False,          # True: guide_r1_charge3_lf_more_vm_lf_ts (see ship_setup_scores)
          'reach_plus': False,          # True: ..._vm_lf_ts_reach (see install_reach)
          'setup_roots': False,         # True: ..._vm_lf_ts_reach (see setup_search)
          'setup_soft': False,          # True: ..._vm_lf_ts_reach (opponent-adjacent starts first, none blocked)
          'research_focus': False,      # True: ..._vm_lf_ts_reach (see research_focus_scores)
          'former_use': False,          # True: ..._vm_lf_ts_former (see install_former_use)
          'research_when': False,       # True: ..._vm_lf_ts_when (see research_when_track)
          'contested_first': False,     # True: ..._vm_lf_ts_when (see contested_first_scores)
          'ship_when': False,           # True: ..._vm_lf_ts_when (see ship_when_scores)
          'research_defend': False,     # True: ..._vm_lf_ts_ships_defend (see research_defend_track)
          'leech_when': False,          # True: install_when(leech=True) (see leech_when_scores)
          'artifact_when': False,       # the next four: install_when(not_yet=...) (see _not_yet)
          'mine_stock': False,
          'taklons_pi': False,
          'twilight_knowledge': False,
          'burn_when': False,           # the next two: ..._when_all_tech (see _not_yet)
          'terrans_former': False,
          'academy_kind': False,        # True: install_when(academy=True) (see academy_kind_scores)
          'tech_when': False,           # True: ..._when_all_tech (see tech_when_scores)
          'fed_upgrade': False,         # GUIDE_MORE: ..._when_all_tech (see _not_yet_more, guide_more_scores)
          'ts_excess': False,
          'rebellion_ts': False,
          'knowledge_action': False,
          'qic_late': False,
          'rebellion_qic': False,
          'fed_cap': False,
          'leech_lf': False,
          'ship_first': False,
          'qic_round6': False,
          'fed_design': False,
          'fed_token': False,
          'pass_booster': False,
          'mines_kept': False,          # GUIDE_REST: ..._when_all_tech (see _not_yet_more, guide_more_scores)
          'ore_terraform': False,
          'artifact_vp': False,
          'academy_ahead': False,
          'contested_order': False,
          'gaia_tile': False,           # GUIDE_LAST: ..._when_all_tech (see _tech_wanted, _guide_last)
          'round_goal': False,
          'final_mission': False,
          'former_booster': False,      # GUIDE_FINAL: ..._when_all_tech (see _not_yet_more, setup_step_scores)
          'late_ship': False,
          'mine_tile': False,
          'setup_step1': False,
          'track_set': False,           # ..._when_all_tech (see FACTION_TRACKS)
          'terrans_gaia_cond': False,   # ..._when_all_tech (see _early_terrans_gaia)
          'faction_more': False,        # ..._when_all_tech (see _faction_hold)
          'adv_immediate': False,       # ..._when_all_tech (see lf_advanced_option)
          'r1_basics': False,           # ..._when_all_tech (see guide_more_scores, SH3-01/03)
          'tokens_lf': False,           # ..._when_all_tech (see lf_power_value)
          'hold_no_pass': False}        # ..._when_all_tech (see not_yet_scores)


_POWER_VALUE = {'Mine': 1, 'TradingStation': 2, 'ResearchLab': 2, 'PlanetaryInstitute': 3, 'Academy': 3}


def _structure_power(structure):
    kind = structure['kind']
    kind = next(iter(kind)) if isinstance(kind, dict) else kind
    return _POWER_VALUE.get(kind, 0)


def federation_progress(state, player):
    """User (2026-10-07): progress toward the next federation. The largest group of unfederated
    buildings (chained within 2 hexes, one satellite apart) is worth its share of power value 7
    of a base federation token (LF01, 18 charges). A formed federation moves those buildings out
    and its token reward into VP/stock."""
    import guide_value as gv
    federated = set(map(str, player.get('federated_hexes') or []))
    left = [s for s in player['structures'] if str(s['hex']) not in federated and _structure_power(s)]
    best, seen = 0, set()
    for i in range(len(left)):
        if i in seen:
            continue
        group, todo = 0, [i]
        seen.add(i)
        while todo:
            j = todo.pop()
            group += _structure_power(left[j])
            for k in range(len(left)):
                if k not in seen and _value.distance(left[j]['hex'], left[k]['hex']) <= 2:
                    seen.add(k)
                    todo.append(k)
        best = max(best, group)
    return gv.to_vp(state, gv.FEDERATION_TOKEN*min(best, gv.FEDERATION_POWER)/gv.FEDERATION_POWER)


def leech_value(state, player):
    """User (2026-10-07): power charges still to come from neighbours — each opponent with a
    building within 2 hexes of ours, LEECH_PER_NEIGHBOR charges for every round left."""
    import guide_value as gv
    mine = [s['hex'] for s in player['structures']]
    neighbors = sum(any(_value.distance(a['hex'], b) <= 2 for a in other['structures'] for b in mine)
                    for other in state['players'] if other is not player)
    rounds = 7-max(state['round'], 1)
    return gv.to_vp(state, gv.LEECH_PER_NEIGHBOR*min(neighbors, gv.LEECH_NEIGHBORS_MAX)*rounds)


def lf_research_options(state, player):
    """four_factions.value.research_options at the LF prices, with advanced tiles valued by
    lf_advanced_option."""
    import copy
    import guide_value as gv
    v = _value
    horizon = max(0, 6-state['round'])
    if not horizon:
        return 0.0
    result = 0.0
    current = v.production(state, player, include_booster=False)
    if player['resources']['knowledge']+current[2] >= 4:
        for track in ('economy', 'science'):
            if player['research_tracks'][track] != 1:
                continue
            after = copy.deepcopy(player)
            after['research_tracks'][track] = 2
            future = v.production(state, after, include_booster=False)
            delta = {k: max(0, future[i]-current[i]) for i, k in enumerate(v.RESOURCE_KEYS)}
            result += .5*horizon*gv.materials(state, delta)
    active = set(player['tech_tiles'])-set(player['covered_tech_tiles'])
    if player['federation_tokens'] and active:
        tracks = ('terraforming', 'navigation', 'ai', 'gaia', 'economy', 'science')
        options = []
        for track, tile in zip(tracks, state['research_board']['advanced_tech_tiles']):
            if tile is not None:
                proximity = (0, 0, .1, .25, .4, .4)[player['research_tracks'][track]]
                options.append(proximity*lf_advanced_option(state, player, tile))
        result += max(options, default=0)
    return result


def standard_tiles_value(state, player, active, horizon):
    """User (2026-10-07): standard tiles 6 (big buildings' power +1) and 12 (+1 range) have no
    standing value; their effect shows in the round-4 rollout. Tile 8 (3 VP per mine built on a
    Gaia planet) pays only for mines built after it: the planets now being Gaia-formed plus the
    one or two more the player will still form (as for pass tiles). Replaces the frozen
    0.5 VP x rounds left for these three tiles."""
    if 8 not in active or not horizon:
        return 0.0
    more = 2 if horizon >= 3 else 1
    return 3*(player.get('gaiaformers_deployed', 0)+more)


def lf_advanced_option(state, player, tile):
    """Pass tiles (user 2026-10-07): VP per pass x (current count + the one or two more the
    player will still build) x passes left, without the frozen 0.6 discount. Other tiles keep
    the frozen advanced_option."""
    import guide_value as gv
    from integrated.features import counters, PASS, EVENT, RESOURCE_ACTIONS
    horizon = max(0, 6-state['round'])
    if _guide['lf_more'] and tile in EVENT:
        # one or two triggers a round (EVENT_USES_PER_ROUND) for this round and those left
        return gv.EVENT_USES_PER_ROUND*(horizon+int(not player['passed']))*EVENT[tile][1]
    if _guide['lf_more'] and tile in RESOURCE_ACTIONS:
        available = tile not in player['advanced_tech_tile_special_actions_used_this_round']
        uses = horizon + int(available and not player['passed'])
        return uses*gv.to_vp(state, gv.SPECIAL_ACTION[tile])
    if _guide['adv_immediate'] and tile not in player['advanced_tech_tiles']:
        from integrated.features import IMMEDIATE
        if tile in IMMEDIATE:
            # adv_immediate (user 2026-10-15 "다 넣어"; C013 "획득 당시 실제 보드 상태로 가치를 판단", SH5-01
            # "즉발 고급 기술은 평균 약 12점"): an immediate tile not yet held is worth what it would pay
            # now (the frozen option counted 0); a held one has paid already.
            counter, per_unit = IMMEDIATE[tile]
            return per_unit*counters(state, player)[counter]
    if tile not in PASS:
        return _value.advanced_option(state, player, tile)
    passes = horizon + int(not player['passed'])
    if not passes:
        return 0.0
    counter, vp = PASS[tile]
    more = 2 if passes >= 3 else 1
    return passes*vp*(counters(state, player)[counter]+more)


def _track_income(state, player):
    """The Economy and Science tracks' share of the income vector (four_factions.value.production)."""
    from four_factions.value import INCOME
    economy = INCOME['economy'][state['research_board']['economy_research_tile_side']][player['research_tracks']['economy']]
    science = INCOME['science'][player['research_tracks']['science']]
    return [a+b for a, b in zip(economy, science)]


def guide_potential(state, actor, *, home=None, guide_tracks=False):
    import guide_value as gv
    v = _value
    phase = state['phase']
    if isinstance(phase, dict) and 'Ended' in phase:
        return float(dict(phase['Ended']['final_scores'])[actor])
    player = state['players'][actor]
    horizon = max(0, 6-state['round'])
    result = player['vp'] + v.standings(state, actor)
    result += gv.research_value(state, player)
    power = player['resources']['power']
    if _guide['lf_frozen']:
        result += gv.materials(state, player['resources']) + lf_power_value(state, player)
    else:
        result += gv.materials(state, player['resources']) + gv.power_value(state, player)
    if horizon:
        # The frozen teacher's own Brainstone term (kept); its Gaia-area term unless lf_frozen.
        result += {'Area1': .5, 'Area2': 1.5, 'Area3': 4.2, 'Gaia': 0, None: 0}[power['brainstone']]
        if not _guide['lf_frozen']:
            result += (.6 if player['faction'] == 'Terrans' else .2)*power['gaia_forming']
    income = v.production(state, player, include_booster=False)
    if not _guide['track_income']:
        # research_value already prices every level at 16 charges "for the research advance"
        # (LF01 §2.4), so the Economy/Science levels' income is not counted a second time.
        income = [a-b for a, b in zip(income, _track_income(state, player))]
    result += gv.incomes_value(state, income)
    if horizon and (player['passed'] or state['round'] == 0):
        result += _booster_value(state, player, player['booster'])
    elif horizon and _action_phase(state):
        # Symmetric pass (cycle 017): an unpassed player also passes this round.
        result += max((_booster_value(state, player, b) for b in state['boosters']), default=0)
    if state['round'] >= 1 and not player['passed'] and _action_phase(state):
        result += booster_pass_vp(state, player)
    result += gv.planet_value(state)*len(player['structures'])
    if _guide['lf_tables']:
        result += gv.ships_value(state, player) + gv.green_tokens_value(state, player)
    else:
        result += gv.ship_value(state)*len(player['explored_ships'])
    if (not _guide['lf_frozen'] and player['faction'] == 'Taklons'
            and any(s['kind'] == 'PlanetaryInstitute' for s in player['structures'])):
        owners = {b['owner'] for c, cell in state['board']['hexes'].items()
                  if any(v.distance(c, s['hex']) <= 2 for s in player['structures'])
                  for b in cell['structures'] if b['owner'] != actor}
        result += horizon*min(2, len(owners))
    if _guide['lf_frozen']:
        result += colony_options(state, player, home=home)
        result += lf_research_options(state, player) + federation_progress(state, player)
        result += lf_leech_value(state, player)
        return result + _guide_tiles(state, player, horizon)
    reach = player
    if not _guide['qic_reach']:
        # The guide's QIC price already includes its range use; count planets reachable
        # without spending QIC so a QIC is not paid twice (free_conversions note).
        reach = {**player, 'resources': {**player['resources'], 'qic': 0}}
    if guide_tracks:
        from four_factions.track_guidance import expansion_potential
        result += v.gaia_value(state, reach) + expansion_potential(state, reach)
    else:
        result += v.gaia_value(state, reach) + (v.expansion_value(state, reach, home=home) if horizon else 0)
    if _guide['lf_more']:
        result += lf_research_options(state, player)
        result += federation_progress(state, player) + leech_value(state, player)
    else:
        result += v.research_options(state, player)
    return result + _guide_tiles(state, player, horizon)


def _guide_tiles(state, player, horizon):
    """Advanced and standard tech tiles held (the tail of guide_potential)."""
    import guide_value as gv
    advanced = lf_advanced_option if _guide['lf_tables'] else _value.advanced_option
    result = sum(advanced(state, player, tile) for tile in player['advanced_tech_tiles'])
    active = set(player['tech_tiles'])-set(player['covered_tech_tiles'])
    if _guide['lf_tiles']:
        result += standard_tiles_value(state, player, active, horizon)
    else:
        result += .5*horizon*len(active - {2, 3, 5, 4, 7, 9, 11, 13, gv.CHARGE_TILE})
    result += gv.charge_tile_value(state, player)
    return result


guide_potential.__wrapped__ = _original

_resource_value = {'original': None}


def guide_resource_value(player, resources):
    """integrated.features.resource_value at the guide's prices (1 VP = 1.5 charges)."""
    import guide_value as gv
    return sum(gv.CHARGE[k]*amount for k, amount in resources.items())/gv.CHARGES_PER_VP[4]


def install_guide_values():
    import sys
    import integrated.features as features
    known = (_original, symmetric_potential, guide_potential)
    for module in list(sys.modules.values()):
        if getattr(module, '__name__', '').split('.')[0] in ('four_factions', 'faction_teachers'):
            if getattr(module, 'potential', None) in known:
                module.potential = guide_potential
    _value.potential = guide_potential
    original = _resource_value['original'] or features.resource_value
    _resource_value['original'] = original
    for module in list(sys.modules.values()):
        if getattr(module, 'resource_value', None) is original:
            module.resource_value = guide_resource_value


def guide_values(seed, **kwargs):
    """Teacher factory: geodens_guide with the uiqoo guide prices in the state value."""
    import current_actions.teacher    # noqa: F401  (import every user of resource_value first)
    import research_plans.value       # noqa: F401
    teacher = geodens_guide(seed, **kwargs)
    install_guide_values()
    return teacher


# ── uiqoo_openings ─────────────────────────────────────────────────────────────────────
# Opt-in, on top of guide_values. The faction guides' round-1 openings, as end-of-round-1
# inventories (the BGG catalog's own notation), are compared first and in the guide's order;
# the rollout still decides which is played (order only, no value). Geodens keeps
# geodens_guide (B14). Labels count the starting mines (Terrans/Taklons 2, Xenos 3):
#   B04 Terrans §4: 아카데미+광산 "최고의 오프닝" (1AC+1M), 행성 의회+광산+광산 "무난" (1PI+2M),
#       행성 의회+교역소+광산+광산 (1PI+1TS+2M), 연구소+광산+광산 (1RL+2M).
#   B10 Taklons §4: 아카데미+광산+광산 "기본 오프닝" (1AC+2M), 연구소+교역소+광산+광산 (1RL+1TS+2M),
#       연구소+광산×5 (1RL+5M).
#   B15 Xenos §4: 연구소+광산×5 "가장 무난하고 강력" (1RL+5M), 연구소+광산+광산+4정보 (1RL+2M),
#       아카데미+광산+광산 (1AC+2M).
UIQOO_OPENINGS = {
    'Terrans': ('1AC+1M', '1PI+2M', '1PI+1TS+2M', '1RL+2M'),
    'Taklons': ('1AC+2M', '1RL+1TS+2M', '1RL+5M'),
    'Xenos': ('1RL+5M', '1RL+2M', '1AC+2M'),
}


# sheden_r1 (user 2026-10-07, "진행해"): SH4-01/03/05/06/07 (sheden #4 종족 별 추천 빌드, end-of-round-1
# buildings) replace the uiqoo order, Geodens included. 연=RL, 의=PI, 아=AC, 교=TS, N광=N mines
# ("연4광" = RL + 4 mines or more). Rank 1 then rank 2 then rank 3, each in the article's order:
#   Terrans: 연4광, 연교2광 / 의교광광 (1R tech federation only), 연2광.
#   Xenos: 연4광, 연교2광 / 의교광 (1R tech federation only).
#   Taklons: 연4광 / 아2광, 연교2광.
#   Geodens: 의4광, 의교2광 / 의2광 / 연4광, 연교2광 (no terraforming action at all).
# Labels missing from the BGG catalog for a faction are simply never proposed.
_RL4 = ('1RL+4M', '1RL+5M', '1RL+6M')
SHEDEN_OPENINGS = {
    'Terrans': (*_RL4, '1RL+1TS+2M', '1PI+1TS+2M', '1RL+2M'),
    'Xenos': (*_RL4, '1RL+1TS+2M', '1PI+1TS+1M'),
    'Taklons': (*_RL4, '1AC+2M', '1RL+1TS+2M'),
    'Geodens': ('1PI+4M', '1PI+5M', '1PI+1TS+2M', '1PI+2M', *_RL4, '1RL+1TS+2M'),
}


def uiqoo_opening_order(snapshot, goals, remembered=None):
    faction = snapshot['state']['players'][snapshot['player']]['faction']
    order = (SHEDEN_OPENINGS if _guide.get('sheden_r1') else UIQOO_OPENINGS).get(faction)
    if not order:
        return goals
    rank = {label: i for i, label in enumerate(order)}

    def key(item):
        i, goal = item
        return (goal.target != remembered, rank.get(goal.target, len(order)), i)
    return [goal for _, goal in sorted(enumerate(goals), key=key)]


def install_uiqoo_openings():
    import bgg_openings.planning as planning
    original = getattr(planning.goals, '__wrapped__', planning.goals)

    def goals(snapshot, remembered=None):
        return uiqoo_opening_order(snapshot, original(snapshot, remembered), remembered)
    goals.__wrapped__ = original
    planning.goals = goals


def guide_values_openings(seed, **kwargs):
    """Teacher factory: guide_values plus the faction guides' round-1 opening order."""
    teacher = guide_values(seed, **kwargs)
    install_uiqoo_openings()
    return teacher


# ── free_conversions ───────────────────────────────────────────────────────────────────
# Opt-in, on top of guide_values. User (2026-10-06): at the guide prices (QIC 7, ore 4,
# knowledge 4, credits 1.2 charges) a losing conversion is already priced as a loss, so the
# frozen teacher's hand-written conversion bans are lifted and the value decides:
#   - OreToCredit / KnowledgeToCredit were always blocked (current_actions.conservation.FORBIDDEN);
#   - QicToOre was blocked unless the very next action completed a PI, Academy or federation
#     with exactly that ore (four_factions.teacher.critical_proofs, conservation.critical_paths).
# Existing proofs are still returned (and still commit the follow-up), so opening funding that
# relied on them is unchanged. The quick timeout fallback keeps its QicToOre block.
_NOT_BLOCKED = ''  # never equals a snapshot identity: "allowed, no required follow-up"


def install_free_conversions():
    import current_actions.conservation as conservation
    import four_factions.teacher as native
    import resource_plans.funding as funding
    conservation.FORBIDDEN.clear()   # the same set object every importer holds
    paths = getattr(conservation.critical_paths, '__wrapped__', conservation.critical_paths)
    proofs = getattr(native.critical_proofs, '__wrapped__', native.critical_proofs)

    def critical_paths(env, snapshot, index):
        return paths(env, snapshot, index) or {_NOT_BLOCKED: set()}

    def critical_proofs(env, snapshot, index, branch, after):
        return proofs(env, snapshot, index, branch, after) or {_NOT_BLOCKED: set()}
    critical_paths.__wrapped__ = paths
    critical_proofs.__wrapped__ = proofs
    conservation.critical_paths = critical_paths
    funding.critical_paths = critical_paths
    native.critical_proofs = critical_proofs


# ── academy_first ──────────────────────────────────────────────────────────────────────
# User (2026-10-06): a round-1 academy opening needs every resource (the 4-power 2-ore action,
# QIC to ore); a new mine before it spends what the academy needs. While a BGG round-1 target
# still lacks its academy, the opening step tries the upgrade chain and its funding first and
# builds a mine only when no academy progress is found (order only, no value).
def _new_mine(action):
    return action['type'] == 'Build' or action['type'].endswith('RangeBuild')


# academy_r1 (user 2026-10-07, "AC 스타트는 지형 영향을 크게 안 받는다 — 할 수 있는데 자원을 허투루 써서
# 못 짓는다"; 040: 1 round-1 academy in 48 seats, research labs in round 1 almost always). Order
# only, no value:
# 1. While a round-1 BGG target still lacks its academy, only the upgrade chain and the moves that
#    can fund it are tried first (academy_first put only new mines later). Research, Gaia forming,
#    ships and pass come after, when no academy progress is found; a power burn that opens an
#    ore or credit power action counts as funding.
# 2. An opening whose comparison completed round 1 with an academy is selected before the others;
#    among them select_forecast decides as before.
ACADEMY_FUNDING = ('Upgrade', 'FreeAction', 'PowerAction', 'AcademyQicAction', 'TechTileSpecialAction',
                   'ChargePower', 'ChooseIncomeOrder')


def _academy_later(action):
    """Moves put after the academy: new mines, or with _guide['academy_r1'] every move that
    neither upgrades nor funds the upgrade (research, Gaia forming, ships, pass, ...)."""
    if _guide.get('academy_r1'):
        return action['type'] not in ACADEMY_FUNDING
    return _new_mine(action)


def _burn_for_funding(env, snapshot, scores):
    """A power burn that opens a power action paying ore or credits (the 4-power 2-ore action,
    the 7-credit action), checked on the native forks; the smallest such burn."""
    from current_actions.conservation import blocked
    actor = snapshot['player']
    held = snapshot['state']['players'][actor]['resources']
    open_now = {json.dumps(c['action'], sort_keys=True) for c in snapshot['candidates']
                if c['action']['type'] == 'PowerAction'}
    burns = sorted((c['action'].get('count', 0), i) for i, c in enumerate(snapshot['candidates'])
                   if c['action']['type'] == 'FreeAction' and c['action'].get('kind') == 'BurnPower'
                   and not blocked(scores[i]))
    for _, i in burns:
        after = json.loads(env.fork(snapshot['decision_id'], i).snapshot_json())
        if after.get('player') != actor:
            continue
        for j, c in enumerate(after['candidates']):
            if c['action']['type'] != 'PowerAction' or json.dumps(c['action'], sort_keys=True) in open_now:
                continue
            paid = json.loads(env.fork(snapshot['decision_id'], i).fork(after['decision_id'], j)
                              .snapshot_json())['state']['players'][actor]['resources']
            if paid['ore'] > held['ore'] or paid['credits'] > held['credits']:
                return i
    return None


# sheden_r1: SH4-07 Bal'Tak "아2광 (테라포밍 트랙으로 2광석획득)" — the Terraforming level 1 reward is
# 2 ore (gaia-engine/data/research_tracks.toml). When the academy chain is stuck short of ore,
# research Terraforming 0→1 before the fallback. Ore still owed by the chain (rulebook costs):
# academy 6, research lab 3, trading station 2.
def _chain_ore(player, target):
    from bgg_openings.inventory import building_counts
    counts = building_counts(player)
    if counts.research_lab > target.research_lab:
        return 6
    if counts.trading_station > target.trading_station:
        return 9
    return 11


def _terraforming_ore(snapshot, scores, target):
    from current_actions.conservation import blocked
    player = snapshot['state']['players'][snapshot['player']]
    if (player['research_tracks']['terraforming'] != 0
            or player['resources']['ore'] >= _chain_ore(player, target)):
        return None
    for i, c in enumerate(snapshot['candidates']):
        if (c['action']['type'] == 'ResearchAdvance' and c['action'].get('track') == 'Terraforming'
                and not blocked(scores[i])):
            return i
    return None


def install_academy_first():
    import bgg_openings.planning as planning
    from bgg_openings.inventory import building_counts
    from current_actions.conservation import BLOCKED, PREFIX
    from research_plans.teacher import best_index
    original = getattr(planning.select_action, '__wrapped__', planning.select_action)

    def select_action(env, snapshot, scores, target, policies, deadline):
        player = snapshot['state']['players'][snapshot['player']]
        if (snapshot['state']['round'] == 1 and 'ActionPhase' in snapshot['state']['phase']
                and target.academy > building_counts(player).academy):
            masked = [(BLOCKED, PREFIX+'academy first: other spending after the academy')
                      if _academy_later(c['action']) else score
                      for c, score in zip(snapshot['candidates'], scores)]
            i = original(env, snapshot, masked, target, policies, deadline)
            if i is not None and (i != best_index(masked, range(len(masked)))
                                  or snapshot['candidates'][i]['action']['type'] == 'Upgrade'):
                return i
            if _guide.get('academy_r1'):
                i = _burn_for_funding(env, snapshot, masked)
                if i is not None:
                    return i
            if _guide.get('sheden_r1'):
                i = _terraforming_ore(snapshot, masked, target)
                if i is not None:
                    return i
        return original(env, snapshot, scores, target, policies, deadline)
    select_action.__wrapped__ = original
    planning.select_action = select_action


def guide_values_openings_free(seed, **kwargs):
    """Teacher factory: guide_values_openings without the hand-written conversion bans,
    and round-1 academy openings built before new mines."""
    teacher = guide_values_openings(seed, **kwargs)
    install_free_conversions()
    install_academy_first()
    return teacher


# ── guide_r1 ───────────────────────────────────────────────────────────────────────────
# User (2026-10-06), on top of guide_values_openings_free:
# 1. Setup placement next to opponents (LF4-02 "파워를 받는 곳(교역소가 싼 곳)에 자리 잡는 게 함대만큼
#    중요", B10-02 "시작은 남들과 붙는 게 최우선"): a starting structure within distance 2 of an
#    opponent's structure (the engine's cheap trading station range) is preferred: when one
#    exists, isolated starts are not compared (ordering alone lost to setup-comparison noise).
# 2. Terrans Gaia track (B04 §4: 1단계로 두고 3-4라운드까지 상황을 보다가 4-5라운드부터 올려도 된다):
#    in rounds 1-3 a Terrans Gaia research advance ranks below every other move and the Gaia
#    research plans are proposed last. Order only.
# 3. QIC priced once: planets reachable only by spending QIC no longer add to the expansion and
#    Gaia opportunity terms (the guide price of a QIC already includes its range use).
# 4. Research priced once (user 2026-10-06, "다들 경제 트랙만 올린다", 035: Economy+Science 64% of
#    B research in rounds 1-3, Geodens included): every level is already 16 charges in
#    research_value, so the Economy/Science levels' income no longer adds again in incomes_value.
NEXT_TO_OPPONENT = 2
TERRANS_GAIA_FROM_ROUND = 4


def _next_to_opponent(state, actor, coord):
    from strategy_teacher import distance
    return any(distance(c, coord) <= NEXT_TO_OPPONENT and any(s['owner'] != actor for s in cell['structures'])
               for c, cell in state['board']['hexes'].items() if cell['structures'])


def _future_opponent_sites(state, actor):
    """Free home planets of opponents who still place starting structures (rule: a starting
    structure goes on the faction's home planet; counts from gaia-engine/data/factions.toml)."""
    from faction_teachers.profiles import profiles
    homes = set()
    for p in state['players']:
        if p['player_id'] == actor:
            continue
        profile = profiles().get(p['faction'])
        if profile and len(p['structures']) < profile.starting_structures:
            homes.add(profile.home)
    return [c for c, cell in state['board']['hexes'].items()
            if cell['planet'] and cell['planet']['planet_type'] in homes
            and cell['planet']['owner'] is None and not cell['structures']]


def _near_sites(state, actor, coord, sites):
    from strategy_teacher import distance
    return any(c != coord and distance(c, coord) <= NEXT_TO_OPPONENT for c in sites)


def _early_terrans_gaia(state, actor):
    player = state['players'][actor]
    if player['faction'] != 'Terrans' or state['round'] >= TERRANS_GAIA_FROM_ROUND:
        return False
    if _guide['terrans_gaia_cond']:
        # B04's condition ("차원 변형 행성을 충분히 확보하기 전엔 올리지 않음", user 2026-10-15): with two
        # unformed Transdim planets in reach the Gaia track may go up before round 4 (B18-03's count).
        free = [c for c, t in _in_reach(state, player, ('Transdim',)).items()
                if not (state['board']['hexes'][c]['planet'] or {}).get('is_gaia_formed')]
        return len(free) < WHEN_TRANSDIM
    return True


def _near_places(snapshot, scores):
    """Unblocked starting places within NEXT_TO_OPPONENT of an opponent's structure, or (nobody
    placed nearby yet) of a free home planet of an opponent with placements left."""
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot['player']
    places = [i for i, c in enumerate(snapshot['candidates'])
              if c['action']['type'] == 'PlaceStartingStructure' and not blocked(scores[i])]
    near = {i for i in places if _next_to_opponent(state, actor, snapshot['candidates'][i]['action']['coord'])}
    if not near and places:
        sites = _future_opponent_sites(state, actor)
        near = {i for i in places if _near_sites(state, actor, snapshot['candidates'][i]['action']['coord'], sites)}
    return near


def guide_r1_scores(snapshot, scores):
    from current_actions.conservation import BLOCKED, PREFIX, blocked
    state, actor = snapshot['state'], snapshot['player']
    finite = [s[0] for s in scores if not blocked(s)]
    if not finite:
        return scores
    bottom = min(finite)
    result = list(scores)
    near = _near_places(snapshot, scores)
    for i, candidate in enumerate(snapshot['candidates']):
        action = candidate['action']
        if blocked(scores[i]):
            continue
        if action['type'] == 'PlaceStartingStructure' and near and i not in near and not _guide['setup_soft']:
            # Setup comparisons end at the round-1/2 income and differ by noise (034: 154.3
            # vs 153.5), so ordering alone let an isolated start win; compare only the near ones.
            result[i] = (BLOCKED, PREFIX+'guide: start next to an opponent (LF4-02, B10-02)')
        elif (action['type'] == 'ResearchAdvance' and action.get('track') == 'GaiaProject'
              and _early_terrans_gaia(state, actor)):
            result[i] = (scores[i][0]-abs(bottom)-1000, *scores[i][1:])
    return result


# 5. Geodens 1PI+4M first when its conditions hold (user 2026-10-06; BGG-O2 Geodens table:
#    1PI+4M 153 avg over 228 games vs 1PI+2M 134, "effective only when the player gets 4 mines in
#    round 1, ideally on different types: home, red, yellow, Gaia"). The PI's 3 knowledge per new
#    planet type needs the three new mines on Oxide, Desert (1 terraforming step from Volcanic)
#    and Gaia. Facts checked, order only:
#    - an unoccupied Oxide, Desert and Gaia planet in range, the range QIC of all three plus the
#      Gaia planet's own QIC within the QIC held (engine targets/path distance, one QIC = +2 range);
#    - two terraforming steps from cheap sources: booster 12 held (1), power action 2 (2 steps,
#      5 power) or 6 (1 step, 3 power) unused and payable from bowl III plus burning now,
#      TF Mars explored or explorable now (1). Ore-paid steps are left to the comparison.
GEODENS_PI4 = '1PI+4M'
GEODENS_NEW_TYPES = ('Oxide', 'Desert')
TERRAFORM_POWER_ACTIONS = {2: (5, 2), 6: (3, 1)}   # engine id: (power, free steps)


def geodens_pi4_ready(snapshot):
    from four_factions.value import targets
    state, actor = snapshot['state'], snapshot['player']
    player = state['players'][actor]
    if player['faction'] != 'Geodens' or state['round'] != 1:
        return False
    unlimited = {**player, 'resources': {**player['resources'], 'qic': 99}}
    need = 0
    for planet_type in (*GEODENS_NEW_TYPES, 'Gaia'):
        options = [qic for _, _, qic in targets(state, unlimited, (planet_type,))]
        if not options:
            return False
        need += min(options) + (planet_type == 'Gaia')
    if need > player['resources']['qic']:
        return False
    power = player['resources']['power']
    spendable = power['bowl3'] + power['bowl2']//2
    used = state.get('used_power_actions', [])
    steps = int(player['booster'] == 12)
    steps += max((free for i, (cost, free) in TERRAFORM_POWER_ACTIONS.items()
                  if i not in used and cost <= spendable), default=0)
    steps += int('TFMars' in player['explored_ships'] or any(
        c['action']['type'] == 'ExploreSpaceship' and c['action'].get('ship') == 'TFMars'
        for c in snapshot['candidates']))
    return steps >= 2


def geodens_pi4_order(snapshot, goals):
    if not geodens_pi4_ready(snapshot):
        return goals
    first = [g for g in goals if g.family == 'bgg-opening' and g.target == GEODENS_PI4]
    return first + [g for g in goals if g not in first]


# 6. Geodens research order from the BGG opening articles (user 2026-10-06, "글 내용에 최대한 부합"):
#    Part 1: "지오덴 HS 플레이어 중 19%는 AC 루트… 경제 또는 과학 트랙과 조합". Part 2: AC opening "대부분 경제
#    트랙에서 단계를 밟으며 2/3라운드 PI를 준비", 2RL start "거의 항상 경제 트랙". With a PI the articles name
#    no track ("기술 트랙을 조기에 발전"), so geodens_guide's Terraforming-3 / Navigation-2 plans lose
#    their place at the front and follow the colony plans. Order only; the comparison decides.
GEODENS_LATE_RESEARCH = ('Geodens-Terraforming-3', 'Geodens-Navigation-2')


def geodens_r1_goals(snapshot, goals):
    from four_factions.preparation import Goal
    from strategy_teacher import kind
    state, actor = snapshot['state'], snapshot['player']
    player = state['players'][actor]
    if player['faction'] != 'Geodens':
        return goals
    kinds = [kind(s['kind']) for s in player['structures']]
    late = [g for g in goals if g.name in GEODENS_LATE_RESEARCH]
    rest = [g for g in goals if g not in late]
    first = []
    if 'PlanetaryInstitute' not in kinds and ('Academy' in kinds or kinds.count('ResearchLab') >= 2):
        tracks = player['research_tracks']
        sources = ('BGG-O1', 'BGG-O2')
        if tracks['economy'] < 5:
            first.append(Goal(f'Geodens-Economy-{tracks["economy"]+1}', 'research', target='Economy',
                              level=tracks['economy']+1, sources=sources))
        if 'Academy' in kinds and tracks['science'] < 5:
            first.append(Goal(f'Geodens-Science-{tracks["science"]+1}', 'research', target='Science',
                              level=tracks['science']+1, sources=sources))
    if not late and not first:
        return goals
    colonies = [g for g in rest if _target_coord(g)]
    others = [g for g in rest if not _target_coord(g)]
    return first + colonies + late + others


def install_guide_r1():
    import bgg_openings.planning as planning
    import faction_teachers.paths as paths
    import four_factions.preparation as p
    _guide['qic_reach'] = False
    _guide['track_income'] = False
    if not getattr(paths.goals, '_guide_r1', False):
        inner_paths_goals = paths.goals

        def faction_goals(snapshot):
            return geodens_r1_goals(snapshot, inner_paths_goals(snapshot))
        faction_goals.__wrapped__ = getattr(inner_paths_goals, '__wrapped__', inner_paths_goals)
        faction_goals._guide_r1 = True
        paths.goals = faction_goals
    if not getattr(planning.goals, '_guide_r1', False):
        inner_opening_goals = planning.goals

        def opening_goals(snapshot, remembered=None):
            goals = inner_opening_goals(snapshot, remembered)
            if remembered is not None:
                return goals
            return geodens_pi4_order(snapshot, goals)
        opening_goals.__wrapped__ = getattr(inner_opening_goals, '__wrapped__', inner_opening_goals)
        opening_goals._guide_r1 = True
        planning.goals = opening_goals
    if not getattr(p.Policies.rank, '_guide_r1', False):
        inner_rank = p.Policies.rank

        def rank(self, env, snapshot):
            return guide_r1_scores(snapshot, inner_rank(self, env, snapshot))
        rank.__wrapped__ = getattr(inner_rank, '__wrapped__', inner_rank)
        rank._guide_r1 = True
        p.Policies.rank = rank
    if not getattr(p.goals_for, '_guide_r1', False):
        inner_goals_for = p.goals_for

        def goals_for(snapshot, **kwargs):
            goals = inner_goals_for(snapshot, **kwargs)
            if not _early_terrans_gaia(snapshot['state'], snapshot['player']):
                return goals
            late = [g for g in goals if g.family == 'research' and g.target == 'GaiaProject']
            return [g for g in goals if g not in late] + late
        goals_for.__wrapped__ = getattr(inner_goals_for, '__wrapped__', inner_goals_for)
        goals_for._guide_r1 = True
        p.goals_for = goals_for


def guide_r1(seed, **kwargs):
    """Teacher factory: guide_values_openings_free plus opponent-adjacent setup, Terrans Gaia
    research after round 3 and QIC priced once."""
    teacher = guide_values_openings_free(seed, **kwargs)
    install_guide_r1()
    return teacher


# ── charge_r3 ──────────────────────────────────────────────────────────────────────────
# Opt-in, on top of guide_r1. User (2026-10-06): "아직 점수 벌 타이밍이 아니다 — 3라운드까지 두고
# 점수 대신 모은 파워로 비교. 건물·자원 전부 파워로 치환, 4파워 충전 기술처럼 3라운드 이후에 얻을
# 파워도 같이 계산." A comparison started in rounds 0-3 rolls out to the start of round 4's
# actions (not the next income) and its leaf is the guide value in charges without VP:
# guide_potential minus VP held, final-scoring standings and the pass VP of the held booster.
# Everything else stays in it at the LF prices: stock resources and power, every remaining income
# (buildings, tracks, tech tiles), research levels, buildings, ships and the 4-charge tile per
# round left. VP spent (e.g. fleet entry) is therefore not a cost here, unless
# _guide['charge_vp'] keeps the VP held (guide_r1_charge3_lf_tiles).
CHARGE_LAST_ROUND = 3
CHARGE_ROLLOUT_LIMIT = 720   # three rounds of four seats; the tree's 192 covers about one
_charge = {'active': False}


def charge_value(state, actor, *, with_vp=None):
    """Every faction, Xenos included, is valued by the same charge measure here.

    with_vp (default _guide['charge_vp']): keep the VP held, at 1 VP = 1.5 charges like every
    other value. User (2026-10-07): "모든 VP도 파워로 치환" — VP spent (fleet entry) is then a
    cost and VP gained (federations, artifacts, round scoring) a gain."""
    from faction_teachers.profiles import profiles
    v = _value
    player = state['players'][actor]
    home = None if player['faction'] in v.HOME else profiles()[player['faction']].home
    if with_vp is None:
        with_vp = _guide['charge_vp']
    result = guide_potential(state, actor, home=home) - v.standings(state, actor)
    if not with_vp:
        result -= player['vp']
    if state['round'] >= 1 and not player['passed'] and _action_phase(state):
        result -= booster_pass_vp(state, player)
    return result


def install_charge_r3():
    import four_factions.preparation as p
    if getattr(p.rollout, '_charge_r3', False):
        return
    inner_rollout, inner_leaf = p.rollout, p.leaf_value
    raw_horizon = getattr(p.reached_horizon, '__wrapped__', p.reached_horizon)

    def to_round4(state, target_round):   # no __wrapped__: geodens_guide keeps it as is
        return raw_horizon(state, CHARGE_LAST_ROUND+1)

    def leaf_value(snapshot, actor, *args, **kwargs):
        if _charge['active']:
            return charge_value(snapshot['state'], actor)
        return inner_leaf(snapshot, actor, *args, **kwargs)

    def rollout(env, snapshot, first, goal, policies, deadline, *args, **kwargs):
        if snapshot['state']['round'] > CHARGE_LAST_ROUND or _charge['active']:
            return inner_rollout(env, snapshot, first, goal, policies, deadline, *args, **kwargs)
        if not args:
            kwargs.setdefault('limit', CHARGE_ROLLOUT_LIMIT)
        configured = p.reached_horizon
        p.reached_horizon, _charge['active'] = to_round4, True
        try:
            return inner_rollout(env, snapshot, first, goal, policies, deadline, *args, **kwargs)
        finally:
            p.reached_horizon, _charge['active'] = configured, False
    rollout.__wrapped__ = getattr(inner_rollout, '__wrapped__', inner_rollout)
    rollout._charge_r3 = True
    leaf_value.__wrapped__ = getattr(inner_leaf, '__wrapped__', inner_leaf)
    p.rollout, p.leaf_value = rollout, leaf_value


def guide_r1_charge3(seed, **kwargs):
    """Teacher factory: guide_r1 with rounds 0-3 compared at round 4 in charges, not VP."""
    teacher = guide_r1(seed, **kwargs)
    install_charge_r3()
    return teacher


def guide_r1_charge3_lf(seed, **kwargs):
    """Teacher factory: guide_r1_charge3 with LF01/LF02 table values for explored ships (best
    net action every round), green federation tokens (3 charges) and pass advanced tiles."""
    teacher = guide_r1_charge3(seed, **kwargs)
    _guide['lf_tables'] = True
    return teacher


def guide_r1_charge3_lf_tiles(seed, **kwargs):
    """Teacher factory: guide_r1_charge3_lf with standard tiles 6 and 12 left to the search,
    tile 8 valued by the Gaia mines still to come, and VP held kept in the charge value."""
    teacher = guide_r1_charge3_lf(seed, **kwargs)
    _guide['lf_tiles'] = True
    _guide['charge_vp'] = True
    return teacher


def guide_r1_charge3_lf_more(seed, **kwargs):
    """Teacher factory: guide_r1_charge3_lf_tiles with advanced event/special action tiles and
    the research options at LF values, plus federation progress and neighbour charges."""
    teacher = guide_r1_charge3_lf_tiles(seed, **kwargs)
    _guide['lf_more'] = True
    return teacher


def academy_openings_first(original, rows, remembered, comparisons):
    """Among completed comparisons, those that built an academy in round 1 first."""
    built = [c for c in comparisons if c.get('complete') and (c.get('r1_buildings') or {}).get('academy')]
    return original(rows, remembered, built) or original(rows, remembered, comparisons)


def install_academy_r1():
    import bgg_openings.planning as planning
    _guide['academy_r1'] = True
    if not getattr(planning.select_forecast, '_academy_r1', False):
        inner_forecast = planning.select_forecast

        def select_forecast(rows, remembered, comparisons):
            return academy_openings_first(inner_forecast, rows, remembered, comparisons)
        select_forecast._academy_r1 = True
        planning.select_forecast = select_forecast


def guide_r1_charge3_lf_more_ac(seed, **kwargs):
    """Teacher factory: guide_r1_charge3_lf_more with round-1 academy openings funded before
    other spending and selected first when a comparison completed one (academy_r1)."""
    teacher = guide_r1_charge3_lf_more(seed, **kwargs)
    install_academy_r1()
    return teacher


def guide_r1_charge3_lf_more_sh(seed, **kwargs):
    """Teacher factory: guide_r1_charge3_lf_more with the round-1 openings ordered by sheden #4
    (SHEDEN_OPENINGS, Geodens included) and Terraforming 0→1 (2 ore) researched when a round-1
    academy chain is stuck short of ore. No academy_r1."""
    teacher = guide_r1_charge3_lf_more(seed, **kwargs)
    _guide['sheden_r1'] = True
    return teacher


# ── value_max ──────────────────────────────────────────────────────────────────────────
# User (2026-10-08, 042 pair-004/game-0-A01): the comparisons were right and the plan choice
# threw them away. Geodens step 18: 1PI+4M 274.2 vs current-choice 212.5, but the opening plan
# did not finish the PI in round 1, so `select_forecast` found no matching opening and the
# search fell back to the best non-opening plan. Terrans step 47: an academy/Gaia plan 269.3
# lost to the remembered BGG opening 256.1. Geodens step 54: upgrade plan 267.6 lost to a
# pass plan 218.0 the same way. value_max plays the first move of the completed comparison
# with the highest value, whatever its family; nothing is valued differently.
#
# ts_chain (same day): "연구소나 의회까지 바로 올라가는 업그레이드면 좋게 판단해야". At LF prices a
# trading station alone is a loss (034), so the root ranking puts it below pass. When the
# resources left after the trading station already pay the research lab or the planetary
# institute (engine costs, preparation.funding_need), the trading station goes before every
# move that is not an upgrade. Rounds 1-3 only, the span charge3 compares. Order only.
#
# ts_chain_direct (user 2026-10-08, lab 046 p001-g1): the lift also put a second trading station
# ahead of upgrading an existing one straight to the research lab (Terrans step 27: 20.91 vs 20.80,
# Xenos step 30: 82.97 vs 80.94). When a research lab or planetary institute upgrade is already
# legal, the chain it would prepare is available now, so no trading station is lifted. A
# building already in a federation is not lifted either (user, same day): its power is spent.
#
# knowledge_spend (user, same day): "지식은 무조건 쓰는 방향으로". Held knowledge only pays when
# a level-5 advance lacks it, and by then the knowledge income is in place, so while the actor
# holds 4 knowledge and a research advance is legal, passing is blocked. Rule, not a value.

def _value_max(snapshot, result):
    import math
    plans = [(plan['value'], -order, plan) for order, plan in enumerate(result.get('plans') or [])
             if plan.get('complete') and isinstance(plan.get('value'), (int, float))
             and math.isfinite(plan['value'])]
    if not plans:
        return
    best = max(plans, key=lambda item: item[:2])[2]
    if best['first'] == result.get('index'):
        return
    result['value_max'] = {'replaced': result.get('selected'), 'replaced_index': result.get('index')}
    result.update(index=best['first'], selected=f'value-max {best["goal"]}')
    target = (best.get('goal_spec') or {}).get('target')
    if best.get('family') == 'bgg-opening' and target and isinstance(result.get('memory'), dict):
        result['memory'].setdefault('_bgg_targets', {})[str(snapshot['player'])] = target


def ts_chain_scores(env, snapshot, scores):
    import json
    from bgg_openings.catalog import LIMITS
    from bgg_openings.inventory import building_counts
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if not 1 <= state['round'] <= 3 or 'ActionPhase' not in state['phase'] or actor is None:
        return scores
    if _guide['ts_chain_direct'] and any(
            candidate['action'].get('type') == 'Upgrade'
            and candidate['action'].get('to') in ('ResearchLab', 'PlanetaryInstitute')
            and not blocked(scores[i]) for i, candidate in enumerate(snapshot['candidates'])):
        return scores
    federated = set(map(str, state['players'][actor].get('federated_hexes') or []))
    counts = building_counts(state['players'][actor])
    nexts = [cost for cost, kind in (((3, 5), 'research_lab'), ((4, 6), 'planetary_institute'))
             if getattr(counts, kind) < LIMITS[kind]]
    chained = []
    for i, candidate in enumerate(snapshot['candidates']):
        action = candidate['action']
        if action.get('type') != 'Upgrade' or action.get('to') != 'TradingStation' or blocked(scores[i]):
            continue
        if _guide['ts_chain_direct'] and str(action.get('coord')) in federated:
            continue
        after = json.loads(env.fork(snapshot['decision_id'], i).snapshot_json())
        left = after['state']['players'][actor]['resources']
        if any(left['ore'] >= ore and left['credits'] >= credits for ore, credits in nexts):
            chained.append(i)
    if not chained:
        return scores
    others = [s[0] for i, s in enumerate(scores) if not blocked(s)
              and snapshot['candidates'][i]['action'].get('type') != 'Upgrade']
    floor = max(others, default=0.0)
    lifted = list(scores)
    for i in chained:
        if scores[i][0] <= floor:
            lifted[i] = (floor+1.0+scores[i][0]/1000.0, f'{scores[i][1]}; ts_chain: lab/PI paid next',
                         *scores[i][2:])
    return lifted


def knowledge_spend_scores(env, snapshot, scores):
    from current_actions.conservation import BLOCKED, PREFIX, blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if 'ActionPhase' not in state['phase'] or actor is None:
        return scores
    if state['players'][actor]['resources']['knowledge'] < 4:
        return scores
    candidates = snapshot['candidates']
    if not any(c['action'].get('type') == 'ResearchAdvance' and not blocked(scores[i])
               for i, c in enumerate(candidates)):
        return scores
    lifted = list(scores)
    for i, candidate in enumerate(candidates):
        if candidate['action'].get('type') == 'Pass':
            lifted[i] = (BLOCKED, PREFIX+'knowledge spend: research before passing', *scores[i][2:])
    return lifted


def _wrap_rank(flag, adjust):
    """Wrap Policies.rank once with adjust(env, snapshot, scores), keeping the earlier wrappers'
    install flags so a second factory call does not stack them."""
    import four_factions.preparation as p
    inner_rank = p.Policies.rank
    if getattr(inner_rank, flag, False):
        return

    def rank(self, env, snapshot):
        return adjust(env, snapshot, inner_rank(self, env, snapshot))
    for name, value in vars(inner_rank).items():
        if name.startswith('_') and isinstance(value, bool):
            setattr(rank, name, value)
    rank.__wrapped__ = getattr(inner_rank, '__wrapped__', inner_rank)
    setattr(rank, flag, True)
    p.Policies.rank = rank


def install_knowledge_spend():
    _guide['knowledge_spend'] = True
    _wrap_rank('_knowledge_spend', knowledge_spend_scores)


# ship_setup (user 2026-10-08, lab 046 p001-g1: nearest ship 2-5 hexes from the starting mines):
# among the starting places the guide_r1 filter leaves, those within SHIP_SETUP_RANGE of a Lost
# Fleet ship tile go first, and among them the ship that fits the faction (LF03 L3-7: QIC left
# over → Rebellion, credits → Eclipse, power tokens → Twilight, terraforming → TF Mars; average
# strength Rebellion ≥ Twilight > Eclipse ≥ TF Mars breaks ties). The fit is the resource with the
# largest share of the player's income at the guide prices, not a per-faction table. Order only:
# the comparison still decides.
SHIP_SETUP_RANGE = 3
SHIP_STRENGTH = ('Rebellion', 'Twilight', 'Eclipse', 'TFMars')
SHIP_FOR_INCOME = {'qic': 'Rebellion', 'credits': 'Eclipse', 'tokens': 'Twilight', 'ore': 'TFMars'}


def _ship_fit(state, player):
    import guide_value as gv
    income = _value.production(state, player, include_booster=False)
    shares = {'ore': gv.CHARGE['ore']*income[0], 'credits': gv.CHARGE['credits']*income[1],
              'qic': gv.CHARGE['qic']*income[3], 'tokens': income[4] + gv.TOKEN*income[5]}
    best = max(shares, key=lambda k: (shares[k], -SHIP_STRENGTH.index(SHIP_FOR_INCOME[k])))
    fitted = SHIP_FOR_INCOME[best]
    return (fitted,) + tuple(s for s in SHIP_STRENGTH if s != fitted)


def ship_setup_scores(env, snapshot, scores):
    from current_actions.conservation import blocked
    from strategy_teacher import distance
    state, actor = snapshot['state'], snapshot.get('player')
    ships = state['board'].get('spaceship_tiles') or {}
    places = [i for i, c in enumerate(snapshot['candidates'])
              if c['action'].get('type') == 'PlaceStartingStructure' and not blocked(scores[i])]
    if actor is None or not ships or not places:
        return scores
    order = _ship_fit(state, state['players'][actor])
    finite = [s[0] for s in scores if not blocked(s)]
    top = max(finite)
    lifted = list(scores)
    for i in places:
        coord = snapshot['candidates'][i]['action']['coord']
        near = [(order.index(ship), distance(coord, at)) for ship, at in ships.items()
                if ship in order and distance(coord, at) <= SHIP_SETUP_RANGE]
        if not near:
            continue
        rank, gap = min(near)
        lifted[i] = (top + 1 + (len(order)-rank) + (SHIP_SETUP_RANGE-gap)/10 + scores[i][0]/1000,
                     f'{scores[i][1]}; ship setup: {order[rank]} at {gap}', *scores[i][2:])
    return lifted


def install_ship_setup():
    _guide['ship_setup'] = True
    _wrap_rank('_ship_setup', ship_setup_scores)


def install_value_max():
    import four_factions.preparation as p
    _guide['value_max'] = True
    if not getattr(p.search, '_value_max', False):
        inner_search = p.search

        def search(env, snapshot, memory, publish, *args, **kwargs):
            def publish_value_max(result):
                _value_max(snapshot, result)
                publish(result)
            result = inner_search(env, snapshot, memory, publish_value_max, *args, **kwargs)
            _value_max(snapshot, result)
            return result
        search._value_max = True
        search._parallel = getattr(inner_search, '_parallel', False)
        p.search = search
    if not getattr(p.Policies.rank, '_ts_chain', False):
        inner_rank = p.Policies.rank

        def rank(self, env, snapshot):
            return ts_chain_scores(env, snapshot, inner_rank(self, env, snapshot))
        rank.__wrapped__ = getattr(inner_rank, '__wrapped__', inner_rank)
        rank._ts_chain = True
        rank._parallel = getattr(inner_rank, '_parallel', False)
        p.Policies.rank = rank


def guide_r1_charge3_lf_more_vm(seed, **kwargs):
    """Teacher factory: guide_r1_charge3_lf_more with the highest completed comparison played
    (value_max) and trading stations whose lab/PI is already paid ranked before non-upgrades."""
    teacher = guide_r1_charge3_lf_more(seed, **kwargs)
    install_value_max()
    return teacher


# ── vp1 + leech rule ───────────────────────────────────────────────────────────────────
# User (2026-10-08): at 1 VP = 1.5 charges a 3-charge leech is already break-even and a fleet
# entry's VP cost is too large; "1점을 1로 혹은 그 아래로", and "4단계는 안 받는다". A single VP
# rate cannot also make bigger leeches better (net N-(N-1)k falls with N for k >= 1), so the
# leech choice is a rule, not a value: a leech costing at most 2 VP (charge <= 3) is accepted,
# one costing 3 VP or more (charge >= 4) is declined. The other answer is blocked, so neither the
# root ranking nor a comparison can pick it. User decision, not an LF number (LF01 states 1.5).
VP_RATE_USER = 1.0
LEECH_MAX_VP = 2


def leech_rule_scores(env, snapshot, scores):
    import json
    from current_actions.conservation import BLOCKED, PREFIX
    actor = snapshot.get('player')
    answers = {c['action'].get('accept'): i for i, c in enumerate(snapshot['candidates'])
               if c['action'].get('type') == 'ChargePower'}
    if actor is None or True not in answers or False not in answers:
        return scores
    accept = answers[True]
    after = json.loads(env.fork(snapshot['decision_id'], accept).snapshot_json())
    cost = snapshot['state']['players'][actor]['vp'] - after['state']['players'][actor]['vp']
    refused = answers[False] if cost <= LEECH_MAX_VP else accept
    lifted = list(scores)
    lifted[refused] = (BLOCKED, PREFIX+f'leech rule: accept up to {LEECH_MAX_VP} VP, cost {cost}',
                       *scores[refused][2:])
    return lifted


def install_vp1_leech(rate=VP_RATE_USER):
    import guide_value as gv
    import four_factions.preparation as p
    _guide['vp_rate'] = rate
    for r in gv.CHARGES_PER_VP:
        gv.CHARGES_PER_VP[r] = rate
    if not getattr(p.Policies.rank, '_leech_rule', False):
        inner_rank = p.Policies.rank

        def rank(self, env, snapshot):
            return leech_rule_scores(env, snapshot, inner_rank(self, env, snapshot))
        rank.__wrapped__ = getattr(inner_rank, '__wrapped__', inner_rank)
        rank._leech_rule = True
        rank._ts_chain = getattr(inner_rank, '_ts_chain', False)
        rank._parallel = getattr(inner_rank, '_parallel', False)
        p.Policies.rank = rank


def guide_r1_charge3_lf_more_vm_vp1(seed, **kwargs):
    """Teacher factory: guide_r1_charge3_lf_more_vm with 1 VP = 1 charge and the leech rule
    (accept a leech costing at most 2 VP, decline 3 VP or more)."""
    teacher = guide_r1_charge3_lf_more_vm(seed, **kwargs)
    install_vp1_leech()
    return teacher


# ── lf_frozen ──────────────────────────────────────────────────────────────────────────
# User (2026-10-08, after 045 "그렇게 해"): the frozen teacher's remaining hand formulas are
# replaced by calculations at the guide prices, on top of lf_more_vm (no vp1, no leech rule):
# 1. Colony options (frozen expansion_value 4/(cost+QIC+1) top 3, gaia_value 6+2·rounds per
#    colony ×0.65, both capped by hand): every planet in range now is priced as a mine built next
#    round — planet (LF01 6 charges) + the mine's income from the round after — minus its cost
#    at LF prices (1 ore + terraforming ore, 2 credits, range QIC, 1 QIC on a Gaia planet). Transdim
#    planets count when a Gaia former and its tokens are free (rulebook Gaia project); Terrans'
#    returning tokens land in bowl II (one charge each). Positive options only, best first, within
#    the ore/credits/QIC held plus the next income and the 8-mine limit. QIC is paid here, so
#    planets are reached with the QIC really held (qic_reach no longer applies).
# 2. Gaia-area tokens (frozen 0.6 Terrans / 0.2 others): tokens, B02 value up to the need,
#    counted with the bowl tokens since they come back at the next Gaia phase.
# 3. Neighbour charges (frozen Taklons PI term horizon·min(2, owners); lf_more 2 charges per
#    neighbour): each opponent within 2 hexes charges, once a round, the highest power value of
#    our buildings near theirs (rulebook leech amount); with the Taklons PI one more token
#    (rulebook PI ability, B02 token value while needed).
# 4. Setup placement (frozen 3/d home, 1.5/d near colours, 2·owners, −0.25·ship distance): 0.
#    The placed structure's reachable planets and neighbours are now in the state value (1, 3) and
#    guide_r1 still compares only starts next to an opponent.
# 5. Xenos leech (integrated teacher: charge·1.1 − cost·(1.5 or 0.7), −4 without ships): the
#    charge at the guide price minus its VP cost, accepted when positive.
# Kept: standings, Brainstone, the −0.25 free-action term.


def lf_power_value(state, player):
    """guide_value.power_value with the Gaia-area tokens counted as tokens held (item 2)."""
    import guide_value as gv
    power = player['resources']['power']
    charges = power['bowl2'] + 2*power['bowl3']
    if player['faction'] == 'Terrans':
        charges += power['gaia_forming']
    tokens = sum(power[k] for k in ('bowl1', 'bowl2', 'bowl3')) + power['gaia_forming']
    if not _guide['tokens_lf']:
        tokens = min(tokens, gv.tokens_needed(player))
    # tokens_lf (user 2026-10-15): no cap at B02's need — LF1-02 "파워 토큰이 많아도 방해만 되지 않음,
    # 기회가 될 때 늘려두면 도움" (Gaia use, Asteroids, artifacts); each token at the LF01 price.
    return gv.to_vp(state, charges + gv.TOKEN*tokens)


GAIA_TOKENS = (255, 6, 6, 4, 3, 3)   # rulebook: tokens per Gaia former by Gaia track level
MINE_COST = {'ore': 1, 'credits': 2}
MINE_LIMIT = 8


def _reach_targets(state, player, planet_types):
    """[(coord, planet, qic, nav)]: v.targets, plus (reach_plus) the planets that the next range
    step on the Navigation track brings closer; nav = the knowledge those levels cost (0 = none)."""
    v = _value
    found = {coord: (planet, qic, 0) for coord, planet, qic in v.targets(state, player, planet_types)}
    plus = _nav_plus(player) if _guide['reach_plus'] else None
    if plus is not None:
        plus, knowledge = plus
        for coord, planet, qic in v.targets(state, plus, planet_types):
            if coord not in found or qic < found[coord][1]:
                found[coord] = (planet, qic, knowledge)
    return [(coord, *rest) for coord, rest in found.items()]


def _colony_costs(state, player, home):
    """(cost, extra charges, Navigation knowledge needed) of each colony option (item 1), before pricing."""
    from economy.teacher import ORE_PER_STEP, RING
    options = []
    if home in RING:
        step_ore = ORE_PER_STEP[player['research_tracks']['terraforming']]
        for _, planet, qic, nav in _reach_targets(state, player, (*RING, 'Gaia')):
            if planet['planet_type'] == 'Gaia':
                options.append(({**MINE_COST, 'qic': qic+1}, 0, nav))
                continue
            gap = abs(RING.index(home)-RING.index(planet['planet_type']))
            ore = MINE_COST['ore'] + min(gap, 7-gap)*step_ore
            options.append(({**MINE_COST, 'ore': ore, 'qic': qic}, 0, nav))
    level = player['research_tracks']['gaia']
    terrans = player['faction'] == 'Terrans'
    reserved = sum(cell['planet'] is not None and cell['planet']['owner'] == player['player_id']
                   and cell['planet']['planet_type'] == 'Transdim' and not cell['structures']
                   for cell in state['board']['hexes'].values())
    options += [(dict(MINE_COST), 0, 0)]*reserved
    room = _gaia_room(player)
    if room and not _guide['former_use']:
        transdim = sorted((qic, nav) for _, _, qic, nav in _reach_targets(state, player, ('Transdim',)))[:room]
        options += [({**MINE_COST, 'qic': qic}, GAIA_TOKENS[level]*terrans, nav) for qic, nav in transdim]
    # Formers on a planet or in the Gaia area come back, so every former not yet used up counts.
    formers = (max(0, player['gaiaformers_total'] - player['resources']['spent_gaia_formers'])
               if _guide['former_use'] else 0)
    if formers:
        # Lost Fleet rulebook: a mine on an Asteroid costs no ore or credits, only the range QIC,
        # and uses up one Gaia former.
        asteroids = sorted((qic, nav) for _, _, qic, nav in _reach_targets(state, player, ('Asteroid',)))[:formers]
        options += [({'qic': qic}, 0, nav) for qic, nav in asteroids]
    return options


def _idle_formers(player):
    """Gaia formers neither on a planet, in the Gaia area nor used up on an Asteroid."""
    return max(0, player['gaiaformers_total'] - player['gaiaformers_deployed']
               - player['gaiaformers_in_gaia_area'] - player['resources']['spent_gaia_formers'])


def _gaia_room(player):
    """Gaia formers that can start now: free formers, each with its tokens in the bowls."""
    level = player['research_tracks']['gaia']
    if not level:
        return 0
    power = player['resources']['power']
    tokens = sum(power[k] for k in ('bowl1', 'bowl2', 'bowl3'))
    formers = max(0, player['gaiaformers_total'] - player['gaiaformers_deployed']
                  - player['gaiaformers_in_gaia_area'] - player['resources']['spent_gaia_formers'])
    return min(formers, tokens//GAIA_TOKENS[level])


def colony_options(state, player, *, home=None):
    import guide_value as gv
    v = _value
    if state['round'] >= 6:
        return 0.0
    home = v.HOME.get(player['faction']) if home is None else home
    current = v.production(state, player, include_booster=False)
    built = {**player, 'structures': [*player['structures'], {'kind': 'Mine', 'hex': None}]}
    delta = [b-a for a, b in zip(current, v.production(state, built, include_booster=False))]
    gain = gv.planet_value(state) + gv.incomes_value(dict(state, round=state['round']+1), delta)
    recurring = v.production(state, player, include_booster=player['passed'])
    resources = player['resources']
    budget = {'ore': resources['ore']+recurring[0], 'credits': resources['credits']+recurring[1],
              'qic': resources['qic']+recurring[3], 'knowledge': resources['knowledge']+recurring[2]}
    priced = []
    for cost, charges, nav in _colony_costs(state, player, home):
        net = gain + gv.to_vp(state, charges - sum(gv.CHARGE[k]*n for k, n in cost.items()))
        if net > 0:
            priced.append((net, cost, nav))
    room = max(0, MINE_LIMIT - sum(v.kind(s['kind']) == 'Mine' for s in player['structures']))
    total, nav_paid = 0.0, False
    for net, cost, nav in sorted(priced, key=lambda item: -item[0]):
        if not room:
            break
        # reach_plus: the Navigation levels are paid once, in knowledge (rulebook: 4 a level);
        # each level is worth the same 16 charges (LF01), so they add no price here.
        need = {**cost, 'knowledge': nav} if nav and not nav_paid else cost
        if all(budget[k] >= n for k, n in need.items()):
            for k, n in need.items():
                budget[k] -= n
            total += net
            room -= 1
            nav_paid = nav_paid or nav
    return total


def lf_leech_value(state, player):
    """Item 3: per opponent, the highest power value among our buildings within 2 hexes of
    theirs, once for every round left; the Taklons PI adds a token per leech."""
    import guide_value as gv
    v = _value
    power = player['resources']['power']
    tokens = sum(power[k] for k in ('bowl1', 'bowl2', 'bowl3'))
    pi_token = (player['faction'] == 'Taklons'
                and any(v.kind(s['kind']) == 'PlanetaryInstitute' for s in player['structures'])
                and tokens < gv.tokens_needed(player))
    per_round = []
    for other in state['players']:
        if other is player:
            continue
        near = [_structure_power(s) for s in player['structures']
                if any(v.distance(s['hex'], b['hex']) <= 2 for b in other['structures'])]
        if near:
            per_round.append(max(near) + gv.TOKEN*pi_token)
    rounds = 7-max(state['round'], 1)
    best = sorted(per_round, reverse=True)[:gv.LEECH_NEIGHBORS_MAX]
    return gv.to_vp(state, sum(best)*rounds)


def lf_charge_score(teacher, snapshot, action):
    """Item 5 for the integrated (Xenos) teacher; None when no charge is pending."""
    import guide_value as gv
    state, player, resources = teacher.context(snapshot)
    phase = state['phase']
    queue = phase.get('ChargePowerPending', {}).get('queue', []) if isinstance(phase, dict) else []
    entry = next((q for q in queue if q['player'] == player['player_id']), None)
    if not entry:
        return None
    p = resources['power']
    charge = min(entry['max_power'], 2*p['bowl1']+p['bowl2'], max(0, player['vp'])+1)
    value = gv.to_vp(state, charge) - max(0, charge-1)
    return (value if action['accept'] else 0), f'charge: {charge} at the guide price minus its VP cost'


def _no_placement(state, player, coord, *, home=None):
    return 0.0


def install_lf_frozen():
    import four_factions.quick as quick
    import four_factions.teacher as ff_teacher
    import integrated.teacher as integrated
    _guide['lf_frozen'] = True
    ff_teacher.placement = quick.placement = _no_placement
    cls = integrated.IntegratedTeacher
    if not getattr(cls.score, '_lf_frozen', False):
        inner_score = cls.score

        def score(self, snapshot, action):
            if action['type'] == 'ChargePower':
                result = lf_charge_score(self, snapshot, action)
                if result is not None:
                    return result
            return inner_score(self, snapshot, action)
        score._lf_frozen = True
        cls.score = score


def guide_r1_charge3_lf_more_vm_lf(seed, **kwargs):
    """Teacher factory: guide_r1_charge3_lf_more_vm with the frozen hand formulas (colony
    options, Gaia-area tokens, neighbour charges, setup placement, Xenos leech) computed at the
    guide prices (lf_frozen)."""
    teacher = guide_r1_charge3_lf_more_vm(seed, **kwargs)
    install_lf_frozen()
    return teacher


def guide_r1_charge3_lf_more_vm_lf_ts(seed, **kwargs):
    """Teacher factory: guide_r1_charge3_lf_more_vm_lf whose ts_chain lifts no trading station
    while a research lab or planetary institute upgrade is legal or on a federated building
    (ts_chain_direct), and which researches before passing while holding 4 knowledge
    (knowledge_spend), and which compares starting places near a fitting ship first (ship_setup)."""
    teacher = guide_r1_charge3_lf_more_vm_lf(seed, **kwargs)
    _guide['ts_chain_direct'] = True
    install_knowledge_spend()
    install_ship_setup()
    return teacher


# ── reach (user 2026-10-09, lab 047 pair-000/game-1) ───────────────────────────────────
# A. Setup search. Both comparisons of a setup decision started with the same move (Geodens
#    start -2,-2; Geodens booster 2, so booster 8 never rolled out; Terrans booster 13, so 5 never),
#    because the BGG/plan proposals all begin with the ranking's first choice and a rollout to
#    round 4 takes ~10 s against the 20 s cap. User: "셋업은 내 모행성만 건설 가능" (few places) and
#    boosters "4턴부터 고르니까 2턴이면 최소 3위까지". Setup decisions now compare the current choice
#    and the next-ranked distinct places or boosters only (no plan proposals; the round-1 opening is
#    chosen at the first round-1 decision), up to the comparison budget (4: at least the top 3),
#    with SETUP_SECONDS instead of the cap.
# B. Opponent-adjacent starts (guide_r1 1) are ordered first instead of blocking the others
#    (user: "거리 2 이내는 중요한데 가중치를 살짝만 낮추거나"), so isolated places can be compared.
# C. Range +1 (user: "앞으로 모든 행동은 사거리 +1(항해술 2렙을 찍고 시작하는 경우)까지 고민해야지, 즉시
#    포밍을 qic 쓰면서 쓸 수도 있잖아"): colony options also count the planets that the next range step
#    on the Navigation track brings within reach (QIC included), paying its knowledge once; booster 5
#    (immediate Gaia forming) is worth its table price only when a free Gaia former can reach a
#    Transdim planet that way, otherwise its income alone (Terrans 047 took it and returned it unused).
# D. Research focus (user: "한 트랙 집중해서 타라니까 아니면 항해술 2렙 찍고 확장 한다음 트랙 고르던지"):
#    the research advances' own root scores are reassigned, best score to the preferred track: the
#    highest track already at level 2 or more; with none, Navigation below level 2; then the higher
#    level first. Order among research moves only; research against other moves is unchanged.
SETUP_SECONDS = 50
SETUP_TYPES = frozenset({'PlaceStartingStructure', 'SelectStartingBooster'})
IMMEDIATE_GAIA_BOOSTER = 5
NAV_KNOWLEDGE = 4   # rulebook: one research level costs 4 knowledge
FOCUS_FROM = 2
TRACK_KEYS = {'Terraforming': 'terraforming', 'Navigation': 'navigation', 'ArtificialIntelligence': 'ai',
              'GaiaProject': 'gaia', 'Economy': 'economy', 'Science': 'science'}


def _nav_plus(player):
    """(player with Navigation at the next level that adds range, knowledge for those levels), or None."""
    from economy.teacher import NAV_RANGE
    level = player['research_tracks']['navigation']
    nxt = next((n for n in range(level+1, len(NAV_RANGE)) if NAV_RANGE[n] > NAV_RANGE[level]), None)
    if nxt is None:
        return None
    plus = {**player, 'research_tracks': {**player['research_tracks'], 'navigation': nxt}}
    return plus, NAV_KNOWLEDGE*(nxt-level)


def _immediate_gaia_usable(state, player):
    if not _gaia_room(player):
        return False
    knowledge = player['resources']['knowledge']
    return any(nav <= knowledge for _, _, _, nav in _reach_targets(state, player, ('Transdim',)))


def _booster_value(state, player, booster):
    import guide_value as gv
    if (_guide['reach_plus'] and booster == IMMEDIATE_GAIA_BOOSTER
            and not _immediate_gaia_usable(state, player)):
        income = [*_value.INCOME['boosters'].get(str(booster), []), *[0]*7][:7]
        return gv.income_value(state, income)
    return gv.booster_value(state, booster)


def _setup_choice(snapshot):
    kinds = {c['action'].get('type') for c in snapshot['candidates']}
    return bool(kinds) and kinds <= SETUP_TYPES


def install_setup_search():
    import time
    import bgg_openings.planning as planning
    import four_factions.preparation as p
    _guide['setup_roots'] = True
    if getattr(p.search, '_setup_roots', False):
        return
    inner_search = p.search

    def no_goals(snapshot, *args, **kwargs):
        return []

    def search(env, snapshot, *args, **kwargs):
        if not _setup_choice(snapshot):
            return inner_search(env, snapshot, *args, **kwargs)
        if 'hard_deadline' in kwargs:
            kwargs['hard_deadline'] = max(kwargs['hard_deadline'], time.monotonic()+SETUP_SECONDS)
        goals_for, opening_goals = p.goals_for, planning.goals
        p.goals_for = planning.goals = no_goals
        try:
            return inner_search(env, snapshot, *args, **kwargs)
        finally:
            p.goals_for, planning.goals = goals_for, opening_goals
    for name, value in vars(inner_search).items():
        if name.startswith('_') and isinstance(value, bool):
            setattr(search, name, value)
    search._setup_roots = True
    p.search = search


def setup_near_scores(env, snapshot, scores):
    """B: every opponent-adjacent start above every other start; order kept inside each group."""
    from current_actions.conservation import blocked
    near = _near_places(snapshot, scores)
    places = [i for i, c in enumerate(snapshot['candidates'])
              if c['action'].get('type') == 'PlaceStartingStructure' and not blocked(scores[i])]
    far = [i for i in places if i not in near]
    if not near or not far:
        return scores
    gap = max(scores[i][0] for i in far) - min(scores[i][0] for i in near) + 1
    if gap <= 0:
        return scores
    lifted = list(scores)
    for i in near:
        lifted[i] = (scores[i][0]+gap, f'{scores[i][1]}; next to an opponent first', *scores[i][2:])
    return lifted


def _focus_key(tracks):
    focus = [t for t in tracks if t != 'navigation' and tracks[t] >= FOCUS_FROM]
    if focus:
        best = max(tracks[t] for t in focus)
        return lambda t: (0 if t in focus and tracks[t] == best else 1, -tracks[t])
    if tracks['navigation'] < FOCUS_FROM:
        return lambda t: (0 if t == 'navigation' else 1, -tracks[t])
    # Navigation 2 reached and no track chosen yet: the other tracks by level, Navigation after
    # them. Lab 048 ranked Navigation first here too (it was the highest level), so the focus never
    # left it: rounds 1-3 Taklons 18 of 25 advances on Navigation, Terrans 13 of 23 (A: 0, 0).
    return lambda t: (1 if t == 'navigation' else 0, -tracks[t])


def research_focus_scores(env, snapshot, scores):
    """D: the research moves' scores, best first, handed to the tracks in focus order."""
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or 'ActionPhase' not in state['phase']:
        return scores
    research = [i for i, c in enumerate(snapshot['candidates'])
                if c['action'].get('type') == 'ResearchAdvance' and not blocked(scores[i])
                and c['action'].get('track') in TRACK_KEYS
                and not (c['action']['track'] == 'GaiaProject' and _early_terrans_gaia(state, actor))]
    if len(research) < 2:
        return scores
    tracks = state['players'][actor]['research_tracks']
    key = _focus_key(tracks)
    by_score = sorted(research, key=lambda i: -scores[i][0])
    order = sorted(research, key=lambda i: (key(TRACK_KEYS[snapshot['candidates'][i]['action']['track']]),
                                            by_score.index(i)))
    lifted = list(scores)
    for i, source in zip(order, by_score):
        if i != source:
            lifted[i] = (scores[source][0], f'{scores[i][1]}; research focus', *scores[i][2:])
    return lifted


def install_reach(setup=True, plus=True, focus=True):
    """setup: A and B; plus: C; focus: D. Lab 048 ran all four together."""
    if setup:
        _guide['setup_soft'] = True
        _wrap_rank('_setup_near', setup_near_scores)
        install_setup_search()
    if plus:
        _guide['reach_plus'] = True
    if focus:
        _guide['research_focus'] = True
        _wrap_rank('_research_focus', research_focus_scores)


def guide_r1_charge3_lf_more_vm_lf_ts_reach(seed, **kwargs):
    """Teacher factory: guide_r1_charge3_lf_more_vm_lf_ts plus distinct setup comparisons,
    opponent-adjacent starts ordered first (not blocking), range +1 in colony options and booster 5,
    and research focus order (install_reach)."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts(seed, **kwargs)
    install_reach()
    return teacher


# Lab 048 parts, one at a time on guide_r1_charge3_lf_more_vm_lf_ts (cause of the Taklons and
# Terrans loss).
def guide_r1_charge3_lf_more_vm_lf_ts_reach_setup(seed, **kwargs):
    """Teacher factory: reach parts A and B only (setup comparisons, opponent-adjacent starts first)."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts(seed, **kwargs)
    install_reach(plus=False, focus=False)
    return teacher


def guide_r1_charge3_lf_more_vm_lf_ts_reach_plus(seed, **kwargs):
    """Teacher factory: reach part C only (range +1 in colony options and booster 5)."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts(seed, **kwargs)
    install_reach(setup=False, focus=False)
    return teacher


def guide_r1_charge3_lf_more_vm_lf_ts_reach_focus(seed, **kwargs):
    """Teacher factory: reach part D only (research focus order)."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts(seed, **kwargs)
    install_reach(setup=False, plus=False)
    return teacher


# ── former_use (user 2026-10-13, lab 052 pair-006/game-1 Taklons) ──────────────────────
# "1라운드에 가이아 포머를 먹었으면 적어도 즉시 포밍 1회 + 소행성 던지기는 해야지." In 052 the stack
# advanced the Gaia track 19 times with Taklons and formed twice (Geodens 15 and 3). Causes in the
# lf_frozen colony options:
# 1. A free former with its tokens already priced the Transdim planet in reach as a mine built next
#    round, and a formed planet priced the same, so forming itself gained nothing while the Gaia
#    advance that brought the former gained the whole option. Now the option is counted only for a
#    planet actually being formed (the `reserved` ones).
# 2. Asteroids were not colony options at all. With an idle former each Asteroid in reach is one
#    (rulebook cost: range QIC only; the former is used up, at no price of its own — an idle former
#    has no other value after 1).
# 3. Order only: while a former is idle and forming or an Asteroid mine is legal, the best of those
#    goes ahead of a Gaia track advance that outranks it.
def former_first_scores(env, snapshot, scores):
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or 'ActionPhase' not in state['phase']:
        return scores
    if not _idle_formers(state['players'][actor]):
        return scores
    hexes = state['board']['hexes']

    def uses_former(action):
        if action.get('type') == 'GaiaFormation':
            return True
        if action.get('type') != 'Build':
            return False
        planet = (hexes.get(str(action.get('coord'))) or {}).get('planet')
        return bool(planet) and planet['planet_type'] == 'Asteroid' and not planet['is_gaia_formed']

    candidates = snapshot['candidates']
    player = state['players'][actor]
    uses = [i for i, c in enumerate(candidates) if uses_former(c['action']) and not blocked(scores[i])
            and not _not_yet(state, player, c['action'])]
    gaia = [i for i, c in enumerate(candidates) if c['action'].get('type') == 'ResearchAdvance'
            and c['action'].get('track') == 'GaiaProject' and not blocked(scores[i])]
    if not uses or not gaia:
        return scores
    best = max(uses, key=lambda i: scores[i][0])
    top = max(scores[i][0] for i in gaia)
    if scores[best][0] > top:
        return scores
    lifted = list(scores)
    lifted[best] = (top+0.001, f'{scores[best][1]}; former_use: idle former before the Gaia track',
                    *scores[best][2:])
    return lifted


# ── brainstone_ships (user 2026-10-13) ─────────────────────────────────────────────────
# Lost Fleet: when Taklons explore a spaceship the Brainstone goes to the Gaia area until the next
# Gaia phase (engine apply_explore_spaceship_impl). The frozen "no Brainstone Gaia commitment"
# policy, written for Gaia projects, therefore blocked every Taklons ship entry: 0 entries in both
# arms of lab 052. User: "1단계 브레인스톤만 턴 마지막에 쓰면 손해가 없는데" — a Brainstone in bowl I
# loses nothing by waiting there. Ship entry is allowed while the Brainstone is in bowl I; the
# policy stands for everything else.
# Timing (user, same day: "더이상 파워를 안 받겠다 싶은 때, 혹은 덜 받더라도 꼭 필요한 게 있을 때"): while an
# opponent who has not passed has a building within 2 hexes of ours (it can still give a charge),
# the entry ranks just above passing, so it comes after every move worth making; a plan whose
# rollout needs the ship earlier can still win the comparison. With no such opponent the entry
# keeps its own score. Order only.
SHIP_ENTRIES = frozenset({'ExploreSpaceship', 'RoundBoosterRangeExploreSpaceship', 'TwilightRangeExploreSpaceship'})
ENTRY_BEFORE_PASS = 0.001


def taklons_ship_timing_scores(env, snapshot, scores):
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or 'ActionPhase' not in state['phase']:
        return scores
    player = state['players'][actor]
    if player['faction'] != 'Taklons':
        return scores
    entries = [i for i, c in enumerate(snapshot['candidates']) if c['action'].get('type') in SHIP_ENTRIES
               and not blocked(scores[i]) and scores[i][0] > ENTRY_BEFORE_PASS]
    if not entries:
        return scores
    charging = any(not other['passed'] and any(_value.distance(s['hex'], b['hex']) <= 2
                                                for s in player['structures'] for b in other['structures'])
                   for other in state['players'] if other is not player)
    if not charging:
        return scores
    lifted = list(scores)
    for i in entries:
        lifted[i] = (ENTRY_BEFORE_PASS, f'{scores[i][1]}; Taklons ship entry after the moves worth making '
                     '(a neighbour can still charge the Brainstone)', *scores[i][2:])
    return lifted


def install_brainstone_ships():
    import four_factions.quick as quick
    import four_factions.teacher as ff_teacher
    _wrap_rank('_taklons_ship_timing', taklons_ship_timing_scores)
    inner = ff_teacher.brainstone_committed
    if getattr(inner, '_ships', False):
        return

    def brainstone_committed(before, after, actor):
        if not inner(before, after, actor):
            return False
        was, now = before['state']['players'][actor], after['state']['players'][actor]
        explored = len(now.get('explored_ships') or []) > len(was.get('explored_ships') or [])
        return not (explored and was['resources']['power']['brainstone'] == 'Area1')
    brainstone_committed._ships = True
    ff_teacher.brainstone_committed = quick.brainstone_committed = brainstone_committed


def guide_r1_charge3_lf_more_vm_lf_ts_ships(seed, **kwargs):
    """Teacher factory: guide_r1_charge3_lf_more_vm_lf_ts where Taklons may explore a spaceship
    while the Brainstone is in bowl I (brainstone_ships)."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts(seed, **kwargs)
    install_brainstone_ships()
    return teacher


def install_former_use():
    _guide['former_use'] = True
    _wrap_rank('_former_use', former_first_scores)


def guide_r1_charge3_lf_more_vm_lf_ts_former(seed, **kwargs):
    """Teacher factory: guide_r1_charge3_lf_more_vm_lf_ts whose colony options count a Transdim
    planet only once it is being formed and an Asteroid per idle former, and which uses an idle
    former before advancing the Gaia track again (former_use)."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts(seed, **kwargs)
    install_former_use()
    return teacher


# ── when (user 2026-10-13: "경제는 값을 따지기 전에 먼저 언제 올리는지 아나", "전부 넣을 때까지 반복") ──
# The guides' timing rules, one at a time, as order only (HANDOFF lists them with their claim ids).
# 1. research_when — which track a round 1-3 advance takes (lab 053 pair-006/game-1: Terrans took
#    Terraforming with the lab's tile and Science next, Economy ranked last at 0.0):
#    - Navigation while below level 2, when range 2 brings a home-type or Gaia planet within reach
#      that is out of reach now (B18-03 "2사거리로 이득이 있으면 항해 2가 가장 좋음");
#    - else the Gaia track: from level 0 with an Asteroid in reach (SH3-03 "소행성에 지을 수 있으면
#      가이아"), or below level 2 with two Transdim planets in reach (B18-03);
#    - else Economy up to level 2 while Navigation is below 2 (B18-03 "메리트가 없으면 경제 2",
#      SH3-03, B19-06 "항해 2를 먼저 찍었으면 경제는 굳이 안 감");
#    - else no preference.
#    The preferred track swaps scores with the best research move, and among the tech-tile
#    choices of one upgrade with the best track of the same tile. Research against other moves
#    and the tile itself are unchanged. The Terrans' early Gaia rule (guide_r1 2) stands.
WHEN_ROUNDS = (1, 2, 3)
WHEN_LEVEL = 2
WHEN_TRANSDIM = 2


def _in_reach(state, player, planet_types):
    """{coord: planet type} of the free planets of those types in range without a QIC."""
    return {coord: planet['planet_type']
            for coord, planet, qic in _value.targets(state, player, planet_types) if not qic}


def research_when_track(state, actor):
    """The action name of the track the guides advance now, or None."""
    player = state['players'][actor]
    tracks = player['research_tracks']
    home = _value.HOME.get(player['faction'])
    wide = tuple(k for k in (home, 'Gaia') if k)
    now = _in_reach(state, player, (*wide, 'Asteroid', 'Transdim'))
    if tracks['navigation'] < WHEN_LEVEL:
        plus = _nav_plus(player)
        if plus is not None and set(_in_reach(state, plus[0], wide)) - set(now):
            return 'Navigation'
    return _gaia_or_economy(state, actor, list(now.values()))


def _gaia_or_economy(state, actor, kinds):
    """The Gaia and Economy branches of rule 1; kinds = planet types in reach without a QIC."""
    tracks = state['players'][actor]['research_tracks']
    if not _early_terrans_gaia(state, actor):
        if not tracks['gaia'] and 'Asteroid' in kinds:
            return 'GaiaProject'
        if tracks['gaia'] < WHEN_LEVEL and kinds.count('Transdim') >= WHEN_TRANSDIM:
            return 'GaiaProject'
    if tracks['economy'] < WHEN_LEVEL and tracks['navigation'] < WHEN_LEVEL:
        return 'Economy'
    return None


# 1b. research_defend — rule 1 as the source words it (lab 054: rule 1 sent three factions to
#    Navigation, 0-3 advances to 15-20, and lost charges; user 2026-10-14). B18 p.3 "1라운드에 진보할
#    연구 트랙": "이득이라는 것은 2사거리나 4사거리의 모행성, 가이아 행성, 인접 종족의 모행성을 2개 이상 수비할
#    수 있다거나 …", "부스터와 시작 정보 큐브만으로도 행성 2개가 충분히 확보가 된다든가, 아카데미를 올릴 것이라서
#    … 메리트가 없다면 경제 2단계". Against rule 1:
#    - round 1 only, and two or more planets worth defending must come newly within reach;
#    - not when the range, QIC and range booster held already reach two of them, nor with an
#      Academy built (the plan's Academy target is not visible to the ranking; this is the proxy);
#    - what is worth defending (user): a home-type planet only when a faction whose home is one
#      terraforming step away plays ("인접 종족이 아니면 수비를 늦게 해도 된다" — of the four fixed
#      factions Terrans have none). Without such a faction the planets are still to be gained,
#      only later ("인접 종족이 없을수록 경제나 과학 올린 후에 항해술"): Economy to level 2 first (B01
#      p.11 "경제 2 또는 4"), then Navigation, this part also in rounds 2-3. Science instead of
#      Economy when the third federation is sure (B18), which the user defines as: home planets
#      near and easy to defend, and the advanced tile above Science worth more than the final
#      goals. Computed as: two or more free home-type planets within the range and QIC held
#      that no opponent reaches without a QIC (all of them when no neighbouring faction plays),
#      and lf_advanced_option of that tile above the frozen standings value. The round goals
#      are not compared (no such value exists). Science then goes on to level 4; a planet one step from home only with a cheap step at hand
#      ("삽을 얻기 쉬우면"); a Gaia planet only if an opponent reaches it too and a mine there brings
#      a new planet within reach or joins two of our building groups ("전략적 요충지인지 판단").
#    The Gaia and Economy branches are rule 1's, in round 1 only. The round 1 mine scoring case
#    of the source is not in.
DEFEND_ROUNDS = (1,)
DEFEND_PLANETS = 2
LINK_HEXES = 2
RANGE_BOOSTER = (8, 3)   # booster id, range added to one build per round
SCIENCE_LEVEL = 4        # B18 p.3: "과학을 올리기 시작했으면 최대한 빨리 과학 4단계"
SCIENCE_TILE = 5         # index of the Science track in research_board.advanced_tech_tiles


def _home_type(player):
    from faction_teachers.profiles import profiles
    return _value.HOME.get(player['faction']) or profiles()[player['faction']].home


def _ring_gap(a, b):
    """Terraforming steps between two planet types, None off the ring."""
    from economy.teacher import RING
    if a not in RING or b not in RING:
        return None
    gap = abs(RING.index(a)-RING.index(b))
    return min(gap, len(RING)-gap)


def _cheap_step(state, player):
    """A terraforming step at hand: booster, TF Mars, an open power action, or 1 ore per step."""
    from economy.teacher import ORE_PER_STEP
    power = player['resources']['power']
    spendable = power['bowl3'] + power['bowl2']//2
    used = state.get('used_power_actions', [])
    return (player['booster'] == 12 or 'TFMars' in (player.get('explored_ships') or [])
            or ORE_PER_STEP[player['research_tracks']['terraforming']] == 1
            or any(i not in used and cost <= spendable for i, (cost, _) in TERRAFORM_POWER_ACTIONS.items()))


def _groups(hexes):
    """Building hexes chained within LINK_HEXES of each other."""
    groups = []
    for coord in hexes:
        near = [g for g in groups if any(_value.distance(coord, h) <= LINK_HEXES for h in g)]
        groups = [g for g in groups if g not in near] + [{coord}.union(*near)]
    return groups


def _free_planets(state, planet_types):
    for coord, cell in state['board']['hexes'].items():
        planet = cell['planet']
        if planet and planet['owner'] is None and not cell['structures'] and planet['planet_type'] in planet_types:
            yield coord, planet


def _key_site(state, player, coord, reach):
    """A mine on coord joins two of our building groups, or brings within `reach` a planet to
    build on that our buildings do not reach."""
    from economy.teacher import RING, path_distance
    starts = [s['hex'] for s in player['structures']]
    if sum(any(_value.distance(coord, h) <= LINK_HEXES for h in g) for g in _groups(starts)) >= 2:
        return True
    return any(path_distance(state, [coord], other) <= reach < path_distance(state, starts, other)
               for other, _ in _free_planets(state, (*RING, 'Gaia')) if other != coord)


def _defend_counts(state, player, contested=True):
    """(new, held): planets worth defending that the next range step brings within reach, and
    those the range, QIC and range booster held already reach. contested=False counts the
    home-type planets without a neighbouring faction too (planets to gain, in no hurry)."""
    from economy.teacher import RING, path_distance
    plus = _nav_plus(player)
    if plus is None:
        return 0, 0
    plus, home = plus[0], _home_type(player)
    others = [o for o in state['players'] if o is not player]
    neighbour = not contested or any(_ring_gap(home, _home_type(o)) == 1 for o in others)
    step = _cheap_step(state, player)
    types = (*(k for k in RING if (k == home and neighbour) or (step and _ring_gap(home, k) == 1)), 'Gaia')
    rivals = {coord for o in others for coord, _, _ in _value.targets(state, o, ('Gaia',))}
    reach = _value.navigation(plus)

    def worth(coord, planet):
        return planet['planet_type'] != 'Gaia' or (coord in rivals and _key_site(state, player, coord, reach))
    now = set(_in_reach(state, player, types))
    new = [c for c, p, qic in _value.targets(state, plus, types) if not qic and c not in now and worth(c, p)]
    held = {c for c, p, _ in _value.targets(state, player, types) if worth(c, p)}
    booster, far = RANGE_BOOSTER
    if player['booster'] == booster:
        starts = [s['hex'] for s in player['structures']]
        held |= {c for c, p in _free_planets(state, types) if c not in held and worth(c, p)
                 and path_distance(state, starts, c) <= _value.navigation(player)+far}
    return len(new), len(held)


def _science_sure(state, actor):
    """The user's "3연방이 확실하다" (see rule 1b)."""
    player = state['players'][actor]
    home = _home_type(player)
    others = [o for o in state['players'] if o is not player]
    near = {coord for coord, _, _ in _value.targets(state, player, (home,))}
    if any(_ring_gap(home, _home_type(o)) == 1 for o in others):
        near -= {coord for o in others for coord in _in_reach(state, o, (home,))}
    if len(near) < DEFEND_PLANETS:
        return False
    tile = state['research_board']['advanced_tech_tiles'][SCIENCE_TILE]
    return tile is not None and lf_advanced_option(state, player, tile) > _value.standings(state, actor)


def research_defend_track(state, actor):
    """The action name of the track an advance takes (rule 1b), a tuple when either of two
    will do, or None."""
    player = state['players'][actor]
    tracks, early = player['research_tracks'], state['round'] in DEFEND_ROUNDS
    academy = any((s['kind'] if isinstance(s['kind'], str) else next(iter(s['kind']))) == 'Academy'
                  for s in player['structures'])

    def merit(contested):
        new, held = _defend_counts(state, player, contested)
        return new >= DEFEND_PLANETS and held < DEFEND_PLANETS
    wide = tracks['navigation'] < WHEN_LEVEL and not academy
    if wide and early and merit(True):
        return 'Navigation'
    # Science: begun in round 1 when the third federation is sure, then on to level 4.
    if (tracks['science'] < SCIENCE_LEVEL and (early or tracks['science'] >= WHEN_LEVEL)
            and _science_sure(state, actor)):
        return 'Science'
    if wide and merit(False):
        # Nobody is near enough in colour to take the planets: Economy 2 (or the Science
        # climb) first, Navigation after it (also in rounds 2-3).
        if tracks['economy'] >= WHEN_LEVEL or tracks['science'] >= SCIENCE_LEVEL:
            return 'Navigation'
        return 'Economy' if early else None
    if not early:
        return None
    return _gaia_or_economy(state, actor, list(_in_reach(state, player, ('Asteroid', 'Transdim')).values()))


def _when_groups(candidates):
    """Candidate indices that differ only in the track advanced: {key: {track: index}}."""
    groups = {}
    for i, candidate in enumerate(candidates):
        action = candidate['action']
        if action.get('type') == 'ResearchAdvance':
            key, track = 'research', action.get('track')
        else:
            choice = action.get('tech_tile_choice')
            if not isinstance(choice, dict) or not choice.get('advance_track'):
                continue
            track = choice['advance_track']
            key = json.dumps({**action, 'tech_tile_choice': {**choice, 'advance_track': None}}, sort_keys=True)
        groups.setdefault(key, {})[track] = i
    return groups


def research_when_scores(env, snapshot, scores, *, track_of=None, rounds=WHEN_ROUNDS):
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or 'ActionPhase' not in state['phase'] or state['round'] not in rounds:
        return scores
    groups = [g for g in _when_groups(snapshot['candidates']).values() if len(g) > 1]
    if not groups:
        return scores
    track = (track_of or research_when_track)(state, actor)
    if track is None:
        return scores
    lifted = list(scores)
    for group in groups:
        open_moves = [i for i in group.values() if not blocked(scores[i])]
        wants = [group[t] for t in ((track,) if isinstance(track, str) else track) if group.get(t) in open_moves]
        if not wants:
            continue
        want = max(wants, key=lambda i: scores[i][0])
        best = max(open_moves, key=lambda i: scores[i][0])
        if scores[best][0] > scores[want][0]:
            lifted[want] = (scores[best][0], f'{scores[want][1]}; research when: {track} now', *scores[want][2:])
            lifted[best] = (scores[want][0], *scores[best][1:])
    return lifted


def research_defend_scores(env, snapshot, scores):
    return research_when_scores(env, snapshot, scores, track_of=research_defend_track)


# 2. contested_first — the order of the moves inside a round (SH3-07 "빼앗길 수 있는 액션(QIC 액션·
#    파워 액션·행성에 광산)을 먼저, 언제든 할 수 있는 액션(업그레이드·4지식 진보)은 최대한 뒤로"; SH1-07:
#    the ship actions are shared too, "내가 안 누르면 남이 먹음"). While an opponent has not passed,
#    the best move another player can take away that still ranks above passing goes just ahead of
#    the best upgrade or research advance ranked above it (their scores stay, so the tile and track
#    order of rule 1 holds), provided the upgrade or advance can still be paid afterwards — without
#    that the rollouts built mines until nothing else was affordable (053 p006-g1 step 16: 8 mines
#    and 15 ore left by round 4) and no comparison finished inside the 20 s cap.
#    Ship entries are not in the list (their
#    timing is its own rule). Order only: both moves stay worth making, and a plan whose rollout
#    needs the upgrade first can still win the comparison (the guide's "예외 있음").
CONTESTED = frozenset({
    'PowerAction', 'Build', 'GaiaFormation', 'RoundBoosterRangeBuild', 'RoundBoosterRangeGaiaFormation',
    'RoundBoosterTerraformBuild', 'RoundBoosterImmediateGaiaFormation', 'ExamineArtifact',
    'SpaceshipCreditTerraform', 'TwilightFreeResearchLab', 'TwilightReplayFederationToken',
    'TwilightRangeBuild', 'TwilightRangeGaiaFormation', 'RebellionFreeTradingStation',
    'RebellionCreditsAndQic', 'RebellionGainTechTile', 'TFMarsTechBonus', 'TFMarsGaiaFormation',
    'EclipsePlanetTypeBonus', 'EclipseResearchBoost', 'EclipseAsteroidMine'})
ANYTIME = frozenset({'Upgrade', 'ResearchAdvance'})
CONTESTED_AHEAD = 0.001
WHEN_STOCK = ('ore', 'credits', 'knowledge', 'qic')
_when_root = []   # decision ids of the searches in progress (see _install_when_root)


def contested_first_scores(env, snapshot, scores):
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or 'ActionPhase' not in state['phase']:
        return scores
    # Only the decision being made: inside a search every other ranking is a rollout step, and
    # with the rule there the rollouts ran so long that no comparison finished in the 20 s cap.
    if _when_root and _when_root[-1] != snapshot['decision_id']:
        return scores
    if all(other['passed'] for i, other in enumerate(state['players']) if i != actor):
        return scores
    candidates = snapshot['candidates']
    passing = max((scores[i][0] for i, c in enumerate(candidates)
                   if c['action'].get('type') == 'Pass' and not blocked(scores[i])), default=0.0)

    def best(kinds):
        found = [i for i, c in enumerate(candidates) if c['action'].get('type') in kinds
                 and not blocked(scores[i]) and scores[i][0] > passing]
        return max(found, key=lambda i: scores[i][0]) if found else None

    # Rule 3: in rounds 1-2 a ship entry is a move to make early too. An entry held back to
    # just above passing (Taklons timing) is not above `passing` here and stays where it is.
    early_entry = _guide['ship_when'] and state['round'] in SHIP_EARLY_ROUNDS
    passing = max(passing, ENTRY_BEFORE_PASS) if early_entry else passing
    contested, anytime = best(CONTESTED | SHIP_ENTRIES if early_entry else CONTESTED), best(ANYTIME)
    if contested is None or anytime is None or scores[contested][0] >= scores[anytime][0]:
        return scores
    # "Later" must stay possible: what the upgrade or advance costs is still held after the
    # contested move (engine fork of both moves, no price table).
    held = state['players'][actor]['resources']

    def after(index):
        branch = env.fork(snapshot['decision_id'], index)
        return json.loads(branch.snapshot_json())['state']['players'][actor]['resources']
    paid, left = after(anytime), after(contested)
    if any(left[k] < held[k]-paid[k] for k in WHEN_STOCK):
        return scores
    lifted = list(scores)
    lifted[contested] = (scores[anytime][0]+CONTESTED_AHEAD, f'{scores[contested][1]}; contested first',
                         *scores[contested][2:])
    return lifted


# 3. ship_when — when to enter which ship.
#    - Which ship, by round (order among the entry moves only; their scores are handed out again
#      in this order, so entry against other moves is unchanged): rounds 1-2 Rebellion first
#      (C027, LF4-06: its 3-QIC tech action is the second best move of round 1 and "1–2R 두 번 다
#      놓치면 입장 의미 없음"); round 1 Eclipse last (C031: "하드쉬 외엔 1R부터 6돈을 쓸 여유가 없어 보통
#      2R부터"); from round 3 TF Mars last (C028: "3–4R이면 가장 안 좋은 함대").
#    - Early (LF3-04 "들어갈 거면 일찍", LF4-04 "입장 턴을 미리 없애 우선권 확보", LF3-05 upgrades are
#      delayed for the entry points): in rounds 1-2 an entry counts among the moves of rule 2 that
#      go before upgrades and research. The Taklons timing (brainstone_ships, user) stands.
SHIP_EARLY_ROUNDS = (1, 2)


def _ship_when_key(ship, round_):
    if round_ in SHIP_EARLY_ROUNDS and ship == 'Rebellion':
        return 0
    if (round_ == 1 and ship == 'Eclipse') or (round_ >= 3 and ship == 'TFMars'):
        return 2
    return 1


def ship_when_scores(env, snapshot, scores):
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or 'ActionPhase' not in state['phase']:
        return scores
    entries = [i for i, c in enumerate(snapshot['candidates']) if c['action'].get('type') in SHIP_ENTRIES
               and not blocked(scores[i])]
    if len({snapshot['candidates'][i]['action'].get('ship') for i in entries}) < 2:
        return scores
    by_score = sorted(entries, key=lambda i: -scores[i][0])
    order = sorted(entries, key=lambda i: (_ship_when_key(snapshot['candidates'][i]['action'].get('ship'),
                                                         state['round']), by_score.index(i)))
    lifted = list(scores)
    for i, source in zip(order, by_score):
        if i != source:
            lifted[i] = (scores[source][0], f'{scores[i][1]}; ship when', *scores[i][2:])
    return lifted


# 4. leech_when — which charges to accept, by round (B2-02 "5R까지 2충전은 … 수락, 3충전도 3–4R까지는
#    수락, 4충전 이상은 정말 중요한 타이밍이 아니면 거절"). The answer the guide gives swaps scores with
#    the other one when it ranks lower; a comparison can still pick the other ("정말 중요한 타이밍").
#    Charges outside these lines (a free 1-charge, 2 in round 6, 3 from round 5) keep their order.
#    The VP cost is read from the engine (charge - 1). SH1-11's exceptions (keeping 5 VP for a
#    ship, tokens to spend) are not in.
LEECH_ACCEPT_UNTIL = {1: 5, 2: 4}   # VP cost: last round in which the charge is accepted
LEECH_DECLINE_FROM = 3              # VP cost (a 4-charge)


def _leech_when(cost, round_, keep_ship=False):
    """True accept, False decline, None no guidance. leech_lf (SH1-11, the Lost Fleet text over
    B2-02 for the early rounds): "초반엔 함선 5점을 남기거나 토큰을 써야 하는 상황이 아니면 받는 게 좋음" —
    in rounds 1-2 every charge is accepted unless it leaves fewer VP than a ship entry costs while a
    ship can still be entered (then no guidance; C023 "함대 하나를 포기하고 파워를 받는 게 나을 수 있음")."""
    if _guide['leech_lf'] and round_ in LEECH_LF_ROUNDS and cost:
        return None if keep_ship else True
    if cost >= LEECH_DECLINE_FROM:
        return False
    return True if round_ <= LEECH_ACCEPT_UNTIL.get(cost, 0) else None


def leech_when_scores(env, snapshot, scores):
    from current_actions.conservation import blocked
    actor = snapshot.get('player')
    answers = {c['action'].get('accept'): i for i, c in enumerate(snapshot['candidates'])
               if c['action'].get('type') == 'ChargePower'}
    if actor is None or True not in answers or False not in answers:
        return scores
    after = json.loads(env.fork(snapshot['decision_id'], answers[True]).snapshot_json())
    cost = snapshot['state']['players'][actor]['vp'] - after['state']['players'][actor]['vp']
    keep_ship = (_guide['leech_lf'] and after['state']['players'][actor]['vp'] < SHIP_VP
                 and _ship_open(snapshot['state'], snapshot['state']['players'][actor]))
    answer = _leech_when(cost, snapshot['state']['round'], keep_ship)
    if answer is None and keep_ship and snapshot['state']['round'] in LEECH_LF_ROUNDS:
        # A tie still goes to accepting (C023 "1R 파워 거부는 손해가 막심"); a ranked decline stands.
        accept, decline = answers[True], answers[False]
        if scores[accept][0] == scores[decline][0] and not blocked(scores[accept]):
            lifted = list(scores)
            lifted[accept] = (scores[accept][0]+AHEAD, f'{scores[accept][1]}; leech when: tie to accept',
                              *scores[accept][2:])
            return lifted
    if answer is None:
        return scores
    want, other = answers[answer], answers[not answer]
    if blocked(scores[want]) or blocked(scores[other]) or scores[want][0] > scores[other][0]:
        return scores
    lifted = list(scores)
    if scores[want][0] == scores[other][0]:
        # A tie went to the first candidate (decline, 056 p005-g1 step 62); leech_lf breaks it.
        if not _guide['leech_lf']:
            return scores
        lifted[want] = (scores[want][0]+AHEAD, f'{scores[want][1]}; leech when: cost {cost} VP', *scores[want][2:])
        return lifted
    lifted[want] = (scores[other][0], f'{scores[want][1]}; leech when: cost {cost} VP', *scores[want][2:])
    lifted[other] = (scores[want][0], *scores[other][1:])
    return lifted


# 5-9. Moves the guides say not to make yet: each drops to just below passing while its condition
#    holds (order only: the root ranking no longer picks it, a comparison still can).
#    5 artifact_when — a resource or income artifact (engine ids below) only in round 1 and only
#      if three power tokens are left after the six it costs (C029, LF1-11 "극초반은 시작 토큰 6개가
#      이미 초과", LF4-07 "파워 토큰이 3개는 남아야 게임이 정상 진행"). VP artifacts are untouched.
#    8 mine_stock — the last mine in hand is not built on an ordinary planet while a free
#      Asteroid or Proto planet is in reach (LF3-14 "광산을 수중에 1개는 남겨야 원시 행성·소행성을 가져갈 수
#      있음").
#    9 taklons_pi — no Taklons Planetary Institute before round 4 (B10-02 "4–6R에 위성용 토큰 확보 목적").
#    twilight_knowledge — the Twilight range action (1 knowledge) not while the knowledge held is
#      a multiple of 4 (user: "트와일라잇은 지식이 남을 때 얘기, 4지식으로 트랙을 올릴 수 있는데 안 올리면 안 됨").
#    Not in: 7 (B2-06 "다음 라운드 지식이 짝수가 되게" names no move to reorder), 10 (the base game's
#    4-QIC action is not one of the Lost Fleet QIC action spaces).
RESOURCE_ARTIFACTS = frozenset({2, 3, 6, 7, 9})   # engine artifact_effect: tokens, income, resources
ARTIFACT_TOKENS = 6                               # engine ExamineArtifact: "Discards 6 power"
ARTIFACT_TOKENS_LEFT = 3
ARTIFACT_ROUND = 1
TAKLONS_PI_FROM_ROUND = 4
TWILIGHT_RANGE = frozenset({'TwilightRangeBuild', 'TwilightRangeGaiaFormation', 'TwilightRangeExploreSpaceship'})
SPARE_MINE_PLANETS = ('Asteroid', 'ProtoPlanet')
NOT_YET = 0.001
POWER_COST = {1: 7, 2: 5, 3: 4, 4: 4, 5: 4, 6: 3, 7: 3}   # engine PowerAction id: power (frozen power_purpose)


def _kind(structure):
    kind = structure['kind'] if 'kind' in structure else structure
    return kind if isinstance(kind, str) else next(iter(kind))


def _not_yet(state, player, action):
    """Why the guides hold this move back now, or None."""
    kind = action.get('type')
    if _guide['artifact_when'] and kind == 'ExamineArtifact' and action.get('artifact') in RESOURCE_ARTIFACTS:
        power = player['resources']['power']
        left = sum(power[k] for k in ('bowl1', 'bowl2', 'bowl3')) - ARTIFACT_TOKENS
        if state['round'] != ARTIFACT_ROUND or left < ARTIFACT_TOKENS_LEFT:
            return f'resource artifact only in round {ARTIFACT_ROUND} with {ARTIFACT_TOKENS_LEFT} tokens left'
    if _guide['mine_stock'] and kind == 'Build':
        mines = sum(_kind(s) == 'Mine' for s in player['structures'])
        if mines == MINE_LIMIT-1 and _in_reach(state, player, SPARE_MINE_PLANETS):
            return 'last mine kept for an Asteroid or Proto planet'
    if (_guide['taklons_pi'] and kind == 'Upgrade' and player['faction'] == 'Taklons'
            and action.get('to') == 'PlanetaryInstitute' and state['round'] < TAKLONS_PI_FROM_ROUND):
        return f'Taklons Planetary Institute from round {TAKLONS_PI_FROM_ROUND}'
    if _guide['twilight_knowledge'] and kind in TWILIGHT_RANGE:
        knowledge = player['resources']['knowledge']
        if knowledge >= NAV_KNOWLEDGE and knowledge % NAV_KNOWLEDGE == 0:
            return 'Twilight range only with knowledge left over after research'
    if (_guide['burn_when'] and kind == 'FreeAction' and action.get('kind') == 'BurnPower'
            and not (_guide['faction_more'] and player['faction'] == 'Taklons'
                     and _tokens(player) > TAKLONS_TOKENS)):
        bowl3, burned = player['resources']['power']['bowl3'], action.get('count', 1)
        used = state.get('used_power_actions', [])
        if not any(bowl3 < cost <= bowl3+burned for id_, cost in POWER_COST.items() if id_ not in used):
            return 'burn only for a power action it pays for'
    if (_guide['terrans_former'] and kind == 'Build' and player['faction'] == 'Terrans'
            and _asteroid(state, action) and _gaia_room(player)
            and _in_reach(state, player, ('Transdim',))):
        return 'Terrans former goes to a Transdim planet before an Asteroid'
    return _not_yet_more(state, player, action)


def _not_yet_more(state, player, action):
    """The guide_more holds (see GUIDE_MORE)."""
    kind, round_ = action.get('type'), state.get('round', 0)
    if _guide['fed_upgrade'] and kind == 'Upgrade' and str(action.get('coord')) in player.get('federated_hexes', []):
        now = next((_kind(s) for s in player['structures'] if str(s['hex']) == str(action.get('coord'))), None)
        if not (now == 'TradingStation' and action.get('to') == 'ResearchLab'):
            return 'a federated building is not upgraded (only a trading station to a lab)'
    new_ts = (kind == 'Upgrade' and action.get('to') == 'TradingStation') or kind == 'RebellionFreeTradingStation'
    if _guide['ts_excess'] and new_ts and round_ in TS_EXCESS_ROUNDS:
        resources = player['resources']
        stations = sum(_kind(s) == 'TradingStation' for s in player['structures'])
        if stations >= TS_EXCESS_HELD or resources['credits'] >= CREDIT_EXCESS*max(resources['ore'], 1):
            return 'no third trading station or credits beyond 2.5 per ore in rounds 1-3'
    if (_guide['rebellion_ts'] and kind == 'RebellionFreeTradingStation'
            and _next_to_opponent(state, player['player_id'], str(action.get('coord')))):
        return 'Rebellion trading station only where it would cost 6 credits'
    if (_guide['knowledge_action'] and kind == 'PowerAction' and action.get('id') == KNOWLEDGE_ACTION
            and player['resources']['knowledge'] % NAV_KNOWLEDGE != 1):
        return '3-knowledge power action only with 1 knowledge left over'
    if _guide['qic_late'] and kind in QIC_LATE and round_ < QIC_LATE_FROM:
        return f'2-QIC ship actions from round {QIC_LATE_FROM}'
    if _guide['rebellion_qic'] and kind == 'RebellionCreditsAndQic' and player['resources']['qic']+1 < REBELLION_QIC:
        return 'Rebellion 2 knowledge for a QIC only when it makes 3 QIC'
    if _guide['fed_cap'] and kind == 'FormFederation' and _federations(player) >= FEDERATION_CAP:
        return f'no federation beyond {FEDERATION_CAP}'
    if _guide['mines_kept'] and kind == 'Upgrade' and round_ >= MINES_KEPT_FROM:
        now = next((_kind(s) for s in player['structures'] if str(s['hex']) == str(action.get('coord'))), None)
        if now == 'Mine' and sum(_kind(s) == 'Mine' for s in player['structures']) <= MINES_KEPT:
            return f'{MINES_KEPT} mines kept on the board'
    if _guide['ore_terraform'] and kind == 'Build' and _ore_steps(state, player, action):
        return 'no terraforming paid with 3 ore a step'
    if _guide['mine_tile'] and _mine_effect(state, action) and _mines_in_hand(player) == 0:
        return 'its free mine needs a mine in hand'
    if _guide['faction_more']:
        why = _faction_hold(state, player, action)
        if why:
            return why
    if _guide['late_ship'] and kind in SHIP_ENTRIES and round_ >= LATE_SHIP_FROM:
        return f'no ship entry from round {LATE_SHIP_FROM}: fewer than 3 actions left'
    return None


def _ore_steps(state, player, action):
    """A plain Build that pays its terraforming steps at 3 ore each (Terraforming level 0)."""
    from economy.teacher import ORE_PER_STEP, RING
    planet = (state['board']['hexes'].get(str(action.get('coord'))) or {}).get('planet')
    home = _value.HOME.get(player['faction'])
    if not planet or home not in RING or planet['planet_type'] not in RING:
        return False
    gap = abs(RING.index(home)-RING.index(planet['planet_type']))
    return min(gap, 7-gap) > 0 and ORE_PER_STEP[player['research_tracks']['terraforming']] >= ORE_PER_PAID_STEP


def _federations(player):
    return len(player.get('federation_tokens') or []) + len(player.get('gray_federation_tokens') or [])


def _asteroid(state, action):
    planet = (state['board']['hexes'].get(str(action.get('coord'))) or {}).get('planet')
    return bool(planet) and planet['planet_type'] == 'Asteroid' and not planet['is_gaia_formed']


def not_yet_scores(env, snapshot, scores):
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or 'ActionPhase' not in state['phase']:
        return scores
    candidates = snapshot['candidates']
    passing = [scores[i][0] for i, c in enumerate(candidates)
               if c['action'].get('type') == 'Pass' and not blocked(scores[i])]
    if not passing and _guide['hold_no_pass']:
        # Passing blocked (knowledge_spend): a held move goes below every other move instead (moves
        # already pushed down by more than HOLD_DEPTH, such as the early Terrans Gaia advance, aside).
        finite = [s[0] for s in scores if not blocked(s)]
        passing = [min((v for v in finite if v > max(finite)-HOLD_DEPTH), default=min(finite, default=0.0))]
    if not passing:
        return scores
    floor, lifted = min(passing)-NOT_YET, list(scores)
    for i, candidate in enumerate(candidates):
        if blocked(scores[i]) or scores[i][0] <= floor:
            continue
        why = _not_yet(state, state['players'][actor], candidate['action'])
        if why:
            lifted[i] = (floor, f'{scores[i][1]}; not yet: {why}', *scores[i][2:])
    return lifted


# 6. academy_kind — which Academy (B2-07 "1–3R은 지식 아카데미, 5–6R은 QIC 아카데미가 많음"; SH4-02
#    "리벨리온 3QIC를 누를 수 있으면 QIC 아카데미, 아니면 지식 아카데미" before round 3). Among upgrades
#    that differ only in the Academy type the guide's one swaps scores with the better-ranked
#    one. Rebellion explored stands for "can press its 3-QIC action". Round 4 has no guidance.
ACADEMY_SCIENCE_UNTIL = 3
ACADEMY_QIC_FROM = 5


def _academy_kind(state, player):
    if state['round'] <= ACADEMY_SCIENCE_UNTIL:
        return 'Qic' if 'Rebellion' in (player.get('explored_ships') or []) else 'Science'
    return 'Qic' if state['round'] >= ACADEMY_QIC_FROM else None


def academy_kind_scores(env, snapshot, scores):
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or 'ActionPhase' not in state['phase']:
        return scores
    want = _academy_kind(state, state['players'][actor])
    groups = {}
    for i, candidate in enumerate(snapshot['candidates']):
        action = candidate['action']
        to = action.get('to')
        if action.get('type') == 'Upgrade' and isinstance(to, dict) and 'Academy' in to and not blocked(scores[i]):
            key = json.dumps({**action, 'to': 'Academy'}, sort_keys=True)
            groups.setdefault(key, {})[to['Academy']] = i
    if want is None or not groups:
        return scores
    lifted = list(scores)
    for group in groups.values():
        if want not in group or len(group) < 2:
            continue
        mine, best = group[want], max(group.values(), key=lambda i: scores[i][0])
        if scores[best][0] > scores[mine][0]:
            lifted[mine] = (scores[best][0], f'{scores[mine][1]}; academy kind: {want}', *scores[mine][2:])
            lifted[best] = (scores[mine][0], *scores[best][1:])
    return lifted


def _install_when_root():
    """Record the decision a search is deciding (contested_first applies to that one only)."""
    import four_factions.preparation as p
    inner_search = p.search
    if getattr(inner_search, '_when_root', False):
        return

    def search(env, snapshot, *args, **kwargs):
        _when_root.append(snapshot['decision_id'])
        try:
            return inner_search(env, snapshot, *args, **kwargs)
        finally:
            _when_root.pop()
    for name, value in vars(inner_search).items():
        if name.startswith('_') and isinstance(value, bool):
            setattr(search, name, value)
    search._when_root = True
    p.search = search


def install_when(research=True, contested=True, ships=True, defend=False, leech=False, not_yet=(),
                 academy=False):
    if academy:
        _guide['academy_kind'] = True
        _wrap_rank('_academy_kind', academy_kind_scores)
    if not_yet:
        for name in not_yet:
            _guide[name] = True
        _wrap_rank('_not_yet', not_yet_scores)
    if leech:
        _guide['leech_when'] = True
        _wrap_rank('_leech_when', leech_when_scores)
    if defend:
        _guide['research_defend'] = True
        _wrap_rank('_research_defend', research_defend_scores)
    if research:
        _guide['research_when'] = True
        _wrap_rank('_research_when', research_when_scores)
    if ships:
        _guide['ship_when'] = True
        _wrap_rank('_ship_when', ship_when_scores)
    if contested:
        _guide['contested_first'] = True
        _install_when_root()
        _wrap_rank('_contested_first', contested_first_scores)


def guide_r1_charge3_lf_more_vm_lf_ts_when(seed, **kwargs):
    """Teacher factory: guide_r1_charge3_lf_more_vm_lf_ts plus the guides' timing rules added so
    far (install_when): the track of a round 1-3 research advance, moves an opponent can take
    away before upgrades and research, and which ship to enter in which round."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts(seed, **kwargs)
    install_when()
    return teacher


def guide_r1_charge3_lf_more_vm_lf_ts_ships_defend(seed, **kwargs):
    """Teacher factory: guide_r1_charge3_lf_more_vm_lf_ts_ships plus rule 1b alone (research_defend:
    the track of a round 1 advance as the source words it), without rules 1-3 of lab 054."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts_ships(seed, **kwargs)
    install_when(research=False, contested=False, ships=False, defend=True)
    return teacher


WHEN_NOT_YET = ('artifact_when', 'mine_stock', 'taklons_pi', 'twilight_knowledge')


def guide_r1_charge3_lf_more_vm_lf_ts_ships_when_all(seed, **kwargs):
    """Teacher factory: guide_r1_charge3_lf_more_vm_lf_ts_ships plus every timing rule written so
    far: 1b research_defend, 2 contested_first, 3 ship_when, 4 leech_when, 5 artifact_when,
    6 academy_kind, 8 mine_stock, 9 taklons_pi and twilight_knowledge (rule 1 of lab 054 is
    replaced by 1b)."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts_ships(seed, **kwargs)
    install_when(research=False, defend=True, leech=True, not_yet=WHEN_NOT_YET, academy=True)
    return teacher


# ── tech_when (user 2026-10-14, lab 056 pair-005/game-1: "어떤 기술이 언제 좋은지 우선순위가 안 잡혀 있나?") ──
# A standard tech tile was chosen by value alone, and the tile choices of one upgrade rarely reach the
# comparisons (step 25: Terrans took tile 5 at 23.40 over the 4-charge tile 10 at 22.07; no plan rolled
# tile 10 out). The guides' timing for standard tiles (engine ids), order only, among the choices of
# one upgrade:
# - the first standard tile: Terrans and Taklons the 4-charge tile 10 (B04, B3-T4 "테란·타클론에 특히
#   좋음", TK01 "첫 기술은 무조건 4충전"), Xenos the 4-credit tile 3 or tile 10 (HANDOFF 2026-10-05 "제노스
#   4돈/4충전"); any other faction one of B18-03's first tiles "1광석1QIC·4충전·4돈" (4, 10, 3) or the
#   Lost Fleet 1 ore 3 knowledge tile 13 that LF2-03 puts above 1 ore 1 QIC; from an Academy the
#   1 knowledge 1 credit tile 5 (B18-03 "아카데미면 1지식1돈");
# - not yet: tile 7 (7 VP) before round 6 (B3-T8 "최후반 점수 수단", LF2-09 "함대 입장 점수를 벌려고 7점
#   기술을 집지 말 것"), tile 9 (knowledge per planet type) in rounds 1-2 (B3-T7 "초반엔 손해", LF2-04
#   "중반에 얻는 즉발 기술"), the +1 range tile 12 from round 3 or at Navigation 2 (LF2-06 "극초반에만
#   의미", "항해 2단계 이상이면 가치가 작아짐").
# The wanted tile's best choice swaps scores with the group's best, as academy_kind; a held-back tile
# that leads swaps with the best other standard tile. An advanced tile that leads keeps its place.
# Not in: the Gaia-mine tile 8 early (B3-T9 "가이아 테크면 일찍", "의회 먼저 지은 테란은 첫 번째로") —
# LF2-08 and T01: in Lost Fleet "가이아 테크여도 끝까지 안 먹는 경우가 많음"; tile 6 before the first
# federation (B3-T6 names no state the ranking can check); SH3-03's immediate tile when it builds one
# more mine this round (needs the round plan); even knowledge (B3-T3 tile 5, B2-14 the lab) — removed by
# the user (2026-10-15): base-game advice, and in Lost Fleet an odd knowledge has uses (C026: Twilight
# 1-knowledge range, the 1 ore 3 knowledge tile).
TECH_FIRST = {'Terrans': (10,), 'Taklons': (10,), 'Xenos': (3, 10)}
TECH_FIRST_OTHER = (4, 10, 3, 13)
ACADEMY_FIRST_TILE = 5
RANGE_TILE = 12
TECH_FROM_ROUND = {7: 6, 9: 3}   # tile: first round it may lead
# gaia_tile (user 2026-10-15 "그냥 다 넣어"): SH1-04 (Lost Fleet) "가이아 미션이 많거나 글린·테란·아이타처럼
# 포밍 많은 종족이 먹으면 15–30점 엔진" — tile 8 after the first tile for Terrans (of the four fixed
# factions the only one named) or with the Gaia-planet final mission; B04/B19-02 "아카데미로 4충전+가이아
# 3점" agree for Terrans. LF2-08's "확장판에선 약해짐" is the general case these two exceptions leave.
GAIA_MINE_TILE = 8
GAIA_TILE_FACTIONS = frozenset({'Terrans'})


def _tech_wanted(state, player, academy=False):
    """[(tiles, reason)] in the order the guides want them now."""
    wanted = []
    if not player['tech_tiles']:
        if player['faction'] in TECH_FIRST:
            wanted.append((TECH_FIRST[player['faction']], 'first tile'))
        if academy:
            wanted.append(((ACADEMY_FIRST_TILE,), 'first tile from an Academy'))
        wanted.append((TECH_FIRST_OTHER, 'first tile'))
    if (_guide['gaia_tile'] and GAIA_MINE_TILE not in player['tech_tiles']
            and (player['faction'] in GAIA_TILE_FACTIONS
                 or any(t.get('condition') == 'MostGaiaPlanets' for t in state.get('final_scoring_tiles', [])))):
        wanted.append(((GAIA_MINE_TILE,), 'Gaia-mine tile (SH1-04)'))
    return wanted


# faction_more (user 2026-10-15 "다 넣어": the four fixed factions' guides, beyond openings and tracks):
# - Xenos: no federation before the Planetary Institute, and no Institute before a lab (B15-01 "연방 선언
#   전에 반드시 행성 의회", "의회보다 연구소를 먼저"; B19-04 "선의회 빼고");
# - Geodens: no mine on a planet type not yet colonized before the Institute (GE01/B18 "의회 전엔 다른 행성
#   종류에 광산 금지" — the Institute's knowledge per new type);
# - Terrans: with 6 power or more in bowl III no power-to-resource free action while a power action it
#   pays for is open (B4-01 "6파워 이상은 프리 액션이 아닌 파워 액션으로");
# - Taklons: burning allowed above 4 tokens (B10-01, TK01 "토큰을 최대한 태워 브레인스톤 포함 3–4개 유지"),
#   and among power actions 1 terraforming, then 2 knowledge first (B19-05 "1테라 > 2지식", B10-01
#   "2광석·7돈은 욕심낼 필요 없고 1테라·2지식이 중요"), in guide_more_scores.
TAKLONS_TOKENS = 4
TERRANS_POWER = 6
POWER_TO_RESOURCE = frozenset({'PowerToCredit', 'PowerToOre', 'PowerToQic', 'PowerToKnowledge'})
TAKLONS_POWER_ORDER = (6, 5)   # engine PowerAction ids: 1 terraforming step, 2 knowledge


def _tokens(player):
    power = player['resources']['power']
    return sum(power[k] for k in ('bowl1', 'bowl2', 'bowl3')) + int(power.get('brainstone') not in (None, 'Gaia'))


def _faction_hold(state, player, action):
    kind, faction = action.get('type'), player.get('faction')
    built = {_kind(s) for s in player.get('structures', [])}
    if faction == 'Xenos':
        if kind == 'FormFederation' and 'PlanetaryInstitute' not in built:
            return 'Xenos federation after the Planetary Institute (B15-01)'
        if kind == 'Upgrade' and action.get('to') == 'PlanetaryInstitute' and 'ResearchLab' not in built:
            return 'Xenos lab before the Planetary Institute (B15-01)'
    if faction == 'Geodens' and kind == 'Build' and 'PlanetaryInstitute' not in built:
        planet = (state['board']['hexes'].get(str(action.get('coord'))) or {}).get('planet')
        held = {((state['board']['hexes'].get(str(s['hex'])) or {}).get('planet') or {}).get('planet_type')
                for s in player['structures']}
        if planet and planet['planet_type'] not in held:
            return 'Geodens new planet types after the Planetary Institute (GE01)'
    if faction == 'Terrans' and kind == 'FreeAction' and action.get('kind') in POWER_TO_RESOURCE:
        bowl3 = player['resources']['power']['bowl3']
        used = state.get('used_power_actions', [])
        if bowl3 >= TERRANS_POWER and any(c <= bowl3 for i, c in POWER_COST.items() if i not in used):
            return 'Terrans 6+ power goes to a power action (B4-01)'
    return None


def _mines_in_hand(player):
    return max(0, MINE_LIMIT - sum(_kind(s) == 'Mine' for s in player.get('structures', [])))


def _mine_effect(state, action):
    """The move's reward includes building a mine (user 2026-10-15: "광산 설치하는 타일, 기술은 광산이 없으면
    효과를 사용할 수 없어"): the Lost Fleet 2-terraform mine tile, the free-build federation tokens,
    the Proto planet and Asteroid mine artifacts."""
    kind = action.get('type')
    if kind == 'RebellionGainTechTile':
        return action.get('tile') == MINE_TILE
    if kind == 'FormFederation':
        return (_token_kind(state, action.get('token')) in MINE_TOKENS
                or action.get('bonus_tech_tile') == MINE_TILE)
    if kind == 'TwilightReplayFederationToken':
        return action.get('token_kind') in MINE_TOKENS or action.get('bonus_tech_tile') == MINE_TILE
    if kind == 'ExamineArtifact':
        return action.get('artifact') in MINE_ARTIFACTS
    return False


def _tech_held_back(state, tile, player=None):
    if _guide['mine_tile'] and tile == MINE_TILE and player is not None:
        return _mines_in_hand(player) == 0
    if tile == RANGE_TILE and player is not None:
        return state['round'] >= 3 or player['research_tracks']['navigation'] >= WHEN_LEVEL
    return state['round'] < TECH_FROM_ROUND.get(tile, 0)


def _tile_groups(candidates, scores):
    from current_actions.conservation import blocked
    groups = {}
    for i, candidate in enumerate(candidates):
        action = candidate['action']
        choice = action.get('tech_tile_choice')
        if isinstance(choice, dict) and not blocked(scores[i]):
            key = json.dumps({**action, 'tech_tile_choice': None}, sort_keys=True)
            groups.setdefault(key, []).append((i, choice.get('kind'), choice.get('tile')))
    return groups


def tech_when_scores(env, snapshot, scores):
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or 'ActionPhase' not in state['phase']:
        return scores
    groups = [g for g in _tile_groups(snapshot['candidates'], scores).values() if len(g) > 1]
    if not groups:
        return scores
    player = state['players'][actor]
    lifted = list(scores)
    for group in groups:
        best = max(group, key=lambda g: scores[g[0]][0])
        if best[1] != 'Standard':
            continue
        to = snapshot['candidates'][best[0]]['action'].get('to')
        wanted = _tech_wanted(state, player, academy=isinstance(to, dict) and 'Academy' in to)
        standard = [g for g in group if g[1] == 'Standard']
        target, why = None, None
        for tiles, reason in wanted:
            options = [g for g in standard if g[2] in tiles and not _tech_held_back(state, g[2], player)]
            if options:
                target, why = max(options, key=lambda g: scores[g[0]][0]), reason
                break
        if target is None and _tech_held_back(state, best[2], player):
            others = [g for g in standard if not _tech_held_back(state, g[2], player)]
            if others:
                target = max(others, key=lambda g: scores[g[0]][0])
                why = f'tile {best[2]} not yet'
        if target is None or scores[best[0]][0] <= scores[target[0]][0]:
            continue
        mine, top = target[0], best[0]
        lifted[mine] = (scores[top][0], f'{scores[mine][1]}; tech when: {why}', *scores[mine][2:])
        lifted[top] = (scores[mine][0], *scores[top][1:])
    return lifted


def guide_r1_charge3_lf_more_vm_lf_ts_ships_when_all_tech(seed, **kwargs):
    """Teacher factory: guide_r1_charge3_lf_more_vm_lf_ts_ships_when_all (the base stack after lab 056)
    plus the fixes from the 056 pair-005/game-1 replay (user 2026-10-14 "일단 구현해봐, 아직 안 한 작업도"):
    opponent-adjacent starts ordered first instead of blocking the others, with distinct setup
    comparisons (reach parts A and B, lab 051); idle formers used before the Gaia track, a Transdim
    planet counted only once formed, Asteroids as colony options (former_use); a burn only for a power
    action it pays for and the Terrans former kept for a Transdim planet (not yet); standard tech tiles
    by the guides' timing (tech_when)."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts_ships_when_all(seed, **kwargs)
    install_reach(plus=False, focus=False)
    install_former_use()
    _guide['burn_when'] = _guide['terrans_former'] = True
    _guide['tech_when'] = True
    _wrap_rank('_tech_when', tech_when_scores)
    install_guide_more()
    return teacher


# ── guide_more (user 2026-10-14: "기존 11개 말고 더 없어? 이번이 진짜 마지막 … 종족별 공략을 제외하고 모든
#    자료를 참고") — the common claims of gaia-strategy-claims.csv that name a move and a time and were
#    not in the stack yet, order only (no new numbers; thresholds are the sources'):
#    holds (just below passing, _not_yet_more):
#    - fed_upgrade: no upgrade of a federated building except a trading station to a lab (SH3-06
#      "교역소→연구소를 제외하면 이미 연방에 묶인 건물을 업그레이드하면 파워 손해", B2-05);
#    - ts_excess: in rounds 1-3 no third trading station, nor one while credits are 2.5 or more per ore
#      (SH3-04 "1:2.5 이상은 방지", "1–3R엔 교역소를 3개 이상 남기지 않음");
#    - rebellion_ts: the Rebellion trading station (3 power 1 ore) only where a trading station costs 6
#      credits, no opponent within 2 (SH2-06 "6돈 교역소에 쓸 것", LF1-08 "비싼 교역소일 때 매우 큼");
#    - knowledge_action: the 7-power 3-knowledge action only with 1 knowledge left over (B18-08 "3지식은
#      1지식이 남을 때만", LF1-07 "7파워 3지식은 손해");
#    - qic_late: the 2-QIC ship actions (TF Mars, Eclipse) from round 4 (SH1-07 "4R 이후 누르길 추천");
#    - rebellion_qic: Rebellion 2 knowledge → 2 credits 1 QIC only when it makes 3 QIC (SH2-06 "3QIC를
#      누를 수 있게 해줄 때만 최고");
#    - fed_cap: no fifth federation (SH1-03 "5–6연방 집착 금지", LF3-02 "티어 보너스 없는 종족의 5연방은
#      노리지 말 것"; the four fixed factions have no tier bonus).
#    leech_lf: rounds 1-2 charges by SH1-11 (see _leech_when).
#    first moves (guide_more_scores):
#    - ship_first: the Twilight lab (3 power 2 ore) and a 6-credit Rebellion trading station go first
#      (LF1-08 "기회가 있으면 1순위 자원 액션", SH2-07 "모든 파워 액션 중 최고 효율");
#    - qic_round6: in round 6 a QIC action before passing (B18-08 "6R엔 QIC 액션 하나는 꼭");
#    - fed_design: in rounds 1-3 a federation without two labs or five mines before one with them
#      (SH3-05 "첫 연방에 연구소 2개를 묶지 말 것", "광산도 초반 한 연방에 5개 이상 묶지 않음");
#    - fed_token: among the tokens of one federation the technology token in rounds 1-2 (LF1-10 "기술
#      습득 토큰은 초반 압도적"), else 8 VP 8 credits (LF3-10 "보통 8점8돈 최고"); never the 2-token or
#      the unlimited-range token while another is there (B18-07, B19-09 "2토큰 연방은 없는 셈", LF1-10
#      "무한사거리 광산 토큰은 대부분 가장 나쁨");
#    - pass_booster: a pass booster worth 4 VP or more at the current counts before the best-ranked
#      pass (SH1-06 "초반에도 4점 이상이면 점수 부스터"), and from round 5 a pass for 8 VP or more goes
#      first even with moves left (SH1-06 "후반 8점 이상이면 할 행동이 남아도 패스", B18-05).
#    Not in (no move or time the ranking can act on, or faction guides): B2-05 "광산 2개는 항상 유지"
#    (which two is unclear), B2-06 lab for even knowledge (rule 7), SH3-02 ore terraforming (value),
#    SH1-04/SH1-08 artifacts and Gaia tile late, LF3-03 Academy ahead for 4 federations, B18-06 the
#    order among contested moves, final-scoring and round-goal claims (no goal value exists).
GUIDE_MORE = ('fed_upgrade', 'ts_excess', 'rebellion_ts', 'knowledge_action', 'qic_late', 'rebellion_qic',
              'fed_cap', 'leech_lf', 'ship_first', 'qic_round6', 'fed_design', 'fed_token', 'pass_booster')
TS_EXCESS_ROUNDS = (1, 2, 3)
TS_EXCESS_HELD = 2
CREDIT_EXCESS = 2.5
KNOWLEDGE_ACTION = 1                       # engine PowerAction id: 7 power → 3 knowledge
QIC_LATE = frozenset({'TFMarsTechBonus', 'EclipsePlanetTypeBonus'})
QIC_LATE_FROM = 4
QIC_ACTIONS = QIC_LATE | {'RebellionGainTechTile', 'TwilightReplayFederationToken'}
REBELLION_QIC = 3
FEDERATION_CAP = 4
LEECH_LF_ROUNDS = (1, 2)
SHIP_VP = 5                                # engine SPACESHIP_DEPLOY_VP_COST
FED_DESIGN_ROUNDS = (1, 2, 3)
FED_LABS, FED_MINES = 2, 5
TECH_TOKEN, BEST_TOKEN = 12, 8
TOKEN_AVOID = frozenset({3, 15})           # 8 VP + 2 tokens, unlimited-range mine
TOKEN_TECH_ROUNDS = (1, 2)
PASS_EARLY_VP, PASS_LATE_VP, PASS_LATE_FROM = 4, 8, 5
AHEAD = 0.001
# GUIDE_REST (user 2026-10-15 "일단 나머지 적용해": what guide_more had left out, read as follows):
# - mines_kept: from round 2 no mine upgraded while 2 or fewer mines stand (B2-05 "광산 2개는 항상
#   유지"; read as mines on the board — round 1 openings upgrade a starting mine, so not then);
# - (lab_even, B2-06 "다음 라운드 지식이 짝수가 되게", was here; removed by the user 2026-10-15, see tech_when);
# - ore_terraform: no Build paying 3 ore a terraforming step (SH3-02 "광석을 쓰는 깡 테라포밍은 절대
#   하지 말 것"; the frozen power_purpose's "expensive" line);
# - artifact_vp: a VP artifact worth 9 VP or more goes first (SH1-08 "9점 이상이면 좋고", LF1-11 "9점이면
#   가져갈 만함"; the gain read from an engine fork, root decision only);
# - academy_ahead: with two federations and no Academy the best Academy upgrade goes before other
#   upgrades (LF3-03 "4연방을 할 때 아카데미 1개는 결국 필요하므로 미리");
# - contested_order: among the moves above passing, level-5 advances and advanced tiles, then QIC
#   actions, then power actions (B18-06 "5단계·고급 기술 > QIC 액션 > 파워 액션"), while an opponent
#   still plays; their scores are handed out in that order (root decision only).
# Still not in: final and round goals (the frozen value already counts the VP a move scores now;
# SH1-09/B20-01 "미션을 과하게 신경쓰지 말 것"), the Gaia-mine tile (LF2-08 over SH1-04).
GUIDE_REST = ('ore_terraform', 'artifact_vp', 'academy_ahead', 'contested_order')
MINES_KEPT, MINES_KEPT_FROM = 2, 2
ORE_PER_PAID_STEP = 3
ARTIFACT_VP = 9
ACADEMY_AHEAD_FEDS = 2
TOP_LEVEL = 5


def _ship_open(state, player):
    """A ship the player has not explored still has a free slot."""
    return any(None in board['explorers'] and player['player_id'] not in board['explorers']
               for board in state.get('spaceship_boards', []))


def _booster_vp(state, player, booster):
    """booster_pass_vp for `booster` held instead of the player's own."""
    return booster_pass_vp(state, {**player, 'booster': booster})


def _token_kind(state, token):
    if not isinstance(token, dict):
        return None
    if token.get('source') == 'Supply':
        return token.get('kind')
    board = next((b for b in state.get('spaceship_boards', []) if b['id'] == token.get('ship')), None)
    return board and board.get('federation_token')


def _fed_heavy(player, hexes):
    kinds = {str(s['hex']): _kind(s) for s in player['structures']}
    held = [kinds.get(str(h)) for h in hexes]
    return held.count('ResearchLab') >= FED_LABS or held.count('Mine') >= FED_MINES


def _swap(lifted, scores, mine, top, why):
    lifted[mine] = (scores[top][0], f'{scores[mine][1]}; {why}', *scores[mine][2:])
    lifted[top] = (scores[mine][0], *scores[top][1:])


def guide_more_scores(env, snapshot, scores):
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or 'ActionPhase' not in state['phase']:
        return scores
    player, round_ = state['players'][actor], state['round']
    candidates = snapshot['candidates']
    # A move a "not yet" rule held down is never promoted again here (056 p005-g1 step 39: the round
    # goal swap lifted a held third trading station back to the top).
    live = [i for i in range(len(candidates)) if not blocked(scores[i]) and 'not yet:' not in str(scores[i][1])]
    if not live:
        return scores
    lifted = list(scores)
    act = {i: candidates[i]['action'] for i in live}
    passes = [i for i in live if act[i].get('type') == 'Pass']
    top = max(scores[i][0] for i in live)

    def lift(i, value, why):
        lifted[i] = (value, f'{scores[i][1]}; {why}', *scores[i][2:])

    if _guide['ship_first']:
        for i in live:
            kind = act[i].get('type')
            if ((kind == 'TwilightFreeResearchLab' or (kind == 'RebellionFreeTradingStation'
                 and not _next_to_opponent(state, actor, str(act[i].get('coord')))))
                    and not _not_yet(state, player, act[i]) and scores[i][0] < top):
                lift(i, top+AHEAD, 'ship action first (LF1-08)')
    if _guide['qic_round6'] and round_ == 6 and passes:
        qic = [i for i in live if act[i].get('type') in QIC_ACTIONS]
        floor = max(scores[i][0] for i in passes)
        if qic and max(scores[i][0] for i in qic) <= floor:
            lift(max(qic, key=lambda i: scores[i][0]), floor+AHEAD, 'a QIC action in round 6 (B18-08)')
    feds = [i for i in live if act[i].get('type') == 'FormFederation']
    if _guide['fed_design'] and round_ in FED_DESIGN_ROUNDS and len(feds) > 1:
        best = max(feds, key=lambda i: scores[i][0])
        light = [i for i in feds if not _fed_heavy(player, act[i]['hexes'])]
        if light and _fed_heavy(player, act[best]['hexes']):
            _swap(lifted, scores, max(light, key=lambda i: scores[i][0]), best,
                  'federation without two labs or five mines (SH3-05)')
    if _guide['fed_token'] and len(feds) > 1:
        groups = {}
        for i in feds:
            key = json.dumps({k: v for k, v in act[i].items() if not k.startswith('bonus_') and k != 'token'},
                             sort_keys=True)
            groups.setdefault(key, []).append(i)
        avoid = TOKEN_AVOID | (MINE_TOKENS if _guide['mine_tile'] and not _mines_in_hand(player) else frozenset())
        for group in groups.values():
            if len(group) < 2:
                continue
            ranked = sorted(group, key=lambda i: -lifted[i][0])
            kinds = {i: _token_kind(state, act[i].get('token')) for i in group}
            wanted = [k for k in ((TECH_TOKEN,) if round_ in TOKEN_TECH_ROUNDS else ()) + (BEST_TOKEN,)
                      if k in kinds.values()]
            if wanted:
                mine = next(i for i in ranked if kinds[i] == wanted[0])
            elif kinds[ranked[0]] in avoid:
                mine = next((i for i in ranked if kinds[i] not in avoid), None)
            else:
                mine = None
            if mine is not None and mine != ranked[0]:
                _swap(lifted, list(lifted), mine, ranked[0], f'federation token {kinds[mine]}')
    if (_guide['pass_booster'] or _guide['former_booster']) and passes:
        vp = {i: _booster_vp(state, player, act[i].get('booster_id')) for i in passes}
        best = max(passes, key=lambda i: lifted[i][0])
        rich = max(passes, key=lambda i: (vp[i], lifted[i][0]))
        if _guide['pass_booster'] and vp[rich] >= PASS_EARLY_VP and rich != best and vp[rich] > vp[best]:
            _swap(lifted, list(lifted), rich, best, f'pass booster for {vp[rich]} VP (SH1-06)')
            best = rich
        if (_guide['former_booster'] and act[best].get('booster_id') == FORMER_BOOSTER
                and _idle_formers(player) and _in_reach(state, player, ('Asteroid',))):
            # The formers will go to an Asteroid next round, so they will not be there to score.
            others = [i for i in passes if act[i].get('booster_id') != FORMER_BOOSTER]
            if others:
                other = max(others, key=lambda i: lifted[i][0])
                _swap(lifted, list(lifted), other, best, 'formers go to an Asteroid next round (C035)')
                best = other
        high = max(lifted[i][0] for i in live)
        if _guide['pass_booster'] and round_ >= PASS_LATE_FROM and vp[best] >= PASS_LATE_VP and lifted[best][0] < high:
            lifted[best] = (high+AHEAD, f'{lifted[best][1]}; pass for {vp[best]} VP late (SH1-06, B18-05)',
                            *lifted[best][2:])
    if _guide['faction_more'] and player['faction'] == 'Taklons':
        powers = [i for i in live if act[i].get('type') == 'PowerAction']
        if len({act[i].get('id') for i in powers}) > 1:
            rank = {pid: n for n, pid in enumerate(TAKLONS_POWER_ORDER)}
            by_score = sorted(powers, key=lambda i: -lifted[i][0])
            order = sorted(powers, key=lambda i: (rank.get(act[i].get('id'), len(rank)), by_score.index(i)))
            given = list(lifted)
            for i, source in zip(order, by_score):
                if i != source:
                    lifted[i] = (given[source][0], f'{given[i][1]}; Taklons power action order (B19-05)', *given[i][2:])
    if _guide['r1_basics'] and round_ == 1 and passes:
        # SH3-01 "아카데미 스타트·파이락이 아니면 1R에 최소 광산 1개", SH3-03 "의회 빌드가 아닌 종족의 1R 연구소는
        # 무조건" (Geodens are the source's Institute faction): before passing in round 1.
        floor = max(lifted[i][0] for i in passes)
        built = [_kind(s) for s in player['structures']]
        starting = R1_START_MINES.get(player['faction'], 2)
        needs = []
        if len(built) <= starting and 'Academy' not in built:
            needs.append(('mine', {'Build', 'RoundBoosterTerraformBuild', 'RoundBoosterRangeBuild',
                                   'TwilightRangeBuild', 'SpaceshipCreditTerraform', 'EclipseAsteroidMine'}))
        if player['faction'] != 'Geodens' and not {'ResearchLab', 'Academy'} & set(built):
            needs.append(('lab', None))
        for name, kinds in needs:
            options = [i for i in live if (act[i].get('type') in kinds if kinds else
                                           act[i].get('type') == 'Upgrade' and act[i].get('to') == 'ResearchLab')]
            if options and max(lifted[i][0] for i in options) <= floor:
                best = max(options, key=lambda i: lifted[i][0])
                lifted[best] = (floor+AHEAD, f'{lifted[best][1]}; round 1 {name} before passing (SH3-01/03)',
                                *lifted[best][2:])
    if _guide['track_set'] and round_ < TRACK_FREE_ROUND and player['faction'] in FACTION_TRACKS:
        tracks, groups = _faction_tracks(state, player), {}
        research = [i for i in live if act[i].get('type') == 'ResearchAdvance']
        for i in live:
            choice = act[i].get('tech_tile_choice')
            if isinstance(choice, dict) and choice.get('advance_track'):
                key = json.dumps({**act[i], 'tech_tile_choice': {**choice, 'advance_track': None}}, sort_keys=True)
                groups.setdefault(key, []).append(i)
        for group in [research, *groups.values()]:
            if len(group) < 2:
                continue
            best = max(group, key=lambda i: lifted[i][0])
            if 'research when' in lifted[best][1]:
                continue   # a situational rule chose this track (user: "트랙은 언제나 상황 맞춰가는 거")
            track = act[best].get('track') or act[best]['tech_tile_choice']['advance_track']
            own = [i for i in group if TRACK_KEYS.get(act[i].get('track')
                                                     or act[i]['tech_tile_choice']['advance_track']) in tracks]
            if own and TRACK_KEYS.get(track) not in tracks:
                _swap(lifted, list(lifted), max(own, key=lambda i: lifted[i][0]), best,
                      f'{player["faction"]} research on its tracks')
    return _guide_rest(env, snapshot, scores, lifted, live, act)


def _guide_rest(env, snapshot, scores, lifted, live, act):
    """The GUIDE_REST firsts (see guide_more)."""
    state, actor = snapshot['state'], snapshot['player']
    player = state['players'][actor]
    root = not _when_root or _when_root[-1] == snapshot['decision_id']
    if _guide['artifact_vp'] and root and env is not None:
        high = max(lifted[i][0] for i in live)
        for i in live:
            if act[i].get('type') != 'ExamineArtifact' or act[i].get('artifact') in RESOURCE_ARTIFACTS:
                continue
            after = json.loads(env.fork(snapshot['decision_id'], i).snapshot_json())
            gain = after['state']['players'][actor]['vp'] - player['vp']
            if gain >= ARTIFACT_VP and lifted[i][0] < high:
                lifted[i] = (high+AHEAD, f'{lifted[i][1]}; artifact for {gain} VP (SH1-08, LF1-11)', *lifted[i][2:])
    upgrades = [i for i in live if act[i].get('type') == 'Upgrade']
    if (_guide['academy_ahead'] and _federations(player) >= ACADEMY_AHEAD_FEDS
            and not any(_kind(s) == 'Academy' for s in player['structures'])):
        academy = [i for i in upgrades if isinstance(act[i].get('to'), dict) and 'Academy' in act[i]['to']]
        if academy:
            mine, best = max(academy, key=lambda i: lifted[i][0]), max(upgrades, key=lambda i: lifted[i][0])
            if best not in academy:
                _swap(lifted, list(lifted), mine, best, 'an Academy ahead of the fourth federation (LF3-03)')
    if _guide['contested_order'] and root and not all(
            other['passed'] for i, other in enumerate(state['players']) if i != actor):
        floor = max((lifted[i][0] for i in live if act[i].get('type') == 'Pass'), default=0.0)
        tracks = player['research_tracks']

        def rank(i):
            a, kind = act[i], act[i].get('type')
            choice = a.get('tech_tile_choice') or {}
            if ((kind == 'ResearchAdvance' and tracks.get(TRACK_KEYS.get(a.get('track')), 0) == TOP_LEVEL-1)
                    or choice.get('kind') in ('Advanced', 'LostFleetAdvanced')):
                return 0
            if kind in QIC_ACTIONS:
                return 1
            return 2 if kind == 'PowerAction' else None
        ranked = [i for i in live if rank(i) is not None and lifted[i][0] > floor]
        if len({rank(i) for i in ranked}) > 1:
            by_score = sorted(ranked, key=lambda i: -lifted[i][0])
            order = sorted(ranked, key=lambda i: (rank(i), by_score.index(i)))
            given = list(lifted)
            for i, source in zip(order, by_score):
                if i != source:
                    lifted[i] = (given[source][0], f'{given[i][1]}; contested order (B18-06)', *given[i][2:])
    return _guide_last(env, snapshot, lifted, live, act, root)


# GUIDE_LAST (user 2026-10-15 "그냥 다 넣어": the round and final missions too):
# - round_goal: among the moves that build, upgrade, form a Gaia planet or advance research, the best
#   one that scores VP now (the round tile, read from an engine fork) goes ahead of the best of them
#   (LF3-05 "1R 라운드 보너스를 따라가는 것이 매우 중요", SH1-02 "라운드 미션은 자원을 그대로 점수로 바꿔주는
#   엔진"); root decision only;
# - final_mission: from round 4, a player last on both final missions puts first the best move that
#   raises one of their metrics (SH1-09 "두 미션 모두 꼴찌면 1등이 어려우니 최소 6점 확보"; B20-01, LF3-12
#   otherwise "과하게 신경쓰지 말 것"); root decision only.
GUIDE_LAST = ('gaia_tile', 'round_goal', 'final_mission')
GOAL_MOVES = frozenset({'Build', 'Upgrade', 'GaiaFormation', 'ResearchAdvance', 'RoundBoosterTerraformBuild',
                        'RoundBoosterRangeBuild', 'TwilightRangeBuild', 'SpaceshipCreditTerraform',
                        'EclipseAsteroidMine', 'TwilightFreeResearchLab', 'RebellionFreeTradingStation'})
FINAL_FROM = 4


def _final_ranks(state, actor):
    """[(condition, own metric, last on it)] for the two final missions."""
    from research_plans.value import final_metric
    result = []
    for tile in state.get('final_scoring_tiles', []):
        try:
            values = [final_metric(state, p, tile['condition']) for p in state['players']]
        except (KeyError, TypeError, ValueError):
            continue
        result.append((tile['condition'], values[actor], values[actor] < min(v for i, v in enumerate(values) if i != actor)))
    return result


def _guide_last(env, snapshot, lifted, live, act, root):
    state, actor = snapshot['state'], snapshot['player']
    if not root or env is None:
        return lifted
    player = state['players'][actor]
    moves = [i for i in live if act[i].get('type') in GOAL_MOVES]
    if not moves:
        return lifted
    forks = {}

    def after(i):
        if i not in forks:
            forks[i] = json.loads(env.fork(snapshot['decision_id'], i).snapshot_json())['state']
        return forks[i]
    floor = max((lifted[i][0] for i in live if act[i].get('type') == 'Pass'), default=None)
    if _guide['round_goal']:
        # A tech tile's own VP (tile 7, advanced tiles) is not the round goal: the moves that differ
        # only in the tile are read through one member taking a standard tile other than 7.
        groups = {}
        for i in moves:
            choice = act[i].get('tech_tile_choice')
            key = json.dumps({**act[i], 'tech_tile_choice': None}, sort_keys=True) if isinstance(choice, dict) else i
            groups.setdefault(key, []).append(i)
        scores_goal = set()
        for group in groups.values():
            plain = [i for i in group if not isinstance(act[i].get('tech_tile_choice'), dict)
                     or (act[i]['tech_tile_choice'].get('kind') == 'Standard'
                         and act[i]['tech_tile_choice'].get('tile') != 7)]
            if plain and after(plain[0])['players'][actor]['vp'] > player['vp']:
                scores_goal.update(group)
        best = max(moves, key=lambda i: lifted[i][0])
        scoring = [i for i in scores_goal if floor is None or lifted[i][0] > floor]
        if scoring and best not in scoring:
            _swap(lifted, list(lifted), max(scoring, key=lambda i: lifted[i][0]), best,
                  'scores the round goal (LF3-05, SH1-02)')
    if _guide['final_mission'] and state['round'] >= FINAL_FROM:
        from research_plans.value import final_metric
        ranks = _final_ranks(state, actor)
        if len(ranks) == 2 and all(last for _, _, last in ranks):
            raising = [i for i in moves if any(
                final_metric(after(i), after(i)['players'][actor], c) > own for c, own, _ in ranks)]
            best = max(moves, key=lambda i: lifted[i][0])
            if raising and best not in raising:
                _swap(lifted, list(lifted), max(raising, key=lambda i: lifted[i][0]), best,
                      'last on both final missions (SH1-09)')
    return lifted


# GUIDE_FINAL (user 2026-10-15 "더 넣어야 하지 않나?" — a second pass over the common claims):
# - former_booster: when passing, not the former pass booster (engine 6, 3 VP a former at the next
#   pass) while an idle former has an Asteroid in reach — it goes there next round (C035/PG24 "포머를
#   남겨 부스터 점수를 받는 것과 소행성에 쓰는 것이 충돌"; user 2026-10-15: "다음 라운드에 포머를 소행성에 쓸
#   생각이 있으면 포머당 3점을 안 가져오는 방향", replacing a first version that kept the formers);
#   it overrides pass_booster;
# - late_ship: no ship entry from round 5 (SH1-12 "들어가서 액션을 3번 이상 못 하면 가치가 떨어짐"; from round
#   5 at most two rounds of actions are left);
# - mine_tile: the 2-terraform mine tile (Lost Fleet 11) held back with no mine left in hand (LF2-05
#   "남은 광산 재고가 0이면 가치가 0에 수렴"), and so is every other reward that builds a mine (the
#   free-build federation tokens 14/15, the mine artifacts 8/12, tile 11 through Rebellion or a token;
#   user 2026-10-15 "광산이 없으면 효과를 사용할 수 없어. 경계해야지");
# - setup_step1: among starting places of the same kind (next to an opponent or not), one with a free
#   planet one terraforming step from home within 2 hexes goes first (C017 "2칸 이내 1단계 테라포밍 행성").
# Left out after this pass: plan-level goals (C001-C003 federation counts, SH5-03/04 fast advanced-tile
# runs, B2-04 saving for the next round), value claims already priced (LF01/LF02 resources, boosters,
# tokens, QIC for Gaia), research spread (C006-C008, SH1-10, B19-06/07: the focus rule lost in lab 049),
# claims about expansion factions or the faction guides, the engine-rule note LF2-14, and coaching-only rows.
# - track_set (user, same day: "흩뿌리진 말아야지. 종족마다 좋은 트랙 정해져 있잖아"): before round 6 each
#   faction advances only its three tracks (SH1-10 "중구난방으로 올리지 말 것 … 트랙 두세 개는 아예 포기",
#   B19-07 "과학을 제외하면 일반적으로 3트랙 … 올릴 트랙을 초반에 정해 거기만", C008 user "많아야 2–3개");
#   round 6 is free (B19-07 "테라포밍·인공지능 중 하나는 6R 남는 진보용"). Order only, and only as the
#   default (user, same day: "트랙은 언제나 상황 맞춰가는 거"): when the best research move or tile advance
#   is on another track and no situational rule (1b and the other "research when" rules) picked it, it
#   swaps with the best one on the faction's tracks; nothing is held.
#   The tracks, from the faction guides:
#   Geodens terraforming, navigation, AI (GE01/B19 "테라 3·항해 2 맞추고 테라 꼭대기 수비하며 인공지능");
#   Xenos Gaia, navigation, economy (B15-02 "가이아 트랙을 가장 추천 … 항해 1+가이아 2", B15-03 "경제 2");
#   Taklons navigation, economy, science (B19-05 "가이아 빼고 아무 테크", B10-03 "지식 아카데미 … 선과학",
#   SH4-06 "항해를 올리거나"); Terrans navigation, Gaia, economy (B4-01 "가이아 3단계는 항해 2가 먼저", B4-02
#   "4연방은 경제+큰 건물 4티어"), terraforming instead of economy with the planet-type final mission
#   (B19-02, B4-02 "행성 종류 미션이면 테라포밍 선점"). Lab 049's focus rule (one track, chosen by level) lost
#   charges; this one fixes the tracks by faction instead.
# Also (user 2026-10-15, "제안대로 해"): terrans_gaia_cond — the early Terrans Gaia ban keeps B04's condition;
# tokens_lf — tokens above B02's need keep their price (LF1-02); mines_kept is dropped (B2-05 unclear).
FACTION_TRACKS = {'Geodens': ('terraforming', 'navigation', 'ai'),
                  'Xenos': ('gaia', 'navigation', 'economy'),
                  'Taklons': ('navigation', 'economy', 'science'),
                  'Terrans': ('navigation', 'gaia', 'economy')}


def _faction_tracks(state, player):
    tracks = FACTION_TRACKS[player['faction']]
    if player['faction'] == 'Terrans' and any(t.get('condition') == 'MostPlanetTypes'
                                              for t in state.get('final_scoring_tiles', [])):
        return ('navigation', 'gaia', 'terraforming')
    return tracks
TRACK_FREE_ROUND = 6
HOLD_DEPTH = 100
GUIDE_FINAL = ('former_booster', 'late_ship', 'mine_tile', 'setup_step1', 'track_set', 'hold_no_pass',
               'terrans_gaia_cond', 'tokens_lf', 'faction_more', 'adv_immediate', 'r1_basics')
R1_START_MINES = {'Xenos': 3}   # starting mines (others 2; engine factions.toml)
FORMER_BOOSTER = 6
LATE_SHIP_FROM = 5
MINE_TILE = 11
MINE_TOKENS = frozenset({14, 15})   # engine federation tokens: free build 3 steps, unlimited range
MINE_ARTIFACTS = frozenset({8, 12})  # engine artifacts: 7 VP + Proto planet mine, 7 VP + Asteroid mine
STEP1_HEXES = 2


def _step1_near(state, player, coord):
    """A free planet one terraforming step from home within STEP1_HEXES of coord."""
    from economy.teacher import RING
    from strategy_teacher import distance
    home = _value.HOME.get(player['faction'])
    if home not in RING:
        return False
    for c, cell in state['board']['hexes'].items():
        planet = cell.get('planet')
        if (planet and planet['owner'] is None and not cell['structures'] and planet['planet_type'] in RING
                and distance(c, coord) <= STEP1_HEXES):
            gap = abs(RING.index(home)-RING.index(planet['planet_type']))
            if min(gap, 7-gap) == 1:
                return True
    return False


def setup_step_scores(env, snapshot, scores):
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot.get('player')
    places = [i for i, c in enumerate(snapshot['candidates'])
              if c['action'].get('type') == 'PlaceStartingStructure' and not blocked(scores[i])]
    if actor is None or len(places) < 2:
        return scores
    player = state['players'][actor]
    near = _near_places(snapshot, scores)
    lifted = list(scores)
    for group in ([i for i in places if i in near], [i for i in places if i not in near]):
        if len(group) < 2:
            continue
        best = max(group, key=lambda i: lifted[i][0])
        step1 = [i for i in group
                 if _step1_near(state, player, str(snapshot['candidates'][i]['action']['coord']))]
        if step1 and best not in step1:
            _swap(lifted, list(lifted), max(step1, key=lambda i: lifted[i][0]), best,
                  'one-step planet within 2 (C017)')
    return lifted


def install_guide_more(names=GUIDE_MORE+GUIDE_REST+GUIDE_LAST+GUIDE_FINAL):
    for name in names:
        _guide[name] = True
    _wrap_rank('_not_yet', not_yet_scores)
    _wrap_rank('_leech_when', leech_when_scores)
    _wrap_rank('_guide_more', guide_more_scores)
    if _guide['setup_step1']:
        _wrap_rank('_setup_step1', setup_step_scores)
