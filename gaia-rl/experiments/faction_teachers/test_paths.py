"""Guide/predicate fixtures are not legal native game demonstrations."""
from copy import deepcopy
import unittest

from faction_learning import FACTIONS
from faction_teachers.paths import goals, action_matches
from four_factions.preparation import Goal, achieved, advance_goal, predicate_for
from four_factions.test_preparation import root


class GuidePathTests(unittest.TestCase):
    def test_all_ten_new_base_factions_have_executable_guide_proposals(self):
        _, original = root()
        sources = {'Ambas': 'B06', 'Gleens': 'B05', 'Itars': 'B07', 'Nevlas': 'B08',
                   'Firaks': 'B09', 'BalTaks': 'B11', 'Ivits': 'B12', 'Bescods': 'B13',
                   'Geodens': 'B14', 'Lantids': 'B16'}
        for faction, source in sources.items():
            snapshot = deepcopy(original)
            snapshot['state']['players'][snapshot['player']]['faction'] = faction
            proposals = goals(snapshot)
            self.assertTrue(proposals, faction)
            self.assertTrue(all(source in g.sources and g.family == 'ordered' for g in proposals))
            for goal in proposals:
                self.assertTrue(goal.steps)
                self.assertTrue(callable(predicate_for(snapshot, goal)))

    def test_expansion_profiles_do_not_invent_source_openings_or_guide_sequences(self):
        _, snapshot = root()
        for faction in FACTIONS[-4:]:
            snapshot['state']['players'][snapshot['player']]['faction'] = faction
            self.assertEqual(goals(snapshot), [])

    def test_firaks_rebuild_is_not_precompleted_before_its_downgrade(self):
        _, before = root()
        actor = before['player']
        player = before['state']['players'][actor]
        player['faction'] = 'Firaks'
        player['structures'][0]['kind'] = 'PlanetaryInstitute'
        player['structures'][1]['kind'] = 'ResearchLab'
        site = player['structures'][1]['hex']
        goal = next(g for g in goals(before) if g.name.endswith(f'lab-downgrade-rebuild@{site}'))
        self.assertEqual([s.family for s in goal.steps], ['faction-action', 'upgrade'])
        self.assertFalse(achieved(before, actor, goal))
        action = {'type': 'FiraksDowngradeResearchLab', 'coord': site, 'track': 'Science'}
        self.assertTrue(predicate_for(before, goal)(action))
        after = deepcopy(before)
        after['state']['players'][actor]['structures'][1]['kind'] = 'TradingStation'
        pending = advance_goal(after, actor, goal, action, before=before)
        self.assertEqual(len(pending.steps), 1)
        self.assertFalse(achieved(after, actor, pending))
        last = deepcopy(after)
        last['state']['players'][actor]['structures'][1]['kind'] = 'ResearchLab'
        finished = advance_goal(last, actor, pending,
                               {'type': 'Upgrade', 'coord': site, 'to': 'ResearchLab'}, before=after)
        self.assertTrue(achieved(last, actor, finished))

    def test_special_action_goal_checks_action_kind_and_location(self):
        goal = Goal('former', 'faction-action', target='FreeAction:GaiaformerToQic')
        self.assertTrue(action_matches(goal, {'type': 'FreeAction', 'kind': 'GaiaformerToQic'}))
        self.assertFalse(action_matches(goal, {'type': 'FreeAction', 'kind': 'PowerToQic'}))
        goal = Goal('swap', 'faction-action', '1,2', 'AmbasSwapPlanetaryInstitute')
        self.assertTrue(action_matches(goal, {'type': 'AmbasSwapPlanetaryInstitute', 'mine_coord': '1,2'}))
        self.assertFalse(action_matches(goal, {'type': 'AmbasSwapPlanetaryInstitute', 'mine_coord': '2,3'}))


if __name__ == '__main__':
    unittest.main()
