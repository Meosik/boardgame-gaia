"""bc_train: shard reader and batcher (numpy), and — when torch is installed — a tiny training run."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

import bc_train

TORCH = importlib.util.find_spec('torch') is not None
RAY = importlib.util.find_spec('ray') is not None


def write_shard(path, counts, chosen, features=5, observation=7, seed=0, game=None, v4=False):
    """Candidate feature 0 is 1 for the chosen candidate and 0 otherwise, so the task is learnable.
    v4: valid encoding 4 rows (two random field ids, one board cell, random outcome columns); the marker is the
    first outcome column. game: one game id per sample."""
    rng = np.random.default_rng(seed)
    offsets = np.concatenate([[0], np.cumsum(counts)])
    if v4:
        from gaia_rl import network
        from gaia_rl.encoding import BOARD_CAPACITY, FIELD_VOCABULARY
        cand = np.zeros((offsets[-1], network.V4_CANDIDATE_SIZE), dtype=np.float16)
        # As in real rows, most fields are absent (id 0) and few cells are set: 34 random ids per row would add 34
        # unrelated embeddings and bury the marker.
        cand[:, :2] = rng.integers(0, FIELD_VOCABULARY, size=(offsets[-1], 2))
        cells = network.FIELDS + rng.integers(0, BOARD_CAPACITY, size=offsets[-1])
        cand[np.arange(offsets[-1]), cells] = rng.choice([1, 2, 32, 64], size=offsets[-1])
        outcome = network.FIELDS + BOARD_CAPACITY
        cand[:, outcome:] = np.round(rng.normal(size=(offsets[-1], cand.shape[1]-outcome))*4)/4
        marker = outcome
    else:
        cand = rng.normal(size=(offsets[-1], features)).astype(np.float16)
        marker = 0
    cand[:, marker] = 0
    for i, pick in enumerate(chosen):
        cand[offsets[i]+pick, marker] = 1
    extra = {} if game is None else {'game': np.array(game, dtype=int)}
    np.savez_compressed(path, observation=rng.normal(size=(len(counts), observation)).astype(np.float16), cand=cand,
                        cand_offsets=offsets, chosen=np.array(chosen), seat=np.zeros(len(counts), dtype=int),
                        faction=np.zeros(len(counts), dtype=int), round=np.ones(len(counts), dtype=int),
                        value=np.full(len(counts), np.nan, dtype=np.float32), **extra)


class BatchTests(unittest.TestCase):
    def test_batches_pad_to_the_largest_list_and_mask_the_rest(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_shard(Path(tmp)/'shard-00000.npz', [2, 5, 3], [1, 4, 0])
            shard = bc_train.load_shard(bc_train.shard_paths(tmp)[0])
            (first, second) = list(bc_train.batches(shard, 2))
            self.assertEqual(first['candidates'].shape, (2, 5, 5))
            self.assertEqual(first['mask'].sum(axis=1).tolist(), [2, 5])
            self.assertTrue((first['candidates'][0, 2:] == 0).all())
            self.assertEqual(first['chosen'].tolist(), [1, 4])
            self.assertEqual(first['observation'].dtype, np.float32)
            self.assertEqual(second['candidates'].shape, (1, 3, 5))
            # the chosen candidate keeps its marker after padding
            self.assertEqual([float(b['candidates'][i, c, 0]) for b in (first, second)
                              for i, c in enumerate(b['chosen'])], [1.0, 1.0, 1.0])

    def test_shuffled_batches_cover_every_sample_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_shard(Path(tmp)/'shard-00000.npz', [3]*10, list(range(3))*3+[0])
            shard = bc_train.load_shard(bc_train.shard_paths(tmp)[0])
            seen = np.concatenate([b['observation'] for b in bc_train.batches(shard, 4, np.random.default_rng(1))])
            self.assertEqual(sorted(map(tuple, seen)), sorted(map(tuple, shard['observation'].astype(np.float32))))

    def test_bad_chosen_index_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_shard(Path(tmp)/'shard-00000.npz', [2, 2], [0, 1])
            data = dict(np.load(Path(tmp)/'shard-00000.npz'))
            data['chosen'] = np.array([0, 2])
            np.savez_compressed(Path(tmp)/'shard-00000.npz', **data)
            with self.assertRaises(ValueError):
                bc_train.load_shard(Path(tmp)/'shard-00000.npz')

    def test_no_shards(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(FileNotFoundError):
            bc_train.shard_paths(tmp)

    def test_default_width_per_encoding(self):
        self.assertEqual(bc_train.WIDTHS, {3: 64, 4: 256})

    def test_held_out_games_takes_every_nth_game_in_id_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_shard(Path(tmp)/'shard-00000.npz', [2]*4, [0]*4, game=[0, 0, 1, 3])
            write_shard(Path(tmp)/'shard-00001.npz', [2]*5, [0]*5, game=[3, 4, 7, 7, 9])
            paths = bc_train.shard_paths(tmp)
            # sorted ids: 0 1 3 4 7 9
            self.assertEqual(bc_train.held_out_games(paths, 5), {7})
            self.assertEqual(bc_train.held_out_games(paths, 2), {1, 4, 9})
            self.assertEqual(bc_train.held_out_games(paths, 0), set())
            write_shard(Path(tmp)/'shard-00002.npz', [2], [0])
            self.assertIsNone(bc_train.held_out_games(bc_train.shard_paths(tmp), 5))

    def test_batches_keep_only_the_given_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_shard(Path(tmp)/'shard-00000.npz', [2, 3, 2, 4, 3, 2], [1, 2, 0, 3, 1, 0])
            shard = bc_train.load_shard(bc_train.shard_paths(tmp)[0])
            rows = np.array([1, 4, 5])
            (batch,) = list(bc_train.batches(shard, 4, rows=rows))
            self.assertEqual(batch['chosen'].tolist(), [2, 1, 0])
            np.testing.assert_array_equal(batch['observation'], shard['observation'][rows].astype(np.float32))
            (shuffled,) = list(bc_train.batches(shard, 4, np.random.default_rng(1), rows=rows))
            self.assertEqual(sorted(shuffled['chosen'].tolist()), [0, 1, 2])
            self.assertEqual(sorted(map(tuple, shuffled['observation'])), sorted(map(tuple, batch['observation'])))


@unittest.skipUnless(TORCH, 'torch is not installed (pyproject extra "train")')
class TrainTests(unittest.TestCase):
    def test_model_has_the_candidate_module_parameters_and_learns_the_marker(self):
        import torch
        torch.manual_seed(0)
        with tempfile.TemporaryDirectory() as tmp:
            rng = np.random.default_rng(0)
            for n in range(2):
                counts = rng.integers(2, 6, size=200)
                write_shard(Path(tmp)/f'shard-{n:05d}.npz', counts, [int(rng.integers(c)) for c in counts], seed=n)
            model = bc_train.build_model(7, 5, 16)
            self.assertEqual(tuple(model.state_dict()), bc_train.PARAMETERS[3])
            optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
            paths = bc_train.shard_paths(tmp)
            for _ in range(30):
                bc_train._run(model, paths[:1], 32, 0.0, optimizer, rng)
            result = bc_train._run(model, paths[1:], 32, 0.0)
            self.assertGreater(result['accuracy'], result['chance']+0.3)
            json.dumps(result)

    def test_encoding_4_model_has_its_parameters_and_learns_the_marker(self):
        import torch
        from gaia_rl import network
        torch.manual_seed(0)
        with tempfile.TemporaryDirectory() as tmp:
            rng = np.random.default_rng(0)
            for n in range(2):
                counts = rng.integers(2, 6, size=200)
                write_shard(Path(tmp)/f'shard-{n:05d}.npz', counts, [int(rng.integers(c)) for c in counts],
                            seed=n, v4=True)
            model = bc_train.build_model(7, network.V4_CANDIDATE_SIZE, 16, 4)
            self.assertEqual(tuple(model.state_dict()), bc_train.PARAMETERS[4])
            optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
            paths = bc_train.shard_paths(tmp)
            # 60 passes: the 32 absent-field embeddings (N(0,1) each, as measured) start most tanh units saturated,
            # so the marker is learned more slowly than in the encoding 3 test (30 passes reach chance + 0.30).
            for _ in range(60):
                bc_train._run(model, paths[:1], 32, 0.0, optimizer, rng)
            result = bc_train._run(model, paths[1:], 32, 0.0)
            self.assertGreater(result['accuracy'], result['chance']+0.3)

    def test_train_holds_out_games_and_saves_the_lowest_validation_loss_epoch(self):
        import torch
        from gaia_rl import network
        from gaia_rl.encoding import FeatureEncoderV4
        size = FeatureEncoderV4().state_size
        with tempfile.TemporaryDirectory() as tmp:
            shards, out = Path(tmp)/'shards', Path(tmp)/'checkpoint'
            shards.mkdir()
            write_shard(shards/'shard-00000.npz', [2, 3, 4, 2, 3], [1, 0, 3, 1, 2], observation=size,
                        game=[0, 0, 1, 1, 2], v4=True)
            write_shard(shards/'shard-00001.npz', [3, 2, 4, 2, 3], [0, 1, 2, 1, 2], observation=size, seed=1,
                        game=[2, 3, 3, 4, 4], v4=True)
            history = bc_train.train(shards, out, epochs=3, batch=4, lr=0.01, width=16, val_every=5)
            self.assertEqual(len(history), 3)
            self.assertTrue(all('validation' in row for row in history))
            self.assertEqual(history[0]['train']['samples'], 8)
            self.assertEqual(history[0]['validation']['samples'], 2)      # game 4 is held out
            metadata = json.loads((out/'metadata.json').read_text())
            self.assertEqual(metadata['encoding_version'], 4)
            self.assertEqual(metadata['model'], {'width': 16, 'encoding': 4})
            best = min(history, key=lambda row: row['validation']['loss'])['epoch']
            behaviour = metadata['behaviour_cloning']
            self.assertEqual(behaviour['validation_games'], [4])
            self.assertEqual(behaviour['saved_epoch'], best)
            self.assertEqual(behaviour['width'], 16)
            state = torch.load(out/'inference.pt', weights_only=True)
            self.assertEqual(tuple(state), bc_train.PARAMETERS[4])
            with self.assertRaises(ValueError):
                bc_train.train(shards, Path(tmp)/'other', epochs=1, val_every=1)

    def test_encoding_3_refuses_another_width(self):
        from gaia_rl.encoding import FeatureEncoder
        spaces = FeatureEncoder().observation_space.spaces
        with tempfile.TemporaryDirectory() as tmp:
            shards = Path(tmp)/'shards'
            shards.mkdir()
            write_shard(shards/'shard-00000.npz', [2, 3], [1, 0],
                        features=spaces['candidates'].shape[-1], observation=spaces['observation'].shape[0])
            with self.assertRaises(ValueError):
                bc_train.train(shards, Path(tmp)/'out', epochs=1, batch=2, val_shards=0, width=128)


@unittest.skipUnless(TORCH and RAY, 'torch and ray are not installed (pyproject extra "train")')
class CheckpointTests(unittest.TestCase):
    def test_trained_checkpoint_loads_in_offline_policy(self):
        from gaia_rl.encoding import FeatureEncoder
        from gaia_rl.evaluation import OfflinePolicy
        spaces = FeatureEncoder().observation_space.spaces
        with tempfile.TemporaryDirectory() as tmp:
            shards, out = Path(tmp)/'shards', Path(tmp)/'checkpoint'
            shards.mkdir()
            write_shard(shards/'shard-00000.npz', [2, 3, 4, 2], [1, 0, 3, 1],
                        features=spaces['candidates'].shape[-1], observation=spaces['observation'].shape[0])
            history = bc_train.train(shards, out, epochs=1, batch=2, val_shards=0)
            self.assertEqual(len(history), 1)
            policy = OfflinePolicy(out)
            self.assertEqual(tuple(policy.module.state_dict()), bc_train.PARAMETERS[3])
            self.assertEqual(json.loads((out/'metadata.json').read_text())['behaviour_cloning']['width'], 64)
            self.assertEqual(policy.encoding, 3)

    def test_encoding_4_checkpoint_plays_through_offline_policy(self):
        """The metadata picks FeatureEncoderV4 and the width; choose() previews every candidate on the environment
        and picks the candidate that bc_train's network scores highest on the same rows (training = playing input)."""
        import torch
        from gaia_rl import Environment, network
        from gaia_rl.encoding import FeatureEncoderV4
        from gaia_rl.evaluation import OfflinePolicy
        encoder = FeatureEncoderV4()
        with tempfile.TemporaryDirectory() as tmp:
            shards, out = Path(tmp)/'shards', Path(tmp)/'checkpoint'
            shards.mkdir()
            write_shard(shards/'shard-00000.npz', [2, 3, 4, 2], [1, 0, 3, 1], observation=encoder.state_size, v4=True)
            bc_train.train(shards, out, epochs=1, batch=2, val_shards=0, width=16)
            policy = OfflinePolicy(out)
            self.assertEqual((policy.encoding, type(policy.encoder)), (4, FeatureEncoderV4))
            self.assertEqual(tuple(policy.module.state_dict()), bc_train.PARAMETERS[4])
            model = bc_train.build_model(encoder.state_size, encoder.candidate_size, 16, 4)
            model.load_state_dict(torch.load(out/'inference.pt', weights_only=True))
            model.eval()
            env = Environment('quartet-a-72715')
            for _ in range(6):
                snapshot = json.loads(env.snapshot_json())
                count = len(snapshot['candidates'])
                with self.assertRaises(ValueError):
                    policy.choose(snapshot)                 # no environment: nothing to preview
                decision, index = policy.choose(snapshot, env)
                previews = [json.loads(env.preview_state_json(snapshot['decision_id'], i)) for i in range(count)]
                rows = encoder.encode(snapshot, snapshot['player'], previews)
                with torch.no_grad():
                    logits, _ = network.score(model, torch.as_tensor(rows['observation'])[None],
                                              torch.as_tensor(rows['candidates'][:count])[None],
                                              torch.ones(1, count, dtype=torch.bool))
                self.assertEqual((decision, index), (snapshot['decision_id'], int(logits[0].argmax())))
                env.step(decision, index)

    def test_metadata_whose_model_disagrees_with_the_encoding_is_refused(self):
        from gaia_rl.encoding import FeatureEncoder
        from gaia_rl.evaluation import OfflinePolicy
        spaces = FeatureEncoder().observation_space.spaces
        with tempfile.TemporaryDirectory() as tmp:
            shards, out = Path(tmp)/'shards', Path(tmp)/'checkpoint'
            shards.mkdir()
            write_shard(shards/'shard-00000.npz', [2, 3], [1, 0],
                        features=spaces['candidates'].shape[-1], observation=spaces['observation'].shape[0])
            bc_train.train(shards, out, epochs=1, batch=2, val_shards=0)
            metadata = json.loads((out/'metadata.json').read_text())
            for change in ({'encoding_version': 4}, {'encoding_version': 5, 'model': {'width': 64, 'encoding': 5}}):
                (out/'metadata.json').write_text(json.dumps({**metadata, **change}))
                with self.assertRaises(ValueError):
                    OfflinePolicy(out)
            del metadata['model']                           # checkpoints of gaia_rl.training: encoding 3, width 64
            (out/'metadata.json').write_text(json.dumps(metadata))
            self.assertEqual(OfflinePolicy(out).encoding, 3)


if __name__ == '__main__':
    unittest.main()
