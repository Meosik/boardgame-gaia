"""Preserve a game's original journal and resume a verified prefix separately."""
from hashlib import sha256
import json
from pathlib import Path
import shutil

from coaching.session import Session, write_new


def branch_session(source, destination, steps, environment_factory, teacher_factory):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    rows = sorted((source/'decisions').glob('*.json'))
    if type(steps) is not int or not 0 <= steps < len(rows):
        raise ValueError('Choose a recorded action to undo')
    if [p.name for p in rows] != [f'{i:06d}.json' for i in range(len(rows))]:
        raise ValueError('Discontinuous source history')
    target = json.loads(rows[steps].read_text())['before']
    files = [source/'session.json', *rows, *sorted((source/'suggestions').glob('*.json'))]
    if (source/'runtime-clock.json').exists():
        files.append(source/'runtime-clock.json')
    hashes = {str(p.relative_to(source)): sha256(p.read_bytes()).hexdigest() for p in files}
    destination.mkdir(parents=True, exist_ok=False)
    for name in hashes:
        path = Path(name)
        if path.parent.name == 'decisions' and int(path.stem) >= steps:
            continue
        if path.parent.name == 'suggestions' and int(path.stem) > steps:
            continue
        (destination/path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source/path, destination/path)
    manifest = json.loads((destination/'session.json').read_text())
    session = Session(destination, manifest['config'], environment_factory, teacher_factory)
    if session.current != target:
        raise ValueError('Native replay did not reproduce the undo position')
    if any(sha256((source/name).read_bytes()).hexdigest() != value for name, value in hashes.items()):
        raise ValueError('Source changed during branch verification')
    write_new(destination/'branch.json', {'schema': 1, 'source': str(source),
        'retained_actions': steps, 'original_recorded_actions': len(rows),
        'source_sha256': hashes, 'native_replay_verified': True,
        'later_actions_reapplied': False, 'training_performed': False})
    return session
