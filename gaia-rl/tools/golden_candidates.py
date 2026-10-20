"""Golden candidate lists of recorded lab games: dump them with one engine build, compare with another.

The engine's candidate order is the JSON-string order of `ai_decisions_with_diagnostics` (BTreeMap by
serde_json string), and recorded games replay by candidate `index`, so any engine change made for speed
(E58: reach memo, validation) must leave every decision's candidate list byte-identical. `dump` replays
each recorded game (engine only, no teacher) and writes, per decision, the candidate list as the engine
serializes it; `compare` replays the same games with the current build and reports the first differing
decision per game. Replay stops at the first mismatch for that game (later indices would be meaningless).

  .venv/bin/python tools/golden_candidates.py dump  --games RUN_DIR/pair-*/game-* --out runs/golden-candidates
  .venv/bin/python tools/golden_candidates.py compare --golden runs/golden-candidates [--metrics runs/golden-candidates/metrics.json]

Golden files: <out>/<run>__<pair>__<game>.jsonl.gz, one line per decision
  {"step": n, "decision_id": d, "player": p, "n": len, "candidates": "<json string of the list>"}
plus <out>/index.json (game dir → golden file, engine build id).
"""
import argparse
import gzip
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(ROOT/'python'), str(ROOT/'tools')]


def decisions(game_dir):
    with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as handle:
        for line in handle:
            yield json.loads(line)


def candidate_text(env):
    snapshot = json.loads(env.snapshot_json())
    return (snapshot['decision_id'], snapshot.get('player'),
            json.dumps(snapshot['candidates'], separators=(',', ':'), sort_keys=False))


def golden_name(game_dir):
    game_dir = Path(game_dir).resolve()
    return f'{game_dir.parents[1].name}__{game_dir.parent.name}__{game_dir.name}.jsonl.gz'


def dump(args):
    from gaia_rl import Environment
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    index = {'engine_build_id': None, 'games': {}}
    total = 0
    for game in args.games:
        game_dir = Path(game).expanduser()
        result = json.loads((game_dir/'result.json').read_text())
        env = Environment(result['seed'], 2000)
        if index['engine_build_id'] is None:
            index['engine_build_id'] = json.loads(env.snapshot_json()).get('engine_build_id')
        name = golden_name(game_dir)
        rows = 0
        with gzip.open(out/name, 'wt') as handle:
            for step, row in enumerate(decisions(game_dir)):
                decision_id, player, text = candidate_text(env)
                handle.write(json.dumps({'step': step, 'decision_id': decision_id, 'player': player,
                                         'n': text.count('{"phase"'), 'sha256': hashlib.sha256(text.encode()).hexdigest(),
                                         'candidates': text})+'\n')
                rows += 1
                env.step(row['decision_id'], row['index'])
        index['games'][str(game_dir)] = {'file': name, 'seed': result['seed'], 'decisions': rows}
        total += rows
        print(f'{name}: {rows} decisions', flush=True)
    (out/'index.json').write_text(json.dumps(index, indent=1, ensure_ascii=False)+'\n')
    print(f'{len(args.games)} games, {total} decisions → {out}')


def compare(args):
    from gaia_rl import Environment
    golden = Path(args.golden).expanduser()
    index = json.loads((golden/'index.json').read_text())
    report = {'golden_engine_build_id': index.get('engine_build_id'), 'engine_build_id': None,
              'games': {}, 'mismatched_games': 0, 'decisions': 0, 'seconds': 0.0}
    started = time.perf_counter()
    for game, entry in index['games'].items():
        game_dir = Path(game)
        env = Environment(entry['seed'], 2000)
        if report['engine_build_id'] is None:
            report['engine_build_id'] = json.loads(env.snapshot_json()).get('engine_build_id')
        mismatch = None
        checked = 0
        with gzip.open(golden/entry['file'], 'rt') as handle:
            for row, recorded in zip(handle, decisions(game_dir)):
                want = json.loads(row)
                decision_id, player, text = candidate_text(env)
                if text != want['candidates'] or decision_id != want['decision_id']:
                    mismatch = {'step': want['step'], 'decision_id': want['decision_id'],
                                'golden_n': want['n'], 'now_n': text.count('{"phase"'),
                                'first_difference': next((i for i, (a, b) in enumerate(zip(text, want['candidates']))
                                                          if a != b), min(len(text), len(want['candidates'])))}
                    break
                checked += 1
                env.step(recorded['decision_id'], recorded['index'])
        report['games'][game] = {'decisions': checked, 'mismatch': mismatch}
        report['decisions'] += checked
        if mismatch:
            report['mismatched_games'] += 1
            print(f'MISMATCH {entry["file"]} at step {mismatch["step"]}: {mismatch}', flush=True)
        else:
            print(f'ok {entry["file"]}: {checked} decisions', flush=True)
    report['seconds'] = round(time.perf_counter()-started, 1)
    report['identical'] = report['mismatched_games'] == 0
    if args.metrics:
        metrics = Path(args.metrics).expanduser()
        metrics.parent.mkdir(parents=True, exist_ok=True)
        metrics.write_text(json.dumps(report, indent=1, ensure_ascii=False)+'\n')
    print(f'{len(index["games"])} games, {report["decisions"]} decisions, mismatched games '
          f'{report["mismatched_games"]}, {report["seconds"]} s, engine {report["golden_engine_build_id"]} → '
          f'{report["engine_build_id"]}')
    return 0 if report['identical'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='mode', required=True)
    d = sub.add_parser('dump')
    d.add_argument('--games', nargs='+', required=True)
    d.add_argument('--out', required=True)
    c = sub.add_parser('compare')
    c.add_argument('--golden', required=True)
    c.add_argument('--metrics')
    args = parser.parse_args()
    if args.mode == 'dump':
        dump(args)
        return 0
    return compare(args)


if __name__ == '__main__':
    sys.exit(main())
