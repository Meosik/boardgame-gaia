"""Bounded, single-owner CLI handoff loop. Entry point: handoff_loop.sh."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

BEGIN = '<!-- HANDOFF LOOP START -->'
END = '<!-- HANDOFF LOOP END -->'
NEXT = re.compile(r'^next:\s*(sol|astra|human)\s*$', re.MULTILINE)
MODELS = {'astra': 'gpt-6-astra', 'sol': 'gpt-6-sol'}
SOL_NETWORK_CONFIG = (
    'sandbox_workspace_write.network_access=true',
    'features.network_proxy.enabled=true',
    'features.network_proxy.domains={"127.0.0.1"="allow"}',
    'features.network_proxy.allow_local_binding=false',
    'features.network_proxy.allow_upstream_proxy=false',
)


def role_config_args(role):
    # Network access alone would allow arbitrary egress: always pair it with
    # the enforced proxy and exact loopback allowlist. Astra stays unchanged.
    configs = SOL_NETWORK_CONFIG if role == 'sol' else ()
    return [argument for config in configs for argument in ('-c', config)]


def atomic_write(path, text):
    temporary = path.with_name(f'.{path.name}.{os.getpid()}.tmp')
    temporary.write_text(text)
    temporary.replace(path)


def next_role(text):
    matches = NEXT.findall(text)
    if len(matches) != 1 or len(re.findall(r'^next:', text, re.MULTILINE)) != 1:
        raise ValueError('QUEUE requires exactly one next: sol|astra|human')
    return matches[0]


def transition(path, expected, role):
    # Never overwrite a human edit made while a CLI was running.
    actual = path.read_text()
    if actual != expected:
        return False
    atomic_write(path, NEXT.sub(f'next: {role}', actual, count=1))
    return True


def stop_process(process):
    # A CLI can spawn test runners; terminate the entire process group.
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


class Loop:
    def __init__(self, args):
        self.args = args
        self.root = args.root.resolve()
        self.handoff = self.root / 'handoff'
        self.logs = self.handoff / 'logs'
        self.queue = self.handoff / 'QUEUE.md'
        self.status = self.root / 'gaia-rl/research/strategy/STATUS.md'
        self.state_path = self.handoff / '.loop-state.json'
        self.stopping = False
        self.child = None
        self.state = {}

    def save(self):
        atomic_write(self.state_path, json.dumps(self.state, indent=2) + '\n')

    def report(self, message):
        stamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
        message = message.replace('\n', ' ').replace('|', '/')
        block = (f'{BEGIN}\n\n## Handoff 자동화\n\n'
                 f'| 상태 | CLI 실행 | 연속 실패 | PID | 갱신(UTC) |\n'
                 f'|---|---:|---:|---:|---|\n'
                 f'| {message} | {self.state["cycles"]}/6 | '
                 f'{self.state["failures"]}/2 | {os.getpid()} | {stamp} |\n\n{END}')
        original = self.status.read_text() if self.status.exists() else '# STATUS\n'
        if BEGIN in original and END in original:
            original = re.sub(re.escape(BEGIN) + r'.*?' + re.escape(END),
                              lambda _: block, original, flags=re.DOTALL)
        else:
            original = original.rstrip() + '\n\n' + block + '\n'
        self.status.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(self.status, original)
        print(f'{stamp} {message}', flush=True)

    def request_stop(self, *_):
        self.stopping = True

    def human(self):
        text = self.queue.read_text()
        try:
            next_role(text)
        except ValueError:
            return  # Preserve malformed input for the human to repair.
        transition(self.queue, text, 'human')

    def invoke(self, role, queue_text):
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        prefix = self.logs / f'{stamp}-{self.state["cycles"]:02d}-{role}'
        result_path = prefix.with_suffix('.result.json')
        prompt_path = self.handoff / f'{role.upper()}_PROMPT.md'
        command = [os.environ.get('HANDOFF_CODEX', 'codex'), 'exec',
                   '--model', MODELS[role], '--sandbox', 'workspace-write',
                   '-c', 'approval_policy="never"', '--cd', str(self.root),
                   *role_config_args(role),
                   '--json', '--color', 'never',
                   '--output-schema', str(self.handoff / 'result.schema.json'),
                   '--output-last-message', str(result_path), '-']
        environment = dict(os.environ, GAIA_ENGINE_FIXES_2='1')
        atomic_write(prefix.with_suffix('.queue.md'), queue_text)
        try:
            with prompt_path.open('rb') as prompt, prefix.with_suffix('.log').open('wb') as log:
                self.child = subprocess.Popen(command, cwd=self.root, env=environment,
                                              stdin=prompt, stdout=log, stderr=log,
                                              start_new_session=True)
                while self.child.poll() is None:
                    if self.stopping or time.time() >= self.state['deadline']:
                        stop_process(self.child)
                        return 'human', '중단 요청 또는 8시간 한도'
                    try:
                        current = self.queue.read_text()
                        if current != queue_text and next_role(current) == 'human':
                            stop_process(self.child)
                            return 'human', '사람이 next: human으로 중단'
                    except (OSError, ValueError):
                        stop_process(self.child)
                        return 'gate_failed', '실행 중 QUEUE 누락/형식 오류'
                    time.sleep(min(.2, self.args.poll_seconds))
                if self.child.returncode != 0:
                    return 'gate_failed', f'{role} CLI exit={self.child.returncode}; {prefix.name}.log'
            result = json.loads(result_path.read_text())
            if (not isinstance(result, dict)
                    or set(result) != {'status', 'summary', 'evidence'}
                    or result['status'] not in ('pass', 'gate_failed', 'human')
                    or not isinstance(result['summary'], str)
                    or not isinstance(result['evidence'], list)
                    or not all(isinstance(item, str) for item in result['evidence'])):
                raise ValueError('invalid result schema')
            return result['status'], result['summary']
        except (OSError, ValueError) as error:
            with prefix.with_suffix('.log').open('a') as log:
                log.write(f'\nSupervisor error: {error}\n')
            return 'gate_failed', f'{role} 실행/결과 오류; {prefix.name}.log'
        finally:
            if self.child is not None:
                # Also reap lingering workers after the CLI exits normally.
                stop_process(self.child)
                self.child = None

    def run(self):
        self.logs.mkdir(parents=True, exist_ok=True)
        with (self.handoff / '.loop.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print('handoff loop already running', file=sys.stderr)
                return 2
            signal.signal(signal.SIGTERM, self.request_stop)
            signal.signal(signal.SIGINT, self.request_stop)
            if self.state_path.exists():
                self.state = json.loads(self.state_path.read_text())
                if self.state.get('inflight'):
                    self.human()
                    self.state['inflight'] = None
                    self.save()
            else:
                self.state = {'cycles': 0, 'failures': 0, 'inflight': None,
                              'deadline': time.time() + self.args.max_seconds}
            # Restart never grants another eight hours or six attempts.
            self.state['deadline'] = min(self.state['deadline'],
                                         time.time() + self.args.max_seconds)
            self.save()
            self.report('시작; Astra 구현 / Sol 검증')
            notified = False
            while not self.stopping:
                if (self.state['cycles'] >= self.args.max_cycles
                        or time.time() >= self.state['deadline']):
                    self.human()
                    self.report('자동 중단: 실행 횟수 또는 시간 한도')
                    return 0
                try:
                    queue_text = self.queue.read_text()
                    role = next_role(queue_text)
                except (OSError, ValueError) as error:
                    self.report(f'자동 중단: {error}')
                    return 2
                if role == 'human':
                    if not notified:
                        self.report('next: human — 과제/승인 대기, CLI 실행 없음')
                        notified = True
                else:
                    notified = False
                    self.state['cycles'] += 1
                    self.state['inflight'] = role
                    self.save()
                    self.report(f'{role} 실행 중')
                    result, summary = self.invoke(role, queue_text)
                    self.state['inflight'] = None
                    self.state['failures'] = self.state['failures'] + 1 if result == 'gate_failed' else 0
                    target = 'astra' if role == 'sol' else 'sol'
                    if result == 'human' or self.state['failures'] >= 2:
                        target = 'human'
                    if self.state['cycles'] >= self.args.max_cycles or time.time() >= self.state['deadline']:
                        target = 'human'
                    changed = transition(self.queue, queue_text, target)
                    if (self.state['failures'] >= 2
                            or self.state['cycles'] >= self.args.max_cycles
                            or time.time() >= self.state['deadline']):
                        # Limits override routing, but preserve the latest task text.
                        self.human()
                    if not changed:
                        summary += '; 외부 QUEUE 변경 보존'
                    self.save()
                    self.report(f'{role}: {result} — {summary}')
                    if (self.state['cycles'] >= self.args.max_cycles
                            or time.time() >= self.state['deadline']):
                        self.report('자동 중단: 실행 횟수 또는 시간 한도')
                        return 0
                remaining = max(0, self.state['deadline'] - time.time())
                time.sleep(min(self.args.poll_seconds, remaining))
            self.human()
            self.report('중단 요청 처리; next: human')
            return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--poll-seconds', type=float, default=10)
    parser.add_argument('--max-cycles', type=int, default=6)
    parser.add_argument('--max-seconds', type=float, default=8 * 60 * 60)
    args = parser.parse_args()
    if not 0 < args.max_cycles <= 6 or not 0 < args.max_seconds <= 28800 or args.poll_seconds <= 0:
        parser.error('limits may only be shortened: cycles 1..6, seconds (0,28800], poll > 0')
    return Loop(args).run()


if __name__ == '__main__':
    sys.exit(main())
