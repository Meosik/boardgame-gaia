import copy
import unittest

from action_purpose.teacher import PurposeTeacher
from action_purpose.test_teacher import FakeEnv, SimpleTeacher as PreviousSimple, action, node
from current_actions.teacher import (BOOSTER_BUILD, CurrentActionTeacher,
                                    construction_cost, terraform_action_value)
from economy.teacher import HOME, ORE_PER_STEP, RING
from economy.test_teacher import fixture, line_board
from integrated.boosters import evaluate_booster as previous_booster, next_income
from integrated.features import resource_value


class SimpleTeacher(CurrentActionTeacher):
    def base_rank(self, snapshot):
        return [(v, 'base') for v in snapshot['values']]


class BoosterTests(unittest.TestCase):
    def setUp(self):
        self.snapshot, self.player = fixture()
        self.state = self.snapshot['state']
        line_board(self.state)
        self.state['spaceship_boards'] = [b for b in self.state['spaceship_boards']
                                         if b['id'] in self.state['board']['spaceship_tiles']]
        self.player['structures'] = [{'hex': '0,0', 'kind': 'Mine'}]
        self.player['resources'].update(ore=8, credits=10, qic=5)
        self.player['tech_tiles'] = []
        self.player['covered_tech_tiles'] = []
        self.player['research_tracks']['navigation'] = 0
        self.state['round'] = 2
        self.target = self.state['board']['hexes']['1,0']['planet']

    def cost(self, coord='1,0'):
        return construction_cost(self.state, self.player, {'type': BOOSTER_BUILD, 'coord': coord})

    def test_only_one_step_free_with_mine_cost_at_every_level_and_home(self):
        for faction, home in HOME.items():
            self.player['faction'] = faction
            for level, price in enumerate(ORE_PER_STEP):
                self.player['research_tracks']['terraforming'] = level
                for offset in range(4):
                    with self.subTest(faction=faction, level=level, steps=offset):
                        self.target['planet_type'] = RING[(RING.index(home)+offset) % 7]
                        cost = self.cost()
                        self.assertEqual((cost.ore, cost.credits, cost.terraform_steps),
                                         (1+max(0, offset-1)*price, 2, max(0, offset-1)))

    def test_gaia_entry_range_and_owned_former_costs_are_preserved(self):
        target = self.state['board']['hexes']['3,0']['planet']
        target.update(planet_type='Gaia', is_gaia_formed=False)
        cost = self.cost('3,0')
        self.assertEqual((cost.ore, cost.credits, cost.qic), (1, 2, 2))
        target.update(planet_type='Transdim', is_gaia_formed=True, owner=1)
        self.assertEqual(self.cost('3,0').qic, 1)
        self.target.update(planet_type='Transdim', is_gaia_formed=False, owner=None)
        self.assertIsNone(self.cost())

    def test_protoplanet_keeps_two_paid_steps_and_asteroid_rule_unchanged(self):
        self.player['research_tracks']['terraforming'] = 0
        self.target['planet_type'] = 'ProtoPlanet'
        self.assertEqual((self.cost().ore, self.cost().credits), (7, 2))
        self.target['planet_type'] = 'Asteroid'
        self.assertEqual((self.cost().ore, self.cost().credits), (0, 0))

    def test_score_reuses_mine_score_with_only_existing_ore_saving(self):
        teacher = CurrentActionTeacher()
        for planet in ('Desert', 'Volcanic', 'Gaia'):
            self.target['planet_type'] = planet
            for ore in (3, 8):
                self.player['resources']['ore'] = ore
                before = copy.deepcopy(self.snapshot)
                ordinary = {'type': 'Build', 'coord': '1,0'}
                special = {'type': BOOSTER_BUILD, 'coord': '1,0'}
                base = PurposeTeacher().score(self.snapshot, ordinary)[0]
                actual, reason = teacher.score(self.snapshot, special)
                saved = construction_cost(self.state, self.player, ordinary).ore-self.cost().ore
                self.assertAlmostEqual(actual-base, saved*(2.5 if ore >= 5 else 3.5))
                self.assertIn('actual cost=', reason)
                self.assertNotIn('unmodeled', reason)
                self.assertEqual(self.snapshot, before)

    def test_unsupported_factions_are_not_silently_treated_as_xenos(self):
        self.player['faction'] = 'Terrans'
        with self.assertRaisesRegex(ValueError, 'scoped'):
            self.cost()

    def test_selection_values_one_funded_free_step_not_just_two_credits(self):
        self.target['planet_type'] = 'Volcanic'
        self.player['research_tracks']['terraforming'] = 0
        self.player['resources'].update(ore=1, credits=0, qic=0)
        pick = {'type': 'SelectStartingBooster', 'booster_id': 12}
        baseline = previous_booster(self.state, self.player, 12, starting=True)
        projected = next_income(self.state, self.player)
        expected = resource_value(projected, {'ore': 3})
        before = copy.deepcopy(self.snapshot)
        value, reason = CurrentActionTeacher().score(self.snapshot, pick)
        self.assertAlmostEqual(value, baseline.total+expected)
        self.assertIn('funded one-step terraform saving', reason)
        self.assertEqual(self.snapshot, before)
        # Another eligible target cannot multiply a once-per-round saving.
        self.state['board']['hexes']['2,0']['planet']['planet_type'] = 'Volcanic'
        self.player['resources']['qic'] = 5
        one = CurrentActionTeacher().score(self.snapshot, pick)[0]
        self.state['board']['hexes']['3,0']['planet']['planet_type'] = 'Volcanic'
        self.assertEqual(CurrentActionTeacher().score(self.snapshot, pick)[0], one)

    def test_unusable_discount_gets_no_selection_bonus(self):
        pick = {'type': 'SelectStartingBooster', 'booster_id': 12}
        self.player['research_tracks']['terraforming'] = 0
        self.player['resources'].update(ore=0, credits=0, qic=0)
        for target_type in ('Desert', 'Gaia', 'Transdim', 'Asteroid', 'ProtoPlanet'):
            self.target['planet_type'] = target_type
            with self.subTest(target=target_type):
                self.assertEqual(CurrentActionTeacher().score(self.snapshot, pick)[0],
                                 previous_booster(self.state, self.player, 12, starting=True).total)
        self.target['planet_type'] = 'Volcanic'
        self.player['structures'] = [{'hex': '0,0', 'kind': 'Mine'}]*8
        self.assertEqual(CurrentActionTeacher().score(self.snapshot, pick)[0],
                         previous_booster(self.state, self.player, 12, starting=True).total)

    def test_other_boosters_unchanged_and_pass_stays_below_three(self):
        teacher = CurrentActionTeacher()
        for booster in range(1, 15):
            if booster == 12:
                continue
            pick = {'type': 'SelectStartingBooster', 'booster_id': booster}
            self.assertEqual(teacher.score(self.snapshot, pick), PurposeTeacher().score(self.snapshot, pick))
        self.target['planet_type'] = 'Volcanic'
        passing = {'type': 'Pass', 'booster_id': 12}
        old = PurposeTeacher().score(self.snapshot, passing)[0]
        new = teacher.score(self.snapshot, passing)[0]
        self.assertGreater(new, old)
        self.assertLess(new, 3)
        self.state['round'] = 6
        self.assertEqual(teacher.score(self.snapshot, passing)[0], 0)

    def test_action_forecast_requires_paid_mine_extra_steps_and_range(self):
        self.player['research_tracks']['terraforming'] = 0
        self.target['planet_type'] = 'Volcanic'
        for ore, credits in ((0, 2), (1, 1), (0, 0)):
            self.player['resources'].update(ore=ore, credits=credits, qic=0)
            self.assertEqual(terraform_action_value(self.state, self.player), 0)
        self.player['resources'].update(ore=1, credits=2)
        self.assertGreater(terraform_action_value(self.state, self.player), 0)
        self.target['planet_type'] = 'Oxide'  # Xenos: two steps, one still paid.
        self.assertEqual(terraform_action_value(self.state, self.player), 0)
        self.player['resources']['ore'] = 4
        self.assertGreater(terraform_action_value(self.state, self.player), 0)
        self.target['owner'] = 2
        self.state['board']['hexes']['3,0']['planet']['planet_type'] = 'Volcanic'
        self.assertEqual(terraform_action_value(self.state, self.player), 0)
        self.player['resources']['qic'] = 1
        self.assertGreater(terraform_action_value(self.state, self.player), 0)


class BatchTests(unittest.TestCase):
    def test_productive_batch_uses_actual_branch_and_equal_per_unit_penalty(self):
        batch = {**action('PowerToCredit'), 'count': 2}
        build, skip = {'type': BOOSTER_BUILD, 'coord': '1,0'}, {'type': 'Pass'}
        before = node([batch, skip], [58, 2], ore=4, credits=0, power=(2, 4, 4))
        after = node([build, skip], [50, 2], ore=4, credits=2, power=(4, 4, 2))
        native = FakeEnv(before, {0: FakeEnv(after)})
        teacher = SimpleTeacher().bind(native)
        scores = teacher.rank(before)
        expected = PreviousSimple().route_value(before, after, set(), [action('PowerToCredit')]*2)
        self.assertEqual(scores[0][0], expected[0])
        self.assertGreater(scores[0][0], scores[1][0])
        self.assertIn(BOOSTER_BUILD, scores[0][1])
        self.assertEqual(teacher.preview_count, 1)
        self.assertEqual(before['state']['players'][0]['resources']['credits'], 0)
        self.assertEqual(PreviousSimple().bind(native).rank(before)[0][0], -12)

    def test_unproductive_already_funded_or_other_actor_batch_is_not_rewarded(self):
        batch, build = {**action('PowerToCredit'), 'count': 2}, {'type': 'Build', 'coord': '1,0'}
        skip = {'type': 'Pass'}
        for actions, after_actions, other_actor in (([batch, skip], [skip], False),
                                                    ([batch, build], [build], False),
                                                    ([batch, skip], [build], True)):
            before = node(actions, [58, 50])
            after = node(after_actions, [60], ore=2, credits=5)
            if other_actor:
                after['player'] = 1
            teacher = SimpleTeacher().bind(FakeEnv(before, {0: FakeEnv(after)}))
            self.assertEqual(teacher.rank(before)[0][0], -12)

    def test_count_one_behavior_and_xenos_exception_are_preserved(self):
        for kind in ('PowerToCredit', 'OreToPowerBowl3', 'BurnPower'):
            before = node([action(kind), {'type': 'Pass'}], [58, 2])
            after = node([{'type': 'Build', 'coord': '1,0'}], [50], ore=3, credits=4)
            env = FakeEnv(before, {0: FakeEnv(after)})
            self.assertEqual(SimpleTeacher().bind(env).rank(before),
                             PreviousSimple().bind(env).rank(before))
        batch = {**action('OreToPowerBowl3'), 'count': 2}
        before = node([batch], [58])
        after = node([{'type': 'Pass'}], [2])
        teacher = SimpleTeacher().bind(FakeEnv(before, {0: FakeEnv(after)}))
        self.assertEqual(teacher.rank(before)[0][0], -12)

    def test_preview_budget_stays_bounded_and_missing_native_is_rejected(self):
        before = node([{**action('PowerToCredit'), 'count': n} for n in range(1, 31)], [58]*30)
        after = node([{'type': 'Pass'}], [2])
        teacher = SimpleTeacher().bind(FakeEnv(before, {i: FakeEnv(after) for i in range(30)}))
        self.assertTrue(all(value == -12 for value, _ in teacher.rank(before)))
        self.assertEqual(teacher.preview_count, 24)
        with self.assertRaisesRegex(ValueError, 'native environment'):
            SimpleTeacher().rank(before)


if __name__ == '__main__':
    unittest.main()
