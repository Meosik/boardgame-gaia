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


def game_row(game_dir, result, focus):
    """What one handover game shows: scores, the focus seat's rank, federations formed, decision times."""
    row = {'game': game_dir.name, 'complete': result['complete'], 'failure': result.get('failure_kind'),
           'error': result.get('error'), 'steps': result.get('steps', result.get('step')),
           'stopped_at_round': result.get('stopped_at_round'), 'scores': result.get('scores')}
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
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('A new output directory is required')
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
        'versions': runtime_versions(), 'training_performed': False})
    jobs = [(number, k) for number in rounds for k in range(args.repeats)]
    lock = threading.Lock()

    def play_one(job):
        number, k = job
        game_dir = args.output/f'round-{number}'/f'game-{k}'
        game_dir.parent.mkdir(exist_ok=True)
        result = teacher_ab.play(game_dir, f'{args.room}-s{k}', {'A': teacher, 'B': teacher}, {0, 1, 2, 3}, clock,
                                 state=args.output/'states'/f'round-{number}.json', max_steps=args.max_steps)
        row = {'start_round': number, 'repeat': k, **game_row(game_dir, result, focus)}
        with lock:
            print(json.dumps({key: row[key] for key in ('start_round', 'repeat', 'complete', 'failure', 'scores',
                                                        'stopped_at_round', 'max_seconds')}), flush=True)
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
    teacher_ab.write_json(args.output/'metrics.json', metrics)
    print(f"{args.focus} in room {args.room}: the room's own final {metrics['room_focus_final']}")
    for number, row in table.items():
        print(f"start round {number}: VP then {row['start_vp']}, teacher finals {row['focus_scores']} "
              f"mean {row['mean']} vs round-1 start {row['mean_minus_round1']} ({row['finished']}/{row['games']} finished)")


if __name__ == '__main__':
    main()
