import copy
import unittest

from integrated import test_teacher
from integrated.boosters import (INCOME, pass_vp, evaluate_booster, action_value,
                                 next_income, growth_value, charge)


class BoosterTests(unittest.TestCase):
    def setUp(self):
        test_teacher.IntegratedTests.setUp(self)
        self.state['spaceship_boards']=[b for b in self.state['spaceship_boards']
                                      if b['id'] in self.state['board']['spaceship_tiles']]

    def test_every_current_booster_mapped_and_unknown_rejected(self):
        self.assertEqual(set(INCOME),set(range(1,15)))
        before=copy.deepcopy(self.state)
        for booster in INCOME:
            self.assertGreaterEqual(evaluate_booster(self.state,self.p,booster).total,0)
        self.assertEqual(self.state,before)
        with self.assertRaises(ValueError):evaluate_booster(self.state,self.p,15)

    def test_printed_pass_effects_include_formers_not_only_deployed(self):
        self.p['structures']=[{'hex':'0,0','kind':'Mine'},{'hex':'1,0','kind':'TradingStation'},
            {'hex':'2,0','kind':'ResearchLab'},{'hex':'3,0','kind':'PlanetaryInstitute'},
            {'hex':'4,0','kind':{'Academy':'Science'}}]
        self.p['gaiaformers_total']=3;self.p['resources']['spent_gaia_formers']=1
        self.p['gaiaformers_deployed']=0
        self.assertEqual([pass_vp(self.state,self.p,i) for i in (1,3,4,6,7)], [3,1,8,6,2])
        self.state['board']['hexes']['0,0']['planet']['planet_type']='Gaia'
        self.assertEqual(pass_vp(self.state,self.p,11),1)
        self.state['board']['sectors']=[{'id':11,'origin':'0,0','rotation':0}]
        self.assertEqual(pass_vp(self.state,self.p,14),2)

    def test_initial_selection_has_same_knowledge_budget_as_next_round(self):
        self.p['resources']['knowledge']=1  # Permanent lab income2 ->3; booster reaches4.
        starting=evaluate_booster(self.state,self.p,1,starting=True)
        passing=evaluate_booster(self.state,self.p,1)
        self.assertGreater(starting.knowledge,2)
        self.assertEqual(starting.knowledge,passing.knowledge)
        self.p['resources']['knowledge']=0
        self.assertLess(evaluate_booster(self.state,self.p,1,starting=True).knowledge,1)

    def test_last_round_pass_has_no_new_booster_reward(self):
        self.state['round']=6
        self.assertEqual(evaluate_booster(self.state,self.p,None).total,0)
        self.assertEqual(evaluate_booster(self.state,self.p,4).total,0)
        self.state['round']=5
        self.assertGreater(evaluate_booster(self.state,self.p,4).total,0)

    def test_old_booster_does_not_change_new_choice_value(self):
        self.p['booster']=1
        first=evaluate_booster(self.state,self.p,3)
        self.p['booster']=4
        self.assertEqual(first,evaluate_booster(self.state,self.p,3))

    def test_income_prices_respond_to_scarcity(self):
        self.p['resources']['credits']=0
        poor=evaluate_booster(self.state,self.p,11).resources
        self.p['resources']['credits']=20
        self.assertGreater(poor,evaluate_booster(self.state,self.p,11).resources)

    def test_tokens_are_not_charge_and_do_not_grow_without_limit(self):
        self.p['resources']['power'].update(bowl1=0,bowl2=0,bowl3=2)
        scarce=evaluate_booster(self.state,self.p,2).power
        self.assertEqual(evaluate_booster(self.state,self.p,4).power,0)
        self.p['resources']['power']['bowl3']=12
        self.assertGreater(scarce,evaluate_booster(self.state,self.p,2).power)
        power={'bowl1':2,'bowl2':2,'bowl3':0};charge(power,4)
        self.assertEqual(power,{'bowl1':0,'bowl2':2,'bowl3':2})

    def test_known_pi_and_artifact_income_applied_before_charge(self):
        self.p['structures'].append({'hex':'3,0','kind':'PlanetaryInstitute'})
        self.p['artifacts']=[2]
        projected=next_income(self.state,self.p)
        self.assertEqual(projected['resources']['qic'],self.p['resources']['qic']+1)
        self.assertEqual(sum(projected['resources']['power'][k] for k in ('bowl1','bowl2','bowl3')),8)

    def test_range_action_requires_funded_target_and_does_not_stack_shovels(self):
        self.p['exploration_shuttles_available']=0
        self.p['resources'].update(ore=1,credits=2,qic=0)
        self.p['structures']=[{'hex':'0,0','kind':'Mine'}]
        for coord in ('1,0','2,0','3,0'):
            self.state['board']['hexes'][coord]['planet']['owner']=2
        self.assertGreater(action_value(self.state,self.p,8,2),0)
        self.state['board']['hexes']['4,0']['planet']['planet_type']='Volcanic'
        self.assertEqual(action_value(self.state,self.p,8,2),0)
        self.p['resources']['ore']=4
        costly=action_value(self.state,self.p,8,2)
        self.state['board']['hexes']['4,0']['planet']['planet_type']='Desert'
        self.assertGreater(action_value(self.state,self.p,8,2),costly)

    def test_immediate_gaia_needs_former_and_reachable_transdim_not_power(self):
        self.p['resources']['power'].update(bowl1=0,bowl2=0,bowl3=0)
        self.p['gaiaformers_total']=1;self.p['gaiaformers_deployed']=0
        self.p['gaiaformers_in_gaia_area']=0;self.p['resources']['spent_gaia_formers']=0
        self.state['board']['hexes']['1,0']['planet']['planet_type']='Transdim'
        self.assertGreater(action_value(self.state,self.p,5,6),0)
        self.p['gaiaformers_deployed']=1
        self.assertEqual(action_value(self.state,self.p,5,6),0)

    def test_next_round_goal_not_current_goal_drives_growth(self):
        self.p['resources'].update(ore=10,credits=20)
        self.state['round_tiles'][0]={'condition':'UpgradeLargeBuilding','vp_per_unit':5}
        self.state['round_tiles'][1]={'condition':'BuildMine','vp_per_unit':2}
        before=evaluate_booster(self.state,self.p,4)
        self.state['round_tiles'][0]={'condition':'BuildMineOnGaia','vp_per_unit':99}
        self.assertEqual(before,evaluate_booster(self.state,self.p,4))
        self.state['round_tiles'][1]={'condition':'UpgradeLargeBuilding','vp_per_unit':5}
        self.assertGreater(evaluate_booster(self.state,self.p,4).growth,before.growth)

    def test_booster_does_not_raise_pass_above_productive_actions(self):
        self.state['round']=5
        self.p['structures'].append({'hex':'3,0','kind':'PlanetaryInstitute'})
        passing=self.teacher.score(self.s,{'type':'Pass','booster_id':4})[0]
        researching=self.teacher.score(self.s,{'type':'ResearchAdvance','track':'Science'})[0]
        self.assertLess(passing,3)
        self.assertGreater(researching,passing)
        initial=self.teacher.score(self.s,{'type':'SelectStartingBooster','booster_id':4})[0]
        self.assertGreater(initial,0)


if __name__=='__main__':unittest.main()
