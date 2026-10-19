"""Behaviour-cloning data from teacher games, for the first PPO stage (user 2026-10-20 "데이터 도구 만들어 놓고").

Every lab/teacher_ab game keeps its seed and the index chosen at each decision (decisions.jsonl.gz), so a
game is replayed instead of stored state by state. Three commands:

  index   RUNS [--glob 'lab-*'] --out lab/bc/manifest.jsonl
          one line per complete game: run, game dir, seed, factions, A seats, teacher spec per seat, final
          scores, rounds played, decisions, the run's engine build, and whether it still replays on the
          current engine (a quick replay without snapshots).
  stats   MANIFEST
          games / decisions per faction and teacher, 6-round games, games that no longer replay.
  export  MANIFEST --out DIR [--shard 2000] [--max N] [--only-6r] [--teacher SUBSTRING]
          replays the games and writes compressed npz shards of encoded samples: observation (float16),
          the legal candidates' features (ragged: cand + cand_offsets), chosen index, seat, faction id,
          round, and the seat's final score minus the table mean (value target; NaN for games that stopped
          before round 6). Uses gaia_rl.encoding.FeatureEncoder, so features match the RL environment.

Training code can also call iter_samples(manifest) directly (one replay at a time, nothing written).
Caution: the log holds indices only, so a game must be replayed on an engine whose legal candidates match
the one that played it. 'replays' only proves the indices stay in range; after an engine change that
alters legality (2026-10-19/20: Lost Fleet Advanced Tech side and order), filter on engine_build_id or
re-index on the engine the games were played with. 2026-10-20 index of all lab runs: 927 games, 781 replay,
341 six-round, 151 233 decisions — almost all Xenos/Terrans/Taklons/Geodens (683–733 seat-games each),
the other base factions 14–50, Lost Fleet none yet (088 adds them).
Only decisions of seats played by a teacher are kept (all seats in lab games). A game that no longer
replays on the current engine is skipped; the index records why.
"""
import argparse
import gzip
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(ROOT/'python'), str(ROOT/'tools')]

FACTIONS = ('Terrans', 'Lantids', 'Xenos', 'Gleens', 'Taklons', 'Ambas', 'HadschHallas', 'Ivits', 'Geodens',
            'BalTaks', 'Firaks', 'Bescods', 'Nevlas', 'Itars', 'Moweyds', 'SpaceGiants', 'Tinkeroids', 'Darkanians')
LAST_ROUND = 6


def _rows(game_dir):
    with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
        return [json.loads(line) for line in f]


def _replays(seed, rows):
    from gaia_rl import Environment
    env = Environment(seed, 2000)
    try:
        for row in rows:
            env.step(row['decision_id'], row['index'])
    except Exception as error:
        return False, str(error)[:200], None
    return True, '', json.loads(env.snapshot_json())['state']['round']


def cmd_index(args):
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out.open('w') as f:
        for run in sorted(Path(args.runs).expanduser().glob(args.glob)):
            manifest = run/'manifest.json'
            if not manifest.exists():
                continue
            meta = json.loads(manifest.read_text())
            teachers = meta.get('teachers') or {}
            for game_dir in sorted(run.glob('pair-*/game-*')):
                result_file = game_dir/'result.json'
                if not result_file.exists() or not (game_dir/'decisions.jsonl.gz').exists():
                    continue
                result = json.loads(result_file.read_text())
                if not result.get('complete'):
                    continue
                rows = _rows(game_dir)
                ok, why, last_round = _replays(result['seed'], rows)
                a_seats = result.get('a_seats', [])
                record = {
                    'run': run.name, 'game': str(game_dir), 'seed': result['seed'], 'factions': result['factions'],
                    'a_seats': a_seats,
                    'teachers': [json.dumps(teachers.get('A' if s in a_seats else 'B'), sort_keys=True)[:300]
                                 for s in range(len(result['factions']))],
                    'scores': [result.get('scores', {}).get(str(s)) for s in range(len(result['factions']))],
                    'decisions': len(rows), 'last_round': last_round,
                    'full_game': bool(ok and last_round == LAST_ROUND),
                    'engine_build_id': (meta.get('versions') or {}).get('engine_build_id'),
                    'replays': ok, 'replay_error': why,
                }
                f.write(json.dumps(record, ensure_ascii=False)+'\n')
                n += 1
    print(f'{n} games indexed -> {out}')


def _load(manifest):
    with open(manifest) as f:
        return [json.loads(line) for line in f if line.strip()]


def cmd_stats(args):
    games = _load(args.manifest)
    ok = [g for g in games if g['replays']]
    seats, decisions = Counter(), 0
    for g in ok:
        decisions += g['decisions']
        for faction in g['factions']:
            seats[faction] += 1
    print(f"games {len(games)}, replay on this engine {len(ok)}, 6-round {sum(g['full_game'] for g in ok)}, "
          f'decisions {decisions}')
    print('seat-games per faction: ' + ', '.join(f'{k} {v}' for k, v in seats.most_common()))
    broken = Counter(g['run'] for g in games if not g['replays'])
    if broken:
        print('no longer replay: ' + ', '.join(f'{k} {v}' for k, v in broken.most_common()))


def iter_samples(manifest, only_6r=False, teacher=None, encoder=None):
    """Yield one dict per decision of the indexed games (see the module docstring)."""
    import numpy as np
    from gaia_rl import Environment
    from gaia_rl.encoding import FeatureEncoder
    encoder = encoder or FeatureEncoder()
    for game in (_load(manifest) if isinstance(manifest, (str, Path)) else manifest):
        if not game['replays'] or (only_6r and not game['full_game']):
            continue
        scores = game['scores']
        full = game['full_game'] and all(s is not None for s in scores)
        mean = sum(scores)/len(scores) if full else math.nan
        env = Environment(game['seed'], 2000)
        for row in _rows(Path(game['game'])):
            snapshot = json.loads(env.snapshot_json())
            seat = snapshot.get('player')
            if seat is not None and (teacher is None or teacher in game['teachers'][seat]):
                encoded = encoder.encode(snapshot, seat)
                n = len(snapshot['candidates'])
                yield {'observation': encoded['observation'].astype(np.float16),
                       'candidates': encoded['candidates'][:n].astype(np.float16),
                       'chosen': row['index'], 'seat': seat,
                       'faction': FACTIONS.index(game['factions'][seat]),
                       'round': snapshot['state'].get('round', 0),
                       'value': (scores[seat]-mean) if full else math.nan,
                       'seed': game['seed']}
            env.step(row['decision_id'], row['index'])


def cmd_export(args):
    import numpy as np
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    buffer, shard, total = [], 0, 0

    def flush():
        nonlocal buffer, shard
        if not buffer:
            return
        counts = np.array([len(s['candidates']) for s in buffer])
        np.savez_compressed(
            out/f'shard-{shard:05d}.npz',
            observation=np.stack([s['observation'] for s in buffer]),
            cand=np.concatenate([s['candidates'] for s in buffer]),
            cand_offsets=np.concatenate([[0], np.cumsum(counts)]),
            chosen=np.array([s['chosen'] for s in buffer]), seat=np.array([s['seat'] for s in buffer]),
            faction=np.array([s['faction'] for s in buffer]), round=np.array([s['round'] for s in buffer]),
            value=np.array([s['value'] for s in buffer], dtype=np.float32))
        shard += 1
        buffer = []
    for sample in iter_samples(args.manifest, only_6r=args.only_6r, teacher=args.teacher):
        buffer.append(sample)
        total += 1
        if len(buffer) >= args.shard:
            flush()
        if args.max and total >= args.max:
            break
    flush()
    print(f'{total} samples in {shard} shards -> {out}')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('index')
    p.add_argument('runs')
    p.add_argument('--glob', default='lab-*')
    p.add_argument('--out', default=str(ROOT/'lab'/'bc'/'manifest.jsonl'))
    p = sub.add_parser('stats')
    p.add_argument('manifest')
    p = sub.add_parser('export')
    p.add_argument('manifest')
    p.add_argument('--out', required=True)
    p.add_argument('--shard', type=int, default=2000)
    p.add_argument('--max', type=int, default=0)
    p.add_argument('--only-6r', action='store_true')
    p.add_argument('--teacher')
    args = parser.parse_args()
    {'index': cmd_index, 'stats': cmd_stats, 'export': cmd_export}[args.cmd](args)


if __name__ == '__main__':
    main()
