"""The potential term split must add up to the teacher's own potential, for every seat."""
import unittest

import extract_dataset as ed
import teacher_patches as tp
from test_teacher_patches import play


class PotentialTermsTests(unittest.TestCase):
    def test_terms_sum_to_potential_for_every_player(self):
        from faction_teachers.profiles import profiles
        checked = 0
        for _, snapshot in play(rounds=3):
            state = snapshot['state']
            if 'ActionPhase' not in state['phase']:
                continue
            for i, player in enumerate(state['players']):
                home = profiles()[player['faction']].home
                terms = ed.potential_terms(state, i, home)
                self.assertAlmostEqual(sum(terms.values()), tp._original(state, i, home=home), places=9)
                facts = ed.facts(state, i)
                self.assertEqual(facts['res_ore'], player['resources']['ore'])
                checked += 1
        self.assertGreater(checked, 100)


if __name__ == '__main__':
    unittest.main()
