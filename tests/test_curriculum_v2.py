import csv
import json
import math
import re
import tempfile
import unittest
from collections import Counter
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch
from diagnostic import engine,extraction,textbooks,mock_exams,practice,revision,book_chat
from diagnostic.curriculum import CHAPTERS
from diagnostic.curriculum_items import make
from diagnostic.upgrade_curriculum import normal


class CurriculumV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nodes,cls.edges=engine.load_graph()

    def test_graph_matches_user_file_and_all_chapters_are_present(self):
        self.assertEqual(engine.graph_source_path().name,'prerequisite_edges_v2.csv')
        with engine.graph_source_path().open(encoding='utf-8-sig') as f:raw=list(csv.DictReader(f))
        self.assertEqual(len(self.edges),len(raw));self.assertEqual(len(self.nodes),144)
        self.assertEqual({n['chapter'] for n in self.nodes.values()},{*[row[0] for row in CHAPTERS],'PRIOR'})
        self.assertTrue(all(n['en'] and n['hi'] for n in self.nodes.values()))
        self.assertTrue(all(not e['confidence_available'] for e in self.edges))

    def test_legacy_item_identity_and_keys_are_preserved(self):
        old=json.loads((engine.ROOT/'diagnostic/question_bank.json').read_text(encoding='utf-8'))
        bank=engine.load_bank();current={q['id']:q for q in bank}
        self.assertEqual(len(bank),432);self.assertEqual({q['concept_id'] for q in bank},set(self.nodes))
        for q in old:
            for key in ('id','concept_id','en','hi','answer','type'):self.assertEqual(q[key],current[q['id']][key])

    def test_every_active_concept_has_in_bounds_bilingual_sources(self):
        cat=textbooks.catalog();pages={};docs={(d['language'],d['filename']):d for d in cat['documents']}
        for cid in self.nodes:
            material=cat['concepts'][cid]
            self.assertEqual(set(material['versions']),{'en','hi'})
            for lang,v in material['versions'].items():
                filename=v['read_url'].split('/')[-1].split('#')[0];doc=docs[(lang,filename)]
                self.assertGreater(v['read_pdf_page'],0);self.assertLessEqual(v['read_pdf_page'],doc['pages'])
                if doc.get('appended_solutions_start_pdf_page'):self.assertLess(v['read_pdf_page'],doc['appended_solutions_start_pdf_page'])
                if v.get('source_match'):
                    key=(lang,filename)
                    if key not in pages:pages[key]={p['page']:p['text'] for p in extraction.get_pages(engine.ROOT/'assets/textbooks'/lang/filename,lang)}
                    self.assertIn(v['verification_anchor'],normal(pages[key][v['read_pdf_page']]))

    def test_all_concepts_have_valid_bilingual_practice_keys(self):
        for cid in self.nodes:
            for seed in (0,17,42):
                q=make(cid,self.nodes,seed)
                self.assertIsNotNone(q,cid);self.assertEqual(engine.score(q,q['answer']),1)
                self.assertRegex(q['hi'],r'[\u0900-\u097f]')
                if q['type']=='mcq':
                    en=dict(re.findall(r'(?:^|; | )([A-D]): (.*?)(?=; [A-D]:|$)',q['en']))
                    hi=dict(re.findall(r'(?:^|; | )([A-D]): (.*?)(?=; [A-D]:|$)',q['hi']))
                    self.assertIn(q['answer'],en);self.assertEqual(set(en),set(hi));self.assertEqual(len(en),len(set(en.values())))
                else:self.assertTrue(math.isfinite(float(q['answer'])))

    def test_fraction_and_integer_examples_have_mathematically_correct_keys(self):
        for seed in range(20):
            q=make('MATH6_C0180',self.nodes,seed);stem=q['en'].split(' A:')[0]
            denominators=[int(x) for x in re.findall(r'1/(\d+)',stem)][:2]
            chosen=re.search(r'(?:^|\s)'+q['answer']+r': (.*?)(?=; [A-D]:|$)',q['en'])[1]
            self.assertEqual(Fraction(chosen),sum((Fraction(1,d) for d in denominators),Fraction(0)))
            q=make('MATH6_C0216',self.nodes,seed);a,b=map(int,re.findall(r'\d+',q['en'])[:2])
            self.assertEqual(int(q['answer']),a+b)

    def test_exams_cover_selected_chapter_and_mixed_covers_all_ten(self):
        for ch,_,_ in CHAPTERS:
            questions=mock_exams.paper(ch)
            self.assertEqual([q['difficulty'] for q in questions],[1,2,2,3])
            self.assertTrue(all(self.nodes[q['concept_id']]['chapter']==ch for q in questions))
        mixed=mock_exams.paper('mixed')
        self.assertEqual(Counter(self.nodes[q['concept_id']]['chapter'] for q in mixed),{ch:2 for ch,_,_ in CHAPTERS})

    def test_new_chapter_mistakes_and_retries_remain_learner_scoped(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn=engine.connect(Path(tmp)/'study.sqlite3')
            try:
                for cid in ('MATH6_C0117','MATH6_C0130','MATH6_C0158','MATH6_C0180','MATH6_C0191','MATH6_C0205','MATH6_C0216'):
                    session=practice.create(conn,'a',cid,'hi')
                    q=json.loads(conn.execute('SELECT payload FROM practice_items WHERE session_id=? AND ordinal=0',(session['id'],)).fetchone()[0])
                    wrong=('B' if q['answer']=='A' else 'A') if q['type']=='mcq' else str(float(q['answer'])+1)
                    practice.respond(conn,'a',session['id'],0,wrong)
                notebook=revision.notebook(conn,'a','hi')
                self.assertEqual(len(notebook['mistakes']),7)
                self.assertFalse(revision.notebook(conn,'b','hi')['mistakes'])
            finally:conn.close()
