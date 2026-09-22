import copy
import gzip
import json
from pathlib import Path
import unittest
from economy.test_teacher import fixture, line_board
from integrated.features import (ADVANCED_IDS, IMMEDIATE, PASS, EVENT, RESOURCE_ACTIONS,
    advanced_value, income, knowledge_budget_value, counters, sector_at)
from integrated.teacher import IntegratedTeacher, reserve_adjustment


class IntegratedTests(unittest.TestCase):
    def setUp(self):
        self.s,self.p=fixture();self.state=self.s['state'];line_board(self.state)
        self.p['structures']=[{'hex':'0,0','kind':'ResearchLab'},{'hex':'2,0','kind':'Mine'}]
        self.p['tech_tiles']=[];self.p['covered_tech_tiles']=[];self.p['artifacts']=[]
        self.p['artifact_mines']=[];self.p['federated_hexes']=[]
        self.p['federation_tokens']=[1];self.p['gray_federation_tokens']=[]
        self.p['research_tracks']={k:0 for k in self.p['research_tracks']}
        self.state['round']=1;self.state['final_scoring_tiles']=[]
        self.state['board']['sectors']=[{'id':1,'rotation':0,'origin':'0,0'}]
        self.p['resources'].update(ore=6,credits=10,knowledge=0,qic=0)
        self.p['resources']['power'].update(bowl1=2,bowl2=4,bowl3=0)
        self.teacher=IntegratedTeacher()

    def test_all_21_advanced_ids_have_exactly_one_effect_family(self):
        self.assertEqual(ADVANCED_IDS,set(range(1,23))-{18})
        self.assertEqual(sum(map(len,(IMMEDIATE,PASS,EVENT,RESOURCE_ACTIONS)))+1,21)
        for tile in ADVANCED_IDS:
            self.assertGreaterEqual(advanced_value(self.state,self.p,tile),0)
        with self.assertRaises(ValueError):advanced_value(self.state,self.p,18)

    def test_immediate_not_multiplied_by_rounds_pass_is(self):
        early_immediate=advanced_value(self.state,self.p,10)
        early_pass=advanced_value(self.state,self.p,7)
        self.state['round']=6
        self.assertEqual(advanced_value(self.state,self.p,10),early_immediate)
        self.assertEqual(advanced_value(self.state,self.p,7),3)
        self.assertGreater(early_pass,3)

    def test_resource_actions_have_current_round_use_at_round6(self):
        early=advanced_value(self.state,self.p,20)
        self.state['round']=6
        self.assertGreater(advanced_value(self.state,self.p,20),0)
        self.assertLess(advanced_value(self.state,self.p,20),early)

    def test_income_counts_permanent_sources_and_science5_stops_income(self):
        self.p['structures'].append({'hex':'3,0','kind':{'Academy':'Science'}})
        self.p['tech_tiles']=[5];self.p['artifacts']=[3];self.p['research_tracks']['science']=4
        self.p['booster']=13
        self.assertEqual(income(self.p)['knowledge'],10)
        self.p['covered_tech_tiles']=[5];self.p['research_tracks']['science']=5
        self.assertEqual(income(self.p)['knowledge'],5)
        self.p['structures'][-1]['kind']={'Academy':'Qic'}
        self.assertEqual(income(self.p)['knowledge'],3)

    def test_research_budget_not_blind_even_bonus(self):
        benefit_3_to_4=knowledge_budget_value(0,4,2)-knowledge_budget_value(0,3,2)
        benefit_4_to_5=knowledge_budget_value(0,5,2)-knowledge_budget_value(0,4,2)
        self.assertGreater(benefit_3_to_4,benefit_4_to_5)
        self.assertGreater(knowledge_budget_value(3,1,1),knowledge_budget_value(0,2,1))
        self.assertLess(knowledge_budget_value(3,1,1,spend=2),knowledge_budget_value(3,1,1))

    def test_covering_income_has_cost_but_spent_immediate_tile_does_not(self):
        self.p['tech_tiles']=[5,7]
        self.state['research_board']['lost_fleet_advanced_tech_tile']=20
        first=self.teacher.technology(self.state,self.p,{'kind':'LostFleetAdvanced','covered_tile':5,'advance_track':None})
        second=self.teacher.technology(self.state,self.p,{'kind':'LostFleetAdvanced','covered_tile':7,'advance_track':None})
        self.assertGreater(second,first)

    def test_acquisition_counters_use_post_upgrade_building(self):
        self.p['structures'][0]['kind']='TradingStation'
        self.p['tech_tiles']=[7];self.state['research_board']['lost_fleet_advanced_tech_tile']=1
        choice={'kind':'LostFleetAdvanced','covered_tile':7,'advance_track':None}
        before=self.teacher.technology(self.state,self.p,choice)
        self.teacher._candidate={'type':'Upgrade','coord':'0,0','to':'ResearchLab'}
        after=self.teacher.technology(self.state,self.p,choice)
        self.assertEqual(before-after,4)

    def test_terraforming_before_paid_builds_not_fixed_late_round(self):
        self.p['research_tracks']['terraforming']=1
        self.state['board']['hexes']['1,0']['planet']['planet_type']='Volcanic'
        self.state['board']['hexes']['3,0']['planet']['planet_type']='Volcanic'
        with_targets=self.teacher.research(self.state,self.p,'Terraforming')
        for cell in self.state['board']['hexes'].values():
            if cell['planet']:cell['planet']['planet_type']='Desert'
        no_targets=self.teacher.research(self.state,self.p,'Terraforming')
        self.assertGreater(with_targets,no_targets)

    def test_navigation_values_reachable_targets(self):
        self.p['structures']=self.p['structures'][:1]
        self.p['research_tracks']['navigation']=1
        with_targets=self.teacher.research(self.state,self.p,'Navigation')
        for c in ('1,0','2,0','3,0','4,0'):
            self.state['board']['hexes'][c]['planet']['owner']=2
        self.assertGreater(with_targets,self.teacher.research(self.state,self.p,'Navigation'))

    def test_green_token_and_actual_advanced_value_guide_track_preparation(self):
        self.p['tech_tiles']=[7];self.p['research_tracks']['ai']=3
        self.state['research_board']['advanced_tech_tiles'][2]=20
        funded=self.teacher.research(self.state,self.p,'ArtificialIntelligence')
        self.p['federation_tokens']=[]
        self.assertGreater(funded,self.teacher.research(self.state,self.p,'ArtificialIntelligence'))

    def test_reserve_discards_not_ordinary_power_spending(self):
        action={'type':'FormFederation','satellite_hexes':['1,0','3,0','4,0']}
        self.assertLess(reserve_adjustment(self.state,self.p,action),0)
        self.assertEqual(reserve_adjustment(self.state,self.p,{'type':'PowerAction','id':1}),0)
        self.assertLess(reserve_adjustment(self.state,self.p,{'type':'FreeAction','kind':'BurnPower','count':1}),0)
        self.assertEqual(reserve_adjustment(self.state,self.p,{'type':'TFMarsGaiaFormation'}),0)
        self.state['round']=6
        self.assertEqual(reserve_adjustment(self.state,self.p,action),0)

    def test_academy_science_early_qic_late(self):
        science={'type':'Upgrade','coord':'0,0','to':{'Academy':'Science'},'tech_tile_choice':None}
        qic=science|{'to':{'Academy':'Qic'}}
        self.assertGreater(self.teacher.score(self.s,science)[0],self.teacher.score(self.s,qic)[0])
        self.state['round']=6
        self.assertGreater(self.teacher.score(self.s,qic)[0],self.teacher.score(self.s,science)[0])

    def test_charge_uses_actual_cost_and_avoids_expensive_early_offer(self):
        self.p['vp']=20;self.p['explored_ships']=[0]
        self.state['phase']={'ChargePowerPending':{'queue':[{'player':1,'max_power':5}]}}
        self.assertLess(self.teacher.score(self.s,{'type':'ChargePower','accept':True})[0],self.teacher.score(self.s,{'type':'ChargePower','accept':False})[0])
        self.state['phase']['ChargePowerPending']['queue'][0]['max_power']=1
        self.assertGreater(self.teacher.score(self.s,{'type':'ChargePower','accept':True})[0],0)

    def test_deep_sector_rotation_does_not_count_interspace_as_sector(self):
        self.state['board']['sectors']=[{'id':11,'rotation':1,'origin':'0,0'}]
        self.assertEqual(sector_at(self.state,'-1,1'),11)
        self.assertIsNone(sector_at(self.state,'2,0'))

    def test_rank_is_finite_deterministic_and_does_not_mutate_snapshot(self):
        self.s['candidates']=[{'action':{'type':'ResearchAdvance','track':'Science'}},
                              {'action':{'type':'Upgrade','coord':'0,0','to':{'Academy':'Science'},'tech_tile_choice':None}}]
        before=copy.deepcopy(self.s)
        self.assertEqual(self.teacher.choose(self.s),self.teacher.choose(self.s))
        self.assertEqual(self.s,before)
        self.assertIsNone(self.teacher._candidate)
        self.assertIsNone(self.teacher._snapshot)


class IntegrationRegressionTests(unittest.TestCase):
    setUp = IntegratedTests.setUp
    def test_immediate_token_reward_counts_toward_reserve(self):
        base={'type':'FormFederation','satellite_hexes':['1,0','3,0'],'token':{'kind':1}}
        reward=base|{'token':{'kind':13}}
        self.assertGreater(reserve_adjustment(self.state,self.p,reward),reserve_adjustment(self.state,self.p,base))

    def test_future_knowledge_spend_can_use_future_income(self):
        self.assertEqual(knowledge_budget_value(0,4,1,spend=2),.7)

    def test_waiting_considers_funded_xenos_pi_threshold_not_round6(self):
        self.p['structures']=[{'hex':'0,0','kind':'Mine'},{'hex':'1,0','kind':'TradingStation'},
                              {'hex':'2,0','kind':'TradingStation'}]
        # These are synthetic routing inputs: only compare heuristic, not engine legality.
        action={'type':'FormFederation','hexes':['0,0','1,0','2,0'],'satellite_hexes':['3,0']*8,'token':{'kind':1}}
        self.state['research_board']['federation_tokens']=[1,1]
        self.assertGreater(self.teacher.waiting_value(self.state,self.p,action),0)
        self.state['round']=6
        self.assertEqual(self.teacher.waiting_value(self.state,self.p,action),0)

    def test_economy_side_credit_income(self):
        self.p['research_tracks']['economy']=4
        self.state['research_board']['economy_research_tile_side']='Power'
        self.assertEqual(income(self.p,self.state)['credits'],2)

    def test_research_trigger_has_no_value_with_no_track_room(self):
        self.p['research_tracks']={k:5 for k in self.p['research_tracks']}
        self.p['resources']['knowledge']=20
        self.assertEqual(advanced_value(self.state,self.p,8),0)

    def test_terraforming_five_values_reserved_token(self):
        self.state['round']=6
        self.p['research_tracks']['terraforming']=4
        self.state['research_board']['terraforming_level_5_token']=1
        value=self.teacher.research(self.state,self.p,'Terraforming')
        self.state['research_board']['terraforming_level_5_token']=None
        self.assertEqual(value-self.teacher.research(self.state,self.p,'Terraforming'),12)

    def test_gaia_five_values_printed_vp_and_natural_gaia(self):
        self.state['round']=6;self.p['research_tracks']['gaia']=4
        self.state['board']['hexes']['0,0']['planet']['planet_type']='Gaia'
        self.assertEqual(self.teacher.research(self.state,self.p,'GaiaProject'),9)

    def test_untracked_lost_mine_matches_engine_counter(self):
        self.state['board']['lost_planet']='4,0'
        self.state['board']['hexes']['4,0']['planet']['owner']=1
        self.assertEqual(counters(self.state,self.p)['mines'],2)

if __name__=='__main__':unittest.main()
