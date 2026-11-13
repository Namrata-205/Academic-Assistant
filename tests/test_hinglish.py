import re
from collections import Counter
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from diagnostic import engine as e,book_chat as chat,hinglish
from diagnostic.tutor_bank import load


class HinglishTests(unittest.TestCase):
    def test_detects_roman_hindi_without_overriding_hindi_or_english(self):
        self.assertEqual(hinglish.detect('mujhe number pattern nahi samjhta theek se'),'hinglish')
        self.assertEqual(hinglish.detect('Explain acute angles simply'),'en')
        self.assertEqual(hinglish.detect('mujhe pattern nahi samajhta','hi'),'hi')
        self.assertEqual(hinglish.detect('2','hinglish'),'hinglish')

    def test_question_math_tokens_and_keys_are_preserved(self):
        for q in load():
            translated=hinglish.question(q)
            self.assertEqual(Counter(re.findall(r'\d+',q['en'])),Counter(re.findall(r'\d+',translated)),q['id'])
            self.assertFalse(re.search('[\u0900-\u097f]',translated))
            self.assertEqual(e.score(q,q['answer']),1)
        self.assertEqual(hinglish.question(next(q for q in load() if q['id']=='TQ_FOUNDATION_06')),'68 aur 70 ke beech kaunsa number aata hai?')

    def test_hinglish_persists_through_answers_and_does_not_leak_between_requests(self):
        with tempfile.TemporaryDirectory() as tmp,patch('diagnostic.chat_router.gemini_generate',side_effect=RuntimeError('offline')):
            conn=e.connect(Path(tmp)/'chat.db')
            start=chat.send(conn,'a','mujhe number pattern nahi samjhta theek se','en')
            self.assertEqual(start['message']['language'],'hinglish')
            self.assertIn('basics',start['message']['message'])
            self.assertTrue(start['message']['check_question']['translations']['hinglish'])
            with patch.object(chat,'generate',side_effect=RuntimeError('offline')):
                reply=chat.send(conn,'a','__check_batch__:'+__import__('json').dumps(['7']*len(start['message']['check_questions'])),'hinglish',start['thread_id'])
            self.assertEqual(reply['message']['language'],'hinglish')
            self.assertNotIn('answer',reply['message']['practice_question'])
            self.assertEqual(hinglish.STYLE.get(),'en')
            self.assertEqual(e.history(conn,'a'),[]);conn.close()


if __name__=='__main__':unittest.main()
