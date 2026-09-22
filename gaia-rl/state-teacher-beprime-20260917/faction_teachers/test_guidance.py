"""Source-to-action contracts, with native-paid acquisition checked separately."""
from copy import deepcopy
from dataclasses import asdict
import json
import time
import unittest

from faction_teachers.guidance import advice_goals, technology_choice, available_technology
from four_factions.preparation import Goal, Policies, achieved, predicate_for, scoring_pairs, select_goal, viable
from four_factions.test_preparation import root


class GuidanceTests(unittest.TestCase):
    def test_terran_pair_and_ambas_power_use_actual_native_tile_ids(self):
        _, s = root()
        terrans = advice_goals(s)
        pair = next(g for g in terrans if 'charge-and-Gaia' in g.name)
        self.assertEqual([g.tile for g in pair.steps if g.family == 'technology'], [10, 8])
        s['state']['players'][s['player']]['faction'] = 'Ambas'
        ambas = advice_goals(s)
        self.assertTrue(any(g.steps[0].tile == 6 and 'B06' in g.sources for g in ambas))
        self.assertFalse(any(g.steps[0].tile == 4 and 'large-power' in g.name for g in ambas))

    def test_every_original_faction_has_technology_or_track_advice(self):
        from bgg_openings.catalog import BASE_FACTIONS
        _, s = root()
        for faction in BASE_FACTIONS:
            s['state']['players'][s['player']]['faction'] = faction
            result = advice_goals(s)
            self.assertTrue(result, faction)
            self.assertTrue(all(g.sources for g in result))
            self.assertTrue(any(any(step.family in ('technology','research','advanced')
                                    for step in g.steps) for g in result), faction)

    def test_standard_choice_recognizes_native_acquisition_variants_and_mandatory_track(self):
        _, s = root()
        tile = s['state']['research_board']['tech_tile_slots'][0]
        for action in ({'type':'Upgrade','tech_tile_choice':{'kind':'Standard','tile':tile,'advance_track':'Science'}},
                       {'type':'ItarsGaiaTechChoice','choice':{'kind':'Standard','tile':tile}},
                       {'type':'SpaceGiantsGainTechTile','choice':{'kind':'Standard','tile':tile}},
                       {'type':'RebellionGainTechTile','tile':tile,'track':'Science'}):
            self.assertEqual(technology_choice(s['state'], action), (tile, 'Terraforming'))
        self.assertIsNone(technology_choice(s['state'], {'type':'Upgrade',
            'tech_tile_choice':{'kind':'Advanced','track':'Science','cover_tile':2}}))

    def test_covered_or_absent_technology_cannot_be_a_new_target(self):
        _, s = root()
        p = s['state']['players'][s['player']]
        goal = Goal('charge', 'technology', tile=10)
        p['tech_tiles'] = [10]
        p['covered_tech_tiles'] = [10]
        self.assertFalse(achieved(s, s['player'], goal))
        self.assertFalse(viable(s, s['player'], goal))
        self.assertFalse(available_technology(s, 255))

    def test_ordered_nested_builds_participate_in_technology_scoring_pairs(self):
        _, s = root()
        s['candidates'] = [{'action': {'type':'Upgrade',
                           'tech_tile_choice':{'kind':'Standard','tile':8}}}]
        goal = Goal('nested-Gaia', 'ordered', steps=(Goal('nested', 'ordered', steps=(
                    Goal('Gaia', 'colony', '-3,-1'),)),))
        result = scoring_pairs(s, [(1, 'fixture')], [goal])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].first, 0)
        self.assertEqual(result[0].steps, goal.steps)

    def test_ordered_technology_choice_prefers_its_next_research_when_legally_available(self):
        _, s = root()
        s['state']['research_board']['tech_tile_slots'] = [1,2,3,4,5,6,10,8,9]
        def action(track):
            return {'type':'Upgrade','tech_tile_choice':{'kind':'Standard','tile':10,'advance_track':track}}
        s['candidates'] = [{'action': action('Science')}, {'action': action('Economy')}]
        goal = Goal('charge-Science', 'ordered', steps=(Goal('charge','technology',tile=10),
                     Goal('science','research',target='Science',level=4)))
        predicate = predicate_for(s, goal)
        self.assertTrue(predicate(action('Science')))
        self.assertFalse(predicate(action('Economy')))

    def test_native_technology_plan_pays_for_preparation_without_mutating_root(self):
        env, s = root()
        policies = Policies(shared_factions=True)
        scores = policies.rank(env, s)
        goal = Goal('knowledge-income','technology',tile=5)
        index = select_goal(env, s, scores, goal, policies, time.monotonic()+30)
        self.assertEqual(json.loads(env.snapshot_json()), s)
        self.assertEqual(s['candidates'][index]['action']['type'], 'Upgrade')
        after = json.loads(env.fork(s['decision_id'], index).snapshot_json())
        actor = s['player']
        self.assertLess(after['state']['players'][actor]['resources']['ore'],
                        s['state']['players'][actor]['resources']['ore'])


if __name__ == '__main__':
    unittest.main()
