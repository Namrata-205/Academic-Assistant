import json
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from diagnostic import engine as e,book_chat as chat,chat_tutor as tutor,practice,mock_exams
from diagnostic.teaching_feedback import public_teaching_request,teaching_decision,context_decision
from diagnostic.learner_evidence import collect,assessment,content_id
from diagnostic.followup_templates import body
from diagnostic.bilingual_quality import check_pair,check_arithmetic


class PersonalizationTests(unittest.TestCase):
    def test_cloud_focus_survives_repeated_sanitization_without_private_fields(self):
        raw={'mode':'another_example','focus_concept_id':'MATH6_C0024','example_variant':2,
             'previous_example_variant':1,'learner':'SECRET','response':'PRIVATE','focus':{'en':'INJECT'}}
        once=public_teaching_request(raw);twice=public_teaching_request(once)
        self.assertEqual(once,twice)
        self.assertEqual(twice['focus']['id'],'MATH6_C0024')
        self.assertNotIn('SECRET',json.dumps(twice));self.assertNotIn('PRIVATE',json.dumps(twice))
        self.assertNotIn('INJECT',json.dumps(twice))
        self.assertNotEqual(twice['worked_example'],twice['previous_worked_example'])

    def test_actual_gemini_payload_retains_focus_and_fresh_recipe(self):
        source={'id':'S1','concept_id':'MATH6_C0024','excerpt':'A right angle measures exactly 90 degrees, which is a quarter turn.'}
        draft={'paragraphs':[{'text':'A right angle measures 90 degrees.','citations':['S1'],'evidence':source['excerpt']}]}
        request=public_teaching_request({'mode':'another_example','focus_concept_id':'MATH6_C0024',
                                         'example_variant':2,'previous_example_variant':1})
        with patch.object(chat,'model_status',return_value={'generation_available':True,'provider':'gemini','model':'gemini-test'}),\
             patch.object(chat,'configuration',return_value={'GEMINI_API_KEY':'test'}),\
             patch.object(chat,'gemini_generate',return_value=draft) as generate:
            chat.generate('Briefly explain right angle','right angle','en',[source],[],{'teaching_request':request,'learner':'PRIVATE'})
        payload=json.loads(generate.call_args.args[1])
        self.assertEqual(payload['teaching_request']['focus']['id'],'MATH6_C0024')
        self.assertNotIn('PRIVATE',json.dumps(payload))
        self.assertNotEqual(payload['teaching_request']['worked_example'],payload['teaching_request']['previous_worked_example'])

    def test_teaching_mode_follows_evidence_instead_of_always_confused(self):
        def report(status,assessment='Assessed'):
            return {'concepts':[{'concept_id':'MATH6_C0024','status':status,'assessment':assessment}]}
        self.assertEqual(teaching_decision(report('Possible prerequisite difficulty'),'MATH6_C0025')['mode'],'still_confused')
        self.assertEqual(teaching_decision(report('Evidence supports understanding'),'MATH6_C0025')['mode'],'build_on_understanding')
        self.assertEqual(teaching_decision(report('Insufficient evidence'),'MATH6_C0025')['mode'],'check_uncertainty')
        self.assertEqual(teaching_decision(report('Insufficient evidence','Unassessed'),'MATH6_C0025')['mode'],'check_uncertainty')

    def test_complete_check_changes_teaching_for_three_learners(self):
        bank=[q for q in e.load_bank() if q['concept_id']=='MATH6_C0024'][:2]
        for learner,profile,expected in [('a','correct','build_on_understanding'),('b','wrong','still_confused'),('c','unclear','check_uncertainty')]:
            with tempfile.TemporaryDirectory() as tmp,patch.object(tutor,'load_tutor_bank',return_value=bank),\
                 patch('diagnostic.chat_router.plan',return_value={'action':'check','concept_id':'MATH6_C0025'}),\
                 patch.object(chat,'answer',return_value={'status':'answered','paragraphs':[],'sources':[]}) as explanation,\
                 closing(e.connect(Path(tmp)/'test.db')) as conn:
                start=chat.send(conn,learner,'help','en');out=start['message']
                while out.get('check_question'):
                    q=next(q for q in bank if q['id']==out['check_question']['id'])
                    wrong=str(int(q['answer'])+1) if q['type']=='numeric' else next(c for c in 'ABCD' if c!=q['answer'])
                    response=q['answer'] if profile=='correct' else 'not sure' if profile=='unclear' else wrong
                    out=chat.send(conn,learner,response,'en',start['thread_id'])['message']
                self.assertEqual(out['teaching_decision']['mode'],expected)
                self.assertEqual(explanation.call_args.kwargs['teaching_request']['mode'],expected)
                self.assertLessEqual(out['tutor_summary']['questions_asked'],3);conn.close()

    def test_another_example_produces_distinct_source_backed_examples_offline(self):
        with tempfile.TemporaryDirectory() as tmp,patch('diagnostic.chat_router.plan',return_value={'action':'explain','concept_id':'MATH6_C0024'}),\
             patch.object(chat,'generate',side_effect=RuntimeError('offline')):
            conn=e.connect(Path(tmp)/'test.db');start=chat.send(conn,'a','Explain right angle','en');examples=[];items=[]
            for _ in range(2):
                result=chat.send(conn,'a','__feedback__:another_example','en',start['thread_id'])['message']
                examples.append(next(p['text'] for p in result['paragraphs'] if p['kind']=='original_worked_example'))
                items.append(result['practice_question']['text'])
                ids={s['id'] for s in result['sources']}
                self.assertTrue(all(set(p['citations'])<=ids for p in result['paragraphs']))
            self.assertNotEqual(examples[0],examples[1]);self.assertNotEqual(items[0],items[1]);conn.close()

    def test_activity_is_scoped_deduplicated_chronological_and_not_a_diagnosis(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn=e.connect(Path(tmp)/'test.db');practice.ensure(conn);mock_exams.ensure(conn)
            item=tutor.practice('MATH6_C0024',e.load_graph()[0]);payload=json.dumps(item)
            for sid,learner,date in [('old','a','2020-01-01T00:00:00+00:00'),('new','a','2021-01-01T00:00:00+00:00'),('other','b','2022-01-01T00:00:00+00:00')]:
                conn.execute('INSERT INTO practice_sessions VALUES (?,?,?,?,?,?,?)',(sid,learner,'MATH6_C0024','en',date,date,'topic-practice-v1'))
                conn.execute('INSERT INTO practice_items VALUES (?,?,?,?,?,?)',(sid,0,payload,'0',0,date))
            conn.execute('INSERT INTO mock_exams VALUES (?,?,?,?,?,?,?)',('exam','a','mixed','en',1609459200.,1609459200.,'submitted'))
            conn.execute('INSERT INTO mock_exam_items VALUES (?,?,?,?,?)',('exam',0,payload,'0',0));conn.commit()
            rows=collect(conn,'a')
            self.assertEqual(len(rows),1) # Same content across activities is one review signal.
            self.assertEqual(rows[0]['created'],'2021-01-01T00:00:00+00:00')
            self.assertEqual(assessment(rows),[])
            duplicate={'question_id':'followup-other-id','concept_id':'MATH6_C0024','response':'0','score':0,
                       'created':'2020-01-01T00:00:00+00:00','origin':'followup','item':item,'assessment_eligible':False}
            self.assertEqual(len(collect(conn,'a',[duplicate])),1)
            self.assertEqual(collect(conn,'nobody'),[])
            from diagnostic.chat_context import context
            n,edges=e.load_graph();c=context(conn,'a','MATH6_C0025',n,edges)
            self.assertEqual(c['selected_prerequisites'][0],'MATH6_C0024')
            self.assertTrue(all(r['status']=='Unassessed' for r in c['learning_evidence']))
            decision=context_decision(c,'MATH6_C0025')
            self.assertEqual(decision['mode'],'review_practice')
            self.assertEqual(decision['focus_concept_id'],'MATH6_C0024');conn.close()

    def test_followup_coverage_bilingual_numbers_keys_and_repetition(self):
        nodes,_=e.load_graph();supported=[]
        for cid in nodes:
            item=tutor.practice(cid,nodes)
            if item is None:continue
            supported.append(cid)
            self.assertTrue(check_pair(item['en'],item['hi'])['passed'],cid)
            self.assertEqual(e.score(item,item['answer']),1)
            check_arithmetic(item['feedback_en']);check_arithmetic(item['feedback_hi'])
        self.assertEqual(len(supported),144)
        self.assertIsNone(tutor.practice('MATH6_C0032',nodes))
        self.assertIsNone(tutor.practice('MATH6_C0048',nodes))
        state={'learner':'a'}
        first=tutor.fresh_practice('MATH6_C0003',nodes,state)
        second=tutor.fresh_practice('MATH6_C0003',nodes,state)
        self.assertNotEqual(content_id(first),content_id(second))

    def test_selected_math_template_keys_and_unambiguous_place_value(self):
        self.assertEqual(body('Collatz conjecture',0)['answer'],'10') # 3*3+1
        self.assertEqual(body('cube number',0)['answer'],'8')
        self.assertEqual(body('triangular number',0)['answer'],'3')
        self.assertEqual(body('Kaprekar number',0)['answer'],'3087')
        for seed in range(50):
            item=body('place value',seed);import re
            digit,number=re.search(r'value of (\d) in (\d+)',item['en']).groups()
            self.assertEqual(number.count(digit),1)
            self.assertEqual(item['answer'],str(int(digit)*100))


if __name__=='__main__':unittest.main()
