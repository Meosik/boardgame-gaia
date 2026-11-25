"""E339: does the current teacher upgrade early? Read-only replay of finished 6R games (114 / 119 / 123).

Per main-turn decision (ActionPhase, candidate list holds Pass) in rounds 1-2:
  selected      - the played move is an Upgrade
  lost_compare  - an Upgrade was legal, a compared plan starts with / aims at an upgrade, another plan won
  menu_only     - an Upgrade was legal, an upgrade goal was in the menu / menu pool but not compared
  not_in_menu   - an Upgrade was legal, no upgrade goal in menu, pool or comparison
  not_legal     - no Upgrade candidate
Split by faction and (for selected / legal) by target building. Also per seat-game: upgrades in R1-2 by target,
first upgrade round, free upgrades (ore and credits unchanged by the move). Decision log fields used:
index, decision_id, compared, menu, menu_pool, selected (tools/teacher_ab.py 534-547).

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

CLASSES = ['selected', 'lost_compare', 'menu_only', 'not_in_menu', 'not_legal']


def target_of(action):
    target = action.get('to')
    if isinstance(target, dict):
        target = next(iter(target), None)
    return str(target)


def is_upgrade_text(value):
    text = json.dumps(value, default=str).lower() if not isinstance(value, str) else value.lower()
    return 'upgrade' in text or 'tradingstation' in text or 'academy' in text or 'researchlab' in text \
        or 'planetaryinstitute' in text or 'trading_station' in text or 'research_lab' in text


def res(player):
    r = player.get('resources', {})
    return (r.get('ore'), r.get('credits'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('runs', nargs='+', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--rounds', type=int, default=2)
    args = parser.parse_args()
    from gaia_rl import ENGINE_BUILD_ID, Environment
    cls = defaultdict(Counter)                 # faction -> class -> n
    cls_target = defaultdict(Counter)          # target -> class (legal decisions only, by the targets legal there)
    sel_target = defaultdict(Counter)          # faction -> target -> upgrades R1..rounds
    free_sel = Counter()                       # faction -> free upgrades R1..rounds
    first_round = defaultdict(Counter)         # faction -> first upgrade round (0 = never) -> seat-games
    seat_games = Counter()
    gaps = []                                  # lost_compare: best value - best upgrade-plan value
    logged = Counter()
    errors = []
    games = 0
    examples = defaultdict(list)
    for run in args.runs:
        for game_dir in sorted(run.expanduser().glob('pair-*/game-*')):
            try:
                result = json.loads((game_dir/'result.json').read_text())
                if not result.get('complete'):
                    continue
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
                    if action.get('type') == 'Upgrade' and seat is not None and seat not in firsts:
                        firsts[seat] = rnd
                    main_turn = ('ActionPhase' in str(state['phase']) and seat is not None
                                 and any(c['action'].get('type') == 'Pass' for c in cands))
                    before = res(state['players'][seat]) if seat is not None else None
                    env.step(row['decision_id'], row['index'])
                    if not main_turn or rnd > args.rounds:
                        continue
                    faction = factions[seat]
                    legal = sorted({target_of(c['action']) for c in cands if c['action'].get('type') == 'Upgrade'})
                    compared = row.get('compared')
                    logged['has_compared_field'] += compared is not None
                    logged['main_decisions'] += 1
                    compared = compared or []
                    menu = (row.get('menu') or []) + (row.get('menu_pool') or [])
                    if action.get('type') == 'Upgrade':
                        c = 'selected'
                        t = target_of(action)
                        sel_target[faction][t] += 1
                        after = res(json.loads(env.snapshot_json())['state']['players'][seat])
                        if after == before:
                            free_sel[faction] += 1
                    elif not legal:
                        c = 'not_legal'
                    else:
                        up = [p for p in compared if is_upgrade_text(p.get('first')) or is_upgrade_text(p.get('goal'))]
                        if up:
                            c = 'lost_compare'
                            vals = [p['value'] for p in compared if p.get('value') is not None]
                            uvals = [p['value'] for p in up if p.get('value') is not None]
                            if vals and uvals:
                                gaps.append(round(max(vals)-max(uvals), 2))
                            if len(examples['lost_compare']) < 15:
                                examples['lost_compare'].append({'game': str(game_dir), 'step': row.get('step'),
                                                                 'faction': faction, 'round': rnd,
                                                                 'selected': row.get('selected'),
                                                                 'compared': compared})
                        elif any(is_upgrade_text(m) for m in menu):
                            c = 'menu_only'
                        else:
                            c = 'not_in_menu'
                            if len(examples['not_in_menu']) < 15:
                                examples['not_in_menu'].append({'game': str(game_dir), 'step': row.get('step'),
                                                                'faction': faction, 'round': rnd, 'legal': legal,
                                                                'menu': row.get('menu'),
                                                                'selected': row.get('selected')})
                    cls[faction][c] += 1
                    cls['ALL'][c] += 1
                    for t in legal:
                        cls_target[t][c] += 1
                for seat, faction in enumerate(factions):
                    seat_games[faction] += 1
                    first_round[faction][firsts.get(seat, 0)] += 1
                games += 1
            except Exception as error:  # noqa: BLE001 - report and go on
                errors.append(f'{game_dir}: {error!r}')
    gaps.sort()
    out = {
        'engine': ENGINE_BUILD_ID, 'games': games, 'rounds': f'1-{args.rounds}', 'logged': dict(logged),
        'classes_by_faction': {f: {c: v[c] for c in CLASSES} for f, v in sorted(cls.items())},
        'classes_by_legal_target': {t: {c: v[c] for c in CLASSES} for t, v in sorted(cls_target.items())},
        'selected_by_faction_target': {f: dict(v) for f, v in sorted(sel_target.items())},
        'free_selected_by_faction': dict(free_sel),
        'seat_games': dict(seat_games),
        'first_upgrade_round_by_faction': {f: dict(sorted(v.items())) for f, v in sorted(first_round.items())},
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


if __name__ == '__main__':
    main()
