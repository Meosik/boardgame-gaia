import importlib.util
import json
import os
import re
import socket
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

SPEC = importlib.util.spec_from_file_location('gpu_smoke', Path(__file__).with_name('gpu_smoke.py'))
smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke)


class SmokeTests(unittest.TestCase):
    def test_launcher_scratch_fits_ray_unix_socket(self):
        script = Path(__file__).with_name('gpu_smoke.sh').read_text()
        template = re.search(r'mktemp -d "([^"]+)"', script).group(1)
        template = template.replace('${USER}', 'shgkoihe')
        with tempfile.TemporaryDirectory(prefix=Path(template).name.rstrip('X'),
                                         dir=Path(template).parent) as directory:
            path = Path(directory) / ('result/tmp/ray/'
                'session_2026-09-17_02-50-00_123456_4194304/sockets/plasma_store')
            path.parent.mkdir(parents=True)
            with socket.socket(socket.AF_UNIX) as connection:
                connection.bind(str(path))

    def test_no_allocation_rejected(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'Slurm'):
                smoke.require_compute_node()

    def test_login_host_rejected_even_with_job_id(self):
        with patch.dict(os.environ, {'SLURM_JOB_ID': '1', 'SLURM_JOB_NODELIST': 'moana-u2'}), \
                patch.object(smoke.subprocess, 'check_output', return_value='moana-u2\n'), \
                patch.object(smoke.socket, 'gethostname', return_value='moana'):
            with self.assertRaisesRegex(RuntimeError, 'not an allocated'):
                smoke.require_compute_node()

    def test_allocated_host_accepted(self):
        with patch.dict(os.environ, {'SLURM_JOB_ID': '1', 'SLURM_JOB_NODELIST': 'moana-u2'}), \
                patch.object(smoke.subprocess, 'check_output', return_value='moana-u2\n'), \
                patch.object(smoke.socket, 'gethostname', return_value='moana-u2.khu.ac.kr'):
            smoke.require_compute_node()

    def test_shell_rejects_before_python(self):
        env = os.environ.copy()
        env.pop('SLURM_JOB_ID', None)
        result = subprocess.run(['bash', str(Path(__file__).with_name('gpu_smoke.sh'))],
                                env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Enter a Slurm GPU allocation', result.stderr)

    def test_output_private_and_never_overwritten(self):
        with tempfile.TemporaryDirectory(prefix='gaia-test-', dir='/tmp') as directory, \
                patch.dict(os.environ):
            output = Path(directory) / 'result'
            self.assertEqual(smoke.prepare_output(output), output)
            self.assertEqual(os.environ['HOME'], str(output / 'home'))
            with self.assertRaises(FileExistsError):
                smoke.prepare_output(output)

    def test_nas_output_rejected(self):
        with self.assertRaisesRegex(ValueError, 'node-local'):
            smoke.prepare_output(Path('/data/someone/result'))

    def test_symlink_to_nas_rejected(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as directory:
            link = Path(directory) / 'nas'
            link.symlink_to('/data')
            with self.assertRaisesRegex(ValueError, 'node-local'):
                smoke.prepare_output(link / 'somebody' / 'result')

    def test_failure_has_no_completion_marker(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as directory, patch.dict(os.environ):
            output = Path(directory) / 'result'
            with patch('sys.argv', ['gpu_smoke.py', '--output', str(output)]), \
                    patch.object(smoke, 'require_compute_node'), \
                    patch.object(smoke, 'run_smoke', side_effect=RuntimeError('test failure')):
                with self.assertRaisesRegex(RuntimeError, 'test failure'):
                    smoke.main()
            self.assertFalse((output / 'complete.json').exists())
            self.assertEqual(json.loads((output / 'failure.json').read_text())['status'], 'failed')

    def test_actual_learner_cpu_rejected(self):
        import torch
        learner = SimpleNamespace(module={'shared': torch.nn.Linear(2, 2)})
        algorithm = SimpleNamespace(learner_group=SimpleNamespace(
            foreach_learner=lambda function: function(learner)))
        with self.assertRaisesRegex(RuntimeError, 'not all on CUDA'):
            smoke.learner_state(algorithm)

    def test_cpu_fallback_rejected(self):
        import torch
        with patch.object(torch.cuda, 'is_available', return_value=False):
            with self.assertRaisesRegex(RuntimeError, 'no CPU fallback'):
                smoke.run_smoke(Path('/tmp/unused-gaia-smoke'))

    def test_multiple_visible_gpus_rejected(self):
        import torch
        with patch.object(torch.cuda, 'is_available', return_value=True), \
                patch.object(torch.cuda, 'device_count', return_value=2):
            with self.assertRaisesRegex(RuntimeError, 'Exactly one'):
                smoke.run_smoke(Path('/tmp/unused-gaia-smoke'))

    def test_learning_settings_match_existing_cpu_pilot(self):
        from ray.rllib.algorithms.ppo import PPOConfig
        from gaia_rl.training import build_algorithm
        with patch.object(PPOConfig, 'build_algo', autospec=True, side_effect=lambda config: config):
            baseline = build_algorithm()
        gpu = smoke.build_config()
        self.assertEqual(baseline.num_gpus_per_learner, 0)
        self.assertEqual(gpu.num_gpus_per_learner, 1)
        for key in ('num_learners', 'local_gpu_idx', 'env', 'env_config',
                    'disable_env_checking', 'framework_str', 'num_env_runners',
                    'rollout_fragment_length', 'batch_mode', 'gamma',
                    'train_batch_size_per_learner', 'minibatch_size', 'num_epochs',
                    'lr', 'grad_clip', 'policies', 'policy_mapping_fn', 'seed'):
            self.assertEqual(getattr(baseline, key), getattr(gpu, key), key)
        self.assertEqual(baseline.rl_module_spec.module_class, gpu.rl_module_spec.module_class)
        self.assertEqual(baseline.rl_module_spec.model_config, gpu.rl_module_spec.model_config)


if __name__ == '__main__':
    unittest.main()
