import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from diagnostic import engine as e,book_chat as chat,chat_router as router


class RouterTests(unittest.TestCase):
    def test_broad_pattern_difficulty_checks_prerequisites_before_patterns(self):
        local=e.map_question('I find patterns difficult to follow',self.nodes,self.edges)
        draft={'action':'check','concept_id':'MATH6_C0003','confidence':.9,'check_style':'example'}
        result=router.validate(draft,self.nodes,local)
        self.assertEqual(result['action'],'check');self.assertEqual(result['concept_id'],'MATH6_C0003')
        self.assertEqual(result['topic_assumption'],'number patterns')
        with tempfile.TemporaryDirectory() as tmp,patch.object(router,'plan',return_value=result):
            conn=e.connect(Path(tmp)/'chat.db')
            message=chat.send(conn,'a','I find patterns difficult to follow','en')['message']
            self.assertEqual(message['mode'],'learning_check')
            self.assertIn(message['check_question']['concept_id'],e.prerequisites('MATH6_C0003',self.edges))
            self.assertNotEqual(message['check_question']['concept_id'],'MATH6_C0003')
            self.assertIn('numbers and digits',message['message']);conn.close()

    @classmethod
    def setUpClass(cls):cls.nodes,cls.edges=e.load_graph()

    def test_actions_ids_and_ambiguity_are_validated(self):
        local={'status':'mapped','concept_id':'MATH6_C0025'}
        for draft in [{'action':'run_sql','concept_id':'MATH6_C0025','confidence':1},
                      {'action':'check','concept_id':'fake','confidence':1},
                      {'action':'check','concept_id':'MATH6_C0025','confidence':True}]:
            with self.assertRaises(ValueError):router.validate(draft,self.nodes,local)
        self.assertEqual(router.validate({'action':'check','concept_id':'MATH6_C0025','confidence':.4},self.nodes,local)['action'],'clarify')
        mapping=e.map_question('odd number',self.nodes,self.edges)
        self.assertEqual(router.validate({'action':'explain','concept_id':'MATH6_C0006','confidence':1},self.nodes,mapping)['action'],'clarify')

    def test_planner_uses_query_and_public_concepts_only(self):
        with patch.object(router,'configuration',return_value={'GEMINI_API_KEY':'test-key'}),patch.object(router,'gemini_generate',return_value={'action':'check','concept_id':'MATH6_C0025','confidence':.95}) as call:
            result=router.plan('I feel lost with acute angles',self.nodes,self.edges)
        self.assertEqual(result['action'],'check');self.assertEqual(result['planner'],'gemini')
        prompt=json.loads(call.call_args.args[1])
        self.assertEqual(set(prompt),{'query','previous_concept','selected_concept','concepts'})
        self.assertNotIn('test-key',json.dumps(prompt))

    def test_llm_routes_unanticipated_phrase_and_local_answers_bypass_it(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(router,'configuration',return_value={'GEMINI_API_KEY':'test-key'}),patch.object(router,'gemini_generate',return_value={'action':'check','concept_id':'MATH6_C0025','confidence':.96}) as planner:
            conn=e.connect(Path(tmp)/'chat.db')
            start=chat.send(conn,'a','Angles smaller than a right angle are a mystery to me.','en')
            self.assertEqual(start['message']['mode'],'learning_check')
            calls=planner.call_count
            with patch.object(chat,'generate',side_effect=RuntimeError('offline')):
                chat.send(conn,'a','__check_batch__:'+__import__('json').dumps(['2']*len(start['message']['check_questions'])),'en',start['thread_id'])
            self.assertEqual(planner.call_count,calls)
            self.assertEqual(e.history(conn,'a'),[]);conn.close()

    def test_explanation_request_and_practice_execute_separate_routes(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn=e.connect(Path(tmp)/'chat.db')
            with patch.object(router,'plan',return_value={'action':'explain','concept_id':'MATH6_C0025','planner':'gemini'}),patch.object(chat,'generate',side_effect=RuntimeError('offline')):
                result=chat.send(conn,'a','Explain acute angles without testing me','en')['message']
            self.assertNotIn('check_question',result)
            with patch.object(router,'plan',return_value={'action':'practice','concept_id':'MATH6_C0025','planner':'gemini'}):
                result=chat.send(conn,'a','Give me an acute angle practice problem','en')['message']
            self.assertIn('practice_question',result);self.assertNotIn('answer',result['practice_question'])
            conn.close()


if __name__=='__main__':unittest.main()
