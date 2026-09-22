"""Loopback-only coaching API; explicit approvals are the only game mutation."""
import argparse
import fcntl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets

from .session import Conflict, Session


def handler(session, token, ui_port, api_port):
    allowed_hosts = {f'{host}:{port}' for host in ('localhost', '127.0.0.1')
                     for port in (ui_port, api_port)}

    class Handler(BaseHTTPRequestHandler):
        def send_json(self, status, value, *, download=False):
            body = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            if download:
                self.send_header('Content-Disposition', 'attachment; filename="coaching-record.json"')
            self.end_headers()
            self.wfile.write(body)

        def allowed(self):
            # Reject DNS rebinding and cross-origin mutation. No permissive CORS.
            if self.headers.get('Host') not in allowed_hosts:
                return False
            origin = self.headers.get('Origin')
            return not origin or origin in {f'http://{host}' for host in allowed_hosts}

        def do_GET(self):
            if not self.allowed():
                self.send_json(403, {'error': 'Local origin required'})
            elif self.path == '/coach-api/state':
                self.send_json(200, {**session.public(), 'token': token})
            elif self.path == '/coach-api/record':
                self.send_json(200, session.export(), download=True)
            else:
                self.send_json(404, {'error': 'Not found'})

        def do_POST(self):
            if (not self.allowed() or not secrets.compare_digest(
                    self.headers.get('X-Coach-Token', ''), token)):
                self.send_json(403, {'error': 'Local coaching token required'})
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if (not 0 < length <= 65536 or self.headers.get('Content-Type') != 'application/json'):
                    raise ValueError('Bounded JSON body required')
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError('JSON object required')
                if self.path == '/coach-api/approve':
                    session.approve(data.get('decision_id'), data.get('index'),
                                    data.get('reason', ''), data.get('plan', ''),
                                    data.get('technology_confirmed', False))
                elif self.path != '/coach-api/retry':
                    self.send_json(404, {'error': 'Not found'})
                    return
                session.start_recommendation()
                self.send_json(200, {**session.public(), 'token': token})
            except Conflict as error:
                self.send_json(409, {'error': str(error)})
            except (ValueError, TypeError) as error:
                self.send_json(400, {'error': str(error)})
            except Exception as error:
                self.log_error('Coaching request failed: %r', error)
                self.send_json(500, {'error': '기록/실행에 실패했습니다. 자동 진행하지 않습니다. 새로고침으로 상태를 확인해 주세요.'})

    return Handler


def teacher_factory(config, runtime_clock=None):
    from faction_teachers.clock import AdaptiveClock
    from four_factions.timed import TimedPreparationTeacher

    def make(prefix, memory):
        settings = config.get('clock', {'target_seconds': 10, 'long_seconds': 10, 'uses_per_seat': 0})
        if runtime_clock and len(prefix) >= runtime_clock['effective_from_decision']:
            settings = runtime_clock['clock']
        clock = AdaptiveClock(target_seconds=settings['target_seconds'],
                              long_seconds=settings['long_seconds'], uses=settings['uses_per_seat'],
                              state=memory.get('_clock') if settings['uses_per_seat'] else None)
        teacher = TimedPreparationTeacher(config['seed'], prefix=prefix,
            target_seconds=clock.target_seconds, maximum_seconds=clock.long_seconds,
            adaptive_clock=clock, bgg_openings=True, delta_factions=config['delta_factions'],
            fixed_openings=config.get('fixed_openings', False))
        teacher.memory = memory
        return teacher
    return make


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--seed', default='quartet-pilot-20260913-27703')
    parser.add_argument('--delta-factions', nargs='*', default=['HadschHallas', 'Taklons'])
    parser.add_argument('--port', type=int, default=8789)
    parser.add_argument('--ui-port', type=int, default=5174)
    args = parser.parse_args()
    from gaia_rl import Environment
    from gaia_rl.versions import runtime_versions
    from current_actions.ab_match import validate_seeds
    from four_factions.provenance import hashes, verify
    validate_seeds([args.seed])
    sources = {'versions': runtime_versions(), 'source_hashes': hashes()}
    verify(sources)
    config = {**sources, 'seed': args.seed, 'delta_factions': args.delta_factions,
              'fixed_openings': True,
              'clock': {'target_seconds': 10, 'long_seconds': 10, 'uses_per_seat': 0}}
    args.session.mkdir(parents=True, exist_ok=True)
    # Only one process can own this game's journal.
    with (args.session/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        original = args.session/'session.json'
        if original.exists():
            # Keep historical clock/source metadata immutable; amendments are separate.
            saved = json.loads(original.read_text())['config']
            if {k: v for k, v in saved.items() if k != 'clock'} != {k: v for k, v in config.items() if k != 'clock'}:
                raise ValueError('Saved teacher sources/setup differ')
            config = saved
        clock_path = args.session/'runtime-clock.json'
        runtime_clock = json.loads(clock_path.read_text()) if clock_path.exists() else None
        if runtime_clock and (runtime_clock.get('schema') != 1
                or type(runtime_clock.get('effective_from_decision')) is not int
                or runtime_clock['effective_from_decision'] < 0
                or runtime_clock.get('clock') != {'target_seconds': 10, 'long_seconds': 10, 'uses_per_seat': 0}):
            raise ValueError('Unsupported runtime clock amendment')
        session = Session(args.session, config, Environment, teacher_factory(config, runtime_clock))
        session.runtime_clock = runtime_clock
        server = ThreadingHTTPServer(('127.0.0.1', args.port),
            handler(session, secrets.token_urlsafe(32), args.ui_port, args.port))
        session.start_recommendation()
        print(f'Coaching ready: http://localhost:{args.ui_port}/?aiCoach=1', flush=True)
        try:
            server.serve_forever()
        finally:
            server.server_close()


if __name__ == '__main__':
    main()
