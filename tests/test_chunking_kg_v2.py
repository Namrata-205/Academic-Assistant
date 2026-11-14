import json
import unittest
import numpy as np
from diagnostic import chunking, kg_v2, engine as e
from diagnostic import semantic_chunks as sc


def fake_encode(texts):
    """Deterministic unit vectors: sentences sharing a first word are similar."""
    out = []
    for t in texts:
        v = np.zeros(16)
        v[hash(t.split()[0].lower()) % 16] = 1.0
        v[hash(t) % 16] += .3
        out.append(v / np.linalg.norm(v))
    return np.stack(out)


PAGES = [{'page': 1, 'text': '2.1 Point\n\nA point determines a location. It has no length, breadth or height.\n\n'
                              '2.2 Line Segment\n\nThe shortest path from point A to point B is called the line segment AB. '
                              'The points A and B are called the end points of the line segment AB.\n\nReprint 2026-27'},
         {'page': 2, 'text': '2.3 Line\n\nImagine that the line segment from A to B is extended beyond A in one direction '
                              'and beyond B in the other direction without any end. This is a line.'}]


class KnowledgeGraphV2(unittest.TestCase):
    def test_acyclic_unique_and_known(self):
        order, cyclic = kg_v2.validate()
        self.assertEqual(cyclic, [])
        self.assertEqual(len(order), len(kg_v2.CONCEPTS))

    def test_question_bank_ids_survive(self):
        ids = {c[0] for c in kg_v2.CONCEPTS}
        bank = {q['concept_id'] for q in e.load_bank()}
        self.assertTrue(bank <= ids, bank - ids)

    def test_every_v1_concept_kept_or_retired(self):
        nodes, _ = e.load_graph()
        ids = {c[0] for c in kg_v2.CONCEPTS}
        self.assertEqual(set(nodes) - ids - set(kg_v2.RETIRED), set())

    def test_every_concept_has_hindi_name_and_anchors(self):
        for c in kg_v2.CONCEPTS:
            self.assertRegex(c[5], r'[ऀ-ॿ]', c[0])
            self.assertTrue(c[6] and c[7], c[0])

    def test_longest_anchor_wins(self):
        compiled = kg_v2.compile_anchors(language='hi')
        self.assertEqual(kg_v2.find_concepts('यह न्यून कोण है', compiled), ['MATH6_C0025'])
        compiled = kg_v2.compile_anchors(language='en')
        self.assertIn('MATH6_C0041', kg_v2.find_concepts('Mark it on the number line.', compiled))
        self.assertNotIn('MATH6_C0017', kg_v2.find_concepts('Mark it on the number line.', compiled))


class ChunkingMethods(unittest.TestCase):
    def words(self, chunks):
        return ' '.join(c['text'] for c in chunks).split()

    def test_all_methods_keep_text_and_pages(self):
        expected = []
        for p in PAGES:
            expected += ' '.join(chunking.page_blocks(p['text'])[0]).split()
        for method in chunking.METHODS:
            chunks = chunking.chunk_chapter(PAGES, 'en', method, chapter=2, encode=fake_encode)
            self.assertEqual(self.words(chunks), expected, method)
            self.assertEqual({c['pdf_page'] for c in chunks}, {1, 2}, method)
            self.assertTrue(all('Reprint' not in c['text'] for c in chunks), method)

    def test_semantic_is_the_current_method(self):
        blocks, _ = chunking.page_blocks(PAGES[0]['text'])
        self.assertEqual(chunking.semantic(blocks, encode=fake_encode), sc.split_semantically(blocks, encode=fake_encode))

    def test_fixed_respects_size(self):
        chunks = chunking.chunk_chapter(PAGES, 'en', 'fixed', size=60)
        self.assertTrue(all(len(c['text']) <= 60 for c in chunks))

    def test_graph_cuts_at_concept_start_and_tags(self):
        chunks = chunking.chunk_chapter(PAGES, 'en', 'graph', chapter=2, min_chars=0)
        self.assertTrue(chunks[0]['text'].startswith('A point'))
        segment = next(c for c in chunks if c['text'].startswith('The shortest path'))
        self.assertIn('MATH6_C0018', segment['concepts'])
        self.assertTrue(any(c['text'].startswith('Imagine') for c in chunks))

    def test_tuned_min_chars_merges_fragments(self):
        loose = chunking.chunk_chapter(PAGES, 'en', 'semantic_tuned', encode=fake_encode, threshold=.99, min_chars=0)
        merged = chunking.chunk_chapter(PAGES, 'en', 'semantic_tuned', encode=fake_encode, threshold=.99, min_chars=200)
        self.assertLess(len(merged), len(loose))

    def test_every_method_gets_the_same_metadata(self):
        required = {'chunk_id', 'language', 'chapter', 'chapter_title', 'section', 'pdf_page', 'printed_page',
                    'char_start', 'char_end', 'char_count', 'token_count', 'truncated_for_embedding', 'concepts',
                    'concept_names', 'primary_concept', 'source_pdf', 'source_sha256', 'citation_url',
                    'method', 'method_params', 'kg_version', 'metadata_version'}
        for method in chunking.METHODS:
            chunks = chunking.chunk_chapter(PAGES, 'en', method, chapter=2, encode=fake_encode)
            for c in chunks:
                self.assertTrue(required <= set(c), (method, required - set(c)))
                self.assertEqual(c['printed_page'], c['pdf_page'] + 12)
                self.assertEqual(c['char_count'], len(c['text']))
                self.assertEqual(c['source_pdf'], 'fegp102.pdf')
            self.assertEqual(len({c['chunk_id'] for c in chunks}), len(chunks), method)
            self.assertEqual(chunks[0]['section'], '2.1 Point', method)

    def test_offsets_point_at_the_chunk_text(self):
        chunks = chunking.chunk_chapter(PAGES, 'en', 'fixed', chapter=2, size=60)
        body = {p['page']: ' '.join(chunking.page_blocks(p['text'])[0]) for p in PAGES}
        for c in chunks:
            self.assertEqual(body[c['pdf_page']][c['char_start']:c['char_end']], c['text'])

    def test_unknown_method(self):
        with self.assertRaises(ValueError):
            chunking.chunk_chapter(PAGES, 'en', 'nope')


if __name__ == '__main__':
    unittest.main()
