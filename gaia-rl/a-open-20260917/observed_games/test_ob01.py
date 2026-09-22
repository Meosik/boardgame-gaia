"""OB01 proposals are opt-in, conditional and executable; fixtures are not legal games."""
from copy import deepcopy
import unittest

from four_factions.preparation import goals_for, predicate_for, viable
from four_factions.test_preparation import root
from observed_games import ab_match
from observed_games.ob01 import FACTIONS, goals


def as_faction(snapshot, faction, **changes):
    snapshot = deepcopy(snapshot)
    player = snapshot['state']['players'][snapshot['player']]
    player['faction'] = faction
    for key, value in changes.items():
        player[key] = value
    return snapshot


class ObservedGoalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cls.snapshot = root()

    def test_other_factions_and_setup_receive_nothing(self):
        self.assertEqual(goals(as_faction(self.snapshot, 'Terrans')), [])
        setup = as_faction(self.snapshot, 'BalTaks')
        setup['state']['round'] = 0
        self.assertEqual(goals(setup), [])

    def test_every_proposal_is_sourced_ordered_and_executable(self):
        for faction in FACTIONS:
            s = as_faction(self.snapshot, faction, gaiaformers_total=2, gaiaformers_deployed=0)
            s['state']['round'] = 3
            proposals = goals(s)
            self.assertTrue(proposals, faction)
            for goal in proposals:
                self.assertEqual(goal.family, 'ordered')
                self.assertEqual(goal.sources, ('OB01',))
                self.assertTrue(goal.name.startswith(f'{faction}-OB01-'))
                self.assertTrue(goal.steps)
                self.assertTrue(callable(predicate_for(s, goal)))
                self.assertTrue(viable(s, s['player'], goal))

    def test_baltaks_converts_a_former_before_the_rebellion_tech(self):
        s = as_faction(self.snapshot, 'BalTaks', gaiaformers_total=1, gaiaformers_deployed=1,
                       gaiaformers_in_gaia_area=1)
        goal = next(g for g in goals(s) if g.name == 'BalTaks-OB01-former-QIC-Rebellion-tech')
        self.assertEqual([step.family for step in goal.steps], ['faction-action', 'ship'])
        matches = predicate_for(s, goal)
        self.assertTrue(matches({'type': 'FreeAction', 'kind': 'GaiaformerToQic'}))
        self.assertFalse(matches({'type': 'FreeAction', 'kind': 'PowerToQic'}))

    def test_taklons_round_three_pi_comparison_only(self):
        s = as_faction(self.snapshot, 'Taklons')
        for round_, expected in ((2, False), (3, True), (4, False)):
            s['state']['round'] = round_
            self.assertEqual(any('round3-PI' in g.name for g in goals(s)), expected, round_)

    def test_firaks_downgrade_focus_matches_only_its_track(self):
        s = as_faction(self.snapshot, 'Firaks')
        player = s['state']['players'][s['player']]
        player['research_tracks'].update(economy=3, navigation=2, science=1)
        player['structures'][0]['kind'] = 'PlanetaryInstitute'
        player['structures'][1]['kind'] = 'ResearchLab'
        names = {g.name: g for g in goals(s)}
        self.assertIn('Firaks-OB01-focus-Economy', names)
        self.assertIn('Firaks-OB01-focus-Navigation', names)
        self.assertNotIn('Firaks-OB01-focus-Science', names)
        matches = predicate_for(s, names['Firaks-OB01-downgrade-focus-Economy'])
        site = player['structures'][1]['hex']
        self.assertTrue(matches({'type': 'FiraksDowngradeResearchLab', 'coord': site, 'track': 'Economy'}))
        self.assertFalse(matches({'type': 'FiraksDowngradeResearchLab', 'coord': site, 'track': 'Science'}))

    def test_proposals_only_enter_the_search_when_opted_in(self):
        s = as_faction(self.snapshot, 'Ivits')
        s['state']['round'] = 2
        off = goals_for(s, shared_factions=True)
        on = goals_for(s, shared_factions=True, observed=True)
        self.assertFalse(any('OB01' in g.sources for g in off))
        self.assertTrue(any('OB01' in g.sources for g in on))
        self.assertEqual([g for g in on if 'OB01' not in g.sources], off)


class ObservedMatchTests(unittest.TestCase):
    def test_complementary_assignments_give_each_faction_both_arms(self):
        spec = {'seed': 's'}
        for pair in range(6):
            first, second = ab_match.assignments(spec, pair)
            self.assertEqual(set(first['observed_factions']) | set(second['observed_factions']), set(FACTIONS))
            self.assertFalse(set(first['observed_factions']) & set(second['observed_factions']))

    def test_paired_scores_attribute_each_arm_to_the_right_game(self):
        factions = ['Taklons', 'BalTaks', 'Firaks', 'Ivits']
        first = {'complete': True, 'seed': 's', 'factions': factions,
                 'observed_factions': ['Taklons', 'Firaks'], 'scores': {0: 10, 1: 20, 2: 30, 3: 40}}
        second = {'complete': True, 'seed': 's', 'factions': factions,
                  'observed_factions': ['BalTaks', 'Ivits'], 'scores': {0: 11, 1: 25, 2: 28, 3: 50}}
        result = ab_match.paired_scores(first, second)['by_faction']
        self.assertEqual(result['Taklons'], {'A': 11, 'B': 10, 'B_minus_A': -1})
        self.assertEqual(result['BalTaks'], {'A': 20, 'B': 25, 'B_minus_A': 5})


if __name__ == '__main__':
    unittest.main()
