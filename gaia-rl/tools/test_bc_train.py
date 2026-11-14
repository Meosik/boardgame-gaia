"""bc_train: shard reader and batcher (numpy), and — when torch is installed — a tiny training run."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

import bc_train

TORCH = importlib.util.find_spec('torch') is not None


def write_shard(path, counts, chosen, features=5, observation=7, seed=0):
    """Candidate feature 0 is 1 for the chosen candidate and 0 otherwise, so the task is learnable."""
    rng = np.random.default_rng(seed)
    offsets = np.concatenate([[0], np.cumsum(counts)])
    cand = rng.normal(size=(offsets[-1], features)).astype(np.float16)
    cand[:, 0] = 0
    for i, pick in enumerate(chosen):
        cand[offsets[i]+pick, 0] = 1
    np.savez_compressed(path, observation=rng.normal(size=(len(counts), observation)).astype(np.float16), cand=cand,
                        cand_offsets=offsets, chosen=np.array(chosen), seat=np.zeros(len(counts), dtype=int),
                        faction=np.zeros(len(counts), dtype=int), round=np.ones(len(counts), dtype=int),
                        value=np.full(len(counts), np.nan, dtype=np.float32))


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
            self.assertEqual(tuple(model.state_dict()), bc_train.PARAMETERS)
            optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
            paths = bc_train.shard_paths(tmp)
            for _ in range(30):
                bc_train._run(model, paths[:1], 32, 0.0, optimizer, rng)
            result = bc_train._run(model, paths[1:], 32, 0.0)
            self.assertGreater(result['accuracy'], result['chance']+0.3)
            json.dumps(result)


if __name__ == '__main__':
    unittest.main()
