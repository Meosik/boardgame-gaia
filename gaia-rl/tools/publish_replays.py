"""Publish replays; show newest 24, prune older viewing files after 30 days."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time

VISIBLE_LIMIT = 24
RETENTION_SECONDS = 30 * 86400


def read_catalog(path):
    if path.is_symlink():
        raise ValueError(f'Refusing symlink: {path}')
    value = json.loads(path.read_text())
    if value.get('schema_version') != 1 or not isinstance(value.get('games'), list):
        raise ValueError(f'Invalid catalog: {path}')
    ids, files = set(), set()
    for game in value['games']:
        if (not isinstance(game.get('id'), str) or not game['id']
                or not re.fullmatch(r'[a-z0-9_-]+\.json\.gz', game.get('file', ''))
                or game['id'] in ids or game['file'] in files):
            raise ValueError(f'Invalid or duplicate game: {path}')
        ids.add(game['id']); files.add(game['file'])
    return value['games']


def write_json(path, value):
    # Readers see either complete old JSON or complete new JSON, never a partial list.
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as f:
        temporary = Path(f.name)
        json.dump(value, f, indent=2)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_catalog(path, games):
    write_json(path, {'schema_version': 1, 'games': games})


def publish(source, destination, *, now=None):
    now = time.time() if now is None else now
    if not isinstance(now, (int, float)) or not math.isfinite(now) or now < 0:
        raise ValueError('Invalid publication time')
    if source.is_symlink() or destination.is_symlink():
        raise ValueError('Refusing symlink publication directory')
    incoming = read_catalog(source/'index.json')
    destination.mkdir(parents=True, exist_ok=True)
    lock = destination/'.publish.lock'
    # Single local publisher; do not allow competing index updates.
    with lock.open('x'):
        pass
    try:
        index = destination/'index.json'
        archive = destination/'archive-index.json'
        history = read_catalog(archive) if archive.exists() else (read_catalog(index) if index.exists() else [])
        times_path = destination/'publication-times.json'
        if times_path.is_symlink():
            raise ValueError('Refusing symlink publication times')
        times = json.loads(times_path.read_text()) if times_path.exists() else {}
        if not isinstance(times, dict) or any(
                not isinstance(value, (int, float)) or isinstance(value, bool)
                or not math.isfinite(value) or value < 0 for value in times.values()):
            raise ValueError('Invalid publication times')
        # Legacy dates are unknown. Start their clock now; never use copied mtimes.
        for game in history:
            times.setdefault(game['id'], now)
        by_id = {g['id']: g for g in history}
        by_file = {g['file']: g for g in history}
        payloads = {}
        for game in incoming:
            if game['id'] in times and game['id'] not in by_id:
                raise ValueError(f'Replay already expired; use a new run: {game["id"]}')
            if (source/game['file']).is_symlink() or (destination/game['file']).is_symlink():
                raise ValueError('Refusing symlink replay payload')
            data = (source/game['file']).read_bytes()
            target = destination/game['file']
            if ((game['id'] in by_id and by_id[game['id']] != game)
                    or (game['file'] in by_file and by_file[game['file']] != game)
                    or (target.exists() and target.read_bytes() != data)):
                raise ValueError(f'Replay collision; originals preserved: {game["id"]}')
            payloads[game['file']] = data
        for game in history:
            if (destination/game['file']).is_symlink():
                raise ValueError('Refusing symlink archived replay')
            if not (destination/game['file']).is_file():
                raise ValueError(f'Missing archived replay: {game["file"]}')
        # All collision/missing-file checks precede writes. Never overwrite replay files.
        for filename, data in payloads.items():
            target = destination/filename
            if not target.exists():
                with target.open('xb') as f:
                    f.write(data)
        # A repeat publication does not promote an old batch above newer games.
        fresh = [g for g in incoming if g['id'] not in by_id]
        for game in fresh:
            times[game['id']] = now
        combined = fresh + history
        expired = [g for g in combined[VISIBLE_LIMIT:]
                   if now - times[g['id']] > RETENTION_SECONDS]
        expired_ids = {g['id'] for g in expired}
        retained = [g for g in combined if g['id'] not in expired_ids]
        # Publish references before deleting files; never prune unlisted files or run data.
        write_catalog(archive, retained)
        write_catalog(index, retained[:VISIBLE_LIMIT])
        write_json(times_path, times)
        for game in expired:
            (destination/game['file']).unlink()
        return len(retained[:VISIBLE_LIMIT]), len(retained)
    finally:
        lock.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    visible, total = publish(args.source, args.destination)
    print(f'{visible} visible; {total} retained. Viewing retention: 30 days, newest 24 protected.')


if __name__ == '__main__':
    main()
