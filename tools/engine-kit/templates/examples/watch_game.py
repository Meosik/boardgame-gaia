"""Run your own local policy and spectate it; no game-server or model download."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import random
import shutil
import sys
import tempfile
import threading
import time
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'gaia-rl/tools'))

from gaia_rl import Environment
from gaia_rl.versions import require_current_sources, runtime_versions
from evaluation_replays import frame
from live_replays import LiveReplayWriter


def choose(snapshot: dict, rng: random.Random) -> int:
    """Replace this function with your policy; every seat uses it in this demo."""
    return rng.randrange(len(snapshot['candidates']))


def play(seed: str, site: Path, max_steps: int = 10000) -> dict:
    env = Environment(seed, max_steps)
    rng = random.Random(seed)
    snapshot = json.loads(env.snapshot_json())
    writer = LiveReplayWriter(site / 'ai-live', str(site))
    replay = {'schema_version': 1, 'metadata': {
        'seed': seed, 'policy': 'uniform-random', 'focus_player': 0,
        'faction': snapshot['state']['players'][0]['faction'], 'steps': 0,
        'versions': runtime_versions()}, 'frames': [frame(snapshot)], 'events': []}
    writer.write(replay)
    published = time.monotonic()
    try:
        while not env.is_terminal():
            index = choose(snapshot, rng)
            if type(index) is not int or not 0 <= index < len(snapshot['candidates']):
                raise ValueError('Policy returned an invalid candidate index')
            before = snapshot
            env.step(before['decision_id'], index)
            snapshot = json.loads(env.snapshot_json())
            replay['frames'].append(frame(snapshot, before['player'],
                before['candidates'][index]['action'], before['candidates']))
            if not env.is_terminal() and time.monotonic() - published >= 0.5:
                writer.write(replay)
                published = time.monotonic()
        replay['metadata']['scores'] = {str(k): v for k, v in env.final_scores()}
        writer.write(replay, 'complete')
    except (Exception, KeyboardInterrupt):
        writer.write(replay, 'failed')
        raise
    return {'complete': True, 'steps': snapshot['steps'], 'scores': env.final_scores(),
            'engine_build_id': snapshot['engine_build_id'], 'seed': seed}


class LocalHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', default='engine-kit-example')
    parser.add_argument('--max-steps', type=int, default=10000)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--generate-only', action='store_true')
    args = parser.parse_args()
    require_current_sources(ROOT)
    binary = ROOT / 'gaia-rl/target/release/examples' / ('replay_income.exe' if os.name == 'nt' else 'replay_income')
    if not binary.is_file() or not (ROOT / 'gaia-frontend/dist/index.html').is_file():
        parser.error('Run setup_viewer.py first to build the viewer and income helper')
    os.environ['GAIA_REPLAY_INCOME_BIN'] = str(binary)
    runs = ROOT / 'runs'
    runs.mkdir(exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='watch-', dir=runs))
    site = run / 'site'
    shutil.copytree(ROOT / 'gaia-frontend/dist', site, ignore=shutil.ignore_patterns('ai-live'))
    server = None
    status = 0
    try:
        if not args.generate_only:
            server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(LocalHandler, directory=str(site)))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            url = f'http://127.0.0.1:{args.port}/'
            print(f'Viewer: {url}\nRecording: {run}', flush=True)
            if not args.no_browser:
                webbrowser.open(url)
        try:
            result = play(args.seed, site, args.max_steps)
            (run / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
            print(json.dumps({**result, 'recording': str(run)}), flush=True)
        except Exception as error:
            (run / 'failure.json').write_text(json.dumps({'error': str(error)}) + '\n')
            print(f'Game failed; last real prefix retained: {error}', file=sys.stderr, flush=True)
            status = 1
        if server is not None:
            print('Viewer remains available. Ctrl+C to stop. No background training is running.', flush=True)
            threading.Event().wait()
    except KeyboardInterrupt:
        print('\nStopped. Recorded prefix remains on disk.', flush=True)
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
    raise SystemExit(status)


if __name__ == '__main__':
    main()
