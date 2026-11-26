"""Heuristic report of starting-structure placements and early build sites.

Usage (from gaia-rl, PYTHONPATH=python:baseline-teacher-20260917:tools):
    python tools/setup_report.py <run dir> [--out DIR]

Reads every **/setup_state.json (written by `teacher_ab.py run --stop-after-setup`) and writes
setup_report.md and setup_report.json into DIR (created; default: the run dir). Both start with a
pooled summary over all seats; seats also carry added_planets_qic (second-mine overlap at reach+QIC)."""
import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import mean, median

QIC_RANGE = 2
TOP_SITES = 5
SPECIAL = ('Gaia', 'Transdim')


def _steps(home, kind):
    """Terraforming steps from the home type on the ring; None for Gaia/Transdim (off the ring)."""
    from economy.teacher import RING
    if kind in SPECIAL or home not in RING or kind not in RING:
        return None
    gap = abs(RING.index(home)-RING.index(kind))
    return min(gap, len(RING)-gap)


def _free_planets_near(state, coord, reach):
    from strategy_teacher import distance
    from teacher_patches import _free_planet
    return {c for c, cell in state['board']['hexes'].items()
            if _free_planet(cell) and distance(coord, c) <= reach}


def seat_report(state, seat):
    from faction_teachers.profiles import profiles
    from strategy_teacher import distance
    from teacher_patches import _next_to_opponent, _reach, expansion_room
    player = state['players'][seat]
    profile = profiles().get(player['faction'])
    home = profile.home if profile else None
    reach = _reach(player)
    own = [s['hex'] for s in player['structures'] if s.get('hex')]
    others = [s['hex'] for i, p in enumerate(state['players']) if i != seat
              for s in p['structures'] if s.get('hex')]
    pairwise = [distance(a, b) for i, a in enumerate(own) for b in own[i+1:]]
    opponent_gap = {c: min((distance(c, o) for o in others), default=None) for c in own}
    reached = {c: sorted(_free_planets_near(state, c, reach)) for c in own}
    added = None
    if len(own) >= 2:
        first, second = set(reached[own[0]]), set(reached[own[1]])
        added = {'second_adds': len(second-first), 'first_adds': len(first-second)}
    added_qic = None
    if len(own) >= 2:
        first = _free_planets_near(state, own[0], reach+QIC_RANGE)
        second = _free_planets_near(state, own[1], reach+QIC_RANGE)
        added_qic = {'first_sees': len(first), 'second_sees': len(second),
                     'second_adds': len(second-first), 'shared': len(first & second)}
    hexes = state['board']['hexes']
    sites = []
    for c, cell in hexes.items():
        from teacher_patches import _free_planet
        if not _free_planet(cell) or not own:
            continue
        nearest = min(distance(c, o) for o in own)
        if nearest > reach+QIC_RANGE:
            continue
        kind = cell['planet']['planet_type']
        sites.append({'coord': c, 'planet': kind, 'steps': _steps(home, kind), 'special': kind in SPECIAL,
                      # distance only: no cost or booster check
                      'qic': nearest > reach, 'distance': nearest,
                      'near_opponent': bool(_next_to_opponent(state, seat, c)),
                      'room': expansion_room(state, seat, c)})
    sites.sort(key=lambda s: (s['qic'], s['steps'] is None, s['steps'] if s['steps'] is not None else 0,
                              not s['near_opponent'], s['coord']))
    return {'seat': seat, 'faction': player['faction'], 'home': home, 'reach': reach, 'structures': own,
            'pairwise_distance': pairwise, 'min_distance_to_opponent': opponent_gap,
            'free_planets_in_reach': reached, 'added_planets': added,
            'added_planets_qic': added_qic, 'sites': sites, 'top_sites': sites[:TOP_SITES]}


def game_report(path):
    state = json.loads(Path(path).read_text())
    result_path = Path(path).parent/'result.json'
    seed = None
    if result_path.exists():
        seed = json.loads(result_path.read_text()).get('seed')
    return {'path': str(path), 'seed': seed, 'factions': [p['faction'] for p in state['players']],
            'seats': [seat_report(state, seat) for seat in range(len(state['players']))]}


def _site_text(site):
    steps = site['planet'] if site['steps'] is None else f"{site['planet']} {site['steps']}"
    flags = ('Q' if site['qic'] else '') + ('N' if site['near_opponent'] else '')
    return f"{site['coord']} ({steps}{', '+flags if flags else ''})"


def _hist(values):
    """Sorted [value, count] pairs; ints first, then string keys."""
    return [[k, v] for k, v in sorted(Counter(values).items(),
                                      key=lambda kv: (isinstance(kv[0], str), str(kv[0]) if isinstance(kv[0], str)
                                                      else kv[0]))]


def _hist_text(hist):
    return ', '.join(f'{k}:{v}' for k, v in hist) or '-'


def _mean(values):
    values = [v for v in values if v is not None]
    return round(mean(values), 2) if values else None


def summary(games):
    """Pooled patterns across every seat of every game."""
    seats = [s for g in games for s in g['seats']]
    pair = [d for s in seats for d in s['pairwise_distance']]
    reach_adds = [s['added_planets']['second_adds'] for s in seats if s['added_planets']]
    qics = [s['added_planets_qic'] for s in seats if s['added_planets_qic']]
    nearest = []
    for s in seats:
        gaps = [v for v in s['min_distance_to_opponent'].values() if v is not None]
        nearest.append(min(gaps) if gaps else None)
    near_known = [v for v in nearest if v is not None]
    tops = [t for s in seats for t in s['top_sites']]
    steps = Counter(('off:'+t['planet']) if t['steps'] is None else t['steps'] for t in tops)
    by_faction = {}
    for s, near in zip(seats, nearest):
        row = by_faction.setdefault(s['faction'], {'dist': [], 'adds': [], 'near': [], 'seats': 0})
        row['seats'] += 1
        row['dist'] += s['pairwise_distance']
        if s['added_planets_qic']:
            row['adds'].append(s['added_planets_qic']['second_adds'])
        row['near'].append(near)
    return {
        'games': len(games), 'seats': len(seats),
        'own_distance_hist': _hist(pair), 'own_distance_median': median(pair) if pair else None,
        'second_adds_reach_hist': _hist(reach_adds),
        'second_adds_qic_hist': _hist([q['second_adds'] for q in qics]),
        'shared_qic_hist': _hist([q['shared'] for q in qics]),
        'first_sees_qic_mean': _mean([q['first_sees'] for q in qics]),
        'second_sees_qic_mean': _mean([q['second_sees'] for q in qics]),
        'two_structure_seats': len(qics),
        'nearest_opponent_hist': _hist(near_known),
        'seats_within_2_of_opponent': sum(v <= 2 for v in near_known),
        'top_sites': {'total': len(tops), 'qic': sum(t['qic'] for t in tops),
                      'near_opponent': sum(t['near_opponent'] for t in tops), 'steps_hist': _hist(steps.elements())},
        'non_qic_sites_per_seat_hist': _hist([sum(not x['qic'] for x in s['top_sites']) for s in seats]),
        'by_faction': {f: {'seats': r['seats'], 'own_distance_mean': _mean(r['dist']),
                           'second_adds_qic_mean': _mean(r['adds']), 'nearest_opponent_mean': _mean(r['near'])}
                       for f, r in sorted(by_faction.items())},
    }


def summary_lines(sm):
    t = sm['top_sites']
    lines = ['## Summary', '', f"{sm['games']} games, {sm['seats']} seats "
             f"({sm['two_structure_seats']} with two structures).", '',
             f"- own distance (value:count): {_hist_text(sm['own_distance_hist'])}; median {sm['own_distance_median']}",
             f"- 2nd mine adds at reach: {_hist_text(sm['second_adds_reach_hist'])}",
             f"- 2nd mine adds at reach+QIC: {_hist_text(sm['second_adds_qic_hist'])}",
             f"- shared planets at reach+QIC: {_hist_text(sm['shared_qic_hist'])}",
             f"- planets seen at reach+QIC, mean: first {sm['first_sees_qic_mean']}, second {sm['second_sees_qic_mean']}",
             f"- nearest opponent distance: {_hist_text(sm['nearest_opponent_hist'])}; "
             f"seats within 2: {sm['seats_within_2_of_opponent']}/{sm['seats']}",
             f"- top sites: {t['total']}, outside base reach (Q) {t['qic']}, near opponent {t['near_opponent']}; "
             f"steps {_hist_text(t['steps_hist'])}",
             f"- top sites inside base reach per seat: {_hist_text(sm['non_qic_sites_per_seat_hist'])}", '',
             '| faction | seats | own distance mean | 2nd adds (reach+QIC) mean | nearest opponent mean |',
             '|---|---|---|---|---|']
    for f, r in sm['by_faction'].items():
        cells = ['-' if v is None else v for v in (r['own_distance_mean'], r['second_adds_qic_mean'],
                                                   r['nearest_opponent_mean'])]
        lines.append(f"| {f} | {r['seats']} | {cells[0]} | {cells[1]} | {cells[2]} |")
    return lines + ['']


def markdown(games):
    out = ['# Setup report', '',
           'Sites: coord (planet type, terraform steps from home; Gaia/Transdim off the ring), Q = outside base reach (distance > reach; QIC by distance only, no cost/booster check), '
           'N = next to an opponent. Rank: no QIC, fewer steps, near opponent first.', '']
    out += summary_lines(summary(games))
    for g in games:
        out += [f"## {g['path']}", '', f"seed {g['seed']}; factions {', '.join(g['factions'])}", '',
                '| seat | faction | structures | own distance | min opp distance | added by 2nd / 1st |',
                '|---|---|---|---|---|---|']
        for s in g['seats']:
            added = s['added_planets']
            out.append(f"| {s['seat']} | {s['faction']} | {' '.join(s['structures'])} | "
                       f"{', '.join(map(str, s['pairwise_distance'])) or '-'} | "
                       f"{', '.join(f'{k}:{v}' for k, v in s['min_distance_to_opponent'].items()) or '-'} | "
                       f"{'-' if added is None else str(added['second_adds'])+' / '+str(added['first_adds'])} |")
        out.append('')
        for s in g['seats']:
            out.append(f"- seat {s['seat']} {s['faction']} top sites: "
                       + ('; '.join(_site_text(x) for x in s['top_sites']) or '-'))
        out.append('')
    return '\n'.join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Setup placement report')
    parser.add_argument('run', help='run dir containing **/setup_state.json')
    parser.add_argument('--out', help='output dir (default: the run dir)')
    args = parser.parse_args(argv)
    run = Path(args.run)
    out = Path(args.out) if args.out else run
    out.mkdir(parents=True, exist_ok=True)
    games = [game_report(p) for p in sorted(run.glob('**/setup_state.json'))]
    report = {'summary': summary(games), 'games': games}
    (out/'setup_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=1)+'\n')
    (out/'setup_report.md').write_text(markdown(games)+'\n')
    print(f'{len(games)} games -> {out/"setup_report.md"}')


if __name__ == '__main__':
    main()
