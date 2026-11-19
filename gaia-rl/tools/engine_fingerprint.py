"""One hash of the engine inputs that are built into the server image's native module.

The same function is used on a folder (the Docker build) and on a git commit (teacher_version.py),
so the two can be compared.

  engine_fingerprint.py FOLDER          print the fingerprint of the folder
  engine_fingerprint.py --commit REV    print the fingerprint of a commit of this repository
"""
import argparse
import hashlib
import io
import os
import subprocess
import tarfile
from pathlib import Path

ENGINE_PATHS = ['gaia-engine/Cargo.toml', 'gaia-engine/src', 'gaia-engine/data',
                'gaia-rl/Cargo.toml', 'gaia-rl/Cargo.lock', 'gaia-rl/build.rs', 'gaia-rl/pyproject.toml',
                'gaia-rl/src', 'gaia-rl/python']   # exactly what the ai-builder stage of gaia-server/Dockerfile copies
SKIP_DIRS = {'__pycache__', 'target'}
SKIP_SUFFIXES = ('.pyc', '.pyo', '.so', '.pyd')    # build leftovers, never in git


def counted(rel):
    parts = str(rel).split('/')
    if any(p in SKIP_DIRS for p in parts):
        return False
    return not str(rel).endswith(SKIP_SUFFIXES)


def combine(digests):
    h = hashlib.sha256()
    for rel in sorted(digests):
        h.update(f'{digests[rel]}  {rel}\n'.encode())
    return h.hexdigest()


def of_folder(root):
    root = Path(root)
    digests = {}
    for path in ENGINE_PATHS:
        p = root / path
        if p.is_file():
            files = [p]
        elif p.is_dir():
            files = [Path(d) / f for d, _, names in os.walk(p) for f in names]
        else:
            continue
        for f in files:
            rel = f.relative_to(root).as_posix()
            if f.is_file() and counted(rel):
                digests[rel] = hashlib.sha256(f.read_bytes()).hexdigest()
    return combine(digests)


def of_commit(repo, commit):
    paths = [p for p in ENGINE_PATHS
             if subprocess.run(['git', 'cat-file', '-e', f'{commit}:{p}'], cwd=repo,
                               capture_output=True).returncode == 0]
    if not paths:
        return combine({})
    r = subprocess.run(['git', 'archive', '--format=tar', commit, '--', *paths], cwd=repo, capture_output=True)
    if r.returncode != 0:
        raise SystemExit(r.stderr.decode(errors='replace').strip() or 'git archive failed')
    digests = {}
    with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tf:
        for m in tf:
            if m.isfile() and counted(m.name):
                digests[m.name] = hashlib.sha256(tf.extractfile(m).read()).hexdigest()
    return combine(digests)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('folder', nargs='?')
    ap.add_argument('--commit')
    args = ap.parse_args(argv)
    if bool(args.folder) == bool(args.commit):
        ap.error('give exactly one of FOLDER or --commit COMMIT')
    if args.commit:
        print(of_commit(Path(__file__).resolve().parents[2], args.commit))
    else:
        print(of_folder(args.folder))


if __name__ == '__main__':
    main()
