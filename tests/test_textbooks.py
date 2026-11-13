import importlib.util
import json
import unittest
from pathlib import Path
from diagnostic import textbooks
from diagnostic.engine import ROOT


class TextbookTests(unittest.TestCase):
    def test_every_graph_concept_has_an_honest_coverage_entry(self):
        from diagnostic.engine import load_graph
        nodes,_=load_graph();cat=textbooks.catalog()
        self.assertEqual(set(nodes),set(cat['concepts']))
        for cid,material in cat['concepts'].items():
            if material['location_verified']:
                self.assertEqual(set(material['versions']),{'en','hi'})
                self.assertIn(material['relation'],('direct','related'))
            else:
                self.assertEqual(material['relation'],'unavailable')
                self.assertEqual(material['versions'],{})
                self.assertTrue(material['reason'])
    def test_catalog_and_links(self):
        catalog=textbooks.catalog()
        self.assertEqual(len(catalog['documents']),22)
        for lang in ('en','hi'):
            self.assertEqual({d['chapter'] for d in catalog['documents'] if d['language']==lang and d['chapter']},set(range(1,11)))
        documents={(d['language'],d['filename']):d for d in catalog['documents']}
        for material in catalog['concepts'].values():
            if material['relation']=='unavailable':
                self.assertFalse(material['location_verified'])
                self.assertEqual(material['versions'],{})
                self.assertTrue(material['reason'])
                continue
            self.assertTrue(material['location_verified'])
            for lang,version in material['versions'].items():
                file=version['practice_url'].split('/')[-1].split('#')[0]
                doc=documents[(lang,file)]
                for field in ('read_pdf_page','practice_pdf_page'):
                    self.assertLessEqual(version[field],doc['pages'])
                    if doc['appended_solutions_start_pdf_page']:
                        self.assertLess(version[field],doc['appended_solutions_start_pdf_page'])
                self.assertTrue((ROOT/'assets'/'textbooks'/lang/file).exists())

    def test_acute_angle_plan_follows_actual_evidence(self):
        report={'target':'MATH6_C0025','concepts':[
            {'concept_id':'MATH6_C0020','assessment':'Assessed','observations':[{'score':1},{'score':0},{'score':0}]},
            {'concept_id':'MATH6_C0025','assessment':'Unassessed','observations':[]},
            {'concept_id':'MATH6_C0024','assessment':'Unassessed','observations':[]},
        ]}
        plan=textbooks.study_plan(report)
        self.assertEqual([p['concept_id'] for p in plan],['MATH6_C0020','MATH6_C0025'])
        self.assertEqual(plan[0]['versions']['en']['read_printed_page'],17)
        self.assertEqual(plan[0]['versions']['en']['practice_printed_page'],19)
        self.assertEqual(plan[1]['versions']['hi']['practice_pdf_page'],19)
        self.assertIn('not checked directly',plan[1]['reason'])

    @unittest.skipUnless(importlib.util.find_spec('fitz'),'PyMuPDF required only for source-verification checks')
    def test_verified_anchors_in_pdf_pages(self):
        import fitz
        anchors=[('en','fegp102.pdf',5,'vertex'),('hi','fhgp102.pdf',5,'शीर्ष'),
                 ('en','fegp102.pdf',7,'name the vertex'),('hi','fhgp102.pdf',7,'शीर्ष'),
                 ('en','fegp102.pdf',19,'acute angles'),('hi','fhgp102.pdf',19,'न्यून'),
                 ('en','fegp103.pdf',6,'Digit sums'),('hi','fhgp103.pdf',6,'योग'),
                 ('en','fegp101.pdf',3,'Odd numbers'),('hi','fhgp101.pdf',3,'विषम')]
        for lang,file,page,anchor in anchors:
            with fitz.open(ROOT/'assets'/'textbooks'/lang/file) as pdf:
                self.assertIn(anchor,pdf[page-1].get_text())


if __name__=='__main__':
    unittest.main()
