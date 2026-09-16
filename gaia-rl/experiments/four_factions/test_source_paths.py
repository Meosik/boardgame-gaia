"""Source suggestions must become paid alternatives, not faction commands."""
from copy import deepcopy
from dataclasses import asdict
import json
import time
import unittest
from unittest.mock import Mock

from four_factions.preparation import (Goal, Policies, achieved, advance_goal,
                                       goal_from_dict, goals_for, predicate_for,
                                       rollout, select_goal, viable, funding_need)
from four_factions.timed import TimedPreparationTeacher
from four_factions.source_paths import opening_goals
from four_factions.test_preparation import root
from research_plans.teacher import best_index


class SourcePathTests(unittest.TestCase):
    def setUp(self):
        self.env, self.snapshot = root()

    def test_all_four_factions_have_distinct_source_backed_alternatives(self):
        expected = {'HadschHallas': 'PG19', 'Xenos': 'PG15',
                    'Terrans': 'PG18', 'Taklons': 'PG21'}
        for faction, source in expected.items():
            snapshot = deepcopy(self.snapshot)
            snapshot['state']['players'][snapshot['player']]['faction'] = faction
            goals = opening_goals(snapshot)
            self.assertTrue(any(source in g.sources for g in goals), faction)
            self.assertTrue(any('+1-mine' in g.name for g in goals), faction)
            self.assertTrue(any('+2-mine' in g.name for g in goals), faction)
            self.assertTrue(any(g.family == 'sequence' for g in goals))
        self.assertTrue(any('two-labs' in g.name for g in opening_goals(snapshot)))

    def test_unplaced_starting_mines_do_not_count_as_paid_extra_expansion(self):
        for faction, initial in (('HadschHallas', 2), ('Xenos', 3), ('Terrans', 2), ('Taklons', 2)):
            s = deepcopy(self.snapshot)
            s['state']['round'] = 0
            p = s['state']['players'][s['player']]
            p['faction'] = faction
            p['structures'] = p['structures'][:1]
            goals = opening_goals(s)
            one = [g for g in goals if '+1-mine' in g.name]
            self.assertTrue(one)
            self.assertTrue(all(next(step.level for step in g.steps if step.family == 'expansion') == initial+1 for g in one))

    def test_sequence_json_roundtrip_and_observed_progress(self):
        a = Goal('PI', 'upgrade', '-3,-4', 'PlanetaryInstitute')
        b = Goal('expand', 'expansion', level=3)
        goal = Goal('PI+mine', 'sequence', steps=(a, b), sources=('PG18',))
        self.assertEqual(goal_from_dict(json.loads(json.dumps(asdict(goal)))), goal)
        after = deepcopy(self.snapshot)
        after['state']['players'][after['player']]['structures'][0]['kind'] = 'PlanetaryInstitute'
        remaining = advance_goal(after, after['player'], goal, {'type': 'Upgrade'})
        self.assertEqual(remaining.steps, (b,))
        self.assertFalse(achieved(after, after['player'], remaining))

    def test_completed_lab_still_counts_after_academy_upgrade(self):
        goal = Goal('lab', 'upgrade', '-3,-4', 'ResearchLab')
        s = deepcopy(self.snapshot)
        s['state']['players'][s['player']]['structures'][0]['kind'] = {'Academy': 'Science'}
        self.assertTrue(achieved(s, s['player'], goal))

    def test_ship_payoff_advances_only_after_own_actual_use(self):
        goal = Goal('ship+mine', 'sequence', steps=(
            Goal('Rebellion', 'ship', target='Rebellion', payoff='RebellionGainTechTile'),
            Goal('expand', 'expansion', level=3)))
        untouched = advance_goal(self.snapshot, self.snapshot['player'], goal, {'type': 'AcceptPower'})
        self.assertEqual(untouched, goal)
        used = advance_goal(self.snapshot, self.snapshot['player'], goal, {'type': 'RebellionGainTechTile'})
        self.assertEqual(len(used.steps), 1)

    def test_advanced_lost_fleet_slot_is_not_omitted(self):
        s = self.snapshot
        tile = s['state']['research_board']['lost_fleet_advanced_tech_tile']
        goals = goals_for(s)
        self.assertTrue(any(g.family == 'lost-fleet' and g.tile == tile for g in goals))

    def test_upgrade_tech_choice_can_prepare_the_next_research_goal(self):
        goal = Goal('lab+Gaia', 'sequence', steps=(
            Goal('lab', 'upgrade', '-3,-4', 'ResearchLab'),
            Goal('Gaia2', 'research', target='GaiaProject', level=2)))
        s = deepcopy(self.snapshot)
        s['state']['players'][s['player']]['structures'][0]['kind'] = 'TradingStation'
        predicate = predicate_for(s, goal)
        good = {'type': 'Upgrade', 'coord': '-3,-4', 'to': 'ResearchLab',
                'tech_tile_choice': {'kind': 'Standard', 'tile': 9}}
        s['candidates'] = [{'action': good}]
        self.assertTrue(predicate(good))

    def test_taken_colony_or_advanced_tile_invalidates_old_plan(self):
        goal = Goal('Gaia', 'colony', '-3,-1')
        self.assertTrue(viable(self.snapshot, self.snapshot['player'], goal))
        s = deepcopy(self.snapshot)
        s['state']['board']['hexes']['-3,-1']['planet']['owner'] = 1
        self.assertFalse(viable(s, s['player'], goal))
        tile = Goal('advanced', 'advanced', target='Navigation', tile=8)
        s['state']['research_board']['advanced_tech_tiles'][1] = None
        self.assertFalse(viable(s, s['player'], tile))
        action = {'type': 'Upgrade', 'tech_tile_choice': {'kind': 'LostFleetAdvanced', 'track': 'Navigation'}}
        self.assertFalse(predicate_for(s, tile)(action))

    def test_main_power_action_can_fund_upgrade_across_opponent_turn(self):
        # Selection unit fixture, not a claim that this synthetic state is replayable.
        s = deepcopy(self.snapshot)
        actor = s['player']
        p = s['state']['players'][actor]
        p['structures'][0]['kind'] = 'ResearchLab'
        p['resources']['ore'] = 5
        p['resources']['credits'] = 6
        s['candidates'] = [{'action': {'type': 'Pass', 'booster_id': 1}},
                           {'action': {'type': 'PowerAction', 'id': 7}}]
        after = deepcopy(s)
        after['player'] = 3
        after['state']['players'][actor]['resources']['ore'] = 6
        env = Mock()
        env.fork.return_value.snapshot_json.return_value = json.dumps(after)
        goal = Goal('academy', 'upgrade', '-3,-4', 'Science')
        policies = Mock()
        self.assertEqual(select_goal(env, s, [(9, 'pass'), (1, 'ore')], goal, policies, time.monotonic()+5), 1)
        policies.rank.assert_not_called()

    def test_shared_quartet_upgrade_costs_do_not_impersonate_another_faction(self):
        for faction in ('HadschHallas', 'Xenos', 'Terrans', 'Taklons'):
            s = deepcopy(self.snapshot)
            s['state']['players'][s['player']]['faction'] = faction
            s['state']['players'][s['player']]['structures'][0]['kind'] = 'ResearchLab'
            need = funding_need(s, Goal('academy', 'upgrade', '-3,-4', 'Science'))
            self.assertEqual(need, {'ore': 6, 'credits': 6})
            self.assertEqual(s['state']['players'][s['player']]['faction'], faction)

    def test_actual_move_updates_plan_without_saving_candidate_index(self):
        s = self.snapshot
        actor = str(s['player'])
        teacher = TimedPreparationTeacher('unused', prefix=[0]*s['steps'])
        goal = Goal('PI+mine', 'sequence', first=123, steps=(
            Goal('PI', 'upgrade', '-3,-4', 'PlanetaryInstitute'),
            Goal('expand', 'expansion', level=3)))
        teacher.memory['_plans'] = {actor: asdict(goal)}
        after = deepcopy(s)
        after['steps'] += 1
        after['state']['players'][s['player']]['structures'][0]['kind'] = 'PlanetaryInstitute'
        teacher.observe(s, 0, after)
        saved = goal_from_dict(teacher.memory['_plans'][actor])
        self.assertIsNone(saved.first)
        self.assertEqual(len(saved.steps), 1)

    def test_native_sequence_pays_for_academy_and_preserves_parent(self):
        s, env = self.snapshot, self.env
        original = env.snapshot_json()
        policies = Policies()
        scores = policies.rank(env, s)
        goal = Goal('academy+Gaia', 'sequence', steps=(
            Goal('academy', 'upgrade', '-3,-4', 'Science'),
            Goal('Gaia2', 'research', target='GaiaProject', level=2)), sources=('B04', 'PG18'))
        deadline = time.monotonic()+180
        first = select_goal(env, s, scores, goal, policies, deadline)
        control = rollout(env, s, best_index(scores, range(len(scores))), Goal('current'), policies, deadline)
        result = rollout(env, s, first, goal, policies, deadline)
        self.assertTrue(result['complete'] and control['complete'])
        self.assertEqual(result['end_round'], control['end_round'])
        self.assertGreater(result['value'], control['value'])
        academy = [a for a in result['actions'] if a['action'].get('to') == {'Academy': 'Science'}]
        self.assertTrue(academy)
        self.assertEqual(academy[0]['resources_before']['ore']-academy[0]['resources_after']['ore'], 6)
        self.assertEqual(env.snapshot_json(), original)


if __name__ == '__main__':
    unittest.main()
