import json
import math
import unittest
from unittest.mock import patch

from gaia_rl import Environment
from bgg_openings.catalog import BASE_FACTIONS, load_catalog
from current_actions.conservation import blocked
from four_factions.preparation import Goal, Policies, funding_need, predicate_for, viable
from four_factions.test_preparation import root
from faction_teachers.profiles import profiles
from faction_teachers.teacher import SharedTeacher
from faction_learning import FACTIONS


class SharedTeacherTests(unittest.TestCase):
    def test_profiles_use_native_identity_income_and_exact_faction_openings(self):
        data = profiles()
        self.assertEqual(set(data), set(FACTIONS))
        self.assertEqual(data['Lantids'].home, 'Terra')
        self.assertEqual(data['Bescods'].home, 'Titanium')
        self.assertEqual(data['Ivits'].starting_structures, 1)
        self.assertEqual(data['Xenos'].starting_structures, 3)
        for faction, profile in data.items():
            from four_factions.source_paths import colony_count
            self.assertEqual(colony_count({'round': 0}, {'faction': faction, 'structures': []}),
                             profile.starting_structures)
            self.assertEqual(profile.openings, load_catalog().get(faction, ()))
            self.assertTrue(profile.sources)
            if faction not in BASE_FACTIONS:
                self.assertIn('native-baseline', profile.coverage)

    def test_original_four_policy_ranks_and_memory_are_unchanged(self):
        env, snapshot = root()
        old, shared = Policies(), Policies(shared_factions=True)
        self.assertEqual(old.rank(env, snapshot), shared.rank(env, snapshot))
        self.assertEqual(old.memory, shared.memory)
        self.assertTrue(shared.clone().shared_factions)

    def test_all_eighteen_get_native_paid_previews_without_parent_mutation(self):
        seen = set()
        for number in range(80):
            env = Environment(f'shared-teacher-base-{number}', 2000)
            snapshot = json.loads(env.snapshot_json())
            lineup = {p['faction'] for p in snapshot['state']['players']}
            if lineup <= seen:
                continue
            policies = Policies(shared_factions=True)
            for _ in range(60):
                actor = snapshot['player']
                faction = snapshot['state']['players'][actor]['faction']
                # Reach real R1 decisions cheaply; setup/other turns are test scaffolding.
                if (snapshot['state']['round'] == 1 and 'ActionPhase' in snapshot['state']['phase']
                        and faction not in seen):
                    original = env.snapshot_json()
                    ranks = policies.rank(env, snapshot)
                    self.assertEqual(env.snapshot_json(), original)
                    self.assertEqual(len(ranks), len(snapshot['candidates']))
                    self.assertTrue(all(math.isfinite(score) for score, _ in ranks))
                    eligible = [i for i, rank in enumerate(ranks) if not blocked(rank)]
                    self.assertTrue(eligible)
                    index = max(eligible, key=lambda i: (ranks[i][0], -i))
                    after = env.fork(snapshot['decision_id'], index)
                    self.assertEqual(json.loads(after.snapshot_json())['steps'], snapshot['steps']+1)
                    seen.add(faction)
                index = next((i for i, c in enumerate(snapshot['candidates'])
                              if c['action']['type'] == 'Pass'), 0)
                env.step(snapshot['decision_id'], index)
                snapshot = json.loads(env.snapshot_json())
                if snapshot['state']['round'] > 1:
                    break
            if seen == set(FACTIONS):
                break
        self.assertEqual(seen, set(FACTIONS))

    def test_bescods_upgrade_goal_uses_its_real_building_graph(self):
        _, snapshot = root()
        player = snapshot['state']['players'][snapshot['player']]
        player['faction'] = 'Bescods'  # Pure predicate fixture, not native execution evidence.
        site = player['structures'][0]['hex']
        player['structures'][0]['kind'] = 'ResearchLab'
        pi = Goal('PI', 'upgrade', site, 'PlanetaryInstitute')
        self.assertTrue(viable(snapshot, snapshot['player'], pi))
        self.assertTrue(predicate_for(snapshot, pi)({'type': 'Upgrade', 'coord': site,
                                                    'to': 'PlanetaryInstitute'}))
        self.assertEqual(funding_need(snapshot, pi), {'ore': 4, 'credits': 6})
        player['structures'][0]['kind'] = 'TradingStation'
        ac = Goal('AC', 'upgrade', site, 'Science')
        self.assertTrue(predicate_for(snapshot, ac)({'type': 'Upgrade', 'coord': site,
                                                    'to': {'Academy': 'Science'}}))

    def test_ivits_does_not_get_the_three_separate_federation_goal(self):
        from four_factions.preparation import goals_for
        for number in range(30):
            env = Environment(f'ivits-shared-profile-{number}', 2000)
            snapshot = json.loads(env.snapshot_json())
            for _ in range(50):
                if (snapshot['state']['players'][snapshot['player']]['faction'] == 'Ivits'
                        and snapshot['state']['round'] == 1):
                    goals = goals_for(snapshot)
                    self.assertFalse(any(g.family == 'federations' for g in goals))
                    self.assertTrue(any(g.name == 'extend-single-federation' for g in goals))
                    return
                index = next((i for i, c in enumerate(snapshot['candidates'])
                              if c['action']['type'] == 'Pass'), 0)
                env.step(snapshot['decision_id'], index)
                snapshot = json.loads(env.snapshot_json())
                if snapshot['state']['round'] > 1:
                    break
        self.fail('No real Ivits R1 fixture found')

    def test_wrapper_enables_shared_search_and_bgg_without_changing_time_bounds(self):
        teacher = SharedTeacher('test')
        self.assertTrue(teacher.shared_factions and teacher.bgg_openings)
        self.assertEqual((teacher.target_seconds, teacher.maximum_seconds), (60, 300))

    def test_unknown_faction_does_not_silently_use_another_teacher(self):
        env = Environment('teacher-scope-diagnostic', 2000)
        snapshot = json.loads(env.snapshot_json())
        snapshot['state']['players'][0]['faction'] = 'UnknownFaction'
        with patch('four_factions.timed.TimedPreparationTeacher.choose') as run:
            with self.assertRaisesRegex(ValueError, 'approved shared teacher profile'):
                SharedTeacher('test').choose(snapshot)
            run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
