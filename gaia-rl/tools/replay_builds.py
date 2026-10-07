"""List one seat's build moves in a published replay with planet type and ore/credit change.

  .venv/bin/python tools/replay_builds.py <replay.json.gz> <seat>
"""
import gzip
import json
import sys


def main():
    path, seat = sys.argv[1], int(sys.argv[2])
    frames = json.load(gzip.open(path, 'rt'))['frames']
    for k in range(1, len(frames)):
        frame = frames[k]
        action = frame['action'] if isinstance(frame['action'], dict) else {'type': str(frame['action'])}
        if frame['player'] != seat or not any(w in action['type'] for w in ('Build', 'Mine')):
            continue
        hexes = frame['state']['board']['hexes']
        if isinstance(hexes, dict):
            hexes = list(hexes.values())
        planet = None
        for h in hexes:
            if isinstance(h, dict) and h.get('coord') == action.get('coord'):
                planet = (h.get('planet') or {}).get('planet_type')
        before = frames[k-1]['state']['players'][seat]
        after = frame['state']['players'][seat]
        print(k, 'R%s' % frame['state']['round'], action.get('type'), action.get('coord'), planet,
              'ore %d->%d' % (before['resources']['ore'], after['resources']['ore']),
              'cr %d->%d' % (before['resources']['credits'], after['resources']['credits']),
              'tf', after['research_tracks']['terraforming'], 'booster', after['booster'])


if __name__ == '__main__':
    main()
