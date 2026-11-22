import unittest
from diagnostic import hybrid_retrieval as hybrid


class HybridRetrievalTests(unittest.TestCase):
    def test_unicode_digits_marks_and_negation(self):
        self.assertEqual(hybrid.words('समकोण ९०° नहीं'),['समकोण','90','नहीं'])
        self.assertNotIn('not',hybrid.STOP_WORDS)
        self.assertNotIn('नहीं',hybrid.STOP_WORDS)

    def test_bm25_exact_numeric_evidence_and_term_frequency(self):
        scores=hybrid.bm25_scores(['A measure of 45 degrees.', 'A measure of 90 degrees.'], '९० degrees')
        self.assertGreater(scores[1],scores[0])
        self.assertEqual(hybrid.bm25_scores(['',''], 'measure'),[0.,0.])
        self.assertEqual(hybrid.bm25_scores(['measure'], 'the is'),[0.])

    def test_fusion_recovers_exact_match_without_mutating_evidence(self):
        rows=[{'url':'/book','excerpt':'Unrelated passage','retrieval_score':.9},
              {'url':'/book','excerpt':'The measure is 90 degrees','retrieval_score':.8}]
        original=[dict(row) for row in rows]
        ranked=hybrid.fuse(rows,'90')
        self.assertEqual(ranked[0]['excerpt'],rows[1]['excerpt'])
        self.assertEqual(ranked[0]['bm25_rank'],1)
        self.assertEqual(rows,original)

    def test_no_keyword_matches_preserve_semantic_order(self):
        rows=[{'url':'/book','excerpt':'first','retrieval_score':.8},
              {'url':'/book','excerpt':'second','retrieval_score':.9}]
        ranked=hybrid.fuse(rows,'unmatched')
        self.assertEqual([r['excerpt'] for r in ranked],['second','first'])
        self.assertTrue(all(r['bm25_rank'] is None for r in ranked))

    def test_metadata_and_expanded_context_do_not_supply_keyword_matches(self):
        row={'url':'/book','excerpt':'Answer: 90 degrees','matched_excerpt':'A heading',
             'concept_en':'90 degrees','retrieval_score':.8}
        self.assertIsNone(hybrid.fuse([row],'90')[0]['bm25_rank'])


if __name__=='__main__':unittest.main()
