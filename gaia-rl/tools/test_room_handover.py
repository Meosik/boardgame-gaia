import gzip
import json
import tempfile
import unittest
from pathlib import Path

import room_handover
import teacher_ab


def candidate(**action):
    return {'phase': 'Game', 'action': action}


def write_log(directory, actions, steps=None):
    path = Path(directory)/'decisions.jsonl.gz'
    steps = list(range(len(actions))) if steps is None else steps
    with gzip.open(path, 'wt') as f:
        for step, action in zip(steps, actions):
            f.write(json.dumps({'step': step, 'chosen': {'phase': 'Game', 'action': action}})+'\n')
    return str(path)


class ScriptedIndexTest(unittest.TestCase):
    def test_an_exact_full_action_returns_its_index(self):
        candidates = [candidate(type='Pass'), candidate(type='Build', coord='1,2'), candidate(type='Build', coord='3,4')]
        self.assertEqual(teacher_ab.scripted_index(candidates, {'type': 'Build', 'coord': '3,4'}), 2)

    def test_a_partial_action_picks_the_one_candidate_that_holds_it(self):
        candidates = [candidate(type='Pass'), candidate(type='Build', coord='1,2', building='Mine')]
        self.assertEqual(teacher_ab.scripted_index(candidates, {'type': 'Build', 'coord': '1,2'}), 1)

    def test_a_nested_value_must_be_equal_as_a_whole(self):
        candidates = [candidate(type='Upgrade', tech_tile_choice={'kind': 'Standard', 'tile': 6, 'advance_track': None})]
        wanted = {'type': 'Upgrade', 'tech_tile_choice': {'kind': 'Standard', 'tile': 6}}
        with self.assertRaises(RuntimeError) as caught:
            teacher_ab.scripted_index(candidates, wanted)
        self.assertIn('matches 0 of 1', str(caught.exception))

    def test_an_ambiguous_partial_action_raises(self):
        candidates = [candidate(type='Build', coord='1,2'), candidate(type='Build', coord='3,4')]
        with self.assertRaises(RuntimeError) as caught:
            teacher_ab.scripted_index(candidates, {'type': 'Build'})
        self.assertIn('matches 2 of 2', str(caught.exception))

    def test_no_matching_candidate_raises(self):
        with self.assertRaises(RuntimeError):
            teacher_ab.scripted_index([candidate(type='Pass')], {'type': 'Build'})

    def test_a_wanted_none_matches_only_a_candidate_that_has_the_key_as_none(self):
        candidates = [candidate(type='Upgrade'), candidate(type='Upgrade', advance_track=None)]
        self.assertEqual(teacher_ab.scripted_index(candidates, {'type': 'Upgrade', 'advance_track': None}), 1)
        with self.assertRaises(RuntimeError):
            teacher_ab.scripted_index([candidate(type='Upgrade')], {'type': 'Upgrade', 'advance_track': None})


class OpeningScriptsTest(unittest.TestCase):
    def test_no_prefix_and_no_first_moves_gives_one_unforced_variant(self):
        expected = [{'first_move': None, 'script': []}]
        self.assertEqual(room_handover.opening_scripts(None, 0, None), expected)
        self.assertEqual(room_handover.opening_scripts(None, 0, []), expected)

    def test_a_prefix_and_two_first_moves_give_two_variants(self):
        prefix = [{'type': 'Build', 'coord': '5,6'}, {'type': 'Pass'}]
        build = {'type': 'Build', 'coord': '1,2'}
        with tempfile.TemporaryDirectory() as tmp:
            log = write_log(tmp, prefix)
            variants = room_handover.opening_scripts(log, 2, ['teacher', '{"type":"Build","coord":"1,2"}'])
        self.assertEqual(variants, [{'first_move': None, 'script': prefix},
                                    {'first_move': build, 'script': prefix+[build]}])

    def test_only_the_first_rows_of_a_longer_log_are_used(self):
        actions = [{'type': 'A'}, {'type': 'B'}, {'type': 'C'}]
        with tempfile.TemporaryDirectory() as tmp:
            variants = room_handover.opening_scripts(write_log(tmp, actions), 2, None)
        self.assertEqual(variants, [{'first_move': None, 'script': actions[:2]}])

    def test_prefix_steps_without_a_prefix_log_exits(self):
        with self.assertRaises(SystemExit):
            room_handover.opening_scripts(None, 2, None)

    def test_a_log_with_fewer_rows_than_prefix_steps_exits(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = write_log(tmp, [{'type': 'A'}])
            with self.assertRaises(SystemExit):
                room_handover.opening_scripts(log, 2, None)

    def test_a_log_whose_steps_are_not_zero_to_k_minus_one_exits(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = write_log(tmp, [{'type': 'A'}, {'type': 'B'}], steps=[1, 2])
            with self.assertRaises(SystemExit):
                room_handover.opening_scripts(log, 2, None)

    def test_a_first_move_that_is_not_a_non_empty_json_object_exits(self):
        for text in ('[]', '{}'):
            with self.assertRaises(SystemExit, msg=text):
                room_handover.opening_scripts(None, 0, [text])


class SeatScriptTest(unittest.TestCase):
    def test_hits_lists_every_matching_index(self):
        candidates = [candidate(type='Build', coord='1,2'), candidate(type='Pass'), candidate(type='Build', coord='3,4')]
        self.assertEqual(teacher_ab.scripted_hits(candidates, {'type': 'Build'}), [0, 2])
        self.assertEqual(teacher_ab.scripted_hits(candidates, {'type': 'Pass'}), [1])
        self.assertEqual(teacher_ab.scripted_hits(candidates, {'type': 'Upgrade'}), [])

    def test_no_moves_left_is_done(self):
        self.assertEqual(teacher_ab.seat_script_step([candidate(type='Pass')], []), ('done', None))

    def test_one_matching_candidate_is_played_even_for_a_partial_action(self):
        candidates = [candidate(type='Pass'), candidate(type='Build', coord='1,2', building='Mine')]
        self.assertEqual(teacher_ab.seat_script_step(candidates, [{'type': 'Build', 'coord': '1,2'}]), ('play', 1))
        self.assertEqual(teacher_ab.seat_script_step(candidates, [{'type': 'Pass'}]), ('play', 0))

    def test_a_reaction_decision_waits_whatever_the_next_move_is(self):
        moves = [{'type': 'Pass'}]
        for kind in sorted(teacher_ab.REACTIONS):
            candidates = [candidate(type=kind, n=0), candidate(type=kind, n=1)]
            self.assertEqual(teacher_ab.seat_script_step(candidates, moves), ('wait', None))
        mixed = [candidate(type='ChargePower'), candidate(type='Pass')]
        self.assertEqual(teacher_ab.seat_script_step(mixed, moves), ('play', 1))
        self.assertEqual(teacher_ab.seat_script_step([candidate(type='ChargePower')], [{'type': 'ChargePower'}]),
                         ('wait', None))

    def test_zero_or_several_matches_stop_with_the_count(self):
        candidates = [candidate(type='Build', coord='1,2'), candidate(type='Build', coord='3,4'), candidate(type='Pass')]
        self.assertEqual(teacher_ab.seat_script_step(candidates, [{'type': 'Upgrade'}]), ('stop', 0))
        self.assertEqual(teacher_ab.seat_script_step(candidates, [{'type': 'Build'}]), ('stop', 2))

    def test_the_moves_list_is_not_changed(self):
        moves = [{'type': 'Pass'}, {'type': 'Build'}]
        teacher_ab.seat_script_step([candidate(type='Pass')], moves)
        teacher_ab.seat_script_step([candidate(type='ChargePower')], moves)
        teacher_ab.seat_script_step([candidate(type='Upgrade')], moves)
        self.assertEqual(moves, [{'type': 'Pass'}, {'type': 'Build'}])


class RoomVariantTest(unittest.TestCase):
    def test_room_variant_carries_the_prefix_and_the_seat_script(self):
        prefix = [{'type': 'Build', 'coord': '5,6'}, {'type': 'Pass'}]
        room = [{'type': 'Build', 'coord': '1,2'}, {'type': 'Pass'}]
        with tempfile.TemporaryDirectory() as tmp:
            variants = room_handover.opening_scripts(write_log(tmp, prefix), 2, ['teacher', 'room'], room)
        self.assertEqual(variants, [{'first_move': None, 'script': prefix},
                                    {'first_move': 'room', 'script': prefix, 'seat_script': room}])
        self.assertNotIn('seat_script', variants[0])

    def test_room_without_restored_moves_exits(self):
        with self.assertRaises(SystemExit):
            room_handover.opening_scripts(None, 0, ['room'], None)

    def test_comparable_drops_only_the_event_log_and_the_undo_state(self):
        state = {'event_log': [1], 'undo_state': {'a': 1}, 'round': 2, 'players': [{'id': 0}]}
        self.assertEqual(room_handover.comparable(state), {'round': 2, 'players': [{'id': 0}]})
        self.assertIn('event_log', state)


try:
    from gaia_rl import Environment
except Exception:  # the engine build is not importable here
    Environment = None

SEED = 'room-moves-test'
DECISIONS = 12


def play_decisions(seed=SEED, count=DECISIONS):
    """Play `count` decisions (candidate 0 each). Returns (rows, states, final_env): rows hold the decision's
    player, candidate count and chosen action; states[k] is the state before decision k, states[count] after."""
    env = Environment(seed, 2000)
    rows, states = [], []
    for _ in range(count):
        snap = json.loads(env.snapshot_json())
        states.append(snap['state'])
        rows.append({'player': snap['player'], 'candidates': len(snap['candidates']),
                     'action': snap['candidates'][0]['action'], 'decision_id': snap['decision_id']})
        env.step(snap['decision_id'], 0)
    states.append(json.loads(env.snapshot_json())['state'])
    return rows, states, env


def write_room(path, states):
    with open(path, 'w') as f:
        for revision, state in enumerate(states):
            f.write(json.dumps({'revision': revision, 'snapshot': state})+'\n')


def expected_moves(rows, states, seat, number):
    """(action, revision) of the seat's own turns in round `number`, by the rule of room_moves."""
    out = []
    for k, row in enumerate(rows):
        if states[k]['round'] != number:
            break
        if row['player'] != seat or row['action']['type'] in teacher_ab.REACTIONS:
            continue
        out.append((row['action'], k))
        if row['action']['type'] == 'Pass':
            break
    return out


@unittest.skipIf(Environment is None, 'gaia_rl engine is not importable')
class RoomMovesTest(unittest.TestCase):
    def test_moves_are_restored_from_consecutive_snapshots(self):
        rows, states, _ = play_decisions()
        number = states[0]['round']
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'room.jsonl'
            write_room(path, states)
            self.assertEqual(len(path.read_text().splitlines()), DECISIONS+1)
            total = 0
            for seat in range(4):
                moves, problems = room_handover.room_moves(str(path), 0, seat, number)
                expected = expected_moves(rows, states, seat, number)
                self.assertEqual([m['action'] for m in moves], [a for a, _ in expected], msg=f'seat {seat}')
                self.assertEqual(problems, [], msg=f'seat {seat}')
                for move, (_, k) in zip(moves, expected):
                    self.assertIn(move['matched_by'], ('state', 'seat'))
                    self.assertEqual((move['revision'], move['next_revision']), (k, k+1))
                total += len(moves)
            self.assertGreater(total, 0)


if __name__ == '__main__':
    unittest.main()
