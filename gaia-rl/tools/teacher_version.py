"""Promote a teacher commit into a version folder and switch which version new AI rooms use.

The game server (gaia-server/src/ai.rs) reads GAIA_AI_TEACHERS_DIR, a folder outside the image:
  <version>/        mirrors the repository layout (<version>/gaia-rl/tools/ai_worker.py,
                    <version>/gaia-rl/baseline-teacher-20260917/, data folders) plus
                    <version>/teacher.json whose "factory" key is the teacher_patches factory name
  current           a text file with one line: the version name new AI rooms use
                    (missing or empty = the teacher built into the image)

Commands:
  add COMMIT --factory F   copy the teacher files of a commit into <dir>/<name>/ (never overwrites)
  use NAME                 write `current` (NAME 'builtin' clears it)
  list                     show the versions and the current one

A version carries only Python and data and runs on the engine module built into the image, so a
commit whose engine sources differ from the deployed commit needs a deploy instead; `add` refuses it.
Each version records the engine fingerprint of its commit (engine_fingerprint.py); the server (and
`use`) compare it with the deployed engine.
"""
import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
from datetime import date, datetime
from pathlib import Path

import engine_fingerprint

TEACHER_PATHS = ['gaia-rl/baseline-teacher-20260917', 'gaia-rl/tools',
                 'gaia-rl/research/strategy/bgg-openings-part2.csv',
                 'gaia-frontend/src/data', 'gaia-engine/data']          # what gaia-server/Dockerfile copies for the worker
ENGINE_PATHS = engine_fingerprint.ENGINE_PATHS  # built into the image
NAME = re.compile(r'^[A-Za-z0-9_-][A-Za-z0-9._-]*$')
RESERVED = {'current', 'builtin'}
WORKER = 'gaia-rl/tools/ai_worker.py'


def git(repo, *args, binary=False):
    r = subprocess.run(['git', *args], cwd=repo, capture_output=True)
    if r.returncode != 0:
        raise SystemExit(r.stderr.decode(errors='replace').strip() or f'git {args[0]} failed')
    return r.stdout if binary else r.stdout.decode().strip()


def deployed_commit(live_dir):
    if live_dir is None or not Path(live_dir).exists():
        return None
    try:
        return git(live_dir, 'rev-parse', 'HEAD')
    except SystemExit:
        return None


def add(repo, versions_dir, commit, factory, name=None, live_dir=None, force_engine=False, today=None):
    versions_dir = Path(versions_dir)
    full = git(repo, 'rev-parse', '--verify', commit + '^{commit}')
    if name is None:
        name = f'{today or date.today():%Y%m%d}-{full[:7]}'
    if not NAME.match(name) or name in RESERVED:
        raise SystemExit(f'bad version name: {name!r}')
    if (versions_dir / name).exists():
        raise SystemExit(f'version {name} already exists (versions are never overwritten)')

    text = git(repo, 'show', f'{full}:gaia-rl/tools/teacher_patches.py')
    if not re.search(rf'^def {re.escape(factory)}\(', text, re.M):
        raise SystemExit(f'factory {factory} is not defined in gaia-rl/tools/teacher_patches.py at {full[:7]}')

    fingerprint = engine_fingerprint.of_commit(repo, full)
    deployed = deployed_commit(live_dir)
    engine_same = None
    if deployed is None:
        if not force_engine:
            raise SystemExit(f'cannot read the deployed commit from {live_dir}; pass --force-engine to make the '
                             'version anyway (the server runs it only on an image built from the same engine)')
    else:
        engine_same = engine_fingerprint.of_commit(repo, deployed) == fingerprint
        if not engine_same and not force_engine:
            raise SystemExit(
                f'engine sources of {full[:7]} differ from the deployed commit {deployed[:7]}: '
                'this teacher needs a deploy. See: '
                f'git diff --stat {deployed[:7]} {full[:7]} -- gaia-engine gaia-rl/src gaia-rl/python')

    data = git(repo, 'archive', '--format=tar', full, '--', *TEACHER_PATHS, binary=True)
    versions_dir.mkdir(parents=True, exist_ok=True)
    tmp = versions_dir / f'.tmp-{name}'
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()
    with tarfile.open(fileobj=io.BytesIO(data)) as tf:
        tf.extractall(tmp, filter='data')
    if not (tmp / WORKER).is_file():
        shutil.rmtree(tmp)
        raise SystemExit(f'{WORKER} is missing in commit {full[:7]}')

    meta = {'name': name, 'commit': full, 'factory': factory,
            'created': datetime.now().astimezone().isoformat(timespec='seconds'),
            'deployed_commit': deployed, 'engine_same_as_deployed': engine_same,
            'engine_fingerprint': fingerprint}
    (tmp / 'teacher.json').write_text(json.dumps(meta, indent=2) + '\n')
    os.rename(tmp, versions_dir / name)
    return name


def use(versions_dir, name, repo=None, live_dir=None, force_engine=False):
    versions_dir = Path(versions_dir)
    if name == 'builtin':
        versions_dir.mkdir(parents=True, exist_ok=True)
        content = ''
    else:
        if not NAME.match(name) or not (versions_dir / name / WORKER).is_file():
            raise SystemExit(f'unknown version: {name!r}')
        try:
            meta = json.loads((versions_dir / name / 'teacher.json').read_text())
        except (OSError, ValueError):
            meta = {}
        fingerprint = meta.get('engine_fingerprint') if isinstance(meta, dict) else None
        if not fingerprint:
            raise SystemExit(f'version {name} has no engine fingerprint; the server will not run it')
        if repo is not None:
            deployed = deployed_commit(live_dir)
            if deployed is None:
                print(f'cannot read the deployed commit from {live_dir}; not compared '
                      '- the server checks the engine itself', file=sys.stderr)
            elif engine_fingerprint.of_commit(repo, deployed) != fingerprint and not force_engine:
                raise SystemExit(
                    f'version {name} was made for another engine than the deployed commit {deployed[:7]}: '
                    'the server would play new rooms with the image teacher. Deploy that engine first, '
                    'or pass --force-engine if that deploy is about to happen')
        content = name + '\n'
    tmp = versions_dir / '.current.tmp'
    tmp.write_text(content)
    os.replace(tmp, versions_dir / 'current')


def current(versions_dir):
    p = Path(versions_dir) / 'current'
    return p.read_text().strip() if p.is_file() else ''


def versions(versions_dir):
    out = []
    d = Path(versions_dir)
    if not d.is_dir():
        return out
    for p in sorted(d.iterdir()):
        if not NAME.match(p.name) or not (p / WORKER).is_file():
            continue
        try:
            meta = json.loads((p / 'teacher.json').read_text())
        except (OSError, ValueError):
            meta = {}
        out.append((p.name, meta))
    return out


def main(argv=None):
    default_dir = os.environ.get('GAIA_TEACHERS_DIR') or '~/gaia-teachers'
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('add')
    a.add_argument('commit')
    a.add_argument('--factory', required=True)
    a.add_argument('--name')
    a.add_argument('--dir', default=default_dir)
    a.add_argument('--live', default='~/gaia-live')
    a.add_argument('--force-engine', action='store_true')
    u = sub.add_parser('use')
    u.add_argument('name')
    u.add_argument('--dir', default=default_dir)
    u.add_argument('--live', default='~/gaia-live')
    u.add_argument('--force-engine', action='store_true')
    l = sub.add_parser('list')
    l.add_argument('--dir', default=default_dir)
    l.add_argument('--live', default='~/gaia-live')
    args = ap.parse_args(argv)
    vdir = Path(args.dir).expanduser()
    repo = Path(__file__).resolve().parents[2]
    if args.cmd == 'add':
        name = add(repo, vdir, args.commit, args.factory, name=args.name,
                   live_dir=Path(args.live).expanduser(), force_engine=args.force_engine)
        print(name)
        print(vdir / name)
        print(f'next: check it inside the container, then  teacher_version.py use {name}')
    elif args.cmd == 'use':
        use(vdir, args.name, repo=repo, live_dir=Path(args.live).expanduser(), force_engine=args.force_engine)
        what = 'the teacher built into the image' if args.name == 'builtin' else args.name
        print(f'new AI rooms use {what}; running games keep their version')
    else:
        cur = current(vdir)
        print(f'current: {cur or "builtin (image teacher)"}')
        live = Path(args.live).expanduser()
        deployed = deployed_commit(live)
        deployed_fp = engine_fingerprint.of_commit(repo, deployed) if deployed else None
        if deployed_fp:
            print(f'deployed engine: {deployed_fp[:12]} (commit {deployed[:7]})')
        else:
            print(f'deployed engine: unknown (cannot read {live})')
        for name, meta in versions(vdir):
            mark = '* ' if name == cur else '  '
            fp = meta.get('engine_fingerprint')
            state = '?' if not (deployed_fp and fp) else ('ok' if fp == deployed_fp else 'differs')
            print(f'{mark}{name} {meta.get("factory", "?")} {str(meta.get("commit", "?"))[:7]} '
                  f'{meta.get("created", "?")} engine {state}')


if __name__ == '__main__':
    main()
