from copy import deepcopy
from dataclasses import asdict
import gzip
import json
from pathlib import Path
import tempfile
import unittest

from four_factions.outcomes import summarize
from four_factions.preparation import Goal, scoring_pairs
from four_factions.test_preparation import root


class OutcomeTests(unittest.TestCase):
    def test_prediction_is_not_reported_as_an_observed_academy(self):
        _, snapshot = root()
        goal = Goal('academy', 'upgrade', '-3,-4', 'Science')
        terminal = deepcopy(snapshot)
        terminal['state']['round'] = 3
        row = {'snapshot': snapshot, 'index': 24, 'teacher_audit': {'selected': 'academy', 'plans': [
            {'goal': 'academy', 'goal_spec': asdict(goal), 'goal_acquired': True}]}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'trace.gz'
            with gzip.open(path, 'wt') as stream:
                stream.write(json.dumps(row)+'\n')
            result = summarize(path, snapshot, terminal)
        observed = result['selected_goal_outcomes'][0]
        self.assertTrue(observed['predicted_goal_acquired'])
        self.assertFalse(observed['observed_goal_acquired'])
        self.assertEqual(result['unresolved_goal_outcomes'], 0)
        self.assertNotIn('Terrans', result['first_academies'])

    def test_original_transdim_formation_and_colonization_are_distinct(self):
        _, snapshot = root()
        terminal = deepcopy(snapshot)
        planet = terminal['state']['board']['hexes']['-3,-1']['planet']
        self.assertEqual(planet['planet_type'], 'Transdim')
        planet['is_gaia_formed'] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'trace.gz'
            with gzip.open(path, 'wt'):
                pass
            result = summarize(path, snapshot, terminal)
        self.assertEqual(result['original_planets']['Transdim']['formed'], 1)
        self.assertEqual(result['original_planets']['Transdim']['colonized'], 0)

    def test_scoring_tile_pairs_keep_intended_work_and_do_not_invent_value(self):
        _, snapshot = root()
        snapshot['candidates'] = [{'action': {'type': 'RebellionGainTechTile', 'tile': 8}},
                                  {'action': {'type': 'Pass', 'booster_id': 1}}]
        goals = [Goal('colony', 'colony', '-3,-1'),
                 Goal('research', 'research', target='Navigation', level=2)]
        pairs = scoring_pairs(snapshot, [(1, 'tech'), (2, 'pass')], goals)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0].family, 'colony')
        self.assertEqual(pairs[0].coord, goals[0].coord)
        self.assertEqual(pairs[0].first, 0)
        self.assertNotIn('value', asdict(pairs[0]))


if __name__ == '__main__':
    unittest.main()
