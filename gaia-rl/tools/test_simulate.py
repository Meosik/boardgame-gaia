import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from simulate import finish, run_evaluation


class AutomaticReplayTests(unittest.TestCase):
    def test_resource_plans_use_the_explicit_runner_without_training(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = SimpleNamespace(kind='resources', output=Path(temporary)/'run', stages='0,1',
                                   specs=Path(temporary)/'specs.json')
            with patch('simulate.subprocess.run') as process, patch('simulate.finish') as publication:
                process.return_value.returncode = 0
                run_evaluation(args)
                self.assertIn('resource_plans.evaluate', process.call_args.args[0])
                self.assertNotIn('gaia_rl.training', process.call_args.args[0])
                publication.assert_called_once_with(args.output)

    def test_research_comparison_is_explicit_and_automatically_published(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = SimpleNamespace(kind='research', output=Path(temporary)/'run', stages='0,1',
                                   specs=Path(temporary)/'specs.json')
            with patch('simulate.subprocess.run') as process, patch('simulate.finish') as publication:
                process.return_value.returncode = 0
                run_evaluation(args)
                command = process.call_args.args[0]
                self.assertIn('research_plans.evaluate', command)
                self.assertIn(str(args.specs), command)
                publication.assert_called_once_with(args.output)

    def test_standard_teacher_selects_booster12_adapter_and_auto_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = SimpleNamespace(kind='purpose', output=Path(temporary)/'run', stages='0,1', specs=None)
            with patch('simulate.subprocess.run') as process, patch('simulate.finish') as publication:
                process.return_value.returncode = 0
                run_evaluation(args)
                command = process.call_args.args[0]
                self.assertIn('current_actions.evaluate', command)
                self.assertNotIn('action_purpose.evaluate', command)
                self.assertNotIn('gaia_rl.training', command)
                publication.assert_called_once_with(args.output)

    def test_standard_ppo_command_automatically_finishes_without_training(self):
        from gaia_rl.versions import runtime_versions
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checkpoint = root/'checkpoint'
            checkpoint.mkdir()
            (checkpoint/'metadata.json').write_text(json.dumps({'versions': runtime_versions()}))
            args = SimpleNamespace(kind='ppo', output=root/'run', checkpoint=checkpoint,
                                   seeds=2, seed_prefix='fixed-eval', opponent=None)
            with patch('simulate.subprocess.run') as process, patch('simulate.finish') as publication:
                process.return_value.returncode = 0
                run_evaluation(args)
                command = process.call_args.args[0]
                self.assertIn('gaia_rl.evaluation', command)
                self.assertNotIn('gaia_rl.training', command)
                publication.assert_called_once_with(args.output)

    def test_publication_failure_preserves_run_and_retry_does_not_simulate(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run/'browser-replays').mkdir()
            (run/'report.json').write_text('{"saved": true}')
            with patch('simulate.export_evaluation', return_value=run/'browser-replays'), \
                    patch('simulate.deploy', side_effect=RuntimeError('network unavailable')), \
                    patch('simulate.subprocess.run') as simulation:
                with self.assertRaisesRegex(RuntimeError, 'network'):
                    finish(run)
                simulation.assert_not_called()
            self.assertEqual((run/'report.json').read_text(), '{"saved": true}')
            self.assertEqual(json.loads((run/'publication.json').read_text())['status'], 'failed')
            with patch('simulate.export_evaluation', return_value=run/'browser-replays'), \
                    patch('simulate.deploy', return_value={'visible': 24}) as deployment, \
                    patch('simulate.subprocess.run') as simulation:
                finish(run)
                self.assertEqual(json.loads((run/'publication.json').read_text())['status'], 'published')
                finish(run)
                deployment.assert_called_once()
                simulation.assert_not_called()

    def test_invalid_export_never_reaches_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run/'browser-replays').mkdir()
            with patch('simulate.export_evaluation', side_effect=ValueError('Incomplete')), \
                    patch('simulate.deploy') as deployment:
                with self.assertRaises(ValueError):
                    finish(run)
                deployment.assert_not_called()


if __name__ == '__main__':
    unittest.main()
