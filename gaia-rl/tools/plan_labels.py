"""Count the selected plan labels per arm and faction over a lab/teacher_ab run.

Reads `decisions.jsonl.gz` (`selected` = "<label> via <plan>") and `result.json` (factions, a_seats) of every
complete game; no replay. Answers "did the B arm ever pick a BGG opening plan" (092: HadschHallas B 0 of 42)
without listing decisions. Labels are counted by their "via" plan (the plan that put the move forward); the
opening plans carry a `BGG-R1-` prefix, so `--prefix BGG-R1-` isolates round-1 openings.

`--families` (E74, user 2026-10-22): per arm, faction and plan family (federation / token / track / ability /
other), how many decisions had a complete plan of that family in the comparison, how often it was the plan
played, and by how much it lost on average when it was not. Needs the `compared` rows the worker writes
since E74 (older runs print only the picks).

  .venv/bin/python tools/plan_labels.py ~/projects/gaia-lab/gaia-rl/runs/lab-093-... [--prefix BGG-R1-] [--factions Ambas,Gleens] [--families]
"""
import argparse
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path

FAMILIES = ('federation', 'token', 'track', 'ability', 'other')


def family_of(goal, faction):
    """The menu family of a compared plan by its name (teacher_patches._menu_family uses the same prefixes)."""
    name = str(goal or '')
    if name == 'current-choice' or name.startswith('root-'):
        return 'plain'
    if name.startswith('federation-'):
        return 'federation'
    if name.startswith('flip-'):
        return 'token'
    if name.startswith('track-plan-'):
        return 'track'
    if name.startswith(f'{faction}-'):
        return 'ability'
    return 'other'


def via_of(selected):
    """The plan a `selected` label credits: "<label> via <plan>", "value-max <plan>", "menu-tie <plan>"."""
    selected = selected or ''
    if ' via ' in selected:
        return selected.split(' via ', 1)[1]
    for prefix in ('value-max ', 'menu-tie '):
        if selected.startswith(prefix):
            return selected[len(prefix):]
    return selected


def family_rows(rows, faction):
    """{family: {'entered', 'picked', 'lost', 'margin_sum'}} over one seat's decision rows."""
    table = {f: Counter() for f in FAMILIES}
    for row in rows:
        compared = [p for p in row.get('compared') or [] if p.get('complete') and p.get('value') is not None]
        if not compared:
            continue
        winner = max(p['value'] for p in compared)
        picked = family_of(via_of(row.get('selected')), faction)
        for family in FAMILIES:
            own = [p['value'] for p in compared if family_of(p.get('goal'), faction) == family]
            if not own:
                continue
            table[family]['entered'] += 1
            if picked == family:
                table[family]['picked'] += 1
            else:
                table[family]['lost'] += 1
                table[family]['margin_sum'] += winner-max(own)
    return table


def position_rows(rows, faction):
    """Where in the comparison order each family entered (E82 (ㄱ)): {'lengths': Counter(number of compared
    plans per decision), family: Counter(position in the compared list), family+'-incomplete': Counter(position)}.
    The compared list is in task order (current-choice first), so position 1 is the first proposal compared."""
    table = defaultdict(Counter)
    for row in rows:
        compared = row.get('compared') or []
        if not compared:
            continue
        table['lengths'][len(compared)] += 1
        # `menu` (E84 debate): the plan_menu front the worker saw — a family generated but absent from `compared`
        # was pushed out; a family absent from `menu` was never generated (e.g. no legal federation now).
        for name in row.get('menu') or []:
            table['menu'][family_of(name, faction)] += 1
        for position, plan in enumerate(compared):
            family = family_of(plan.get('goal'), faction)
            if family == 'plain':
                continue
            key = family if plan.get('complete') else f'{family}-incomplete'
            table[key][position] += 1
    return table


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--prefix', default='', help='only labels whose via-plan starts with this (e.g. BGG-R1-)')
    parser.add_argument('--factions', default='', help='comma-separated faction filter')
    parser.add_argument('--top', type=int, default=8)
    parser.add_argument('--families', action='store_true', help='comparison entry / pick / loss per plan family')
    parser.add_argument('--positions', action='store_true',
                        help='how many plans each decision compared and at which position each family entered')
    args = parser.parse_args()
    wanted = {f for f in args.factions.split(',') if f}
    counts = defaultdict(Counter)
    seats = Counter()
    by_seat = defaultdict(list)   # (arm, faction) -> decision rows
    for game_dir in sorted(args.run_dir.expanduser().glob('pair-*/game-*')):
        result_path = game_dir/'result.json'
        log_path = game_dir/'decisions.jsonl.gz'
        if not result_path.exists() or not log_path.exists():
            continue
        result = json.loads(result_path.read_text())
        if not result.get('complete'):
            continue
        factions = result['factions']
        a_seats = set(result['a_seats'])
        for seat, faction in enumerate(factions):
            seats[('A' if seat in a_seats else 'B', faction)] += 1
        with gzip.open(log_path, 'rt') as handle:
            for line in handle:
                row = json.loads(line)
                faction = factions[row['seat']]
                if wanted and faction not in wanted:
                    continue
                by_seat[(row['arm'], faction)].append(row)
                via = via_of(row.get('selected'))
                if args.prefix and not via.startswith(args.prefix):
                    continue
                counts[(row['arm'], faction)][via] += 1
    for arm, faction in sorted(counts):
        total = sum(counts[(arm, faction)].values())
        top = ' · '.join(f'{label} ×{n}' for label, n in counts[(arm, faction)].most_common(args.top))
        print(f'{arm} {faction:<13} ({seats[(arm, faction)]} seat-games, {total} picks): {top}')
    if args.families:
        print('\nfamilies: entered = decisions with a complete plan of the family in the comparison, '
              'picked = that plan played, lost = mean value margin to the winner when not')
        for arm, faction in sorted(by_seat):
            table = family_rows(by_seat[(arm, faction)], faction)
            cells = []
            for family in FAMILIES:
                c = table[family]
                if not c['entered']:
                    continue
                margin = c['margin_sum']/c['lost'] if c['lost'] else 0.0
                cells.append(f"{family} {c['entered']}/{c['picked']}/{c['lost']} (−{margin:.1f})")
            print(f"{arm} {faction:<13} " + (' · '.join(cells) if cells else '(no compared rows: run before E74)'))
    if args.positions:
        print('\npositions: compared = plans per decision (count ×decisions); family = position in the comparison '
              'order (0 = current-choice) ×entries; -incomplete = the forecast did not finish')
        for arm, faction in sorted(by_seat):
            table = position_rows(by_seat[(arm, faction)], faction)
            if not table:
                print(f'{arm} {faction:<13} (no compared rows: run before E74)')
                continue
            lengths = ' '.join(f'{n}×{c}' for n, c in sorted(table['lengths'].items()))
            menu = ' '.join(f'{f}×{c}' for f, c in sorted(table['menu'].items())) if table.get('menu') else 'not recorded'
            print(f'{arm} {faction:<13} compared {lengths} · menu generated {menu}')
            for key in sorted(k for k in table if k not in ('lengths', 'menu')):
                spread = ' '.join(f'p{p}×{c}' for p, c in sorted(table[key].items()))
                print(f'    {key:<22} {spread}')


if __name__ == '__main__':
    main()
