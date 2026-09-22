"""Regression checks for approved stock scaling; diagnostic failures stay visible."""
import copy
import unittest

from validate_bc import representative, cap_state, successor
import state_evaluation_bef as model


def evaluate(state, actor, enabled=True):
    return model.evaluate_state(state, actor, token_shortfall=True, remaining_income=True,
                                distributed_research=True, round_resource_prices=enabled)


class RoundStockPricesTests(unittest.TestCase):
    def test_prices_all_rounds_and_floors(self):
        for r, multiplier in ((1,1), (2,1), (3,1), (4,.8), (5,.6), (6,.4)):
            for key, value in model.stock_prices(r).items():
                self.assertAlmostEqual(value, max(1/3, model.base.base.PRICES[key]*multiplier))
            for key, value in model.bowl_prices(r).items():
                self.assertGreaterEqual(value, model.POWER_FLOORS[key])
        self.assertAlmostEqual(model.stock_prices(6)['credits'], 1/3)
        self.assertAlmostEqual(model.stock_prices(6)['ore'], 1.068)
        self.assertAlmostEqual(model.bowl_prices(6)['bowl3'], .48)

    def test_disabled_flag_exact_parity_and_only_stock_changes(self):
        for r in (1,3,5,6):
            state, actor = representative(r)
            original = copy.deepcopy(state)
            baseline = model.base.evaluate_state(state, actor, token_shortfall=True,
                remaining_income=True, distributed_research=True)
            self.assertEqual(evaluate(state, actor, False), baseline)
            after = evaluate(state, actor)
            for key in baseline.breakdown:
                if key not in ('ore_stock','credits_stock','knowledge_stock','qic_stock',
                               'power_stock','token_shortfall'):
                    self.assertEqual(baseline.breakdown[key], after.breakdown[key], key)
            self.assertEqual(state, original)
            self.assertAlmostEqual(after.total_vp, sum(after.breakdown.values()))

    def test_brainstone_three_times_normal_and_gaia_return_unchanged(self):
        for r in (1,3,5,6):
            state, actor = representative(r)
            p=state['players'][actor]
            p['faction']='Taklons'
            power=p['resources']['power']
            power.update(bowl1=0,bowl2=0,bowl3=0)
            for stone, bowl in model.STONE_BOWLS.items():
                power['brainstone']=stone
                self.assertAlmostEqual(evaluate(state, actor).breakdown['power_stock'], 3*model.bowl_prices(r)[bowl])
            power['brainstone']='Gaia'
            self.assertEqual(evaluate(state,actor).breakdown['power_stock'],
                             evaluate(state,actor,False).breakdown['power_stock'])

    def test_terminal_native_score_not_discounted(self):
        state, actor=representative(6)
        state['phase']={'Ended':{'final_scores':[[i,100+i] for i in range(4)]}}
        self.assertEqual(evaluate(state,actor).total_vp,100+actor)

    def test_shortfall_scales_with_round_and_ore_to_token_remains_a_cost(self):
        for r, multiplier in ((1,1), (3,1), (5,.6), (6,.4)):
            for count in (3,7):
                state, actor=cap_state(r,count,stress=True)
                after=successor(state,actor,{'type':'FreeAction','kind':'OreToPower','count':1})
                left,right=evaluate(state,actor),evaluate(after,actor)
                stock_loss=-model.stock_prices(r)['ore']
                shortage_gain=2.13*multiplier if count==3 else 0
                self.assertAlmostEqual(right.total_vp-left.total_vp,stock_loss+shortage_gain)
                self.assertAlmostEqual(right.breakdown['ore_stock']-left.breakdown['ore_stock'],stock_loss)
                self.assertAlmostEqual(right.breakdown['token_shortfall']-left.breakdown['token_shortfall'],shortage_gain)
                self.assertLess(right.total_vp,left.total_vp)


class ExpansionRescaleTests(unittest.TestCase):
    def options(self, f=False):
        return dict(top_n=3, conserve_resources=True, secured_planets=False,
                    token_shortfall=True, remaining_income=True, distributed_research=True,
                    round_resource_prices=f)

    def test_cheapest_native_route_and_used_public_slots(self):
        state, actor=representative(1)
        rows=model.expansion_details(state,actor,**self.options())
        row=next(r for r in rows if r['coord']=='1,0')
        self.assertEqual(row['cheapest']['action']['id'],6)
        state['used_power_actions']=[6,2]
        row=next(r for r in model.expansion_details(state,actor,**self.options()) if r['coord']=='1,0')
        self.assertEqual(len(row['paths']),1)
        self.assertEqual(row['cheapest']['action']['type'],'Build')

    def test_poor_state_keeps_colony_and_pays_missing_cost_without_phantom_tokens(self):
        state,actor=representative(1)
        p=state['players'][actor]
        p['resources'].update(ore=0,credits=0,qic=0)
        p['resources']['power'].update(bowl1=0,bowl2=0,bowl3=0)
        state['board']['hexes']['1,0']['planet']['planet_type']='Desert'
        before=copy.deepcopy(state)
        row=next(r for r in model.expansion_details(state,actor,**self.options()) if r['coord']=='1,0')
        self.assertGreater(row['value_vp'],0)
        self.assertAlmostEqual(row['cheapest']['debt_vp'],2.67+2*.8)
        for path in row['paths']:
            if path['legal']:
                self.assertEqual(path['breakdown'].get('token_shortfall',0),0)
                self.assertAlmostEqual(sum(path['breakdown'].values()),path['delta_vp'])
        self.assertEqual(state,before)

    def test_three_independent_options_weighted_and_no_recursion_or_owned_planet(self):
        from validate_bprime import opportunity_fixture
        state,actor=opportunity_fixture(target='Desert',distance=1,count=3)
        state['round']=1
        state['board']['spaceship_tiles']={}
        p=state['players'][actor];p['booster']=None
        rows=model.expansion_details(state,actor,**self.options())
        self.assertEqual(len(rows),3)
        self.assertNotIn('0,0',[r['coord'] for r in rows])
        result=model.evaluate_state(state,actor,expansion_rescale=True,**self.options())
        self.assertAlmostEqual(result.breakdown['expansion_opportunity'],
            sum(row['value_vp']*weight for row,weight in zip(rows,(1,.5,.25))))
        self.assertEqual(model._without_expansion(state,actor,self.options()).breakdown['expansion_opportunity'],0)
        after=successor(state,actor,{'type':'Build','coord':'1,0'})
        self.assertNotIn('1,0',[r['coord'] for r in model.expansion_details(after,actor,**self.options())])

    def test_transdim_keeps_existing_gaia_opportunity(self):
        from validate_bprime import opportunity_fixture
        state,actor=opportunity_fixture(target='Transdim',count=1)
        state['round']=1
        p=state['players'][actor]
        p['research_tracks']['gaia']=1
        p['gaiaformers_total']=1
        original=model.evaluate_state(state,actor,**self.options())
        result=model.evaluate_state(state,actor,expansion_rescale=True,**self.options())
        self.assertEqual(original.breakdown['gaia_opportunity'],result.breakdown['gaia_opportunity'])
        self.assertEqual(model.expansion_details(state,actor,**self.options()),())

    def test_discounted_option_removes_one_income_phase_and_applies_probability(self):
        for r in (1,3,5):
            state, actor = representative(r)
            normal = model.expansion_details(state, actor, **self.options(f=True))
            delayed = model.expansion_details(state, actor, discounted=True, **self.options(f=True))
            by_coord = {row['coord']: row for row in delayed}
            for row in normal:
                later = by_coord[row['coord']]
                self.assertEqual(row['cheapest']['action'], later['cheapest']['action'])
                for first, second in zip(row['paths'], later['paths']):
                    self.assertEqual(first['action'], second['action'])
                    self.assertEqual(first['legal'], second['legal'])
                    if first['legal']:
                        income = first['breakdown'].get('future_income',0)
                        self.assertAlmostEqual(second['delta_vp'],
                            first['delta_vp']-income/(6-r))
                self.assertAlmostEqual(later['value_vp'],
                    model.NEXT_ROUND_REALIZATION*max(0,later['cheapest']['delta_vp']))

    def test_discounted_expansion_zero_in_round_six_and_original_flag_unchanged(self):
        for r in (1,3,5,6):
            state,actor=representative(r)
            old=model.evaluate_state(state,actor,expansion_rescale=True,**self.options(f=True))
            explicit=model.evaluate_state(state,actor,expansion_rescale=True,
                                          discounted_expansion=False,**self.options(f=True))
            self.assertEqual(old,explicit)
            if r==6:
                later=model.evaluate_state(state,actor,discounted_expansion=True,**self.options(f=True))
                self.assertEqual(later.breakdown['expansion_opportunity'],0)
                self.assertEqual(model.expansion_details(state,actor,discounted=True,
                                                         **self.options(f=True)),())

    def test_discounted_expansion_leaves_early_mine_actions_positive(self):
        for r in (1,3):
            state,actor=representative(r)
            home=copy.deepcopy(state)
            home['board']['hexes']['1,0']['planet']['planet_type']='Desert'
            for before,action in ((home,{'type':'Build','coord':'1,0'}),
                                  (state,{'type':'PowerAction','id':6,'coord':'1,0'})):
                after=successor(before,actor,action)
                left=model.evaluate_state(before,actor,discounted_expansion=True,**self.options(f=True))
                right=model.evaluate_state(after,actor,discounted_expansion=True,**self.options(f=True))
                self.assertGreater(right.total_vp-left.total_vp,0)


if __name__ == '__main__':
    unittest.main()
