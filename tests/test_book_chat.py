import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from diagnostic import engine as e,book_chat as chat


class BookChatTests(unittest.TestCase):
    def setUp(self):
        p=patch('diagnostic.chat_router.gemini_generate',side_effect=RuntimeError('offline test'))
        p.start();self.addCleanup(p.stop)
    def test_numeric_place_value_explains_calculation_without_false_book_citation(self):
        output=chat.answer('I do not understand why the 4 in 3452 means 400. Explain simply.','en')
        self.assertEqual(output['concept']['id'],'MATH6_C0038')
        self.assertEqual(output['mode'],'calculated')
        self.assertIn('4 × 100 = 400',output['paragraphs'][0]['text'])
        self.assertEqual(output['sources'],[])
        self.assertIsNone(chat.place_value_example('The 4 in 3442 means 400','en'))
    def test_duplicate_sources_and_uninformative_fragments_are_removed(self):
        a={'id':'S1','url':'/book#page=5','concept_id':'vertex','excerpt':'The vertex is the common endpoint where the two arms of an angle meet.'}
        b=dict(a,id='S2',concept_id='angle')
        c=dict(a,id='S3',concept_id='line segment',excerpt='This gives the idea of a line segment.')
        sources=chat.clean_sources([a,b,c])
        self.assertEqual(len(sources),1)
        self.assertEqual(sources[0]['concept_ids'],['vertex','angle'])
        self.assertEqual(sources[0]['id'],'S1')

    def test_fake_citations_and_evidence_are_rejected(self):
        sources=[{'id':'S1','excerpt':'An angle has two arms sharing a common endpoint called the vertex.'}]
        valid={'paragraphs':[{'text':'An angle has two arms.','citations':['S1'],'evidence':'An angle has two arms sharing a common endpoint'}]}
        self.assertEqual(chat.validate_generation(valid,sources,'en')[0]['citations'],['S1'])
        for bad in [
            {'text':'An angle has two arms.','citations':['S9'],'evidence':sources[0]['excerpt']},
            {'text':'An angle has two arms.','citations':['S1'],'evidence':'This invented quote is not in the textbook'},
            {'text':'An angle has 2 + 2 = 9 arms.','citations':['S1'],'evidence':sources[0]['excerpt']},
        ]:
            with self.assertRaises(ValueError):chat.validate_generation({'paragraphs':[bad]},sources,'en')
        with self.assertRaises(ValueError):chat.validate_generation(valid,sources,'hi')
        bilingual={'paragraphs':[dict(valid['paragraphs'][0],text='An angle is a कोण.')]} 
        with self.assertRaises(ValueError):chat.validate_generation(bilingual,sources,'en')
        with self.assertRaises(ValueError):chat.validate_generation(valid,sources,'en',[{'en':'vertex','hi':'शीर्ष'}])
    def test_bilingual_sources_and_safe_fallback(self):
        with patch('diagnostic.book_chat.generate',side_effect=RuntimeError('generator unavailable')):
            for language in ('en','hi'):
                result=chat.answer('Explain this idea',language,'MATH6_C0025')
                self.assertEqual(result['mode'],'extractive')
                self.assertEqual(result['sources'][0]['language'],language)
                self.assertEqual(result['sources'][0]['printed_page'],31)
                self.assertEqual(result['paragraphs'][0]['text'],result['sources'][0]['excerpt'])
                self.assertIn('न्यून',result['terms'][0]['hi'])
    def test_unavailable_sources_and_out_of_scope_queries_abstain(self):
        self.assertEqual(chat.answer('Explain parallel lines','en','MATH6_C0032')['status'],'insufficient_sources')
        self.assertEqual(chat.answer('How do I add fractions?')['status'],'clarify')
        with self.assertRaises(ValueError):chat.answer('','en')
        with self.assertRaises(ValueError):chat.answer('hello','xx')
    def test_chat_history_is_saved_and_learner_scoped(self):
        with tempfile.TemporaryDirectory() as tmp,patch('diagnostic.book_chat.generate',side_effect=RuntimeError('offline')):
            path=Path(tmp)/'history.sqlite3';conn=e.connect(path)
            result=chat.send(conn,'learner-a','Explain a right angle','en',concept_id='MATH6_C0024')
            sid=result['thread_id']
            self.assertEqual(e.history(conn,'learner-a'),[])
            self.assertEqual(len(chat.messages(conn,'learner-a',sid)),2)
            self.assertEqual(chat.threads(conn,'learner-b'),[])
            with self.assertRaises(LookupError):chat.messages(conn,'learner-b',sid)
            with self.assertRaises(LookupError):chat.send(conn,'learner-b','explain more','en',sid)
            followup=chat.send(conn,'learner-a','explain more','hi',sid)
            self.assertEqual(followup['message']['concept']['id'],'MATH6_C0024')
            self.assertEqual(followup['message']['language'],'hi')
            conn.close();conn=e.connect(path)
            self.assertEqual(len(chat.messages(conn,'learner-a',sid)),4)
            conn.close()


if __name__=='__main__':unittest.main()
