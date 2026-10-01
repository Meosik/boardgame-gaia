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
        if getattr(module, 'potential', None) in (_original, symmetric_potential) and module is not None:
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
