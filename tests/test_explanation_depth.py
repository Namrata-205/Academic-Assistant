import unittest
from unittest.mock import patch
from diagnostic import book_chat as chat


class ExplanationDepthTests(unittest.TestCase):
    def test_definition_only_is_retried_and_not_accepted_as_full_explanation(self):
        source={'id':'S1','excerpt':'An acute angle is greater than zero degrees and less than ninety degrees.'}
        definition={'text':'An acute angle is smaller than a right angle.','citations':['S1'],'evidence':source['excerpt']}
        full={'paragraphs':[definition,
            dict(definition,heading='Worked example',text='45 degrees is greater than zero and smaller than ninety, so it is acute.'),
            dict(definition,heading='Try it',text='Is 60 degrees acute? Compare it with zero and ninety.')]}
        with patch.object(chat,'model_status',return_value={'generation_available':True,'provider':'gemini','model':'test'}),patch.object(chat,'configuration',return_value={'GEMINI_API_KEY':'test'}),patch.object(chat,'gemini_generate',side_effect=[{'paragraphs':[definition]},full]) as call:
            result=chat.generate('What is an acute angle?','acute angle','en',[source],[])
            self.assertEqual(call.call_count,2);self.assertEqual(len(result),3)
            self.assertEqual(result[1]['heading'],'Worked example')
        with patch.object(chat,'model_status',return_value={'generation_available':True,'provider':'gemini','model':'test'}),patch.object(chat,'configuration',return_value={'GEMINI_API_KEY':'test'}),patch.object(chat,'gemini_generate',return_value={'paragraphs':[definition]}) as call:
            result=chat.generate('Briefly define acute angle','acute angle','en',[source],[])
            self.assertEqual(len(result),1);self.assertEqual(call.call_count,1)


if __name__=='__main__':unittest.main()
