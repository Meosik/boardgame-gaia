"""Check actual Codex sandbox boundaries without making model calls."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

from handoff_loop import role_config_args


PROBE = r'''
import errno
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import sys
import threading
import urllib.error
import urllib.request

role, inside_name, outside_name = sys.argv[1:]
checks = []
inside = Path(inside_name)
inside.write_text('workspace-write-ok')
assert inside.read_text() == 'workspace-write-ok'
inside.unlink()
checks.append('workspace-read-write-ok')
try:
    Path(outside_name).write_text('unexpected')
except OSError as error:
    assert error.errno in (errno.EACCES, errno.EPERM, errno.EROFS), error
    checks.append('outside-write-denied')
else:
    raise AssertionError('outside write allowed')

if role == 'astra':
    try:
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except PermissionError:
        checks.append('astra-network-denied')
    else:
        connection.close()
        raise AssertionError('Astra network socket allowed')
else:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'local-ok')

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
        try:
            connection.request('GET', '/')
            response = connection.getresponse()
            assert response.status == 200 and response.read() == b'local-ok'
            checks.append('sol-loopback-http-ok')
        finally:
            connection.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(3)
        assert not thread.is_alive()

    for address in ('1.1.1.1', '192.168.1.1'):
        with socket.socket() as connection:
            connection.settimeout(2)
            try:
                connection.connect((address, 443))
            except OSError as error:
                # A timeout alone would not establish enforcement.
                assert error.errno in (errno.EPERM, errno.EACCES, errno.ENETUNREACH), error
                checks.append('direct-egress-denied:' + address)
            else:
                raise AssertionError('direct egress allowed: ' + address)
    try:
        with urllib.request.urlopen('https://example.com/', timeout=3):
            raise AssertionError('proxy allowed external destination')
    except urllib.error.URLError as error:
        assert '403 Forbidden' in str(error), error
        checks.append('proxy-external-destination-denied')
print(json.dumps({'role': role, 'checks': checks}))
'''


def main():
    root = Path(__file__).resolve().parents[1]
    logs = root / 'handoff/logs'
    logs.mkdir(parents=True, exist_ok=True)
    results = []
    with tempfile.TemporaryDirectory(prefix='.gaia-sandbox-probe-', dir=Path.home()) as directory:
        outside = Path(directory) / 'guard.txt'
        outside.write_text('unchanged')
        for role in ('astra', 'sol'):
            inside = logs / f'.sandbox-probe-{os.getpid()}-{role}.tmp'
            command = [os.environ.get('HANDOFF_CODEX', 'codex'), 'sandbox',
                       '-c', 'sandbox_mode="workspace-write"', *role_config_args(role),
                       '--', 'python3', '-c', PROBE, role, str(inside), str(outside)]
            try:
                result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=20)
                if result.returncode != 0:
                    raise RuntimeError(f'{role} sandbox probe failed: {result.stderr}\n{result.stdout}')
                assert outside.read_text() == 'unchanged'
                results.append(json.loads(result.stdout))
            finally:
                inside.unlink(missing_ok=True)
    print(json.dumps({'status': 'pass', 'results': results}, indent=2))


if __name__ == '__main__':
    main()
