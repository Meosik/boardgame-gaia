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


if __name__ == '__main__':
    unittest.main()
