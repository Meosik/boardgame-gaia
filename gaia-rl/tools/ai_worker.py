"""Live-play AI worker: one JSON request per stdin line, one JSON reply per stdout line.

The game server keeps a small pool of these processes and routes every room to the same
worker, so a teacher's plan memory survives between that room's decisions.

Request  {"op": "choose", "room": "AB12", "state": <GameState>, "player": 2, "level": "normal"}
Reply    {"ok": true, "decision": {"phase": "Game", "action": {...}}, "seconds": 1.4, ...}
         {"ok": false, "error": "..."}  (the server then falls back to its own legal move)
Request  {"op": "forget", "room": "AB12"}   drop that room's teacher memory
Request  {"op": "ping"}

Both levels use the frozen teacher with tools/teacher_patches.py geodens_guide
(symmetric pass for all seats, Geodens guide order and look-ahead for Geodens).
Levels: "easy" = the teacher's one-step ranking only; "normal" = 2 completed
comparisons at the next income boundary with a 5 s cap (cycle 016: +21.8 VP/seat over
easy without the cap, -3.8 for the cap). Run with
PYTHONPATH=python:baseline-teacher-20260917:tools from gaia-rl/.
"""
import json
import os
import sys
import time
import traceback

# Server player ids are global (1, 2, 3, ...); the teachers index `players[player_id]`, so
# states are renumbered to list positions 0..3 first. Actions carry no player ids.
ID_KEYS = {'player_id', 'player', 'owner', 'winner', 'requester', 'responder', 'dev_controller'}
ID_LIST_KEYS = {'satellites', 'turn_order', 'pass_order', 'player_order', 'winners',
                'required_approvals', 'approvals', 'alliance_taken', 'explorers'}
SETUP_PHASES = {'FactionSelection', 'Bidding', 'StartingStructures', 'StartingBoosters'}


def renumber(state):
    """Return (state with ids 0..3 by players-list position, {server id: index})."""
    mapping = {p['player_id']: i for i, p in enumerate(state['players'])}

    def ident(value):
        return mapping[value] if isinstance(value, int) and value in mapping else value

    def walk(value, key=None):
        if isinstance(value, dict):
            out = {}
            for k, v in value.items():
                if k == 'player_levels':
                    out[k] = {str(ident(int(pid))): level for pid, level in v.items()}
                elif k == 'final_scores':
                    out[k] = [[ident(pid), score] for pid, score in v]
                elif k == 'active_player' and key in SETUP_PHASES:
                    out[k] = ident(v)            # setup phases name a player; ActionPhase an index
                else:
                    out[k] = walk(v, k)
            return out
        if isinstance(value, list):
            if key in ID_LIST_KEYS:
                return [ident(v) for v in value]
            return [walk(v) for v in value]
        if key in ID_KEYS:
            return ident(value)
        return value

    renumbered = walk({k: v for k, v in state.items() if k != 'event_log'})
    renumbered['event_log'] = []
    return renumbered, mapping


LEVELS = {'easy': {'comparisons': 0, 'horizon_incomes': 2, 'max_seconds': None},
          'normal': {'comparisons': 2, 'horizon_incomes': 1, 'max_seconds': 5}}
MAX_ROOMS = 256


def main():
    # Patch before any teacher module is imported (see fast_teacher.install).
    import fast_teacher
    fast_teacher.install()
    import budget_teacher
    from gaia_rl import Environment
    # Cycle 017: symmetric pass (+7.7 VP/seat, 95% CI [+0.1, +15.2]); cycle 018: Geodens
    # guide order and look-ahead (Geodens +15.5, 95% CI [+3.9, +27.2]).
    from teacher_patches import geodens_guide as make_teacher

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
            original = json.loads(Environment.from_state_json(json.dumps(request['state']), 2000).snapshot_json())
            if original['player'] != request['player']:
                raise ValueError(f"state awaits player {original['player']}, not {request['player']}")
            state, mapping = renumber(request['state'])
            env = Environment.from_state_json(json.dumps(state), 2000)
            snapshot = json.loads(env.snapshot_json())
            # Any missed id field would change legality; refuse rather than misplay.
            if snapshot['player'] != mapping[request['player']] or snapshot['candidates'] != original['candidates']:
                raise ValueError('player renumbering changed the decision; refusing to play')
            if os.environ.get('GAIA_AI_DUMP'):    # diagnostics: keep every request state
                with open(os.environ['GAIA_AI_DUMP'], 'a') as dump:
                    dump.write(json.dumps({'room': request['room'], 'player': request['player'],
                                           'state': request['state']})+'\n')
            room = request['room']
            teacher = teachers.pop(room, None)
            if teacher is None:
                teacher = make_teacher(room, bgg_openings=True, shared_factions=True)
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
