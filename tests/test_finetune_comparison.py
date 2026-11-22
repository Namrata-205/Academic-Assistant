import importlib.util
import json
from pathlib import Path
import unittest
from diagnostic import engine as e

spec=importlib.util.spec_from_file_location('finetune_compare',e.ROOT/'scripts/finetune_compare.py')
experiment=importlib.util.module_from_spec(spec);spec.loader.exec_module(experiment)


class FineTuningComparisonTests(unittest.TestCase):
    def test_response_checks_reject_invalid_citations_and_incorrect_arithmetic(self):
        sample={'language':'en','sources':[{'id':'S1','excerpt':'An angle has two arms sharing a common endpoint called the vertex.'}],
                'terms':[{'en':'angle','hi':'कोण'}]}
        good={'paragraphs':[{'text':'An angle has two arms.','citations':['S1'],'evidence':sample['sources'][0]['excerpt']}]}
        self.assertTrue(experiment.score_response(json.dumps(good),sample)['source_checked'])
        fenced='```json\n'+json.dumps(good)+'\n```'
        self.assertFalse(experiment.score_response(fenced,sample)['json_valid'])
        self.assertTrue(experiment.score_response(experiment.strip_single_fence(fenced),sample)['source_checked'])
        self.assertFalse(experiment.score_response(experiment.strip_single_fence('Preface\n'+fenced),sample)['json_valid'])
        for raw in ('not json','[]','{}'):
            self.assertFalse(experiment.score_response(raw,sample)['source_checked'])
        bad=json.loads(json.dumps(good));bad['paragraphs'][0]['citations']=['S99']
        self.assertFalse(experiment.score_response(json.dumps(bad),sample)['source_checked'])
        bad=json.loads(json.dumps(good));bad['paragraphs'][0]['text']='An angle has 2 + 2 = 9 arms.'
        self.assertFalse(experiment.score_response(json.dumps(bad),sample)['source_checked'])

    def test_frozen_experiment_excludes_final_scenarios_and_training_test_families(self):
        path=e.ROOT/'reports/finetuning_v2/dataset.json'
        if not path.exists():self.skipTest('Experiment has not been prepared')
        data=json.loads(path.read_text(encoding='utf-8'))
        self.assertFalse(data['provenance']['final_scenarios_used'])
        train={row['family'] for row in data['train']}
        self.assertFalse(train & {row['family'] for row in data['validation']})
        self.assertFalse(train & {row['family'] for row in data['test']})
        self.assertEqual(len(data['test']),12)

    def test_encoded_pairs_mask_prompts_and_keep_shared_token_budget(self):
        path=e.ROOT/'reports/finetuning_v2/encoded_dataset.json'
        if not path.exists():self.skipTest('Training examples have not been encoded')
        data=json.loads(path.read_text(encoding='utf-8'))
        for split in ('train','validation'):
            rows=data[split];ids={row['id'] for row in rows}
            self.assertTrue(rows)
            for row in rows:
                partner=row['id'].replace('-en-','-hi-') if row['language']=='en' else row['id'].replace('-hi-','-en-')
                self.assertIn(partner,ids)
                self.assertLessEqual(len(row['input_ids']),data['config']['max_sequence_tokens'])
                self.assertEqual(len(row['input_ids']),len(row['labels']))
                self.assertEqual(row['labels'][0],-100)
                self.assertNotEqual(row['labels'][-1],-100)


if __name__=='__main__':unittest.main()
