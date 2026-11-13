import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch
from http.server import ThreadingHTTPServer
import server
from diagnostic import engine as e


class LearnerAPIFlowTests(unittest.TestCase):
    def setUp(self):
        p=patch('diagnostic.chat_router.gemini_generate',side_effect=RuntimeError('offline test'))
        p.start();self.addCleanup(p.stop)
    def test_guided_check_save_resume_and_coverage(self):
        original = e.connect
        with tempfile.TemporaryDirectory() as tmp:
            with patch('diagnostic.engine.connect', side_effect=lambda: original(Path(tmp)/'history.sqlite3')):
                http = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
                thread = threading.Thread(target=http.serve_forever, daemon=True)
                thread.start()
                base = f'http://127.0.0.1:{http.server_port}/api'
                def call(path, body=None):
                    req = Request(base+path, data=json.dumps(body).encode() if body is not None else None,
                                  headers={'Content-Type':'application/json'})
                    with urlopen(req, timeout=60) as response:
                        return json.load(response)
                try:
                    mapping = call('/map', {'question':'Help me with place value'})
                    self.assertEqual(mapping['concept_id'], 'MATH6_C0038')
                    self.assertTrue(mapping['details']['concept']['textbook']['location_verified'])
                    self.assertEqual(call('/concepts/MATH6_C0038')['concept']['en'],'place value')
                    self.assertEqual(call('/map',{'question':'unknown topic abc'})['status'],'clarify')
                    state = call('/sessions', {'learner':'browser-test','target':mapping['concept_id']})
                    sid = state['id']
                    for answer in ('400', '७००'):
                        question = state['question']
                        self.assertNotIn('answer', question)
                        state = call(f'/sessions/{sid}/answer', {'learner':'browser-test','question_id':question['id'],'response':answer})
                    self.assertIsNone(state['question'])
                    self.assertEqual(state['report']['question_count'],2)
                    self.assertEqual(state['report']['selection_method'],'graph-guided')
                    self.assertEqual(next(c for c in state['report']['concepts'] if c['role']=='target')['status_code'],1)
                    self.assertIn('study_plan',state['report'])
                    self.assertTrue(state['report']['study_plan'])
                    self.assertEqual(call(f'/sessions/{sid}?learner=browser-test')['report'],state['report'])
                    self.assertEqual(call('/sessions?learner=browser-test')['response_count'],2)
                    progress=call('/progress?learner=browser-test')
                    self.assertEqual(progress['completed_checks'],1)
                    self.assertEqual(progress['total_answers'],2)
                    self.assertTrue(progress['sessions'][0]['target_assessed'])
                    with self.assertRaises(HTTPError) as caught:
                        call('/sessions',{'learner':'browser-test','target':'MATH6_C0036'})
                    self.assertEqual(caught.exception.code,400)
                    with urlopen(base+'/textbooks/en/fegp102.pdf') as pdf:
                        self.assertEqual(pdf.headers['Content-Type'],'application/pdf')
                        self.assertTrue(pdf.read(5).startswith(b'%PDF-'))
                    with self.assertRaises(HTTPError):
                        call('/textbooks/en/unknown.pdf')
                    other=call('/sessions',{'learner':'another-learner','target':'MATH6_C0038'})
                    with patch('diagnostic.book_chat.generate',side_effect=RuntimeError('offline')):
                        chat=call('/chat/message',{'learner':'browser-test','message':'Explain place value','language':'en','concept_id':'MATH6_C0038'})
                        other_chat=call('/chat/message',{'learner':'another-learner','message':'Explain place value','language':'hi','concept_id':'MATH6_C0038'})
                    self.assertEqual(chat['message']['mode'],'extractive')
                    self.assertEqual(len(call('/chat/threads?learner=browser-test')['threads']),1)
                    self.assertEqual(len(call('/chat/threads/'+chat['thread_id']+'?learner=browser-test')['messages']),2)
                    with self.assertRaises(HTTPError) as denied:
                        call('/chat/threads/'+chat['thread_id']+'?learner=another-learner')
                    self.assertEqual(denied.exception.code,404)
                    self.assertTrue(call('/reset',{'learner':'browser-test'})['cleared'])
                    self.assertEqual(call('/chat/threads?learner=browser-test')['threads'],[])
                    self.assertEqual(len(call('/chat/threads?learner=another-learner')['threads']),1)
                    cleared=call('/sessions?learner=browser-test')
                    self.assertEqual(cleared['sessions'],[])
                    self.assertEqual(cleared['response_count'],0)
                    self.assertEqual(call('/progress?learner=browser-test')['total_answers'],0)
                    self.assertEqual(len(call('/sessions?learner=another-learner')['sessions']),1)
                    fresh=call('/sessions',{'learner':'browser-test','target':'MATH6_C0038'})
                    self.assertEqual(fresh['question']['id'],'DQ_0038_1')
                    self.assertEqual(fresh['history_count'],0)
                finally:
                    http.shutdown();http.server_close();thread.join()


if __name__ == '__main__':
    unittest.main()
