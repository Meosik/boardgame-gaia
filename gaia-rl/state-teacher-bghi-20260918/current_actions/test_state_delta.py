import copy
import json
import unittest
from unittest.mock import patch

from current_actions.conservation import Conservation, blocked, identity
from current_actions.state_delta import StateDeltaTeacher
from current_actions.teacher import CurrentActionTeacher, CurrentContextTeacher
from four_factions.preparation import Policies, leaf_value
from four_factions.preparation_cache import PolicyCache
from research_plans.teacher import best_index


class FakeEnvironment:
    def __init__(self, snapshot, states):
        self.snapshot = snapshot
        self.states = states
        self.previews = []

    def snapshot_json(self):
        return json.dumps(self.snapshot)

    def preview_state_json(self, decision, index):
        assert decision == self.snapshot['decision_id']
        self.previews.append(index)
        return json.dumps(self.states[index])


def fixture():
    state = {'phase': {'ActionPhase': {}}, 'round': 3,
             'players': [{'faction': 'Xenos', 'vp': 10, 'resources': {'ore': 4}}]}
    snapshot = {'decision_id': 'one', 'player': 0, 'steps': 1, 'state': state,
                'candidates': [{'action': {'type': 'Build'}}, {'action': {'type': 'Upgrade'}}]}
    states = [copy.deepcopy(state), copy.deepcopy(state)]
    states[0]['players'][0]['vp'] += 2
    states[1]['players'][0]['vp'] += 5
    return snapshot, states


class StateDeltaTests(unittest.TestCase):
    def test_prior_only_orders_previews_and_cannot_change_delta_or_winner(self):
        snapshot, states = fixture()
        env = FakeEnvironment(snapshot, states)
        teacher = StateDeltaTeacher().bind(env)
        references = []

        def value(state, actor, reference, evaluator, *, guide_tracks):
            references.append(reference)
            self.assertTrue(guide_tracks)
            self.assertIsInstance(evaluator, CurrentContextTeacher)
            return state['players'][actor]['vp']

        with patch.object(teacher, 'base_rank', return_value=[(999, 'prior'), (-999, 'prior')]), \
                patch('current_actions.state_delta.endpoint_value', side_effect=value):
            scores = teacher.rank(snapshot)
        self.assertEqual([v for v, _ in scores], [2, 5])
        self.assertEqual(best_index(scores, range(2)), 1)
        self.assertEqual(env.previews, [0, 1])
        self.assertTrue(all(p is snapshot['state']['players'][0] for p in references))
        self.assertEqual(json.loads(env.snapshot_json()), snapshot)

    def test_constraints_apply_before_preview_and_verified_followup_is_retained(self):
        snapshot, states = fixture()
        snapshot['candidates'][0]['action'] = {'type': 'FreeAction', 'kind': 'OreToCredit'}
        env = FakeEnvironment(snapshot, states)
        teacher = StateDeltaTeacher().bind(env)
        teacher._conservation = Conservation()
        teacher._conservation.continuations = {
            identity(snapshot): {identity(snapshot['candidates'][1]['action'])}}
        with patch.object(teacher, 'base_rank', return_value=[(1e9, 'prior'), (0, 'prior')]), \
                patch('current_actions.state_delta.endpoint_value', return_value=10):
            scores = teacher.rank(snapshot)
        self.assertTrue(blocked(scores[0]))
        self.assertFalse(blocked(scores[1]))
        self.assertEqual(env.previews, [1])

    def test_setup_is_the_unchanged_control_and_stale_input_is_rejected(self):
        snapshot, states = fixture()
        snapshot['state']['phase'] = {'Setup': {}}
        teacher = StateDeltaTeacher().bind(FakeEnvironment(snapshot, states))
        with patch.object(CurrentActionTeacher, 'rank', return_value=[(7, 'setup')]) as control:
            self.assertEqual(teacher.rank(snapshot), [(7, 'setup')])
            control.assert_called_once_with(snapshot)
        stale = copy.deepcopy(snapshot)
        stale['decision_id'] = 'stale'
        with self.assertRaisesRegex(ValueError, 'snapshot'):
            teacher.rank(stale)

    def test_nonfinite_values_fail_instead_of_producing_an_arbitrary_move(self):
        snapshot, states = fixture()
        teacher = StateDeltaTeacher().bind(FakeEnvironment(snapshot, states))
        with patch.object(teacher, 'base_rank', return_value=[(0, ''), (0, '')]), \
                patch('current_actions.state_delta.endpoint_value', return_value=float('nan')):
            with self.assertRaisesRegex(ValueError, 'finite'):
                teacher.rank(snapshot)

    def test_policy_clone_and_cache_keep_variants_separate(self):
        snapshot, states = fixture()
        env = FakeEnvironment(snapshot, states)
        cache = PolicyCache()
        a = Policies(cache=cache)
        b = Policies(cache=cache, delta_factions=('Xenos',))

        def rank(policy, snapshot):
            policy._conservation = Conservation()
            return [(2 if isinstance(policy, StateDeltaTeacher) else 1, 'rank')]*2

        with patch.object(CurrentActionTeacher, 'rank', rank), patch.object(StateDeltaTeacher, 'rank', rank):
            self.assertEqual(a.rank(env, snapshot)[0][0], 1)
            self.assertEqual(b.rank(env, snapshot)[0][0], 2)
            self.assertEqual(b.clone().delta_factions, ('Xenos',))
            self.assertEqual(b.clone().rank(env, snapshot)[0][0], 2)
        self.assertEqual(cache.stats()['hits'], 1)
        with self.assertRaises(ValueError):
            Policies(delta_factions=('Itars',))


class NativeStateDeltaTests(unittest.TestCase):
    def test_native_subprocess_uses_B_and_returns_an_applicable_decision(self):
        from four_factions.test_preparation import PREFIX, SEED, root
        from four_factions.timed import TimedPreparationTeacher
        env, snapshot = root()
        original = env.snapshot_json()
        teacher = TimedPreparationTeacher(SEED, prefix=PREFIX, target_seconds=.01,
                                         maximum_seconds=10, delta_factions=('Terrans',)).bind(env)
        decision, index = teacher.choose(snapshot)
        self.assertEqual(teacher.last_audit['ranking_mode'], 'state-delta')
        self.assertEqual(teacher.last_audit['delta_factions'], ['Terrans'])
        self.assertTrue(all(reason.startswith('state-delta:') for value, reason in
                            teacher.last_audit['scores'] if not blocked((value, reason))))
        self.assertEqual(env.snapshot_json(), original)
        env.step(decision, index)
        teacher.observe(snapshot, index, json.loads(env.snapshot_json()))
        self.assertEqual(teacher.prefix, PREFIX+[index])

    def test_terrans_and_taklons_use_their_exact_leaf_without_soft_action_terms(self):
        from four_factions.teacher import NativeFactionTeacher, brainstone_committed
        from four_factions.test_preparation import root
        env, snapshot = root()
        # Follow actual native actions until both factions have a live decision.
        found = set()
        for _ in range(20):
            faction = snapshot['state']['players'][snapshot['player']]['faction']
            if faction in ('Terrans', 'Taklons'):
                found.add(faction)
                teacher = NativeFactionTeacher(state_delta=True).bind(env)
                original = env.snapshot_json()
                scores = teacher.rank(snapshot)
                actor = snapshot['player']
                reference = snapshot['state']['players'][actor]
                base = leaf_value(snapshot, actor, reference, guide_tracks=True)
                for index, score in enumerate(scores):
                    after = {'state': json.loads(env.preview_state_json(snapshot['decision_id'], index))}
                    if brainstone_committed(snapshot, after, actor):
                        self.assertTrue(blocked(score))
                    if not blocked(score):
                        self.assertAlmostEqual(score[0], leaf_value(after, actor, reference, guide_tracks=True)-base)
                self.assertEqual(teacher.last_audit['funding_previews'], 0)
                self.assertEqual(env.snapshot_json(), original)
            if len(found) == 2:
                break
            index = next((i for i, c in enumerate(snapshot['candidates']) if c['action']['type'] == 'Pass'), 0)
            env.step(snapshot['decision_id'], index)
            snapshot = json.loads(env.snapshot_json())
        self.assertEqual(found, {'Terrans', 'Taklons'})

    def test_native_scores_equal_the_existing_leaf_delta_without_parent_mutation(self):
        from current_actions.test_conservation_native import root
        env, snapshot = root(35)
        before = env.snapshot_json()
        teacher = StateDeltaTeacher().bind(env)
        scores = teacher.rank(snapshot)
        base = leaf_value(snapshot, snapshot['player'], snapshot['state']['players'][snapshot['player']],
                          guide_tracks=True)
        for index, score in enumerate(scores):
            if blocked(score):
                continue
            after = json.loads(env.preview_state_json(snapshot['decision_id'], index))
            expected = leaf_value({'state': after}, snapshot['player'],
                                  snapshot['state']['players'][snapshot['player']], guide_tracks=True)-base
            self.assertAlmostEqual(score[0], expected)
        qic = [i for i, c in enumerate(snapshot['candidates']) if c['action'].get('kind') == 'QicToOre']
        self.assertTrue(qic)
        self.assertTrue(all(blocked(scores[i]) for i in qic))
        self.assertEqual(env.snapshot_json(), before)
        env.step(snapshot['decision_id'], best_index(scores, range(len(scores))))

    def test_native_minimum_qic_exception_keeps_the_academy_commitment(self):
        from current_actions.test_conservation_native import root
        env, snapshot = root(160)
        teacher = StateDeltaTeacher().bind(env)
        scores = teacher.rank(snapshot)
        index = next(i for i, c in enumerate(snapshot['candidates'])
                     if c['action'].get('kind') == 'QicToOre' and not blocked(scores[i]))
        branch = env.fork(snapshot['decision_id'], index)
        after = json.loads(branch.snapshot_json())
        ranks = teacher.bind(branch).rank(after)
        allowed = [c['action'] for c, score in zip(after['candidates'], ranks) if not blocked(score)]
        self.assertTrue(allowed)
        self.assertTrue(all(a['type'] == 'Upgrade' and 'Academy' in a.get('to', {}) for a in allowed))


if __name__ == '__main__':
    unittest.main()
