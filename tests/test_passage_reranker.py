import unittest
from unittest.mock import patch
from diagnostic import passage_reranker as ce


class CrossEncoderTests(unittest.TestCase):
    def test_scores_reorder_without_changing_sources_or_dropping_tail(self):
        rows=[{'excerpt':str(i),'url':'/page','chunk_id':str(i)} for i in range(23)]
        with patch.object(ce,'score_passages',return_value=tuple(range(20))) as predict:
            result=ce.rerank(rows,'question')
        self.assertEqual(result[0]['chunk_id'],'19')
        self.assertEqual([r['chunk_id'] for r in result[20:]],['20','21','22'])
        self.assertEqual(set(r['chunk_id'] for r in result),set(r['chunk_id'] for r in rows))
        self.assertEqual(result[-1]['reranker_status'],'outside_shortlist')
        self.assertEqual(predict.call_args.args[0],'question')
        self.assertNotIn('cross_encoder_score',rows[0])

    def test_ties_preserve_original_order(self):
        rows=[{'excerpt':'a'},{'excerpt':'b'}]
        with patch.object(ce,'score_passages',return_value=(1.,1.)):
            self.assertEqual([r['excerpt'] for r in ce.rerank(rows,'q')],['a','b'])

    def test_optional_failure_preserves_order_with_explicit_status(self):
        rows=[{'excerpt':'a'},{'excerpt':'b'}]
        with patch.object(ce,'rerank',side_effect=RuntimeError('missing artifact')):
            output=ce.apply_if_available(rows,'q',enabled=True)
        self.assertEqual([r['excerpt'] for r in output],['a','b'])
        self.assertTrue(all(r['reranker_status']=='unavailable' for r in output))
        with patch.object(ce,'rerank',side_effect=AssertionError('must not run')):
            self.assertIs(ce.apply_if_available(rows,'q',enabled=False),rows)

    def test_real_local_model_separates_an_answer_from_unrelated_text(self):
        if not (ce.MODEL/'manifest.json').exists():self.skipTest('Optional local reranker not installed.')
        scores=ce.score_passages('How many degrees is a right angle?',
                                 ('A right angle measures 90 degrees.','This exercise uses odd numbers.'))
        self.assertGreater(scores[0],scores[1])


if __name__=='__main__':unittest.main()
