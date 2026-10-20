"""Scan seed numbers for the lab's fixed lineups and append the hits to lab/seeds-*.txt.

The faction draw depends on the whole seed string, so each lineup is scanned under its own prefix
(quartet-a-N, quartet-b-N, ...). The lineup of a file is read from its first seed, so the files are the
only lineup table. About 5 ms a seed, one hit in about 2000 (user 2026-10-20 "시드 미리 많이 만들어둬").

  .venv/bin/python tools/scan_seeds.py --start 60000 --count 200000 --jobs 4 --out runs/scan-seeds/metrics.json
  .venv/bin/python tools/scan_seeds.py --files lab/seeds-quartet-b.txt --start 60000 --count 20000
"""
import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(ROOT/'python')]

FILES = ('lab/seeds-quartet-a.txt', 'lab/seeds-quartet-b.txt', 'lab/seeds-quartet-c.txt',
         'lab/seeds-quartet-d.txt', 'lab/seeds-quartet-e.txt', 'lab/seeds-live-quartet.txt')
CHUNK = 2000


def lineup(seed):
    from gaia_rl import Environment
    return frozenset(p['faction'] for p in json.loads(Environment(seed, 2000).snapshot_json())['state']['players'])


def existing(path):
    return [line.strip() for line in path.read_text().splitlines() if line.strip() and not line.startswith('#')]


def scan_chunk(args):
    prefix, want, start, stop = args
    want = frozenset(want)
    return [f'{prefix}-{n}' for n in range(start, stop) if lineup(f'{prefix}-{n}') == want]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--files', nargs='*', default=list(FILES))
    parser.add_argument('--start', type=int, default=60000)
    parser.add_argument('--count', type=int, default=200000)
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--out', default=None, help='metrics json (seeds added per file)')
    args = parser.parse_args()
    added = {}
    with ProcessPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        for name in args.files:
            path = ROOT/name
            seeds = existing(path)
            if not seeds:
                print(f'{name}: no seed to read the lineup from, skipped')
                continue
            prefix = seeds[0].rsplit('-', 1)[0]
            want = sorted(lineup(seeds[0]))
            known = set(seeds)
            tasks = [(prefix, want, s, min(s+CHUNK, args.start+args.count))
                     for s in range(args.start, args.start+args.count, CHUNK)]
            hits = [seed for chunk in pool.map(scan_chunk, tasks) for seed in chunk if seed not in known]
            if hits:
                with path.open('a') as f:
                    f.write(''.join(h+'\n' for h in hits))
            added[name] = len(hits)
            print(f'{name}: {prefix} {want} +{len(hits)} ({args.start}-{args.start+args.count})')
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({'added': added, 'start': args.start, 'count': args.count}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
