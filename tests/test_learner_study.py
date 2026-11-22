from tests.legacy_curriculum import frozen_v1
import tempfile
import unittest
import threading
import json
from pathlib import Path
from unittest.mock import patch
from diagnostic import engine as e,learner_study as study
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen
from server import Handler


class LearnerStudyTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(frozen_v1())

    def test_study_http_flow_and_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            original=e.connect
            with patch('diagnostic.engine.connect',side_effect=lambda:original(Path(tmp)/'api.sqlite3')):
                http=ThreadingHTTPServer(('127.0.0.1',0),Handler)
                thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
                def call(path,body=None):
                    req=Request(f'http://127.0.0.1:{http.server_port}/api'+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
                    with urlopen(req,timeout=10) as response:return json.load(response)
                try:
                    self.assertEqual(call('/study/export')['record_count'],0)
                    initial=call('/study/start',{'participant_code':'fixture-test','target':'MATH6_C0038','consent':True})
                    state=initial['session'];learner=initial['learner']
                    state=call(f'/sessions/{state["id"]}/answer',{'learner':learner,'question_id':state['question']['id'],'response':'400'})
                    state=call(f'/sessions/{state["id"]}/finish',{'learner':learner})
                    self.assertIsNotNone(state['report'])
                    self.assertEqual(call('/study/export')['records'][0]['questions_asked'],1)
                finally:http.shutdown();http.server_close();thread.join()
    def test_allocation_resume_budget_and_no_automatic_gold_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn=e.connect(Path(tmp)/'study.sqlite3')
            try:
                self.assertEqual(study.export(conn)['record_count'],0)
                with self.assertRaises(ValueError):study.enrol(conn,'person-1','MATH6_C0038',False)
                for method in ('fixed','graph-guided'):
                    with patch('diagnostic.learner_study.secrets.choice',return_value=method):
                        sid,learner=study.enrol(conn,'participant-'+method,'MATH6_C0038',True)
                    self.assertEqual(study.enrol(conn,'participant-'+method,'MATH6_C0025',True)[0],sid)
                    self.assertEqual(e.history(conn,learner),[])
                    current=[];bank=e.load_bank();_,edges=e.load_graph()
                    while (question:=e.select_question('MATH6_C0038',bank,edges,current,method=method)) is not None:
                        current.append(e.save_response(conn,sid,question,question['answer']))
                    self.assertLessEqual(len(current),3)
                    report=e.make_report('MATH6_C0038',bank,edges,current)
                    with conn:conn.execute('UPDATE sessions SET report=? WHERE id=?',(__import__('json').dumps(report),sid))
                export=study.export(conn)
                self.assertEqual(export['record_count'],2)
                self.assertTrue(all(r['independent_expected_statuses']=={} for r in export['records']))
                self.assertTrue(all(r['questions_asked']<=3 for r in export['records']))
                self.assertTrue(all(v['reviewed_cases']==0 for v in study.analyse(export)['results'].values()))
                for row in export['records']:
                    row.update(reviewer='independent-test-reviewer',review_status='APPROVED',independent_expected_statuses={'MATH6_C0038':'Evidence supports understanding'})
                analysis=study.analyse(export)
                self.assertTrue(all(v['correct_diagnoses']==1 for v in analysis['results'].values()))
                self.assertFalse(analysis['educational_usefulness_established'])
            finally:conn.close()


if __name__=='__main__':unittest.main()
