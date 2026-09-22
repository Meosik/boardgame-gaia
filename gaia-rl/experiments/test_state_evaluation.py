import copy
import json
import unittest

from gaia_rl._native import Environment
from faction_learning import FACTIONS
from state_evaluation import evaluate_state, engine_facts, planet_opportunities


def opportunity_fixture(*, target='Terra', distance=1, count=3):
    state = json.loads(Environment('quartet-pilot-20260913-424', 2000).snapshot_json())['state']
    actor = next(p['player_id'] for p in state['players'] if p['faction'] == 'Xenos')
    player = state['players'][actor]
    for p in state['players']:
        p['structures'] = []
        p['research_tracks'] = dict.fromkeys(p['research_tracks'], 0)
    state.update(round=2, phase={'ActionPhase': {'active_player': actor}})
    player['structures'] = [{'hex': '0,0', 'kind': 'Mine'}]
    player['research_tracks'].update(terraforming=1, navigation=1, economy=1)
    player['resources'].update(ore=15, credits=30, knowledge=4, qic=0)
    player.update(tech_tiles=[], covered_tech_tiles=[], advanced_tech_tiles=[], artifacts=[],
                  artifact_mines=[], passed=False, federation_tokens=[])
    cells = {}
    for step in range(distance+1):
        for q,r in ((step,0),(0,step),(-step,step)):
            coord = f'{q},{r}'
            cells[coord] = {'coord': coord, 'planet': None, 'space_tile_kind': None,
                            'structures': [], 'satellites': []}
    def planet(kind, owner=None):
        return {'planet_type': kind, 'owner': owner, 'is_gaia_formed': False}
    cells['0,0'].update(planet=planet('Desert',actor), structures=[{'owner':actor,'kind':'Mine'}])
    for coord in (f'{distance},0', f'0,{distance}', f'-{distance},{distance}')[:count]:
        cells[coord]['planet'] = planet(target)
    state['board'].update(hexes=cells, lost_planet=None)
    state['round_tiles'][1] = {'id':1,'condition':'BuildMine','vp_per_unit':2}
    return state, actor


class StateEvaluationTests(unittest.TestCase):
    def setUp(self):
        env = Environment('quartet-pilot-20260913-424', 2000)
        self.state = json.loads(env.snapshot_json())['state']

    def test_all_factions_use_the_same_breakdown(self):
        player = copy.deepcopy(self.state['players'][0])
        keys = None
        for faction in FACTIONS:
            player['faction'] = faction
            state = {**self.state, 'players': [player]}
            result = evaluate_state(state, 0)
            self.assertAlmostEqual(result.total_vp, sum(result.breakdown.values()))
            self.assertEqual(result.breakdown['faction_modifier'], 0)
            if keys is None:
                keys = set(result.breakdown)
            self.assertEqual(set(result.breakdown), keys)

    def test_resource_floor_and_state_only(self):
        for resource in ('ore', 'credits', 'knowledge'):
            before = evaluate_state(self.state, 0)
            changed = copy.deepcopy(self.state)
            changed['players'][0]['resources'][resource] += 1
            after = evaluate_state(changed, 0)
            self.assertGreaterEqual(after.total_vp - before.total_vp, 1 / 3)
            self.assertEqual(self.state['players'][0]['resources'][resource],
                             changed['players'][0]['resources'][resource] - 1)

    def test_research_scores_only_final_levels(self):
        state = copy.deepcopy(self.state)
        state['players'][0]['research_tracks'] = {
            name: 0 for name in state['players'][0]['research_tracks']
        }
        baseline = evaluate_state(state, 0)
        state['players'][0]['research_tracks']['science'] = 5
        self.assertEqual(evaluate_state(state, 0).total_vp - baseline.total_vp, 12)

    def test_setup_bid_is_counted_once(self):
        state = copy.deepcopy(self.state)
        baseline = evaluate_state(state, 0)
        state['players'][0]['setup_bid_vp'] += 2
        after = evaluate_state(state, 0)
        self.assertEqual(after.total_vp - baseline.total_vp, -2)
        self.assertEqual(after.breakdown['bid_penalty_vp'] - baseline.breakdown['bid_penalty_vp'], -2)

    def test_terminal_uses_exact_native_score(self):
        state = copy.deepcopy(self.state)
        state['phase'] = {'Ended': {'final_scores': [[i, 100 + i] for i in range(4)]}}
        result = evaluate_state(state, 0)
        self.assertEqual(result.total_vp, 100)
        self.assertEqual(result.breakdown, {'native_final_score': 100})

    def test_high_terraform_costs_favor_terraforming_over_economy(self):
        state, actor = opportunity_fixture()
        terraform, economy = copy.deepcopy(state), copy.deepcopy(state)
        terraform['players'][actor]['research_tracks']['terraforming'] += 1
        economy['players'][actor]['research_tracks']['economy'] += 1
        self.assertGreater(evaluate_state(terraform,actor).total_vp, evaluate_state(economy,actor).total_vp)

    def test_out_of_range_home_planets_favor_navigation_over_economy(self):
        state, actor = opportunity_fixture(target='Desert',distance=2)
        nav, economy = copy.deepcopy(state), copy.deepcopy(state)
        nav['players'][actor]['research_tracks']['navigation'] += 1
        economy['players'][actor]['research_tracks']['economy'] += 1
        self.assertGreater(evaluate_state(nav,actor).total_vp,evaluate_state(economy,actor).total_vp)

    def test_same_knowledge_and_invested_levels_favor_concentration(self):
        focused, actor = opportunity_fixture(count=0)
        tracks = focused['players'][actor]['research_tracks']
        tracks.update(dict.fromkeys(tracks,0))
        tracks['science'] = 2
        spread = copy.deepcopy(focused)
        spread['players'][actor]['research_tracks'].update(science=1,economy=1)
        self.assertGreater(evaluate_state(focused,actor).total_vp,evaluate_state(spread,actor).total_vp)

    def test_unchanged_native_range_or_cost_allows_zero_opportunity_gain(self):
        for track, key in (('terraforming','terraform_ore_per_step'),('navigation','navigation_range')):
            state,actor = opportunity_fixture()
            player = state['players'][actor]
            rules = engine_facts(state,player)
            for level in range(len(rules[key])-1):
                player['research_tracks'][track] = level
                before = planet_opportunities(state,player)
                player['research_tracks'][track] = level+1
                after = planet_opportunities(state,player)
                if rules[key][level] == rules[key][level+1]:
                    self.assertEqual(before,after,(track,level))

    def test_gaia_entry_cost_and_project_capacity_are_distinct(self):
        state,actor = opportunity_fixture(target='Gaia',count=1)
        player = state['players'][actor]
        self.assertEqual(evaluate_state(state,actor).breakdown['gaia_opportunity'],0)
        player['resources']['qic'] = 1
        ready = evaluate_state(state,actor)
        self.assertGreater(ready.breakdown['gaia_opportunity'],0)
        self.assertEqual(ready.breakdown['expansion_opportunity'],0)
        state['board']['hexes']['1,0']['planet']['planet_type'] = 'Transdim'
        self.assertEqual(evaluate_state(state,actor).breakdown['gaia_opportunity'],0)
        player['research_tracks']['gaia'] = 1
        player['gaiaformers_total'] = 1
        player['gaiaformers_deployed'] = player['gaiaformers_in_gaia_area'] = 0
        player['resources']['power'].update(bowl1=6,bowl2=0,bowl3=0)
        forming = evaluate_state(state,actor)
        self.assertGreater(forming.breakdown['gaia_opportunity'],0)
        self.assertEqual(forming.opportunities[0].power_tokens,6)
        player['resources']['power']['bowl1'] = 5
        self.assertEqual(evaluate_state(state,actor).breakdown['gaia_opportunity'],0)

    def test_project_pays_range_twice_and_reservation_only_once(self):
        state,actor = opportunity_fixture(target='Transdim',distance=2,count=1)
        player = state['players'][actor]
        player['research_tracks']['gaia'] = 1
        player['resources']['qic'] = 2
        self.assertEqual(planet_opportunities(state,player)[0].qic,2)
        state['board']['hexes']['2,0']['planet']['owner'] = actor
        self.assertEqual(planet_opportunities(state,player)[0].qic,1)

    def test_no_cross_gap_distance_or_duplicate_budget(self):
        state,actor = opportunity_fixture(target='Desert',distance=2,count=1)
        state['players'][actor]['resources']['qic'] = 10
        del state['board']['hexes']['1,0']
        self.assertEqual(evaluate_state(state,actor).opportunities,())
        state,actor = opportunity_fixture(target='Desert')
        state['players'][actor]['resources']['ore'] = 1
        result = evaluate_state(state,actor)
        self.assertEqual(len(result.opportunities),1)
        self.assertEqual(evaluate_state(state,actor,top_n=0).opportunities,())

    def test_ties_and_terminal_rewards_are_not_heuristic_bonuses(self):
        from state_evaluation import final_rank_value
        facts = {'final_tiles':[{'values':[[0,2],[1,2],[2,1],[3,0]],'awards':[18,12,6,0]}]}
        self.assertEqual(final_rank_value(facts,0),15)

    def test_tiles_are_individually_broken_down_and_covered_is_excluded(self):
        state,actor = opportunity_fixture()
        player = state['players'][actor]
        player['tech_tiles'] = [3,7]
        result = evaluate_state(state,actor)
        rows = {r['tile']:r for r in result.tile_values if not r['advanced']}
        self.assertEqual(rows[7]['expected_vp'],0)  # Immediate VP has already been awarded.
        self.assertGreater(rows[3]['expected_vp'],0)
        player['covered_tech_tiles'] = [3]
        self.assertEqual(evaluate_state(state,actor).breakdown['technology_tiles'],0)

    def test_state_is_immutable_and_breakdown_adds_up(self):
        state,actor = opportunity_fixture()
        before = copy.deepcopy(state)
        result = evaluate_state(state,actor)
        self.assertEqual(state,before)
        self.assertEqual(result,evaluate_state(state,actor))
        self.assertAlmostEqual(result.total_vp,sum(result.breakdown.values()))

    def test_level_five_requires_token_and_unclaimed_track(self):
        state,actor = opportunity_fixture(count=0)
        player = state['players'][actor]
        player['research_tracks'] = dict.fromkeys(player['research_tracks'],5)
        player['research_tracks']['science'] = 4
        self.assertEqual(evaluate_state(state,actor).breakdown['research_progress'],0)
        player['federation_tokens'] = [1]
        self.assertGreater(evaluate_state(state,actor).breakdown['research_progress'],0)
        state['players'][(actor+1)%4]['research_tracks']['science'] = 5
        self.assertEqual(evaluate_state(state,actor).breakdown['research_progress'],0)


if __name__ == '__main__':
    unittest.main()
