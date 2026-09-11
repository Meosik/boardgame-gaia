import copy
import unittest
from integrated import test_teacher
from integrated.teacher import IntegratedTeacher
from integrated.features import income
from research_context.teacher import (ContextResearchTeacher, advance, expansion_gain,
                                     gaia_opportunity, knowledge_stream, material_capacity)


class ResearchContextTests(unittest.TestCase):
    def setUp(self):
        test_teacher.IntegratedTests.setUp(self)
        self.teacher=ContextResearchTeacher()
        self.p['gaiaformers_total']=0;self.p['gaiaformers_deployed']=0
        self.p['gaiaformers_in_gaia_area']=0;self.p['resources']['spent_gaia_formers']=0
        self.state['spaceship_boards']=[b for b in self.state['spaceship_boards']
                                      if b['id'] in self.state['board']['spaceship_tiles']]
        self.state['research_board']['advanced_tech_tiles']=[None]*6

    def test_science_values_income_once_not_twice(self):
        stock=self.p['resources']['knowledge'];old=income(self.p,self.state)['knowledge']
        expected=(knowledge_stream(stock,old+1,5,30)-knowledge_stream(stock,old,5,30))*material_capacity(self.state,self.p)
        self.assertAlmostEqual(self.teacher.research(self.state,self.p,'Science'),expected)
        self.assertLess(expected,IntegratedTeacher().research(self.state,self.p,'Science'))

    def test_resource_engine_changes_science_value_without_faction_constant(self):
        rich=self.teacher.research(self.state,self.p,'Science')
        self.p['resources'].update(ore=0,credits=0)
        poor=self.teacher.research(self.state,self.p,'Science')
        self.assertGreater(rich,poor)
        self.p['structures'] += [{'hex':'1,0','kind':'TradingStation'},{'hex':'3,0','kind':'TradingStation'}]
        self.assertGreater(self.teacher.research(self.state,self.p,'Science'),poor)

    def test_late_science_entry_has_no_income_value_in_round6(self):
        early=self.teacher.research(self.state,self.p,'Science')
        self.state['round']=6
        self.assertEqual(self.teacher.research(self.state,self.p,'Science'),0)
        self.assertGreater(early,0)

    def test_surplus_knowledge_does_not_score_when_no_research_room(self):
        self.assertEqual(knowledge_stream(20,10,5,0),0)
        self.assertEqual(knowledge_stream(20,10,5,2),knowledge_stream(20,0,5,2))

    def test_terminal_science_compares_immediate_knowledge_and_lost_income(self):
        self.p['research_tracks']['science']=4
        early=self.teacher.research(self.state,self.p,'Science')
        self.state['round']=6
        late=self.teacher.research(self.state,self.p,'Science')
        self.assertGreater(late,early)

    def test_navigation_prepares_level2_and_requires_followup_budget(self):
        self.p['structures']=[{'hex':'0,0','kind':'Mine'}]
        self.p['exploration_shuttles_available']=0
        self.state['board']['hexes']['1,0']['planet']['owner']=2
        self.p['resources']['knowledge']=8
        rich=self.teacher.research(self.state,self.p,'Navigation')
        self.p['resources']['knowledge']=0
        poor=self.teacher.research(self.state,self.p,'Navigation')
        self.assertGreater(rich,poor)
        # All targets already within baseline range removes foundation value.
        for q in (2,3,4):self.state['board']['hexes'][f'{q},0']['planet']['owner']=2
        self.p['resources']['knowledge']=8
        self.assertEqual(self.teacher.research(self.state,self.p,'Navigation'),poor)

    def test_navigation_includes_natural_gaia_not_only_regular_colors(self):
        self.p['structures']=[{'hex':'0,0','kind':'Mine'}]
        for q in (1,3,4):self.state['board']['hexes'][f'{q},0']['planet']['owner']=2
        self.state['board']['hexes']['2,0']['planet']['planet_type']='Gaia'
        self.p['research_tracks']['navigation']=1
        self.assertGreater(expansion_gain(self.state,self.p,advance(self.p,'Navigation')),0)
        self.p['resources']['credits']=0
        self.p['research_tracks']['economy']=0
        self.assertEqual(expansion_gain(self.state,self.p,advance(self.p,'Navigation')),0)

    def test_gaia_requires_available_former_power_and_colony_funding(self):
        self.state['board']['hexes']['1,0']['planet']['planet_type']='Transdim'
        after=advance(self.p,'GaiaProject')
        self.assertEqual(after['gaiaformers_total'],1)
        self.assertGreater(gaia_opportunity(self.state,after),0)
        after['resources']['power'].update(bowl1=0,bowl2=0,bowl3=0)
        self.assertEqual(gaia_opportunity(self.state,after),0)
        after=advance(self.p,'GaiaProject');after['gaiaformers_deployed']=1
        self.assertEqual(gaia_opportunity(self.state,after),0)
        after=advance(self.p,'GaiaProject');after['resources']['credits']=0
        self.assertEqual(gaia_opportunity(self.state,after),0)

    def test_gaia_goal_and_next_round_bonus_increase_project_value(self):
        self.state['board']['hexes']['1,0']['planet']['planet_type']='Transdim'
        after=advance(self.p,'GaiaProject')
        self.state['round_tiles'][1]={'condition':'ResearchAdvance','vp_per_unit':2}
        before=gaia_opportunity(self.state,after)
        self.state['round_tiles'][1]={'condition':'BuildMineOnGaia','vp_per_unit':4}
        self.state['final_scoring_tiles']=[{'condition':'MostGaiaPlanets'}]
        self.assertGreater(gaia_opportunity(self.state,after),before)
        self.state['round']=6
        self.assertEqual(gaia_opportunity(self.state,after),0)

    def test_gaia_power_cost_reduction_opens_real_project(self):
        self.p['research_tracks']['gaia']=2;self.p['gaiaformers_total']=1
        self.p['resources']['power'].update(bowl1=0,bowl2=0,bowl3=4)
        self.state['board']['hexes']['1,0']['planet']['planet_type']='Transdim'
        self.assertEqual(gaia_opportunity(self.state,self.p),0)
        self.assertGreater(gaia_opportunity(self.state,advance(self.p,'GaiaProject')),0)

    def test_paid_advance_cost_not_applied_to_free_tile_research(self):
        self.p['resources']['knowledge']=4
        a={'type':'ResearchAdvance','track':'Science'}
        direct=self.teacher.score(self.s,a)[0]
        self.assertAlmostEqual(direct,40+self.teacher.research(self.state,self.p,'Science')-4)
        self.teacher._candidate={'type':'Upgrade'}
        free=self.teacher.research(self.state,self.p,'Science')
        self.teacher._candidate=None
        self.assertAlmostEqual(free,self.teacher.research(self.state,self.p,'Science'))

    def test_map_context_can_prefer_navigation_or_gaia_over_science(self):
        self.p['resources']['knowledge']=8
        self.p['structures']=[{'hex':'0,0','kind':'Mine'}]
        self.p['exploration_shuttles_available']=0
        self.state['board']['hexes']['1,0']['planet']['owner']=2
        self.assertGreater(self.teacher.research(self.state,self.p,'Navigation'),
                           self.teacher.research(self.state,self.p,'Science'))
        self.state['board']['hexes']['1,0']['planet'].update(owner=None,planet_type='Transdim')
        self.state['round_tiles'][1]={'condition':'BuildMineOnGaia','vp_per_unit':4}
        self.assertGreater(self.teacher.research(self.state,self.p,'GaiaProject'),
                           self.teacher.research(self.state,self.p,'Science'))
        self.state['board']['hexes']['1,0']['planet']['owner']=2
        self.assertGreater(self.teacher.research(self.state,self.p,'Science'),
                           self.teacher.research(self.state,self.p,'GaiaProject'))

    def test_last_green_token_considers_current_legal_advanced_choice(self):
        self.p['research_tracks']['science']=4;self.state['round']=6
        self.p['resources']['knowledge']=4;self.p['tech_tiles']=[7]
        self.state['research_board']['advanced_tech_tiles'][5]=10
        a={'type':'ResearchAdvance','track':'Science'}
        self.s['candidates']=[{'action':a}]
        without=self.teacher.score(self.s,a)[0]
        self.s['candidates'].append({'action':{'type':'Upgrade','coord':'2,0','to':'TradingStation',
            'tech_tile_choice':{'kind':'Advanced','track':'Science','covered_tile':7,'advance_track':None}}})
        # Prospective upgrade removes the only mine, so choose a lab upgrade instead.
        self.s['candidates'][-1]['action'].update(coord='0,0',to={'Academy':'Science'})
        self.assertLess(self.teacher.score(self.s,a)[0],without)
        self.p['federation_tokens'].append(2)
        self.assertEqual(self.teacher.score(self.s,a)[0],without)

    def test_context_ranking_is_deterministic_and_snapshot_unchanged(self):
        self.p['resources']['knowledge']=8
        self.s['candidates']=[{'action':{'type':'ResearchAdvance','track':t}}
                              for t in ('Science','Navigation','GaiaProject','Terraforming')]
        before=copy.deepcopy(self.s)
        self.assertEqual(self.teacher.rank(self.s),self.teacher.rank(self.s))
        self.assertEqual(before,self.s)


if __name__=='__main__':unittest.main()
