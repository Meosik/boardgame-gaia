import copy
import json
import unittest
import numpy as np
from gaia_rl import Environment
from gaia_rl.encoding import (FeatureEncoder, FeatureEncoderV4, EncodingError, ACTION_FIELDS, CATEGORY_IDS,
                              FIELD_VOCABULARY, OUTCOME_COLUMNS, OUTCOME_PLAYER, OUTCOME_OTHERS, OUTCOME_SIZE)
from gaia_rl.vocabulary import CATEGORIES


class EncodingTests(unittest.TestCase):
    def test_terraform_booster_and_batch_counts_have_distinct_candidate_features(self):
        encoder = FeatureEncoder()
        indices = {'1,0': 0}
        def build(kind):
            return {'phase': 'Game', 'action': {'type': kind, 'coord': '1,0'}}
        booster = encoder.candidate(build('RoundBoosterTerraformBuild'), indices)
        for kind in ('Build', 'RoundBoosterRangeBuild', 'SpaceGiantsBuildMine'):
            self.assertFalse(np.array_equal(booster, encoder.candidate(build(kind), indices)))
        def conversion(count):
            return {'phase': 'Game', 'action': {'type': 'FreeAction', 'kind': 'PowerToOre', 'count': count}}
        self.assertFalse(np.array_equal(encoder.candidate(conversion(1), indices),
                                        encoder.candidate(conversion(2), indices)))

    def setUp(self):
        self.snapshot=json.loads(Environment('encoding-unit').snapshot_json())
        self.encoder=FeatureEncoder(256)

    def test_shape_determinism_and_candidate_identity(self):
        s=self.snapshot;obs=self.encoder.encode(s,s['player'])
        self.assertTrue(self.encoder.observation_space.contains(obs))
        other=copy.deepcopy(s)
        other['state']['board']['hexes']=dict(reversed(list(other['state']['board']['hexes'].items())))
        for key,value in obs.items():
            np.testing.assert_array_equal(value,self.encoder.encode(other,s['player'])[key])
        n=len(s['candidates'])
        self.assertEqual(len({row.tobytes() for row in obs['candidates'][:n]}),n)

    def test_unknown_action_is_not_silently_ignored(self):
        self.snapshot['candidates'][0]['action']['new_rule']=True
        with self.assertRaises(EncodingError):
            self.encoder.encode(self.snapshot,self.snapshot['player'])

    def test_itars_technology_choices_preserve_all_parameters_and_mask(self):
        coords = list(self.snapshot['state']['board']['hexes'])[:2]
        choices = [
            {'kind': 'Standard', 'tile': 2, 'advance_track': None, 'bonus_build_coord': None},
            {'kind': 'Standard', 'tile': 2, 'advance_track': 'Science', 'bonus_build_coord': None},
            {'kind': 'Standard', 'tile': 11, 'advance_track': None, 'bonus_build_coord': coords[0]},
            {'kind': 'Standard', 'tile': 11, 'advance_track': None, 'bonus_build_coord': coords[1]},
            {'kind': 'Advanced', 'track': 'Terraforming', 'covered_tile': 3, 'advance_track': 'Science'},
            {'kind': 'Advanced', 'track': 'Terraforming', 'covered_tile': 4, 'advance_track': 'Science'},
            {'kind': 'Advanced', 'track': 'Navigation', 'covered_tile': 3, 'advance_track': 'Science'},
            {'kind': 'LostFleetAdvanced', 'covered_tile': 3, 'advance_track': 'Science'},
        ]
        self.snapshot['candidates'] = [
            {'phase': 'Game', 'action': {'type': 'ItarsGaiaTechChoice', 'choice': choice}}
            for choice in choices
        ]
        # Legacy requests must remain representable, but distinct from the new action.
        self.snapshot['candidates'].append({'phase': 'Game', 'action': {
            'type': 'ItarsGaiaTechTile', 'tile': 2, 'track': 'Science', 'bonus_build_coord': None,
        }})
        obs = self.encoder.encode(self.snapshot, self.snapshot['player'])
        count = len(self.snapshot['candidates'])
        self.assertTrue(self.encoder.observation_space.contains(obs))
        self.assertEqual(len({row.tobytes() for row in obs['candidates'][:count]}), count)
        np.testing.assert_array_equal(obs['action_mask'][:count], np.ones(count))
        self.assertFalse(obs['action_mask'][count:].any())
        self.assertTrue(np.isfinite(obs['candidates']).all())

    def test_unknown_action_category_still_fails_closed(self):
        self.snapshot['candidates'][0]['action']['type'] = 'UnregisteredFactionAction'
        with self.assertRaises(EncodingError):
            self.encoder.encode(self.snapshot, self.snapshot['player'])

    def test_distinct_federation_layouts(self):
        indices={'0,0':0,'0,1':1,'1,0':2}
        def action(sat):
            return {'phase':'Game','action':{'type':'FormFederation','hexes':['0,0'],
                    'satellite_hexes':[sat],'token':{'source':'Supply','kind':1}}}
        self.assertFalse(np.array_equal(self.encoder.candidate(action('0,1'),indices),
                                        self.encoder.candidate(action('1,0'),indices)))


if __name__=='__main__':
    unittest.main()

class ShipStateTests(unittest.TestCase):
    def test_exploration_and_action_usage_affect_state_features(self):
        s=json.loads(Environment('ship-state').snapshot_json());encoder=FeatureEncoder()
        original=encoder.encode(s,0)['observation']
        s['state']['players'][0]['explored_ships']=[2]
        explored=encoder.encode(s,0)['observation']
        self.assertFalse(np.array_equal(original,explored))
        s['state']['used_spaceship_actions']=[12]
        used=encoder.encode(s,0)['observation']
        self.assertFalse(np.array_equal(explored,used))

class SnapshotVersionTests(unittest.TestCase):
    def test_foreign_engine_snapshot_is_rejected(self):
        s=json.loads(Environment('snapshot-version').snapshot_json())
        s['engine_build_id']='foreign-build'
        with self.assertRaises(EncodingError):
            FeatureEncoder().encode(s,0)


class EncodingV4Tests(unittest.TestCase):
    def setUp(self):
        self.env = Environment('encoding-v4-unit')
        self.snapshot = json.loads(self.env.snapshot_json())
        self.previews = [json.loads(self.env.preview_state_json(self.snapshot['decision_id'], index))
                         for index in range(len(self.snapshot['candidates']))]
        self.encoder = FeatureEncoderV4(256)

    def test_candidate_row_holds_field_ids_and_board_roles(self):
        names = len(CATEGORIES)
        field = ACTION_FIELDS.index
        row = self.encoder.candidate(
            {'phase': 'Game', 'action': {'type': 'FreeAction', 'kind': 'PowerToOre', 'count': 2}}, {})
        self.assertEqual(row[field('type')], CATEGORY_IDS['FreeAction'])
        self.assertEqual(row[field('kind')], CATEGORY_IDS['PowerToOre'])
        self.assertEqual(row[field('count')], names + 1 + 2)
        self.assertEqual(row[field('track')], 0)
        accept = self.encoder.candidate({'phase': 'Game', 'action': {'type': 'FreeAction', 'accept': False}}, {})
        self.assertEqual(accept[field('accept')], names + 1)
        build = self.encoder.candidate(
            {'phase': 'Game', 'action': {'type': 'Build', 'coord': '1,0', 'hexes': ['1,0', '2,0']}},
            {'1,0': 3, '2,0': 5})
        board = build[self.encoder.board_offset:self.encoder.outcome_offset]
        self.assertEqual((board[3], board[5], board.sum()), (1 + 32, 32, 1 + 32 + 32))
        self.assertEqual(len(row), len(ACTION_FIELDS) + 256 + OUTCOME_SIZE)
        self.assertLess(row[:len(ACTION_FIELDS)].max(), FIELD_VOCABULARY)

    def test_field_values_outside_the_vocabulary_fail_closed(self):
        for value in (64, -1, 1.5, 'NoSuchName'):
            with self.assertRaises(EncodingError):
                self.encoder.candidate({'phase': 'Game', 'action': {'type': 'FreeAction', 'count': value}}, {})

    def test_state_vector_is_version_3_and_outcome_is_the_preview_difference(self):
        s = self.snapshot
        obs = self.encoder.encode(s, s['player'], self.previews)
        self.assertTrue(self.encoder.observation_space.contains(obs))
        old = FeatureEncoder(256).encode(s, s['player'])
        np.testing.assert_array_equal(obs['observation'], old['observation'])
        np.testing.assert_array_equal(obs['action_mask'], old['action_mask'])
        board = slice(self.encoder.board_offset, self.encoder.outcome_offset)
        np.testing.assert_array_equal(obs['candidates'][:, board], old['candidates'][:, len(ACTION_FIELDS)*2:])
        actor = s['player']
        def me(state):
            return next(p for p in state['players'] if p['player_id'] == actor)
        outcome = obs['candidates'][:, self.encoder.outcome_offset:]
        changed = 0
        for index, after in enumerate(self.previews):
            for name, path in (('vp', ('vp',)), ('resources.ore', ('resources', 'ore')),
                               ('resources.power.bowl1', ('resources', 'power', 'bowl1'))):
                before_value, after_value = me(s['state']), me(after)
                for key in path:
                    before_value, after_value = before_value[key], after_value[key]
                expected = np.clip(after_value - before_value, -30, 30) / 4
                self.assertEqual(outcome[index, OUTCOME_COLUMNS[name]], np.float32(expected))
            self.assertEqual(outcome[index, len(OUTCOME_PLAYER) + len(OUTCOME_OTHERS) + 1],
                             (after['round'] - s['state']['round']) / 4)
            changed += bool(np.abs(outcome[index]).max() > 0)
        self.assertGreater(changed, 0)
        self.assertEqual(np.abs(outcome[len(self.previews):]).max(), 0)

    def test_previews_are_required_and_unknown_player_numbers_fail_closed(self):
        s = self.snapshot
        with self.assertRaises(EncodingError):
            self.encoder.encode(s, s['player'])
        with self.assertRaises(EncodingError):
            self.encoder.encode(s, s['player'], self.previews[:-1])
        previews = copy.deepcopy(self.previews)
        next(p for p in previews[0]['players'] if p['player_id'] == s['player'])['new_counter'] = 1
        with self.assertRaises(EncodingError):
            self.encoder.encode(s, s['player'], previews)
