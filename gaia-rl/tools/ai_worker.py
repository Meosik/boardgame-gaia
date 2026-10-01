"""Live-play AI worker: one JSON request per stdin line, one JSON reply per stdout line.

The game server keeps a small pool of these processes and routes every room to the same
worker, so a teacher's plan memory survives between that room's decisions.

Request  {"op": "choose", "room": "AB12", "state": <GameState>, "player": 2, "level": "normal"}
Reply    {"ok": true, "decision": {"phase": "Game", "action": {...}}, "seconds": 1.4, ...}
         {"ok": false, "error": "..."}  (the server then falls back to its own legal move)
Request  {"op": "forget", "room": "AB12"}   drop that room's teacher memory
Request  {"op": "ping"}

Levels: "easy" = the frozen teacher's one-step ranking only; "normal" = 2 completed
comparisons at the next income boundary with a 5 s cap (cycle 016: +21.8 VP/seat over
easy without the cap, -3.8 for the cap). Run with
PYTHONPATH=python:baseline-teacher-20260917:tools from gaia-rl/.
"""
import json
import sys
import time
import traceback

LEVELS = {'easy': {'comparisons': 0, 'horizon_incomes': 2, 'max_seconds': None},
          'normal': {'comparisons': 2, 'horizon_incomes': 1, 'max_seconds': 5}}
MAX_ROOMS = 256


def main():
    # Patch before any teacher module is imported (see fast_teacher.install).
    import fast_teacher
    fast_teacher.install()
    import budget_teacher
    from gaia_rl import Environment
    from four_factions.timed import TimedPreparationTeacher

    teachers = {}
    out = sys.stdout
    sys.stdout = sys.stderr   # teacher prints must not corrupt the protocol stream

    def reply(value):
        out.write(json.dumps(value, allow_nan=False)+'\n')
        out.flush()

    for line in sys.stdin:
        started = time.monotonic()
        try:
            request = json.loads(line)
            op = request.get('op')
            if op == 'ping':
                reply({'ok': True, 'pong': True})
                continue
            if op == 'forget':
                teachers.pop(request['room'], None)
                reply({'ok': True})
                continue
            if op != 'choose':
                raise ValueError(f'unknown op {op!r}')
            level = LEVELS[request.get('level', 'normal')]
            # Budget settings are process-wide; set them for every request.
            budget_teacher.install(level['comparisons'], max_seconds=level['max_seconds'])
            budget_teacher.set_horizon(level['horizon_incomes'])
            env = Environment.from_state_json(json.dumps(request['state']), 2000)
            snapshot = json.loads(env.snapshot_json())
            if snapshot['player'] != request['player']:
                raise ValueError(f"state awaits player {snapshot['player']}, not {request['player']}")
            room = request['room']
            teacher = teachers.pop(room, None)
            if teacher is None:
                teacher = TimedPreparationTeacher(room, bgg_openings=True, shared_factions=True)
            teachers[room] = teacher          # most recently used last
            while len(teachers) > MAX_ROOMS:
                teachers.pop(next(iter(teachers)))
            teacher.prefix = []               # a fresh native env per decision starts at step 0
            teacher.bind(env)
            decision_id, index = teacher.choose(snapshot)
            if decision_id != snapshot['decision_id']:
                raise RuntimeError('teacher answered another decision')
            audit = teacher.last_audit or {}
            reply({'ok': True, 'decision': snapshot['candidates'][index],
                   'seconds': round(time.monotonic()-started, 3),
                   'completed_comparisons': audit.get('completed_comparisons', 0),
                   'time_capped': bool(audit.get('time_capped')),
                   'selected': audit.get('selected')})
        except Exception as error:  # report, never crash the pool member
            print(traceback.format_exc(), file=sys.stderr, flush=True)
            reply({'ok': False, 'error': repr(error)[:500]})


if __name__ == '__main__':
    main()
