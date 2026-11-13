import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from diagnostic import engine as e,practice


class TopicPracticeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'practice.db';self.conn=e.connect(self.path)
    def tearDown(self):self.conn.close();self.tmp.cleanup()

    def test_save_resume_scoring_and_learner_isolation(self):
        session=practice.create(self.conn,'a','MATH6_C0025','en');sid=session['id']
        self.assertNotIn('answer',session['question']);self.assertEqual(session['answered'],0)
        self.assertEqual(practice.analytics(self.conn,'b')['attempts'],[])
        with self.assertRaises(LookupError):practice.view(self.conn,'b',sid)
        with self.assertRaises(LookupError):practice.respond(self.conn,'b',sid,0,'A')
        first=True
        while session['question']:
            q=session['question'];raw=json.loads(self.conn.execute('SELECT payload FROM practice_items WHERE session_id=? AND ordinal=?',(sid,q['ordinal'])).fetchone()[0])
            session=practice.respond(self.conn,'a',sid,q['ordinal'],raw['answer'])
            self.assertEqual(session['history'][-1]['score'],1)
            if first:
                with self.assertRaises(ValueError):practice.respond(self.conn,'a',sid,q['ordinal'],raw['answer'])
                first=False
        self.assertTrue(session['completed']);self.assertEqual(session['correct'],session['total'])
        self.assertEqual(e.history(self.conn,'a'),[])
        summary=practice.analytics(self.conn,'a');self.assertEqual(summary['completed_sessions'],1)
        self.assertEqual(summary['topics'][0]['accuracy'],100.)
        self.conn.close();self.conn=e.connect(self.path)
        self.assertTrue(practice.view(self.conn,'a',sid)['completed'])

    def test_hindi_unscorable_and_language_analytics(self):
        session=practice.create(self.conn,'a','MATH6_C0038','hi')
        self.assertEqual(session['language'],'hi')
        q=session['question'];raw=json.loads(self.conn.execute('SELECT payload FROM practice_items WHERE session_id=? AND ordinal=?',(session['id'],q['ordinal'])).fetchone()[0])
        devanagari=raw['answer'].translate(str.maketrans('0123456789','०१२३४५६७८९'))
        session=practice.respond(self.conn,'a',session['id'],q['ordinal'],devanagari)
        self.assertEqual(session['correct'],1)
        if session['question']:session=practice.respond(self.conn,'a',session['id'],session['question']['ordinal'],'not sure')
        self.assertIsNone(session['history'][-1]['score'])
        practice.create(self.conn,'a','MATH6_C0025','en')
        stats=practice.analytics(self.conn,'a')
        self.assertEqual(stats['languages']['hi']['accuracy'],100.)
        self.assertIsNone(stats['languages']['en']['accuracy'])

    def test_invalid_topic_and_generated_question_source_checks(self):
        with self.assertRaises(ValueError):practice.create(self.conn,'a','not-a-concept','en')
        nodes,_=e.load_graph()
        source={'id':'S1','excerpt':'Parallel lines are lines in a plane that do not meet.','url':'/book','chapter_title':'Geometry','printed_page':3,'concept_id':'MATH6_C0032'}
        draft={'items':[{'text':'Which lines never meet?','options':['Parallel','Intersecting','Perpendicular','Rays'],'answer':'A','explanation':'Parallel lines in a plane never meet.','source_id':'FAKE','evidence':source['excerpt']}]}
        with patch.object(practice.book_chat,'retrieve_sources',return_value=([source],[])),patch.object(practice,'configuration',return_value={'GEMINI_API_KEY':'test'}),patch.object(practice,'gemini_generate',return_value=draft):
            with self.assertRaises(ValueError):practice.generated_items('MATH6_C0032','en',nodes,5)


if __name__=='__main__':unittest.main()
