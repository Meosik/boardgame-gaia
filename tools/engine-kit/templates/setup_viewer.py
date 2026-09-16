"""Build the local spectator; downloads dependencies but never publishes anything."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main() -> None:
    npm = shutil.which('npm')
    if npm is None or shutil.which('cargo') is None:
        raise SystemExit('Install Node.js/npm and the Rust toolchain first. See VIEWER.md.')
    environment = dict(os.environ)
    environment.setdefault('CARGO_BUILD_JOBS', '1')
    for command, directory in (
        ([sys.executable, '-m', 'pip', 'install', './gaia-rl'], ROOT),
        (['cargo', 'build', '--locked', '--release', '--manifest-path', 'gaia-rl/Cargo.toml',
          '--example', 'replay_income'], ROOT),
        ([npm, 'ci'], ROOT / 'gaia-frontend'),
        ([npm, 'run', 'build'], ROOT / 'gaia-frontend'),
    ):
        subprocess.run(command, cwd=directory, env=environment, check=True)
    print(f'Installed. Run: "{sys.executable}" examples/watch_game.py')


if __name__ == '__main__':
    main()
