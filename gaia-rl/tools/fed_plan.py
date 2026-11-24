"""Next-federation plan of one seat, computed from a snapshot (design: research/strategy/federation-plan-design.md,
stage 1 — a calculation only: no teacher reads it yet, the engine is not touched).

User 2026-11-24: 「현재 연방에서 몇 티어가 부족한지. 어떻게 채울지 고민을 하는게 맞지. 연방 자리를 미리 고민해두고」.

plan(state, pid, candidates) answers, for the seat's next federation:
  need      power the federation must reach (engine federation_minimum_power: 7; Xenos with the planetary institute 6;
            Ivits with a federation 7 x (tokens owned - terraforming-5 token + 1), counted over the whole federation)
  target    the building group to federate: its hexes, power, how much is short, satellites to connect it
  ready     a federation is formable now (power, a satellite route the seat can pay, a supply token)
  reason    when not ready: 'power', 'route' (no free space connects a strong enough group), 'satellites' (the route is
            longer than the seat can pay) or 'token' (empty supply; spaceship tokens are not read)
  moves     the Build / Upgrade candidates that are legal now and bring the target closer, with the shortfall after
  sites     free planets next to the target (gap 0) or one free space away (gap 1) — where a mine would join it

Facts used (rulebook p.14 as the engine implements it, gaia-engine/src/rules/engine.rs 4869-5020 and
rules/ai_federation.rs 24-39): building power mine 1, trading station / research lab 2, planetary institute /
academy 3, space station 1 (+1 on the large buildings with the tech tile, +1 per Bescods building on its home planet
type with the institute, +2 per Moweyds ring, +1 the lost planet); a new federation may not touch an existing one and a
mine built next to a federation joins it, so buildings and free spaces next to a federation are out; a satellite
needs a space without planet, building, own satellite or spaceship tile and costs one power token (Ivits: one QIC),
25 satellites at most.

Not in this stage: prices. A move is offered only when the engine lists it as legal now, so "cheapest" is not
computed and a filling that takes two moves is not sequenced.

  fed_plan.py check <run dir> [--python-path DIR] [--forks N]     compare with the engine on a recorded run
"""
import heapq
from itertools import combinations

POWER = {'Mine': 1, 'TradingStation': 2, 'ResearchLab': 2, 'PlanetaryInstitute': 3, 'Academy': 3, 'SpaceStation': 1}
LARGE = ('PlanetaryInstitute', 'Academy')
BUILD = ('Build', 'RoundBoosterTerraformBuild', 'RoundBoosterRangeBuild', 'TwilightRangeBuild')
MAX_GROUPS = 9          # satellite routes are exact up to this many separate building groups (strongest kept)
INF = 10**6


def kind_name(kind):
    return kind if isinstance(kind, str) else next(iter(kind))


def neighbors(coord):
    q, r = (int(x) for x in str(coord).split(','))
    return [f'{q+dq},{r+dr}' for dq, dr in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1))]


def hex_power(state, player, coord, growth, kinds=None, institute=None):
    """Power the hex adds to a federation of `player` (kinds: the seat's building kinds there, to test a change;
    institute: whether the seat has its planetary institute, to test building it)."""
    pid, board = player['player_id'], state['board']
    cell = board['hexes'][coord]
    if kinds is None:
        kinds = [kind_name(s['kind']) for s in cell['structures']
                 if s['owner'] == pid and kind_name(s['kind']) != 'Satellite']
    total = sum(POWER[name] for name in kinds)
    active = set(player['tech_tiles']) - set(player['covered_tech_tiles'])
    if 6 in active:
        total += sum(1 for name in kinds if name in LARGE)
    planet = cell.get('planet') or {}
    if (board.get('lost_planet') == coord and planet.get('owner') == pid
            and not any(s['hex'] == coord for s in player['structures'])):
        total += 1
    if growth:
        return total
    if institute is None:
        institute = any(kind_name(s['kind']) == 'PlanetaryInstitute' for s in player['structures'])
    if player['faction'] == 'Bescods' and institute:
        if planet.get('planet_type') == 'Titanium' and not planet.get('is_gaia_formed'):
            total += len(kinds)
    if player['faction'] == 'Moweyds' and coord in player['moweyds_power_ring_hexes']:
        total += 2
    return total


def need_of(player, growth):
    if growth:
        tokens = len(player['federation_tokens']) + len(player['gray_federation_tokens'])
        return 7*(max(tokens - (player['research_tracks']['terraforming'] == 5), 0) + 1)
    if player['faction'] == 'Xenos' and any(kind_name(s['kind']) == 'PlanetaryInstitute' for s in player['structures']):
        return 6
    return 7


def board_facts(state, pid):
    """What the calculation starts from: free buildings and their power, satellite spaces, the federation."""
    player = next(p for p in state['players'] if p['player_id'] == pid)
    hexes = state['board']['hexes']
    federated = {str(h) for h in player['federated_hexes']}
    growth = player['faction'] == 'Ivits' and bool(federated)
    touching = set() if growth else federated | {n for h in federated for n in neighbors(h)}
    ship_tiles = {str(c) for c in (state['board'].get('spaceship_tiles') or {}).values()}
    values, spaces = {}, set()
    for coord, cell in hexes.items():
        if coord in federated or coord in touching:
            continue
        planet = cell.get('planet')
        mine = any(s['owner'] == pid and kind_name(s['kind']) != 'Satellite' for s in cell['structures'])
        lost = bool(planet) and planet.get('planet_type') == 'LostPlanet' and planet.get('owner') == pid
        if mine or lost:
            values[coord] = hex_power(state, player, coord, growth)
        elif not planet and not cell['structures'] and pid not in cell['satellites'] and coord not in ship_tiles:
            spaces.add(coord)
    bowls = player['resources']['power']
    funds = player['resources']['qic'] if player['faction'] == 'Ivits' else bowls['bowl1'] + bowls['bowl2'] + bowls['bowl3']
    placed = sum(1 for cell in hexes.values() if pid in cell['satellites'])
    inside = sum(hex_power(state, player, h, True) for h in federated if h in hexes) if growth else 0
    return {'player': player, 'growth': growth, 'federated': federated, 'touching': touching, 'values': values,
            'spaces': spaces, 'funds': min(funds, 25 - placed), 'inside': inside, 'need': need_of(player, growth),
            'token': bool(state['research_board']['federation_tokens'])}


def solve(values, spaces, need, funds, anchors=(), base=0):
    """Best building group: {'ready', 'hexes', 'power', 'short', 'sats', 'reason', 'exact'}.

    values: hex -> power of the free buildings; spaces: hexes a satellite may take; anchors: the hexes of the
    federation that grows (Ivits) with power `base`. Adjacent buildings form one group (no satellite between
    them); the satellites of a set of groups are a minimum Steiner tree over the spaces (exact, Dreyfus-Wagner)."""
    zero = set(values) | set(anchors)
    groups, seen = [], set()
    for start in sorted(zero):
        if start in seen:
            continue
        group, stack = {start}, [start]
        while stack:
            for n in neighbors(stack.pop()):
                if n in zero and n not in group:
                    group.add(n)
                    stack.append(n)
        seen |= group
        groups.append(group)
    anchor = [g for g in groups if g & set(anchors)]
    free = sorted((g for g in groups if not g & set(anchors)), key=lambda g: (-sum(values[h] for h in g), sorted(g)))
    exact = len(free) <= MAX_GROUPS
    free = free[:MAX_GROUPS]
    terminals = anchor + free                       # the anchor (if any) is terminal 0 and always included
    fixed = 1 if anchor else 0
    if not terminals:
        return {'ready': False, 'hexes': [], 'power': base, 'short': max(0, need - base), 'sats': 0,
                'reason': 'power', 'exact': exact}
    nodes = sorted(zero | set(spaces))
    index = {h: i for i, h in enumerate(nodes)}
    weight = [0 if h in zero else 1 for h in nodes]
    edges = [[index[n] for n in neighbors(h) if n in index] for h in nodes]
    count = 1 << len(terminals)
    dp = [None]*count

    def relax(costs):
        heap = [(c, v) for v, c in enumerate(costs) if c < INF]
        heapq.heapify(heap)
        while heap:
            cost, v = heapq.heappop(heap)
            if cost != costs[v]:
                continue
            for u in edges[v]:
                step = cost + weight[u]
                if step < costs[u]:
                    costs[u] = step
                    heapq.heappush(heap, (step, u))
        return costs

    for mask in range(1, count):
        costs = [INF]*len(nodes)
        if mask & (mask - 1) == 0:
            for h in terminals[mask.bit_length() - 1]:
                costs[index[h]] = 0
        sub = (mask - 1) & mask
        while sub:
            other = mask ^ sub
            if sub < other:
                left, right = dp[sub], dp[other]
                for v in range(len(nodes)):
                    value = left[v] + right[v] - weight[v]
                    if value < costs[v]:
                        costs[v] = value
            sub = (sub - 1) & mask
        dp[mask] = relax(costs)

    def satellites(mask):
        first = terminals[(mask & -mask).bit_length() - 1]
        return min(dp[mask][index[h]] for h in first)

    best = strongest = None
    for mask in range(1, count):
        if fixed and not mask & 1:
            continue
        chosen = [terminals[i] for i in range(len(terminals)) if mask >> i & 1]
        hexes = sorted(h for g in chosen for h in g if h in values)
        power = base + sum(values[h] for h in hexes)
        sats = satellites(mask)
        short = max(0, need - power)
        row = {'hexes': hexes, 'power': power, 'short': short, 'sats': sats}
        if short == 0 and (strongest is None or sats < strongest['sats']):
            strongest = row                           # enough power, whatever the route costs
        if sats <= funds and (best is None or (short, sats, len(hexes)) < (best['short'], best['sats'], len(best['hexes']))):
            best = row
    if best is None:                                  # only possible with an anchor whose own groups cannot be reached
        best = {'hexes': [], 'power': base, 'short': max(0, need - base), 'sats': 0}
    ready = best['short'] == 0
    reason = None
    if not ready:
        reason = ('power' if strongest is None else 'route' if strongest['sats'] >= INF else 'satellites')
        if strongest is not None:
            best = {**best, 'blocked': strongest}
    return {**best, 'ready': ready, 'reason': reason, 'exact': exact}


def _after(state, facts, action):
    """(values, base, anchors, need) after a Build / Upgrade of the seat, or None when it does not change the plan.

    The planetary institute changes more than its own hex: every Bescods building on the home planet type gains 1
    and the Xenos need drops to 6 (engine bescods_home_planet_power_bonus, federation_minimum_power)."""
    player, growth, need = facts['player'], facts['growth'], facts['need']
    coord, values, base, anchors = action.get('coord'), dict(facts['values']), facts['inside'], set(facts['federated'])
    if coord is None:
        return None
    if action['type'] in BUILD:
        gain = hex_power(state, player, coord, growth, ['Mine'])
        if growth and any(n in facts['federated'] for n in neighbors(coord)):
            return values, base + gain, anchors | {coord}, need  # joins the federation that grows
        if coord in facts['touching']:
            return None                                          # joins an existing federation: no new group
        values[coord] = gain
        return values, base, anchors, need
    if action['type'] == 'Upgrade':
        to = kind_name(action['to'])
        institute = True if to == 'PlanetaryInstitute' else None
        if institute and not growth:
            if player['faction'] == 'Bescods':
                values = {h: hex_power(state, player, h, growth, institute=True) for h in values}
            if player['faction'] == 'Xenos':
                need = 6
        new = hex_power(state, player, coord, growth, [to], institute)
        if coord in values:
            if new == facts['values'][coord] and values == facts['values'] and need == facts['need']:
                return None
            values[coord] = new
            return values, base, anchors, need
        if growth and coord in facts['federated']:
            old = hex_power(state, player, coord, True)
            return (values, base + new - old, anchors, need) if new != old else None
        if values != facts['values'] or need != facts['need']:
            return values, base, anchors, need                   # the institute stands inside a federation
    return None


def plan(state, pid, candidates=()):
    facts = board_facts(state, pid)
    anchors = facts['federated'] if facts['growth'] else ()
    now = solve(facts['values'], facts['spaces'], facts['need'], facts['funds'], anchors, facts['inside'])
    ready = now['ready'] and facts['token']
    reason = now['reason'] if not now['ready'] else None if facts['token'] else 'token'
    moves, seen = [], set()
    for number, candidate in enumerate(candidates):
        action = candidate['action']
        if action.get('type') not in BUILD and action.get('type') != 'Upgrade':
            continue
        key = (action.get('coord'), 'Mine' if action['type'] in BUILD else kind_name(action['to']))
        if key in seen:
            continue
        seen.add(key)
        changed = _after(state, facts, action)
        if changed is None:
            continue
        values, base, grown, need = changed
        spaces = facts['spaces'] - {key[0]}
        after = solve(values, spaces, need, facts['funds'], grown if facts['growth'] else (), base)
        if after['short'] < now['short'] or (after['ready'] and not now['ready']):
            # Funds are taken as unchanged by the move. Ivits pays satellites with QIC and may pay the mine's range
            # with the same QIC (lab 133 pair-007 step 145: 3 QIC -> 1), so that case is marked, not decided.
            unknown = (facts['player']['faction'] == 'Ivits' and action['type'] in BUILD and after['sats'] > 0)
            moves.append({'index': number, 'type': action['type'], 'coord': key[0], 'to': key[1],
                          'short_after': after['short'], 'sats_after': after['sats'],
                          'ready_after': after['ready'] and facts['token'], 'funds_unknown': unknown})
    moves.sort(key=lambda m: (not m['ready_after'], m['short_after'], m['sats_after'], m['index']))
    return {'need': facts['need'], 'growth': facts['growth'], 'funds': facts['funds'], 'token': facts['token'],
            'buildings': facts['values'], 'inside': facts['inside'], 'ready': ready, 'reason': reason,
            'target': {k: now[k] for k in ('hexes', 'power', 'short', 'sats')}, 'blocked': now.get('blocked'),
            'exact': now['exact'], 'moves': moves, 'sites': sites(state, facts, now['hexes'], candidates)}


def sites(state, facts, target, candidates=()):
    """Free planets where a mine would join the target group: next to it (gap 0) or one free space away (gap 1)."""
    hexes = state['board']['hexes']
    legal = {c['action'].get('coord') for c in candidates if c['action'].get('type') in BUILD}
    around = set(target) or set(facts['values']) or (facts['federated'] if facts['growth'] else set())
    near = {n for h in around for n in neighbors(h)}
    far = {n for h in near if h in facts['spaces'] for n in neighbors(h)}
    out = []
    for coord in sorted((near | far) - around):
        planet = (hexes.get(coord) or {}).get('planet')
        if not planet or planet.get('owner') is not None or hexes[coord]['structures'] or coord in facts['touching']:
            continue
        out.append({'coord': coord, 'gap': 0 if coord in near else 1, 'planet_type': planet.get('planet_type'),
                    'legal_now': coord in legal})
    return out


def _main_turn(snapshot):
    state = snapshot['state']
    if 'ActionPhase' not in str(state['phase']) or snapshot.get('player') is None:
        return False
    return any(c['action'].get('type') == 'Pass' for c in snapshot['candidates'])


def _next_main_turn(branch, pid, json, limit=80):
    """Advance a fork with the first candidate of every other decision until `pid` is to move again."""
    for _ in range(limit):
        snapshot = json.loads(branch.snapshot_json())
        if not snapshot.get('candidates'):
            return None
        if _main_turn(snapshot) and snapshot['player'] == pid:
            return snapshot
        branch.step(snapshot['decision_id'], 0)
    return None


def check(run_dir, forks, python_path=None):
    import gzip
    import json
    import os
    import sys
    import time
    from collections import Counter
    from pathlib import Path
    os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
    if python_path:
        sys.path.insert(0, python_path)
    from gaia_rl import ENGINE_BUILD_ID, Environment
    start = time.monotonic()
    count = Counter()
    examples = []
    for game_dir in sorted(Path(run_dir).expanduser().glob('pair-*/game-*')):
        result = json.loads((game_dir/'result.json').read_text())
        if not result.get('complete'):
            continue
        env = Environment(result['seed'], 2000)
        with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
            rows = [json.loads(line) for line in f]
        for step, row in enumerate(rows):
            snapshot = json.loads(env.snapshot_json())
            if _main_turn(snapshot):
                state, pid, candidates = snapshot['state'], snapshot['player'], snapshot['candidates']
                types = [c['action'].get('type') for c in candidates]
                legal = 'FormFederation' in types
                limit = (snapshot.get('candidate_generation') or {}).get('federation_limit_hits', 0) > 0
                p = plan(state, pid, candidates)
                count['decisions'] += 1
                count['exact'] += p['exact']
                where = f"{game_dir.parent.name} step {step} seat {pid} {result['factions'][pid]} R{state['round']}"
                if legal:
                    count['engine legal'] += 1
                    if not p['ready']:
                        count['A engine legal, plan not ready'] += 1
                        examples.append(f"A {where} reason {p['reason']} target {p['target']}")
                else:
                    count[f"engine not legal, plan reason {p['reason'] or 'READY'}"] += 1
                    if p['ready'] and not limit:
                        count['B plan ready, engine not legal'] += 1
                        examples.append(f"B {where} target {p['target']} funds {p['funds']}")
                    for wanted in (True, False):
                        count['moves with funds unknown (Ivits mine, not forked)'] += wanted and sum(
                            m['funds_unknown'] for m in p['moves'])
                        pick = next((m for m in p['moves'] if m['ready_after'] == wanted and not m['funds_unknown']), None)
                        name = 'C fill makes it legal' if wanted else 'D move leaves it short'
                        if pick is None or count[name + ' (forks)'] >= forks:
                            continue
                        count[name + ' (forks)'] += 1
                        later = _next_main_turn(env.fork(row['decision_id'], pick['index']), pid, json)
                        if later is None or later['state']['round'] != state['round']:
                            count[name + ': seat has no further turn'] += 1
                            continue
                        formed = any(c['action'].get('type') == 'FormFederation' for c in later['candidates'])
                        if formed == wanted:
                            count[name + ': engine agrees'] += 1
                        else:
                            count[name + ': MISMATCH'] += 1
                            examples.append(f"{name[0]} {where} move {pick} engine legal after: {formed} | funds "
                                            f"{p['funds']} -> {board_facts(later['state'], pid)['funds']}")
                played = candidates[row['index']]['action']
                if played.get('type') == 'FormFederation':
                    facts = board_facts(state, pid)
                    power = facts['inside'] + sum(facts['values'].get(str(h), 0) for h in played['hexes'])
                    count['federations formed'] += 1
                    if power < facts['need'] or any(str(h) not in facts['values'] for h in played['hexes']):
                        count['E formed below need or outside the free buildings'] += 1
                        examples.append(f"E {where} power {power} need {facts['need']} hexes {played['hexes']}")
            env.step(row['decision_id'], row['index'])
    print('engine', ENGINE_BUILD_ID[:8], '| seconds', round(time.monotonic() - start))
    for name, value in sorted(count.items()):
        print(f'  {name}: {value}')
    for line in examples[:12]:
        print('  example', line)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=['check'])
    parser.add_argument('run_dir')
    parser.add_argument('--python-path', help='folder holding the gaia_rl build the run was recorded with')
    parser.add_argument('--forks', type=int, default=60, help='engine forks per check (C and D each)')
    args = parser.parse_args()
    check(args.run_dir, args.forks, args.python_path)
