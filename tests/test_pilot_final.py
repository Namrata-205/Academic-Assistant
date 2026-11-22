from tests.legacy_curriculum import frozen_v1
import unittest
from unittest.mock import patch
from diagnostic import engine as e
from diagnostic.pilot_final import run_case,validate_cases,CASES
import json


class DevelopmentPilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._legacy=frozen_v1();cls._legacy.__enter__();cls.addClassCleanup(cls._legacy.__exit__,None,None,None)
        cls.nodes,cls.edges=e.load_graph();cls.bank=e.load_bank()

    def fixture(self,mode='correct'):
        responses={q['id']:q['answer'] if mode=='correct' else 'not sure' for q in self.bank}
        return {'id':'DEV_ONLY','language':'en','input':'Explain place value','expected_mapping':'MATH6_C0038',
                'response_mode':mode,'responses':responses,
                'expected_statuses':{q['concept_id']:'Evidence supports understanding' for q in self.bank}}

    def test_same_item_answers_and_shared_budget(self):
        case=self.fixture();fixed=run_case(case,'fixed',self.bank,self.nodes,self.edges)
        guided=run_case(case,'graph-guided',self.bank,self.nodes,self.edges)
        self.assertEqual(fixed['questions_asked'],3);self.assertEqual(guided['questions_asked'],2)
        self.assertEqual(fixed['correct_diagnoses'],1);self.assertEqual(guided['correct_diagnoses'],1)
        self.assertEqual(case['responses'],self.fixture()['responses'])

    def test_unclear_answers_never_create_difficulty_and_mapping_abstention_keeps_opportunities(self):
        case=self.fixture('ambiguous');out=run_case(case,'graph-guided',self.bank,self.nodes,self.edges)
        self.assertEqual(out['questions_asked'],3);self.assertEqual(out['false_diagnoses'],0)
        self.assertEqual(out['unresolved_concepts'],1)
        with patch('diagnostic.pilot_final.e.map_question',return_value={'status':'clarify'}):
            out=run_case(self.fixture(),'fixed',self.bank,self.nodes,self.edges)
        self.assertFalse(out['mapping_correct']);self.assertEqual(out['unresolved_concepts'],1)
        self.assertEqual(out['questions_asked'],0)

    def test_export_is_bilingual_and_transport_corruption_is_rejected(self):
        data=json.loads(CASES.read_text(encoding='utf-8'))
        validate_cases(data,self.bank)
        case=next(c for c in data['cases'] if c['language']=='hi' and c['input'])
        case['input']='????'
        with self.assertRaises(ValueError):validate_cases(data,self.bank)


if __name__=='__main__':unittest.main()
