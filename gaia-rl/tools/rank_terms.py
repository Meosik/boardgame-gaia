"""Diagnostic only: which part of the state value a default-ranking score comes from (HANDOFF E292, cycle 132j).

The default ranking scores a move by `potential(state after) − potential(state before)` for the acting seat
(four_factions/teacher.py NativeFactionTeacher.rank; score patches may add to it afterwards). `potential_terms`
names the parts of that value the way teacher_patches.guide_potential adds them up, and puts everything it does
not name (Brainstone and Gaia-area terms, any wrapper around the potential) into 'other' = total − named parts,
so a part this mirror misses shows there instead of being lost. 'total' is the installed potential itself.
Nothing here is used by a teacher.
"""
import json


def potential_terms(state, actor, home=None):
    import four_factions.value as v
    import guide_value as gv
    import teacher_patches as tp
    total = float(v.potential(state, actor, home=home))
    phase = state['phase']
    if isinstance(phase, dict) and 'Ended' in phase:
        return {'final_score': total, 'other': 0.0, 'total': total}
    player = state['players'][actor]
    horizon = max(0, 6-state['round'])
    guide = tp._guide
    parts = {'vp': player['vp'], 'standings': v.standings(state, actor)}
    if not horizon and (guide['endgame_prices'] or tp._part(player, 'endgame_prices')):
        parts['endgame_stock'] = tp.endgame_stock_vp(player)
    else:
        parts['research'] = gv.research_value(state, player)
        parts['stock'] = gv.materials(state, player['resources'])
        parts['power'] = tp.lf_power_value(state, player) if guide['lf_frozen'] else gv.power_value(state, player)
    income = v.production(state, player, include_booster=False)
    track_income = guide['track_income']
    if track_income is False and tp._part(player, 'track_income'):
        track_income = 'sweet'
    if track_income == 'sweet':
        income = [a-b for a, b in zip(income, tp._track_income_excess(state, player))]
    elif not track_income:
        income = [a-b for a, b in zip(income, tp._track_income(state, player))]
    parts['income'] = gv.incomes_value(state, income)
    booster = 0.0
    if horizon and (player['passed'] or state['round'] == 0):
        booster = tp._booster_value(state, player, player['booster'])
    elif horizon and tp._action_phase(state):
        booster = max((tp._booster_value(state, player, b) for b in state['boosters']), default=0)
    if state['round'] >= 1 and not player['passed'] and tp._action_phase(state):
        booster += tp.booster_pass_vp(state, player)
    parts['booster'] = booster
    parts['structures'] = gv.planet_value(state)*len(player['structures'])
    parts['ships'] = (gv.ships_value(state, player)+gv.green_tokens_value(state, player) if guide['lf_tables']
                      else gv.ship_value(state)*len(player['explored_ships']))
    if guide['lf_frozen']:
        parts['colony_options'] = tp.colony_options(state, player, home=home)
        parts['research_options'] = tp.lf_research_options(state, player)
        parts['federation_progress'] = tp.federation_progress(state, player)
        parts['leech'] = tp.lf_leech_value(state, player)
    else:
        reach = player if guide['qic_reach'] else {**player, 'resources': {**player['resources'], 'qic': 0}}
        parts['gaia'] = v.gaia_value(state, reach)
        parts['expansion'] = v.expansion_value(state, reach, home=home) if horizon else 0.0
        if guide['lf_more']:
            parts['research_options'] = tp.lf_research_options(state, player)
            parts['federation_progress'] = tp.federation_progress(state, player)
            parts['leech'] = tp.leech_value(state, player)
        else:
            parts['research_options'] = v.research_options(state, player)
    parts['tiles'] = tp._guide_tiles(state, player, horizon)
    parts = {name: float(value) for name, value in parts.items()}
    parts['other'] = total-sum(parts.values())
    parts['total'] = total
    return parts


def home_of(player):
    """The `home` NativeFactionTeacher.value passes: the shared profile's, None for the frozen quartet."""
    from four_factions.preparation import FACTIONS
    if player['faction'] in FACTIONS:
        return None
    try:
        from faction_teachers.profiles import profiles
        profile = profiles().get(player['faction'])
    except Exception:
        return None
    return getattr(profile, 'home', None)


def breakdown_indices(scores, candidates, watch, top=20, variants=3):
    """Candidate indices to break down: the watched moves, the `top` best unblocked scores, and the `variants`
    best of each upgrade target that has a watched move (the watched move's siblings). Order: watch first, then
    by score; no duplicates."""
    def unblocked(i):
        return not str(scores[i][1]).startswith('conservation blocked: ')
    ranked = sorted((i for i in range(len(scores)) if unblocked(i)), key=lambda i: (-scores[i][0], i))
    chosen = [i for i in watch if 0 <= i < len(scores)]
    chosen += ranked[:top]
    targets = {json.dumps(candidates[i]['action'].get('to'), sort_keys=True) for i in watch
               if 0 <= i < len(candidates) and candidates[i]['action'].get('type') == 'Upgrade'}
    for target in sorted(targets):
        same = [i for i in ranked if candidates[i]['action'].get('type') == 'Upgrade'
                and json.dumps(candidates[i]['action'].get('to'), sort_keys=True) == target]
        chosen += same[:variants]
    return list(dict.fromkeys(chosen))


def root_scores_record(env, snapshot, scores, watch, top=20, variants=3):
    """One JSON-ready record of the root ranking: every candidate's score and reason, the rank of each among
    the unblocked ones (1 = best), and for `breakdown_indices` the value parts before and after the move
    (`delta` = after − before per part; `score_minus_delta` = what the ranking added to the plain state delta).
    Read-only: forks the environment per broken-down candidate, as the ranking itself does."""
    actor = snapshot['player']
    candidates = snapshot['candidates']
    home = home_of(snapshot['state']['players'][actor])
    ranked = sorted((i for i in range(len(scores)) if not str(scores[i][1]).startswith('conservation blocked: ')),
                    key=lambda i: (-scores[i][0], i))
    rank = {i: n+1 for n, i in enumerate(ranked)}
    record = {'event': 'root_scores', 'actor': actor, 'unblocked': len(ranked),
              'scores': [[round(float(score), 4) if rank.get(i) else None, str(reason)[:120], rank.get(i)]
                         for i, (score, reason) in enumerate(scores)]}
    try:
        before = potential_terms(snapshot['state'], actor, home)
        record['before'] = before
        rows = []
        for i in breakdown_indices(scores, candidates, watch, top, variants):
            row = {'index': i, 'rank': rank.get(i), 'score': float(scores[i][0]), 'reason': str(scores[i][1])[:200],
                   'action': candidates[i]['action']}
            try:
                after = json.loads(env.fork(snapshot['decision_id'], i).snapshot_json())
                terms = potential_terms(after['state'], actor, home)
                row['next_player'] = after.get('player')
                row['own_federations_after'] = (sum(c['action'].get('type') == 'FormFederation' for c in after['candidates'])
                                                if after.get('player') == actor else None)
                row['delta'] = {name: round(terms.get(name, 0.0)-before.get(name, 0.0), 4)
                                for name in dict.fromkeys([*before, *terms])}
                row['score_minus_delta'] = round(float(scores[i][0])-row['delta']['total'], 4)
            except Exception as error:
                row['error'] = repr(error)[:200]
            rows.append(row)
        record['breakdown'] = rows
    except Exception as error:
        record['error'] = repr(error)[:300]
    return record
