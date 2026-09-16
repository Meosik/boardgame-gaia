from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from deploy_replays import deploy, remote_publish


class ReplayDeploymentTests(unittest.TestCase):
    def test_changed_origin_stops_before_any_publication_or_copy(self):
        with tempfile.TemporaryDirectory() as temporary:
            stage = Path(temporary)
            outputs = [b'{"StartedAt":"before"}', b'container', b'sha256:old', b'gaia:test', b'changed catalog']
            with patch('deploy_replays.validate_batch'), \
                    patch('deploy_replays.command', side_effect=outputs), \
                    patch('deploy_replays.publish') as publication, \
                    patch('deploy_replays.shutil.copytree') as copying:
                with self.assertRaisesRegex(ValueError, 'Origin catalog changed'):
                    remote_publish(stage, 'expected hash', 123)
                publication.assert_not_called()
                copying.assert_not_called()

    def test_failed_remote_publish_preserves_diagnostic_location(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            def execute(args, **kwargs):
                if args[0] == 'curl':
                    return b'{"schema_version":1,"games":[]}'
                if args[0] == 'ssh':
                    return b'/tmp/gaia-auto-replays.test\n'
                return b''
            with patch('deploy_replays.validate_batch', return_value=[]), \
                    patch('deploy_replays.command', side_effect=execute), \
                    patch('deploy_replays.subprocess.run', return_value=subprocess.CompletedProcess([], 1, b'', b'failed')):
                with self.assertRaises(subprocess.CalledProcessError):
                    deploy(root/'source', root/'evidence')
            self.assertTrue((root/'evidence/remote-stage.json').exists())
            self.assertEqual((root/'evidence/deploy.log').read_bytes(), b'failed')
            self.assertFalse((root/'evidence/receipt.json').exists())


if __name__ == '__main__':
    unittest.main()
