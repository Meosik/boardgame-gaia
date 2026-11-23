"""Hand an exported live room over to the lab teacher.

From the first action decision of each chosen round of the room (income and Gaia phase done), one teacher
plays all four seats to the end of the game. The round-1 start is the control: same map, factions, seats,
starting structures and boosters as the room, every later move the teacher's. A later round's start also holds
what the room's players — the owner and the live AI seats — did until then, so
`focus seat's final score (round N start) - (round 1 start)` is the value of the whole room position at
round N for this teacher, not of the owner's moves alone (HANDOFF E258, Codex debate). One room is one map:
an exploratory read of where to look, not a strength measurement.

The room export is `~/gaia-media/rooms/<ROOM>-snapshots.jsonl` (one {"revision", "snapshot"} per line, the
server's GameState). States are renumbered to seats 0..3 like the live worker does (ai_worker.renumber). The
teacher starts with an empty plan memory at every start, as the live worker does after a restart.

  cd gaia-rl && GAIA_ENGINE_FIXES_2=1 PYTHONPATH=python:baseline-teacher-20260917:tools .venv/bin/python \\
      tools/room_handover.py --room 98ADBD --rounds 1 4 5 6 --repeats 3 --teacher tools/<spec>.json \\
      --comparisons 4 --fast-copy --output runs/<name>

Testing one decision (HANDOFF E265, one start round only): `--prefix-log <decisions.jsonl.gz of an earlier game from
the same start> --prefix-steps K` replays that game's first K decisions in every game, so all games reach the
same state; each `--first-move` then gives one game whose next decision is that action (JSON of the action, or
the part that names it; it must match exactly one legal candidate) — or `teacher` for the unforced game. From
there the teacher plays on. Games are written to `round-N/move-I/game-K`, I in the order of the `--first-move`
values, and `metrics.json` has one `by_first_move` row per value.

`--first-move room` is the game that follows the owner: after the prefix, every own turn of the focus seat is its
next move of that round in the room (restored from the snapshots, room_moves; listed in manifest.json
`room_moves`) for as long as that move is legal in this game — the other seats are the teacher's, so the board
may differ from the room's. At the first move that is not legal the teacher takes the seat over; reactions
(charge offers, income order) are always the teacher's. `seat_script` in metrics.json says how many moves were
played and where it stopped. If a move cannot be restored with this engine build the run stops before any game.
"""
import argparse
import gzip
import json
import statistics
import threading
from pathlib import Path

import teacher_ab
from ai_worker import renumber
from charge_rounds import round_started


def room_starts(path, rounds):
    """({round: {'revision', 'state' (renumbered GameState), 'player', 'vp'}}, mapping, final scores by seat, skipped).

    A snapshot the lab engine refuses (transient phases such as RoundScoring) is skipped and counted."""
    from gaia_rl import Environment
    starts, mapping, final, skipped = {}, None, None, 0
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            phase = row['snapshot'].get('phase')
            if isinstance(phase, dict) and 'Ended' in phase:
                ids = {p['player_id']: i for i, p in enumerate(row['snapshot']['players'])}
                final = {ids[pid]: score for pid, score in phase['Ended']['final_scores']}
            if len(starts) == len(rounds):
                continue
            try:
                state, mapping = renumber(row['snapshot'])
                snapshot = json.loads(Environment.from_state_json(json.dumps(state), 2000).snapshot_json())
                original = json.loads(Environment.from_state_json(json.dumps(row['snapshot']), 2000).snapshot_json())
            except Exception:
                skipped += 1
                continue
            for number in rounds:
                if number in starts or not round_started(snapshot['state'], number):
                    continue
                if snapshot['state']['round'] != number:
                    raise SystemExit(f'round {number}: no loadable snapshot at its first decision '
                                     f'(revision {row["revision"]} is already round {snapshot["state"]["round"]})')
                # As in ai_worker: a missed id field would change legality.
                if snapshot['player'] != mapping[original['player']] or snapshot['candidates'] != original['candidates']:
                    raise SystemExit(f'revision {row["revision"]}: renumbering changed the decision')
                starts[number] = {'revision': row['revision'], 'state': state, 'player': snapshot['player'],
                                  'vp': [p['vp'] for p in snapshot['state']['players']],
                                  'factions': [p['faction'] for p in snapshot['state']['players']]}
    missing = [n for n in rounds if n not in starts]
    if missing:
        raise SystemExit(f'no start found for rounds {missing}')
    return starts, mapping, final, skipped


def comparable(state):
    """A GameState without what the server alone keeps (undo bookkeeping) and the event log."""
    return {key: value for key, value in state.items() if key not in ('event_log', 'undo_state')}


def room_moves(path, start_revision, seat, number):
    """(moves, problems): the seat's own turns in round `number` of the room, from the start revision to its pass.

    The export holds states — its event log names only the type of each action — so a move is restored as the
    one legal candidate that turns a snapshot into the room's next one. Only the room's final line counts: when
    a snapshot equals an earlier one (comparable) the room was undone to it, and the snapshots kept between
    the two are cut — the same action played again after an undo is one move; a snapshot whose event log is
    not the beginning of the final log is dropped too. Each move is {'revision', 'next_revision', 'action',
    'matched_by'}: 'state' = the whole next state is reproduced (comparable), 'seat' = no candidate does that
    and exactly one reproduces the seat's own player record (an engine build that differs from the server's in
    what follows the move, e.g. the income after a pass). Reactions (teacher_ab.REACTIONS) are left out.
    problems lists the steps that could not be restored; the moves after such a step are still listed."""
    from gaia_rl import Environment
    with open(path) as f:
        lines = [line for line in f if line.strip()]
    final_log = json.loads(lines[-1])['snapshot']['event_log']
    line, server_id = [], None
    for text in lines:
        row = json.loads(text)
        log = row['snapshot'].get('event_log', [])
        if row['revision'] < start_revision or log != final_log[:len(log)]:
            continue
        try:
            state, mapping = renumber(row['snapshot'])
            env = Environment.from_state_json(json.dumps(state), 2000)
            snapshot = json.loads(env.snapshot_json())
        except Exception:
            continue  # a transient phase: nobody decides there
        server_id = next(pid for pid, index in mapping.items() if index == seat)
        now = comparable(snapshot['state'])
        back = next((i for i, kept in enumerate(line) if kept[4] == now), None)
        if back is not None:
            # An undo: the room is back at a state it had before, so what was kept after that state never
            # happened — also when the undone action was then played again and its log looks like the final one.
            del line[back+1:]
            continue
        line.append((row['revision'], env, snapshot, log, now))
        if snapshot['state']['round'] > number:
            break
    moves, problems = [], []
    for (revision, env, snapshot, log, _), (next_revision, _, _, next_log, after) in zip(line, line[1:]):
        if snapshot['state']['round'] != number:
            break
        if snapshot['player'] != seat:
            continue
        forks = [comparable(json.loads(env.fork(snapshot['decision_id'], i).snapshot_json())['state'])
                 for i in range(len(snapshot['candidates']))]
        hits, matched_by = [i for i, state in enumerate(forks) if state == after], 'state'
        if len(hits) != 1:
            hits = [i for i, state in enumerate(forks) if state['players'][seat] == after['players'][seat]]
            matched_by = 'seat'
        logged = [e['ActionLog']['action'] for e in next_log[len(log):]
                  if 'ActionLog' in e and e['ActionLog']['player'] == server_id]
        if len(hits) != 1:
            problems.append(f'revision {revision}->{next_revision}: {len(hits)} of {len(snapshot["candidates"])} '
                            f'candidates give the room\'s next state (the room logged {logged})')
            continue
        action = snapshot['candidates'][hits[0]]['action']
        if logged and isinstance(logged[0], str) and logged[0] != action['type']:
            problems.append(f'revision {revision}->{next_revision}: restored {action["type"]}, the room logged {logged}')
            continue
        if action['type'] in teacher_ab.REACTIONS:
            continue
        moves.append({'revision': revision, 'next_revision': next_revision, 'action': action, 'matched_by': matched_by})
        if action['type'] == 'Pass':
            break
    return moves, problems


def opening_scripts(prefix_log, prefix_steps, first_moves, room=None):
    """[{'first_move': action, None or 'room', 'script': [action, ...]}], one per --first-move value
    ('teacher' = None).

    The script is what teacher_ab.play plays before any teacher chooses: the first prefix_steps decisions of an
    earlier game from the same start, then the forced first move if there is one. The value 'room' has the
    prefix as its script and 'seat_script': `room` (the focus seat's own turns, room_moves) — played in order
    on that seat's turns for as long as each is legal."""
    prefix = []
    if prefix_steps:
        if prefix_log is None:
            raise SystemExit('--prefix-steps needs --prefix-log')
        with gzip.open(prefix_log, 'rt') as f:
            rows = [json.loads(line) for _, line in zip(range(prefix_steps), f)]
        if [row['step'] for row in rows] != list(range(prefix_steps)):
            raise SystemExit(f'{prefix_log} does not hold decisions 0..{prefix_steps-1}')
        prefix = [row['chosen']['action'] for row in rows]
    variants = []
    for text in first_moves or ['teacher']:
        if text == 'room':
            if room is None:
                raise SystemExit('--first-move room: no room moves were restored')
            variants.append({'first_move': 'room', 'script': list(prefix), 'seat_script': list(room)})
            continue
        move = None if text == 'teacher' else json.loads(text)
        if move is not None and not (isinstance(move, dict) and move):
            raise SystemExit(f'--first-move must be "teacher" or a JSON action object: {text}')
        variants.append({'first_move': move, 'script': prefix+([] if move is None else [move])})
    return variants


def game_row(game_dir, result, focus):
    """What one handover game shows: scores, the focus seat's rank, federations formed, decision times."""
    row = {'game': game_dir.name, 'complete': result['complete'], 'failure': result.get('failure_kind'),
           'error': result.get('error'), 'steps': result.get('steps', result.get('step')),
           'stopped_at_round': result.get('stopped_at_round'), 'scores': result.get('scores'),
           'seat_script': (result.get('seat_scripts') or {}).get(str(focus))}
    federations, seconds, fallbacks = [0, 0, 0, 0], [], 0
    trace = game_dir/'decisions.jsonl.gz'
    if trace.exists():
        with gzip.open(trace, 'rt') as f:
            for line in f:
                decision = json.loads(line)
                action = decision['chosen'].get('action') if isinstance(decision['chosen'], dict) else None
                if isinstance(action, dict) and action.get('type') == 'FormFederation':
                    federations[decision['seat']] += 1
                seconds.append(decision['seconds'])
                fallbacks += bool(decision.get('fallback_timeout'))
    row.update(federations_formed=federations, decisions=len(seconds), max_seconds=max(seconds, default=0),
               at_or_over_60_seconds=sum(s >= 60 for s in seconds), over_100_seconds=sum(s > 100 for s in seconds),
               fallback_timeouts=fallbacks)
    if result['complete'] and row['stopped_at_round'] is None:
        scores = [result['scores'][str(seat)] for seat in range(4)]
        row.update(focus_score=scores[focus], focus_rank=sorted(scores, reverse=True).index(scores[focus])+1)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--room', required=True)
    parser.add_argument('--snapshots', type=Path, help='Default ~/gaia-media/rooms/<ROOM>-snapshots.jsonl')
    parser.add_argument('--rounds', type=int, nargs='+', required=True, help='Start rounds; 1 is the control')
    parser.add_argument('--repeats', type=int, default=1,
                        help='Games per start; repeat k uses the teacher seed label <ROOM>-s<k> at every start')
    parser.add_argument('--focus', default='Ivits', help="Faction whose score is reported (the owner's seat)")
    parser.add_argument('--teacher', required=True, help='teachers.json name or spec .json path')
    parser.add_argument('--comparisons', type=int, required=True)
    parser.add_argument('--fast-copy', action='store_true')
    parser.add_argument('--jobs', type=int, default=1)
    parser.add_argument('--max-steps', type=int, help='Stop every game after this many decisions (tool check only)')
    parser.add_argument('--prefix-log', type=Path,
                        help='decisions.jsonl.gz of an earlier game from the same start (see --prefix-steps)')
    parser.add_argument('--prefix-steps', type=int, default=0,
                        help='Replay the first K decisions of --prefix-log in every game')
    parser.add_argument('--first-move', action='append',
                        help='One game per value: the action (JSON) forced as the decision after the prefix, '
                             '"teacher" for the unforced game, or "room" for the focus seat\'s own turns of '
                             'that round in the room, for as long as they are legal')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('A new output directory is required')
    scripted = bool(args.prefix_steps or args.first_move)
    if scripted and len(set(args.rounds)) != 1:
        raise SystemExit('--prefix-steps / --first-move need exactly one start round')
    teacher = teacher_ab.resolve_teacher(args.teacher)
    problems = teacher_ab.frozen_problems(teacher)
    if problems:
        raise SystemExit(f'Frozen teacher ({teacher["name"]}) changed: {problems[:5]}')
    clock = teacher_ab.budget_clock(args.comparisons)
    if args.fast_copy:
        clock['fast_copy'] = True
    source = args.snapshots or Path.home()/'gaia-media'/'rooms'/f'{args.room}-snapshots.jsonl'
    rounds = sorted(set(args.rounds))
    starts, mapping, room_final, skipped = room_starts(source, rounds)
    factions = starts[rounds[0]]['factions']
    focus = factions.index(args.focus)
    restored = None
    if 'room' in (args.first_move or ()):
        restored, problems = room_moves(source, starts[rounds[0]]['revision'], focus, rounds[0])
        if problems or not restored:
            raise SystemExit('--first-move room: ' + '; '.join(problems or [f'no turn of {args.focus} found']))
    variants = opening_scripts(args.prefix_log, args.prefix_steps, args.first_move,
                               None if restored is None else [move['action'] for move in restored])
    (args.output/'states').mkdir(parents=True)
    for number, start in starts.items():
        (args.output/'states'/f'round-{number}.json').write_text(json.dumps(start['state']))
    from gaia_rl.versions import runtime_versions
    teacher_ab.write_json(args.output/'manifest.json', {
        'created_at': teacher_ab.now(), 'room': args.room, 'snapshots': str(source), 'snapshots_skipped': skipped,
        'server_player_to_seat': {str(k): v for k, v in mapping.items()}, 'factions': factions,
        'focus': args.focus, 'focus_seat': focus, 'room_final_scores': room_final,
        'starts': {str(n): {k: s[k] for k in ('revision', 'player', 'vp')} for n, s in starts.items()},
        'teacher': {**teacher, 'fingerprint': teacher_ab.fingerprint(teacher)}, 'clock': clock,
        'repeats': args.repeats, 'max_steps': args.max_steps, 'jobs': args.jobs,
        'prefix_log': str(args.prefix_log) if args.prefix_log else None, 'prefix_steps': args.prefix_steps,
        'first_moves': [v['first_move'] for v in variants] if scripted else None, 'room_moves': restored,
        'versions': runtime_versions(), 'training_performed': False})
    jobs = [(number, i, k) for number in rounds for i in range(len(variants)) for k in range(args.repeats)]
    lock = threading.Lock()

    def play_one(job):
        number, i, k = job
        # The plain run keeps its layout (round-N/game-K); a scripted run has one folder per first move.
        game_dir = args.output/f'round-{number}'/(f'move-{i}' if scripted else '')/f'game-{k}'
        game_dir.parent.mkdir(parents=True, exist_ok=True)
        result = teacher_ab.play(game_dir, f'{args.room}-s{k}', {'A': teacher, 'B': teacher}, {0, 1, 2, 3}, clock,
                                 state=args.output/'states'/f'round-{number}.json', max_steps=args.max_steps,
                                 script=variants[i]['script'],
                                 seat_scripts={focus: variants[i]['seat_script']} if 'seat_script' in variants[i] else None)
        row = {'start_round': number, 'variant': i, 'first_move': variants[i]['first_move'], 'repeat': k,
               **game_row(game_dir, result, focus)}
        with lock:
            print(json.dumps({key: row[key] for key in ('start_round', 'variant', 'repeat', 'complete', 'failure',
                                                        'scores', 'stopped_at_round', 'max_seconds')}), flush=True)
        return row

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        games = list(pool.map(play_one, jobs))
    table = {}
    for number in rounds:
        scores = [g['focus_score'] for g in games if g['start_round'] == number and 'focus_score' in g]
        table[str(number)] = {'games': sum(g['start_round'] == number for g in games), 'finished': len(scores),
                              'start_vp': starts[number]['vp'][focus], 'focus_scores': scores,
                              'mean': statistics.mean(scores) if scores else None}
    control = table.get('1', {}).get('mean')
    for row in table.values():
        row['mean_minus_round1'] = None if control is None or row['mean'] is None else row['mean']-control
    metrics = {'room': args.room, 'focus': args.focus, 'focus_seat': focus, 'factions': factions,
               'room_final_scores': room_final, 'room_focus_final': (room_final or {}).get(focus),
               'games_planned': len(jobs), 'games_complete': sum(g['complete'] for g in games),
               'failures': [g for g in games if not g['complete']], 'max_steps': args.max_steps,
               'by_start_round': table, 'games': games}
    if scripted:
        metrics['by_first_move'] = [
            {'variant': i, 'first_move': v['first_move'], 'prefix_steps': args.prefix_steps,
             'focus_scores': [g['focus_score'] for g in games if g['variant'] == i and 'focus_score' in g],
             'scores': [g['scores'] for g in games if g['variant'] == i and 'focus_score' in g],
             'seat_script': [g['seat_script'] for g in games if g['variant'] == i],
             'games': sum(g['variant'] == i for g in games)} for i, v in enumerate(variants)]
    teacher_ab.write_json(args.output/'metrics.json', metrics)
    for row in metrics.get('by_first_move', ()):
        print(f"first move {row['variant']} {json.dumps(row['first_move']) if row['first_move'] else 'teacher'}: "
              f"{args.focus} finals {row['focus_scores']}, all seats {row['scores']}"
              + (f", room moves played/stopped {row['seat_script']}" if row['first_move'] == 'room' else ''))
    print(f"{args.focus} in room {args.room}: the room's own final {metrics['room_focus_final']}")
    for number, row in table.items():
        print(f"start round {number}: VP then {row['start_vp']}, teacher finals {row['focus_scores']} "
              f"mean {row['mean']} vs round-1 start {row['mean_minus_round1']} ({row['finished']}/{row['games']} finished)")


if __name__ == '__main__':
    main()
