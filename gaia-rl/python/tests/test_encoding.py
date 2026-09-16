import copy
import json
import unittest
import numpy as np
from gaia_rl import Environment
from gaia_rl.encoding import FeatureEncoder, EncodingError


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
