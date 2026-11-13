import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from diagnostic import engine as e,book_chat as chat,chat_router,chat_tutor


class HindiChatTests(unittest.TestCase):
    def test_hindi_angle_comparison_starts_a_foundation_check_without_topic_choices(self):
        question='मुझे समकोण और न्यून कोण के बीच का अंतर समझ नहीं आ रहा है। क्या आप आसान भाषा में समझा सकते हैं?'
        nodes,edges=e.load_graph();mapping=chat_tutor.tutoring_mapping(question,nodes,edges)
        self.assertEqual(mapping['concept_id'],'MATH6_C0025')
        plan=chat_router.validate({'action':'check','concept_id':'MATH6_C0024','confidence':.95},nodes,mapping)
        self.assertEqual(plan['concept_id'],'MATH6_C0025')
        with tempfile.TemporaryDirectory() as tmp,patch.object(chat_router,'plan',return_value=plan):
            conn=e.connect(Path(tmp)/'test.db')
            message=chat.send(conn,'a',question,'hi')['message']
            self.assertEqual(message['mode'],'learning_check')
            self.assertIn('समीक्षा',message['notice'])
            self.assertIn('hi',message['check_question']['translations'])
            self.assertNotIn('answer',message['check_question'])
            self.assertFalse(any(word in message['notice'] for word in ['Tutoring','Diagnostic','review']))
            conn.close()

    def test_hindi_fallback_notice_is_localized(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(chat_router,'plan',return_value={'action':'explain','concept_id':'MATH6_C0025'}),patch.object(chat,'generate',side_effect=RuntimeError('offline')):
            conn=e.connect(Path(tmp)/'test.db')
            message=chat.send(conn,'a','न्यून कोण समझाइए','hi')['message']
            self.assertEqual(message['mode'],'extractive')
            self.assertIn('पाठ्यपुस्तक',message['notice']);self.assertNotIn('Direct textbook',message['notice']);conn.close()


if __name__=='__main__':unittest.main()
