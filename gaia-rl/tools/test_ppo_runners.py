"""gaia_rl.training with remote env runners (HANDOFF E329): every sampling process has its own episode seed stream,
save_run keeps each process's RNG, restore_run gives it back and a resumed run repeats.

  GAIA_ENGINE_FIXES_2=1 PYTHONPATH=gaia-rl/python:gaia-rl/baseline-teacher-20260917:gaia-rl/tools \
      gaia-rl/.venv/bin/python -m unittest gaia-rl/tools/test_ppo_runners.py
"""
import tempfile
import unittest
import unittest.mock
from pathlib import Path

import numpy as np
import ray
import torch

from gaia_rl.training import (_runner_rng, _runner_threads, build_algorithm, episode_env, learner_device,
                              parameter_vector, remote_runners, require_learner_device, restore_run, save_run)

SEED = 5


def settings(runners):
    return {'seed': SEED, 'capacity': 2048, 'batch_size': 32, 'device': 'cpu', 'encoding': 3, 'width': 64,
            'env_runners': runners, 'minibatch_size': 8}


def same(a, b):
    """Equality of RNG states (nested dicts / tuples with arrays and tensors)."""
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[key], b[key]) for key in a)
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if isinstance(a, (np.ndarray, torch.Tensor)):
        return bool(np.array_equal(np.asarray(a), np.asarray(b)))
    return a == b


def train(algorithm):
    learner = algorithm.train()['learners']['shared']
    assert all(np.isfinite(learner[key]) for key in ('total_loss', 'policy_loss', 'vf_loss'))
    return parameter_vector(algorithm)


class RemoteRunners(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(2)
        ray.init(num_cpus=4, include_dashboard=False, object_store_memory=1024**3, log_to_driver=False)
        cls.folder = tempfile.TemporaryDirectory()
        cls.root = Path(cls.folder.name)

    @classmethod
    def tearDownClass(cls):
        ray.shutdown()
        cls.folder.cleanup()

    def build(self, runners):
        algorithm = build_algorithm(SEED, env_runners=runners)
        self.addCleanup(algorithm.stop)
        return algorithm

    def test_two_runners_save_and_resume(self):
        first = self.build(2)
        start = dict(remote_runners(first, _runner_rng))
        self.assertEqual(sorted(start), [1, 2])
        for index, state in start.items():      # the stream of (seed, worker index) after the first episode's seed
            stream = np.random.default_rng([SEED, index])
            stream.integers(0, 2**63)            # RLlib resets the environment once when it builds the runner
            self.assertTrue(same(state['episode_rng'], stream.bit_generator.state))
        self.assertFalse(same(start[1]['episode_rng'], start[2]['episode_rng']))
        self.assertEqual(remote_runners(first, _runner_threads), [1, 1])    # no oversubscription by the runners

        trained = train(first)
        played = dict(remote_runners(first, _runner_rng))
        for index in (1, 2):                     # each runner drew its own episode seed
            self.assertFalse(same(played[index]['episode_rng'], start[index]['episode_rng']))
        self.assertFalse(same(played[1]['episode_rng'], played[2]['episode_rng']))

        save_run(first, self.root/'first', settings(2), 1)
        saved = torch.load(self.root/'first'/'rng.pt', weights_only=False)
        self.assertIsNone(saved['episode_rng'])
        self.assertEqual(sorted(saved['runners']), [1, 2])
        self.assertTrue(same(saved['runners'], played))

        after = []
        for _ in range(2):                       # two resumes of the same checkpoint
            resumed = self.build(2)
            self.assertEqual(restore_run(resumed, self.root/'first', settings(2)), 1)
            torch.testing.assert_close(parameter_vector(resumed), trained, rtol=0, atol=0)
            self.assertTrue(same(dict(remote_runners(resumed, _runner_rng)), played))
            after.append(train(resumed))
            # New episodes at the resume boundary: each runner drew exactly the next seed of its saved stream.
            for index, state in dict(remote_runners(resumed, _runner_rng)).items():
                stream = np.random.default_rng()
                stream.bit_generator.state = played[index]['episode_rng']
                stream.integers(0, 2**63)
                self.assertTrue(same(state['episode_rng'], stream.bit_generator.state))
            resumed.stop()
        self.assertFalse(torch.equal(after[0], trained))
        # The resume is exact: both resumed runs sample and learn the same next iteration.
        torch.testing.assert_close(after[0], after[1], rtol=0, atol=0)

        # A different number of sampling processes is not a resume of this run.
        with self.assertRaises(ValueError):
            restore_run(None, self.root/'first', settings(0))
        with self.assertRaises(ValueError):
            restore_run(None, self.root/'first', settings(3))

    def test_single_process_keeps_its_format(self):
        first = self.build(0)
        train(first)
        state = episode_env(first.env_runner).episode_rng_state()
        legacy = {key: value for key, value in settings(0).items() if key not in ('env_runners', 'minibatch_size')}
        save_run(first, self.root/'single', legacy, 1)      # settings as saved before the new arguments
        saved = torch.load(self.root/'single'/'rng.pt', weights_only=False)
        self.assertTrue(same(saved['episode_rng'], state))
        self.assertEqual(saved['runners'], {})
        resumed = self.build(0)
        self.assertEqual(restore_run(resumed, self.root/'single', settings(0)), 1)
        self.assertTrue(same(episode_env(resumed.env_runner).episode_rng_state(), state))
        train(resumed)


class LearnerDevice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(2)
        ray.init(num_cpus=4, include_dashboard=False, object_store_memory=1024**3, log_to_driver=False)

    @classmethod
    def tearDownClass(cls):
        ray.shutdown()

    def test_learner_device(self):
        self.assertEqual(learner_device(False), 'cpu')
        with unittest.mock.patch('torch.cuda.is_available', return_value=False):
            with self.assertRaises(ValueError):
                learner_device(True)
        with unittest.mock.patch('torch.cuda.is_available', return_value=True):
            self.assertEqual(learner_device(True), 'cuda')

    def test_cpu_learner_is_checked_and_saved_on_cpu(self):
        algorithm = build_algorithm(SEED, env_runners=0)
        self.addCleanup(algorithm.stop)
        require_learner_device(algorithm, 'cpu')
        with self.assertRaises(RuntimeError):
            require_learner_device(algorithm, 'cuda')
        train(algorithm)
        with tempfile.TemporaryDirectory() as folder:
            run = Path(folder)/'run'
            save_run(algorithm, run, {**settings(0), 'device': 'cpu'}, 1)
            self.assertIsNone(torch.load(run/'rng.pt', weights_only=False)['torch_cuda'])
            weights = torch.load(run/'inference.pt', weights_only=True)
            self.assertTrue(weights)
            self.assertTrue(all(value.device.type == 'cpu' for value in weights.values()))

    @unittest.skipUnless(torch.cuda.is_available(), 'no CUDA device')
    def test_gpu_learner_updates_on_cuda(self):
        algorithm = build_algorithm(SEED, env_runners=0, learner_gpu=True)
        self.addCleanup(algorithm.stop)
        require_learner_device(algorithm, 'cuda')
        learner = algorithm.train()['learners']['shared']
        self.assertTrue(np.isfinite(learner['total_loss']))


class SpeedSummary(unittest.TestCase):
    def test_summarize(self):
        from ppo_speed import summarize
        report = {'iteration_seconds': [100.0, 80.0], 'peak_driver_rss_mib': 900.0, 'results': [
            {'num_env_steps_sampled_lifetime': 256, 'timers': {'env_runner_sampling_timer': 70, 'learner_update_timer': 28},
             'env_runners': {}, 'learners': {'shared': {'total_loss': 2.0}}},
            {'num_env_steps_sampled_lifetime': 512, 'timers': {'env_runner_sampling_timer': 50, 'learner_update_timer': 30},
             'env_runners': {'num_episodes': 1, 'episode_len_mean': 400.0}, 'learners': {'shared': {'total_loss': 1.5}}}]}
        arm = summarize(report, 256)
        self.assertEqual((arm['iterations'], arm['seconds'], arm['decisions']), (2, 180.0, 512.0))
        self.assertEqual(arm['decisions_per_hour'], 10240)
        self.assertEqual((arm['sampling_seconds_mean'], arm['update_seconds_mean']), (60.0, 29.0))
        self.assertEqual((arm['episodes_finished'], arm['games_per_hour'], arm['games_per_hour_by_length']),
                         (1.0, 20.0, 25.6))
        self.assertEqual((arm['total_loss_first'], arm['total_loss_last']), (2.0, 1.5))
        # No result rows (an arm that wrote only its timings): decisions fall back to batch size x iterations.
        self.assertEqual(summarize({'iteration_seconds': [10.0]}, 256)['decisions'], 256.0)


class SpeedMemory(unittest.TestCase):
    def test_meminfo_mib(self):
        from ppo_speed import meminfo_mib
        text = ('MemTotal:       16384000 kB\nMemFree:         1024000 kB\nMemAvailable:    8192000 kB\n'
                'Shmem:           2048000 kB\n')
        self.assertEqual(meminfo_mib(text), {'MemTotal': 16000.0, 'MemAvailable': 8000.0, 'Shmem': 2000.0})
        without = meminfo_mib('MemTotal: 1024 kB\nMemAvailable: 2048 kB\n')
        self.assertEqual(without, {'MemTotal': 1.0, 'MemAvailable': 2.0, 'Shmem': None})

    def test_tree_pss_mib(self):
        from ppo_speed import tree_pss_mib
        with tempfile.TemporaryDirectory() as folder:
            proc = Path(folder)
            (proc/'self').mkdir()
            for pid, name, parent, pss in ((10, '(train)', 1, 1024), (11, '(ray::Env Runner)', 10, 2048),
                                           (12, '(a) b)', 11, 4096), (13, '(other)', 1, 8192)):
                (proc/str(pid)).mkdir()
                (proc/str(pid)/'stat').write_text(f'{pid} {name} S {parent} {pid} 0 0 -1 4194304\n')
                (proc/str(pid)/'smaps_rollup').write_text(f'Rss:  {pss*2} kB\nPss:  {pss} kB\n')
            self.assertEqual(tree_pss_mib(10, proc), (7.0, 3))
            (proc/'12'/'smaps_rollup').unlink()
            self.assertEqual(tree_pss_mib(10, proc), (3.0, 2))


if __name__ == '__main__':
    unittest.main()
