import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from diagnostic import engine as e,book_chat as chat,chat_tutor as tutor
from diagnostic.tutor_bank import load
from diagnostic.tutor_selection import choose,prerequisite_rank_audit
from diagnostic.teaching_feedback import public_teaching_request,contrast_explanation
from diagnostic.bilingual_quality import check_pair,check_arithmetic,check_angle_claims,glossary


class SelectionTests(unittest.TestCase):
    def test_confirmation_changes_next_item_and_records_candidate_reason(self):
        bank=[{'id':f'{cid}-{i}','concept_id':cid} for cid in ('foundation','other') for i in (1,2)]
        edges=[{'source_id':cid,'target_id':'topic','confidence':confidence} for cid,confidence in [('foundation',.8),('other',.9)]]
        q,audit=choose('topic',bank,edges)
        self.assertEqual(q['concept_id'],'other')
        current=[{'question_id':'foundation-1','concept_id':'foundation','score':0}]
        q,audit=choose('topic',bank,edges,current)
        self.assertEqual(q['id'],'foundation-2')
        self.assertEqual(audit['reason'],'confirm_unclear_or_single_observation')
        self.assertNotIn('answer',json.dumps(audit))
        current.append({'question_id':'foundation-2','concept_id':'foundation','score':0})
        self.assertEqual(choose('topic',bank,edges,current)[0]['concept_id'],'other')
        current.append({'question_id':'other-1','concept_id':'other','score':1})
        self.assertIsNone(choose('topic',bank,edges,current)[0])

    def test_unclear_response_confirms_and_no_history_item_is_reused(self):
        nodes,edges=e.load_graph();bank=load();target='MATH6_C0025'
        first,_=choose(target,bank,edges)
        current=[{'question_id':first['id'],'concept_id':first['concept_id'],'score':None}]
        second,audit=choose(target,bank,edges,current)
        self.assertEqual(second['concept_id'],first['concept_id'])
        self.assertNotEqual(second['id'],first['id'])
        self.assertTrue(audit['candidates'][0]['needs_confirmation'])

    def test_prerequisite_audit_reports_missing_graph_and_missing_items(self):
        row=prerequisite_rank_audit('target',['absent'],[],[])
        self.assertEqual(row['recall_at_3'],0.)
        self.assertEqual(row['not_in_graph'],['absent'])
        self.assertEqual(row['without_bank_items'],['absent'])


class BilingualTests(unittest.TestCase):
    def test_glossary_ids_and_paired_numbers_units(self):
        nodes,_=e.load_graph()
        for cid,row in glossary()['concepts'].items():
            self.assertIn(cid,nodes)
            self.assertTrue(check_pair(row['definition_en'],row['definition_hi'])['passed'],cid)
            check_arithmetic(row['definition_en']);check_arithmetic(row['definition_hi'])
        self.assertTrue(check_pair('90 degrees','९० अंश')['passed'])
        self.assertFalse(check_pair('90 degrees','180 अंश')['passed'])
        self.assertFalse(check_pair('90 degrees','90 सेमी')['passed'])

    def test_numeric_and_angle_guardrails(self):
        for text in ['१२ ÷ ३ = ५','90 + 90 = 90','4 × 4 = 12']:
            with self.assertRaises(ValueError):check_arithmetic(text)
        check_arithmetic('१२ ÷ ३ = ४')
        check_arithmetic('3 + 5 + 2 = 10')
        for text in ['A right angle measures 180 degrees.','समकोण का माप 180 अंश है।']:
            with self.assertRaises(ValueError):check_angle_claims(text)
        check_angle_claims('A straight angle measures 180 degrees.')

    def test_related_activity_is_not_presented_as_a_direct_explanation(self):
        with patch.object(chat,'generate') as generation:
            result=chat.answer('Explain place value','en','MATH6_C0038')
        self.assertEqual(result['status'],'insufficient_sources')
        self.assertIn('related',result['message'])
        self.assertEqual(result['paragraphs'],[])
        generation.assert_not_called()

    def test_cloud_teaching_request_drops_private_fields(self):
        request=public_teaching_request({'mode':'still_confused','focus_concept_id':'MATH6_C0024',
                                        'private_history':'SECRET','response':'wrong','learner':'alice'})
        self.assertEqual(request['focus']['id'],'MATH6_C0024')
        self.assertNotIn('SECRET',json.dumps(request));self.assertNotIn('alice',json.dumps(request))

    def test_contrast_fails_without_support_and_translations_preserve_values(self):
        with patch.object(chat,'retrieve_sources',return_value=([],[])):
            self.assertIsNone(contrast_explanation('en'))
        en=contrast_explanation('en');hi=contrast_explanation('hi')
        self.assertIsNotNone(en);self.assertIsNotNone(hi)
        self.assertTrue(check_pair(' '.join(p['text'] for p in en['paragraphs']),
                                   ' '.join(p['text'] for p in hi['paragraphs']))['passed'])
        for result in (en,hi):
            self.assertEqual(len(chat.validate_generation({'paragraphs':result['paragraphs']},result['sources'],result['language'])),2)


class TutoringCycleTests(unittest.TestCase):
    def test_right_straight_check_explain_rotated_transfer_and_feedback_both_languages(self):
        for language,text in [('en','I confuse a right angle with a straight angle.'),('hi','मुझे समकोण और सरल कोण में भ्रम होता है।')]:
            with self.subTest(language=language),tempfile.TemporaryDirectory() as tmp,patch('diagnostic.chat_router.gemini_generate',side_effect=RuntimeError('offline')),patch.object(chat,'generate',side_effect=RuntimeError('offline')):
                conn=e.connect(Path(tmp)/'cycle.db')
                start=chat.send(conn,'alice',text,language);thread=start['thread_id'];out=start['message']
                seen=[]
                while out.get('check_question'):
                    public=out['check_question'];seen.append(public['id'])
                    self.assertNotIn('answer',public)
                    self.assertNotIn('check_questions',out)
                    q=next(q for q in load() if q['id']==public['id'])
                    # Repeatedly confuse the two angle types.
                    wrong='B' if q['answer']=='A' else 'A'
                    out=chat.send(conn,'alice',wrong,language,thread)['message']
                self.assertEqual(len(seen),2)
                self.assertEqual(out['mode'],'source_backed_template')
                self.assertEqual(out['practice_question']['diagram']['rotation'],55)
                self.assertEqual(out['tutor_summary']['questions_asked'],2)
                self.assertTrue(any(c['status']=='Possible prerequisite difficulty' for c in out['tutor_summary']['concepts']))
                answer=chat.send(conn,'alice','A',language,thread)['message']
                self.assertEqual(answer['practice_score'],1)
                self.assertEqual(len(tutor.followup_evidence(conn,'alice')),1)
                self.assertEqual(tutor.followup_evidence(conn,'bob'),[])
                self.assertEqual(e.history(conn,'alice'),[])
                for action in ('simpler','another_example','still_confused','language_help'):
                    out=chat.send(conn,'alice','__feedback__:'+action,language,thread)['message']
                    self.assertEqual(out['feedback_action'],action)
                    if action=='another_example':
                        self.assertIn('practice_question',out)
                        self.assertNotEqual(out['practice_question']['diagram']['rotation'],55)
                    else:
                        self.assertNotIn('practice_question',out)
                self.assertEqual(len(tutor.history(conn,'alice')),2)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM book_chat_tutor_events WHERE kind='feedback'").fetchone()[0],4)
                with self.assertRaises(LookupError):chat.send(conn,'bob','__feedback__:simpler',language,thread)
                conn.close()

    def test_skip_consumes_no_extra_question_and_feedback_cannot_bypass_pending_check(self):
        with tempfile.TemporaryDirectory() as tmp,patch('diagnostic.chat_router.plan',return_value={'action':'check','concept_id':'MATH6_C0025'}),patch.object(chat,'generate',side_effect=RuntimeError('offline')):
            conn=e.connect(Path(tmp)/'cycle.db');start=chat.send(conn,'a','help','en');thread=start['thread_id']
            with self.assertRaises(ValueError):chat.send(conn,'a','__feedback__:simpler','en',thread)
            out=chat.send(conn,'a','__explain_now__','en',thread)['message']
            self.assertEqual(out['tutor_summary']['questions_asked'],0)
            self.assertTrue(all(c['status']=='Unassessed' for c in out['tutor_summary']['concepts']))
            conn.close()

    def test_followup_snapshot_is_usable_by_a_subsequent_check(self):
        with tempfile.TemporaryDirectory() as tmp,patch('diagnostic.chat_router.plan',return_value={'action':'practice','concept_id':'MATH6_C0024'}):
            conn=e.connect(Path(tmp)/'cycle.db');start=chat.send(conn,'a','practice','en');thread=start['thread_id']
            state=json.loads(conn.execute('SELECT payload FROM book_chat_tutoring WHERE thread_id=?',(thread,)).fetchone()[0])
            chat.send(conn,'a',state['practice']['answer'],'en',thread)
            with patch('diagnostic.chat_router.plan',return_value={'action':'check','concept_id':'MATH6_C0025'}),patch.object(chat,'generate',side_effect=RuntimeError('offline')):
                out=chat.send(conn,'a','check acute angle','en',thread)['message']
                while out.get('check_question'):
                    q=next(q for q in load() if q['id']==out['check_question']['id'])
                    out=chat.send(conn,'a',q['answer'],'en',thread)['message']
                self.assertIn('tutor_summary',out)
            conn.close()


if __name__=='__main__':unittest.main()
