"""Publish a completed replay batch; keep all files/history, show newest 24 games."""
import argparse
import json
import os
from pathlib import Path
import re
import tempfile

VISIBLE_LIMIT = 24


def read_catalog(path):
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


def write_catalog(path, games):
    # Readers see either complete old JSON or complete new JSON, never a partial list.
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as f:
        temporary = Path(f.name)
        json.dump({'schema_version': 1, 'games': games}, f, indent=2)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def publish(source, destination):
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
        by_id = {g['id']: g for g in history}
        by_file = {g['file']: g for g in history}
        payloads = {}
        for game in incoming:
            data = (source/game['file']).read_bytes()
            target = destination/game['file']
            if ((game['id'] in by_id and by_id[game['id']] != game)
                    or (game['file'] in by_file and by_file[game['file']] != game)
                    or (target.exists() and target.read_bytes() != data)):
                raise ValueError(f'Replay collision; originals preserved: {game["id"]}')
            payloads[game['file']] = data
        for game in history:
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
        combined = fresh + history
        write_catalog(archive, combined)
        write_catalog(index, combined[:VISIBLE_LIMIT])
        return len(combined[:VISIBLE_LIMIT]), len(combined)
    finally:
        lock.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    visible, total = publish(args.source, args.destination)
    print(f'{visible} visible; {total} retained. No replay files deleted.')


if __name__ == '__main__':
    main()
