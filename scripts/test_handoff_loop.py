"""No paid model calls: exercise the real supervisor with a local fake CLI."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

SCRIPT = Path(__file__).with_name('handoff_loop.py')
REPO = SCRIPT.parents[1]
spec = importlib.util.spec_from_file_location('handoff_loop', SCRIPT)
loop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loop)
FAKE = '''#!/usr/bin/env python3
import json, os, pathlib, sys, time
root = pathlib.Path.cwd()
calls = root/'calls.json'
rows = json.loads(calls.read_text()) if calls.exists() else []
role = sys.argv[sys.argv.index('--model')+1]
rows.append({'model':role,'args':sys.argv[1:],'engine':os.environ['GAIA_ENGINE_FIXES_2'],
             'prompt':sys.stdin.read()})
calls.write_text(json.dumps(rows))
statuses = json.loads(os.environ.get('FAKE_STATUSES','["pass"]'))
status = statuses[min(len(rows)-1,len(statuses)-1)]
if status == 'sleep':
    (root/'child.pid').write_text(str(os.getpid()))
    time.sleep(30)
if status == 'exit': sys.exit(2)
if status == 'missing': sys.exit(0)
if status == 'null':
    pathlib.Path(sys.argv[sys.argv.index('--output-last-message')+1]).write_text('null')
    sys.exit(0)
if status == 'human_edit':
    (root/'handoff/QUEUE.md').write_text('next: human\\n# edited by user\\n')
    status='pass'
pathlib.Path(sys.argv[sys.argv.index('--output-last-message')+1]).write_text(
    json.dumps({'status':status,'summary':'test result','evidence':['mock evidence']}))
print('test stdout')
print('test stderr',file=sys.stderr)
'''


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root/'handoff').mkdir()
        for name in ('ASTRA_PROMPT.md', 'SOL_PROMPT.md', 'result.schema.json'):
            shutil.copyfile(REPO/'handoff'/name, self.root/'handoff'/name)
        self.queue = self.root/'handoff/QUEUE.md'
        self.queue.write_text('next: astra\n# approved mock task\n')
        self.fake = self.root/'fake-codex'
        self.fake.write_text(FAKE)
        self.fake.chmod(0o755)
        self.status = self.root/'gaia-rl/research/strategy/STATUS.md'
        self.status.parent.mkdir(parents=True)
        self.status.write_text('# Existing results must survive\n')

    def command(self, cycles=6, seconds=1):
        return [sys.executable, str(SCRIPT), '--root', str(self.root),
                '--poll-seconds', '.01', '--max-cycles', str(cycles),
                '--max-seconds', str(seconds)]

    def environment(self, statuses):
        return dict(os.environ, HANDOFF_CODEX=str(self.fake), FAKE_STATUSES=json.dumps(statuses))

    def run_loop(self, statuses=('pass',), cycles=6, seconds=1):
        result = subprocess.run(self.command(cycles, seconds), env=self.environment(statuses),
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.status.read_text().startswith('# Existing results must survive'))
        return json.loads((self.root/'handoff/.loop-state.json').read_text())

    def calls(self):
        path = self.root/'calls.json'
        return json.loads(path.read_text()) if path.exists() else []

    def test_six_calls_alternate_and_capture_unique_logs(self):
        state = self.run_loop(seconds=3)
        self.assertEqual(state['cycles'], 6)
        self.assertEqual([r['model'] for r in self.calls()], ['gpt-6-astra','gpt-6-sol']*3)
        for row in self.calls():
            self.assertEqual(row['engine'], '1')
            self.assertNotIn('--dangerously-bypass-approvals-and-sandbox', row['args'])
            self.assertIn('구현 담당' if row['model'].endswith('astra') else '검증 담당', row['prompt'])
            configs = [row['args'][i+1] for i, arg in enumerate(row['args']) if arg == '-c']
            if row['model'].endswith('sol'):
                self.assertTrue(set(loop.SOL_NETWORK_CONFIG).issubset(configs))
            else:
                self.assertFalse(set(loop.SOL_NETWORK_CONFIG).intersection(configs))
        logs = list((self.root/'handoff/logs').glob('*.log'))
        self.assertEqual(len(logs), 6)
        self.assertTrue(all('test stderr' in p.read_text() for p in logs))
        self.assertEqual(loop.next_role(self.queue.read_text()), 'human')

    def test_human_wait_never_invokes_cli(self):
        self.queue.write_text('next: human\n')
        state = self.run_loop(seconds=.15)
        self.assertEqual(state['cycles'], 0)
        self.assertEqual(self.calls(), [])

    def test_sol_network_permission_is_paired_with_exact_proxy_policy(self):
        self.assertEqual(loop.role_config_args('astra'), [])
        self.assertEqual(loop.role_config_args('sol'), [
            '-c', 'sandbox_workspace_write.network_access=true',
            '-c', 'features.network_proxy.enabled=true',
            '-c', 'features.network_proxy.domains={"127.0.0.1"="allow"}',
            '-c', 'features.network_proxy.allow_local_binding=false',
            '-c', 'features.network_proxy.allow_upstream_proxy=false',
        ])

    def test_two_mixed_failures_go_to_human(self):
        state = self.run_loop(('gate_failed','exit'))
        self.assertEqual(state['cycles'], 2)
        self.assertEqual(state['failures'], 2)
        self.assertEqual(loop.next_role(self.queue.read_text()), 'human')

    def test_success_resets_failure_streak(self):
        state = self.run_loop(('gate_failed','pass','gate_failed','gate_failed'), seconds=2)
        self.assertEqual(state['cycles'], 4)
        self.assertEqual(state['failures'], 2)

    def test_missing_result_is_failure_not_success(self):
        state = self.run_loop(('missing',))
        self.assertEqual(state['cycles'], 2)
        self.assertEqual(state['failures'], 2)

    def test_explicit_human_result_stops_automatic_work(self):
        state = self.run_loop(('human',))
        self.assertEqual(state['cycles'], 1)

    def test_invalid_json_shape_counts_as_failure(self):
        state = self.run_loop(('null',))
        self.assertEqual(state['cycles'], 2)
        self.assertEqual(state['failures'], 2)

    def test_external_queue_edit_is_preserved(self):
        self.run_loop(('human_edit',))
        self.assertEqual(self.queue.read_text(), 'next: human\n# edited by user\n')

    def test_timeout_terminates_inflight_process(self):
        before = time.monotonic()
        state = self.run_loop(('sleep',), seconds=.3)
        self.assertLess(time.monotonic()-before, 3)
        self.assertEqual(state['cycles'], 1)
        pid = int((self.root/'child.pid').read_text())
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    def test_restart_does_not_reset_limits(self):
        first = self.run_loop(cycles=1)
        second = self.run_loop(cycles=1)
        self.assertEqual(first['deadline'], second['deadline'])
        self.assertEqual(len(self.calls()), 1)

    def test_recovered_inflight_attempt_requires_human(self):
        (self.root/'handoff/.loop-state.json').write_text(json.dumps(
            {'cycles':1,'failures':0,'inflight':'astra','deadline':time.time()+.2}))
        state = self.run_loop()
        self.assertEqual(state['cycles'], 1)
        self.assertEqual(self.calls(), [])

    def test_duplicate_runner_refused(self):
        self.queue.write_text('next: human\n')
        first = subprocess.Popen(self.command(seconds=2), env=self.environment(['pass']),
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(100):
                if (self.root/'handoff/.loop-state.json').exists(): break
                time.sleep(.01)
            second = subprocess.run(self.command(), env=self.environment(['pass']),
                                    capture_output=True, timeout=3)
            self.assertEqual(second.returncode, 2)
            self.assertIn(b'already running', second.stderr)
        finally:
            first.terminate()
            first.wait(timeout=3)

    def test_malformed_queue_never_runs(self):
        self.queue.write_text('next: sol\nnext: astra\n')
        result = subprocess.run(self.command(), capture_output=True, timeout=3)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.calls(), [])


if __name__ == '__main__':
    unittest.main()
