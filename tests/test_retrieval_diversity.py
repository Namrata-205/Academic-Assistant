import unittest
from diagnostic.retrieval_diversity import rerank,merged,length,intersection,budgeted_prefix


class DiversityTests(unittest.TestCase):
    def test_budget_preserves_prefix_and_never_exceeds_old_ceiling(self):
        rows=[{'excerpt':'a'*400},{'excerpt':'b'*400},{'excerpt':'c'*400}]
        self.assertEqual(budgeted_prefix(rows),rows)
        rows[2]['excerpt']='c'*600
        self.assertEqual(budgeted_prefix(rows),rows[:2])
        with self.assertRaises(ValueError):budgeted_prefix(rows,max_chars=0)
    def test_union_and_intersection_do_not_double_count(self):
        self.assertEqual(merged([(0,10),(5,20),(20,25)]),[(0,25)])
        self.assertEqual(length([(0,10),(5,20)]),20)
        self.assertEqual(intersection([(0,20)],[(5,10),(8,15)]),10)

    def test_redundancy_is_penalized_but_pool_and_first_result_are_preserved(self):
        rows=[{'id':'a','url':'/book#page=1','retrieval_score':1.,'context_char_start':0,'context_char_end':100},
              {'id':'b','url':'/book#page=1','retrieval_score':.99,'context_char_start':0,'context_char_end':100},
              {'id':'c','url':'/book#page=1','retrieval_score':.95,'context_char_start':100,'context_char_end':200}]
        for row in rows:row.update(semantic_score=.8,query_coverage=.5)
        result=rerank(rows)
        self.assertEqual([r['id'] for r in result],['a','c','b'])
        self.assertEqual(set(r['id'] for r in result),set(r['id'] for r in rows))
        self.assertNotIn('source_overlap',rows[0])

    def test_diversity_cannot_promote_weaker_evidence(self):
        rows=[{'id':'a','url':'/page','retrieval_score':1.,'context_char_start':0,'context_char_end':100,
               'semantic_score':.9,'query_coverage':.8},
              {'id':'b','url':'/page','retrieval_score':.99,'context_char_start':0,'context_char_end':100,
               'semantic_score':.8,'query_coverage':.7},
              {'id':'c','url':'/page','retrieval_score':.95,'context_char_start':100,'context_char_end':200,
               'semantic_score':.7,'query_coverage':.7}]
        self.assertEqual([r['id'] for r in rerank(rows)],['a','b','c'])

    def test_other_pages_and_unknown_offsets_are_not_penalized(self):
        rows=[{'url':'/book#page=1','retrieval_score':1.,'context_char_start':0,'context_char_end':100},
              {'url':'/book#page=2','retrieval_score':.99,'context_char_start':0,'context_char_end':100},
              {'url':'/book#page=1','retrieval_score':.98}]
        self.assertEqual([r['source_overlap'] for r in rerank(rows)],[0.,0.,0.])

    def test_support_coverage_does_not_reward_duplicate_excerpts(self):
        from scripts.evaluate_evidence_coverage import coverage
        a={'url':'/page','excerpt':'x'*100,'context_char_start':0,'context_char_end':100}
        b={'url':'/page','excerpt':'y'*100,'context_char_start':100,'context_char_end':200}
        reference={'/page':[(0,200)]}
        self.assertEqual(coverage([a,a],reference)['support_span_coverage'],.5)
        self.assertEqual(coverage([a,a],reference)['redundant_fraction'],.5)
        self.assertEqual(coverage([a,b],reference)['support_span_coverage'],1.)
        self.assertEqual(coverage([a,b],reference)['redundant_fraction'],0.)
        self.assertIsNone(coverage([a],{})['support_span_coverage'])


if __name__=='__main__':unittest.main()
