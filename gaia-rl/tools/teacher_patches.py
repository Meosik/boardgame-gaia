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
