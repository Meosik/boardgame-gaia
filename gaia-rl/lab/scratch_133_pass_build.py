"""Read-only counts on a self-play run (HANDOFF E296 / E303 (ㄱ)): passes with a building still legal, and the
E179 (ㄱ) condition (1-2 short of the next federation in R5-6) with the power-raising moves legal at that time.

Replays every game with the lab engine build (seed + decision log; nothing is written to the run). At each main-turn
decision of a seat (the candidate list holds Pass):
  buildable   legal Build / Upgrade candidates, deduplicated by site x target building kind (tech-tile and track
              variants of one upgrade count once). Legal = with the resources as they are; a building that needs a
              free-action conversion first is not counted.
  outside     buildable whose site is outside the seat's federations: an upgrade on a hex that is not federated, a
              mine on a hex not next to a federated hex (Ivits with a federation: every site, its federation grows)
  raising     outside and raises the building power (the teacher's own predicate, conditional_plans/routes.py
              prepare: a mine, or an upgrade to a kind with more power)
A pass is a decision whose played candidate is Pass (denominator: all passes). The count says a building was legal,
not that passing was wrong (keeping resources for the next round is a choice).

  scratch_133_pass_build.py <run dir>
"""
import gzip
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

LAB = Path('/home/sohegi/projects/gaia-lab/gaia-rl')
HERE = Path(__file__).resolve().parent
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(LAB/'python')]
from gaia_rl import ENGINE_BUILD_ID, Environment  # noqa: E402  (lab build first: the work tree build diverges)
sys.path.append(str(HERE.parent/'baseline-teacher-20260917'))
sys.path.append(str(HERE))
from federation.teacher import power  # noqa: E402
from strategy_teacher import distance, kind  # noqa: E402
from scratch_fed_why import numbers  # noqa: E402

BUILD = ('Build', 'RoundBoosterTerraformBuild', 'RoundBoosterRangeBuild', 'TwilightRangeBuild')


def sites(state, pid, candidates):
    player = next(p for p in state['players'] if p['player_id'] == pid)
    used = set(player['federated_hexes'])
    grows = player['faction'] == 'Ivits' and bool(used)
    at = {s['hex']: s['kind'] for s in player['structures']}
    buildable, outside, raising = set(), set(), set()
    for candidate in candidates:
        action = candidate['action']
        coord = action.get('coord')
        if action['type'] in BUILD and coord:
            key = (coord, 'Mine')
            out = grows or not any(distance(coord, c) == 1 for c in used)
            up = out
        elif action['type'] == 'Upgrade':
            key = (coord, kind(action['to']))
            out = grows or coord not in used
            up = out and power(player, action['to']) > power(player, at.get(coord))
        else:
            continue
        buildable.add(key)
        if out:
            outside.add(key)
        if up:
            raising.add(key)
    return player, buildable, outside, raising


def main():
    run = Path(sys.argv[1])
    print('engine', ENGINE_BUILD_ID[:8])
    passes = []          # one row per Pass played
    seats = {}           # (game, seat) -> E179 condition record
    for game_dir in sorted(run.glob('pair-*/game-*')):
        result = json.loads((game_dir/'result.json').read_text())
        if not result.get('complete'):
            print('INCOMPLETE', game_dir)
            continue
        env = Environment(result['seed'], 2000)
        formed = [0]*len(result['factions'])
        with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
            rows = [json.loads(line) for line in f]
        for step, row in enumerate(rows):
            snapshot = json.loads(env.snapshot_json())
            state = snapshot['state']
            if 'ActionPhase' in str(state['phase']) and snapshot.get('player') is not None:
                candidates = snapshot['candidates']
                types = [c['action'].get('type') for c in candidates]
                if 'Pass' in types:
                    pid = snapshot['player']
                    played = candidates[row['index']]['action']
                    player, buildable, outside, raising = sites(state, pid, candidates)
                    n = numbers(state, pid)
                    gap = n['need'] - n['total']
                    key = (game_dir.parent.name, pid)
                    record = seats.setdefault(key, {'faction': result['factions'][pid], 'hits': []})
                    if state['round'] >= 5 and 1 <= gap <= 2:
                        played_key = None
                        if played['type'] in BUILD:
                            played_key = (played.get('coord'), 'Mine')
                        elif played['type'] == 'Upgrade':
                            played_key = (played.get('coord'), kind(played['to']))
                        record['hits'].append({'round': state['round'], 'step': step, 'stage': formed[pid], 'gap': gap,
                                               'raising': len(raising), 'played': played['type'],
                                               'played_raising': played_key in raising})
                    if played['type'] == 'Pass':
                        res = player['resources']
                        passes.append({'round': state['round'], 'stage': formed[pid], 'buildable': len(buildable),
                                       'outside': len(outside), 'raising': len(raising), 'gap': gap,
                                       'credits': res['credits'], 'ore': res['ore'], 'knowledge': res['knowledge'],
                                       'qic': res['qic'], 'kinds': Counter(k for _, k in buildable)})
                    if played['type'] == 'FormFederation':
                        formed[pid] += 1
            env.step(row['decision_id'], row['index'])
        for pid in range(len(result['factions'])):
            seats[(game_dir.parent.name, pid)]['formed'] = formed[pid]

    print(f'passes {len(passes)} | seats {len(seats)}')
    print('\npasses with a legal building (site x kind, deduplicated), by round:')
    for rnd in range(1, 7):
        rows = [p for p in passes if p['round'] == rnd]
        some = [p for p in rows if p['buildable']]
        mean = lambda name, items: (sum(p[name] for p in items)/len(items) if items else 0)  # noqa: E731
        kinds = Counter()
        for p in some:
            kinds.update(p['kinds'].keys())
        print(f"  R{rnd}: passes {len(rows)} | buildable > 0: {len(some)} | outside > 0: {sum(1 for p in rows if p['outside'])} | "
              f"raising > 0: {sum(1 for p in rows if p['raising'])} | mean buildable when > 0: {mean('buildable', some):.1f} | "
              f"left at those passes: credits {mean('credits', some):.1f} ore {mean('ore', some):.1f} "
              f"knowledge {mean('knowledge', some):.1f} qic {mean('qic', some):.1f} | passes by kind {dict(kinds)}")
    total = [p for p in passes if p['buildable']]
    print(f"  all: buildable > 0 {len(total)} / {len(passes)} | outside > 0 {sum(1 for p in passes if p['outside'])} | "
          f"raising > 0 {sum(1 for p in passes if p['raising'])}")
    print('\nby federations formed before the pass (passes / buildable > 0 / outside > 0 / raising > 0):')
    for stage in sorted({p['stage'] for p in passes}):
        rows = [p for p in passes if p['stage'] == stage]
        print(f"  {stage}: {len(rows)} / {sum(1 for p in rows if p['buildable'])} / {sum(1 for p in rows if p['outside'])} / "
              f"{sum(1 for p in rows if p['raising'])}")
    print('\nR5-6 passes with a raising move legal, by shortfall of the next federation (gap <= 0 / 1-2 / 3+):')
    late = [p for p in passes if p['round'] >= 5 and p['raising']]
    print('  ', sum(1 for p in late if p['gap'] <= 0), '/', sum(1 for p in late if 1 <= p['gap'] <= 2), '/',
          sum(1 for p in late if p['gap'] >= 3), '| R5', sum(1 for p in late if p['round'] == 5), 'R6',
          sum(1 for p in late if p['round'] == 6))

    print('\nE179 condition: R5-6 main-turn decisions with the next federation 1-2 short')
    hit = {k: s for k, s in seats.items() if s['hits']}
    print(f"  seats with at least one such decision: {len(hit)} / {len(seats)} | decisions {sum(len(s['hits']) for s in hit.values())}")
    groups = defaultdict(list)
    for key, s in hit.items():
        # the stage of the hit ended formed when the seat formed more federations than it had at the hit
        ended = {('formed later' if h['stage'] < s['formed'] else 'stopped') for h in s['hits']}
        groups[' + '.join(sorted(ended))].append((key, s))
    for name, items in sorted(groups.items()):
        with_move = [(k, s) for k, s in items if any(h['raising'] for h in s['hits'])]
        played = [(k, s) for k, s in items if any(h['played_raising'] for h in s['hits'])]
        passed = [(k, s) for k, s in items if any(h['played'] == 'Pass' and h['raising'] for h in s['hits'])]
        print(f"  {name}: seats {len(items)} | a raising move legal at some such decision {len(with_move)} | "
              f"played a raising move there {len(played)} | passed with one legal {len(passed)}")
        for key, s in items:
            hits = s['hits']
            print(f"    {key[0]} seat {key[1]} {s['faction']} formed {s['formed']}: decisions {len(hits)} "
                  f"(R5 {sum(h['round'] == 5 for h in hits)}, R6 {sum(h['round'] == 6 for h in hits)}) | "
                  f"with a raising move {sum(1 for h in hits if h['raising'])} (max {max(h['raising'] for h in hits)}) | "
                  f"played raising {sum(h['played_raising'] for h in hits)} | "
                  f"pass with one legal {sum(1 for h in hits if h['played'] == 'Pass' and h['raising'])} | "
                  f"gap {min(h['gap'] for h in hits)}-{max(h['gap'] for h in hits)}")


if __name__ == '__main__':
    main()
