import unittest
from pathlib import Path
from diagnostic.engine import ROOT,load_graph,map_question


class SemanticMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.nodes,cls.edges=load_graph()
    def test_context_regressions_and_mathematical_constraints(self):
        examples=[('समकोण कितने डिग्री का होता है?','MATH6_C0024'),
                  ('How do I find the value of 7 in 4720?','MATH6_C0038'),
                  ('An angle smaller than a quarter turn','MATH6_C0025'),
                  ('A path with one starting point and no end','MATH6_C0019'),
                  ('किसी संख्या के अंकों का योग कैसे निकालूँ?','MATH6_C0039')]
        for text,expected in examples:
            with self.subTest(text=text):self.assertEqual(map_question(text,self.nodes,self.edges).get('concept_id'),expected)
        for text in ['I don’t understand why the 4 in 3452 means 400. Can you explain it simply with an example?',
                     'Why does the 6 in 268 represent 60?', 'The 4 in 3452 means 40. Is that right?']:
            with self.subTest(text=text):self.assertEqual(map_question(text,self.nodes,self.edges).get('concept_id'),'MATH6_C0038')
        for text in ['भिन्नों का जोड़ कैसे करें?','Explain fractions and addition','right angle and place value','odd number','विषम संख्या']:
            with self.subTest(text=text):self.assertEqual(map_question(text,self.nodes,self.edges)['status'],'clarify')
    @unittest.skipUnless((ROOT/'assets/models/multilingual-minilm/model_quantized.onnx').exists(),'Local model not installed')
    def test_genuine_semantic_paraphrases(self):
        for text,expected in [('What is the shared endpoint of two arms called?','MATH6_C0021'),
                              ('How do I round 367 to the nearest hundred?','MATH6_C0043')]:
            result=map_question(text,self.nodes,self.edges)
            self.assertEqual(result.get('concept_id'),expected)
            self.assertEqual(result['method'],'local multilingual semantic retrieval')
            self.assertFalse(result['similarity_is_probability'])


if __name__=='__main__':unittest.main()
