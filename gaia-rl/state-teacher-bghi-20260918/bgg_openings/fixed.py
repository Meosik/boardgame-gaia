"""Approved quartet coaching openings, not engine rules or PPO action masks.

The target is a minimum milestone, not an instruction to pass or stop developing
once it is built. BGG's aggregate AC count is deliberately NOT used: these three
factions must build the Science academy.
"""
import json

from current_actions.conservation import BLOCKED, PREFIX, blocked, identity

TARGETS = {'Xenos': 'Science', 'HadschHallas': 'Science',
           'Taklons': 'Science', 'Terrans': 'PlanetaryInstitute'}
# A small teacher-utility loss at the R1 boundary, never deducted from native VP.
MISSED_TARGET_COST = 3.0


def target_kind(faction):
    target = TARGETS.get(faction)
    return {'Academy': target} if target == 'Science' else target


def completed(player):
    target = target_kind(player['faction'])
    return target is not None and any(s['kind'] == target for s in player['structures']) and sum(
        s['kind'] == 'Mine' for s in player['structures']) >= 2


def boundary_loss(before, after, actor):
    if before['round'] == 1 and after['round'] > 1:
        player = before['players'][actor]
        if player['faction'] in TARGETS and not completed(player):
            return MISSED_TARGET_COST
    return 0.0


def _preview(env, snapshot, index):
    return json.loads(env.preview_state_json(snapshot['decision_id'], index))


def _burn_uses(env, snapshot, index):
    """Prove a newly payable main power spend, not just a larger bowl III.

    Loose liquidation alone is not a use. Final-round settlement retains its
    existing separate policy. Native transitions handle Brainstone and costs.
    """
    actor = snapshot['player']
    already = {identity(c['action']) for c in snapshot['candidates']}
    branch = env.fork(snapshot['decision_id'], index)
    after = json.loads(branch.snapshot_json())
    if after['player'] != actor:
        return set()
    power = after['state']['players'][actor]['resources']['power']['bowl3']
    targets = set()
    for j, candidate in enumerate(after['candidates']):
        action = candidate['action']
        if action['type'] in ('FreeAction', 'Pass') or identity(action) in already:
            continue
        end = _preview(branch, after, j)
        if end['players'][actor]['resources']['power']['bowl3'] < power:
            targets.add(identity(action))
    return targets


def _burn_funding_routes(env, snapshot, index):
    """Burn -> power conversion -> optional minimum QIC -> paid opening core.

    Bounded to these two free links; never enumerate arbitrary conversion loops.
    Native candidates prove every link. Reuse the existing critical-QIC policy.
    """
    actor = snapshot['player']
    player = snapshot['state']['players'][actor]
    core = target_kind(player['faction'])
    if snapshot['state']['round'] != 1 or any(s['kind'] == core for s in player['structures']):
        return {}
    already = {identity(c['action']) for c in snapshot['candidates']}
    branch = env.fork(snapshot['decision_id'], index)
    after = json.loads(branch.snapshot_json())
    proofs = {}

    def ready(s):
        return {identity(c['action']) for c in s['candidates'] if c['action']['type'] == 'Upgrade'
                and c['action'].get('to') == core and identity(c['action']) not in already}

    for j, candidate in enumerate(after['candidates']):
        action = candidate['action']
        if (action['type'] != 'FreeAction' or action.get('kind') not in ('PowerToOre', 'PowerToCredit')
                or identity(action) in already):
            continue
        converted = branch.fork(after['decision_id'], j)
        middle = json.loads(converted.snapshot_json())
        if middle['player'] != actor:
            continue
        terminal = ready(middle)
        if terminal:
            proofs.setdefault(identity(after), set()).add(identity(action))
            proofs.setdefault(identity(middle), set()).update(terminal)
        for k, next_candidate in enumerate(middle['candidates']):
            qic = next_candidate['action']
            if qic['type'] != 'FreeAction' or qic.get('kind') != 'QicToOre':
                continue
            funded = converted.fork(middle['decision_id'], k)
            end = json.loads(funded.snapshot_json())
            from four_factions.teacher import critical_proofs
            protected = critical_proofs(converted, middle, k, funded, end)
            terminal = ready(end) & protected.get(identity(end), set())
            if terminal:
                proofs.setdefault(identity(after), set()).add(identity(action))
                proofs.setdefault(identity(middle), set()).add(identity(qic))
                proofs.setdefault(identity(end), set()).update(terminal)
    return proofs


def enforce(env, snapshot, scores, memory):
    """Prefer real opening progress/funding; retain ordinary play when complete.

    Returns policy scores and a diagnostic. Never changes a native candidate,
    game reward, historical opening target, or a conservation prohibition.
    """
    actor = snapshot['player']
    state = snapshot['state']
    player = state['players'][actor]
    target = TARGETS.get(player['faction'])
    result = list(scores)
    audit = {'target': target, 'minimum_mines': 2, 'completed': completed(player),
             'mode': 'ordinary-continuation', 'missed_target_utility_cost': MISSED_TARGET_COST}
    if target is None or 'ActionPhase' not in state['phase']:
        return result, audit

    # Honor a proven immediate spend after our own burn; never let a later
    # baseline turn the newly enabled action into a pass or further stockpiling.
    required = memory.get('_burn_uses', {}).get(identity(snapshot))
    if required:
        allowed = [i for i, c in enumerate(snapshot['candidates'])
                   if identity(c['action']) in required and not blocked(result[i])]
        if allowed:
            result = _restrict(result, allowed, 'complete verified power spend')
            if not (state['round'] == 1 and all(snapshot['candidates'][i]['action']['type'] == 'Upgrade'
                                              for i in allowed)):
                return result, {**audit, 'mode': 'verified-burn-spend', 'eligible_indices': allowed}
            # The paid core must still choose a technology that leaves its
            # final mine funded; a conversion commitment does not choose tech.
            audit['verified_burn_chain'] = True
    memory.pop('_burn_uses', None)

    burns = [i for i, c in enumerate(snapshot['candidates']) if not blocked(result[i])
             and c['action'].get('kind') == 'BurnPower' and c['action']['type'] == 'FreeAction']
    uses = {}
    seen = set()
    if state['round'] < 6:
        for i in sorted(burns, key=lambda j: snapshot['candidates'][j]['action'].get('count', 1)):
            targets = _burn_uses(env, snapshot, i)
            routes = _burn_funding_routes(env, snapshot, i)
            after = json.loads(env.fork(snapshot['decision_id'], i).snapshot_json())
            targets.update(routes.get(identity(after), set()))
            fresh = targets-seen
            seen.update(targets)
            if fresh:
                uses[i] = fresh
                memory.setdefault('_burn_uses', {})[identity(after)] = sorted(fresh)
                for key, actions in routes.items():
                    if key != identity(after):
                        memory['_burn_uses'][key] = sorted(set(memory['_burn_uses'].get(key, ())) | actions)
            else:
                result[i] = (BLOCKED, PREFIX+'no new minimum-burn main power spend')

    if state['round'] != 1 or audit['completed']:
        return result, audit

    resources = player['resources']
    core = target_kind(player['faction'])
    has_core = any(s['kind'] == core for s in player['structures'])
    previews, states = {}, {}
    eligible = [i for i, score in enumerate(result) if not blocked(score)]
    for i in eligible:
        states[i] = _preview(env, snapshot, i)
        previews[i] = states[i]['players'][actor]

    direct, funded, needs = [], [], []
    if not has_core:
        # Finish the most advanced existing core instead of opening more labs.
        stages = {'Mine': 0, 'TradingStation': 1, 'ResearchLab': 2}
        sites = [s for s in player['structures'] if isinstance(s['kind'], str)
                 and s['kind'] in stages and not (target == 'PlanetaryInstitute' and s['kind'] == 'ResearchLab')]
        furthest = max((stages[s['kind']] for s in sites), default=-1)
        sites = [s for s in sites if stages[s['kind']] == furthest]
        from four_factions.preparation import Goal, funding_need, next_upgrade
        for site in sites:
            goal = Goal('fixed-opening-core', 'upgrade', site['hex'], target)
            next_kind = next_upgrade(player, goal)
            need = funding_need(snapshot, goal)
            needs.append(need)
            missing = {k: v-resources[k] for k, v in need.items() if v > resources[k]}
            for i in eligible:
                action = snapshot['candidates'][i]['action']
                after = previews[i]
                if any(s['hex'] == site['hex'] and s['kind'] == next_kind for s in after['structures']):
                    direct.append(i)
                elif missing and action['type'] != 'Pass':
                    gains = {k: after['resources'][k]-resources[k] for k in missing}
                    # Includes resource-granting research/tech actions, not only
                    # free conversions. Protected QIC routes stay protected.
                    if any(v > 0 for v in gains.values()) and all(
                            after['resources'][k] >= min(resources[k], need[k]) for k in need):
                        funded.append(i)
                    elif action['type'] == 'TechTileSpecialAction' and 'ore' in missing:
                        # Charge toward the shared ore action only while unused.
                        # Actual useful funding is reconsidered after every turn.
                        if 3 not in state.get('used_power_actions', []) and sum(
                            n*after['resources']['power'][b] for n, b in ((1, 'bowl2'), (2, 'bowl3'))) > sum(
                            n*resources['power'][b] for n, b in ((1, 'bowl2'), (2, 'bowl3'))):
                            funded.append(i)
    else:
        from four_factions.track_guidance import costs
        possible = costs(state, player)
        if possible:
            cheapest = min(possible.values(), key=lambda c: (c.qic, c.ore, c.credits))
            needs.append({k: getattr(cheapest, k) for k in ('ore', 'credits', 'qic')})
        mines = sum(s['kind'] == 'Mine' for s in player['structures'])
        for i in eligible:
            after = previews[i]
            if any(s['kind'] == core for s in after['structures']) and sum(
                    s['kind'] == 'Mine' for s in after['structures']) > mines:
                direct.append(i)
            elif snapshot['candidates'][i]['action']['type'] != 'Pass' and any(
                    any(resources[k] < n and after['resources'][k] > resources[k] for k, n in need.items())
                    and all(after['resources'][k] >= min(resources[k], n) for k, n in need.items())
                    for need in needs):
                funded.append(i)

    # A burn may fund a needed ore/credit action, but only with a paid-use proof.
    for i, targets in uses.items():
        # Newly available actions aren't in the root menu; check their real gains.
        branch = env.fork(snapshot['decision_id'], i)
        after = json.loads(branch.snapshot_json())
        for j, c in enumerate(after['candidates']):
            if identity(c['action']) not in targets:
                continue
            end = _preview(branch, after, j)['players'][actor]['resources']
            if any(any(resources[k] < n and end[k] > resources[k] for k, n in need.items()) for need in needs):
                funded.append(i)
                break

    # A payable cash/knowledge action alone does not justify burning while the
    # opening lacks ore. Keep only burns that actually fund this goal.
    for i in burns:
        if state['round'] < 6 and i not in funded:
            result[i] = (BLOCKED, PREFIX+'burn does not fund unfinished opening')

    if direct and not has_core:
        # A core's technology is part of the same paid action. Prefer variants
        # that also leave the last mine payable, rather than declaring the core
        # alone a success and discovering one ore missing just before passing.
        # No tile or research track is hard-coded here.
        finishable = [i for i in direct if _funded_mine_finish(states[i], previews[i], core)]
        if finishable:
            direct = finishable
            audit['next_mine_funded'] = True
    allowed = sorted(set(direct or funded))
    if allowed:
        audit.update(mode='core-or-mine-progress' if direct else 'fund-opening', eligible_indices=allowed)
        return _restrict(result, allowed, 'fixed opening takes priority'), audit

    # No proof is not impossibility. Do not invent an action or force a pass.
    # Unrelated QIC-funded colonies must not spend the opening's scarce cubes.
    for i in eligible:
        after = previews[i]
        if len(after['structures']) > len(player['structures']) and (
                not has_core or after['resources']['qic'] < resources['qic']):
            result[i] = (BLOCKED, PREFIX+'reserve construction budget for unfinished fixed opening')
    audit['mode'] = 'no-funded-progress-found'
    return result, audit


def _restrict(scores, indices, reason):
    allowed = set(indices)
    return [score if i in allowed else (BLOCKED, PREFIX+reason) for i, score in enumerate(scores)]


def _funded_mine_finish(state, player, core):
    if not any(s['kind'] == core for s in player['structures']):
        return False
    mines = sum(s['kind'] == 'Mine' for s in player['structures'])
    if mines >= 2:
        return True
    if mines != 1:
        return False  # Do not pretend to prove a multi-mine route with one cost.
    from four_factions.track_guidance import costs, affordable
    return any(affordable(cost, player['resources']) for cost in costs(state, player).values())
