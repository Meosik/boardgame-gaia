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
    'Terrans': frozenset({'terrans_gaia_late',      # _early_terrans_gaia: Gaia research last in rounds 1-3 (guide_r1 ②)
                          'track_income'}),         # 'sweet' (074+076+084: 084 charges +31.3 [+8.2, +54.5] 6/6, VP +20.3;
                                                    # user 2026-10-19 "배포 교사는 바꿔야지", E18)
    'Taklons': frozenset({'brainstone_ships',       # taklons_ship_timing_scores + brainstone_committed (053)
                          'taklons_pi_token'}),     # lf_leech_value: the PI's token per leech (046)
}
CANDIDATE_FACTION_PARTS = {
    # Terrans track_income moved to BASE_FACTION_PARTS on 2026-10-19 (084 passed, E18).
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


# The rest of the faction guides (user 2026-10-19 "반영 안된거부터 처리해야지"): what
# faction-tracks-openings.md says beyond the track priority — round targets for a track level
# (track_steps), level caps (track_caps) and buildings a faction does not build (building_limits) —
# plus track_set for the four Lost Fleet factions (sheden faction articles MW/SG/TK/DK, claims.csv).
# On only in ..._ships_byfaction_guide, on top of CANDIDATE_FACTION_PARTS, so byfaction (085–087) stays
# reproducible and byfaction vs byfaction_guide measures these parts alone. Order only (swaps).
GUIDE_FACTION_PARTS = {
    'Gleens': frozenset({'track_steps', 'track_caps'}),
    'Ambas': frozenset({'track_caps', 'building_limits', 'tile_prefs'}),
    'Itars': frozenset({'track_caps', 'tile_prefs'}),
    'Nevlas': frozenset({'track_caps'}),
    'Firaks': frozenset({'track_steps', 'track_caps', 'building_limits'}),
    # BalTaks academy start (user 2026-10-19 "발타크는 아카데미 스타트 시켜야지"; 086 R1 academies 0 / 12):
    # only the academy openings are targets, with the Taklons budget tools that keep the academy's ore.
    'BalTaks': frozenset({'track_steps', 'track_caps', 'building_limits', 'opening_only', 'fixed_academy',
                          'opening_budget', 'budget_guard', 'opening_release', 'tile_prefs'}),
    'Ivits': frozenset({'track_steps', 'track_caps', 'tile_prefs'}),
    'Bescods': frozenset({'track_steps', 'track_caps', 'tile_prefs'}),
    'Lantids': frozenset({'track_steps', 'track_caps', 'tile_prefs'}),
    'HadschHallas': frozenset({'track_steps', 'track_caps', 'tile_prefs', 'niche_tracks'}),
    # Geodens and Xenos (user 2026-10-20 "기존 자료에 있는 내용 쓸만하면 반영"): B14-01 tile timing, B15-02 Gaia.
    'Geodens': frozenset({'tile_prefs'}),
    'Xenos': frozenset({'niche_tracks'}),
    'Moweyds': frozenset({'track_set'}),
    'SpaceGiants': frozenset({'track_set'}),
    'Tinkeroids': frozenset({'track_set'}),
    'Darkanians': frozenset({'track_set', 'track_steps'}),
}

# The three factions with the fewest round 1-3 charges in 088 (HadschHallas 123.7, Firaks 133.1, Itars −30
# against its quartet; user 2026-10-20 "제안 순서대로 진행해"): the round-1 openings the sources agree on
# (research/strategy/conflicts/weak-factions.md) and HadschHallas' no-early-institute rule. On only in
# ..._ships_byfaction_guide_weak, on top of GUIDE_FACTION_PARTS, so 091 stays as queued. Scope only.
WEAK_FACTION_PARTS = {
    'HadschHallas': frozenset({'opening_only', 'building_limits'}),
    'Itars': frozenset({'opening_only'}),
    'Firaks': frozenset({'opening_only'}),
}

# Source parts (user 2026-10-20 "아직 테스트 하지 않은 종족들의 부품을 구현하거나, 미구현 부분 해결해"): what
# research/strategy/conflicts/ resolved for the other base factions — the BGG openings the sources agree on
# (opening_only), the PG track orders that the experiment teacher had reversed (track_steps_src: Nevlas
# Science, Lantids Economy 2, Ivits Science first) and an institute due round (building_due: Firaks, Itars).
# On only in ..._ships_byfaction_guide_src, on top of GUIDE_FACTION_PARTS (not weak_factions), so 092 and
# 093 measure separate sets. Order and scope only.
# 093 (cycles/093-guide-vs-src-4r.md): the opening lists fired fully only for Gleens (big-mine / two-building
# forecasts rarely complete in 20 s), track_steps_src fired in all three factions, Nevlas +11.2 (5 of 6 pairs).
# `source_tracks` (..._ships_byfaction_guide_srctracks) turns on track_steps_src alone, so the track order is
# judged without the opening lists (user 2026-10-21 "그렇게 해", E59 (ㄱ)).
SOURCE_TRACK_PARTS = frozenset({'track_steps_src'})
SOURCE_FACTION_PARTS = {
    'Ambas': frozenset({'opening_only'}),
    'Bescods': frozenset({'opening_only'}),
    'Gleens': frozenset({'opening_only'}),
    'Nevlas': frozenset({'opening_only', 'track_steps_src'}),
    'Lantids': frozenset({'opening_only', 'track_steps_src'}),
    'Ivits': frozenset({'track_steps_src'}),
    'Firaks': frozenset({'building_due'}),
    'Itars': frozenset({'building_due'}),
}

# Resolved parts (user 2026-10-20 "블로그, 팟캐스트 위주로 진행하고, LF 자료는 최신 자료라 더 잘 반영해야해", "다카니안은
# 상황을 많이 타지. 테라포밍을 많이 구할수 있냐 없냐", "경제랑 과학도 비슷해 …", "자료 충돌과 부품구현부터"): the conflicts
# re-judged in conflicts/base-factions.md "사용자 원칙으로 재판정" — round-1 opening order for Terrans (T1), Taklons
# (K1) and Darkanians (terraforming supply), and the Economy-or-Science first step for Nevlas and Ivits (I1, N1)
# by condition instead of a fixed order. On only in ..._ships_byfaction_guide_res, on top of SOURCE_FACTION_PARTS
# (science_when replaces track_steps_src there). Order only.
RESOLVED_FACTION_PARTS = {
    'Terrans': frozenset({'opening_res'}),
    'Taklons': frozenset({'opening_res'}),
    'Darkanians': frozenset({'opening_res'}),
    'Nevlas': frozenset({'science_when'}),
    'Ivits': frozenset({'science_when'}),
    # Second batch (user 2026-10-20 "미구현부터 구현해"): Xenos round-1 institute only with a reachable tech
    # federation (X1), Bescods institute by round 3 (M3), Itars' first track by its opening (weak-factions.md 2).
    'Xenos': frozenset({'opening_res'}),
    'Bescods': frozenset({'building_due'}),
    # Itars academy Science only (weak-factions.md 3: PG23-S01, B07-S07, SH04-S45; academy_kind_scores).
    'Itars': frozenset({'track_by_opening', 'academy_kind'}),
    # Third batch (user 2026-10-20 "미구현 항목들 개선해"): BalTaks' fixed academy is the credit (QIC) one (B2:
    # PG16-T26, PG02-S05, PG01-S12), HadschHallas keeps the no-institute rule of rounds 1-2 with the LF
    # exception (weak-factions.md 2: SH04-S23, H06 — the Rebellion in our reach, no rival able to press its 3 QIC).
    'BalTaks': frozenset({'qic_academy'}),
    # HadschHallas federation tokens (weak-factions.md 5; user "넘어가"): first token 6 credits, replay first after
    # the institute (fed_token_scores, replay_first_goal).
    'HadschHallas': frozenset({'building_limits', 'institute_rebellion', 'fed_token_credits', 'replay_first',
                               'track_by_neighbour'}),
}


# Parts that only ..._ships_menu1_all adds (E103 ②b, with the mj01 flag): Taklons' charge-4 tile (tile_prefs, K2), Xenos'
# guide tracks with AI late unless a good advanced tile sits on AI (track_set, X4: E97 (ㄱ)).
ALL_FACTION_PARTS = {
    'Taklons': frozenset({'tile_prefs'}),
    'Xenos': frozenset({'track_set'}),
    'Moweyds': frozenset({'opening_res'}),   # institute opening only with a tech federation (TECH_FEDERATION_OPENINGS)
    'Nevlas': frozenset({'tile_prefs'}),     # B19-S60 charge-4 tile not under Gaia (TILE_PREFS)
    'Geodens': frozenset({'opening_res'}),   # E106 institute start (RESOLVED_OPENINGS, SH04/SH09/MJ01-20)
    # User 2026-10-25 (lab 106 Bescods): lab openings, no academy in round 1 (faction-tracks-openings.md, PG01-S23).
    'Bescods': frozenset({'opening_res', 'building_limits'}),
}

# power_prefs (E103 ④, ships_menu1_all only): the power actions a guide ranks, used when a power action is the best
# move — another power action the guide ranks higher and still legal takes its place. Taklons B19-S46 "가장 중요한
# 파워 액션은 1테라, 그다음 2지식" (ids: 6 one terraform step, 5 two knowledge). Order only.
POWER_PREFS = {'Taklons': (6, 5)}


def power_prefs_scores(env, snapshot, scores):
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or 'ActionPhase' not in state['phase']:
        return scores
    player = state['players'][actor]
    order = POWER_PREFS.get(player['faction'])
    if not order or not _part(player, 'mj01'):
        return scores
    act = {i: c['action'] for i, c in enumerate(snapshot['candidates']) if not blocked(scores[i])}
    if not act:
        return scores
    top = max(act, key=lambda i: scores[i][0])
    if act[top].get('type') != 'PowerAction' or act[top].get('id') not in order:
        return scores
    rank = order.index(act[top]['id'])
    better = [i for i, a in act.items() if a.get('type') == 'PowerAction' and a.get('id') in order[:rank]]
    if not better:
        return scores
    lifted = list(scores)
    _swap(lifted, list(scores), max(better, key=lambda i: scores[i][0]), top,
          f"{player['faction']} power action order {order} (B19-S46, power_prefs)")
    return lifted


def _faction_parts(faction):
    parts = set(BASE_FACTION_PARTS.get(faction, ()))
    if _guide['byfaction']:
        parts.update(CANDIDATE_FACTION_PARTS.get(faction, ()))
    if _guide['faction_guide']:
        parts.update(GUIDE_FACTION_PARTS.get(faction, ()))
    if _guide['weak_factions']:
        parts.update(WEAK_FACTION_PARTS.get(faction, ()))
    if _guide['source_parts']:
        parts.update(SOURCE_FACTION_PARTS.get(faction, ()))
    elif _guide['source_tracks']:
        parts.update(SOURCE_FACTION_PARTS.get(faction, frozenset()) & SOURCE_TRACK_PARTS)
    if _guide['resolved_parts']:
        parts.update(RESOLVED_FACTION_PARTS.get(faction, ()))
    if _guide['fed']:
        parts.update(FED_PARTS)
    if _guide['tokens']:
        parts.update(TOKEN_PARTS)
    if _guide['track_plans']:
        parts.add('track_plans')
    if _guide['round_tile_lead']:
        parts.add('round_tile_lead')
    if _guide['plan_menu']:
        parts.update({'plan_menu', 'track_plans'})
    if _guide['mj01']:
        parts.add('mj01')
        parts.update(ALL_FACTION_PARTS.get(faction, ()))
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
          'faction_guide': False,       # True: ..._ships_byfaction_guide (GUIDE_FACTION_PARTS on as well)
          'weak_factions': False,       # True: ..._ships_byfaction_guide_weak (WEAK_FACTION_PARTS on as well)
          'source_parts': False,        # True: ..._ships_byfaction_guide_src (SOURCE_FACTION_PARTS on as well)
          'source_tracks': False,       # True: ..._ships_byfaction_guide_srctracks (track_steps_src of SOURCE_FACTION_PARTS only)
          'resolved_parts': False,      # True: ..._ships_byfaction_guide_res (RESOLVED_FACTION_PARTS on as well)
          'fed': False,                 # True: ..._ships_fed (fed_compare + fed_cluster for every faction)
          'tokens': False,              # True: ..._ships_tokens (token_compare + track_race + race_prune)
          'ship_adjacent_mine': False,  # True: ..._ships_shipmine (see ship_adjacent_mine_scores)
          'endgame_prices': False,      # True: ..._ships_endgame (round 6 stock at the final-scoring rates)
          'track_plans': False,         # True: ..._ships_plans (a research step compared as the plan it opens)
          'round_tile_lead': False,     # True: ..._ships_roundtile (the goals this round's tile scores lead)
          'plan_menu': False,           # True: ..._ships_menu (one plan menu: tile, federation, token, track, ability)
          'menu_first': 3,              # plan_menu front slots (MENU_FIRST); ..._ships_menu1 sets 1 (E89 (ㄷ) B')
          'mj01': False,                # True: ..._ships_menu1_all (MJ01 Lost Fleet track corrections, see MJ_TRACK_CAPS)
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
    tracks = _faction_tracks(player)
    economy = INCOME['economy'][state['research_board']['economy_research_tile_side']]
    level = player['research_tracks']['economy']
    counted = level if tracks[:1] == ('economy',) else min(level, ECONOMY_COUNTED.get(faction, ECONOMY_SWEET))
    if _part(player, 'mj01'):
        counted = min(counted, MJ_ECONOMY_CAP)
    excess = [a-b for a, b in zip(economy[level], economy[counted])]
    if 'science' not in tracks:
        excess = [a+b for a, b in zip(excess, INCOME['science'][player['research_tracks']['science']])]
    return excess


FINAL_RESOURCES_PER_VP = 3     # rulebook p.18 / scoring.rs: 1 VP per 3 ore, credits and knowledge
FINAL_RESEARCH_VP = 4          # 4 VP per research level reached among 3, 4 and 5


def endgame_stock_vp(player):
    """What the final scoring pays for the stock held now (fractions kept so the ranking keeps a slope)."""
    res = player['resources']
    stock = (res.get('ore', 0) + res.get('credits', 0) + res.get('knowledge', 0)) / FINAL_RESOURCES_PER_VP
    levels = sum(min(3, max(0, level - 2)) for level in player['research_tracks'].values())
    return stock + FINAL_RESEARCH_VP*levels


def guide_potential(state, actor, *, home=None, guide_tracks=False):
    import guide_value as gv
    v = _value
    phase = state['phase']
    if isinstance(phase, dict) and 'Ended' in phase:
        return float(dict(phase['Ended']['final_scores'])[actor])
    player = state['players'][actor]
    horizon = max(0, 6-state['round'])
    result = player['vp'] + v.standings(state, actor)
    power = player['resources']['power']
    if not horizon and (_guide['endgame_prices'] or _part(player, 'endgame_prices')):
        # endgame_prices (user 2026-10-20, 090 p003 Terrans: 9 QIC held in round 6 while the Twilight
        # token replay — 3 QIC for 8 VP — ranked −1.33 because a QIC was still 7 charges): in the last
        # round the stock is worth what the final scoring pays (scoring.rs): 1 VP per 3 ore + credits +
        # knowledge, QIC and power nothing, 4 VP per research level reached among 3-5. Moves that turn
        # the stock into VP within the round show their VP themselves.
        result += endgame_stock_vp(player)
    else:
        result += gv.research_value(state, player)
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



# opening_res (RESOLVED_FACTION_PARTS, conflicts/base-factions.md "사용자 원칙으로 재판정"): blog and podcast first, LF
# sources weighted up. Terrans T1: institute openings (B4-03, PG18-T01; with a trading station when a round-1
# federation is on, SH04-S18 — the federation condition is not modelled, so the search compares both), then
# lab + 4 mines (PG18-T02, SH04 rank 1), academy last (PG18-T04 "AC 금지"). Taklons K1: academy + 2 mines
# (B10-03, PG21-T10), then lab + 5 / 4 mines (B19-05, SH04-S37), two labs last (PG21-T11).
RESOLVED_OPENINGS = {
    'Terrans': ('1PI+2M', '1PI+1TS+2M', '1RL+4M', '1AC+1M'),
    'Taklons': ('1AC+2M', '1RL+5M', '1RL+4M', '2RL+2M'),
    'Xenos': ('1RL+5M', '1RL+6M', '1AC+2M', '1RL+2M'),
    # Geodens, ships_menu1_all only (E106; ALL_FACTION_PARTS opening_res): the Lost Fleet sources start with the institute —
    # SH04 rank 1 의4광·의교2광, SH09 "의회 빌드가 강제", MJ01-20 — against B14's base-game academy start (UIQOO_OPENINGS,
    # user 2026-10-16 "기오덴 빼줘" removed the BGG institute-first part then). A label the catalog lacks is not proposed.
    'Geodens': ('1PI+1TS+2M', '1PI+4M', '1PI+2M', '1RL+1TS+2M', '1AC+2M'),
    # Bescods, ships_menu1_all only (user 2026-10-25, lab 106 pair-014; faction-tracks-openings.md, PG01-S23): lab openings,
    # the academy first is the worst (UIQOO_OPENINGS ends with '1AC+2M'; BUILDING_LIMITS blocks the round-1 academy).
    'Bescods': ('1RL+1TS+2M', '1RL+2M', '2RL'),
}
# With a round-1 tech federation in reach (LF token 12 "tech tile of choice" on a ship board within
# SHIP_SETUP_RANGE of our buildings: C004, LF3-10, SH02-S07 "the only reason to design a round-1 opening"):
# Terrans the institute + trading station first (SH04-S18), Xenos the institute opening (SH04-S33 rank 2,
# X10 Rebellion) — otherwise Xenos keeps no institute at the front (X1: B19-04, BGGO1-S17 −30 VP); X5 lab with
# 5-6 mines or academy is left to the search's reachability.
TECH_FEDERATION_TOKEN = 12
TECH_FEDERATION_OPENINGS = {
    'Terrans': ('1PI+1TS+2M', '1PI+2M', '1RL+4M', '1AC+1M'),
    'Xenos': ('1PI+1TS+1M', '1RL+5M', '1RL+6M', '1AC+2M'),
    # Moweyds (E103, ships_menu1_all only): the institute first only with a tech federation to make (SH-MW
    # MW-02~04, MJ01-14 "선의회는 특수한 경우 외 비권장"); otherwise LOST_FLEET_OPENINGS' lab openings stay first.
    'Moweyds': ('1PI+1TS', '1PI+1TS+1M', '1PI+1RL', '1PI+2M', '1RL+4M', '1RL+1TS+2M'),
}


def tech_federation_reachable(snapshot):
    """The LF tech-tile federation token sits on a ship whose tile is within SHIP_SETUP_RANGE of our buildings."""
    from strategy_teacher import distance
    state = snapshot['state']
    player = state['players'][snapshot['player']]
    tiles = state['board'].get('spaceship_tiles') or {}
    for board in state.get('spaceship_boards') or ():
        at = tiles.get(board.get('id'))
        if board.get('federation_token') == TECH_FEDERATION_TOKEN and at is not None and any(
                distance(s['hex'], at) <= SHIP_SETUP_RANGE for s in player['structures']):
            return True
    return False
# Darkanians (general-and-lf.md, user "테라포밍을 많이 구할수 있냐 없냐"): with terraforming at hand in round 1 the
# expansion builds (institute for new-sector mines: PG25-S25, SH-DK; lab + 4 mines: SH04-S53), without it the
# academy first (SH-DK "1테라 부스터와 TF마스가 생명줄", academy when the institute cannot reach two mines).
# Supply counted from facts: the 1-terraform round booster (engine ROUND_BOOSTER_TERRAFORM 12) and the TF Mars
# ship within SHIP_SETUP_RANGE of our buildings. Rich at one or more (bot's reading; the user's threshold is open).
DARKANIAN_OPENINGS = {True: ('1PI+1TS+2M', '1RL+4M', '1RL+1TS+2M', '1AC+1M'),
                      False: ('1AC+1M', '1RL+1TS+2M', '1RL+4M', '1PI+1TS+2M')}
TERRAFORM_BOOSTER = 12
DARKANIAN_TERRA_RICH = 1


def darkanian_terraforming(snapshot):
    """Round-1 terraforming sources at hand: the terraform booster held, the TF Mars ship within reach."""
    from strategy_teacher import distance
    state = snapshot['state']
    player = state['players'][snapshot['player']]
    supply = int(player.get('booster') == TERRAFORM_BOOSTER)
    mars = (state['board'].get('spaceship_tiles') or {}).get('TFMars')
    if mars is not None and any(distance(s['hex'], mars) <= SHIP_SETUP_RANGE for s in player['structures']):
        supply += 1
    return supply


def guide_opening_labels(faction, snapshot=None):
    """The guide's round-1 opening order for a faction, () when no guide order applies."""
    if snapshot is not None and _part({'faction': faction}, 'opening_res'):
        if faction == 'Darkanians':
            return DARKANIAN_OPENINGS[darkanian_terraforming(snapshot) >= DARKANIAN_TERRA_RICH]
        if faction in TECH_FEDERATION_OPENINGS and tech_federation_reachable(snapshot):
            return TECH_FEDERATION_OPENINGS[faction]
        if faction in RESOLVED_OPENINGS:
            return RESOLVED_OPENINGS[faction]
    return UIQOO_OPENINGS.get(faction) or ()


def uiqoo_opening_order(snapshot, goals, remembered=None):
    faction = snapshot['state']['players'][snapshot['player']]['faction']
    order = guide_opening_labels(faction, snapshot)
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


# Far-start exception, ships_menu1_all only (user 2026-10-25, lab 106 pair-014 Bescods, known-bad-decisions.md 12): a start
# that is not next to an opponent stays allowed when (a) a free planet within the setup reach of it is a cheap mine (at most
# one terraforming step from the home type) and itself next to an opponent — a cheap trading station without upgrading the
# setup planet — or (b) round booster 5 (instant Gaia, engine actions.rs:166) is in the supply and instant_gaia_spot holds.
FAR_START_TERRAFORM_STEPS = 1
# instant_gaia_spot (user 2026-10-25 "booster 5 first is too eager: only with 2 Transdim planets nearby and hard expansion
# elsewhere", known-bad-decisions.md 12/15): at least this many free Transdim planets and at most EASY_EXPANSION_MAX cheap
# non-Transdim free planets within reach.
INSTANT_GAIA_TRANSDIM = 2
EASY_EXPANSION_MAX = 1


def _free_planet(cell):
    return bool(cell['planet']) and cell['planet']['owner'] is None and not cell['structures']


def _reach(player):
    return _value.navigation(player) if player.get('research_tracks') else 1


def _cheap_planet(home, kind):
    """True when `kind` is on the terraforming ring and at most FAR_START_TERRAFORM_STEPS steps from `home`."""
    from economy.teacher import RING
    if home not in RING or kind not in RING:
        return False
    gap = abs(RING.index(home)-RING.index(kind))
    return min(gap, 7-gap) <= FAR_START_TERRAFORM_STEPS


def instant_gaia_spot(state, actor, coords):
    """Within reach of any of `coords`: at least INSTANT_GAIA_TRANSDIM free Transdim planets and at most EASY_EXPANSION_MAX
    cheap free planets of other types."""
    from faction_teachers.profiles import profiles
    from strategy_teacher import distance
    player = state['players'][actor]
    reach = _reach(player)
    profile = profiles().get(player['faction'])
    home = profile.home if profile else None
    transdim = easy = 0
    for c, cell in state['board']['hexes'].items():
        if c in coords or not _free_planet(cell) or not any(distance(h, c) <= reach for h in coords):
            continue
        kind = cell['planet']['planet_type']
        if kind == 'Transdim':
            transdim += 1
        elif _cheap_planet(home, kind):
            easy += 1
    return transdim >= INSTANT_GAIA_TRANSDIM and easy <= EASY_EXPANSION_MAX


def far_start_allowed(state, actor, start):
    from faction_teachers.profiles import profiles
    from strategy_teacher import distance
    player = state['players'][actor]
    if not _part(player, 'mj01'):
        return False
    hexes = state['board']['hexes']
    if INSTANT_GAIA_BOOSTER in state.get('boosters', ()) and instant_gaia_spot(state, actor, [start]):
        return True
    profile = profiles().get(player['faction'])
    if not profile:
        return False
    reach = _reach(player)
    sites = _future_opponent_sites(state, actor)
    for c, cell in hexes.items():
        if c == start or not _free_planet(cell) or distance(start, c) > reach:
            continue
        if _cheap_planet(profile.home, cell['planet']['planet_type']) and (
                _next_to_opponent(state, actor, c) or _near_sites(state, actor, c, sites)):
            return True
    return False


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
        if action['type'] == 'PlaceStartingStructure' and near and i not in near \
                and not far_start_allowed(state, actor, action['coord']):
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
    if _guide.get('plan_menu') and state['round'] >= 2:
        late = []    # E96 debate: the BGG round-1 order demoted Terraforming-3 / Navigation-2 in every round
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
        # Only a label of the faction's BGG table is kept: preparation.search raises on a saved target
        # outside it, and the Lost Fleet labels (LOST_FLEET_OPENINGS) have no table (smoke 2026-10-19:
        # every Lost Fleet game stopped with "Saved BGG target does not belong to the actual faction").
        from bgg_openings.catalog import load_catalog
        faction = snapshot['state']['players'][snapshot['player']]['faction']
        if target in {row.label for row in load_catalog().get(faction, ())}:
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
    mj01 = _part(player, 'mj01')
    transdim = sorted((qic, nav, coord) for coord, _, qic, nav in _reach_targets(state, player, ('Transdim',)))
    if mj01 and transdim and _tfmars_gaia_ready(state, player):
        # MJ01-06: the T F Mars action gaiaforms a Transdim planet at once for 2 printed power, no tokens locked — only
        # once explored, unused this round, payable and with an idle former (engine.rs validate_tfmars_gaia_formation).
        # The cheapest planet takes this path and leaves the normal Gaia projects (one planet, one path).
        qic, nav, _ = transdim.pop(0)
        options.append(({**MINE_COST, 'qic': qic}, -2*_tfmars_tokens(player), nav))
    if room and not former_use:
        options += [({**MINE_COST, 'qic': qic}, GAIA_TOKENS[level]*terrans, nav) for qic, nav, _ in transdim[:room]]
    # Formers on a planet or in the Gaia area come back, so every former not yet used up counts.
    formers = (max(0, player['gaiaformers_total'] - player['resources']['spent_gaia_formers'])
               if former_use or mj01 else 0)
    if formers:
        # Lost Fleet rulebook: a mine on an Asteroid costs no ore or credits, only the range QIC,
        # and uses up one Gaia former.
        asteroids = sorted((qic, nav) for _, _, qic, nav in _reach_targets(state, player, ('Asteroid',)))[:formers]
        options += [({'qic': qic}, 0, nav) for qic, nav in asteroids]
    return options


TFMARS_SHIP = 2                 # engine spaceship_id_to_ship_id(TFMars)
TFMARS_GAIA_ACTION = 6          # engine SPACESHIP_ACTION_TFMARS_GAIA_FORMATION
TFMARS_GAIA_POWER = 2           # printed power cost (each token spent from bowl III is 2 charges in the charge measure)


def _tfmars_tokens(player):
    """Tokens the 2-power action spends: Nevlas with the institute pay half, rounded up (engine power_action_token_cost)."""
    nevlas_pi = player['faction'] == 'Nevlas' and any(
        _structure_kind(s) == 'PlanetaryInstitute' for s in player.get('structures', ()))
    return -(-TFMARS_GAIA_POWER // 2) if nevlas_pi else TFMARS_GAIA_POWER


def _tfmars_gaia_ready(state, player):
    """The T F Mars instant Gaia formation is usable now: ship explored, action space free, payable (bowl III plus a
    Brainstone there counting 3 — engine spendable_power_value), an idle former."""
    power = player['resources']['power']
    spendable = power['bowl3'] + (3 if power.get('brainstone') == 'Area3' else 0)
    return (TFMARS_SHIP in (player.get('explored_ships') or ())
            and TFMARS_GAIA_ACTION not in (state.get('used_spaceship_actions') or ())
            and spendable >= _tfmars_tokens(player)
            and _idle_formers(player) > 0)


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
    install_task_dedup()            # E90: each plan once in the comparison order (deployed stack and everything on top)
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
    caps = _track_caps(player, table=_part(player, 'track_caps'))
    levels = player.get('research_tracks') or {}
    # A guide track at its cap counts as off the faction's tracks (track_caps).
    tracks = tuple(t for t in _faction_tracks(player) if levels.get(t, 0) < caps.get(t, 99))
    if player['faction'] == 'Xenos' and _part(player, 'mj01') and \
            state['research_board']['advanced_tech_tiles'][AI_SLOT] in GOOD_ADVANCED:
        tracks += ('ai',)      # X4 (base-factions.md:65): a good advanced tile on AI makes early AI worth it
    if 'gaia' not in tracks and _asteroid_gaia(state, player):
        tracks += ('gaia',)
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


# ── faction guide rest (GUIDE_FACTION_PARTS; faction-tracks-openings.md, B05–B17, DK-03) ────────
# track_caps: the level the guide stops a track at before round 6 (track_set treats a capped track as
# off the faction's tracks). Ambas Gaia 1 (B06), Itars Navigation 2 (B07), Nevlas / Firaks / Lantids /
# HadschHallas / Bescods Navigation 2, Ivits Navigation 2 and Gaia 1 (B12), Gleens Navigation 4
# ("끝 4", B05), BalTaks AI 4 (B11), Bescods Economy 4, Lantids Science 4, HadschHallas Economy 4
# ("2·4 sweet spot", B17).
TRACK_CAPS = {'Ambas': {'gaia': 1},
              'Itars': {'navigation': 2},
              'Nevlas': {'navigation': 2},
              'Firaks': {'navigation': 2},
              'Ivits': {'navigation': 2, 'gaia': 1},
              'Gleens': {'navigation': 4},
              'BalTaks': {'ai': 4},
              'Bescods': {'navigation': 2, 'economy': 4},
              'Lantids': {'navigation': 2, 'science': 4},
              'HadschHallas': {'navigation': 2, 'economy': 4}}

# track_steps: (from round, track, level) in the guide's order — from that round until round 5, while
# the level is not reached, that track's advance leads the research moves and the track variants of a
# tile choice (the first unmet entry that is offered). Gleens Navigation 2 in round 1 (B05), BalTaks
# Gaia 4 in round 1 ("필수", B11), Ivits Economy 2 in round 1 (B12), Bescods Science 2 in round 1,
# Economy 2 in round 2, Navigation 2 in round 3 (B13), Firaks Economy 4 first, Navigation 2 from round 3
# (B09), Lantids Navigation 2 first (B16), HadschHallas Economy 2 (B17), Darkanians Economy 2 (DK-03).
# Research against other moves is unchanged (order only).
TRACK_STEPS = {'Gleens': ((1, 'navigation', 2),),
               'BalTaks': ((1, 'gaia', 4),),
               'Ivits': ((1, 'economy', 2),),
               'Bescods': ((1, 'science', 2), (2, 'economy', 2), (3, 'navigation', 2)),
               'Firaks': ((1, 'economy', 4), (3, 'navigation', 2)),
               'Lantids': ((1, 'navigation', 2),),
               'HadschHallas': ((1, 'economy', 2),),
               'Darkanians': ((1, 'economy', 2),)}

# mj01 (research/strategy/mj01-lf-changes-factions.md, user 2026-10-24 "일단 반영할거 다 반영해봐", E104; on in
# ..._ships_menu1_all only): the Lost Fleet corrections of the tables above. Economy 3-4 were weakened in the
# expansion and are not raised before the late game, Economy 2 stays good (MJ01-10; Firaks MJ01-21 "초반 경제 3–4
# 비추"): every faction's Economy is capped at 2 before round 6 and track_income counts it at most to 2, and Firaks'
# round-1 Economy 4 target becomes Economy 2. Terrans keep Gaia 1 and go Terraforming or AI (MJ01-23, too many Gaia
# rivals in the expansion; replaces T2 there); Space Giants skip Terraforming for Gaia forming (MJ01-13, the free two
# steps a round are enough); Darkanians skip Terraforming and get Navigation 3 early, then Economy / AI (MJ01-11, the
# TF Mars and Eclipse ships carry the expansion); Geodens may take Gaia 1 (MJ01-20). Order and scope only.
MJ_ECONOMY_CAP = 2
MJ_TRACK_CAPS = {'Terrans': {'gaia': 1}, 'SpaceGiants': {'terraforming': 0},
                 'Darkanians': {'terraforming': 0}, 'Geodens': {'gaia': 1}, 'Taklons': {'gaia': 1}}
MJ_TRACK_STEPS = {'Firaks': ((1, 'economy', 2), (3, 'navigation', 2)),
                  'Darkanians': ((1, 'economy', 2), (1, 'navigation', 3))}
MJ_FACTION_TRACKS = {'Terrans': ('navigation', 'terraforming', 'ai', 'economy'),
                     'SpaceGiants': ('navigation', 'gaia'),
                     'Darkanians': ('navigation', 'economy', 'ai'),
                     'Geodens': ('terraforming', 'navigation', 'economy', 'ai', 'gaia')}


def _asteroid_gaia(state, player):
    """mj01: Gaia 1 joins the faction's tracks while it has no former and an empty Asteroid is in reach now — the
    Lost Fleet former-on-Asteroid mine makes Gaia 1 an early expansion step (SH11 p.17 "테라포밍 1단계보다 나은 경우가
    많다", SH03 p.8 "소행성에 건물을 지을 수 있으면 가이아 트랙"). Capped at 1 by _track_caps for the factions whose
    guide has no Gaia track."""
    if not _part(player, 'mj01') or (player.get('research_tracks') or {}).get('gaia', 0) > 0:
        return False
    if player.get('gaiaformers_total', 0) > 0 or not player.get('structures'):
        return False
    if _reach_targets(state, player, ('Asteroid',)):
        return True
    # User 10-25 "가이아 즉시포밍 > 그 후 닿는 곳에 소행성이면 충분": with an instant formation at hand (the T F Mars action or
    # round booster 5) the former first turns a reachable Transdim planet into a mine, then goes to an Asteroid in range
    # of that new mine (SH02 T F Mars opening: Gaia 1 → instant formation → former removed → Asteroid mine).
    if not _instant_gaia_source(state, player):
        return False
    # Both legs as four_factions.value.targets counts reach (range + 2 hexes a QIC); the second leg from the new mine
    # with the QIC left after the first (debate 1/1).
    from economy.teacher import path_distance
    rng, qic = _value.navigation(player), player['resources']['qic']
    asteroids = [c for c, cell in state['board']['hexes'].items() if cell.get('planet')
                 and cell['planet'].get('planet_type') == 'Asteroid' and cell['planet'].get('owner') is None
                 and not cell.get('structures')]
    for t, _, first, _ in _reach_targets(state, player, ('Transdim',)):
        for a in asteroids:
            if max(0, (path_distance(state, [t], a) - rng + 1)//2) <= qic - first:
                return True
    return False


INSTANT_GAIA_BOOSTER = 5        # engine ROUND_BOOSTER_IMMEDIATE_GAIA
CREDIT_QIC_BOOSTER = 9          # round booster 9: 2 credits + 1 QIC (user 2026-10-25)


def _instant_gaia_source(state, player):
    """An instant Gaia formation this round: round booster 5 held, or T F Mars explored with its action space free."""
    return (player.get('booster') == INSTANT_GAIA_BOOSTER
            or (TFMARS_SHIP in (player.get('explored_ships') or ())
                and TFMARS_GAIA_ACTION not in (state.get('used_spaceship_actions') or ())))


def _faction_tracks(player):
    """The faction's guide tracks (FACTION_TRACKS), with the mj01 corrections when that part is on."""
    if _part(player, 'mj01') and player['faction'] in MJ_FACTION_TRACKS:
        return MJ_FACTION_TRACKS[player['faction']]
    return FACTION_TRACKS.get(player['faction'], ())


def _track_caps(player, table=True):
    """{track: cap} — TRACK_CAPS (when `table`), with the mj01 Economy cap and corrections on top."""
    caps = dict(TRACK_CAPS.get(player['faction'], {})) if table else {}
    if _part(player, 'mj01'):
        caps['economy'] = min(caps.get('economy', 5), MJ_ECONOMY_CAP)
        caps.update(MJ_TRACK_CAPS.get(player['faction'], {}))
        if 'gaia' not in _faction_tracks(player):
            caps['gaia'] = min(caps.get('gaia', 5), 1)      # _asteroid_gaia: Gaia 1 only for the former
        active =set(player.get('tech_tiles') or ()) - set(player.get('covered_tech_tiles') or ())
        if RANGE_TILE in active:      # MJ01-08: with the +1 range tile Navigation is not raised any more
            caps['navigation'] = min(caps.get('navigation', 5), (player.get('research_tracks') or {}).get('navigation', 0))
    return caps


# range_tile (MJ01-08; ships_menu1_all only): the Lost Fleet +1 range standard tile (engine id 12, four_factions.value
# .navigation) is taken in round 1 — round 2 at the latest — and not from round 3; with it Navigation stops (_track_caps).
# Among the tile variants of one move: rounds 1-2 the tile-12 variant leads, from round 3 it swaps with the best other.
RANGE_TILE = 12
RANGE_TILE_LAST_ROUND = 2
# SH11 p.40 / SH04 Gleens "첫 타일로 가이아 3점을 먹으면 나중에 자원이 모자람": the VP-per-Gaia tile (8) is not the first
# standard tile, for every faction; among the variants of one move it swaps with the best other (range_tile_scores).
GAIA_VP_TILE = 8


def range_tile_scores(env, snapshot, scores):
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or 'ActionPhase' not in state['phase']:
        return scores
    if not _part(state['players'][actor], 'mj01'):
        return scores
    groups, tiles = {}, {}
    for i, c in enumerate(snapshot['candidates']):
        found = None if blocked(scores[i]) else _tile_choice(c['action'])
        if found is not None:
            key, tiles[i] = found
            groups.setdefault(key, []).append(i)
    lifted = list(scores)
    early = state['round'] <= RANGE_TILE_LAST_ROUND
    player = state['players'][actor]
    first_tile = not (player.get('tech_tiles') or ())
    # Both avoidances apply together (debate 1/1: one swap must not hand the top to a tile the other avoids).
    avoid = ({GAIA_VP_TILE} if first_tile else set()) | (set() if early else {RANGE_TILE})
    for members in groups.values():
        top = max(members, key=lambda i: lifted[i][0])
        wanted = [i for i in members if tiles[i] == RANGE_TILE] if early else []
        if wanted and top not in wanted:
            _swap(lifted, list(lifted), max(wanted, key=lambda i: lifted[i][0]), top, 'range tile in rounds 1-2 (MJ01-08)')
            continue
        allowed = [i for i in members if tiles[i] not in avoid]
        if tiles[top] in avoid and allowed:
            why = 'no Gaia-VP tile as the first tile (SH11, SH04)' if tiles[top] == GAIA_VP_TILE else \
                'no range tile from round 3 (MJ01-08)'
            _swap(lifted, list(lifted), max(allowed, key=lambda i: lifted[i][0]), top, why)
    return lifted if lifted != scores else scores


def _track_steps_table(player):
    """TRACK_STEPS for the faction, or its mj01 replacement."""
    if _part(player, 'mj01') and player['faction'] in MJ_TRACK_STEPS:
        return MJ_TRACK_STEPS[player['faction']]
    return TRACK_STEPS.get(player['faction'], ())
# track_steps_src (SOURCE_FACTION_PARTS): the PG order where conflicts/base-factions.md found the B blog
# order in TRACK_STEPS against a "상" podcast source; replaces the faction's TRACK_STEPS entry. Nevlas
# Science 3 in round 1, Economy first is "a trap" (N1: PG10-S18·S19); Lantids Economy 2 first, round-1
# Navigation "completely wrong" (L1: PG06-S04·S12·S25, PG25-S07 LF); Ivits Science first (I1: PG22-S14·S16).
TRACK_STEPS_SRC = {'Nevlas': ((1, 'science', 3),),
                   'Lantids': ((1, 'economy', 2),),
                   'Ivits': ((1, 'science', 2),)}
# science_when (RESOLVED_FACTION_PARTS; user 2026-10-20 "과학쪽 고급 기술이 맛있거나, 5 6라운드에 트랙 상승 점수가 잇거나,
# 좋은 고급기술이 많을때. 과학을 올릴 수 있는 종족은 애초에 경제가 조금은 받혀주니까" — science first still keeps the
# upgrades going): the science entry when the round 5 or 6 tile scores research steps, the Advanced tile above
# Science is S or A tier, or S/A tiles are many on the board (knowledge reaches them); else the economy entry
# (Ivits B12-02, Nevlas B8-02). "Good" = S/A in the LF tier list (user "자료에 나와있는 S급 A급 중에 과학을 올렸을때
# 먹을수 있을만한거"; LF2-11: S federation pass 3 (11), lab pass 3 (7), mine 3 (4); A research step 2 (8),
# 1 QIC 5 credits (22), terraform step 2 (17), asteroid pass 2 (14); ids as integrated.features). "Many" = half
# of the six tracks or more (bot's reading, not the user's number).
SCIENCE_WHEN = {'Nevlas': (((1, 'science', 3),), ((1, 'economy', 2),)),
                'Ivits': (((1, 'science', 2),), ((1, 'economy', 2),))}
# track_by_opening (RESOLVED_FACTION_PARTS, weak-factions.md Itars 2 "첫 트랙을 오프닝에 맞춤": SH04-S44,
# PG23-S16·S19, B07-S16·S18): with the institute Gaia 1 in round 1, with an academy Economy 2.
TRACK_BY_OPENING = {'Itars': (('PlanetaryInstitute', ((1, 'gaia', 1),)), ('Academy', ((1, 'economy', 2),)))}
# track_by_neighbour (RESOLVED_FACTION_PARTS, weak-factions.md HadschHallas: B17, PG19 "인접 종족이 있으면 2R까지 항해 2로
# 모행성 수비, 아니면 경제 2"; user 2026-10-20 "하드쉬 다음으로 이어서 진행해"): (steps with a neighbour, steps without).
# A neighbour = a rival building within NEIGHBOUR_RANGE of one of ours, read in rounds 1-2 (the bot's reading of
# "인접"; the user's distance is open). From round 3 the faction's TRACK_STEPS entry applies.
TRACK_BY_NEIGHBOUR = {'HadschHallas': (((1, 'navigation', 2),), ((1, 'economy', 2),))}
NEIGHBOUR_RANGE = 2
NEIGHBOUR_ROUNDS = 2
GOOD_ADVANCED = frozenset({11, 7, 4, 8, 22, 17, 14})
GOOD_ADVANCED_MANY = 3


def science_first(state, player):
    if any(tile.get('condition') == 'ResearchAdvance' for tile in (state.get('round_tiles') or [])[4:6]):
        return True
    board = state['research_board']['advanced_tech_tiles']
    if board[5] in GOOD_ADVANCED:
        return True
    return sum(tile in GOOD_ADVANCED for tile in board) >= GOOD_ADVANCED_MANY


TRACK_STEPS_LAST_ROUND = 5
TRACK_NAMES = {key: name for name, key in TRACK_KEYS.items()}


def rival_adjacent(state, actor):
    """A rival building within NEIGHBOUR_RANGE of one of ours."""
    from strategy_teacher import distance
    ours = [s['hex'] for s in state['players'][actor].get('structures', ())]
    return any(distance(s['hex'], h) <= NEIGHBOUR_RANGE for i, p in enumerate(state['players']) if i != actor
               for s in p.get('structures', ()) for h in ours)


def track_steps_scores(env, snapshot, scores):
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or 'ActionPhase' not in state['phase'] or state['round'] > TRACK_STEPS_LAST_ROUND:
        return scores
    player = state['players'][actor]
    when = _part(player, 'science_when') and player['faction'] in SCIENCE_WHEN
    src = _part(player, 'track_steps_src') and player['faction'] in TRACK_STEPS_SRC
    built = {_structure_kind(s) for s in player.get('structures', ())}
    opening = next((steps for kind, steps in TRACK_BY_OPENING.get(player['faction'], ()) if kind in built), None) \
        if _part(player, 'track_by_opening') else None
    neighbour = (_part(player, 'track_by_neighbour') and player['faction'] in TRACK_BY_NEIGHBOUR
                 and state['round'] <= NEIGHBOUR_ROUNDS)
    if not (when or src or opening or neighbour or _part(player, 'track_steps')):
        return scores
    levels = player.get('research_tracks') or {}
    if opening:
        steps = opening
    elif neighbour:
        steps = TRACK_BY_NEIGHBOUR[player['faction']][0 if rival_adjacent(state, actor) else 1]
    elif when:
        steps = SCIENCE_WHEN[player['faction']][0 if science_first(state, player) else 1]
    else:
        steps = TRACK_STEPS_SRC.get(player['faction'], ()) if src else _track_steps_table(player)
    wanted = [TRACK_NAMES[t] for start, t, level in steps
              if start <= state['round'] and levels.get(t, 0) < level]
    if not wanted:
        return scores
    candidates = snapshot['candidates']
    act = {i: c['action'] for i, c in enumerate(candidates) if not blocked(scores[i])}

    def track_of(i):
        if act[i].get('type') == 'ResearchAdvance':
            return act[i].get('track')
        return _tile_track(state, act[i].get('tech_tile_choice'))
    research = [i for i in act if act[i].get('type') == 'ResearchAdvance']
    groups = {}
    for i in act:
        choice = act[i].get('tech_tile_choice')
        if isinstance(choice, dict) and choice.get('kind') == 'Standard':
            key = json.dumps({**act[i], 'tech_tile_choice': {**choice, 'advance_track': None}}, sort_keys=True)
            groups.setdefault(key, []).append(i)
    lifted = list(scores)
    for group in [research, *groups.values()]:
        if len(group) < 2:
            continue
        best = max(group, key=lambda i: lifted[i][0])
        for track in wanted:
            lead = [i for i in group if track_of(i) == track]
            if lead:
                break
        else:
            continue
        if best not in lead:
            _swap(lifted, list(lifted), max(lead, key=lambda i: lifted[i][0]), best,
                  f'{player["faction"]} {track} to its guide level (track_steps)')
    return lifted


# building_limits: buildings the guide says a faction does not build, through a round. Firaks never an
# academy ("아카데미 안 지음", B09), BalTaks no planetary institute before round 6 ("의회 안 지음(6R 티어 외)",
# B11), Ambas the institute in rounds 3–4 ("의회 3–4R", B06), so not in rounds 1–2. When the best move
# builds one, it swaps scores with the best move that does not (order only).
BUILDING_LIMITS = {'Firaks': (('Academy', 6),),
                   'BalTaks': (('PlanetaryInstitute', 5),),
                   'Ambas': (('PlanetaryInstitute', 2),),
                   # weak_factions: no institute in rounds 1-2 (BGG PI openings 110-127 vs 141 without, BGGO1-S10,
                   # BGGO2-S22; PG19-S27 "2R 의회는 실수", PG19-S33 3-4R). The LF Rebellion 3-QIC exception is the
                   # institute_rebellion part (resolved_parts): the rule is dropped while rebellion_reachable.
                   'HadschHallas': (('PlanetaryInstitute', 2),),
                   # ships_menu1_all only (ALL_FACTION_PARTS): no academy in round 1 (user 2026-10-25, PG01-S23).
                   'Bescods': (('Academy', 1),)}


REBELLION = 1                # ship id in explored_ships (engine spaceship_id_to_ship_id)
REBELLION_TECH_QIC = 3       # engine REBELLION_GAIN_TECH_TILE_QIC_COST (once a round for everyone)


def rebellion_reachable(snapshot):
    """The LF exception's "3 QIC 확정" read from facts (SH04-S23, H06; user 2026-10-20 "일단 그렇게 해"): we have
    explored the Rebellion or its tile is within SHIP_SETUP_RANGE of our buildings, and no rival can press its
    3-QIC action now — explored the Rebellion and holding 3 QIC (engine.rs validate_rebellion_gain_tech_tile).
    Next round's income and the turn order are not predicted."""
    from strategy_teacher import distance
    state, actor = snapshot['state'], snapshot['player']
    player = state['players'][actor]
    at = (state['board'].get('spaceship_tiles') or {}).get('Rebellion')
    if REBELLION not in (player.get('explored_ships') or ()) and (at is None or not any(
            distance(s['hex'], at) <= SHIP_SETUP_RANGE for s in player['structures'])):
        return False
    return not any(REBELLION in (p.get('explored_ships') or ()) and p['resources']['qic'] >= REBELLION_TECH_QIC
                   for i, p in enumerate(state['players']) if i != actor)


def _upgrade_target(action):
    if action.get('type') != 'Upgrade':
        return None
    target = action.get('to')
    return next(iter(target)) if isinstance(target, dict) else target


def building_limits_scores(env, snapshot, scores):
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or 'ActionPhase' not in state['phase']:
        return scores
    player = state['players'][actor]
    if not _part(player, 'building_limits'):
        return scores
    limited = {building for building, last in BUILDING_LIMITS.get(player['faction'], ()) if state['round'] <= last}
    if 'PlanetaryInstitute' in limited and _part(player, 'institute_rebellion') and rebellion_reachable(snapshot):
        limited.discard('PlanetaryInstitute')
    if not limited:
        return scores
    candidates = snapshot['candidates']
    open_ = [i for i in range(len(candidates)) if not blocked(scores[i])]
    if not open_:
        return scores
    best = max(open_, key=lambda i: scores[i][0])
    if _upgrade_target(candidates[best]['action']) not in limited:
        return scores
    others = [i for i in open_ if _upgrade_target(candidates[i]['action']) not in limited]
    if not others:
        return scores
    lifted = list(scores)
    _swap(lifted, list(scores), max(others, key=lambda i: scores[i][0]), best,
          f'{player["faction"]} does not build this (building_limits)')
    return lifted


# academy_kind (RESOLVED_FACTION_PARTS): the only academy kind the guide allows a faction — Itars Science
# ("아카데미는 지식만": PG23-S01, B07-S07, SH04-S45; the QIC academy only to press Rebellion's 3 QIC, which Itars
# values low: LF4-06, C027). When the best move builds the other kind, it swaps with the best move that does not.
ACADEMY_ONLY = {'Itars': 'Science'}


def academy_kind_scores(env, snapshot, scores):
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or 'ActionPhase' not in state['phase']:
        return scores
    player = state['players'][actor]
    allowed = ACADEMY_ONLY.get(player['faction'])
    if allowed is None or not _part(player, 'academy_kind'):
        return scores
    candidates = snapshot['candidates']

    def wrong(i):
        target = candidates[i]['action'].get('to') if candidates[i]['action'].get('type') == 'Upgrade' else None
        return isinstance(target, dict) and 'Academy' in target and target['Academy'] != allowed
    open_ = [i for i in range(len(candidates)) if not blocked(scores[i])]
    if not open_:
        return scores
    best = max(open_, key=lambda i: scores[i][0])
    others = [i for i in open_ if not wrong(i)]
    if not wrong(best) or not others:
        return scores
    lifted = list(scores)
    _swap(lifted, list(scores), max(others, key=lambda i: scores[i][0]), best,
          f'{player["faction"]} academy is {allowed} only (academy_kind)')
    return lifted


# building_due (SOURCE_FACTION_PARTS): from the due round, while the faction has no such building, an upgrade to
# it leads the other big-building upgrades (research lab, academy) — "2R 시작 때 의회가 없으면 대형건물 후보 중
# 의회를 맨 앞에" (conflicts/weak-factions.md). Firaks institute by round 2 (PG17-S16, BGGO1-S20, B19-S51,
# LF4-06), Itars by round 3 (B19-S62, B07-S21, PG23-S08, MISC1-S34). Mines, research and actions keep their
# place (order among upgrades only).
BUILDING_DUE = {'Firaks': ('PlanetaryInstitute', 2),
                'Itars': ('PlanetaryInstitute', 3),
                # resolved_parts: Bescods institute in round 3 (M3: PG13-S11, LF timings one round earlier).
                'Bescods': ('PlanetaryInstitute', 3)}
BIG_BUILDINGS = frozenset({'PlanetaryInstitute', 'ResearchLab', 'Academy'})


def _structure_kind(structure):
    kind = structure.get('kind')
    return next(iter(kind)) if isinstance(kind, dict) else kind


def building_due_scores(env, snapshot, scores):
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or 'ActionPhase' not in state['phase']:
        return scores
    player = state['players'][actor]
    due = BUILDING_DUE.get(player['faction'])
    if due is None or not _part(player, 'building_due') or state['round'] < due[1]:
        return scores
    building = due[0]
    if any(_structure_kind(s) == building for s in player['structures']):
        return scores
    candidates = snapshot['candidates']
    big = [i for i in range(len(candidates)) if not blocked(scores[i])
           and _upgrade_target(candidates[i]['action']) in BIG_BUILDINGS]
    lead = [i for i in big if _upgrade_target(candidates[i]['action']) == building]
    if not lead or len(big) < 2:
        return scores
    best = max(big, key=lambda i: scores[i][0])
    if best in lead:
        return scores
    lifted = list(scores)
    _swap(lifted, list(scores), max(lead, key=lambda i: scores[i][0]), best,
          f'{player["faction"]} {building} due by round {due[1]} (building_due)')
    return lifted


# opening_only: the round-1 openings a faction is held to. The BGG catalog rows are the targets the
# search compares and the forecast it keeps (preparation.choose → select_forecast picks the best
# completed forecast among them, so the guide order alone did not hold: 086 BalTaks 1RL, 0 academies).
# With the part on, the faction's catalog is cut to these labels (B11 "아카데미+광산 가장 좋음", BGG
# BalTaks rows 1 and 3). When no academy forecast completes, the teacher falls back to the search as before.
# weak_factions (conflicts/weak-factions.md, BGG part 2 games/average): HadschHallas drops every institute
# opening (110-127) and the lab with 2-3 mines (135) — lab with 4-5 mines (144, 157) or academy (145, 149);
# Itars drop the lab-only openings (116-153, all sources) — academy or institute (153-157, condition left to
# the search); Firaks keep the lab → institute → downgrade opening (1PI+1TS 160) and the lab + trading
# station fallback (147, 146; B09-S10, SH04-S39).
OPENING_ONLY = {'BalTaks': ('1AC+1M', '1AC+2M'),
                'HadschHallas': ('1AC+2M', '1RL+4M', '1AC+1M', '1RL+5M'),
                'Itars': ('1AC+1M', '1AC+2M', '1PI+2M', '1PI+1M'),
                'Firaks': ('1PI+1TS', '1RL+1TS+2M', '1RL+1TS+1M'),
                # source_parts (conflicts/base-factions.md): Ambas lab with 4-6 mines or academy, not lab + trading
                # station (A1: RL+5M 159, RL+6M 169, AC+2M 153 vs RL+TS+2M 142); Bescods lab with 4-5 mines or
                # 2 labs (M1: 145, 150, 145 vs RL+TS+2M 136); Gleens mines only or lab + 4 mines (G1: 6M 151,
                # 7M 158, RL+4M 147); Nevlas institute + lab, or + trading station (N2: 154, 168, PI+TS+2M 148);
                # Lantids institute with 3-6 mines (agreement: PI 142 vs 134, PI+4M 151, PI+5M 162).
                'Ambas': ('1RL+4M', '1AC+2M', '1RL+5M', '1RL+6M'),
                'Bescods': ('1RL+4M', '1RL+5M', '2RL+1M'),
                'Gleens': ('1RL+4M', '6M', '7M'),
                'Nevlas': ('1PI+1RL+1M', '1PI+1RL+2M', '1PI+1TS+2M'),
                'Lantids': ('1PI+3M', '1PI+4M', '1PI+5M', '1PI+6M')}


def install_opening_only():
    import bgg_openings.catalog as catalog
    import bgg_openings.planning as planning
    if getattr(catalog.load_catalog, '_opening_only', False):
        return
    inner = catalog.load_catalog

    def load_catalog(*args, **kwargs):
        rows = dict(inner(*args, **kwargs))
        for faction, labels in OPENING_ONLY.items():
            if faction in rows and _part({'faction': faction}, 'opening_only'):
                rows[faction] = tuple(r for r in rows[faction] if r.label in labels)
        return rows
    load_catalog._opening_only = True
    load_catalog.__wrapped__ = inner
    catalog.load_catalog = load_catalog
    planning.load_catalog = load_catalog


# fixed_academy: the frozen teacher's fixed-opening coach (bgg_openings.fixed.enforce — round 1 keeps only
# the moves that advance the most advanced site to the academy or fund it, then the second mine) for a
# faction with the part, in round 1 only. The 20 s search completes about one forecast a decision, so the
# academy forecast rarely completes and opening_only alone left BalTaks at the research lab (smoke
# 2026-10-19: forecasts completed 0–1 per decision, "local-baseline" picks, TS → RL → Gaia research).
# Science academy as for the other fixed factions (B11-03 "연구소→4지식"). The module dict is extended at
# run time; the frozen file is not edited, and its own fixed_openings switch stays off.
FIXED_ACADEMY = {'BalTaks': 'Science'}
# B2 (conflicts/base-factions.md; PG16-T26, PG02-S05, PG01-S12 "지식 AC 2개는 크레딧 고갈"; user: blog and podcast
# first): with the qic_academy part the fixed academy is the credit (QIC) one. The frozen coach reads the kind from
# its TARGETS at decision time and maps only 'Science' to the structure kind, so the entry is set before each
# enforce call and target_kind is wrapped; the frozen file is not edited.
QIC_ACADEMY = {'BalTaks': 'qic_academy'}
ACADEMY_KINDS = ('Science', 'Qic')


def academy_target(faction):
    """The fixed coach's target for `faction` now: the QIC academy with the part, else its TARGETS entry."""
    import bgg_openings.fixed as fixed
    part = QIC_ACADEMY.get(faction)
    if part and part in _faction_parts(faction):
        return 'Qic'
    return FIXED_ACADEMY.get(faction, fixed.TARGETS.get(faction))


def install_fixed_academy():
    import bgg_openings.fixed as fixed
    import four_factions.preparation as p
    for faction, kind in FIXED_ACADEMY.items():
        fixed.TARGETS.setdefault(faction, kind)
    if not getattr(fixed.target_kind, '_qic_academy', False):
        def target_kind(faction):
            target = academy_target(faction)
            return {'Academy': target} if target in ACADEMY_KINDS else target
        target_kind._qic_academy = True
        fixed.target_kind = target_kind
    inner_rank = p.Policies.rank
    if getattr(inner_rank, '_fixed_academy', False):
        return

    def rank(self, env, snapshot):
        scores = inner_rank(self, env, snapshot)
        actor = snapshot.get('player')
        state = snapshot['state']
        if actor is None or state['round'] != 1 or 'ActionPhase' not in state['phase']:
            return scores
        faction = state['players'][actor]['faction']
        if not _part(state['players'][actor], 'fixed_academy'):
            return scores
        fixed.TARGETS[faction] = academy_target(faction)
        scores, _ = fixed.enforce(env, snapshot, scores, self.memory)
        return scores
    for name, value in vars(inner_rank).items():
        if name.startswith('_') and isinstance(value, bool):
            setattr(rank, name, value)
    rank.__wrapped__ = getattr(inner_rank, '__wrapped__', inner_rank)
    rank._fixed_academy = True
    p.Policies.rank = rank


# tile_prefs (user 2026-10-20 "기존 자료에 있는 내용 쓸만하면 반영"): the standard tiles a faction guide asks
# for or avoids (engine ids: 2 ore+charge income, 3 four credits income, 4 ore+QIC now, 5 knowledge+credit
# income, 6 big buildings power 4, 7 VP now, 8 VP per Gaia mine, 9 knowledge per planet type, 10 charge-4
# action). Among the tile variants of one move, an avoided tile on top swaps with the best allowed one, and
# a preferred tile (in the guide's order) that is offered leads. Order only.
#   HadschHallas: avoid 3 (B17-01, H01, LF2-01 "4돈보다 1광석1충전"), prefer 2.  Bescods: avoid 3 (IR01-03),
#   prefer 6 (B13-04 "큰 건물 4티어 확보").  Ambas: avoid 2 (B6-01 "1광석 1충전을 제외한 … 모두 좋음").
#   BalTaks: prefer 3, 5, 10 (B11-03 "추천 기술 4돈·1지식1돈·4충전"), avoid 2.  Itars: prefer 6, 8, 4, 10, 7
#   (B7-01).  Ivits: prefer 10, then 4 or 9 (B12-01).  Lantids: prefer 3, avoid 10 (B16-01).
#   Geodens: prefer 10 in rounds 1-3, 9 from round 4 (B14-01).
# Scope (091: Itars −63.4 charges, 6/6 — the income tiles 2 and 5 never taken; HANDOFF E35): a guide names
# the tiles for one way of taking them. Itars' list is "의회로 가져갈 기술" (B7-01) — the institute's Gaia-phase
# tile (ItarsGaiaTechTile), so 'only': 'ability'; Bescods' big-building tile comes with the institute or
# academy after two labs (B13-04 "연구소 2개 → 행성 의회와 지식 아카데미(4티어 기술)"), so 'only': 'big' (an
# upgrade to the institute or an academy). The lab and academy tiles of those two factions stay the search's.
TILE_PREFS = {
    'HadschHallas': {'prefer': (2,), 'avoid': (3,)},
    'Bescods': {'prefer': (6,), 'avoid': (3,), 'only': 'big'},
    'Ambas': {'prefer': (), 'avoid': (2,)},
    'BalTaks': {'prefer': (3, 5, 10), 'avoid': (2,)},
    'Itars': {'prefer': (6, 8, 4, 10, 7), 'avoid': (), 'only': 'ability'},
    'Ivits': {'prefer': (10, 4, 9), 'avoid': ()},
    'Lantids': {'prefer': (3,), 'avoid': (10,)},
    'Geodens': {'prefer': (10,), 'avoid': (), 'late_prefer': (9,), 'late_from': 4},
    # Taklons (E97 (ㄱ), E103 ②b): the charge-4 tile first (paia-timing-rules R3, PG02-S40), but not when it lies
    # under Gaia (B19-S46, K2 base-factions.md:83) — then the knowledge + credit income tile (K2).
    'Taklons': {'prefer': (10, 5), 'avoid': (), 'not_under_gaia': (10,)},
    # Nevlas (E103 ④, B19-S60 "타클론처럼 4충전이 가이아 밑이면 안 집는 게 나음"): only the Gaia-column exception.
    # SH11 p.32-33 / SH04 Nevlas "첫 타일은 4파워 회전": power factions take the charge-4 tile first.
    'Nevlas': {'prefer': (10,), 'avoid': (), 'not_under_gaia': (10,)},
}
AI_SLOT = 2        # advanced_tech_tiles / tech_tile_slots index of the AI column
GAIA_SLOT = 3      # tech_tile_slots: the six track columns in ResearchTrack order (TF, Nav, AI, Gaia, Eco, Sci), then 3


def _tile_choice(action, scope=None):
    """(variant group key, standard tile id) when `action` takes a standard tile inside `scope` — None:
    any lab / academy / institute tile choice; 'big': an upgrade to the institute or an academy;
    'ability': the Itars institute's Gaia-phase tile (ItarsGaiaTechTile) — else None."""
    if scope == 'ability':
        if action.get('type') != 'ItarsGaiaTechTile':
            return None
        return json.dumps({k: v for k, v in action.items() if k != 'tile'}, sort_keys=True), action.get('tile')
    choice = action.get('tech_tile_choice')
    if not isinstance(choice, dict) or choice.get('kind') != 'Standard':
        return None
    if scope == 'big':
        to = action.get('to')
        if action.get('type') != 'Upgrade' or not (to == 'PlanetaryInstitute' or isinstance(to, dict) and 'Academy' in to):
            return None
    return json.dumps({k: v for k, v in action.items() if k != 'tech_tile_choice'}, sort_keys=True), choice.get('tile')


def tile_prefs_scores(env, snapshot, scores):
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or 'ActionPhase' not in state['phase']:
        return scores
    player = state['players'][actor]
    prefs = TILE_PREFS.get(player['faction'])
    if prefs is None or not _part(player, 'tile_prefs'):
        return scores
    prefer, avoid = prefs['prefer'], prefs['avoid']
    if prefs.get('late_from') and state['round'] >= prefs['late_from']:
        prefer = prefs['late_prefer']
    # A tile the guide wants only off the Gaia column (Taklons K2): there it is avoided and the next preference leads.
    slots = (state.get('research_board') or {}).get('tech_tile_slots') or ()
    on_gaia = slots[GAIA_SLOT] if len(slots) > GAIA_SLOT else None
    if on_gaia is not None and on_gaia in prefs.get('not_under_gaia', ()):
        prefer = tuple(t for t in prefer if t != on_gaia)
        avoid = (*avoid, on_gaia)
    candidates = snapshot['candidates']
    groups, tiles = {}, {}
    for i, c in enumerate(candidates):
        found = None if blocked(scores[i]) else _tile_choice(c['action'], prefs.get('only'))
        if found is None:
            continue
        key, tiles[i] = found
        groups.setdefault(key, []).append(i)
    lifted = list(scores)
    tile = tiles.get
    for members in groups.values():
        if len({tile(i) for i in members}) < 2:
            continue
        top = max(members, key=lambda i: lifted[i][0])
        wanted = next(([i for i in members if tile(i) == t] for t in prefer if any(tile(i) == t for i in members)), [])
        if wanted and top not in wanted:
            _swap(lifted, list(lifted), max(wanted, key=lambda i: lifted[i][0]), top,
                  f'{player["faction"]} guide tile {tile(wanted[0])} (tile_prefs)')
            continue
        if tile(top) in avoid:
            allowed = [i for i in members if tile(i) not in avoid]
            if allowed:
                _swap(lifted, list(lifted), max(allowed, key=lambda i: lifted[i][0]), top,
                      f'{player["faction"]} avoids tile {tile(top)} (tile_prefs)')
    return lifted if lifted != scores else scores


# niche_tracks: a track the others leave alone (user 2026-10-20 "하드쉬나 제노스 자료중에 남들이 안가는 테크 가라는
# 내용"). HadschHallas (B19-03 "남들이 안 가는 테크(가이아·테라포밍·QIC 액션)를 찾음"): once Economy 2 or Navigation 2
# is reached, among the research moves the one on Gaia, Terraforming or AI with the lowest sum of the
# opponents' levels leads. Xenos (B15-02 "가이아 특화 종족이 없으면 가이아 트랙을 가장 추천 … 항해 1+가이아 2"): with
# no Gaia faction among the opponents (Terrans, Itars, BalTaks, Gleens — bot's reading, not in the guide),
# the Gaia advance leads the research moves in rounds 1-3 until Gaia 2. Order only.
NICHE_TRACKS = {'HadschHallas': ('GaiaProject', 'Terraforming', 'ArtificialIntelligence')}
GAIA_FACTIONS = frozenset({'Terrans', 'Itars', 'BalTaks', 'Gleens'})
XENOS_GAIA_LEVEL = 2
XENOS_GAIA_LAST_ROUND = 3


def niche_tracks_scores(env, snapshot, scores):
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or 'ActionPhase' not in state['phase']:
        return scores
    player = state['players'][actor]
    if not _part(player, 'niche_tracks'):
        return scores
    candidates = snapshot['candidates']
    research = [i for i, c in enumerate(candidates)
                if c['action'].get('type') == 'ResearchAdvance' and not blocked(scores[i])]
    if len(research) < 2:
        return scores
    levels = player['research_tracks']
    others = [p for i, p in enumerate(state['players']) if i != actor]
    lead, why = [], ''
    if player['faction'] == 'HadschHallas' and (levels['economy'] >= 2 or levels['navigation'] >= 2):
        niche = [i for i in research if candidates[i]['action'].get('track') in NICHE_TRACKS['HadschHallas']]
        if niche:
            crowd = lambda i: sum(p['research_tracks'][TRACK_KEYS[candidates[i]['action']['track']]] for p in others)
            least = min(crowd(i) for i in niche)
            lead, why = [i for i in niche if crowd(i) == least], 'HadschHallas track the others leave (niche_tracks)'
    elif (player['faction'] == 'Xenos' and state['round'] <= XENOS_GAIA_LAST_ROUND
          and levels['gaia'] < XENOS_GAIA_LEVEL and not any(p['faction'] in GAIA_FACTIONS for p in others)):
        lead = [i for i in research if candidates[i]['action'].get('track') == 'GaiaProject']
        why = 'Xenos Gaia with no Gaia faction in the game (niche_tracks)'
    if not lead:
        return scores
    best = max(research, key=lambda i: scores[i][0])
    if best in lead:
        return scores
    lifted = list(scores)
    _swap(lifted, list(scores), max(lead, key=lambda i: scores[i][0]), best, why)
    return lifted


def guide_r1_charge3_lf_more_vm_lf_ts_ships_byfaction_guide(seed, **kwargs):
    """Teacher factory: ..._ships_byfaction plus GUIDE_FACTION_PARTS — track_steps, track_caps and
    building_limits from the faction guides, and track_set for the Lost Fleet factions (user 2026-10-19
    "반영 안된거부터 처리해야지"). track_steps runs after track_set, so a round target wins over the priority."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts_ships_byfaction(seed, **kwargs)
    _guide['faction_guide'] = True
    _wrap_rank('_track_steps', track_steps_scores)
    _wrap_rank('_building_limits', building_limits_scores)
    install_opening_only()
    install_fixed_academy()
    _wrap_rank('_tile_prefs', tile_prefs_scores)
    _wrap_rank('_niche_tracks', niche_tracks_scores)
    return teacher


def guide_r1_charge3_lf_more_vm_lf_ts_ships_byfaction_guide_weak(seed, **kwargs):
    """Teacher factory: ..._ships_byfaction_guide plus WEAK_FACTION_PARTS — the round-1 openings of
    HadschHallas, Itars and Firaks and HadschHallas' no institute before round 3 (088's lowest charges)."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts_ships_byfaction_guide(seed, **kwargs)
    _guide['weak_factions'] = True
    return teacher


def guide_r1_charge3_lf_more_vm_lf_ts_ships_byfaction_guide_src(seed, **kwargs):
    """Teacher factory: ..._ships_byfaction_guide plus SOURCE_FACTION_PARTS — the openings, PG track orders and
    institute due rounds resolved in research/strategy/conflicts/ for Ambas, Bescods, Gleens, Nevlas, Lantids,
    Ivits, Firaks and Itars."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts_ships_byfaction_guide(seed, **kwargs)
    _guide['source_parts'] = True
    _wrap_rank('_building_due', building_due_scores)
    return teacher


def guide_r1_charge3_lf_more_vm_lf_ts_ships_byfaction_guide_srctracks(seed, **kwargs):
    """Teacher factory: ..._ships_byfaction_guide plus the track_steps_src entries of SOURCE_FACTION_PARTS only
    (Nevlas Science 3, Lantids Economy 2, Ivits Science 2 in round 1) — 093's opening lists and building_due
    left off, so the PG track order is measured alone (E59 (ㄱ))."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts_ships_byfaction_guide(seed, **kwargs)
    _guide['source_tracks'] = True
    return teacher


def guide_r1_charge3_lf_more_vm_lf_ts_ships_byfaction_guide_res(seed, **kwargs):
    """Teacher factory: ..._ships_byfaction_guide_src plus RESOLVED_FACTION_PARTS — the conflicts re-judged by the
    user's source priority: Terrans, Taklons and Darkanians opening order (opening_res), Nevlas and Ivits Economy
    or Science first by condition (science_when)."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts_ships_byfaction_guide_src(seed, **kwargs)
    _guide['resolved_parts'] = True
    # Third batch: Itars academy kind, HadschHallas token parts. fed_remember_scores last so replay_first_goal sees
    # the final ranking.
    _wrap_rank('_academy_kind', academy_kind_scores)
    _wrap_rank('_fed_token', fed_token_scores)
    install_replay_first()
    _wrap_rank('_fed_remember', fed_remember_scores)
    return teacher


# ── federations (user 2026-10-19 "연방을 왜 먹지 않지? … 파워 토큰을 너무 많이 쓰는거 아냐?", "그렇게 해") ──────
# 084 (tools/federation_chances.py): a federation was legal 3-8 times a seat-game but 0.7-2.0 were formed,
# 28 passes with one legal (5 in round 6); in the replay of pair-001/game-0-A23 step 241 every federation
# scored -16 in the one-step ranking against Pass 0 and none reached the 4 compared plans. And the cheapest
# legal federation usually needed 6-11 satellites, formed ones 3.4-5.9 — the buildings are spread. Guides:
# 0-2 satellites with adjacent buildings (B15-01, B13-04, PG15-T12), at least 3 federations (C001).
#
# fed_compare: when a federation is legal, the best-ranked one (fewest satellites on a tie) is compared
# first after the current choice, so the rollout to the horizon — not the one-step preview — judges it.
# Order and scope only. fed_cluster: in rounds 1-5, each legal mine is scored by how it changes the
# satellites needed to link all our buildings outside a federation (_link_costs: 0 = adjacent, 1 = one
# satellite, negative = it bridges two groups, user 2026-10-20 "원래 3칸 돌아가야 했던 건물이 … 더 적은
# 칸으로 줄어드는 경우"); when the best mine changes it more than the best-linking mine (and that one adds at
# most one satellite), the two swap scores. Order only. (084 step 129: the teacher built at distance 3
# while 0,-4 joined with one satellite.)
FED_CLUSTER_LAST_ROUND = 5
FED_CLUSTER_MAX_DELTA = 1   # a mine "links" when it adds at most one satellite to linking our buildings
_fed_scores = {}   # id(snapshot) -> its root ranking, for goals_for (the last one only)


def _hex_distance(a, b):
    (q1, r1), (q2, r2) = (tuple(int(x) for x in str(c).split(',')) for c in (a, b))
    return (abs(q1-q2) + abs(r1-r2) + abs(q1+r1-q2-r2)) // 2


def _hex_neighbors(coord):
    q, r = (int(x) for x in str(coord).split(','))
    return [f'{q+dq},{r+dr}' for dq, dr in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1))]


def fed_remember_scores(env, snapshot, scores):
    _fed_scores.clear()
    _fed_scores[id(snapshot)] = scores
    return scores


def fed_compare_goal(snapshot, part=True):
    """Goal comparing the best legal federation, or None (no federation, part off, no ranking).
    part=False (plan_menu): no part check."""
    from current_actions.conservation import blocked
    from four_factions.preparation import Goal
    actor = snapshot.get('player')
    if actor is None or (part and not _part(snapshot['state']['players'][actor], 'fed_compare')):
        return None
    scores = _fed_scores.get(id(snapshot))
    if scores is None or len(scores) != len(snapshot['candidates']):
        return None
    feds = [i for i, c in enumerate(snapshot['candidates'])
            if c['action'].get('type') == 'FormFederation' and not blocked(scores[i])]
    if not feds:
        return None
    best = max(feds, key=lambda i: (scores[i][0], -len(snapshot['candidates'][i]['action'].get('satellite_hexes', []))))
    # Family 'root': not remembered as a multi-step plan (preparation.search keeps other families).
    return Goal(f'federation-{best}', 'root', first=best)


def install_fed_compare():
    import four_factions.preparation as p
    if getattr(p.goals_for, '_fed_compare', False):
        return
    inner = p.goals_for

    def goals_for(snapshot, **kwargs):
        goals = inner(snapshot, **kwargs)
        goal = fed_compare_goal(snapshot)
        return [goal, *goals] if goal is not None else goals
    goals_for._fed_compare = True
    goals_for.__wrapped__ = inner
    p.goals_for = goals_for


def fed_cluster_scores(env, snapshot, scores):
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or 'ActionPhase' not in state['phase'] or state['round'] > FED_CLUSTER_LAST_ROUND:
        return scores
    player = state['players'][actor]
    if not _part(player, 'fed_cluster'):
        return scores
    # Federation rules (rulebook p.14; engine validate_federation / apply_build): a mine next to one of
    # our federations joins it, and a new federation may not touch an existing one. So a hex next to a
    # federation (satellites included) is no seed for a new one, neither as a mine nor as a neighbour.
    federated = {str(h) for h in player.get('federated_hexes', [])}
    touching = federated | {n for h in federated for n in _hex_neighbors(h)}
    own = [str(s['hex']) for s in player['structures'] if str(s['hex']) not in touching]
    if not own:
        return scores
    candidates = snapshot['candidates']
    builds = [i for i, c in enumerate(candidates)
              if c['action'].get('type') == 'Build' and c['action'].get('coord') is not None and not blocked(scores[i])]
    if len(builds) < 2:
        return scores
    link = _link_costs(state, own, touching)
    delta = {i: link(str(candidates[i]['action']['coord'])) for i in builds}
    best = max(builds, key=lambda i: scores[i][0])
    lead = min(delta.values())
    # A mine that joins with at most one satellite or shortens the links counts; farther does not.
    if lead > FED_CLUSTER_MAX_DELTA or delta[best] <= lead:
        return scores
    near = [i for i in builds if delta[i] == lead]
    lifted = list(scores)
    _swap(lifted, list(scores), max(near, key=lambda i: scores[i][0]), best,
          f'mine that links our buildings for a federation, satellites {lead:+d} (fed_cluster)')
    return lifted


def _link_costs(state, own, touching):
    """Function coord -> change in the satellites needed to link all our free buildings if a mine
    stands on coord (negative: it bridges two groups; 9: it cannot be linked or touches a federation).

    Facts only (rulebook p.14, engine validate_satellite_hex): our free buildings are 0-cost nodes,
    adjacent ones form one group; an empty space (no planet, building or spaceship tile, not next to
    one of our federations) takes a satellite (cost 1); anything else blocks. The cost of linking the
    groups is a minimum spanning tree over group-to-group shortest paths (0-1 BFS)."""
    hexes = state['board']['hexes']
    ship_tiles = {str(c) for c in (state['board'].get('spaceship_tiles') or {}).values()}
    seeds = set(own)

    def satellite_room(coord):
        cell = hexes.get(coord)
        return (cell is not None and not cell.get('planet') and not cell.get('structures')
                and coord not in ship_tiles and coord not in touching)

    groups = []
    for h in own:
        if any(h in g for g in groups):
            continue
        group, stack = {h}, [h]
        while stack:
            for n in _hex_neighbors(stack.pop()):
                if n in seeds and n not in group:
                    group.add(n)
                    stack.append(n)
        groups.append(group)

    def bfs(sources):
        from collections import deque
        dist = {h: 0 for h in sources}
        queue = deque(sources)
        while queue:
            h = queue.popleft()
            for n in _hex_neighbors(h):
                step = 0 if n in seeds else 1 if satellite_room(n) else None
                if step is None or dist.get(n, 99) <= dist[h] + step:
                    continue
                dist[n] = dist[h] + step
                (queue.appendleft if step == 0 else queue.append)(n)
        return dist
    reach = [bfs(g) for g in groups]
    pair = {(a, b): min((reach[a].get(h, 99) for h in groups[b]), default=99)
            for a in range(len(groups)) for b in range(len(groups)) if a < b}

    def tree(nodes, cost):
        """Minimum spanning forest weight over `nodes` with edge costs `cost(a, b)` (99 = no link)."""
        parent = {n: n for n in nodes}

        def root(n):
            while parent[n] != n:
                parent[n] = parent[parent[n]]
                n = parent[n]
            return n
        total = 0
        edges = [(cost(a, b), a, b) for a in nodes for b in nodes if str(a) < str(b)]
        for c, a, b in sorted(edges, key=lambda e: (e[0], str(e[1]), str(e[2]))):
            if c >= 99:
                break
            ra, rb = root(a), root(b)
            if ra != rb:
                parent[ra] = rb
                total += c
        return total
    base = tree(range(len(groups)), lambda a, b: pair[(min(a, b), max(a, b))])

    def change(coord):
        if coord in touching:
            return 9
        # The mine is a 0-cost node; its link to a group is the cheapest neighbour of it.
        to_group = [min(((reach[k].get(n, 99) if n in seeds or satellite_room(n) else 99)
                         for n in _hex_neighbors(coord)), default=99) for k in range(len(groups))]
        if min(to_group, default=99) >= 99:
            return 9
        nodes = [*range(len(groups)), 'mine']

        def cost(a, b):
            if 'mine' in (a, b):
                return to_group[b if a == 'mine' else a]
            return pair[(min(a, b), max(a, b))]
        return tree(nodes, cost) - base
    return change


FED_PARTS = frozenset({'fed_compare', 'fed_cluster'})


# ── green tokens and track races (user 2026-10-20 "잘 풀리면 다 쓰는거고 누가 5단계를 뺏었고 … 못 돌린거지",
# "트랙 경쟁과 관련된 부품이 존재하나?", "내가 상대방에게 밀리는 것을 미리 인지하면 그걸 먹기 위해 하는 수들을 다른 곳에
# 투자할 수 잇지 않았을까?", "그렇게 해") ────────────────────────────────────────────────────────────
# 060–084: 0.45 green tokens a seat stayed unflipped, 0.40 of them while a free level 5 or an Advanced tile
# above a level-4+ track remained (endgame_tech_counts 'missed'). No part looked at the race.
# token_compare: with a green token, the best legal move that flips it (a level-5 advance, an upgrade
#   taking an Advanced tile) is compared first, judged by the rollout. Scope only.
# track_race: when an opponent is also at level 4 on a track with a green token, our level-5 advance there
#   leads the research moves, and among one upgrade's tile choices the Advanced tile above that track leads.
#   Order only.
# race_prune: a research goal to level 5 or an Advanced-tile goal on a track already lost — level 5 taken,
#   or an opponent at 4 with a green token while we are at 3 or below — leaves the compared goals, so the
#   comparisons go elsewhere. Scope only.
TOKEN_PARTS = frozenset({'token_compare', 'track_race', 'race_prune'})


def _green(player):
    return bool(player.get('federation_tokens'))


LEVEL5_KNOWLEDGE = 4                       # rulebook research cost
SCIENCE_INCOME = (0, 1, 2, 3, 4, 0)        # knowledge a round by Science level (rulebook p.22)
UPGRADE_TO_TECH = (('TradingStation', 3, 5), ('ResearchLab', 6, 6))   # -> lab / academy (ore, credits)
TWILIGHT = 0                 # ship id in explored_ships (engine spaceship_id_to_ship_id)
TWILIGHT_LAB_ORE = 2         # engine TWILIGHT_RESEARCH_LAB_ORE_COST
ITARS_TILE_TOKENS = 4        # Itars institute: 4 Gaia-area tokens for a tech tile


def _rival_ready(player, path):
    """Whether a rival can pay the step soon (user 2026-10-20 "상대방의 자원도 카운팅해야하지 않을까? 아니면
    앞으로 자원을 먹을 수 있는지"): 'level5' — 4 knowledge now or after the next Science income;
    'advanced' — a lab or academy upgrade it can pay now (a tile comes with the upgrade)."""
    res = player.get('resources') or {}
    if path == 'level5':
        knowledge = res.get('knowledge', 0)
        return knowledge + SCIENCE_INCOME[player['research_tracks'].get('science', 0)] >= LEVEL5_KNOWLEDGE
    # Every way an Advanced tile comes (engine valid_tech_tile_choices callers; user 2026-10-20 "고급 기술의 경로는
    # 건물 건설만 있는 것이 아니야"): a lab or academy upgrade, Twilight's free lab (2 ore, a trading station,
    # Twilight explored), the Itars' Gaia-phase tile (institute + 4 tokens in the Gaia area), the Space Giants'
    # institute tile (once). Rebellion's tile action and the federation tile token give Standard tiles only.
    kinds = {s['kind'] for s in player.get('structures', []) if isinstance(s.get('kind'), str)}
    ore, credits = res.get('ore', 0), res.get('credits', 0)
    if any(kind in kinds and ore >= o and credits >= c for kind, o, c in UPGRADE_TO_TECH):
        return True
    if 'TradingStation' in kinds and TWILIGHT in player.get('explored_ships', []) and ore >= TWILIGHT_LAB_ORE:
        return True
    faction = player.get('faction')
    gaia_area = (res.get('power') or {}).get('gaia_forming', 0)
    if faction == 'Itars' and 'PlanetaryInstitute' in kinds and gaia_area >= ITARS_TILE_TOKENS:
        return True
    if faction == 'SpaceGiants' and not player.get('pi_ability_used'):
        return 'PlanetaryInstitute' in kinds or ('TradingStation' in kinds and ore >= 4 and credits >= 6)
    return False


def _race(state, actor, track, path='level5'):
    """'lost', 'contested' or None for our level 5 (path 'level5') or the Advanced tile (path 'advanced')
    on `track` (TRACK_KEYS name). A rival counts when it is at level 4+, holds a green token and can pay
    the step soon; level 5 already taken is lost for both paths' level-5 goals."""
    key = TRACK_KEYS[track]
    me = state['players'][actor]
    others = [p for i, p in enumerate(state['players']) if i != actor]
    if path == 'level5' and any(p['research_tracks'][key] >= 5 for p in others):
        return 'lost'
    rivals = [p for p in others if p['research_tracks'][key] >= 4 and _green(p) and _rival_ready(p, path)]
    if not rivals:
        return None
    return 'lost' if me['research_tracks'][key] <= 3 else 'contested'


# Economy and Science level 5 replace the level-4 income with a one-time gain (rulebook p.22): Economy
# 3 ore 6 credits charge 6 against 2 ore 4 credits charge 4 a round (1.5 rounds), Science 9 knowledge
# against 4 a round (2.25 rounds). The step pays only when no more income phases are left than that:
# Economy from round 5, Science from round 4 (user 2026-10-20 "경제나 과학 5단계 올라가면 기존 수입을 못받는데").
LEVEL5_INCOME_ROUNDS = {'Economy': 1.5, 'Science': 2.25}
LAST_ROUND = 6


def _level5_pays(state, track):
    rounds = LEVEL5_INCOME_ROUNDS.get(track)
    return rounds is None or LAST_ROUND - state['round'] <= rounds


def _flips_token(state, actor, action):
    if action.get('type') == 'ResearchAdvance':
        key = TRACK_KEYS.get(action.get('track'))
        return (key is not None and state['players'][actor]['research_tracks'][key] == 4
                and _level5_pays(state, action['track']))
    choice = action.get('tech_tile_choice') or {}
    return choice.get('kind') in ('Advanced', 'LostFleetAdvanced')


def token_compare_goal(snapshot, part=True):
    """Goal comparing the best legal token flip, or None. part=False (plan_menu): no part check."""
    from current_actions.conservation import blocked
    from four_factions.preparation import Goal
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or (part and not _part(state['players'][actor], 'token_compare')) or not _green(state['players'][actor]):
        return None
    scores = _fed_scores.get(id(snapshot))
    if scores is None or len(scores) != len(snapshot['candidates']):
        return None
    flips = [i for i, c in enumerate(snapshot['candidates'])
             if not blocked(scores[i]) and _flips_token(state, actor, c['action'])]
    if not flips:
        return None
    best = max(flips, key=lambda i: scores[i][0])
    return Goal(f'flip-{best}', 'root', first=best)


def race_prune_goals(snapshot, goals):
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or not _part(state['players'][actor], 'race_prune'):
        return goals
    kept = []
    for goal in goals:
        family, target = getattr(goal, 'family', None), getattr(goal, 'target', None)
        lost = target in TRACK_KEYS and (
            (family == 'research' and goal.level >= 5 and _race(state, actor, target, 'level5') == 'lost')
            or (family == 'advanced' and _race(state, actor, target, 'advanced') == 'lost'))
        if not lost:
            kept.append(goal)
    return kept


def install_token_goals():
    import four_factions.preparation as p
    if getattr(p.goals_for, '_token_goals', False):
        return
    inner = p.goals_for

    def goals_for(snapshot, **kwargs):
        goals = race_prune_goals(snapshot, inner(snapshot, **kwargs))
        goal = token_compare_goal(snapshot)
        return [goal, *goals] if goal is not None else goals
    goals_for._token_goals = True
    for name, value in vars(inner).items():
        if name.startswith('_') and isinstance(value, bool):
            setattr(goals_for, name, value)
    goals_for.__wrapped__ = getattr(inner, '__wrapped__', inner)
    p.goals_for = goals_for


# HadschHallas federation tokens (weak-factions.md 5: PG19-S28·S29·S42, B17-S03, H04, PG01-S18; user 2026-10-20
# "넘어가"): the first federation takes the 6-credit token (engine id 5, Vp7PlusCredits6 — the institute turns
# credits into resources), and once the institute stands, replaying a token (Lost Fleet: Twilight's 3-QIC "score a
# federation token again", the base game's QIC action the sources mean) is compared first whenever it is legal —
# the rollout decides, as fed_compare does. The "ore token without an institute plan" branch (PG19-S42) is not
# modelled: the guide plans the institute for rounds 3-4. Order and scope only.
HH_FIRST_TOKEN = 5
TWILIGHT_REPLAY = 'TwilightReplayFederationToken'


def _has_federation(player):
    return bool(player.get('federation_tokens') or player.get('gray_federation_tokens'))


def fed_token_scores(env, snapshot, scores):
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or 'ActionPhase' not in state['phase']:
        return scores
    player = state['players'][actor]
    if not _part(player, 'fed_token_credits') or _has_federation(player):
        return scores
    candidates = snapshot['candidates']
    groups = {}
    for i, c in enumerate(candidates):
        action = c['action']
        if action.get('type') == 'FormFederation' and not blocked(scores[i]):
            groups.setdefault(json.dumps([action.get('hexes'), action.get('satellite_hexes')]), []).append(i)
    lifted = list(scores)
    for members in groups.values():
        credits = [i for i in members if (candidates[i]['action'].get('token') or {}).get('kind') == HH_FIRST_TOKEN]
        if not credits or len(members) < 2:
            continue
        top = max(members, key=lambda i: scores[i][0])
        if top not in credits:
            _swap(lifted, list(scores), max(credits, key=lambda i: scores[i][0]), top,
                  f'{player["faction"]} first federation takes the 6-credit token (fed_token_credits)')
    return lifted


def replay_first_goal(snapshot):
    """Goal comparing the best legal token replay once the institute stands, or None."""
    from current_actions.conservation import blocked
    from four_factions.preparation import Goal
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None:
        return None
    player = state['players'][actor]
    if not _part(player, 'replay_first') or not any(s['kind'] == 'PlanetaryInstitute' for s in player['structures']):
        return None
    scores = _fed_scores.get(id(snapshot))
    if scores is None or len(scores) != len(snapshot['candidates']):
        return None
    replays = [i for i, c in enumerate(snapshot['candidates'])
               if c['action'].get('type') == TWILIGHT_REPLAY and not blocked(scores[i])]
    if not replays:
        return None
    best = max(replays, key=lambda i: scores[i][0])
    return Goal(f'replay-{best}', 'root', first=best)


def install_replay_first():
    import four_factions.preparation as p
    if getattr(p.goals_for, '_replay_first', False):
        return
    inner = p.goals_for

    def goals_for(snapshot, **kwargs):
        goals = inner(snapshot, **kwargs)
        goal = replay_first_goal(snapshot)
        return [goal, *goals] if goal is not None else goals
    goals_for._replay_first = True
    for name, value in vars(inner).items():
        if name.startswith('_') and isinstance(value, bool):
            setattr(goals_for, name, value)
    goals_for.__wrapped__ = getattr(inner, '__wrapped__', inner)
    p.goals_for = goals_for


def track_race_scores(env, snapshot, scores):
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or 'ActionPhase' not in state['phase']:
        return scores
    player = state['players'][actor]
    if not _part(player, 'track_race') or not _green(player):
        return scores
    candidates = snapshot['candidates']
    act = {i: c['action'] for i, c in enumerate(candidates) if not blocked(scores[i])}
    lifted = list(scores)
    research = [i for i in act if act[i].get('type') == 'ResearchAdvance']
    race5 = [i for i in research if act[i].get('track') in TRACK_KEYS
             and player['research_tracks'][TRACK_KEYS[act[i]['track']]] == 4
             and _level5_pays(state, act[i]['track'])
             and _race(state, actor, act[i]['track']) == 'contested']
    if race5 and research:
        best = max(research, key=lambda i: lifted[i][0])
        if best not in race5:
            _swap(lifted, list(lifted), max(race5, key=lambda i: lifted[i][0]), best,
                  'level 5 before a rival with a green token (track_race)')
    groups = {}
    for i in act:
        choice = act[i].get('tech_tile_choice')
        if act[i].get('type') == 'Upgrade' and isinstance(choice, dict):
            groups.setdefault(json.dumps({k: v for k, v in act[i].items() if k != 'tech_tile_choice'},
                                         sort_keys=True), []).append(i)
    for members in groups.values():
        contested = [i for i in members if act[i]['tech_tile_choice'].get('kind') == 'Advanced'
                     and act[i]['tech_tile_choice'].get('track') in TRACK_KEYS
                     and _race(state, actor, act[i]['tech_tile_choice']['track'], 'advanced') == 'contested']
        if not contested or len(members) < 2:
            continue
        top = max(members, key=lambda i: lifted[i][0])
        if top not in contested:
            _swap(lifted, list(lifted), max(contested, key=lambda i: lifted[i][0]), top,
                  'Advanced tile before a rival with a green token (track_race)')
    return lifted


def guide_r1_charge3_lf_more_vm_lf_ts_ships_tokens(seed, **kwargs):
    """Teacher factory: ..._ships (the base stack) plus token_compare, track_race and race_prune for every
    faction (above). The root ranking is kept for goals_for by fed_remember_scores, installed last."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts_ships(seed, **kwargs)
    _guide['tokens'] = True
    _wrap_rank('_track_race', track_race_scores)
    install_token_goals()
    _wrap_rank('_fed_remember', fed_remember_scores)
    return teacher


def guide_r1_charge3_lf_more_vm_lf_ts_ships_fed(seed, **kwargs):
    """Teacher factory: ..._ships (the base stack) plus fed_compare and fed_cluster for every faction
    (above). fed_remember_scores is installed last so it keeps the final root ranking."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts_ships(seed, **kwargs)
    _guide['fed'] = True
    _wrap_rank('_fed_cluster', fed_cluster_scores)
    install_fed_compare()
    _wrap_rank('_fed_remember', fed_remember_scores)
    return teacher


# ── ship_adjacent_mine ─────────────────────────────────────────────────────────────────
# User (2026-10-20 "함선에 들어가기 위해 qic를 썼는데 함선 바로 인접한 곳에 모행성/1테라포밍 행성이 있는 경우
# 그냥 함선 들어가나?" → "진행해"): a spaceship is explored, not colonized — later range is measured
# from the nearest colonized planet, never from the ship (expansion rulebook p.9) — so the QIC spent to
# reach a ship leaves no footprint. When a plain entry would pay range QIC and a mine on a home or
# one-step planet next to the ship tile is legal for no more QIC, the best such mine is ranked above the
# entry: from that mine the ship is in base range next turn and the QIC (or the footprint) stays.
# Order only; the comparison decides. Gaia (1 QIC), Asteroid (a former) and Transdim planets do not count.
def _ring_steps(home, planet):
    """Terraforming steps from `home` to `planet` for ring planets, None otherwise."""
    from economy.teacher import RING
    if home not in RING or planet.get('planet_type') not in RING:
        return None
    gap = abs(RING.index(home) - RING.index(planet['planet_type']))
    return min(gap, 7 - gap)


def ship_adjacent_mine_scores(env, snapshot, scores):
    from current_actions.conservation import blocked
    from economy.teacher import range_qic
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or 'ActionPhase' not in state['phase']:
        return scores
    player = state['players'][actor]
    if not (_guide['ship_adjacent_mine'] or _part(player, 'ship_adjacent_mine')):
        return scores
    candidates = snapshot['candidates']
    tiles = state['board']['spaceship_tiles']
    entries = [(range_qic(state, player, tiles[c['action']['ship']]), i) for i, c in enumerate(candidates)
               if c['action'].get('type') == 'ExploreSpaceship' and c['action'].get('ship') in tiles
               and not blocked(scores[i])]
    entries = [(qic, i) for qic, i in entries if qic > 0]
    if not entries:
        return scores
    entry_qic, entry = max(entries, key=lambda pair: scores[pair[1]][0])
    ship = candidates[entry]['action']['ship']
    ship_coord = tiles[ship]
    home = _home_type(player)
    mines = []
    for i, c in enumerate(candidates):
        action = c['action']
        coord = action.get('coord')
        if action.get('type') != 'Build' or coord is None or blocked(scores[i]):
            continue
        if _value.distance(coord, ship_coord) != 1:
            continue
        planet = (state['board']['hexes'].get(coord) or {}).get('planet')
        if not planet or planet.get('is_gaia_formed'):
            continue
        steps = _ring_steps(home, planet)
        if steps is None or steps > 1 or range_qic(state, player, coord) > entry_qic:
            continue
        mines.append(i)
    if not mines:
        return scores
    best = max(mines, key=lambda i: scores[i][0])
    if scores[best][0] >= scores[entry][0]:
        return scores
    lifted = list(scores)
    if _part(player, 'mj01'):
        # E61 (ㄱ), ships_menu1_all: 095's swap handed the entry the mine's low score and pushed it out of the four
        # comparisons (explain: excluded, not reordered). Here the entry keeps its score and the mine is lifted right
        # under it, so both are compared and the rollout decides.
        lifted[best] = (scores[entry][0] - SHIP_MINE_EPSILON,
                        f'{scores[best][1]}; mine next to the {ship} tile compared with the entry (ship_adjacent_mine)',
                        *scores[best][2:])
        return lifted
    _swap(lifted, list(scores), best, entry,
          f'mine next to the {ship} tile before the entry that pays {entry_qic} QIC for range; '
          f'the ship is in base range from the mine (ship_adjacent_mine)')
    return lifted


SHIP_MINE_EPSILON = 1e-6


def guide_r1_charge3_lf_more_vm_lf_ts_ships_shipmine(seed, **kwargs):
    """Teacher factory: ..._ships (the base stack) plus ship_adjacent_mine for every faction (above)."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts_ships(seed, **kwargs)
    _guide['ship_adjacent_mine'] = True
    _wrap_rank('_ship_adjacent_mine', ship_adjacent_mine_scores)
    return teacher


def guide_r1_charge3_lf_more_vm_lf_ts_ships_endgame(seed, **kwargs):
    """Teacher factory: ..._ships (the base stack) plus endgame_prices for every faction: in round 6 the
    state value prices the stock at the final-scoring rates (see guide_potential)."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts_ships(seed, **kwargs)
    _guide['endgame_prices'] = True
    return teacher


# ── track_plans (user 2026-10-20 "트랙을 가치로 보는게 맞는데 그것 보단 현재 상황/종족/계획에 따라 고르는 모습을 보여줬으면",
# "종족별 추천 부품이랑 연계 되게끔 할래?", "구현해"; HANDOFF E36–E37) ──────────────────────────────────────────
# Why: a research level is 16 charges whatever the track (guide_value.RESEARCH_STEP), so the one-step ranking
# keeps only the step's immediate reward — AI's QIC (7 charges) beats Navigation's range, Gaia's former and
# Science's knowledge, which pay only when a later move uses them (091 p006 step 140: AI 9.33, Navigation 4.67,
# three compared plans tied at 311.88). The deployment factions have no track order at all (E36).
# What: a research step is compared as the plan it opens — Navigation: the cheapest planet the new range
# reaches; Terraforming: a planet whose ore cost drops; Gaia: a reachable transdim planet for the former;
# AI: a planet the new QIC reach; Economy / Science: the level itself (income). The faction tables are the
# input: FACTION_TRACKS orders the plans (a track off the faction's list gets a plan only when it opens a
# colony), TRACK_CAPS stops a track, an unmet TRACK_STEPS round target leads, and the conflicts' conditions
# pick the track (T2: Terrans Gaia after Navigation only with a Gaia rival at the table, else Science;
# X3 / B15-02: Xenos Gaia only without one). The first TRACK_PLANS_FIRST plans are compared right after the
# current choice (ahead of the family interleave), the rest keep their place; a plan that wins is remembered
# like any multi-step goal. The horizon stays the configured one for every plan (rounds 1–3 run to round 4
# under charge_r3): a longer horizon for the track plans alone made their values incomparable with the
# one-income plans (090 p002 step 166: 276.88 against 314.06), so a two-income horizon is a later, whole-seat
# experiment. Order and scope only — the rollout judges, no new number; the plan's moves are legal moves.
TRACK_PLANS_FIRST = 2
TRACK_PLANS_LAST_ROUND = 5
TRACK_PLAN_COLONIES = 2                  # colonies tried per track, cheapest first
QIC_BY_AI_LEVEL = (0, 1, 1, 2, 2, 4)     # QIC gained entering each AI level (rulebook p.22)
FORMER_LEVELS = (1, 3, 4)                # Gaia levels that add a Gaiaformer (rulebook p.22)


def _plan_level(track, level):
    """The level a track plan aims at: the frozen goals_for milestones (range at Navigation 2 / 4,
    income steps at Economy / Science 2 / 4 / 5, Terraforming 3 from 1-2)."""
    if track in ('navigation', 'economy', 'science'):
        return 2 if level < 2 else 4 if level < 4 else 5
    if track == 'terraforming' and level in (1, 2):
        return 3
    return level+1


def _plan_tracks(state, actor):
    """[(track key, target level)] in the order the faction's guide names them, after the conditions
    (T2, X3), the caps (TRACK_CAPS) and the round targets (TRACK_STEPS: an unmet one leads)."""
    player = state['players'][actor]
    faction = player['faction']
    levels = player['research_tracks']
    others = [p for i, p in enumerate(state['players']) if i != actor]
    gaia_rival = any(p.get('faction') in GAIA_FACTIONS for p in others)
    tracks = list(_faction_tracks(player))
    if faction == 'Terrans' and not _part(player, 'mj01'):    # T2 (conflicts/base-factions.md); mj01: MJ01-23
        tracks = ['navigation', 'gaia' if gaia_rival else 'science', 'economy']
    elif faction == 'Xenos' and gaia_rival:                    # X3 / B15-02 (niche_tracks' reading)
        tracks = [t for t in tracks if t != 'gaia']
    if faction == 'Taklons' and _part(player, 'mj01') and TFMARS_SHIP in (player.get('explored_ships') or ()):
        tracks.append('gaia')      # user 10-24: T F Mars forms at once, no tokens locked — Gaia 1 for the former only
    if 'gaia' not in tracks and _asteroid_gaia(state, player):
        tracks.append('gaia')
    caps = _track_caps(player)
    steps = [(t, level) for start, t, level in _track_steps_table(player)
             if start <= state['round'] and levels.get(t, 0) < level]
    if _guide.get('plan_menu'):
        steps = _menu_track_steps(state, actor, steps)
    plan = list(steps)
    for t in tracks:
        if levels.get(t, 0) < min(caps.get(t, 5), 5) and all(t != s for s, _ in plan):
            plan.append((t, _plan_level(t, levels.get(t, 0))))
    return plan


# Round targets that only the plan_menu track plans read (E97, user 2026-10-24 "자료 기반으로 종족별 좋은 테크트리를
# 최대한 올릴 수 있게" → "plan_menu 보충"): Geodens Terraforming 3 and Navigation 2 first after the round-1 Economy /
# Science start (faction-tracks-openings.md Geodens row, B14; "the round terraforming starts" read as round 2, the bot's
# reading). 105 rounds 1-3: Geodens Terraforming 3 / 0 steps, AI 67 / 53 (research_counts). Generation order only.
MENU_TRACK_STEPS = {'Geodens': ((2, 'terraforming', 3), (2, 'navigation', 2))}


def _menu_track_steps(state, actor, steps):
    """E86 (ㄴ): the resource conditions of two swap rules become the track plans' generation order under
    plan_menu (the swap rules themselves are untouched). science_when (Nevlas, Ivits; science_first): the
    faction's round target is the Science or the Economy entry by the tiles on the board. research_when_land
    (LAND_ROUNDS, only when no faction round target is pending): no cheap land in reach → the Navigation plan
    leads (Terraforming at Navigation 5); land in reach and none contested → the Economy plan to ECONOMY_SWEET.
    Contested land: the guide order stands. Order of generation only; the rollout judges."""
    player = state['players'][actor]
    faction, levels = player['faction'], player['research_tracks']
    if _part(player, 'science_when') and faction in SCIENCE_WHEN:
        entry = SCIENCE_WHEN[faction][0 if science_first(state, player) else 1]
        steps = [(t, level) for start, t, level in entry if start <= state['round'] and levels.get(t, 0) < level]
    if not steps and faction in MENU_TRACK_STEPS:
        steps = [(t, level) for start, t, level in MENU_TRACK_STEPS[faction]
                 if start <= state['round'] and levels.get(t, 0) < level]
    if steps or state['round'] not in LAND_ROUNDS:
        return steps
    reach, contested = _land_counts(state, player)
    if reach == 0:
        lead = 'navigation' if levels.get('navigation', 0) < 5 else 'terraforming'
    elif contested == 0 and levels.get('economy', 0) < ECONOMY_SWEET:
        lead = 'economy'
    else:
        return steps
    if levels.get(lead, 0) >= 5:
        return steps
    return [(lead, _plan_level(lead, levels.get(lead, 0)))]


def _at_level(player, track, level):
    after = dict(player, research_tracks={**player['research_tracks'], track: level})
    if track == 'ai':
        gained = sum(QIC_BY_AI_LEVEL[player['research_tracks'].get('ai', 0)+1:level+1])
        after['resources'] = {**player['resources'], 'qic': player['resources'].get('qic', 0)+gained}
    return after


def _formers_free(player):
    res = player.get('resources') or {}
    return (player.get('gaiaformers_total', 0) - player.get('gaiaformers_deployed', 0)
            - player.get('gaiaformers_in_gaia_area', 0) - res.get('spent_gaia_formers', 0)) > 0


def _opened_colonies(state, player, track, level):
    """Planets the step to `level` on `track` opens, cheapest first: newly in reach (Navigation; AI's QIC),
    cheaper to terraform (Terraforming), a reachable transdim planet for a former (Gaia). Facts only."""
    from economy.teacher import RING, ORE_PER_STEP
    after = _at_level(player, track, level)
    reach = lambda p, types: {coord for coord, _, _ in _value.targets(state, p, types)}
    if track in ('navigation', 'ai'):
        opened = reach(after, RING+('Gaia',)) - reach(player, RING+('Gaia',))
    elif track == 'terraforming':
        home = _home_type(player)
        now = player['research_tracks'].get('terraforming', 0)
        opened = set()
        if home in RING and ORE_PER_STEP[level] < ORE_PER_STEP[now]:
            for coord, planet, _ in _value.targets(state, player, RING):
                gap = abs(RING.index(home)-RING.index(planet['planet_type']))
                if min(gap, 7-gap):
                    opened.add(coord)
    elif track == 'gaia':
        former = level in FORMER_LEVELS or _formers_free(player)
        # mj01: the former also opens an Asteroid mine (Lost Fleet; _asteroid_gaia's reason for Gaia 1, debate 1/1).
        types = ('Transdim', 'Asteroid') if _part(player, 'mj01') else ('Transdim',)
        opened = reach(after, types) if former else set()
    else:
        return []
    return sorted(opened, key=lambda c: (_colony_cost(state, after, c)[1], c))[:TRACK_PLAN_COLONIES]


def track_plan_goals(snapshot):
    """The track plans for this decision (empty: part off, not the action phase, round 6)."""
    from four_factions.preparation import Goal, viable, achieved
    state, actor = snapshot['state'], snapshot.get('player')
    phase = state.get('phase')
    if (actor is None or not isinstance(phase, dict) or 'ActionPhase' not in phase
            or state['round'] > TRACK_PLANS_LAST_ROUND):
        return []
    player = state['players'][actor]
    if not _part(player, 'track_plans'):
        return []
    levels = player['research_tracks']
    plans = []

    def add(track, level, colonies, bare):
        name = TRACK_NAMES[track]
        research = Goal(f'{name}-{level}', 'research', target=name, level=level)
        for coord in colonies:
            plans.append(Goal(f'track-plan-{name}-{level}>colony@{coord}', 'ordered',
                              steps=(research, Goal(f'colony@{coord}', 'colony', coord)), sources=('track_plans',)))
        if bare and not colonies:
            plans.append(Goal(f'track-plan-{name}-{level}', 'ordered', steps=(research,), sources=('track_plans',)))
    guide = _plan_tracks(state, actor)
    for track, level in guide:
        add(track, level, _opened_colonies(state, player, track, level), bare=True)
    for track in TRACK_KEYS.values():
        if levels.get(track, 0) < 5 and all(track != t for t, _ in guide):
            level = _plan_level(track, levels.get(track, 0))
            add(track, level, _opened_colonies(state, player, track, level), bare=False)
    return [p for p in plans if viable(snapshot, actor, p) and not achieved(snapshot, actor, p)]


def _is_track_plan(goal):
    return str(getattr(goal, 'name', '')).startswith('track-plan')


def _plan_track(goal):
    """The track a track plan researches, or None."""
    if not _is_track_plan(goal):
        return None
    return next((step.target for step in goal.steps if step.family == 'research'), None)


def install_track_plans():
    """goals_for: the track plans first, the bare research goals they cover dropped; interleave_families:
    the first TRACK_PLANS_FIRST plans (one per track) stay ahead of the family round-robin."""
    import four_factions.preparation as p
    inner = p.goals_for
    if not getattr(inner, '_track_plans', False):
        def goals_for(snapshot, **kwargs):
            goals = inner(snapshot, **kwargs)
            plans = track_plan_goals(snapshot)
            if not plans:
                return goals
            covered = {step.name for plan in plans for step in plan.steps if step.family == 'research'}
            return [*plans, *[g for g in goals
                              if not (getattr(g, 'family', None) == 'research' and g.name in covered)]]
        for name, value in vars(inner).items():
            if name.startswith('_') and isinstance(value, bool):
                setattr(goals_for, name, value)
        goals_for._track_plans = True
        goals_for.__wrapped__ = getattr(inner, '__wrapped__', inner)
        p.goals_for = goals_for
    inner_interleave = p.interleave_families
    if not getattr(inner_interleave, '_track_plans', False):
        def interleave_families(items, family):
            first, tracks = [], set()
            for g in items:                      # one plan per track ahead, the guide's order
                track = _plan_track(g)
                if track is not None and track not in tracks and len(first) < TRACK_PLANS_FIRST:
                    first.append(g)
                    tracks.add(track)
            return first + inner_interleave([g for g in items if g not in first], family)
        interleave_families._track_plans = True
        interleave_families.__wrapped__ = inner_interleave
        p.interleave_families = interleave_families
    install_task_dedup()


def guide_r1_charge3_lf_more_vm_lf_ts_ships_plans(seed, **kwargs):
    """Teacher factory: ..._ships (the base stack) plus track_plans for every faction (above)."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts_ships(seed, **kwargs)
    _guide['track_plans'] = True
    install_track_plans()
    return teacher


# ── round_tile_lead (user 2026-10-20 "테스트 오래 걸리는데 미리 만드는거 어때"; HANDOFF E38 round_tile_plans) ──────
# The round scoring tile pays its VP inside the rollout already (engine VP), but with four comparisons the goal
# that scores it is often never compared (091 step 140: four plans, none a colony while the tile paid mines).
# round_tile_lead moves the first ROUND_TILE_LEAD goals whose next step is what this round's tile scores
# (RoundCondition: BuildMine, BuildMineOnGaia, BuildMineOnNewPlanetType, BuildMineInNewSector,
# TerraformingStep, UpgradeTradingStation, UpgradeResearchLab, UpgradeLargeBuilding, ResearchAdvance,
# FormFederation) to the front of the goal list, so their family leads the round-robin. Facts only
# (the tile's condition against the goal's planet / building / track), order only; the rollout judges.
ROUND_TILE_LEAD = 2


def _round_condition(state):
    tiles = state.get('round_tiles') or []
    rnd = state.get('round') or 0
    if not 1 <= rnd <= len(tiles) or not isinstance(tiles[rnd-1], dict):
        return None
    return tiles[rnd-1].get('condition')


def _planet_kind(planet):
    return 'Gaia' if planet.get('is_gaia_formed') else planet.get('planet_type')


def _scores_round_tile(state, actor, goal, condition):
    """Whether `goal`'s next step is what this round's tile scores."""
    from economy.teacher import RING
    from four_factions.preparation import owned
    player = state['players'][actor]
    if getattr(goal, 'family', None) == 'ordered' and goal.steps:
        goal = goal.steps[0]
    family = getattr(goal, 'family', None)
    if condition == 'ResearchAdvance':
        return family == 'research'
    if condition == 'FormFederation':
        return family in ('federations', 'federation-race') or (
            family == 'root' and str(getattr(goal, 'name', '')).startswith('federation'))
    if condition in ('UpgradeTradingStation', 'UpgradeResearchLab', 'UpgradeLargeBuilding'):
        if family != 'upgrade':
            return False
        old = owned(player, goal.coord)
        bescods = player['faction'] == 'Bescods'
        if condition == 'UpgradeTradingStation':
            return old == 'Mine'
        if condition == 'UpgradeResearchLab':
            return old == 'TradingStation' and goal.target != 'PlanetaryInstitute' and not bescods
        return ((old == 'TradingStation' and (goal.target == 'PlanetaryInstitute' or bescods))
                or (old == 'ResearchLab' and goal.target != 'PlanetaryInstitute'))
    if family == 'expansion':
        return condition == 'BuildMine'
    if family != 'colony':
        return False
    cell = state['board']['hexes'].get(goal.coord)
    planet = cell.get('planet') if cell else None
    if not planet:
        return False
    kind = _planet_kind(planet)
    if condition == 'BuildMine':
        return True
    if condition == 'BuildMineOnGaia':
        return kind == 'Gaia'
    if condition == 'BuildMineOnNewPlanetType':
        hexes = state['board']['hexes']
        own = {_planet_kind(hexes[s['hex']]['planet']) for s in player['structures']
               if hexes.get(s['hex']) and hexes[s['hex']].get('planet')}
        return kind not in own
    if condition == 'BuildMineInNewSector':
        from integrated.features import sector_at
        return sector_at(state, goal.coord) not in {sector_at(state, s['hex']) for s in player['structures']}
    if condition == 'TerraformingStep':
        home = _home_type(player)
        if kind not in RING or home not in RING:
            return False
        gap = abs(RING.index(home)-RING.index(kind))
        return min(gap, 7-gap) > 0
    return False


def round_tile_lead_goals(snapshot, goals):
    """`goals` with the first ROUND_TILE_LEAD goals this round's tile scores moved to the front."""
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or not isinstance(state.get('phase'), dict) or 'ActionPhase' not in state['phase']:
        return goals
    if not _part(state['players'][actor], 'round_tile_lead'):
        return goals
    condition = _round_condition(state)
    if condition is None:
        return goals
    lead = [g for g in goals if _scores_round_tile(state, actor, g, condition)][:ROUND_TILE_LEAD]
    if not lead:
        return goals
    return lead + [g for g in goals if g not in lead]


def install_round_tile_lead():
    import four_factions.preparation as p
    inner = p.goals_for
    if getattr(inner, '_round_tile_lead', False):
        return

    def goals_for(snapshot, **kwargs):
        return round_tile_lead_goals(snapshot, inner(snapshot, **kwargs))
    for name, value in vars(inner).items():
        if name.startswith('_') and isinstance(value, bool):
            setattr(goals_for, name, value)
    goals_for._round_tile_lead = True
    goals_for.__wrapped__ = getattr(inner, '__wrapped__', inner)
    p.goals_for = goals_for


def guide_r1_charge3_lf_more_vm_lf_ts_ships_roundtile(seed, **kwargs):
    """Teacher factory: ..._ships (the base stack) plus round_tile_lead for every faction (above)."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts_ships(seed, **kwargs)
    _guide['round_tile_lead'] = True
    install_round_tile_lead()
    return teacher


# ── plan_menu (user 2026-10-20 "plan_menu 만들어 보고"; HANDOFF E41, E45–E48) ────────────────────────────────
# One mechanism for "what the rollout compares": the plans the situation offers are gathered, the first
# MENU_FIRST of them go ahead of the family round-robin in the order the faction's row names, and the rollout
# judges (rule proposes, rollout decides — E45). Menu families:
#   'tile'       a goal whose next step is what this round's scoring tile pays (round_tile_lead's test)
#   'federation' the best legal federation now (fed_compare's root goal, no part check)
#   'token'      the best legal move flipping a green token now (token_compare's root goal)
#   'track'      the guide-track plans (track_plans: FACTION_TRACKS, TRACK_CAPS, TRACK_STEPS, T2 / X3)
#   'ability'    the faction's own multi-step plans (frozen faction_teachers/paths.py: Itars Gaia tile, Ivits
#                station, Bescods lowest-track advance, Ambas institute swap, Firaks lab cycle, Nevlas
#                knowledge, BalTaks former QIC, Gleens natural Gaia, Geodens new type, Lantids cohabit)
#   'colony' / 'upgrade' / … the frozen goals of that family (not named in a row: they keep the round-robin)
# FACTION_MENU: the order a faction's sources give the families; MENU_DEFAULT for the rest. Data rows only —
# a new source adds or edits a row (E47). The base ranking is untouched; no horizon change (E37).
MENU_FIRST = 3
MENU_DEFAULT = ('tile', 'federation', 'token', 'track', 'ability')
FACTION_MENU = {
    'Itars': ('tile', 'ability', 'federation', 'token', 'track'),     # B7-01: the institute ability "게임 최고의 능력"
    'Bescods': ('tile', 'ability', 'federation', 'token', 'track'),   # BGGO2-S14, B13-S02: the ability before the lab
    'Ivits': ('ability', 'tile', 'federation', 'token', 'track'),     # B12: station, then federation or expansion
    'Xenos': ('federation', 'tile', 'token', 'track', 'ability'),     # B15-01: federations early (2.2 a game, 084)
    'Ambas': ('tile', 'federation', 'ability', 'token', 'track'),     # B06: institute swap feeds the federation
    'Geodens': ('tile', 'ability', 'federation', 'token', 'track'),   # B14 §4: the institute's new planet types are the engine
    'Gleens': ('tile', 'ability', 'federation', 'token', 'track'),    # B05, G4: natural Gaia colonies, then 3 federations
    'Nevlas': ('tile', 'ability', 'federation', 'token', 'track'),    # B08: power → knowledge funds the research
    'Firaks': ('tile', 'ability', 'federation', 'token', 'track'),    # weak-factions.md: lab → institute → downgrade cycle
    'Lantids': ('tile', 'ability', 'federation', 'token', 'track'),   # B16, L2: cohabit colonies, 3 federations
    'BalTaks': ('tile', 'track', 'ability', 'federation', 'token'),   # B11-02, B3: Gaia 4 in round 1 before the former QIC
    'HadschHallas': ('tile', 'track', 'federation', 'token', 'ability'),  # B17-03 Economy 2 first, federation about 3R
    # Terrans, Taklons and the Lost Fleet factions: MENU_DEFAULT (T5, K3/K4: 3 federations, no ability plan).
}
_menu_front = set()      # id() of the goals plan_menu put in front, read by the interleave wrapper
_menu_slots = []         # the same goals in row order; install_plan_menu hands them to the three task lists
_menu_pool = []          # every federation / token / track / ability goal generated this decision (front or not)
_menu_dropped = []       # generated but dropped by plan_affordable (E107 funnel: generated → budget → compared → chosen)


def _menu_family(snapshot, goal):
    name = str(getattr(goal, 'name', ''))
    faction = snapshot['state']['players'][snapshot['player']]['faction']
    if name.startswith('federation-'):
        return 'federation'
    if name.startswith('flip-'):
        return 'token'
    if _is_track_plan(goal):
        return 'track'
    if name.startswith(f'{faction}-'):
        return 'ability'
    return getattr(goal, 'family', None)


# E86 (ㄱ) affordability (user 2026-10-22 "기본기를 올려서 자원 량을 늘리고 불필요한 자원 소모를 줄이면"): a multi-step
# track / ability plan whose pending steps together cost more than the resources held plus the next income is not
# generated and, when remembered from an earlier decision, is forgotten. Plans the next income can pay stay (E75:
# the Geodens institute plan is not forced into the same round). Costs are facts: funding_need for upgrades and
# research, the mine at rulebook prices (1 ore + terraforming ore, 2 credits, range QIC, 1 QIC on a Gaia planet),
# power-paid or free faction actions cost nothing here (the Ivits station's range QIC is not budgeted either).
def _mine_cost(state, player, coord):
    from economy.teacher import RING, ORE_PER_STEP, path_distance
    from four_factions.value import navigation
    planet = state['board']['hexes'][coord]['planet']
    if planet is None:
        return {}
    starts = [s['hex'] for s in player['structures']]
    qic = max(0, (path_distance(state, starts, coord)-navigation(player)+1)//2)
    kind = planet['planet_type']
    if kind == 'Asteroid':
        return {'qic': qic}
    cost = {**MINE_COST, 'qic': qic}
    if kind == 'Gaia':
        cost['qic'] += 1
    elif kind in RING:
        gap = abs(RING.index(_home_type(player))-RING.index(kind))
        cost['ore'] += min(gap, 7-gap)*ORE_PER_STEP[player['research_tracks'].get('terraforming', 0)]
    return cost


def _plan_cost(snapshot, goal):
    """{resource: n} the pending steps of `goal` still cost together."""
    from four_factions.preparation import achieved, funding_need
    state, actor = snapshot['state'], snapshot['player']
    player = state['players'][actor]
    total = {}
    mj01 = _part(player, 'mj01')
    for step in goal.steps if goal.family == 'ordered' else (goal,):
        # mj01: an upgrade is judged on the simulated buildings (_upgrade_chain_cost: 0 when already there), not on the
        # real board — a Firaks rebuild after its downgrade is not "achieved" by the lab standing now (debate 1/1).
        if not (mj01 and step.family == 'upgrade' and step.coord) and achieved(snapshot, actor, step):
            continue
        qic_gain = 0
        if step.family == 'colony' and step.coord:
            cost = _mine_cost(state, player, step.coord)
        elif step.family == 'faction-action' and mj01 and step.target == 'FiraksDowngradeResearchLab' and step.coord:
            cost = {}       # the lab goes back to a trading station (rulebook p.21 Firaks institute), so the rebuild pays again
            player = {**player, 'structures': [{**s, 'kind': 'TradingStation'} if s['hex'] == step.coord else s
                                               for s in player['structures']]}
        elif step.family == 'faction-action':
            cost = _mine_cost(state, player, step.coord) if step.target == 'Build' and step.coord else {}
        elif step.family == 'research' and step.target in TRACK_KEYS:
            track = TRACK_KEYS[step.target]
            cost = {'knowledge': 4*max(0, step.level-player['research_tracks'].get(track, 0))}
            after = _at_level(player, track, step.level)
            qic_gain = after['resources'].get('qic', 0)-player['resources'].get('qic', 0)
            player = after
        elif step.family == 'upgrade' and step.coord and _part(player, 'mj01'):
            cost, player = _upgrade_chain_cost(snapshot, player, step)
        else:
            cost = funding_need(snapshot, step)
        for key, n in cost.items():
            total[key] = total.get(key, 0) + n
        if qic_gain:
            total['qic'] = total.get('qic', 0) - qic_gain
    return total


def _upgrade_chain_cost(snapshot, player, step):
    """mj01 (codex review 10-25 ②): funding_need prices only the next upgrade (Mine → Trading Station of a 'Mine → Institute'
    plan), so the plan looked cheap. Every upgrade up to the target is summed, the building replaced step by step
    (preparation.next_upgrade, engine prices as funding_need). Returns (cost, player after)."""
    from four_factions.preparation import next_upgrade, owned, funding_need

    def reached(kind):
        if step.target in ('Science', 'Qic'):
            return isinstance(kind, dict) and 'Academy' in kind
        return kind == step.target
    total, current = {}, player
    for _ in range(3):                                   # Mine → TS → lab / institute → academy at most
        old = owned(current, step.coord)
        if old is None or reached(old) or old == 'PlanetaryInstitute' or isinstance(old, dict):
            break
        players = [current if i == snapshot['player'] else p for i, p in enumerate(snapshot['state']['players'])]
        for key, n in funding_need(dict(snapshot, state=dict(snapshot['state'], players=players)), step).items():
            total[key] = total.get(key, 0) + n
        new = next_upgrade(current, step)
        current = {**current, 'structures': [{**s, 'kind': new} if s['hex'] == step.coord else s
                                             for s in current['structures']]}
    return total, current


def _plan_budget(state, player):
    """Resources held plus the next income (the booster's only once the seat has passed, as colony_options)."""
    income = _value.production(state, player, include_booster=bool(player.get('passed')))
    return {key: player['resources'].get(key, 0) + income[i] for i, key in enumerate(RESOURCE_KEYS)}


def _menu_multi_step(snapshot, goal):
    """A track / ability plan with two or more pending steps — the plans the affordability rule covers."""
    if goal.family != 'ordered' or _menu_family(snapshot, goal) not in ('track', 'ability'):
        return False
    from four_factions.preparation import achieved
    player = snapshot['state']['players'][snapshot['player']]
    if not _part(player, 'mj01'):
        return sum(not achieved(snapshot, snapshot['player'], step) for step in goal.steps) >= 2
    return _pending_steps(snapshot, goal) >= 2


def _pending_steps(snapshot, goal):
    """mj01: steps still to play, in plan order — an upgrade is pending when the simulated building (after the plan's
    own earlier upgrades and Firaks downgrades) is not the target yet, as _plan_cost counts (debate 1/1: a Firaks
    'downgrade → lab' with the lab standing now is two steps, not one)."""
    from four_factions.preparation import achieved, owned
    player = snapshot['state']['players'][snapshot['player']]
    pending = 0
    for step in goal.steps:
        if step.family == 'upgrade' and step.coord:
            cost, player = _upgrade_chain_cost(snapshot, player, step)
            pending += bool(cost) or owned(player, step.coord) is None
        elif step.family == 'faction-action' and step.target == 'FiraksDowngradeResearchLab' and step.coord:
            pending += 1
            player = {**player, 'structures': [{**s, 'kind': 'TradingStation'} if s['hex'] == step.coord else s
                                               for s in player['structures']]}
        else:
            pending += not achieved(snapshot, snapshot['player'], step)
    return pending


def plan_affordable(snapshot, goal):
    """False only for a multi-step track / ability plan whose pending steps cost more than held + next income."""
    if not _menu_multi_step(snapshot, goal):
        return True
    state = snapshot['state']
    player = state['players'][snapshot['player']]
    budget = _plan_budget(state, player)
    cost = _plan_cost(snapshot, goal)
    if not _part(player, 'mj01'):
        return all(budget.get(key, 0) >= n for key, n in cost.items())
    # mj01 (codex review 10-25 ①): a shortfall the free power conversions cover is affordable — rulebook free actions
    # 1 power → 1 credit, 3 → 1 ore, 4 → 1 knowledge or 1 QIC; Nevlas move one bowl-III token to the Gaia area for 1
    # knowledge (their plan 'knowledge-then-<track>'). Power counted: bowl III (a Brainstone there 3) plus what a burn
    # of bowl II brings (half of it). Coverage only — the plan's own conversions are what the rollout plays.
    power = player['resources']['power']
    tokens = power['bowl3'] + power['bowl2']//2
    brainstone = 3 if power.get('brainstone') == 'Area3' else 0
    short = {key: n - budget.get(key, 0) for key, n in cost.items() if n > budget.get(key, 0)}
    if any(key not in POWER_CONVERSION for key in short):
        return False
    if player['faction'] == 'Nevlas':
        # Knowledge: one token to the Gaia area each; the rest is spent as power, two per token with the institute
        # (rulebook p.21) — the two uses counted apart (debate 1/1).
        # Each free conversion is paid on its own and an odd remainder is lost (engine power_action_token_cost rounds
        # up per payment, debate 1/1): tokens per unit = ceil(rate / 2) with the institute.
        pi = any(_structure_kind(s) == 'PlanetaryInstitute' for s in player['structures'])
        per_unit = {key: -(-POWER_CONVERSION[key] // (2 if pi else 1)) for key in POWER_CONVERSION}
        return short.get('knowledge', 0) + sum(per_unit[key]*n for key, n in short.items() if key != 'knowledge') <= tokens
    return sum(POWER_CONVERSION[key]*n for key, n in short.items()) <= tokens + brainstone


POWER_CONVERSION = {'credits': 1, 'ore': 3, 'knowledge': 4, 'qic': 4}      # rulebook free actions, power per resource


def forget_unaffordable_plan(snapshot, memory):
    """The memory with the remembered plan dropped when plan_affordable says no; (memory, dropped name or None)."""
    from four_factions.preparation import goal_from_dict
    key = str(snapshot.get('player'))
    plans = memory.get('_plans') if isinstance(memory, dict) else None
    saved = plans.get(key) if isinstance(plans, dict) else None
    if not saved:
        return memory, None
    try:
        goal = goal_from_dict(saved)
    except TypeError:
        return memory, None
    if plan_affordable(snapshot, goal):
        return memory, None
    return {**memory, '_plans': {k: v for k, v in plans.items() if k != key}}, goal.name


def plan_menu_goals(snapshot, goals):
    """The goal list with the menu's first MENU_FIRST plans in front (faction row order); `_menu_slots` keeps them
    for the interleave / scoring_pairs wrappers that place them in the comparison order (install_plan_menu)."""
    state, actor = snapshot['state'], snapshot.get('player')
    _menu_front.clear()
    _menu_slots.clear()
    _menu_pool.clear()
    _menu_dropped.clear()
    if actor is None or not isinstance(state.get('phase'), dict) or 'ActionPhase' not in state['phase']:
        return goals
    player = state['players'][actor]
    if not _part(player, 'plan_menu'):
        return goals
    from four_factions.preparation import achieved
    all_plans = track_plan_goals(snapshot)
    plans = [g for g in all_plans if plan_affordable(snapshot, g)]      # E86 (ㄱ)
    covered = {step.name for plan in plans for step in plan.steps if step.family == 'research'}
    pool = [g for g in (fed_compare_goal(snapshot, part=False), token_compare_goal(snapshot, part=False)) if g]
    pool += plans + [g for g in goals if not (getattr(g, 'family', None) == 'research' and g.name in covered)]
    # A dropped plan's research stays a bare goal (the goals_for wrapper may already have removed it from `goals`).
    for plan in all_plans:
        if plan in plans:
            continue
        for step in plan.steps:
            if (step.family == 'research' and not achieved(snapshot, actor, step) and step.name not in covered
                    and all(g.name != step.name for g in pool)):
                pool.append(step)
    _menu_dropped.extend(g for g in all_plans if g not in plans)
    _menu_dropped.extend(g for g in pool if not plan_affordable(snapshot, g))
    pool = [g for g in pool if g not in _menu_dropped]
    condition = _round_condition(state)
    front = []
    for family in FACTION_MENU.get(player['faction'], MENU_DEFAULT):
        if len(front) >= _guide.get('menu_first', MENU_FIRST):
            break
        if family == 'tile':
            pick = next((g for g in pool if g not in front and condition
                         and _scores_round_tile(state, actor, g, condition)), None)
        else:
            pick = next((g for g in pool if g not in front and _menu_family(snapshot, g) == family), None)
        if pick is not None:
            front.append(pick)
    _menu_front.update(id(g) for g in front)
    _menu_slots.extend(front)
    # Debate 2026-10-22 (Codex): the front alone cannot tell "never generated" from "generated, behind the third
    # slot" (Geodens' token is fourth in its row); the worker records both lists.
    _menu_pool.extend(g for g in pool if _menu_family(snapshot, g) in ('federation', 'token', 'track', 'ability'))
    return front + [g for g in pool if g not in front]


def _plain_plan(plan):
    """current-choice and the root-N alternatives preparation.search builds from the ranking. The menu's
    federation-N / flip-N goals also carry family 'root' (single moves, never remembered) but they are
    proposals and take an exact tie like any other plan (review-code-d60b9b0)."""
    name = str(plan.get('goal', ''))
    return name == 'current-choice' or name.startswith('root-') or plan.get('family') == 'current'


def menu_tie_break(snapshot, result):
    """An exact value tie between the current choice (or a root move) and a proposed plan goes to the plan.

    User 2026-10-22 ("계측 만들고, plan_menu 대부분 완성하고 실험 돌리면서 고쳐", E74): 101 pair-002/game-0-A03 step
    114 — the menu's Geodens new-type plan tied the current choice at 265.89 and lost the tie to comparison
    order, so nothing was remembered and the ability plan's second half (the colony after the institute)
    never guided the next decisions. "규칙이 제안, 롤아웃이 결정": when the rollout is indifferent the proposal
    stands — its first move is played and the plan is remembered like a winner. Exact ties only, no value
    changes; the decision log keeps the replaced choice under `menu_tie`."""
    import math
    plans = [p for p in result.get('plans') or [] if p.get('complete')
             and isinstance(p.get('value'), (int, float)) and math.isfinite(p['value'])]
    if not plans:
        return
    best = max(p['value'] for p in plans)
    winner_plain = any(p['value'] == best and p.get('first') == result.get('index') and _plain_plan(p) for p in plans)
    tied = [p for p in plans if p['value'] == best and not _plain_plan(p) and p.get('family') != 'bgg-opening'
            and isinstance(p.get('first'), int)]
    if not winner_plain or not tied or str(result.get('selected', '')).startswith('menu-tie '):
        return
    pick = tied[0]
    # publish_current() rewrites index/selected after every comparison, so this runs again on each
    # publish and at the end (like _value_max); the first replaced choice is the one kept.
    result.setdefault('menu_tie', {'replaced': result.get('selected'), 'replaced_index': result.get('index')})
    result.update(index=pick['first'], selected=f'menu-tie {pick["goal"]}')
    memory, spec, actor = result.get('memory'), pick.get('goal_spec'), snapshot.get('player')
    # Family 'root' (federation-N / flip-N) is a single move: played, not remembered (as in preparation.search).
    if isinstance(memory, dict) and isinstance(spec, dict) and actor is not None and pick.get('family') != 'root':
        memory.setdefault('_plans', {})[str(actor)] = {**spec, 'first': None}


def install_plan_menu():
    """goals_for: plan_menu_goals over the frozen goals; interleave_families / scoring_pairs: the menu's front
    opens the comparison order (below); fed_remember_scores keeps the root ranking for the federation / token
    goals; search: menu_tie_break after value_max (E74).

    Comparison order (E82 (ㄱ), 102 `--positions`): preparation.search and parallel_search._planned_tasks build the
    tasks as control, goals[0], roots[0], paired[0], goals[1], roots[1], ... — a front of three kept together in the
    goals list landed at positions 1, 4 and 7, and cap60 compares four plans, so the second slot was compared only
    when no scoring pair existed (102: federation at p3 ×2–23 per faction, token ×0–5) and the third never. The
    three slots are spread over the three lists instead: goals keep slot 1 (and any slot beyond the third), the
    roots list opens with slot 2, the scoring pairs with slot 3 — positions 1, 2, 3 after control. A remembered
    plan (search inserts it at goals[0]) still takes position 1 and pushes slot 1 to 4, as before."""
    import four_factions.preparation as p
    if not getattr(p.search, '_menu_tie', False):
        inner_search = p.search

        def search(env, snapshot, memory, publish, *args, **kwargs):
            def publish_tie(result):
                if _guide.get('plan_menu'):
                    menu_tie_break(snapshot, result)
                publish(result)
            forgot = None
            if _guide.get('plan_menu'):
                memory, forgot = forget_unaffordable_plan(snapshot, memory)      # E86 (ㄱ): the memory it gets is a copy
            result = inner_search(env, snapshot, memory, publish_tie, *args, **kwargs)
            if _guide.get('plan_menu'):
                menu_tie_break(snapshot, result)
                if forgot:
                    result['menu_forgot'] = forgot
            return result
        search._menu_tie = True
        search._value_max = getattr(inner_search, '_value_max', False)
        search._parallel = getattr(inner_search, '_parallel', False)
        p.search = search
    inner = p.goals_for
    if not getattr(inner, '_plan_menu', False):
        def goals_for(snapshot, **kwargs):
            return plan_menu_goals(snapshot, inner(snapshot, **kwargs))
        for name, value in vars(inner).items():
            if name.startswith('_') and isinstance(value, bool):
                setattr(goals_for, name, value)
        goals_for._plan_menu = True
        goals_for.__wrapped__ = getattr(inner, '__wrapped__', inner)
        p.goals_for = goals_for
    inner_interleave = p.interleave_families
    if not getattr(inner_interleave, '_plan_menu', False):
        def interleave_families(items, family):
            # Only search's two calls are touched: the proposals (they carry the front) and the root-N list.
            # quick.py (candidate indices) and source_paths.py (cores) import this name too and pass through.
            if any(id(g) in _menu_front for g in items):
                return _menu_slots[0:1] + _menu_slots[3:] + inner_interleave(
                    [g for g in items if id(g) not in _menu_front], family)
            if items and all(str(getattr(g, 'name', '')).startswith('root-') for g in items):
                return _menu_slots[1:2] + inner_interleave(items, family)
            return inner_interleave(items, family)
        interleave_families._plan_menu = True
        interleave_families.__wrapped__ = inner_interleave
        p.interleave_families = interleave_families
    inner_pairs = p.scoring_pairs
    if not getattr(inner_pairs, '_plan_menu', False):
        def scoring_pairs(snapshot, scores, goals):
            # Slots 2 and 3 are not in `goals` any more; the pairs are still built over them.
            return _menu_slots[2:3] + inner_pairs(snapshot, scores, [*goals, *_menu_slots[1:3]])
        scoring_pairs._plan_menu = True
        scoring_pairs.__wrapped__ = inner_pairs
        p.scoring_pairs = scoring_pairs
    _wrap_rank('_fed_remember', fed_remember_scores)
    install_task_dedup()


_task_seen = []     # the goals and scoring pairs of the search being built; the roots list that follows drops them
_task_exec_key = [False]    # ..._ships_menu1_all: dedup by execution key (set by goals_for, which starts each search)


def _exec_key(goal):
    """The Goal with its label-only fields cleared: name; sources down to the one flag the rollout reads
    ('B19' in preparation.viable / funding_need); steps recursively. family, coord, target, level, tile, first, payoff
    all steer moves and stay."""
    from dataclasses import replace
    return replace(goal, name='', sources=('B19',) if 'B19' in goal.sources else (),
                   steps=tuple(_exec_key(step) for step in goal.steps))


def _task_in(goal, goals):
    if not _task_exec_key[0]:
        return goal in goals
    key = _exec_key(goal)
    return any(goal == other or key == _exec_key(other) for other in goals)


def _wrapper_flags(wrapper, inner, flag):
    """Keep the inner wrappers' install flags visible on the outermost function (installers test the outermost)."""
    for name, value in vars(inner).items():
        if name.startswith('_') and isinstance(value, bool):
            setattr(wrapper, name, value)
    setattr(wrapper, flag, True)
    wrapper.__wrapped__ = inner


def install_task_dedup():
    """Each plan once in the comparison order (lab 103, E90). search builds control, goals[0], roots[0], paired[0],
    goals[1], … and a remembered plan inserted at goals[0] can be proposed again — by goals_for itself (A arm, 15% of
    103's decisions) or by plan_menu's slots 2 and 3 at the head of the roots / scoring-pair lists (B, 31%) — so it
    rolled out twice and took one of the four comparisons. The frozen tree cannot change (teacher_ab refuses a
    changed FROZEN.json), so the three names search calls are wrapped, outermost: goals_for starts a new list,
    scoring_pairs (called right after the remembered plan is inserted) drops later duplicates from search's own
    goals list in place and from its pairs, and the roots interleave that search calls next drops what goals and
    pairs already hold. parallel_search._planned_tasks makes the same calls, so its prediction stays exact.
    Equality is the whole Goal (name, steps, first …), not the name. Installers that wrap these names call this
    again at their end so it stays outermost. Each wrapper acts only while it is the outermost function (otherwise it
    passes straight through), so two layers left by repeated installs do not let the inner one consume _task_seen."""
    import four_factions.preparation as p
    inner_goals = p.goals_for
    if not getattr(inner_goals, '_task_dedup_outer', False):
        def goals_for(snapshot, **kwargs):
            if p.goals_for is not goals_for:    # an inner layer left by an earlier install must not consume _task_seen
                return inner_goals(snapshot, **kwargs)
            _task_seen.clear()
            try:
                player = snapshot['state']['players'][snapshot['player']]
                _task_exec_key[0] = bool(_part(player, 'mj01'))
            except (KeyError, TypeError, IndexError):
                _task_exec_key[0] = False
            return inner_goals(snapshot, **kwargs)
        _wrapper_flags(goals_for, inner_goals, '_task_dedup')
        goals_for.__wrapped__ = getattr(inner_goals, '__wrapped__', inner_goals)
        goals_for._task_dedup_outer = True
        p.goals_for = goals_for
    inner_pairs = p.scoring_pairs
    if not getattr(inner_pairs, '_task_dedup_outer', False):
        def scoring_pairs(snapshot, scores, goals):
            if p.scoring_pairs is not scoring_pairs:
                return inner_pairs(snapshot, scores, goals)
            kept = []
            for goal in goals:
                if not _task_in(goal, kept):
                    kept.append(goal)
            goals[:] = kept
            paired = []
            for goal in inner_pairs(snapshot, scores, goals):
                if not _task_in(goal, kept) and not _task_in(goal, paired):
                    paired.append(goal)
            _task_seen[:] = kept + paired
            return paired
        _wrapper_flags(scoring_pairs, inner_pairs, '_task_dedup')
        scoring_pairs._task_dedup_outer = True
        p.scoring_pairs = scoring_pairs
    inner_interleave = p.interleave_families
    if not getattr(inner_interleave, '_task_dedup_outer', False):
        def interleave_families(items, family):
            if p.interleave_families is not interleave_families:
                return inner_interleave(items, family)
            result = inner_interleave(items, family)
            # Only search's roots call (all root-N); quick.py / source_paths.py pass other items through.
            if _task_seen and items and all(str(getattr(g, 'name', '')).startswith('root-') for g in items):
                seen = list(_task_seen)
                _task_seen.clear()
                kept = []
                for goal in result:
                    if not _task_in(goal, seen) and not _task_in(goal, kept):
                        kept.append(goal)
                return kept
            return result
        _wrapper_flags(interleave_families, inner_interleave, '_task_dedup')
        interleave_families._task_dedup_outer = True
        p.interleave_families = interleave_families


def guide_r1_charge3_lf_more_vm_lf_ts_ships_menu(seed, **kwargs):
    """Teacher factory: ..._ships (the base stack) plus plan_menu for every faction (above); track_plans'
    generator is on as the menu's 'track' family (its own installer is not used)."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts_ships(seed, **kwargs)
    _guide['plan_menu'] = True
    install_plan_menu()
    return teacher


def guide_r1_charge3_lf_more_vm_lf_ts_ships_menu1(seed, **kwargs):
    """Teacher factory: ..._ships_menu with one menu front slot instead of three (E89 (ㄷ) B': 103's menu took three
    of the four comparisons and pushed the root / upgrade plans out)."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts_ships_menu(seed, **kwargs)
    _guide['menu_first'] = 1
    return teacher


# artifact_tokens (E103 ②b-2, MJ01-09 / MJ01-17; ships_menu1_all only): an Artifact discards 6 power tokens, so it is taken
# only when 4 or more tokens are left afterwards ("토큰이 없으면 거의 진행 불가"), and Itars do not take one (their 6 tokens
# are worth more as tech tiles). Such an ExamineArtifact on top swaps with the best other move. Order only.
ARTIFACT_TOKENS_DISCARDED = 6
ARTIFACT_TOKEN_FLOOR = 4


def artifact_tokens_scores(env, snapshot, scores):
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or 'ActionPhase' not in state['phase']:
        return scores
    player = state['players'][actor]
    if not _part(player, 'mj01'):
        return scores
    power = player['resources']['power']
    left = sum(power.get(k, 0) for k in ('bowl1', 'bowl2', 'bowl3')) - ARTIFACT_TOKENS_DISCARDED
    if left >= ARTIFACT_TOKEN_FLOOR and player['faction'] != 'Itars':
        return scores
    live = [i for i in range(len(scores)) if not blocked(scores[i])]
    if not live:
        return scores
    top = max(live, key=lambda i: scores[i][0])
    if snapshot['candidates'][top]['action'].get('type') != 'ExamineArtifact':
        return scores
    others = [i for i in live if snapshot['candidates'][i]['action'].get('type') != 'ExamineArtifact']
    if not others:
        return scores
    lifted = list(scores)
    why = 'Itars skip artifacts (MJ01-17)' if player['faction'] == 'Itars' else \
        f'artifact leaves {left} tokens < {ARTIFACT_TOKEN_FLOOR} (MJ01-09)'
    _swap(lifted, list(scores), max(others, key=lambda i: scores[i][0]), top, why)
    return lifted


def start_booster5_scores(env, snapshot, scores):
    """ships_menu1_all only (user 2026-10-25, known-bad-decisions.md 12/15): at the setup booster pick, when instant_gaia_spot
    holds around our structures (two Transdim planets in reach, at most one easy expansion), round booster 5 (instant Gaia)
    goes first and booster 9 (2 credits + 1 QIC), if it is an unblocked candidate, second, so the comparison sees both.
    Order only: the picks' scores are permuted (5, 9, then the rest in their old order)."""
    from current_actions.conservation import blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None:
        return scores
    player = state['players'][actor]
    if not _part(player, 'mj01'):
        return scores
    picks = {i: c['action'] for i, c in enumerate(snapshot['candidates'])
             if c['action'].get('type') == 'SelectStartingBooster' and not blocked(scores[i])}
    five = [i for i, a in picks.items() if a.get('booster_id') == INSTANT_GAIA_BOOSTER]
    if not five or not instant_gaia_spot(state, actor, [s['hex'] for s in player['structures']]):
        return scores
    nine = [i for i, a in picks.items() if a.get('booster_id') == CREDIT_QIC_BOOSTER]
    order = five[:1] + nine[:1]
    order += sorted((i for i in picks if i not in order), key=lambda i: -scores[i][0])
    slots = sorted(picks, key=lambda i: -scores[i][0])
    if order == slots:
        return scores
    lifted = list(scores)
    for i, j in zip(order, slots):
        why = '; booster 5 with two Transdim planets in reach and little easy expansion (instant Gaia)' if i == five[0] \
            else '; kept second against booster 5 (2 credits + 1 QIC)' if nine and i == nine[0] else ''
        lifted[i] = (scores[j][0], f'{scores[i][1]}{why}', *scores[i][2:])
    return lifted


def knowledge_to_credit_scores(env, snapshot, scores):
    """ships_menu1_all only (user 2026-10-25, lab 106 pair-005 Geodens "지식 > 돈은 최악의 수"): knowledge to credits is blocked
    while a research advance, or an ore or power to credit conversion of the same count, is open."""
    from current_actions.conservation import BLOCKED, PREFIX, blocked
    state, actor = snapshot['state'], snapshot.get('player')
    if actor is None or 'ActionPhase' not in state['phase'] or not _part(state['players'][actor], 'mj01'):
        return scores
    live = [(i, c['action']) for i, c in enumerate(snapshot['candidates']) if not blocked(scores[i])]
    research = any(a.get('type') == 'ResearchAdvance' for _, a in live)
    result = list(scores)
    for i, a in live:
        if a.get('type') != 'FreeAction' or a.get('kind') != 'KnowledgeToCredit':
            continue
        cheaper = any(b.get('type') == 'FreeAction' and b.get('kind') in ('OreToCredit', 'PowerToCredit')
                      and b.get('count', 1) == a.get('count', 1) for _, b in live)
        if research or cheaper:
            result[i] = (BLOCKED, PREFIX+'knowledge to credits is the worst conversion (research or ore/power to credits open)')
    return result


def guide_r1_charge3_lf_more_vm_lf_ts_ships_menu1_all(seed, **kwargs):
    """Teacher factory: every faction part the sources gave so far on top of ships_menu1 (user 2026-10-24 "일단
    반영할거 다 반영해봐", E103; integrate first, fix by replays): ..._byfaction_guide_res (CANDIDATE, GUIDE, SOURCE
    and RESOLVED parts) plus WEAK_FACTION_PARTS, then plan_menu with one front slot as in ships_menu1."""
    teacher = guide_r1_charge3_lf_more_vm_lf_ts_ships_byfaction_guide_res(seed, **kwargs)
    _guide['weak_factions'] = True
    _guide['mj01'] = True      # E104: the MJ01 Lost Fleet track corrections (MJ_TRACK_CAPS)
    _wrap_rank('_artifact_tokens', artifact_tokens_scores)
    _wrap_rank('_range_tile', range_tile_scores)
    _wrap_rank('_power_prefs', power_prefs_scores)
    _wrap_rank('_start_booster5', start_booster5_scores)
    _wrap_rank('_knowledge_to_credit', knowledge_to_credit_scores)
    # User 10-25 "넣을거 다 넣어봐 일단": the measured families not in the stack yet — ship_adjacent_mine in its E61 (ㄱ)
    # form (095), endgame_prices (096; watch round-5 ore→power, Taklons 7→41), federations (089: fed_compare +
    # fed_cluster) and green tokens (090: token_compare + track_race + race_prune); fed_remember stays last.
    _guide['ship_adjacent_mine'] = True
    _wrap_rank('_ship_adjacent_mine', ship_adjacent_mine_scores)
    _guide['endgame_prices'] = True
    _guide['fed'] = True
    _wrap_rank('_fed_cluster', fed_cluster_scores)
    install_fed_compare()
    _guide['tokens'] = True
    _wrap_rank('_track_race', track_race_scores)
    install_token_goals()
    _guide['plan_menu'] = True
    install_plan_menu()
    _guide['menu_first'] = 1
    # byfaction_guide_res already installed '_fed_remember' inside these wrappers and _wrap_rank does not move it, so
    # the federation / token comparisons would read the ranking before track_race, fed_cluster and the rest (debate
    # 1/1). A second recorder as the outermost wrapper stores the final ranking.
    _wrap_rank('_fed_remember_outer', fed_remember_scores)
    return teacher


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


