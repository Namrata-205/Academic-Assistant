import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from diagnostic import engine,book_chat as chat,chat_tutor


class InlineQuizTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.conn=engine.connect(Path(self.tmp.name)/'quiz.sqlite3');self.addCleanup(self.conn.close)
        for name in ('diagnostic.chat_router.gemini_generate','diagnostic.book_chat.generate'):
            p=patch(name,side_effect=RuntimeError('offline'));p.start();self.addCleanup(p.stop)

    def test_new_topic_checks_first_and_explicit_skip_teaches(self):
        first=chat.send(self.conn,'a','What is an acute angle?','en',check_first=True)
        self.assertEqual(first['message']['mode'],'learning_check')
        self.assertFalse(first['message'].get('paragraphs'))
        result=chat.send(self.conn,'a','__explain_now__','en',first['thread_id'],check_first=True)['message']
        self.assertTrue(result['paragraphs'])
        self.assertFalse(chat_tutor.history(self.conn,'a'))

    def test_batch_and_practice_answers_stay_in_persisted_question_cards(self):
        first=chat.send(self.conn,'a','What is an acute angle?','en',check_first=True)
        tid=first['thread_id'];result=first
        while result['message'].get('check_question'):
            q=result['message']['check_question']
            result=chat.send(self.conn,'a','__quiz_answer__:'+json.dumps({'question_id':q['id'],'answer':'not sure'}),'en',tid)
            self.assertEqual(len(result['quiz_update']['results']),1)
        saved=chat.messages(self.conn,'a',tid)
        self.assertEqual(sum(m['role']=='user' for m in saved),1)
        self.assertIn('quiz_feedback',saved[1]['payload'])
        q=result['message']['practice_question']
        token='__quiz_answer__:'+json.dumps({'question_id':q['id'],'answer':'A' if q['type']=='mcq' else '99999'})
        answered=chat.send(self.conn,'a',token,'en',tid)
        self.assertFalse(answered['append_message'])
        reopened=chat.messages(self.conn,'a',tid)
        self.assertEqual(len(reopened),len(saved))
        self.assertEqual(reopened[-1]['payload']['quiz_feedback'][0]['question_id'],q['id'])
        with self.assertRaises(ValueError):chat.send(self.conn,'a',token,'en',tid)
        with self.assertRaises(LookupError):chat.send(self.conn,'b',token,'en',tid)

    def test_angle_followup_persists_two_different_next_steps(self):
        from diagnostic.learner_evidence import next_step
        for learner, answer, action, reason in (
                ('correct', 'A', 'compare_angles', 'followup_correct'),
                ('review', 'B', 'review_half_turn', 'followup_review')):
            start = chat.send(self.conn, learner, '__continue_angle__:review', 'en', concept_id='MATH6_C0024')
            thread = start['thread_id']
            item = start['message']['practice_question']
            token = '__quiz_answer__:'+json.dumps({'question_id':item['id'],'answer':answer})
            chat.send(self.conn, learner, token, 'en', thread)
            feedback = chat.messages(self.conn, learner, thread)[-1]['payload']['quiz_feedback'][0]
            self.assertEqual(feedback['next_action'], action)
            self.assertEqual(next_step(self.conn, learner)['reason'], reason)
            command = '__angle_compare__' if action=='compare_angles' else '__feedback__:another_example'
            response = chat.send(self.conn, learner, command, 'en', thread)['message']
            if action=='compare_angles':
                self.assertIn('How much larger', response['practice_question']['text'])
            else:
                self.assertTrue(any('clock hand' in p['text'] for p in response['paragraphs']))

    def test_mismatched_question_does_not_consume_answer(self):
        first=chat.send(self.conn,'a','What is an acute angle?','en',check_first=True)
        token='__quiz_answer__:'+json.dumps({'question_id':'different-question','answer':'A'})
        with self.assertRaises(ValueError):chat.send(self.conn,'a',token,'en',first['thread_id'])
        self.assertFalse(chat_tutor.history(self.conn,'a'))

    def test_foundation_focus_does_not_force_textbook_dump(self):
        result=chat.answer('Explain acute angle simply','en','MATH6_C0025',conn=self.conn,learner='a',
            teaching_request={'mode':'still_confused','focus_concept_id':'MATH6_C0024','example_variant':1})
        self.assertEqual(result['mode'],'guided_local')
        self.assertFalse(any(p.get('kind')=='textbook_excerpt' for p in result['paragraphs']))

    def test_explicit_explanation_without_quiz_is_respected(self):
        result=chat.send(self.conn,'a','Just explain acute angle without questions','en',check_first=True)['message']
        self.assertNotEqual(result['mode'],'learning_check')
        self.assertTrue(result['paragraphs'])
