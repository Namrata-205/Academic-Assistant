import csv
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from diagnostic import engine as e, imported_reports as ir
from server import session_view
from server import Handler
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen
from urllib.error import HTTPError


class ImportedReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.store=self.root/'imports.sqlite3'
        self.students=self.root/'student_report.csv'
        self.gaps=self.root/'student_gap_report.csv'
        self.write(self.students,[{'student_id':'s1','answered':'12','correct':'7','recommended_revision':'Place Value | Fractions','strong_topics':'Squares, Cubes, etc'},
                                  {'student_id':'s2','answered':'0','correct':'0','recommended_revision':'','strong_topics':''}])
        self.write(self.gaps,[{'student_id':'s1','gap_topic':'Place Value','status':'confirmed','diagnostic_mode':'retrospective_replay','prerequisite_attempts':'0','prerequisite_accuracy':'','diagnostic_items':'0'},
                              {'student_id':'s1','gap_topic':'Fractions','status':'pending','diagnostic_mode':'retrospective_replay','prerequisite_attempts':'3','prerequisite_accuracy':'0.3','diagnostic_items':'0'}])
        ir.import_files(self.students,self.gaps,self.store)
    def tearDown(self):
        self.tmp.cleanup()
    @staticmethod
    def write(path,rows):
        with path.open('w',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    def test_exact_mapping_and_no_fabricated_observations(self):
        profile=ir.get_profile('s1',self.store)
        nodes,edges=e.load_graph()
        context=ir.context_for_target(profile,'MATH6_C0038',nodes,edges)
        self.assertEqual(len(context['items']),1)
        self.assertEqual(context['items'][0]['source_status'],'confirmed')
        self.assertEqual(context['items'][0]['mapping'],'exact')
        self.assertEqual(context['items'][0]['diagnostic_items'],'0')
        self.assertEqual(context['unmapped_topic_count'],1)
        report=e.make_report('MATH6_C0038',e.load_bank(),edges,[])
        report['external_context']=context
        self.assertTrue(all(c['assessment']=='Unassessed' for c in report['concepts']))
        self.assertNotIn('score',context['items'][0])
    def test_learner_lookup_is_exact_and_unrelated_context_is_excluded(self):
        self.assertEqual(ir.get_profile('s2',self.store)['gaps'],[])
        with self.assertRaises(LookupError):ir.get_profile('s',self.store)
        nodes,edges=e.load_graph()
        self.assertEqual(ir.context_for_target(ir.get_profile('s1',self.store),'MATH6_C0018',nodes,edges)['items'],[])
    def test_profile_listing_search_and_gap_filter(self):
        listing=ir.list_profiles(db_path=self.store)
        self.assertEqual(listing['total'],2)
        self.assertEqual([s['student_id'] for s in listing['students']],['s1','s2'])
        self.assertEqual(ir.list_profiles('s2',db_path=self.store)['students'][0]['gap_count'],0)
        filtered=ir.list_profiles(gaps_only=True,db_path=self.store)
        self.assertEqual([s['student_id'] for s in filtered['students']],['s1'])
        self.assertEqual(ir.list_profiles('%',db_path=self.store)['total'],0)
        self.assertEqual(ir.list_profiles(page=999,db_path=self.store)['page'],1)
        self.assertNotIn('payload',listing['students'][0])
        alias=ir.display_name('s1')
        self.assertEqual(ir.list_profiles(alias,db_path=self.store)['students'][0]['student_id'],'s1')
    def test_profile_snapshot_preserves_source_trends_and_missing_scores(self):
        profile=ir.get_profile('s1',self.store)
        profile['student'].update({'strong_subjects':'Number | Algebra','weak_subjects':'Geometry',
                                  'number_percentage':'72.5','number_trend':'improving',
                                  'algebra_percentage':'','algebra_trend':'insufficient data'})
        summary=ir.profile_summary(profile)
        self.assertEqual(summary['strong_subjects'],['Number','Algebra'])
        self.assertEqual(summary['weak_subjects'],['Geometry'])
        self.assertEqual(summary['subjects'][0]['trend'],'improving')
        self.assertEqual(summary['subjects'][0]['percentage'],72.5)
        self.assertIsNone(summary['subjects'][1]['percentage'])
        self.assertIn('nickname',summary['name_note'])
    def test_student_space_is_persisted_and_recovers_existing_history(self):
        with patch.object(ir,'STORE',self.store):
            path=self.root/'spaces.sqlite3';conn=e.connect(path)
            with conn:conn.execute('INSERT INTO external_profile_links VALUES (?,?)',('old-browser','s1'))
            e.new_session(conn,'old-browser','MATH6_C0038','graph-guided',[])
            space=ir.select_learning_space(conn,'s1')
            self.assertEqual(space['learner'],'old-browser')
            conn.close();conn=e.connect(path)
            try:
                self.assertEqual(ir.select_learning_space(conn,'s1')['learner'],'old-browser')
                self.assertNotEqual(ir.select_learning_space(conn,'s2')['learner'],'old-browser')
                self.assertEqual(conn.execute('SELECT count(*) FROM sessions WHERE learner=?',('old-browser',)).fetchone()[0],1)
            finally:conn.close()
    def test_aggregate_source_does_not_change_question_selection(self):
        nodes,edges=e.load_graph();bank=e.load_bank()
        conn=e.connect(self.root/'history.sqlite3')
        try:
            with patch.object(ir,'STORE',self.store):
                with conn:conn.execute('INSERT INTO external_profile_links VALUES (?,?)',('local','s1'))
                context=ir.linked_context(conn,'local','MATH6_C0038',nodes,edges)
                sid=e.new_session(conn,'local','MATH6_C0038','graph-guided',[])
                with conn:conn.execute('INSERT INTO session_external_context VALUES (?,?)',(sid,json.dumps(context)))
                view=session_view(conn,sid,'local')
                self.assertEqual(view['question']['id'],e.select_question('MATH6_C0038',bank,edges,[])['id'])
                self.assertEqual(e.history(conn,'local'),[])
                with conn:conn.execute('DELETE FROM external_profile_links WHERE learner=?',('local',))
                self.assertEqual(session_view(conn,sid,'local')['external_context'],context)
                self.assertIsNone(ir.linked_context(conn,'local','MATH6_C0038',nodes,edges))
        finally:conn.close()
    def test_reimport_is_idempotent_and_orphans_are_rejected(self):
        ir.import_files(self.students,self.gaps,self.store)
        self.assertEqual(len(ir.get_profile('s1',self.store)['gaps']),2)
        self.write(self.gaps,[{'student_id':'missing','gap_topic':'x','status':'pending','diagnostic_mode':'retrospective_replay'}])
        with self.assertRaises(ValueError):ir.import_files(self.students,self.gaps,self.store)
        self.assertEqual(len(ir.get_profile('s1',self.store)['gaps']),2)

    def test_profile_api_links_only_the_requested_learner(self):
        original_connect=e.connect
        with patch.object(ir,'STORE',self.store), patch('diagnostic.engine.connect',side_effect=lambda:original_connect(self.root/'api-history.sqlite3')):
            legacy_handler=type('LegacyProfileHandler',(Handler,),{'allow_legacy_profiles':True})
            http=ThreadingHTTPServer(('127.0.0.1',0),legacy_handler)
            thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
            def call(path,body=None):
                req=Request(f'http://127.0.0.1:{http.server_port}/api'+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
                with urlopen(req,timeout=10) as response:return json.load(response)
            try:
                self.assertEqual(call('/profiles?gaps_only=true')['total'],1)
                self.assertEqual(call('/profiles?search=s2')['students'][0]['student_id'],'s2')
                self.assertIsNone(call('/profile?learner=local')['profile'])
                with self.assertRaises(HTTPError):call('/profile/link',{'learner':'local','student_id':'missing'})
                linked=call('/profile/link',{'learner':'local','student_id':'s1'})
                self.assertEqual(linked['profile']['student_id'],'s1')
                self.assertIsNone(call('/profile?learner=other')['profile'])
                state=call('/sessions',{'learner':'local','target':'MATH6_C0038'})
                self.assertEqual(state['external_context']['items'][0]['source_status'],'confirmed')
                sid=state['id']
                count=0
                while state['question']:
                    state=call(f'/sessions/{sid}/answer',{'learner':'local','question_id':state['question']['id'],'response':'not sure'})
                    count+=1;self.assertLessEqual(count,3)
                self.assertEqual(state['report']['question_count'],count)
                self.assertEqual(state['report']['external_context']['student_id'],'s1')
                call('/profile/unlink',{'learner':'local'})
                self.assertIsNone(call('/profile?learner=local')['profile'])
                self.assertIsNotNone(call(f'/sessions/{sid}?learner=local')['external_context'])
            finally:http.shutdown();http.server_close();thread.join()


if __name__=='__main__':
    unittest.main()
