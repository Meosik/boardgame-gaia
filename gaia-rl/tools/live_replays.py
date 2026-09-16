"""Local, atomic live snapshots; never accepted by the completed replay publisher.

Transport/UI are separate. A crash leaves the last real prefix, not fake final
scores. Original revisions remain immutable while a reader may still fetch them.
"""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import os
import tempfile
import time

from replay_log import add_decision_log


def atomic_json(path, value):
    fd, temporary = tempfile.mkstemp(prefix='.live-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class LiveReplayWriter:
    def __init__(self, directory, identity):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=False)
        self.id = 'live-' + hashlib.sha256(identity.encode()).hexdigest()[:16]
        self.revision = 0
        self.status = 'running'
        self.frame_hashes = []
        self.identity = None

    def write(self, replay, status='running'):
        if status not in ('running', 'failed', 'complete'):
            raise ValueError('Unknown live status')
        if self.status != 'running':
            raise ValueError('A finished live recording cannot be resumed or rewritten')
        value = copy.deepcopy(replay)
        frames, meta = value['frames'], value['metadata']
        steps = len(frames)-1
        if steps < 0 or any(f['decision_id'] != i for i, f in enumerate(frames)):
            raise ValueError('Noncontiguous live prefix')
        identity = {k: meta[k] for k in ('seed', 'policy', 'faction', 'focus_player', 'versions')}
        frame_hashes = [hashlib.sha256(json.dumps({k: v for k, v in f.items() if k != 'event_end'},
                       sort_keys=True).encode()).hexdigest() for f in frames]
        if (self.identity is not None and identity != self.identity
                or frame_hashes[:len(self.frame_hashes)] != self.frame_hashes):
            raise ValueError('Live recordings must preserve their identity and append-only history')
        phase = frames[-1]['state']['phase']
        ended = isinstance(phase, dict) and 'Ended' in phase
        if (status == 'complete' and not ended) or (status == 'running' and ended):
            raise ValueError('Live completion must agree with the native terminal state')
        if status != 'complete':
            meta.pop('scores', None)
        meta.update(steps=steps, live_status=status, live_revision=self.revision)
        value = add_decision_log(value)
        if status == 'complete':
            from evaluation_replays import validate_replay
            validate_replay(value)
        filename = f'{self.id}-{self.revision}.json.gz'
        payload = gzip.compress(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode(), mtime=0)
        with (self.directory/filename).open('xb') as stream:
            stream.write(payload)
        game = {'id': self.id, 'file': filename, 'policy': meta['policy'], 'faction': meta['faction'],
                'seed': meta['seed'], 'steps': steps, 'vp': frames[-1]['state']['players'][meta['focus_player']]['vp'],
                'status': status, 'revision': self.revision, 'updated_at': time.time()}
        atomic_json(self.directory/'index.json', {'schema_version': 1, 'games': [game]})
        self.identity = identity
        self.frame_hashes = frame_hashes
        self.status = status
        self.revision += 1
        return game
