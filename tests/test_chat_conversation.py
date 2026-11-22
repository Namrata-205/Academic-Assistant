import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from diagnostic import book_chat as chat, engine
from diagnostic.conversation import CURRENT, feedback


class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.conn=engine.connect(Path(self.tmp.name)/'chat.sqlite3');self.addCleanup(self.conn.close)
        self.offline=patch('diagnostic.chat_router.gemini_generate',side_effect=RuntimeError('offline'))
        self.offline.start();self.addCleanup(self.offline.stop)

    def test_natural_repair_reuses_topic_changes_example_and_does_not_grade_prose(self):
        with patch('diagnostic.book_chat.generate',side_effect=RuntimeError('offline')):
            first=chat.send(self.conn,'a','What is an acute angle?','en')
            tid=first['thread_id']
            self.assertEqual(first['message']['mode'],'guided_local')
            second=chat.send(self.conn,'a',"I didn't understand",'en',tid)['message']
            self.assertEqual(second['concept']['id'],'MATH6_C0025')
            self.assertEqual(second['feedback_action'],'still_confused')
            self.assertNotIn('practice_question',second)
            third=chat.send(self.conn,'a',"__chat_query__:I still don't understand",'en',tid)['message']
            self.assertNotEqual(second['paragraphs'],third['paragraphs'])
            self.assertNotEqual(third['mode'],'practice_feedback')
            self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM book_chat_tutor_events WHERE kind=?',('followup_answer',)).fetchone()[0],0)

    def test_recent_dialogue_is_bounded_restored_and_thread_scoped(self):
        captured=[]
        def generate(*args):
            captured.append(list(CURRENT.get()))
            return [{'text':'An angle measures the opening between its arms.','citations':['S1']}]
        with patch('diagnostic.book_chat.generate',side_effect=generate):
            first=chat.send(self.conn,'a','What is an acute angle?','en')
            tid=first['thread_id']
            chat.send(self.conn,'a','Why is that less than 90?','en',tid)
            self.assertTrue(captured[-1])
            self.assertIn('opening',captured[-1][-1]['text'])
            self.assertEqual(len(chat.messages(self.conn,'a',tid)),4)
            chat.send(self.conn,'b','What is a right angle?','en')
            self.assertEqual(captured[-1],[])
            with self.assertRaises(LookupError):chat.send(self.conn,'b','why?','en',tid)
            self.assertEqual(CURRENT.get(),())

    def test_explicit_new_topic_overrides_previous_topic(self):
        with patch('diagnostic.book_chat.generate',side_effect=RuntimeError('offline')):
            first=chat.send(self.conn,'a','What is an acute angle?','en')
            result=chat.send(self.conn,'a','What is a square number?','en',first['thread_id'])['message']
            self.assertEqual(result['concept']['id'],'MATH6_C0009')

    def test_hindi_and_roman_hindi_repair_phrases(self):
        for text in ('समझ नहीं आया','मुझे नहीं समझ आया','samajh nahi aaya',"I didn’t understand"):
            self.assertEqual(feedback(text),'still_confused')

    def test_numeric_reference_is_resolved_locally_without_a_false_citation(self):
        first=chat.send(self.conn,'a','Why does the 4 in 3452 mean 400?','en')
        result=chat.send(self.conn,'a',"I didn't understand",'en',first['thread_id'])['message']
        self.assertEqual(result['mode'],'calculated')
        self.assertIn('100 + 100 + 100 + 100 = 400',result['paragraphs'][0]['text'])
        self.assertEqual(result['sources'],[])

    def test_generated_lesson_does_not_get_a_second_worked_example_appended(self):
        lesson=[{'text':'Draw two arrows from O. Their shared starting dot is the vertex.',
                 'citations':['S1'],'kind':'explanation'}]
        with patch('diagnostic.book_chat.generate',return_value=lesson):
            result=chat.send(self.conn,'a','Explain the vertex of an angle','en')['message']
        self.assertEqual(result['mode'],'generated')
        self.assertEqual(result['paragraphs'],lesson)

    def test_composer_can_interrupt_a_check_without_scoring_question_as_answer(self):
        with patch('diagnostic.book_chat.generate',side_effect=RuntimeError('offline')):
            first=chat.send(self.conn,'a','I am confused about acute angles','en')
            tid=first['thread_id']
            self.assertEqual(first['message']['mode'],'learning_check')
            result=chat.send(self.conn,'a','__chat_query__:Explain a square number','en',tid)['message']
            self.assertEqual(result['concept']['id'],'MATH6_C0009')
            self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM book_chat_check_answers').fetchone()[0],0)

    def test_cloud_prompt_excludes_dialogue_and_private_evidence(self):
        source={'id':'S1','excerpt':'An acute angle is greater than zero and less than ninety degrees.'}
        reply={'paragraphs':[{'text':'An acute angle has a smaller opening than a right angle.',
              'citations':['S1'],'evidence':source['excerpt']}]}
        token=CURRENT.set(({'role':'assistant','text':'We used a door opening as an example.'},))
        self.addCleanup(CURRENT.reset,token)
        with patch.object(chat,'model_status',return_value={'generation_available':True,'provider':'gemini','model':'test'}),patch.object(chat,'gemini_generate',return_value=reply) as generate:
            chat.generate('explain simply','acute angle','en',[source],[],{'secret_score':'PRIVATE'})
        prompt=json.loads(generate.call_args.args[1])
        self.assertNotIn('conversation',prompt)
        self.assertNotIn('door',generate.call_args.args[1])
        self.assertNotIn('PRIVATE',generate.call_args.args[1])
