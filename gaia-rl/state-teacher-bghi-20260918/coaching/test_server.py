import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer

from coaching.server import handler
from coaching.session import Session
from coaching.test_session import SEED, Teacher
from gaia_rl import Environment


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.session = Session(Path(self.tmp.name)/'game', {'seed': SEED}, Environment, Teacher)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), handler(self.session, 'secret', 5174, 8789))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.session.start_recommendation()
        self.session.worker.join(10)

    def tearDown(self):
        if self.session.worker:
            self.session.worker.join(10)
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(10)
        self.tmp.cleanup()

    def request(self, method, path, data=None, **headers):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        default = {'Host': 'localhost:5174', 'Content-Type': 'application/json', 'X-Coach-Token': 'secret'}
        conn.request(method, path, json.dumps(data) if data is not None else None, {**default, **headers})
        response = conn.getresponse()
        status, value = response.status, json.loads(response.read())
        conn.close()
        return status, value

    def test_get_never_advances_and_export_is_not_training(self):
        for _ in range(3):
            code, state = self.request('GET', '/coach-api/state')
            self.assertEqual(code, 200)
            self.assertEqual(state['snapshot']['steps'], 0)
        code, record = self.request('GET', '/coach-api/record')
        self.assertEqual(code, 200)
        self.assertFalse(record['complete'])
        self.assertFalse(record['training_performed'])
        self.assertEqual(record['decisions'], [])

    def test_approval_once_with_token_origin_and_decision_checks(self):
        decision = self.session.current['decision_id']
        body = {'decision_id': decision, 'index': 0}
        for headers in [{'X-Coach-Token': ''}, {'Origin': 'https://foreign.example'}, {'Host': 'foreign.example'}]:
            self.assertEqual(self.request('POST', '/coach-api/approve', body, **headers)[0], 403)
        self.assertEqual(self.session.current['steps'], 0)
        self.assertEqual(self.request('POST', '/coach-api/approve', body)[0], 200)
        self.assertEqual(self.request('POST', '/coach-api/approve', body)[0], 409)
        self.assertEqual(self.session.current['steps'], 1)
        self.assertEqual(len(self.session.history), 1)

    def test_malformed_or_unexplained_override_is_rejected(self):
        body = {'decision_id': self.session.current['decision_id'], 'index': 1}
        self.assertEqual(self.request('POST', '/coach-api/approve', body)[0], 400)
        self.assertEqual(self.request('POST', '/coach-api/approve', [1])[0], 400)
        self.assertEqual(self.session.current['steps'], 0)

    def test_technology_confirmation_is_required_and_forwarded(self):
        body = {'decision_id': self.session.current['decision_id'], 'index': 0}
        with patch('coaching.session.technology_choice', return_value=True):
            self.assertEqual(self.request('POST', '/coach-api/approve', body)[0], 400)
            self.assertEqual(self.session.current['steps'], 0)
            self.assertEqual(self.request('POST', '/coach-api/approve',
                {**body, 'technology_confirmed': True})[0], 200)
        self.assertTrue(self.session.history[-1]['technology_confirmed'])


if __name__ == '__main__':
    unittest.main()
