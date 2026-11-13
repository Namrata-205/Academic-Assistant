import unittest
from diagnostic.evaluate_rag import ratio,relevant,retrieval_scores,aggregate
from diagnostic.evaluate_retrieval_k import scores


class MetricTests(unittest.TestCase):
    def test_rank_and_missing_result_denominators(self):
        self.assertEqual(retrieval_scores([False,True]),{'hit_at_1':0.,'hit_at_2':1.,'mrr_at_2':.5,'precision_at_2':.5})
        self.assertEqual(retrieval_scores([True])['precision_at_2'],.5)
        self.assertEqual(retrieval_scores([])['mrr_at_2'],0.)
        self.assertIsNone(ratio(0,0));self.assertEqual(ratio(1,2),.5)
        self.assertEqual(aggregate([{'x':0},{'x':1}],['x']),{'x':.5})
        self.assertEqual(aggregate([{'x':None},{'x':.5}],['x']),{'x':.5})
        self.assertEqual(aggregate([{'x':None}],['x']),{'x':None})

    def test_evidence_requires_page_and_all_markers(self):
        case={'pdf_pages':[38],'evidence_all':['acute','90','0']}
        self.assertTrue(relevant({'pdf_page':38,'excerpt':'Acute angles: 0 to 90'},case))
        self.assertFalse(relevant({'pdf_page':19,'excerpt':'Acute angles: 0 to 90'},case))
        self.assertFalse(relevant({'pdf_page':38,'excerpt':'Acute angles'},case))

    def test_multiple_k_uses_all_pool_evidence_and_fixed_precision_slots(self):
        flags=[False,True,False,True]
        self.assertEqual(scores(flags,1)['recall'],0.)
        self.assertEqual(scores(flags,2)['recall'],.5)
        self.assertEqual(scores(flags,5)['recall'],1.)
        self.assertEqual(scores(flags,5)['precision'],.4)
        self.assertEqual(scores(flags,5)['mrr'],.5)
        self.assertIsNone(scores([False],3)['recall'])
        with self.assertRaises(ValueError):scores(flags,0)


if __name__=='__main__':unittest.main()
