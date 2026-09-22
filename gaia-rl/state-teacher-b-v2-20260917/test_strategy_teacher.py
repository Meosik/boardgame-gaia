"""Explicit experiment tests; no changes to normal training/test discovery defaults."""
import copy
import json
import unittest

import numpy as np
import torch

from gaia_rl._native import Environment
from gaia_rl.encoding import FeatureEncoder
from strategy_teacher import StrategyTeacher
from strategy_pilot import batch, discover, make_module, SeedPoolAEC


class TeacherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec=discover('strategy-test',1)[0]
        cls.original=json.loads(Environment(cls.spec['seed']).snapshot_json())

    def setUp(self):
        self.s=copy.deepcopy(self.original)
        self.s['player']=next(p['player_id'] for p in self.s['state']['players'] if p['faction']=='Xenos')
        self.p=self.s['state']['players'][self.s['player']]
        self.teacher=StrategyTeacher()

    def score(self,action): return self.teacher.score(self.s,action)[0]

    def test_choice_is_legal_deterministic_and_does_not_mutate(self):
        # Keep native actor/candidate alignment for the real placement decision.
        s=self.original
        actor=s['state']['players'][s['player']]['faction']
        if actor not in ('Xenos','HadschHallas'):
            s=copy.deepcopy(self.s)
        before=copy.deepcopy(s);first=self.teacher.choose(s)
        self.assertEqual(first,self.teacher.choose(s));self.assertEqual(s,before)
        self.assertLess(first[1],len(s['candidates']))

    def test_foreign_factions_are_not_given_labels(self):
        self.p['faction']='Terrans'
        with self.assertRaises(ValueError): self.teacher.rank(self.s)

    def test_conversion_only_when_deficit(self):
        a={'type':'FreeAction','kind':'CreditsToOre','count':1}
        self.p['resources'].update(ore=1,credits=12)
        self.assertGreater(self.score(a),0)
        self.p['resources']['ore']=5;self.assertLess(self.score(a),0)

    def test_xenos_power_recovery_not_unconditional(self):
        a={'type':'FreeAction','kind':'OreToPowerBowl3','count':1}
        self.p['resources']['ore']=4
        self.p['resources']['power'].update(bowl1=1,bowl2=1,bowl3=1)
        self.assertGreater(self.score(a),0)
        self.p['resources']['power']['bowl1']=8;self.assertLess(self.score(a),0)

    def test_artifact_income_has_horizon_but_immediate_does_not(self):
        self.p['resources']['power'].update(bowl1=10,bowl2=0,bowl3=0)
        self.s['state']['round']=2
        early=self.score({'type':'ExamineArtifact','artifact':3})
        now=self.score({'type':'ExamineArtifact','artifact':6})
        self.s['state']['round']=6
        self.assertGreater(early,self.score({'type':'ExamineArtifact','artifact':3}))
        self.assertEqual(now,self.score({'type':'ExamineArtifact','artifact':6}))

    def test_artifact_does_not_empty_circulation_early(self):
        self.s['state']['round']=2
        self.p['resources']['power'].update(bowl1=6,bowl2=0,bowl3=0)
        self.assertLess(self.score({'type':'ExamineArtifact','artifact':3}),0)

    def test_exploration_requires_funded_follow_up_for_priority(self):
        self.s['state']['round']=1;self.p['resources']['qic']=4
        a={'type':'ExploreSpaceship','ship':'Rebellion'}
        good=self.score(a);self.p['resources']['qic']=0
        self.assertGreater(good,self.score(a))

    def test_advanced_choices_do_not_require_standard_tile_field(self):
        state=self.s['state']
        for choice in ({'kind':'Advanced','track':'Economy','covered_tile':2,'advance_track':None},
                       {'kind':'LostFleetAdvanced','covered_tile':2,'advance_track':'Science'}):
            score=self.teacher.technology(state,self.p,choice)
            self.assertTrue(np.isfinite(score))
        self.assertEqual(self.teacher.technology(state,self.p,{'kind':'Advanced','track':'Economy','covered_tile':2}),8)

    def test_early_pi_is_ranked_not_removed(self):
        self.s['state']['round']=1
        self.assertGreater(self.score({'type':'Upgrade','to':'PlanetaryInstitute'}),0)

    def test_no_late_gaia_without_time_to_build(self):
        coord=self.s['candidates'][0]['action']['coord']
        a={'type':'GaiaFormation','coord':coord}
        self.s['state']['round']=2;early=self.score(a)
        self.s['state']['round']=6;self.assertGreater(early,self.score(a))

    def test_dynamic_bc_padding_retains_every_legal_candidate(self):
        encoder=FeatureEncoder();s=self.original
        obs=encoder.encode(s,s['player']);n=len(s['candidates'])
        samples=[(obs['observation'],obs['candidates'][:n],n-1,'Xenos'),
                 (obs['observation'],obs['candidates'][:1],0,'Xenos')]
        b,y=batch(samples)
        self.assertEqual(b['obs']['action_mask'].sum().item(),n+1)
        module=make_module(encoder)
        logits=module.forward_train(b)['action_dist_inputs']
        loss=torch.nn.functional.cross_entropy(logits,y);loss.backward()
        self.assertTrue(torch.isfinite(loss))
        self.assertTrue(all(torch.isfinite(p.grad).all() for p in module.parameters() if p.grad is not None))

    def test_pool_reset_preserves_initial_reward_and_native_decision(self):
        env=SeedPoolAEC(2048,[self.spec['seed']]);env.reset(seed=3)
        self.assertEqual(env.snapshot,self.original)
        self.assertTrue(all(r==0 for r in env.rewards.values()))
        self.assertEqual(int(env.observe(env.agent_selection)['action_mask'].sum()),len(self.original['candidates']))

    def test_splits_are_disjoint_and_seats_balanced(self):
        specs=discover('strategy-test-heldout',1,True)
        self.assertEqual(len(specs),4)
        for faction in ('Xenos','HadschHallas'):
            self.assertEqual(sorted(s['factions'].index(faction) for s in specs),list(range(4)))
        self.assertNotIn(self.spec['seed'],[s['seed'] for s in specs])


if __name__=='__main__': unittest.main()
