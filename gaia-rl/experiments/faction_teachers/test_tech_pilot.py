"""Pilot contracts: native paid actions; structural fixtures are labeled explicitly."""
from copy import deepcopy
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from faction_learning import FACTIONS
from faction_teachers.guidance import (advice_goals, available_technology, PILOT_SOURCE,
                                      technology_choice, technology_preparations)
from faction_teachers.teacher import SharedTeacher
from four_factions.preparation import (Goal, Policies, SearchExpired, achieved, advance_goal,
    goal_from_dict, goals_for, predicate_for, scoring_pairs, search, select_goal, viable)
from four_factions.preparation_cache import PolicyCache
from four_factions.provenance import hashes
from four_factions.test_preparation import PREFIX, SEED, root
from four_factions.timed import TimedPreparationTeacher


class TechPilotTests(unittest.TestCase):
    def test_flag_is_default_off_and_confined_to_shared_lane(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(SharedTeacher(SEED).faction_tech_plans)
        with patch.dict(os.environ, {'GAIA_FACTION_TECH_PLANS': '1'}):
            self.assertTrue(SharedTeacher(SEED).faction_tech_plans)
            self.assertFalse(SharedTeacher(SEED, faction_tech_plans=False).faction_tech_plans)
            self.assertFalse(TimedPreparationTeacher(SEED).faction_tech_plans)
        self.assertFalse(Policies(faction_tech_plans=True).faction_tech_plans)

    def test_off_goals_rank_selection_memory_and_cache_are_preserved(self):
        env, s = root()
        original = env.snapshot_json()
        cache = PolicyCache()
        default = Policies(shared_factions=True, cache=cache)
        off = Policies(shared_factions=True, cache=cache, faction_tech_plans=False)
        on = Policies(shared_factions=True, cache=cache, faction_tech_plans=True)
        expected = default.rank(env, s)
        self.assertEqual(off.rank(env, s), expected)
        self.assertEqual(default.memory, off.memory)
        self.assertEqual(cache.hits, 1)
        self.assertEqual(on.rank(env, s), expected)
        self.assertEqual(cache.misses, 2)
        self.assertTrue(on.clone().faction_tech_plans)
        old = goals_for(s, shared_factions=True)
        self.assertEqual(old, goals_for(s, shared_factions=True, faction_tech_plans=False))
        proposals = goals_for(s, shared_factions=True, faction_tech_plans=True)
        self.assertTrue(all(g in proposals for g in old))
        self.assertTrue(any(PILOT_SOURCE in g.sources for g in proposals))
        results = []
        for kwargs in ({}, {'faction_tech_plans': False}):
            # Stop after the real baseline rank; forecast length is not tested here.
            with patch('four_factions.preparation.rollout', return_value={
                    'complete': False, 'value': None, 'actions': []}):
                results.append(search(env, s, {}, lambda value: None, shared_factions=True,
                    soft_deadline=time.monotonic()+30, hard_deadline=time.monotonic()+30, **kwargs))
        self.assertEqual(results[0], results[1])
        self.assertEqual(env.snapshot_json(), original)

    def test_other_factions_and_unshared_search_get_no_pilot_goals(self):
        _, s = root()
        # Structural faction fixtures only; no native execution under a fake faction.
        for faction in set(FACTIONS)-{'Terrans', 'Ambas'}:
            s['state']['players'][s['player']]['faction'] = faction
            self.assertEqual(advice_goals(s), [])
            self.assertEqual(goals_for(s, shared_factions=True),
                             goals_for(s, shared_factions=True, faction_tech_plans=True))
        s['state']['players'][s['player']]['faction'] = 'Terrans'
        self.assertEqual(goals_for(s), goals_for(s, faction_tech_plans=True))

    def test_supply_owned_covered_future_tile_and_colony_loss_cancel(self):
        _, s = root()
        actor = s['player']
        goal = advice_goals(s)[0]
        player = s['state']['players'][actor]
        self.assertTrue(available_technology(s, 8))
        depleted = deepcopy(s)
        depleted['state']['research_board']['tech_tiles'] = [t for t in
            depleted['state']['research_board']['tech_tiles'] if t != 8]
        self.assertIn(8, depleted['state']['research_board']['tech_tile_slots'])
        self.assertFalse(available_technology(depleted, 8))
        self.assertFalse(viable(depleted, actor, goal))
        player['tech_tiles'] = [10]
        pending = advance_goal(s, actor, goal, {'type': 'Upgrade'})
        self.assertEqual(pending.steps[0].tile, 8)
        player['covered_tech_tiles'] = [10]
        self.assertFalse(viable(s, actor, pending))
        player['covered_tech_tiles'] = []
        target = goal.steps[-1].coord
        s['state']['board']['hexes'][target]['planet']['owner'] = (actor+1) % 4
        self.assertFalse(viable(s, actor, pending))
        self.assertEqual(goal_from_dict(json.loads(json.dumps(asdict(pending)))), pending)

    def test_ambas_swap_site_and_federation_are_connected(self):
        _, s = root()
        actor = s['player']
        player = s['state']['players'][actor]
        player['faction'] = 'Ambas'  # Predicate fixture, not a native Ambas playthrough.
        goal = advice_goals(s)[0]
        self.assertEqual(goal.steps[0].tile, 6)
        swap, federation = goal.steps[-2:]
        self.assertEqual(swap.coord, federation.coord)
        good = {'type': 'AmbasSwapPlanetaryInstitute', 'mine_coord': swap.coord}
        self.assertTrue(predicate_for(s, swap)(good))
        self.assertTrue(predicate_for(s, federation)({'type': 'FormFederation', 'hexes': [swap.coord]}))
        self.assertFalse(predicate_for(s, federation)({'type': 'FormFederation', 'hexes': ['elsewhere']}))
        reserved = goal.steps[1].coord
        action = {'type': 'Upgrade', 'coord': reserved, 'to': 'ResearchLab',
                  'tech_tile_choice': {'kind': 'Standard', 'tile': 6}}
        self.assertFalse(predicate_for(s, goal)(action))
        lost = deepcopy(s)
        lost['state']['players'][actor]['federated_hexes'] = [swap.coord]
        self.assertFalse(viable(lost, actor, goal))
        player['structures'] = [x for x in player['structures'] if x['hex'] != swap.coord]
        self.assertFalse(viable(s, actor, goal))

    def test_early_colony_cannot_be_reported_as_post_technology_payoff(self):
        _, before = root()
        goal = advice_goals(before)[0]
        actor = before['player']
        before['state']['players'][actor]['structures'].append({'hex': goal.steps[-1].coord, 'kind': 'Mine'})
        self.assertFalse(viable(before, actor, goal))
        after = deepcopy(before)
        after['state']['players'][actor]['tech_tiles'] = [10, 8]
        cancelled = advance_goal(after, actor, goal, {'type': 'Upgrade'}, before=before)
        self.assertFalse(viable(after, actor, cancelled))
        self.assertFalse(achieved(after, actor, cancelled))

    def test_nested_track_choice_and_scoring_variants(self):
        _, s = root()
        s['state']['research_board']['tech_tile_slots'] = [2, 3, 4, 5, 6, 7, 10, 8, 9]
        tech = Goal('charge', 'technology', tile=10)
        nested = Goal('nested', 'ordered', steps=(Goal('inner', 'ordered', steps=(tech,)),
                     Goal('science', 'research', target='Science', level=4)))
        actions = [{'type': 'ItarsGaiaTechChoice', 'choice': {
                    'kind': 'Standard', 'tile': 10, 'advance_track': t}} for t in ('Science', 'Economy')]
        s['candidates'] = [{'action': a} for a in actions]
        self.assertTrue(predicate_for(s, nested)(actions[0]))
        self.assertFalse(predicate_for(s, nested)(actions[1]))
        s['state']['research_board']['tech_tile_slots'][0] = 10
        self.assertEqual(technology_choice(s['state'], actions[0]), (10, 'Terraforming'))
        # A fixed track cannot be rewritten to satisfy the following research.
        self.assertTrue(predicate_for(s, nested)(actions[1]))
        colony = Goal('nested-colony', 'ordered', steps=(Goal('inner', 'sequence', steps=(
            Goal('Gaia', 'colony', '-3,-1'),)),))
        s['candidates'] = [{'action': {'type': 'SpaceGiantsGainTechTile',
                                      'choice': {'kind': 'Standard', 'tile': 8}}}]
        self.assertEqual(scoring_pairs(s, [(1, 'legal fixture')], [colony])[0].steps, colony.steps)
        self.assertEqual(scoring_pairs(s, [(1, 'legal fixture')], [colony], nested=False), [])

    def test_native_technology_preparation_acquires_target_and_pays_costs(self):
        env, s = root()
        original = env.snapshot_json()
        actor = s['player']
        policies = Policies(shared_factions=True, faction_tech_plans=True)
        goal = Goal('charge', 'technology', tile=10)
        scores = policies.rank(env, s)
        first = select_goal(env, s, scores, goal, policies, time.monotonic()+30)
        branch = env.fork(s['decision_id'], first)
        after = json.loads(branch.snapshot_json())
        p, q = s['state']['players'][actor], after['state']['players'][actor]
        self.assertEqual(s['candidates'][first]['action']['to'], 'TradingStation')
        self.assertEqual((p['resources']['ore']-q['resources']['ore'],
                          p['resources']['credits']-q['resources']['credits']), (2, 3))
        for _ in range(24):
            before = json.loads(branch.snapshot_json())
            if before['player'] == actor and 'ActionPhase' in before['state']['phase']:
                index = select_goal(branch, before, policies.rank(branch, before), goal,
                                    policies, time.monotonic()+30)
            else:
                index = next((i for i, c in enumerate(before['candidates'])
                              if c['action']['type'] in ('Pass', 'DeclinePower')), 0)
            branch.step(before['decision_id'], index)
            after = json.loads(branch.snapshot_json())
            if achieved(after, actor, goal):
                self.assertEqual(technology_choice(before['state'], before['candidates'][index]['action'])[0], 10)
                p, q = before['state']['players'][actor], after['state']['players'][actor]
                self.assertEqual((p['resources']['ore']-q['resources']['ore'],
                                  p['resources']['credits']-q['resources']['credits']), (3, 5))
                self.assertEqual(q['research_tracks']['navigation'], p['research_tracks']['navigation']+1)
                break
        else:
            self.fail('Native paid technology was not acquired within the fixture prefix')
        self.assertEqual(env.snapshot_json(), original)

    def test_no_resources_or_prerequisites_cannot_fabricate_technology(self):
        _, s = root()
        player = s['state']['players'][s['player']]
        # Structural fixture: no route can manufacture a legal candidate.
        player['structures'] = []
        player['resources'].update(ore=0, credits=0, knowledge=0, qic=0)
        s['state']['spaceship_boards'] = []
        self.assertEqual(technology_preparations(s, 10), [])
        s['candidates'] = [{'action': {'type': 'Pass'}}]
        scores = [(0, 'only legal fixture action')]
        self.assertEqual(select_goal(None, s, scores, Goal('tile', 'technology', tile=10),
                                    Policies(shared_factions=True), time.monotonic()+1), 0)
        self.assertFalse(achieved(s, s['player'], Goal('tile', 'technology', tile=10)))

    def test_expired_technology_preparation_keeps_deadline(self):
        env, s = root()
        policies = Policies(shared_factions=True)
        scores = policies.rank(env, s)
        with self.assertRaises(SearchExpired):
            select_goal(env, s, scores, Goal('tile', 'technology', tile=10), policies, time.monotonic()-1)

    def test_native_ambas_technology6_acquisition_is_paid(self):
        from gaia_rl import Environment
        env = Environment('shared-teacher-base-4', 2000)
        for index in [0]*12+[34]:
            s = json.loads(env.snapshot_json())
            env.step(s['decision_id'], index)
        original = env.snapshot_json()
        s = json.loads(original)
        actor = s['player']
        self.assertEqual(s['state']['players'][actor]['faction'], 'Ambas')
        policies = Policies(shared_factions=True, faction_tech_plans=True)
        goal = Goal('large-power', 'technology', tile=6)
        first = select_goal(env, s, policies.rank(env, s), goal, policies, time.monotonic()+30)
        branch = env.fork(s['decision_id'], first)
        for _ in range(24):
            before = json.loads(branch.snapshot_json())
            if before['player'] == actor and 'ActionPhase' in before['state']['phase']:
                index = select_goal(branch, before, policies.rank(branch, before), goal,
                                    policies, time.monotonic()+30)
            else:
                index = next((i for i, c in enumerate(before['candidates'])
                              if c['action']['type'] in ('Pass', 'DeclinePower')), 0)
            branch.step(before['decision_id'], index)
            after = json.loads(branch.snapshot_json())
            if achieved(after, actor, goal):
                action = before['candidates'][index]['action']
                self.assertEqual(action['type'], 'Upgrade')
                self.assertEqual(technology_choice(before['state'], action)[0], 6)
                p, q = before['state']['players'][actor], after['state']['players'][actor]
                self.assertEqual((p['resources']['ore']-q['resources']['ore'],
                                  p['resources']['credits']-q['resources']['credits']), (3, 5))
                break
        else:
            self.fail('Native Ambas technology acquisition did not finish within the fixture')
        self.assertEqual(env.snapshot_json(), original)

    def test_shared_teacher_worker_evaluates_pilot_using_native_forks(self):
        env, s = root()
        original = env.snapshot_json()
        teacher = SharedTeacher(SEED, prefix=PREFIX, target_seconds=8, maximum_seconds=10,
                                faction_tech_plans=True).bind(env)
        popen = subprocess.Popen
        children = []
        # Only shorten the forecast horizon in this wiring test. The real worker,
        # replay, policy rank, goal selection, forks, costs and leaf value all run.
        script = '''import sys
from unittest.mock import patch
from four_factions.timed import worker
with patch('four_factions.preparation.reached_horizon', return_value=True):
    worker(sys.argv[1])
'''
        def launch(args, **kwargs):
            request = json.loads(Path(args[-1]).read_text())
            self.assertTrue(request['faction_tech_plans'])
            self.assertTrue(request['shared_factions'])
            child = popen([sys.executable, '-c', script, args[-1]], **kwargs)
            children.append(child)
            return child
        started = time.monotonic()
        with patch('four_factions.timed.subprocess.Popen', side_effect=launch):
            decision, index = teacher.choose(s)
        self.assertLess(time.monotonic()-started, 11)
        self.assertEqual(decision, s['decision_id'])
        self.assertIn(index, range(len(s['candidates'])))
        self.assertIsNotNone(children[0].poll())
        plans = [p for p in teacher.last_audit['plans'] if PILOT_SOURCE in p['goal_spec']['sources']]
        self.assertTrue(plans, teacher.last_audit['selected'])
        self.assertTrue(plans[0]['actions'])
        self.assertEqual(plans[0]['actions'][0]['action']['type'], 'Upgrade')
        self.assertLess(plans[0]['actions'][0]['resources_after']['ore'],
                        plans[0]['actions'][0]['resources_before']['ore'])
        self.assertEqual(env.snapshot_json(), original)
        self.assertTrue(teacher.last_audit['faction_tech_plans'])

    def test_pilot_sources_are_part_of_existing_provenance(self):
        receipt = hashes()
        self.assertIn('gaia-rl/experiments/faction_teachers/guidance.py', receipt)
        self.assertIn('gaia-rl/experiments/four_factions/preparation.py', receipt)

    def test_old_resume_stays_off_even_if_environment_enables_new_games(self):
        from faction_teachers.test_continuation import ContinuationTests
        from faction_teachers.__main__ import collect
        with tempfile.TemporaryDirectory() as temporary:
            path, saved = ContinuationTests().fixture(Path(temporary))
            def stop_at_resume(policy, snapshot):
                self.assertFalse(policy.faction_tech_plans)
                self.assertEqual(policy.memory, saved['memory'])
                raise RuntimeError('test stop before new moves')
            with patch.dict(os.environ, {'GAIA_FACTION_TECH_PLANS': '1'}), \
                    patch('faction_teachers.teacher.SharedTeacher.choose', new=stop_at_resume):
                with self.assertRaisesRegex(RuntimeError, 'test stop'):
                    collect(Path(temporary)/'new', saved['seed'], adaptive=True, resume_checkpoint=path)
            header = json.loads((Path(temporary)/'new/recording.json').read_text())
            self.assertFalse(header['teacher_spec']['faction_tech_plans'])

    def test_on_checkpoint_records_and_restores_flag_and_nested_memory(self):
        from faction_learning.records import NativeRecorder
        from faction_teachers.continuation import load_continuation, restore_continuation, save_checkpoint
        from gaia_rl import Environment
        from gaia_rl.versions import runtime_versions
        import io
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary)/'original'
            manifest = {'versions': runtime_versions(), 'source_hashes': hashes()}
            recorder = NativeRecorder(destination, SEED, teacher_seats=range(4),
                teacher_spec={**manifest, 'name': 'pilot-checkpoint-fixture', 'faction_tech_plans': True})
            policy = SharedTeacher(SEED, faction_tech_plans=True)
            _, fixture = root()
            # Production memory has already crossed the worker JSON boundary.
            policy.memory = json.loads(json.dumps({'_plans': {'2': asdict(advice_goals(fixture)[0])}}))
            (destination/'teacher-audit.jsonl').write_text('')
            save_checkpoint(recorder, policy, manifest)
            recorder.close()
            continuation = load_continuation(destination/'policy-checkpoint.json', SEED)
            self.assertTrue(continuation['saved']['faction_tech_plans'])
            restored = SharedTeacher(SEED, faction_tech_plans=False)
            new = NativeRecorder(Path(temporary)/'new', SEED, teacher_seats=range(4),
                teacher_spec={**manifest, 'name': 'pilot-checkpoint-fixture', 'faction_tech_plans': True})
            try:
                restore_continuation(continuation, Environment(SEED, 2000), new, restored, io.StringIO())
                self.assertTrue(restored.faction_tech_plans)
                self.assertEqual(restored.memory, policy.memory)
                self.assertEqual(goal_from_dict(restored.memory['_plans']['2']), advice_goals(fixture)[0])
                self.assertEqual(restored.prefix, policy.prefix)
            finally:
                new.close()


if __name__ == '__main__':
    unittest.main()
