from tests.legacy_curriculum import frozen_v1
import copy
import csv
import hashlib
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from diagnostic.prepare_scenarios import build,validate
from diagnostic.review_scenarios import readiness
from diagnostic.scenario_replay import Responses


class ScenarioPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._legacy=frozen_v1();cls._legacy.__enter__();cls.addClassCleanup(cls._legacy.__exit__,None,None,None)
        cls.data=build()

    def test_sixty_distinct_paired_cases_balanced_across_chapters_and_profiles(self):
        data=self.data
        self.assertEqual(validate(data)['scenarios'],60)
        self.assertEqual(Counter(c['chapter'] for c in data['cases']),{'CH01':20,'CH02':20,'CH03':20})
        self.assertEqual(Counter(c['split'] for c in data['cases']),{'development':30,'final_candidate':30})
        self.assertEqual(set(Counter(c['profile'] for c in data['cases']).values()),{12})
        for language in ('en','hi'):
            self.assertEqual(len({c['variants'][language]['question'] for c in data['cases']}),60)
        for case in data['cases']:
            self.assertTrue(case['label_reason']);self.assertEqual(case['review_status'],'PENDING')
            for variant in case['variants'].values():
                for source in variant['textbook_passages']:
                    if source['availability']=='available':
                        self.assertTrue(source['excerpt']);self.assertIn('sha256',source)

    def test_family_leakage_and_incomplete_response_packs_are_rejected(self):
        data=copy.deepcopy(self.data);data['cases'][1]['split']='final_candidate'
        with self.assertRaises(ValueError):validate(data)
        data=copy.deepcopy(self.data);data['cases'][0]['variants']['hi']['responses'].pop(next(iter(data['cases'][0]['variants']['hi']['responses'])))
        with self.assertRaises(ValueError):validate(data)

    def test_response_oracle_only_releases_requested_answers_with_budget(self):
        data=self.data;bank=data['bank'];oracle=Responses(data['cases'][0]['variants']['en'],bank)
        for q in bank[:3]:self.assertIsInstance(oracle.ask(q['id']),str)
        self.assertEqual(oracle.asked,[q['id'] for q in bank[:3]])
        with self.assertRaises(ValueError):oracle.ask(bank[3]['id'])
        oracle=Responses(data['cases'][0]['variants']['en'],bank);oracle.ask(bank[0]['id'])
        with self.assertRaises(ValueError):oracle.ask(bank[0]['id'])

    def test_final_is_blocked_without_independent_review_and_frozen_file_cannot_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'cases.json';path.write_text(json.dumps(self.data),encoding='utf-8')
            (root/'manifest.json').write_text(json.dumps({'cases_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}),encoding='utf-8')
            with (root/'blind_review.csv').open('w',newline='',encoding='utf-8-sig') as f:
                writer=csv.DictWriter(f,fieldnames=['case_id','decision']);writer.writeheader()
                writer.writerows({'case_id':c['id'],'decision':''} for c in self.data['cases'])
            status=readiness(root)
            self.assertFalse(status['final_ready']);self.assertEqual(status['independently_approved'],0)
            with self.assertRaises(ValueError):readiness(root,final=True)
            path.write_text('{}',encoding='utf-8')
            with self.assertRaises(ValueError):readiness(root)


if __name__=='__main__':unittest.main()
