"""Freeze this local experiment and serve it separately from ongoing matches."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time


def free_port(port):
    with socket.socket() as probe:
        # Match HTTPServer's restart behavior: TIME_WAIT is not a live owner.
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(('127.0.0.1', port))


def freeze(destination):
    from gaia_rl.versions import require_current_sources, runtime_versions
    from four_factions.provenance import hashes
    from four_factions.value import ROOT
    require_current_sources(ROOT)
    # BGS belongs to a different task. Neither copy nor inspect its implementation.
    sources = {name: digest for name, digest in hashes().items()
               if not name.startswith('gaia-rl/experiments/bgs_records/')}
    for name, expected in sources.items():
        data = (ROOT/name).read_bytes()
        if sha256(data).hexdigest() != expected:
            raise ValueError(f'Source changed during snapshot: {name}')
        target = destination/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    binaries = list((ROOT/'gaia-rl/python/gaia_rl').glob('_native*.so'))
    if len(binaries) != 1:
        raise ValueError('One installed native extension is required')
    binary = destination/'gaia-rl/python/gaia_rl'/binaries[0].name
    shutil.copy2(binaries[0], binary)
    return {'versions': runtime_versions(), 'source_hashes': sources,
            'native_sha256': sha256(binary.read_bytes()).hexdigest()}


def main():
    from four_factions.value import ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--runtime-coaching', type=Path,
                        help='Explicit, hash-recorded coaching service overlay; frozen teacher stays unchanged')
    parser.add_argument('--port', type=int, default=8789)
    parser.add_argument('--ui-port', type=int, default=5174)
    args = parser.parse_args()
    free_port(args.port)
    free_port(args.ui_port)
    output = args.output.resolve()
    if args.resume and not args.runtime_coaching and (output/'launch.json').exists():
        previous_overlay = json.loads((output/'launch.json').read_text()).get('runtime_coaching')
        if previous_overlay:
            args.runtime_coaching = Path(previous_overlay)
    frozen = output/'execution-snapshot'
    if args.resume:
        receipt = json.loads((output/'source-receipt.json').read_text())
        for name, expected in receipt['source_hashes'].items():
            if sha256((frozen/name).read_bytes()).hexdigest() != expected:
                raise ValueError(f'Frozen source changed: {name}')
        binaries = list((frozen/'gaia-rl/python/gaia_rl').glob('_native*.so'))
        if len(binaries) != 1 or sha256(binaries[0].read_bytes()).hexdigest() != receipt['native_sha256']:
            raise ValueError('Frozen native extension changed')
    else:
        output.mkdir(parents=True, exist_ok=False)
        receipt = freeze(frozen)
        (output/'source-receipt.json').write_text(json.dumps(receipt, indent=2))
    env = {**os.environ, 'PYTHONPATH': os.pathsep.join(str(frozen/p) for p in
           ('gaia-rl/python', 'gaia-rl/experiments', 'gaia-rl/tools'))}
    runtime_sources = None
    if args.runtime_coaching:
        overlay = args.runtime_coaching.resolve()
        runtime_sources = json.loads((overlay/'receipt.json').read_text())
        for name, expected in runtime_sources.items():
            if sha256((overlay/name).read_bytes()).hexdigest() != expected:
                raise ValueError(f'Coaching service overlay changed: {name}')
        env['PYTHONPATH'] = str(overlay)+os.pathsep+env['PYTHONPATH']
    processes = []
    streams = []
    def stop(*_):
        for process in processes:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
        for process in processes:
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        commands = [([sys.executable, '-m', 'coaching.server', '--session', str(output/'game'),
                     '--port', str(args.port), '--ui-port', str(args.ui_port)], frozen/'gaia-rl', env, 'api.log'),
                    (['node', 'serve-coach.mjs'], ROOT/'gaia-frontend',
                     {**os.environ, 'COACH_API_PORT': str(args.port), 'COACH_UI_PORT': str(args.ui_port)}, 'ui.log')]
        for command, cwd, environment, log in commands:
            stream = (output/log).open('a')
            streams.append(stream)
            processes.append(subprocess.Popen(command, cwd=cwd, env=environment, stdin=subprocess.DEVNULL,
                                              stdout=stream, stderr=subprocess.STDOUT, start_new_session=True))
        (output/'launch.json').write_text(json.dumps({'launcher_pid': os.getpid(),
            'api_pid': processes[0].pid, 'ui_pid': processes[1].pid,
            'url': f'http://localhost:{args.ui_port}/?aiCoach=1', 'source_frozen': True,
            'runtime_coaching': str(args.runtime_coaching.resolve()) if args.runtime_coaching else None,
            'runtime_sources': runtime_sources}, indent=2))
        print(f'http://localhost:{args.ui_port}/?aiCoach=1 · {output}', flush=True)
        while all(p.poll() is None for p in processes):
            time.sleep(1)
        raise RuntimeError('A coaching service exited; inspect api.log/ui.log. The saved game is preserved.')
    finally:
        stop()
        for stream in streams:
            stream.close()


if __name__ == '__main__':
    main()
