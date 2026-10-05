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
        if bound in (_original, symmetric_potential) or getattr(bound, '__name__', '') == 'calibrated_potential':
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


# ── calibrated_value ───────────────────────────────────────────────────────────────────
# Opt-in, on top of geodens_guide. Replaces the hand-weighted sum in `potential` by the
# per-round weights that tools/value_baseline.py fitted to final results (cycle 019): the
# same terms (tools/extract_dataset.py potential_terms + the cycle-017 pass terms), each
# multiplied by its data-fitted weight instead of 1.0. Setup (round 0) and finished games
# keep the original function. The weights file is the only input; no term is hand-tuned.

_calibrated = {'weights': None}


def calibrated_potential(state, actor, home=None, guide_tracks=False):
    phase = state['phase']
    if (isinstance(phase, dict) and 'Ended' in phase) or state['round'] < 1:
        return symmetric_potential(state, actor, home=home, guide_tracks=guide_tracks)
    from extract_dataset import potential_terms, pass_terms
    if home is None:
        from faction_teachers.profiles import profiles
        home = profiles()[state['players'][actor]['faction']].home
    weights = _calibrated['weights'][str(min(state['round'], 6))]
    terms = {**potential_terms(state, actor, home), **pass_terms(state, actor)}
    return sum(weights.get(k, 0.0)*x for k, x in terms.items())


calibrated_potential.__wrapped__ = _original


def install_calibrated_value(path):
    import json
    import sys
    with open(path) as source:
        _calibrated['weights'] = json.load(source)['rounds']
    for module in list(sys.modules.values()):
        if getattr(module, 'potential', None) in (_original, symmetric_potential, calibrated_potential):
            if getattr(module, '__name__', '').split('.')[0] in ('four_factions', 'faction_teachers'):
                module.potential = calibrated_potential
    _value.potential = calibrated_potential


def calibrated_value(seed, **kwargs):
    """Teacher factory: geodens_guide with data-fitted term weights (GAIA_VALUE_WEIGHTS)."""
    import os
    from pathlib import Path
    path = os.environ.get('GAIA_VALUE_WEIGHTS') or str(Path(__file__).with_name('value-weights.json'))
    teacher = geodens_guide(seed, **kwargs)
    install_calibrated_value(path)
    return teacher


# ── family_rotation ────────────────────────────────────────────────────────────────────
# Opt-in, on top of geodens_guide. At the normal level a decision compares the current choice
# with the FIRST proposal only (cycle 016 budget). `goals_for` lists Academy/PI upgrades
# first, then research, then colonies, so in rounds 2+ the one examined plan was almost
# always an upgrade or a research step and expansion plans were never examined (cycle 021,
# one replayed game: the most frequent first proposals were Qic/Science Academy and PI
# upgrades and Terraforming steps for Terrans, Taklons and Xenos). This rotates which proposal family comes first, by the
# decision's step number, so every family is examined in turn. It ranks nothing: the
# families, their contents and the comparison itself are unchanged. Geodens keeps the
# cycle-018 guide order.

ROTATION_EXEMPT = frozenset({'Geodens'})


_rotation = {'only': None}   # None: every faction but ROTATION_EXEMPT; else this set only


def rotate_families(snapshot, goals):
    player = snapshot['state']['players'][snapshot['player']]
    only = _rotation['only']
    if not goals or player['faction'] in ROTATION_EXEMPT or (only is not None and player['faction'] not in only):
        return goals
    order, groups = [], {}
    for goal in goals:
        if goal.family not in groups:
            order.append(goal.family)
            groups[goal.family] = []
        groups[goal.family].append(goal)
    k = snapshot['steps'] % len(order)
    return [goal for family in order[k:]+order[:k] for goal in groups[family]]


def install_family_rotation():
    import four_factions.preparation as preparation
    original = getattr(preparation.goals_for, '__wrapped__', preparation.goals_for)

    def goals_for(snapshot, **kwargs):
        return rotate_families(snapshot, original(snapshot, **kwargs))
    goals_for.__wrapped__ = original
    preparation.goals_for = goals_for


def family_rotation(seed, **kwargs):
    """Teacher factory: geodens_guide plus rotating the first proposal family per decision."""
    teacher = geodens_guide(seed, **kwargs)
    _rotation['only'] = None
    install_family_rotation()
    return teacher


def xenos_rotation(seed, **kwargs):
    """Teacher factory: geodens_guide plus family rotation for Xenos only.

    Cycle 021 A/B (rotation for every faction but Geodens): Xenos +10.2 [+1.3, +19.1],
    Terrans -12.1 [-24.5, +0.3], Taklons -2.5. Xenos ranks with its own evaluator, not
    `potential`. Selected after seeing that result, so it must be confirmed on new seeds.
    """
    teacher = geodens_guide(seed, **kwargs)
    _rotation['only'] = frozenset({'Xenos'})
    install_family_rotation()
    return teacher


# ── quartet_guide ──────────────────────────────────────────────────────────────────────
# Opt-in, on top of geodens_guide. B19 (uiqoo, 2023) only ORDERS proposals for Terrans and
# Taklons, as cycle 018 did for Geodens; no value term, bonus or prohibition.
# Terrans (B19 "테란"): Academy first for the 4-charge and Gaia-3-VP tiles ("아광"), then the
#   Gaia track, Gaia/Transdim colonies and ordinary expansion; a PI start "is a trap", so PI
#   proposals move to the back (still examined when nothing else is proposed).
# Taklons (B19 "타클론"): research lab + mines ("연5광"); "cover the map with tier-1/2
#   buildings" — an expansion plan first, then the existing two-labs path.

def _expansion(snapshot):
    from four_factions.preparation import Goal
    from four_factions.source_paths import colony_count
    player = snapshot['state']['players'][snapshot['player']]
    return Goal('one-new-colony', 'expansion', level=colony_count(snapshot['state'], player)+1,
                sources=('B19',))


def _terrans_key(goal):
    if goal.name.startswith('Terrans-academy'):
        return 0
    if goal.family == 'research' and goal.target == 'GaiaProject':
        return 1
    if goal.family == 'colony':
        return 2
    if goal.family == 'expansion':
        return 3
    if goal.name.startswith('Terrans-PI') or (goal.family == 'upgrade' and goal.target == 'PlanetaryInstitute'):
        return 9
    return 5


def _taklons_key(goal):
    if goal.family == 'expansion':
        return 0
    if goal.name.startswith('Taklons-two-labs'):
        return 1
    return 5


QUARTET_KEYS = {'Terrans': _terrans_key, 'Taklons': _taklons_key}


def quartet_goals(snapshot, goals):
    from four_factions.preparation import viable, achieved
    faction = snapshot['state']['players'][snapshot['player']]['faction']
    key = QUARTET_KEYS.get(faction)
    if key is None:
        return goals
    extra = _expansion(snapshot)
    if (not any(g.family == 'expansion' and not g.steps for g in goals)
            and viable(snapshot, snapshot['player'], extra) and not achieved(snapshot, snapshot['player'], extra)):
        goals = [*goals, extra]
    return sorted(goals, key=key)   # stable: the tree's order within each rank is kept


def install_quartet_guide():
    import four_factions.preparation as preparation
    original = getattr(preparation.goals_for, '__wrapped__', preparation.goals_for)

    def goals_for(snapshot, **kwargs):
        return quartet_goals(snapshot, original(snapshot, **kwargs))
    goals_for.__wrapped__ = original
    preparation.goals_for = goals_for


def quartet_guide(seed, **kwargs):
    """Teacher factory: geodens_guide plus the B19 proposal order for Terrans and Taklons."""
    teacher = geodens_guide(seed, **kwargs)
    install_quartet_guide()
    return teacher


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
    result += gv.materials(state, player['resources']) + gv.power_value(state, player)
    power = player['resources']['power']
    if horizon:
        # The frozen teacher's own Brainstone and Gaia-area terms (faction-dependent, unchanged).
        result += {'Area1': .5, 'Area2': 1.5, 'Area3': 4.2, 'Gaia': 0, None: 0}[power['brainstone']]
        result += (.6 if player['faction'] == 'Terrans' else .2)*power['gaia_forming']
    result += gv.incomes_value(state, v.production(state, player, include_booster=False))
    if horizon and (player['passed'] or state['round'] == 0):
        result += gv.booster_value(state, player['booster'])
    elif horizon and _action_phase(state):
        # Symmetric pass (cycle 017): an unpassed player also passes this round.
        result += max((gv.booster_value(state, b) for b in state['boosters']), default=0)
    if state['round'] >= 1 and not player['passed'] and _action_phase(state):
        result += booster_pass_vp(state, player)
    result += gv.planet_value(state)*len(player['structures'])
    result += gv.ship_value(state)*len(player['explored_ships'])
    if player['faction'] == 'Taklons' and any(s['kind'] == 'PlanetaryInstitute' for s in player['structures']):
        owners = {b['owner'] for c, cell in state['board']['hexes'].items()
                  if any(v.distance(c, s['hex']) <= 2 for s in player['structures'])
                  for b in cell['structures'] if b['owner'] != actor}
        result += horizon*min(2, len(owners))
    if guide_tracks:
        from four_factions.track_guidance import expansion_potential
        result += v.gaia_value(state, player) + expansion_potential(state, player)
    else:
        result += v.gaia_value(state, player) + (v.expansion_value(state, player, home=home) if horizon else 0)
    result += v.research_options(state, player)
    result += sum(v.advanced_option(state, player, tile) for tile in player['advanced_tech_tiles'])
    active = set(player['tech_tiles'])-set(player['covered_tech_tiles'])
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


def uiqoo_opening_order(snapshot, goals, remembered=None):
    faction = snapshot['state']['players'][snapshot['player']]['faction']
    order = UIQOO_OPENINGS.get(faction)
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


def guide_values_openings_free(seed, **kwargs):
    """Teacher factory: guide_values_openings without the hand-written conversion bans."""
    teacher = guide_values_openings(seed, **kwargs)
    install_free_conversions()
    return teacher
