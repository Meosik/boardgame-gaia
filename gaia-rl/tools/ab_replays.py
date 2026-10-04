"""Turn teacher_ab / lab games into browser replays (the existing `/?aiReplay=1` viewer).

A teacher_ab game directory holds result.json (seed, factions, A seats, final scores) and
decisions.jsonl.gz (every decision id and chosen index). The game is replayed in the engine,
each state recorded, and the final scores checked against result.json; a mismatch exports
nothing. The policy label names the experiment and which seats were A and B.

  # list the games of a run with seats, factions, arms and scores
  .venv/bin/python tools/ab_replays.py list runs/lab-027-search4-cap10

  # export chosen games, then add them to the site's replay catalog
  .venv/bin/python tools/ab_replays.py export runs/lab-027-search4-cap10/pair-003/game-1-A02 \
      --output /tmp/ab-replays [--focus best|worst|A|B|0-3]
  .venv/bin/python tools/publish_replays.py --source /tmp/ab-replays \
      --destination ../gaia-frontend/public/ai-replays

Run with GAIA_ENGINE_FIXES_2=1 and PYTHONPATH=python:tools, as the games were played.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re

from evaluation_replays import frame, validate_replay
from publish_replays import write_catalog
from replay_log import add_decision_log


def game_info(game_dir):
    result = json.loads((game_dir/'result.json').read_text())
    if not result.get('complete'):
        raise ValueError(f'{game_dir}: game did not finish')
    return result


def arm(result, seat):
    return 'A' if seat in result['a_seats'] else 'B'


def cmd_list(args):
    for game_dir in sorted(Path(args.run).glob('pair-*/game-*')):
        try:
            result = game_info(game_dir)
        except (OSError, ValueError):
            continue
        seats = ', '.join(f"{seat}:{faction}({arm(result, seat)}) {result['scores'][str(seat)]}"
                          for seat, faction in enumerate(result['factions']))
        print(f"{game_dir.relative_to(args.run)}  {result['seed']}  {seats}")


def focus_seat(result, focus):
    scores = {seat: result['scores'][str(seat)] for seat in range(4)}
    if focus in ('A', 'B'):
        candidates = [s for s in range(4) if arm(result, s) == focus]
        return max(candidates, key=lambda s: scores[s])
    if focus == 'worst':
        return min(scores, key=scores.get)
    if focus == 'best':
        return max(scores, key=scores.get)
    seat = int(focus)
    if seat not in range(4):
        raise ValueError('--focus seat must be 0-3')
    return seat


def replay_game(game_dir, focus, label):
    from gaia_rl import Environment
    result = game_info(game_dir)
    env = Environment(result['seed'], 2000)
    snapshot = json.loads(env.snapshot_json())
    frames = [frame(snapshot)]
    with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as rows:
        for line in rows:
            row = json.loads(line)
            if row['decision_id'] != snapshot['decision_id']:
                raise ValueError(f'{game_dir}: replay diverged at decision {snapshot["decision_id"]}')
            actor, before = snapshot['player'], snapshot
            env.step(row['decision_id'], row['index'])
            snapshot = json.loads(env.snapshot_json())
            frames.append(frame(snapshot, actor, before['candidates'][row['index']]['action'],
                                before['candidates']))
    scores = {str(k): v for k, v in env.final_scores()}
    if not env.is_terminal() or scores != result['scores']:
        raise ValueError(f'{game_dir}: replay does not reproduce the recorded final scores')
    seat = focus_seat(result, focus)
    # The viewer requires the engine versions; teacher_ab's manifest records those of the match.
    manifest = game_dir.parents[1]/'manifest.json'
    if manifest.exists():
        versions = json.loads(manifest.read_text())['versions']
    else:
        from gaia_rl.versions import runtime_versions
        versions = runtime_versions()
    a_seats = ','.join(map(str, result['a_seats']))
    replay = {'schema_version': 1, 'metadata': {
        'seed': result['seed'], 'focus_player': seat,
        'faction': result['factions'][seat],
        'policy': f'{label} · {arm(result, seat)}팔 (A 좌석 {a_seats})',
        'versions': versions, 'scores': scores, 'steps': snapshot['steps'], 'reproduced_original': True,
        'source': str(game_dir)}, 'frames': frames, 'events': []}
    replay = add_decision_log(replay)
    validate_replay(replay)
    return replay


def cmd_export(args):
    output = Path(args.output)
    if output.exists():
        raise SystemExit(f'{output} exists; choose a new directory')
    replays = [(Path(g), replay_game(Path(g), args.focus, args.label or Path(g).parents[1].name))
               for g in args.games]
    output.mkdir(parents=True)
    catalog = []
    for game_dir, replay in replays:
        meta = replay['metadata']
        payload = json.dumps(replay, separators=(',', ':'), ensure_ascii=False).encode()
        # The content hash in the name gives a regenerated replay a new URL, so no browser or
        # CDN copy of an earlier version can be served in its place.
        digest = hashlib.sha256(payload).hexdigest()[:8]
        name = re.sub(r'[^a-z0-9_-]+', '-',
                      f"ab-{game_dir.parents[1].name}-{game_dir.parent.name}-{game_dir.name}-{digest}".lower())
        (output/f'{name}.json.gz').write_bytes(gzip.compress(payload, mtime=0))
        catalog.append({'id': name, 'file': f'{name}.json.gz', 'policy': meta['policy'],
                        'faction': meta['faction'], 'seed': meta['seed'],
                        'vp': meta['scores'][str(meta['focus_player'])], 'steps': meta['steps']})
        print(f"{name}: {meta['faction']} seat {meta['focus_player']}, {catalog[-1]['vp']} VP, "
              f"{meta['steps']} decisions")
    write_catalog(output/'index.json', catalog)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    listing = sub.add_parser('list')
    listing.add_argument('run')
    export = sub.add_parser('export')
    export.add_argument('games', nargs='+')
    export.add_argument('--output', required=True)
    export.add_argument('--focus', default='best', help='best, worst, A, B or a seat 0-3')
    export.add_argument('--label', help='Replay policy label (default: the run directory name)')
    args = parser.parse_args()
    (cmd_list if args.command == 'list' else cmd_export)(args)


if __name__ == '__main__':
    main()
