"""Heuristic report of starting-structure placements and early build sites.

Usage (from gaia-rl, PYTHONPATH=python:baseline-teacher-20260917:tools):
    python tools/setup_report.py <run dir>

Reads every **/setup_state.json (written by `teacher_ab.py run --stop-after-setup`) and writes
<run dir>/setup_report.md and <run dir>/setup_report.json."""
import json
import sys
from pathlib import Path

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
                      'qic': nearest > reach, 'distance': nearest,
                      'near_opponent': bool(_next_to_opponent(state, seat, c)),
                      'room': expansion_room(state, seat, c)})
    sites.sort(key=lambda s: (s['qic'], s['steps'] is None, s['steps'] if s['steps'] is not None else 0,
                              not s['near_opponent'], s['coord']))
    return {'seat': seat, 'faction': player['faction'], 'home': home, 'reach': reach, 'structures': own,
            'pairwise_distance': pairwise, 'min_distance_to_opponent': opponent_gap,
            'free_planets_in_reach': reached, 'added_planets': added,
            'sites': sites, 'top_sites': sites[:TOP_SITES]}


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


def markdown(games):
    out = ['# Setup report', '',
           'Sites: coord (planet type, terraform steps from home; Gaia/Transdim off the ring), Q = needs a QIC, '
           'N = next to an opponent. Rank: no QIC, fewer steps, near opponent first.', '']
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
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__)
    run = Path(argv[0])
    games = [game_report(p) for p in sorted(run.glob('**/setup_state.json'))]
    (run/'setup_report.json').write_text(json.dumps({'games': games}, ensure_ascii=False, indent=1)+'\n')
    (run/'setup_report.md').write_text(markdown(games)+'\n')
    print(f'{len(games)} games -> {run/"setup_report.md"}')


if __name__ == '__main__':
    main()
