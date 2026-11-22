import http.cookiejar
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener
from unittest.mock import patch

from diagnostic import engine
from server import Handler, LocalHTTPServer


class AccountAPITests(unittest.TestCase):
    def test_signup_login_and_practice_are_account_scoped(self):
        original_connect = engine.connect
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / 'history.sqlite3'
            with patch.object(engine, 'connect', side_effect=lambda: original_connect(db)):
                server = LocalHTTPServer(('127.0.0.1', 0), Handler)
                worker = threading.Thread(target=server.serve_forever, daemon=True)
                worker.start()
                try:
                    self.check_account_api(server.server_port)
                finally:
                    server.shutdown()
                    server.server_close()
                    worker.join()

    def check_account_api(self, port):
        def client():
            return build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))

        def call(browser, path, data=None):
            request = Request(f'http://127.0.0.1:{port}/api' + path,
                              data=json.dumps(data).encode() if data is not None else None,
                              headers={'Content-Type': 'application/json'})
            with browser.open(request, timeout=15) as response:
                return json.load(response)

        owner, other = client(), client()
        credentials = {'email': 'alice@example.test', 'password': 'a-long-test-password', 'name': 'Alice'}
        account = call(owner, '/auth/signup', credentials)['account']
        learner = account['learner']
        self.assertEqual(call(owner, '/auth/session')['account'], account)
        session = call(owner, '/practice/sessions', {'learner': learner, 'concept_id': 'MATH6_C0025'})
        path = '/practice/sessions/' + session['id'] + '?learner=' + learner
        self.assertEqual(call(owner, path)['id'], session['id'])

        call(other, '/auth/signup', dict(credentials, email='another@example.test'))
        for endpoint in ('/revision', '/exams'):
            account_path = endpoint + '?learner=' + learner
            self.assertIsInstance(call(owner, account_path), dict)
            with self.assertRaises(HTTPError) as error:
                call(other, account_path)
            self.assertEqual(error.exception.code, 403)
        with self.assertRaises(HTTPError) as error:
            call(other, path)
        self.assertEqual(error.exception.code, 403)

        call(owner, '/auth/logout', {})
        self.assertIsNone(call(owner, '/auth/session')['account'])
        with self.assertRaises(HTTPError) as error:
            call(owner, path)
        self.assertEqual(error.exception.code, 403)
        self.assertEqual(call(owner, '/auth/login', credentials)['account'], account)
        self.assertEqual(call(owner, path)['id'], session['id'])


if __name__ == '__main__':
    unittest.main()
