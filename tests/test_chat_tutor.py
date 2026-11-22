import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from diagnostic import engine as e,book_chat as chat,chat_tutor as tutor
from diagnostic.tutor_bank import load as load_tutor_bank


class ChatTutorTests(unittest.TestCase):
    def test_composer_question_during_practice_is_not_scored(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn=e.connect(Path(tmp)/'chat.db');chat.ensure(conn)
            nodes,_=e.load_graph();q=tutor.practice('MATH6_C0025',nodes)
            tutor.save(conn,'thread',{'target':'MATH6_C0025','original':'acute angles','learner':'a','phase':'practice','practice':q})
            with patch('diagnostic.chat_router.plan',return_value={'action':'explain','concept_id':'MATH6_C0025'}),patch.object(chat,'answer',return_value={'status':'answered','paragraphs':[]}) as explanation:
                tutor.handle(conn,'a','thread','__chat_query__:Please show another example','en')
                self.assertEqual(explanation.call_args.kwargs['teaching_request']['mode'],'another_example')
                self.assertEqual(explanation.call_args.args[2],'MATH6_C0025')
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM book_chat_practice').fetchone()[0],0)
            conn.close()

    def test_patterns_assess_foundations_and_leave_target_unassessed(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(chat,'generate',side_effect=RuntimeError('offline')):
            conn=e.connect(Path(tmp)/'chat.db')
            start=chat.send(conn,'a','I find patterns difficult to follow','en')
            out=start['message'];seen=[]
            while out.get('check_question'):
                public=out['check_question']
                seen.append(public['concept_id'])
                self.assertNotEqual(public['concept_id'],'MATH6_C0003')
                q=next(q for q in load_tutor_bank() if q['id']==public['id'])
                wrong=('B' if q['answer']=='A' else 'A') if q['type']=='mcq' else str(float(q['answer'])+1)
                out=chat.send(conn,'a',wrong,'en',start['thread_id'])['message']
            self.assertEqual(len(seen),3)
            target=next(c for c in out['tutor_summary']['concepts'] if c['concept_id']=='MATH6_C0003')
            self.assertEqual(target['status'],'Unassessed')
            self.assertTrue(any(c['status']=='Possible prerequisite difficulty' for c in out['tutor_summary']['concepts']))
            self.assertIn('practice_question',out);self.assertEqual(e.history(conn,'a'),[]);conn.close()

    def setUp(self):
        p=patch('diagnostic.chat_router.gemini_generate',side_effect=RuntimeError('offline test'))
        p.start();self.addCleanup(p.stop)
    def test_confused_about_two_related_angle_types_starts_with_a_question(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn=e.connect(Path(tmp)/'chat.db')
            with patch.object(chat,'generate') as generation:
                result=chat.send(conn,'a','I am confused about acute and right angles','en')['message']
                generation.assert_not_called()
            self.assertEqual(result['mode'],'learning_check')
            self.assertEqual(result['concept']['id'],'MATH6_C0025')
            self.assertIn(result['check_question']['concept_id'],['MATH6_C0020','MATH6_C0024'])
            self.assertTrue(result['check_question']['text'])
            conn.close()

    def test_check_explain_practice_is_persisted_and_separate_from_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(chat,'generate',side_effect=RuntimeError('offline')):
            path=Path(tmp)/'chat.db';conn=e.connect(path)
            start=chat.send(conn,'alice','I am struggling with acute angles. Help me practise.','en')
            thread=start['thread_id'];output=start['message'];seen=[]
            self.assertEqual(tutor.history(conn,'alice'),[])
            while output.get('check_question'):
                public=output['check_question']
                self.assertNotIn('answer',public)
                self.assertNotIn(public['id'],seen);seen.append(public['id'])
                q=next(q for q in e.load_bank() if q['id']==public['id'])
                response=q['answer'] if len(seen)==1 else ('1' if q['type']=='numeric' else next(c for c in 'ABCD' if c!=q['answer']))
                output=chat.send(conn,'alice',response,'en',thread)['message']
            self.assertLessEqual(len(seen),3);self.assertEqual(output['tutor_stage'],'explanation')
            self.assertIn('practice_question',output);self.assertNotIn('answer',output['practice_question'])
            self.assertEqual(e.history(conn,'alice'),[])
            self.assertEqual(len(tutor.history(conn,'alice')),len(seen));self.assertEqual(tutor.history(conn,'bob'),[])
            state=json.loads(conn.execute('SELECT payload FROM book_chat_tutoring WHERE thread_id=?',(thread,)).fetchone()[0])
            answer=state['practice']['answer']
            feedback=chat.send(conn,'alice',answer,'en',thread)['message']
            self.assertEqual(feedback['practice_score'],1)
            self.assertEqual(len(tutor.history(conn,'alice')),len(seen));self.assertEqual(e.history(conn,'alice'),[])
            conn.close();conn=e.connect(path)
            self.assertTrue(chat.messages(conn,'alice',thread))
            with self.assertRaises(LookupError):chat.send(conn,'bob','2','en',thread)
            conn.close()

    def test_skip_and_hindi_and_exact_practice_keys(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(chat,'generate',side_effect=RuntimeError('offline')):
            conn=e.connect(Path(tmp)/'chat.db')
            start=chat.send(conn,'a','न्यून कोण समझ नहीं आता। अभ्यास कराइए।','hi')
            self.assertEqual(start['message']['mode'],'learning_check')
            result=start['message']
            while result.get('check_question'):
                result=chat.send(conn,'a','not sure','hi',start['thread_id'])['message']
            self.assertEqual(result['tutor_summary']['questions_asked'],3)
            self.assertTrue(all(c['status'] in ('Unassessed','Insufficient evidence') for c in result['tutor_summary']['concepts']))
            self.assertNotIn('answer',result['practice_question']);self.assertEqual(e.history(conn,'a'),[])
            conn.close()
        nodes,_=e.load_graph()
        for cid in {q['concept_id'] for q in e.load_bank()}:
            for _ in range(4):
                q=tutor.practice(cid,nodes)
                self.assertIsNotNone(q);self.assertEqual(e.score(q,q['answer']),1)


if __name__=='__main__':unittest.main()

