import unittest
from unittest.mock import patch
import numpy as np
from diagnostic import semantic_chunks as chunks


class GraphChunkTests(unittest.TestCase):
    def test_graph_links_prevent_transitive_topic_drift(self):
        # Adjacent cosine is .707, but endpoints have no edge. A chain
        # splitter joins all three; graph density keeps the last topic apart.
        texts=['First sentence.', 'Bridge sentence.', 'Last sentence.']
        vectors=np.array([[1.,0.],[1.,1.],[0.,1.]])
        result=chunks.split_graph(texts,lambda _:vectors)
        self.assertEqual(result,[texts[0]+' '+texts[1],texts[2]])

    def test_empty_singleton_and_zero_vectors(self):
        def fail(_):raise AssertionError('empty input must not be embedded')
        self.assertEqual(chunks.split_graph([],fail),[])
        self.assertEqual(chunks.split_graph(['One sentence.'],lambda _: [[0.,0.]]),['One sentence.'])
        self.assertEqual(chunks.split_graph(['First.', 'Second.'],lambda _:np.zeros((2,2))),['First.', 'Second.'])

    def test_size_ceiling_preserves_all_words_in_order(self):
        text=' '.join(['evidence']*300)
        result=chunks.split_graph([text],lambda ts:np.ones((len(ts),2)))
        self.assertTrue(all(len(t)<=chunks.MAX_CHARS for t in result))
        self.assertEqual(' '.join(result),text)

    def test_hindi_sentence_delimiter(self):
        self.assertEqual(chunks.units(['first\u0964 second\u0964']),['first\u0964','second\u0964'])

    def test_metadata_ranking_keeps_evidence_and_stable_identity(self):
        passages=['Unrelated passage.', 'An acute angle is smaller than a right angle.']
        meta={'url':'/book#page=2','pdf_page':2,'language':'en',
              'concept_en':'acute angle','section':'Angles','sha256':'verified-book'}
        vectors=np.array([[1.,0.],[1.,0.]])
        with patch.object(chunks,'page_index',return_value=(passages,vectors)), patch.object(chunks.sm,'embed',return_value=np.array([[1.,0.]])), patch.object(chunks,'contextual_vectors',return_value=vectors) as contextual:
            first=chunks.rank_pages([('book.pdf',2,1,meta)],'acute angle')
            second=chunks.rank_pages([('book.pdf',2,1,meta)],'acute angle')
        self.assertEqual(first[0]['excerpt'],passages[1])
        self.assertEqual(first[0]['concept_coverage'],1.)
        self.assertEqual(first[0]['chunk_id'],second[0]['chunk_id'])
        self.assertEqual(first[0]['chunk_count'],2)
        self.assertIn('Angles',contextual.call_args.args[1])
        self.assertEqual(first[0]['chunking'],chunks.VERSION)

    def test_page_index_uses_graph_chunks_and_keeps_citations(self):
        chunks.page_index.cache_clear()
        self.addCleanup(chunks.page_index.cache_clear)
        with patch('diagnostic.book_chat.page_content',return_value=['Exact textbook sentence.']), patch.object(chunks.sm,'embed',side_effect=lambda ts:np.ones((len(ts),2))), patch.object(chunks,'split_graph',wraps=chunks.split_graph) as split:
            result=chunks.rank_pages([('book.pdf',2,123,{'url':'/book#page=2','pdf_page':2})],'question',1)
        split.assert_called_once()
        self.assertEqual(result[0]['excerpt'],'Exact textbook sentence.')
        self.assertEqual(result[0]['pdf_page'],2)
        self.assertEqual(result[0]['url'],'/book#page=2')


if __name__=='__main__':unittest.main()
