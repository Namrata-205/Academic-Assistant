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
        self.assertEqual(first[0]['matched_excerpt'],passages[1])
        self.assertIn(passages[1],first[0]['excerpt'])
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

    def test_hindi_words_keep_combining_marks(self):
        text='न्यून कोण और समकोण'
        self.assertEqual(chunks._terms(text),set(text.split()))
        self.assertNotIn('क',chunks._terms(text))

    def test_late_context_preserves_order_and_size_and_question_answer(self):
        texts=['Earlier context.', 'How large is this angle?',
               'It is a right angle.', 'Its measure is 90 degrees.', 'Later context.']
        text,start,end=chunks.evidence_context(texts,1)
        self.assertIn('90 degrees',text)
        self.assertEqual(text,' '.join(texts[start:end]))
        oversized=['x'*400,'y'*400,'z'*400]
        self.assertEqual(chunks.evidence_context(oversized,1),('y'*400,1,2))

    def test_token_windows_retain_tail_without_changing_shared_tokenizer(self):
        # Optional local embedding dependencies live in the semantic runtime.
        chunks.sm.runtime()
        from tokenizers import Tokenizer
        from tokenizers.models import WordLevel
        from tokenizers.pre_tokenizers import Whitespace
        tokenizer=Tokenizer(WordLevel({'[UNK]':0,'body':1,'tail':2},unk_token='[UNK]'))
        tokenizer.pre_tokenizer=Whitespace();tokenizer.enable_truncation(max_length=128)
        before=tokenizer.to_str();text=' '.join(['body']*170+['tail'])
        chunks.embedding_windows.cache_clear()
        with patch.object(chunks.sm,'runtime',return_value=(None,None,tokenizer)):
            windows=chunks.embedding_windows(text)
        self.assertTrue(windows[-1].endswith('tail'))
        self.assertTrue(all(len(tokenizer.encode(w,add_special_tokens=False).ids)<=112 for w in windows))
        self.assertEqual(tokenizer.to_str(),before)
        chunks.embedding_windows.cache_clear()


if __name__=='__main__':unittest.main()
