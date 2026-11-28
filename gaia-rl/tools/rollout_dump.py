"""Dump the failing frame of the teacher's rollout when it raises 'No eligible continuation'.

The error carries no state. This walks the traceback to the innermost `rollout` frame of
preparation.py and writes its locals (blocked seat, candidates with scores, remaining goal and the
full snapshot) to <directory>/no-continuation-<pid>-<time_ns>.json.gz. It never raises.
"""
import dataclasses
import gzip
import json
import os
import time
from pathlib import Path


def _plain(value):
    return dataclasses.asdict(value) if dataclasses.is_dataclass(value) and not isinstance(value, type) else repr(value)


def _frame(exc):
    found, tb = None, exc.__traceback__
    while tb is not None:
        code = tb.tb_frame.f_code
        if code.co_name == 'rollout' and code.co_filename.endswith('preparation.py'):
            found = tb.tb_frame
        tb = tb.tb_next
    return found


def dump_no_continuation(exc, directory):
    try:
        frame = _frame(exc)
        if frame is None:
            return None
        from current_actions.conservation import blocked
        local = frame.f_locals
        current, scores = local['current'], local['scores']
        candidates = []
        for i, candidate in enumerate(current['candidates']):
            score = scores[i] if i < len(scores) else None
            try:
                is_blocked = bool(blocked(score))
            except Exception:
                is_blocked = None
            candidates.append({'index': i, 'action': candidate['action'], 'score': repr(score), 'blocked': is_blocked})
        data = {'actor': local.get('actor'), 'step': local.get('step'), 'player': current['player'],
                'decision_id': current['decision_id'], 'round': current['state']['round'],
                'goal': _plain(local.get('goal')), 'remaining': _plain(local.get('remaining')),
                'candidates': candidates, 'current': current}
        path = Path(directory)/f'no-continuation-{os.getpid()}-{time.time_ns()}.json.gz'
        path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(path, 'wt') as handle:
            handle.write(json.dumps(data, default=repr))
        return str(path)
    except Exception:
        return None
