"""List one seat's moves in a published replay with resources after each move.

  .venv/bin/python tools/replay_moves.py <replay.json.gz> <seat> [--rounds 1-3]

Shows ore/credits/knowledge/QIC and power bowls after the move, so a pass with resources left
or a chain of conversions can be read at a glance.
"""
import argparse
import gzip
import json


def resources(player):
    res = player['resources']
    power = res['power']
    return ('o%d c%d k%d q%d p%d/%d/%d' % (res['ore'], res['credits'], res['knowledge'], res['qic'],
                                           power['bowl1'], power['bowl2'], power['bowl3']))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('replay')
    parser.add_argument('seat', type=int)
    parser.add_argument('--rounds', default='0-6')
    args = parser.parse_args()
    low, high = (int(x) for x in args.rounds.split('-'))
    frames = json.load(gzip.open(args.replay, 'rt'))['frames']
    for k in range(1, len(frames)):
        frame = frames[k]
        state = frame['state']
        if frame['player'] != args.seat or not low <= state['round'] <= high:
            continue
        action = frame['action'] if isinstance(frame['action'], dict) else {'type': str(frame['action'])}
        if action['type'] == 'ChargePower':
            continue
        detail = {key: value for key, value in action.items() if key in ('kind', 'count', 'coord', 'track', 'id', 'to')}
        print('%3d R%d %-28s %-34s %s -> %s' % (
            k, state['round'], action['type'], json.dumps(detail, ensure_ascii=False)[:34],
            resources(frames[k-1]['state']['players'][args.seat]), resources(state['players'][args.seat])))


if __name__ == '__main__':
    main()
