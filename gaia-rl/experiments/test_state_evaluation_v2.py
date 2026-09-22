import copy
import json
import unittest

from gaia_rl._native import evaluation_successor_json
from test_state_evaluation import opportunity_fixture
from state_evaluation import (evaluate_state, engine_facts, power_value, INCOME_DISCOUNT,
                              income_vp, GAIA_RETURN_DISCOUNT)


class StateEvaluationV2Tests(unittest.TestCase):
    def future(self, state, actor):
        return evaluate_state(state,actor).breakdown['future_income']

    def test_build_upgrade_and_research_raise_native_next_income(self):
        state,actor=opportunity_fixture(count=0)
        player=state['players'][actor]
        previous=self.future(state,actor)
        # Additional mine; board and player must describe the same structure.
        player['structures'].append({'hex':'1,0','kind':'Mine'})
        state['board']['hexes']['1,0'].update(planet={'planet_type':'Desert','owner':actor,'is_gaia_formed':False},
                                            structures=[{'owner':actor,'kind':'Mine'}])
        current=self.future(state,actor); self.assertGreater(current,previous)
        for target in ('TradingStation','ResearchLab'):
            previous=current
            player['structures'][-1]['kind']=target
            state['board']['hexes']['1,0']['structures'][0]['kind']=target
            current=self.future(state,actor)
            self.assertGreater(current,previous,target)
        for track in ('economy','science'):
            previous=self.future(state,actor)
            player['research_tracks'][track]+=1
            self.assertGreater(self.future(state,actor),previous,track)

    def test_native_build_and_upgrade_successors_raise_income(self):
        state,actor=opportunity_fixture(target='Desert',count=1)
        previous=self.future(state,actor)
        for action in ({'type':'Build','coord':'1,0'},
                       {'type':'Upgrade','coord':'1,0','to':'TradingStation'},
                       {'type':'Upgrade','coord':'1,0','to':'ResearchLab'}):
            state['phase']={'ActionPhase':{'active_player':actor}}
            state=json.loads(evaluation_successor_json(json.dumps(state),actor,json.dumps(action)))
            current=self.future(state,actor)
            self.assertGreater(current,previous,action)
            previous=current

    def test_income_is_native_and_tile_not_counted_twice(self):
        state,actor=opportunity_fixture(count=0)
        p=state['players'][actor];p['tech_tiles']=[];p['booster']=None
        before=evaluate_state(state,actor)
        p['tech_tiles']=[3]
        after=evaluate_state(state,actor)
        self.assertAlmostEqual(after.breakdown['future_income']-before.breakdown['future_income'],1.0)
        self.assertEqual(after.breakdown['technology_tiles'],before.breakdown['technology_tiles'])
        p['covered_tech_tiles']=[3]
        self.assertAlmostEqual(self.future(state,actor),before.breakdown['future_income'])
        p['booster']=1
        facts=engine_facts(state,p)
        self.assertAlmostEqual(self.future(state,actor),INCOME_DISCOUNT*income_vp(facts['income']))
        self.assertGreater(self.future(state,actor),before.breakdown['future_income'])
        state['round']=6
        self.assertEqual(self.future(state,actor),0)

    def test_brainstone_off_capacity_and_discounted_native_return(self):
        state,actor=opportunity_fixture(target='Transdim',count=1)
        p=state['players'][actor];p['faction']='Taklons';p['research_tracks']['gaia']=1
        p.update(gaiaformers_total=1,gaiaformers_deployed=0,gaiaformers_in_gaia_area=0)
        p['resources']['spent_gaia_formers']=0
        p['resources']['power'].update(bowl1=5,bowl2=0,bowl3=0,brainstone='Area3')
        on=evaluate_state(state,actor)
        off=evaluate_state(state,actor,conserve_resources=False)
        self.assertEqual(on.breakdown['gaia_opportunity'],0)
        self.assertGreater(off.breakdown['gaia_opportunity'],0)
        action={'type':'GaiaFormation','coord':'1,0'}
        after=json.loads(evaluation_successor_json(json.dumps(state),actor,json.dumps(action)))
        power=after['players'][actor]['resources']['power']
        self.assertEqual(power['brainstone'],'Gaia')
        result=evaluate_state(after,actor,conserve_resources=False)
        self.assertAlmostEqual(result.breakdown['power_stock'],GAIA_RETURN_DISCOUNT/3)
        after['round']=6
        self.assertEqual(evaluate_state(after,actor,conserve_resources=False).breakdown['power_stock'],0)

    def test_reachable_ship_options_use_native_costs_and_availability(self):
        state,actor=opportunity_fixture(target='Terra',count=1)
        p=state['players'][actor];p['resources'].update(qic=0,credits=20,ore=10,knowledge=0)
        state['board']['spaceship_tiles']={'TFMars':'0,1'}
        p['vp']=30
        p['resources']['power'].update(bowl1=0,bowl2=0,bowl3=0)
        facts=engine_facts(state,p)
        self.assertEqual([s['ship'] for s in facts['ships']],['TFMars'])
        row=facts['ships'][0]
        self.assertEqual(row['entry_payout']['vp'],-5)  # Rule cost, NOT a net ship penalty.
        self.assertTrue(any(o['action']['type']=='SpaceshipCreditTerraform' for o in row['options']))
        # Already explored: native entry payment is sunk, not charged again.
        entered=json.loads(evaluation_successor_json(json.dumps(state),actor,json.dumps({'type':'ExploreSpaceship','ship':'TFMars'})))
        owned=evaluate_state(entered,actor).ship_values[0]
        self.assertTrue(owned['owned']);self.assertEqual(owned['entry_net_vp'],0)
        self.assertGreater(owned['expected_vp'],0)
        entered['used_spaceship_actions']=[1,3,5,6,7,8,9,10,11,12,13,14]
        restricted=evaluate_state(entered,actor).ship_values[0]
        self.assertLess(restricted['expected_vp'],owned['expected_vp'])
        p['exploration_shuttles_available']=0
        self.assertEqual(engine_facts(state,p)['ships'],[])


if __name__=='__main__':
    unittest.main()
