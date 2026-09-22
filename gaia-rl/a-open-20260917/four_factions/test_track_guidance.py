"""Conditional B19 guidance; synthetic geometry is not a recorded expert game."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from gaia_rl import Environment
from four_factions.track_guidance import expansion_potential, guide_goals, funded_colonies, budget


def fixture(faction='Xenos', *, target='Desert', distance=2):
    snapshot = json.loads(Environment('quartet-pilot-20260913-27703', 2000).snapshot_json())
    state = snapshot['state']
    actor = next(i for i, p in enumerate(state['players']) if p['faction'] == faction)
    snapshot['player'] = actor
    state.update(round=2, phase={'ActionPhase': {}})
    player = state['players'][actor]
    player['research_tracks'] = dict.fromkeys(player['research_tracks'], 0)
    player['structures'] = [{'hex': '0,0', 'kind': 'Mine'}]
    player['resources'].update(ore=4, credits=6, knowledge=4, qic=0)
    player.update(tech_tiles=[], covered_tech_tiles=[], artifacts=[], artifact_mines=[], passed=False)
    planet = {'planet_type': target, 'owner': None, 'is_gaia_formed': False}
    state['board']['hexes'] = {f'{i},0': {'planet': None, 'structures': [], 'satellites': []}
                               for i in range(distance+1)}
    state['board']['hexes']['0,0'].update(
        planet={**planet, 'owner': actor}, structures=[{'owner': actor, 'kind': 'Mine'}])
    state['board']['hexes'][f'{distance},0']['planet'] = planet
    state['round_tiles'][1] = {'condition': 'BuildMine', 'vp_per_unit': 2}
    return snapshot, player


class TrackGuidanceTests(unittest.TestCase):
    def test_navigation_has_value_only_with_a_funded_new_destination(self):
        s, p = fixture()
        p['research_tracks']['navigation'] = 2
        self.assertGreater(expansion_potential(s['state'], p), 0)
        s['state']['board']['hexes']['2,0']['planet']['owner'] = 1
        self.assertEqual(expansion_potential(s['state'], p), 0)
        self.assertEqual(guide_goals(s), [])

    def test_navigation_one_followup_requires_knowledge_and_a_real_payoff(self):
        s, p = fixture()
        p['research_tracks']['navigation'] = 1
        funded = expansion_potential(s['state'], p)
        self.assertGreater(funded, 0)
        p['resources']['knowledge'] = 0
        self.assertEqual(expansion_potential(s['state'], p), 0)
        p['resources']['knowledge'] = 4
        s['state']['board']['hexes']['2,0']['planet'] = None
        self.assertEqual(expansion_potential(s['state'], p), 0)

    def test_natural_gaia_needs_entry_qic_and_is_not_a_gaiaforming_target(self):
        s, p = fixture(target='Gaia')
        p['research_tracks']['navigation'] = 2
        self.assertFalse(funded_colonies(s['state'], p))
        p['resources']['qic'] = 1
        self.assertIn('2,0', funded_colonies(s['state'], p))
        self.assertTrue(all(step.target != 'GaiaProject' for goal in guide_goals(s)
                            for step in goal.steps))

    def test_economy_is_a_bridge_only_when_it_unlocks_blocked_expansion(self):
        s, p = fixture(distance=1)
        p['resources']['credits'] = 0
        goals = guide_goals(s)
        self.assertTrue(any(g.name.startswith('B19-economy2-bridge') for g in goals))
        p['resources']['credits'] = 6
        self.assertFalse(any(g.name.startswith('B19-economy2-bridge') for g in guide_goals(s)))
        p['resources']['credits'] = 0
        p['research_tracks']['economy'] = 2
        self.assertFalse(any(step.target == 'Economy' for g in guide_goals(s) for step in g.steps))

    def test_navigation_then_colony_is_ordered_not_a_forced_action(self):
        from four_factions.preparation import funding_need
        s, p = fixture()
        goals = guide_goals(s)
        goal = next(g for g in goals if g.name.startswith('B19-navigation2'))
        self.assertEqual(goal.family, 'ordered')
        self.assertEqual([(g.family, g.target) for g in goal.steps],
                         [('research', 'Navigation'), ('colony', None)])
        self.assertEqual(goal.sources, ('B19',))
        self.assertEqual(p['research_tracks']['navigation'], 0)
        self.assertEqual(funding_need(s, goal), {'knowledge': 4})
        p['research_tracks']['navigation'] = 2
        self.assertEqual(funding_need(s, goal), {'ore': 1, 'credits': 2, 'qic': 0})

    def test_terraforming_uses_faction_home_cost_not_a_fixed_track_bonus(self):
        for faction, home, adjacent in [('Xenos', 'Desert', 'Volcanic'),
                ('HadschHallas', 'Oxide', 'Terra'), ('Terrans', 'Terra', 'Ice'),
                ('Taklons', 'Swamp', 'Titanium')]:
            s, p = fixture(faction, target=adjacent, distance=1)
            p['research_tracks']['terraforming'] = 1
            self.assertTrue(any(g.name.startswith('B19-terraforming3') for g in guide_goals(s)), faction)
            p['research_tracks']['terraforming'] = 3
            self.assertGreater(expansion_potential(s['state'], p), 0, faction)
            s['state']['board']['hexes']['1,0']['planet']['planet_type'] = home
            self.assertEqual(expansion_potential(s['state'], p), 0, faction)

    def test_no_phantom_mines_at_inventory_limit_or_endgame_or_other_factions(self):
        s, p = fixture()
        p['research_tracks']['navigation'] = 2
        for change in ('supply', 'round', 'faction'):
            branch = deepcopy(s)
            q = branch['state']['players'][branch['player']]
            if change == 'supply':
                q['structures'] *= 8
            elif change == 'round':
                branch['state']['round'] = 6
            else:
                q['faction'] = 'Ivits'
            self.assertEqual(expansion_potential(branch['state'], q), 0)
            self.assertEqual(guide_goals(branch), [])

    def test_guide_does_not_mutate_state_or_sum_competing_colony_plans(self):
        s, p = fixture()
        p['research_tracks']['navigation'] = 2
        original = deepcopy(s)
        one = expansion_potential(s['state'], p)
        guide_goals(s)
        self.assertEqual(s, original)
        # An unrelated income increase does not create a navigation-level bonus.
        with patch('four_factions.value.production', return_value=[15, 30, 15, 0, 0, 0, 0]):
            self.assertEqual(expansion_potential(s['state'], p), one)

    def test_colonies_share_a_budget_and_forecast_income_respects_caps(self):
        s, p = fixture()
        p['research_tracks']['navigation'] = 2
        p['resources']['ore'] = 1
        s['state']['board']['hexes']['0,1'] = {'planet': None, 'structures': []}
        s['state']['board']['hexes']['0,2'] = deepcopy(s['state']['board']['hexes']['2,0'])
        with patch('four_factions.value.production', return_value=[0]*7):
            both = expansion_potential(s['state'], p)
            s['state']['board']['hexes']['0,2']['planet'] = None
            self.assertEqual(expansion_potential(s['state'], p), both)
        with patch('four_factions.value.production', return_value=[99]*7):
            self.assertEqual(budget(s['state'], p)['ore'], 15)
            self.assertEqual(budget(s['state'], p)['credits'], 30)
            self.assertEqual(budget(s['state'], p)['knowledge'], 15)

    def test_lost_target_invalidates_research_plan_and_regular_choices_remain(self):
        from four_factions.preparation import goals_for, viable
        s, p = fixture()
        # The full native board is used for unrelated ship/advanced proposals.
        from four_factions.test_preparation import root
        _, native = root()
        old = goals_for(native)
        augmented = goals_for(native, guide_tracks=True)
        self.assertTrue(all(goal in augmented for goal in old))
        self.assertFalse(any('B19' in goal.sources for goal in old))
        goal = next(g for g in guide_goals(s) if g.name.startswith('B19-navigation2'))
        self.assertTrue(viable(s, s['player'], goal))
        s['state']['board']['hexes']['2,0']['planet']['owner'] = (s['player']+1)%4
        self.assertFalse(viable(s, s['player'], goal))

    def test_control_leaf_is_unchanged_and_B_replaces_not_duplicates_expansion(self):
        from four_factions.preparation import leaf_value
        from four_factions.value import expansion_value
        from four_factions.test_preparation import root
        _, native = root()
        with patch('four_factions.track_guidance.expansion_potential', side_effect=AssertionError('B only')):
            a = [leaf_value(native, actor, p) for actor, p in enumerate(native['state']['players'])]
        for actor, p in enumerate(native['state']['players']):
            b = leaf_value(native, actor, p, guide_tracks=True)
            replaced = 0 if p['faction'] in ('Xenos', 'HadschHallas') else expansion_value(native['state'], p)
            self.assertAlmostEqual(b-a[actor], expansion_potential(native['state'], p)-replaced)

    def test_rollout_dispatches_the_root_factions_leaf_not_the_opponents(self):
        import time
        from four_factions.preparation import rollout, Policies, Goal
        from four_factions.test_preparation import root
        env, native = root()
        actor = native['player']
        faction = native['state']['players'][actor]['faction']
        with patch('four_factions.preparation.reached_horizon', return_value=True), \
                patch('four_factions.preparation.leaf_value', return_value=123) as leaf:
            rollout(env, native, 0, Goal('current'), Policies(delta_factions=(faction,)),
                    time.monotonic()+10)
            self.assertTrue(leaf.call_args.kwargs['guide_tracks'])
            self.assertEqual(leaf.call_args.args[1], actor)
            other = next(p['faction'] for p in native['state']['players'] if p['faction'] != faction)
            rollout(env, native, 0, Goal('current'), Policies(delta_factions=(other,)),
                    time.monotonic()+10)
            self.assertFalse(leaf.call_args.kwargs['guide_tracks'])


if __name__ == '__main__':
    unittest.main()
