"""E339: does the current teacher upgrade early? Read-only replay of finished 6R games (114 / 119 / 123).

Per main-turn decision (ActionPhase, candidate list holds Pass) in rounds 1-2, one class per decision:
  selected      - the played move is an Upgrade
  prep_selected - the played move is not an Upgrade, but the selected plan ("<label> via <plan>") is an upgrade plan
                  (funding first: conversion, power action, ...)
  lost_compare  - an Upgrade was legal, a compared plan is an upgrade plan, the selected plan is not
  menu_only     - an Upgrade was legal, an upgrade goal was in the menu / menu pool but not compared
  not_in_menu   - an Upgrade was legal, no upgrade goal in menu, pool or comparison
  not_legal     - no Upgrade candidate
And, separately for every target building that was a legal Upgrade there, the same classes judged for that target
only (selected = that target was played; prep = selected plan names that target; lost = a compared plan names it; ...).
Per seat-game: R1-2 upgrades by target, first upgrade round, free upgrades (ore and credits unchanged by the move).
Each game is counted in a local tally and merged only after its whole replay succeeded (failed games add nothing).
Decision log fields used: index, decision_id, compared, menu, menu_pool, selected (tools/teacher_ab.py 534-547).

  lab/scratch_e339_upgrades.py <run dir> [<run dir> ...] --out <metrics.json>
"""
import argparse
import gzip
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(ROOT/'python'), str(ROOT/'tools')]

CLASSES = ['selected', 'prep_selected', 'lost_compare', 'menu_only', 'not_in_menu', 'not_legal']
ALIASES = {  # normalised target name -> words a plan / goal text may use for it
    'tradingstation': ('tradingstation', 'trading'),
    'researchlab': ('researchlab',),               # not bare 'lab': the selected text holds '<label> via ...'
    'planetaryinstitute': ('planetaryinstitute', 'institute'),
    'academy': ('academy',),
}


def norm(value):
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return text.lower().replace('_', '').replace(' ', '').replace('-', '')


def target_of(action):
    target = action.get('to')
    if isinstance(target, dict):
        target = next(iter(target), None)
    return norm(str(target))


def names_target(value, target):
    if value is None:
        return False
    text = norm(value)
    return any(word.replace('_', '') in text for word in ALIASES.get(target, (target,)))


def names_upgrade(value):
    if value is None:
        return False
    return 'upgrade' in norm(value) or any(names_target(value, t) for t in ALIASES)


def res(player):
    r = player.get('resources', {})
    return (r.get('ore'), r.get('credits'))


def classify(played_target, selected, compared, menu, legal, match):
    """match(value) says whether a plan text belongs to the upgrade (any upgrade, or one target)."""
    if played_target is not None:
        return 'selected'
    if not legal:
        return 'not_legal'
    if match(selected):
        return 'prep_selected'
    if any(match(p.get('goal')) or match(p.get('first')) for p in compared):
        return 'lost_compare'
    if any(match(m) for m in menu):
        return 'menu_only'
    return 'not_in_menu'


def replay_game(game_dir, rounds, Environment):
    """Tallies of one game; raises on any replay error so the caller drops the whole game."""
    result = json.loads((game_dir/'result.json').read_text())
    if not result.get('complete'):
        return None
    t = {'cls': defaultdict(Counter), 'cls_target': defaultdict(Counter), 'sel_target': defaultdict(Counter),
         'free': Counter(), 'first': defaultdict(Counter), 'seat_games': Counter(), 'gaps': [], 'logged': Counter(),
         'examples': defaultdict(list)}
    env = Environment(result['seed'], 2000)
    with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
        rows = [json.loads(line) for line in f]
    firsts = {}
    factions = result['factions']
    for row in rows:
        snap = json.loads(env.snapshot_json())
        state = snap['state']
        seat = snap.get('player')
        cands = snap['candidates']
        action = cands[row['index']]['action']
        rnd = state['round']
        is_up = action.get('type') == 'Upgrade'
        if is_up and seat is not None and seat not in firsts:
            firsts[seat] = rnd
        main_turn = ('ActionPhase' in str(state['phase']) and seat is not None
                     and any(c['action'].get('type') == 'Pass' for c in cands))
        before = res(state['players'][seat]) if seat is not None else None
        env.step(row['decision_id'], row['index'])
        if not main_turn or rnd > rounds:
            continue
        faction = factions[seat]
        legal = sorted({target_of(c['action']) for c in cands if c['action'].get('type') == 'Upgrade'})
        compared = row.get('compared')
        t['logged']['main_decisions'] += 1
        t['logged']['has_compared_field'] += compared is not None
        compared = compared or []
        menu = (row.get('menu') or []) + (row.get('menu_pool') or [])
        selected = row.get('selected')
        played = target_of(action) if is_up else None
        if is_up:
            t['sel_target'][faction][played] += 1
            if res(json.loads(env.snapshot_json())['state']['players'][seat]) == before:
                t['free'][faction] += 1
        c = classify(played, selected, compared, menu, legal, names_upgrade)
        t['cls'][faction][c] += 1
        t['cls']['ALL'][c] += 1
        if c == 'lost_compare':
            vals = [p['value'] for p in compared if p.get('value') is not None]
            uvals = [p['value'] for p in compared if p.get('value') is not None
                     and (names_upgrade(p.get('goal')) or names_upgrade(p.get('first')))]
            if vals and uvals:
                t['gaps'].append(round(max(vals)-max(uvals), 2))
        if c in ('lost_compare', 'not_in_menu', 'prep_selected'):
            t['examples'][c].append({'game': str(game_dir), 'step': row.get('step'), 'faction': faction,
                                     'round': rnd, 'legal': legal, 'selected': selected,
                                     'compared': compared, 'menu': row.get('menu')})
        for target in legal:                       # per target: judged on that target only
            tc = classify(played if played == target else None, selected, compared, menu, [target],
                          lambda v, target=target: names_target(v, target))
            if tc == 'selected' or played is None or played == target:
                t['cls_target'][target][tc] += 1
            else:
                t['cls_target'][target]['other_upgrade_selected'] += 1
    for seat, faction in enumerate(factions):
        t['seat_games'][faction] += 1
        t['first'][faction][firsts.get(seat, 0)] += 1
    return t


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('runs', nargs='+', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--rounds', type=int, default=2)
    args = parser.parse_args()
    from gaia_rl import ENGINE_BUILD_ID, Environment
    cls, cls_target, sel_target, first = (defaultdict(Counter) for _ in range(4))
    free, seat_games, logged = Counter(), Counter(), Counter()
    gaps, errors, games = [], [], 0
    examples = defaultdict(list)
    for run in args.runs:
        for game_dir in sorted(run.expanduser().glob('pair-*/game-*')):
            try:
                t = replay_game(game_dir, args.rounds, Environment)
            except Exception as error:  # noqa: BLE001 - drop the whole game, report it
                errors.append(f'{game_dir}: {error!r}')
                continue
            if t is None:
                continue
            games += 1
            for total, part in ((cls, t['cls']), (cls_target, t['cls_target']), (sel_target, t['sel_target']),
                                (first, t['first'])):
                for key, counter in part.items():
                    total[key].update(counter)
            free.update(t['free'])
            seat_games.update(t['seat_games'])
            logged.update(t['logged'])
            gaps.extend(t['gaps'])
            for key, rows in t['examples'].items():
                examples[key].extend(rows[:15-len(examples[key])])
    gaps.sort()
    target_classes = CLASSES + ['other_upgrade_selected']
    out = {
        'engine': ENGINE_BUILD_ID, 'games': games, 'rounds': f'1-{args.rounds}', 'logged': dict(logged),
        'classes_by_faction': {f: {c: v[c] for c in CLASSES} for f, v in sorted(cls.items())},
        'classes_by_legal_target': {t: {c: v[c] for c in target_classes} for t, v in sorted(cls_target.items())},
        'selected_by_faction_target': {f: dict(v) for f, v in sorted(sel_target.items())},
        'free_selected_by_faction': dict(free),
        'seat_games': dict(seat_games),
        'first_upgrade_round_by_faction': {f: dict(sorted(v.items())) for f, v in sorted(first.items())},
        'lost_compare_value_gap': {'n': len(gaps), 'median': gaps[len(gaps)//2] if gaps else None,
                                   'p25': gaps[len(gaps)//4] if gaps else None,
                                   'p75': gaps[3*len(gaps)//4] if gaps else None},
        'examples': examples, 'errors': errors[:20], 'error_count': len(errors),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: out[k] for k in ('engine', 'games', 'logged', 'error_count')}))
    for f, v in out['classes_by_faction'].items():
        print(f, v, 'first:', out['first_upgrade_round_by_faction'].get(f))
    for target, v in out['classes_by_legal_target'].items():
        print('target', target, v)


if __name__ == '__main__':
    main()
