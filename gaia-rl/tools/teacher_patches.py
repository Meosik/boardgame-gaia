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

GUIDE = ('B14', 'B19')

# ── faction parts (user 2026-10-19 "종족별로 적용한다", research/strategy/stack-parts.md D) ──────────
# Every faction-specific switch of the stack is read from these two tables, so "which faction has
# what" is one place. BASE_FACTION_PARTS: the parts of the base stack vm_lf_ts_ships that act on one
# faction only (the common parts act on everyone). CANDIDATE_FACTION_PARTS: the opt-in parts measured
# on the base stack (stack-parts.md B) that the ships_byfaction factory turns on for the factions where
# the measurement was positive; a faction absent from a table has none of that table's parts — the
# default for every faction not measured yet. Per-faction data tables (UIQOO_OPENINGS, ECONOMY_COUNTED,
# FACTION_TRACKS) and rule facts (Terrans' Gaia-area tokens come back charged, a Brainstone exists only
# for Taklons) stay where they are: they are not switches.
BASE_FACTION_PARTS = {
    'Geodens': frozenset({'geodens_guide',          # geodens_goals: B14 proposal order (018)
                          'geodens_two_incomes',    # install_geodens_guide: second-income look-ahead (018)
                          'geodens_r1_research'}),  # geodens_r1_goals: Economy/Science first after AC or 2RL (guide_r1 ⑥)
    'Terrans': frozenset({'terrans_gaia_late'}),    # _early_terrans_gaia: Gaia research last in rounds 1-3 (guide_r1 ②)
    'Taklons': frozenset({'brainstone_ships',       # taklons_ship_timing_scores + brainstone_committed (053)
                          'taklons_pi_token'}),     # lf_leech_value: the PI's token per leech (046)
}
CANDIDATE_FACTION_PARTS = {
    'Terrans': frozenset({'track_income'}),         # 074+076, 12 pairs: charges +15.0, final VP +17.0 [+0.3, +33.7]
    'Geodens': frozenset({'former_use'}),           # 079, 6 pairs: charges +20.7 (4 pairs positive), thin
    'Taklons': frozenset({'opening_budget', 'budget_guard', 'opening_release'}),   # 077, 6 pairs: +23.6 (4 pairs), thin
    # Not on: Taklons track_income (076 charges -26.5 significant, VP +13.7 is not the verdict measure);
    # Xenos track_income (+14.0, CI includes 0); Geodens track_income (-35.5 significant).
    # The ten base factions without a lab measurement (user 2026-10-19 "종족별 규칙 넣고 실험 시작"): the
    # guide's research-track priority as an order rule (track_set_scores, FACTION_TRACKS from
    # research/strategy/faction-tracks-openings.md), nothing else — level caps, "never builds an
    # academy" and the like are left for the replays (HANDOFF 1: order and scope only, no new number).
    **{faction: frozenset({'track_set'}) for faction in
       ('Gleens', 'Ambas', 'Itars', 'Nevlas', 'Firaks', 'BalTaks', 'Ivits', 'Bescods', 'Lantids', 'HadschHallas')},
}


def _faction_parts(faction):
    parts = set(BASE_FACTION_PARTS.get(faction, ()))
    if _guide['byfaction']:
        parts.update(CANDIDATE_FACTION_PARTS.get(faction, ()))
    return parts


def _part(player, name):
    """Whether part `name` is on for this player's faction."""
    return name in _faction_parts(player['faction'])


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
    if not _part(player, 'geodens_guide'):
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
        if not _part(snapshot['state']['players'][snapshot['player']], 'geodens_two_incomes'):
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
# Removed on 2026-10-19 (user: "기각은 없애야"; research/strategy/stack-parts.md C, git history
# before commit 12b1456's successor): booster_lookahead (026), distinct_search (030–033), academy_r1
# (041), sheden_r1 (042), vp1 + leech rule (045), reach parts (048–051), the when / tech_when /
# guide_more families (054–060, about 60 flags), geodens_prior and guide_r1 part 5 (064),
# opening_label / label_value (065, 066, 078), instant_forming and geodens_b14_tech (071–077).


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
          'lf_frozen': False,           # True: guide_r1_charge3_lf_more_vm_lf (see install_lf_frozen)
          'ts_chain_direct': False,     # True: guide_r1_charge3_lf_more_vm_lf_ts (see ts_chain_scores)
          'knowledge_spend': False,     # True: guide_r1_charge3_lf_more_vm_lf_ts (see knowledge_spend_scores)
          'ship_setup': False,          # True: guide_r1_charge3_lf_more_vm_lf_ts (see ship_setup_scores)
          'value_max': False,           # True: guide_r1_charge3_lf_more_vm (see install_value_max)
          'byfaction': False,           # True: ..._ships_byfaction (CANDIDATE_FACTION_PARTS on)
          # Opt-in parts measured and not in the base stack (stack-parts.md B; per-faction candidates):
          'former_use': False,          # True: ..._ships_former (see install_former_use)
          'opening_budget': False,      # True: ..._ships_budget (see opening_budget_scores)
          'budget_guard': False,        # True: with opening_budget (see opening_budget_scores)
          'opening_release': False,     # True: install_opening_release
          'academy_economy': False,     # True: install_academy_economy (see academy_economy_scores)
          'research_when_land': False}  # True: ..._ships_land (see research_when_land_scores)


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


# track_income 'sweet' (user 2026-10-18 "track_income 다시 해봐. 단 모든 종족이 다 경제 좋다고 올려버리면
# 안되고"): the Economy and Science levels' income counts again, but only where the faction guides send the
# faction — Economy up to the level the faction's guide names (ECONOMY_COUNTED; the default 2 from B18-03
# "메리트 없으면 경제 2", B17-03 "경제 2 필수", B15-03; Geodens 3 from B14-03 "3경제/3과학"; Terrans 4 from
# PG18-T20 "경제 4에 머물고" and B4-02; HadschHallas and Darkanians 4 from "경제 2·4"), every level when
# Economy is the faction's first guide track (FACTION_TRACKS: Nevlas, Firaks, Ivits, HadschHallas, Darkanians),
# Science only when it is a guide track at all. The rest stays priced once, at 16 charges per level
# (install_guide_r1). Scope only, the levels are the sources' (user 04:25 "경제 왜 2렙까지만이야").
ECONOMY_SWEET = 2
ECONOMY_COUNTED = {'Geodens': 3, 'Terrans': 4, 'HadschHallas': 4, 'Darkanians': 4}


def _track_income_excess(state, player):
    """Track income left uncounted under track_income 'sweet' (see above)."""
    from four_factions.value import INCOME
    faction = player['faction']
    tracks = FACTION_TRACKS.get(faction, ())
    economy = INCOME['economy'][state['research_board']['economy_research_tile_side']]
    level = player['research_tracks']['economy']
    counted = level if tracks[:1] == ('economy',) else min(level, ECONOMY_COUNTED.get(faction, ECONOMY_SWEET))
    excess = [a-b for a, b in zip(economy[level], economy[counted])]
    if 'science' not in tracks:
        excess = [a+b for a, b in zip(excess, INCOME['science'][player['research_tracks']['science']])]
    return excess


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
    track_income = _guide['track_income']
    if track_income is False and _part(player, 'track_income'):
        track_income = 'sweet'
    if track_income == 'sweet':
        income = [a-b for a, b in zip(income, _track_income_excess(state, player))]
    elif not track_income:
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
#   The other ten base factions (user 2026-10-16 "자료대로 해", claims B5-03 … B16-03; the authors' order,
#   labels as the BGG catalog spells them — a label the catalog lacks for the faction is never proposed):
#   B05 Gleens: 교역소+광산×5 "최고" (1TS+5M), 아카데미+광산 (1AC+1M), 연구소+교역소+광산+광산 (1RL+1TS+2M).
#   B06 Ambas: 연구소+교역소+광산+광산, 연구소+광산×4, 아카데미+광산 "기본" (and +광산), 교역소+광산×6.
#   B07 Itars: 행성 의회+교역소+광산+광산 (선의회), 아카데미+광산 "기본" (and +광산).
#   B08 Nevlas: 행성 의회+연구소+광산, 행성 의회+광산+광산 (+4정보), 아카데미+광산 "가장 어려움".
#   B09 Firaks: 행성 의회+연구소 "최고" (the Institute downgrades the lab: BGG's 1PI+1TS), 연구소+교역소+광산+광산,
#       연구소+광산+광산 "기본" and its variants.
#   B11 BalTaks: 아카데미+광산 "가장 좋음", 연구소+광산+광산 (+4정보), 연구소+교역소+광산+광산.
#   B12 Ivits: 행성 의회+연구소+광산 "거의 항상" (the Institute is the starting structure).
#   B13 Bescods: 연구소+교역소+광산+광산 "기본", 연구소+광산+광산, 연구소+연구소 (2기술), 아카데미+광산+광산 "가장 안 좋음".
#   B16 Lantids: 행성 의회+광산+광산 "기본" (+광산 when affordable), 연구소+교역소+광산+광산 (and 연구소+광산+광산).
#   B17 HadschHallas: 연구소+광산×4 "무난", 아카데미+광산 (경제 2 필수).
#   B14 Geodens (user 2026-10-16 "자료랑 다른 부분들 바꿔"): 아카데미+광산+광산 "행성 의회보다 아카데미 스타트가 좋음"
#       (1AC+2M, needs a home planet within range 3), 연구소+교역소+광산+광산 (1RL+1TS+2M, four home planets),
#       행성 의회+교역소+광산+광산 "모행성이 없을 때의 기본" (1PI+1TS+2M). guide_r1 part 5 (BGG-O2 1PI+4M first)
#       is switched off since the same day ("기오덴 빼줘"), so this order stands alone.
#   Lost Fleet factions have no BGG table, so planning.goals proposes nothing for them; LOST_FLEET_OPENINGS
#   (sheden #4 "종족 별 추천 빌드", rank 1 then rank 2 in the article's order, end-of-round-1 buildings) is
#   turned into the same bgg-opening goals by install_uiqoo_openings.
UIQOO_OPENINGS = {
    'Geodens': ('1AC+2M', '1RL+1TS+2M', '1PI+1TS+2M'),
    'Terrans': ('1AC+1M', '1PI+2M', '1PI+1TS+2M', '1RL+2M'),
    'Taklons': ('1AC+2M', '1RL+1TS+2M', '1RL+5M'),
    'Xenos': ('1RL+5M', '1RL+2M', '1AC+2M'),
    'Gleens': ('1TS+5M', '1AC+1M', '1RL+1TS+2M'),
    'Ambas': ('1RL+1TS+2M', '1RL+4M', '1AC+1M', '1AC+2M', '1TS+6M'),
    'Itars': ('1PI+1TS+2M', '1AC+1M', '1AC+2M'),
    'Nevlas': ('1PI+1RL+1M', '1PI+2M', '1AC+1M'),
    'Firaks': ('1PI+1TS', '1RL+1TS+2M', '1RL+2M', '1RL+1TS+1M', '1RL+3M'),
    'BalTaks': ('1AC+1M', '1RL+2M', '1RL+1TS+2M'),
    'Ivits': ('1PI+1RL+1M', '1PI+1RL+2M', '1PI+1RL'),
    'Bescods': ('1RL+1TS+2M', '1RL+2M', '2RL', '1AC+2M'),
    'Lantids': ('1PI+2M', '1PI+3M', '1PI+4M', '1RL+1TS+2M', '1RL+2M'),
    'HadschHallas': ('1RL+4M', '1AC+1M', '1AC+2M'),
}



def guide_opening_labels(faction):
    """The guide's round-1 opening order for a faction, () when no guide order applies."""
    return UIQOO_OPENINGS.get(faction) or ()


def uiqoo_opening_order(snapshot, goals, remembered=None):
    faction = snapshot['state']['players'][snapshot['player']]['faction']
    order = guide_opening_labels(faction)
    if not order:
        return goals
    rank = {label: i for i, label in enumerate(order)}

    def key(item):
        i, goal = item
        return (goal.target != remembered, rank.get(goal.target, len(order)), i)
    return [goal for _, goal in sorted(enumerate(goals), key=key)]


LOST_FLEET_OPENINGS = {   # sheden #4 pp. 16-18: 연=RL 의=PI 아=AC 교=TS N광=N mines
    'Moweyds': ('1RL+4M', '1RL+1TS+2M', '1PI+1TS', '1PI+1TS+1M', '1PI+1RL', '1PI+2M'),
    'SpaceGiants': ('1PI+1TS+2M', '1PI+1RL+1M', '1PI+4M', '1PI+1RL+2M'),
    'Tinkeroids': ('1PI+1TS+2M', '1PI+1RL+2M', '1PI+4M'),
    'Darkanians': ('1RL+4M', '1RL+1TS+2M', '1PI+1TS+2M', '1AC+1M'),
}


def lost_fleet_opening_goals(snapshot, remembered=None):
    """bgg-opening goals for a Lost Fleet faction from LOST_FLEET_OPENINGS, as planning.goals builds
    them from the catalog (round 1 only, reachable inventories only, the remembered label first)."""
    from bgg_openings.catalog import parse_buildings
    from bgg_openings.inventory import building_counts
    from bgg_openings.planning import distance_to
    from four_factions.preparation import Goal
    if snapshot['state']['round'] > 1:
        return []
    player = snapshot['state']['players'][snapshot['player']]
    labels = LOST_FLEET_OPENINGS.get(player['faction'], ())
    current = building_counts(player)
    ordered = sorted(labels, key=lambda label: label != remembered)
    return [Goal(f'BGG-R1-{label}', 'bgg-opening', target=label, sources=('SH4',))
            for label in ordered if distance_to(current, parse_buildings(label), player['faction']) is not None]


def install_uiqoo_openings():
    import bgg_openings.planning as planning
    original = getattr(planning.goals, '__wrapped__', planning.goals)

    def goals(snapshot, remembered=None):
        proposed = original(snapshot, remembered)
        if not proposed:
            proposed = lost_fleet_opening_goals(snapshot, remembered)
        return uiqoo_opening_order(snapshot, proposed, remembered)
    goals.__wrapped__ = original
    planning.goals = goals



# ── opening_budget (user 2026-10-17 "1번 ㄱㄱ"; labs 064–066) ─────────────────────────────
# Why: with a round-1 target such as Geodens 1AC+2M, planning.select_action takes any move that
# shortens the distance to the target, best base rank first. A new mine (1 ore, 3 more per
# terraform step for Geodens) is cheaper than the academy (6 ore) and ranks earlier, so the ore
# meant for the academy is spent on mines or on a second trading station, and the chain stops at
# the research lab in 4 of 6 games (066, list_decisions). The guides say the opposite:
# B14 §4 "아카데미부터 먼저 올리고, 광산은 맨 마지막에 1돈 1광석이 더 있으면; 광석이 부족하면 아카데미+
# 광산으로 끝내고 광산은 2라운드에"; IR01 "최소 11광석 14돈, 광산까지 12광석 16돈, 3~4광석은 파워 프리액션·
# 테라 1단계·1광석1QIC 타일로"; B11 the same arithmetic for BalTaks.
# Rule (order and scope only, engine costs and rulebook conversion rates, no new number, every
# faction with a round-1 target): while the target still owes upgrades, a move that is not one of
# those upgrades is blocked when, on its native fork, what is left can no longer pay them — ore
# plus QIC (1 QIC → 1 ore) plus bowl-III power (3 → 1 ore, 1 → 1 credit) against the owed ore and
# credits. The chain upgrades themselves, moves that spend none of these (research, charging,
# pass) and moves that keep the budget stay as they are; the frozen funding search (QIC→ore, the
# 2-ore power action, power→ore) then pays what is missing, as in the one finished game (066 p003).
# The first version counted ore and credits only; in the 066 p000 replay the 1AC+2M rollout then
# spent its QIC on a mine (no ore moved) and the academy slipped to round 2.
UPGRADE_COSTS = {'trading_station': (2, 6), 'research_lab': (3, 5),
                 'planetary_institute': (4, 6), 'academy': (6, 6)}   # engine.rs::upgrade_cost
BUDGET_KEYS = ('ore', 'credits', 'qic')


def _budget_pays(resources, owed_ore, owed_credits):
    """Can the owed upgrades still be paid from stock plus the rulebook free conversions?"""
    power = resources['power']['bowl3']
    gap = max(0, owed_ore - resources['ore'] - resources['qic'])
    power -= 3*gap
    return power >= 0 and resources['credits'] + power >= owed_credits


def _trading_station_credits(snapshot, player):
    """6 credits, or 3 when one of the player's mines has an opponent structure within range 2
    (rulebook p.13; the same test funding_need makes per mine)."""
    from four_factions.preparation import distance
    hexes = snapshot['state']['board']['hexes']
    mines = [s['hex'] for s in player['structures'] if s['kind'] == 'Mine']
    for coord, cell in hexes.items():
        if any(s['owner'] != snapshot['player'] for s in cell['structures']):
            if any(distance(coord, mine) <= 2 for mine in mines):
                return 3
    return 6


def chain_costs(current, target, faction, ts_credits=6):
    """(ore, credits) still owed by the upgrades on a shortest path from `current` to `target`
    in the opening topology; new mines on that path are not counted (they are deferred). None
    when the target is unreachable."""
    from dataclasses import asdict
    import bgg_openings.planning as planning
    from bgg_openings.catalog import Buildings, LIMITS
    distances = planning._distances(target, faction)
    if current not in distances:
        return None
    ore = credits = 0
    state = current
    while distances[state] > 0:
        counts = asdict(state)
        step = None
        for old, new in planning._edges(faction):
            if counts[old] and counts[new] < LIMITS[new]:
                after = Buildings(**{**counts, old: counts[old]-1, new: counts[new]+1})
                if distances.get(after) == distances[state]-1:
                    step = (after, new)
                    break
        if step is None:
            after = Buildings(**{**counts, 'mine': counts['mine']+1})
            if distances.get(after) != distances[state]-1:
                return None
            state = after
            continue
        state, new = step
        o, c = UPGRADE_COSTS[new]
        ore += o
        credits += (ts_credits if new == 'trading_station' else c)
    return ore, credits


def opening_budget_scores(env, snapshot, scores, target, deadline):
    """Block the moves that would leave less than the owed upgrades cost (see above)."""
    from dataclasses import asdict
    import bgg_openings.planning as planning
    from bgg_openings.inventory import building_counts
    from current_actions.conservation import BLOCKED, PREFIX, blocked
    from four_factions.preparation import check_time
    state = snapshot['state']
    if state['round'] != 1 or 'ActionPhase' not in state['phase']:
        return scores
    actor = snapshot['player']
    player = state['players'][actor]
    faction = player['faction']
    current = building_counts(player)
    owed = chain_costs(current, target, faction, _trading_station_credits(snapshot, player))
    if not owed or owed == (0, 0):
        return scores
    owed_ore, owed_credits = owed
    held = player['resources']
    if (_guide['budget_guard'] or _part(player, 'budget_guard')) and not _budget_pays(held, owed_ore, owed_credits):
        # 068 p001 Taklons (7 ore, 1 QIC, no bowl-III power; TS 2 + RL 3 + AC 6 owed): the chain
        # cannot be paid from what is held, so reserving for it only loses the mine and the round
        # ends at 1RL+1M. Nothing is blocked until a leech or an action makes the chain payable.
        return scores
    distance = planning.distance_to(current, target, faction)
    masked = list(scores)
    for i, candidate in enumerate(snapshot['candidates']):
        action = candidate['action']
        # Exploring a spaceship pays VP and range QIC for actions the chain can use afterwards
        # (Twilight's 2-ore lab, Rebellion's 1-ore trading station and its 2-knowledge → 2 credits
        # + 1 QIC); the search, not the budget, judges those (user 2026-10-17).
        if (blocked(scores[i]) or action['type'] in ('Pass', 'ChargePower', 'ChooseIncomeOrder')
                or action['type'].endswith('ExploreSpaceship')):
            continue
        check_time(deadline)
        after = json.loads(env.fork(snapshot['decision_id'], i).snapshot_json())
        resources = after['state']['players'][actor]['resources']
        if (all(resources[key] >= held[key] for key in BUDGET_KEYS)
                and resources['power']['bowl3'] >= held['power']['bowl3']):
            continue                                    # spends nothing of the budget
        counts = building_counts(after['state']['players'][actor])
        remaining = planning.distance_to(counts, target, faction)
        # A chain upgrade, whatever action pays it (Upgrade, Twilight lab, Rebellion TS): closer to
        # the target with the same number of buildings. A new mine also comes closer but adds a
        # building. (Until 2026-10-17 this compared mine counts, so the first step of every chain —
        # a mine becoming a trading station — failed the test and was budgeted like a mine: in 067/068
        # p001 the Geodens and Terrans TS were blocked at the first decision and the exempt ship
        # entries were played instead; Terrans built nothing in round 1.)
        if (remaining is not None and remaining < distance
                and sum(asdict(counts).values()) == sum(asdict(current).values())):
            continue
        still_owed = (chain_costs(counts, target, faction, _trading_station_credits(snapshot, player))
                      if remaining is not None else None) or (owed_ore, owed_credits)
        if still_owed == (0, 0):
            continue
        if not _budget_pays(resources, *still_owed):
            masked[i] = (BLOCKED, PREFIX+f'opening budget: {still_owed[0]} ore {still_owed[1]} credits '
                         f'still owed by the {target} upgrades')
    return masked


def install_opening_budget(all_factions=True):
    """all_factions=False (ships_byfaction): the budget acts only where CANDIDATE_FACTION_PARTS has
    'opening_budget'; the guard likewise reads 'budget_guard' there."""
    import bgg_openings.planning as planning
    _guide['opening_budget'] = _guide['opening_budget'] or all_factions
    if not getattr(planning.select_action, '_opening_budget', False):
        inner = planning.select_action

        def select_action(env, snapshot, scores, target, policies, deadline):
            player = snapshot['state']['players'][snapshot['player']]
            masked = scores
            if _guide['opening_budget'] or _part(player, 'opening_budget'):
                masked = opening_budget_scores(env, snapshot, scores, target, deadline)
            return inner(env, snapshot, masked, target, policies, deadline)
        select_action._opening_budget = True
        select_action.__wrapped__ = getattr(inner, '__wrapped__', inner)
        planning.select_action = select_action


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
                      if _new_mine(c['action']) else score
                      for c, score in zip(snapshot['candidates'], scores)]
            i = original(env, snapshot, masked, target, policies, deadline)
            if i is not None and (i != best_index(masked, range(len(masked)))
                                  or snapshot['candidates'][i]['action']['type'] == 'Upgrade'):
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
    return _part(player, 'terrans_gaia_late') and state['round'] < TERRANS_GAIA_FROM_ROUND


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
        if action['type'] == 'PlaceStartingStructure' and near and i not in near:
            # Setup comparisons end at the round-1/2 income and differ by noise (034: 154.3
            # vs 153.5), so ordering alone let an isolated start win; compare only the near ones.
            result[i] = (BLOCKED, PREFIX+'guide: start next to an opponent (LF4-02, B10-02)')
        elif (action['type'] == 'ResearchAdvance' and action.get('track') == 'GaiaProject'
              and _early_terrans_gaia(state, actor)):
            result[i] = (scores[i][0]-abs(bottom)-1000, *scores[i][1:])
    return result


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
    if not _part(player, 'geodens_r1_research'):
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
    # Part 5 (Geodens 1PI+4M first) was switched off on 2026-10-16 ("기오덴 빼줘. 자료 대로 바꿔줘") and
    # removed on 2026-10-19 with the geodens_prior factory (lab 064 A arm): the Geodens opening order is
    # B14's alone (UIQOO_OPENINGS).
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
    tokens = min(tokens, gv.tokens_needed(player))
    return gv.to_vp(state, charges + gv.TOKEN*tokens)


GAIA_TOKENS = (255, 6, 6, 4, 3, 3)   # rulebook: tokens per Gaia former by Gaia track level
MINE_COST = {'ore': 1, 'credits': 2}
MINE_LIMIT = 8


def _reach_targets(state, player, planet_types):
    """[(coord, planet, qic, nav)]: v.targets with nav = 0 (the reach_plus variant that added the
    planets one Navigation step away, lab 050, was removed on 2026-10-19)."""
    return [(coord, planet, qic, 0) for coord, planet, qic in _value.targets(state, player, planet_types)]


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
    former_use = _guide['former_use'] or _part(player, 'former_use')
    if room and not former_use:
        transdim = sorted((qic, nav) for _, _, qic, nav in _reach_targets(state, player, ('Transdim',)))[:room]
        options += [({**MINE_COST, 'qic': qic}, GAIA_TOKENS[level]*terrans, nav) for qic, nav in transdim]
    # Formers on a planet or in the Gaia area come back, so every former not yet used up counts.
    formers = (max(0, player['gaiaformers_total'] - player['resources']['spent_gaia_formers'])
               if former_use else 0)
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
    pi_token = (_part(player, 'taklons_pi_token')
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


def _booster_value(state, player, booster):
    import guide_value as gv
    return gv.booster_value(state, booster)


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
    if not (_guide['former_use'] or _part(state['players'][actor], 'former_use')):
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
    uses = [i for i, c in enumerate(candidates) if uses_former(c['action']) and not blocked(scores[i])]
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
    if not _part(player, 'brainstone_ships'):
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


def install_former_use(all_factions=True):
    """all_factions=False (ships_byfaction): former_use acts only where CANDIDATE_FACTION_PARTS has it."""
    _guide['former_use'] = _guide['former_use'] or all_factions
    _wrap_rank('_former_use', former_first_scores)


def guide_r1_charge3_lf_more_vm_lf_ts_ships_budget(seed, **kwargs):
    """Teacher factory: ..._ships where, while the round-1 opening target still owes upgrades, a
    move that would leave less ore or credits than those upgrades cost is blocked unless it is one
    of them (opening_budget; B14 §4 / IR01 academy ore recipe)."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts_ships(seed, **kwargs)
    install_opening_budget()
    return teacher


def guide_r1_charge3_lf_more_vm_lf_ts_ships_former(seed, **kwargs):
    """Teacher factory: ..._ships (the base stack) plus former_use — a Transdim planet is a colony
    option only once it is being formed, an Asteroid per idle former, and an idle former is used
    before the Gaia track is advanced again. Lab 069 (user 2026-10-17 "그렇게 진행해": 068 p001
    Terrans had five Gaia-forming moves at -2.0 in round 1 because the idle former already priced the
    planet as a mine)."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts_ships(seed, **kwargs)
    install_former_use()
    return teacher


# ── ships_fix leftovers (user 2026-10-18 "지금 테스트 멈추고 고칠거 다 고친 후에 돌려야겠는데") ────────
# Of the 068 p001 replay bundle (labs 071, 073, 077) these parts stay as opt-ins, order and scope only:
# - opening_budget with its first-step fix and budget_guard: the academy's ore is kept only while
#   the chain can actually be paid;
# - opening_release: once the round-1 target's upgrades are built, the rest of round 1 goes back to
#   the search (068 p001 Geodens: the label's last mine took the ore of the Rebellion free TS while the
#   search's first choice was the Eclipse entry, 17.1 vs 15.9);
# - academy_economy (below).
# instant_forming and geodens_b14_tech (the Geodens first-tile and no-Gaia-before-round-5 rule, a loss
# in 077) and the ships_fix bundle factories were removed on 2026-10-19.
TRACK_ORDER = ('Terraforming', 'Navigation', 'ArtificialIntelligence', 'GaiaProject', 'Economy', 'Science')


def _tile_track(state, choice):
    """The track a standard tile choice advances: the chosen one, else the track of the slot the
    tile sits in (engine standard_tech_tile_aligned_track; `advance_track: null` means that one)."""
    if not isinstance(choice, dict) or choice.get('kind') != 'Standard':
        return None
    if choice.get('advance_track'):
        return choice['advance_track']
    slots = (state.get('research_board') or {}).get('tech_tile_slots') or []
    for index, slot in enumerate(slots[:len(TRACK_ORDER)]):
        if slot == choice.get('tile'):
            return TRACK_ORDER[index]
    return None


# academy_economy (user 2026-10-18 "선 아카데미를 한 종족은 발타크 빼고 대부분 경제를 2레벨까진 가야하는데
# 안간거"; B17-03 "아카데미+광산(경제 2 필수)", B14-03 1AC+2M "3경제/3과학", B15-03 "아카데미+광산+광산 …
# 경제·과학 2", IT01 "아카데미+경제", B12-02 "1R 경제 2단계"; BalTaks go Gaia 4 first, B11-02): while a
# player with an academy is below Economy 2 in rounds 1-3, the Economy advance leads the research moves
# and, among the tech-tile choices of one upgrade (the academy's own tile included), the Economy variant
# leads its tile. Order only; research against other moves and the tile itself are unchanged.
ACADEMY_ECONOMY_LEVEL = 2
ACADEMY_ECONOMY_ROUNDS = (1, 2, 3)
ACADEMY_ECONOMY_EXCEPT = ('BalTaks',)


def _has_academy(player):
    return any(isinstance(s.get('kind'), dict) and 'Academy' in s['kind'] for s in player['structures'])


def academy_economy_scores(env, snapshot, scores):
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or 'ActionPhase' not in state['phase'] or state['round'] not in ACADEMY_ECONOMY_ROUNDS:
        return scores
    player = state['players'][actor]
    if (player['faction'] in ACADEMY_ECONOMY_EXCEPT
            or player['research_tracks']['economy'] >= ACADEMY_ECONOMY_LEVEL):
        return scores
    academy = _has_academy(player)
    candidates = snapshot['candidates']
    lifted = list(scores)
    why = 'research when: Economy 2 after the academy (user, B17-03, B14-03)'
    if academy:
        research = [i for i, c in enumerate(candidates)
                    if c['action'].get('type') == 'ResearchAdvance' and not blocked(scores[i])]
        economy = [i for i in research if candidates[i]['action'].get('track') == 'Economy']
        if economy and research:
            best = max(research, key=lambda i: lifted[i][0])
            if candidates[best]['action'].get('track') != 'Economy':
                _swap(lifted, list(lifted), economy[0], best, why)
    groups = {}
    for i, c in enumerate(candidates):
        choice = c['action'].get('tech_tile_choice')
        if blocked(lifted[i]) or not isinstance(choice, dict) or choice.get('kind') != 'Standard':
            continue
        # The academy's own tile counts: the upgrade that builds it is the first chance.
        building = isinstance(c['action'].get('to'), dict) and 'Academy' in c['action']['to']
        if not academy and not building:
            continue
        key = json.dumps({**c['action'], 'tech_tile_choice': {**choice, 'advance_track': None}}, sort_keys=True)
        groups.setdefault(key, []).append(i)
    for members in groups.values():
        if len(members) < 2:
            continue
        top = max(members, key=lambda i: lifted[i][0])
        economy = [i for i in members if _tile_track(state, candidates[i]['action']['tech_tile_choice']) == 'Economy']
        if economy and top not in economy:
            _swap(lifted, list(lifted), max(economy, key=lambda i: lifted[i][0]), top, why)
    return lifted


def install_academy_economy():
    _guide['academy_economy'] = True
    _wrap_rank('_academy_economy', academy_economy_scores)


# research_when_land (user 2026-10-18 "항해술을 나중에 올려도 땅 뺏길 걱정이 없다 싶을 때 올리는 게 경제",
# "알아서 처리해"): which track a round 1-3 research advance takes is decided by the land at hand, measured
# as tools/contested_planets.py does — the empty planets of the home type, the ring types one step away,
# Gaia and Transdim within range plus the QIC held (reach), and those an opponent reaches the same way
# (contested). No reach: the Navigation advance leads the research moves (Terraforming when no Navigation
# advance is offered). Reach and nothing contested: the Economy advance leads until level ECONOMY_SWEET.
# Contested land: untouched, the search picks the mine or the range step. Order only, among research moves;
# the one number is zero. 071/060 counts: round 2-3 reach falls to 0.3-8 planets a seat, lost planets
# stay at 0-0.7 a round, so "no land" is the common case, "contested" the rarer one.
LAND_ROUNDS = (1, 2, 3)


def _cheap_types(home):
    from economy.teacher import RING
    types = {home, 'Gaia', 'Transdim'}
    if home in RING:
        i = RING.index(home)
        types |= {RING[(i-1) % len(RING)], RING[(i+1) % len(RING)]}
    return tuple(types)


def _land_counts(state, player):
    """(reach, contested) planets for the player, as in tools/contested_planets.py."""
    def cheap(p):
        return {coord for coord, _, _ in _value.targets(state, p, _cheap_types(_home_type(p)))}
    mine = cheap(player)
    theirs = set()
    for other in state['players']:
        if other is not player:
            theirs |= cheap(other)
    return len(mine), len(mine & theirs)


def research_when_land_scores(env, snapshot, scores):
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or 'ActionPhase' not in state['phase'] or state['round'] not in LAND_ROUNDS:
        return scores
    player = state['players'][actor]
    candidates = snapshot['candidates']
    research = [i for i, c in enumerate(candidates)
                if c['action'].get('type') == 'ResearchAdvance' and not blocked(scores[i])]
    if len(research) < 2:
        return scores
    reach, contested = _land_counts(state, player)
    if reach == 0:
        wanted, why = ('Navigation', 'Terraforming'), 'research when: no land in reach, range first (user 2026-10-18)'
    elif contested == 0 and player['research_tracks']['economy'] < ECONOMY_SWEET:
        wanted, why = ('Economy',), 'research when: land safe, Economy first (user 2026-10-18, B18-03)'
    else:
        return scores
    for track in wanted:
        lead = [i for i in research if candidates[i]['action'].get('track') == track]
        if lead:
            break
    else:
        return scores
    best = max(research, key=lambda i: scores[i][0])
    if best in lead:
        return scores
    lifted = list(scores)
    _swap(lifted, list(scores), lead[0], best, why)
    return lifted


def install_research_when_land():
    _guide['research_when_land'] = True
    _wrap_rank('_research_when_land', research_when_land_scores)


def guide_r1_charge3_lf_more_vm_lf_ts_ships_land(seed, **kwargs):
    """Teacher factory: ..._ships (the base stack) plus research_when_land (above)."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts_ships(seed, **kwargs)
    install_research_when_land()
    return teacher


def install_opening_release(all_factions=True):
    """Once the round-1 target owes no upgrade (only mines, or nothing), planning.select_action
    returns the search's own best move instead of the label's remaining mine. all_factions=False
    (ships_byfaction): only where CANDIDATE_FACTION_PARTS has 'opening_release'."""
    import bgg_openings.planning as planning
    from bgg_openings.inventory import building_counts
    from research_plans.teacher import best_index
    _guide['opening_release'] = _guide['opening_release'] or all_factions
    if getattr(planning.select_action, '_opening_release', False):
        return
    inner = planning.select_action

    def select_action(env, snapshot, scores, target, policies, deadline):
        state = snapshot['state']
        if state['round'] == 1 and 'ActionPhase' in state['phase']:
            player = state['players'][snapshot['player']]
            if ((_guide['opening_release'] or _part(player, 'opening_release'))
                    and chain_costs(building_counts(player), target, player['faction']) == (0, 0)):
                return best_index(scores, range(len(scores)))
        return inner(env, snapshot, scores, target, policies, deadline)
    select_action._opening_release = True
    select_action.__wrapped__ = getattr(inner, '__wrapped__', inner)
    planning.select_action = select_action


def guide_r1_charge3_lf_more_vm_lf_ts_ships_income(seed, **kwargs):
    """Teacher factory: ..._ships (the base stack) with track_income 'sweet' — the Economy and Science
    levels' income counts where the faction guides send the faction (see _track_income_excess)."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts_ships(seed, **kwargs)
    _guide['track_income'] = 'sweet'
    return teacher


def guide_r1_charge3_lf_more_vm_lf_ts_ships_byfaction(seed, **kwargs):
    """Teacher factory: ..._ships (the base stack) plus the per-faction candidates of
    CANDIDATE_FACTION_PARTS — Terrans track_income 'sweet', Geodens former_use, Taklons opening_budget
    with budget_guard and opening_release, and the guide track priority (track_set) for the ten base
    factions not measured in the lab; Xenos plays the base stack unchanged (user 2026-10-19 "종족별로
    적용한다", "종족별 규칙 넣고 실험 시작", stack-parts.md B/D). The wrappers are installed for everyone and
    read the table per actor, so the module flags of those parts stay False here."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts_ships(seed, **kwargs)
    _guide['byfaction'] = True
    install_former_use(all_factions=False)
    install_opening_budget(all_factions=False)
    install_opening_release(all_factions=False)
    _wrap_rank('_track_set', track_set_scores)
    return teacher


# ── track_set (user 2026-10-15 "흩뿌리진 말아야지. 종족마다 좋은 트랙 정해져 있잖아"; re-added 2026-10-19 as a
# per-faction part after the when family was removed): before round 6 a faction advances only the tracks
# its guide names (SH1-10 "중구난방으로 올리지 말 것 … 트랙 두세 개는 아예 포기", B19-07 "올릴 트랙을 초반에 정해
# 거기만"); round 6 is free (B19-07). Order only, and only as the default: when the best research move or
# tile advance is on another track and no situational rule ("research when": academy_economy,
# research_when_land) picked it, it swaps scores with the best one on the faction's tracks; nothing is
# held. The 057–060 bundle that carried this rule lost, so it is on only where CANDIDATE_FACTION_PARTS
# says and is judged per faction.
TRACK_KEYS = {'Terraforming': 'terraforming', 'Navigation': 'navigation', 'ArtificialIntelligence': 'ai',
              'GaiaProject': 'gaia', 'Economy': 'economy', 'Science': 'science'}
TRACK_FREE_ROUND = 6


def track_set_scores(env, snapshot, scores):
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or 'ActionPhase' not in state['phase'] or state['round'] >= TRACK_FREE_ROUND:
        return scores
    player = state['players'][actor]
    if not _part(player, 'track_set') or player['faction'] not in FACTION_TRACKS:
        return scores
    tracks = FACTION_TRACKS[player['faction']]
    candidates = snapshot['candidates']
    act = {i: c['action'] for i, c in enumerate(candidates) if not blocked(scores[i])}

    def track_of(i):
        choice = act[i].get('tech_tile_choice')
        return act[i].get('track') if act[i].get('type') == 'ResearchAdvance' else (choice or {}).get('advance_track')
    research = [i for i in act if act[i].get('type') == 'ResearchAdvance']
    groups = {}
    for i in act:
        choice = act[i].get('tech_tile_choice')
        if isinstance(choice, dict) and choice.get('advance_track'):
            key = json.dumps({**act[i], 'tech_tile_choice': {**choice, 'advance_track': None}}, sort_keys=True)
            groups.setdefault(key, []).append(i)
    lifted = list(scores)
    for group in [research, *groups.values()]:
        if len(group) < 2:
            continue
        best = max(group, key=lambda i: lifted[i][0])
        if 'research when' in str(lifted[best][1]):
            continue   # a situational rule chose this track (user: "트랙은 언제나 상황 맞춰가는 거")
        own = [i for i in group if TRACK_KEYS.get(track_of(i)) in tracks]
        if own and TRACK_KEYS.get(track_of(best)) not in tracks:
            _swap(lifted, list(lifted), max(own, key=lambda i: lifted[i][0]), best,
                  f'{player["faction"]} research on its tracks (track_set)')
    return lifted


# ── helpers kept from the removed families ─────────────────────────────────────────────
def _home_type(player):
    from faction_teachers.profiles import profiles
    return _value.HOME.get(player['faction']) or profiles()[player['faction']].home


def _swap(lifted, scores, mine, top, why):
    """Hand `top`'s score to `mine` and `mine`'s to `top` (order only; the reason is appended)."""
    lifted[mine] = (scores[top][0], f'{scores[mine][1]}; {why}', *scores[mine][2:])
    lifted[top] = (scores[mine][0], *scores[top][1:])


# The tracks each faction's guide names (research/strategy/faction-tracks-openings.md; the four fixed
# factions from B14/B15/B10/B04 and B19, the other ten base factions from B5-02 … B17-02, Lost Fleet
# from the sheden faction articles). Read by track_income 'sweet' (_track_income_excess): Economy is
# counted at every level when it is the faction's first track, Science only when it is a guide track.
# The track_set ordering rule that also read it (when_all_tech, lab 057–060) was removed on 2026-10-19.
FACTION_TRACKS = {'Geodens': ('terraforming', 'navigation', 'economy', 'ai'),
                  'Moweyds': ('science', 'ai'),
                  'SpaceGiants': ('navigation', 'terraforming'),
                  'Tinkeroids': ('science', 'terraforming'),
                  'Darkanians': ('economy', 'navigation'),
                  'Xenos': ('gaia', 'navigation', 'economy'),
                  'Taklons': ('navigation', 'economy', 'science'),
                  'Terrans': ('navigation', 'gaia', 'economy'),
                  'Gleens': ('navigation', 'gaia'),
                  'Ambas': ('terraforming', 'economy', 'science'),
                  'Itars': ('gaia', 'economy', 'terraforming'),
                  'Nevlas': ('economy', 'science', 'navigation'),
                  'Firaks': ('economy', 'navigation', 'gaia'),
                  'BalTaks': ('gaia', 'economy', 'terraforming', 'ai'),
                  'Ivits': ('economy', 'science', 'ai'),
                  'Bescods': ('science', 'economy', 'navigation'),
                  'Lantids': ('navigation', 'science', 'ai'),
                  'HadschHallas': ('economy', 'navigation', 'science')}


