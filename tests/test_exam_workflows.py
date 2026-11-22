import base64
import json
import unittest
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from diagnostic import engine,practice,mock_exams,past_papers,revision,book_chat,chat_tutor
from diagnostic.exam_questions import make


class ExamWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.conn=engine.connect(Path(self.tmp.name)/'test.db');self.addCleanup(self.conn.close)

    def test_local_paper_profile_is_private_and_formats_new_questions(self):
        text='Previous examination paper\n1. Add two numbers. A: 4 B: 5 C: 6 D: 7\n2. Find a sum. A: 1 B: 2 C: 3 D: 4\n'
        profile=past_papers.upload(self.conn,'a','past.txt',base64.b64encode(text.encode()).decode())
        self.assertEqual(profile['mcq_ratio'],1.)
        self.assertEqual(past_papers.list_profiles(self.conn,'b'),[])
        with self.assertRaises(LookupError):past_papers.get(self.conn,'b',profile['id'])
        with self.assertRaises(LookupError):past_papers.remove(self.conn,'b',profile['id'])
        exam=mock_exams.create(self.conn,'a','CH01','en',profile['id'])
        self.assertEqual([q['difficulty'] for q in exam['questions']],[1,2,2,3])
        self.assertTrue(all(q['type']=='mcq' for q in exam['questions']))
        self.assertNotIn('correct_answer',exam['questions'][0])
        self.assertTrue(all(q['concept_id'] in engine.load_graph()[0] for q in exam['questions']))

    def test_custom_exam_settings_and_detected_topics(self):
        text = (
            '1. Identify the right angle in the diagram.\n'
            '2. Find the difference between a right angle and a straight angle.\n'
            '3. Explain why a right angle measures 90 degrees.\n'
        ).encode()
        profile = past_papers.upload(self.conn, 'a', 'angles.txt', base64.b64encode(text).decode())
        self.assertEqual(profile['format_counts'], {'mcq':0,'short_answer':1,'written':1,'diagram':1})
        self.assertEqual(profile['topics'][0], {'concept_id':'MATH6_C0024','count':3})
        self.assertEqual(past_papers.download(self.conn, 'a', profile['id']), ('angles.txt', text))
        with self.assertRaises(LookupError):
            past_papers.download(self.conn, 'b', profile['id'])
        timed = mock_exams.create(self.conn, 'a', 'CH02', 'en', profile['id'], 5, 17)
        self.assertEqual(len(timed['questions']), 5)
        self.assertAlmostEqual(timed['deadline']-timed['server_time'], 17*60, delta=2)
        self.assertTrue(any(q['format']=='diagram' for q in timed['questions']))
        self.assertTrue(any(q['selection_reason']=='past_paper_topic' for q in timed['questions']))
        mock_exams.view(self.conn, 'a', timed['id'], 'submit')
        untimed = mock_exams.create(self.conn, 'a', 'CH02', 'en', question_count=1, minutes=0)
        self.assertIsNone(untimed['deadline'])
        self.assertEqual(mock_exams.summary(self.conn, 'a')['active']['id'], untimed['id'])
        self.assertEqual(mock_exams.view(self.conn, 'a', untimed['id'], 'submit')['reason'], 'submitted')
        with self.assertRaises(ValueError):
            mock_exams.create(self.conn, 'a', 'CH02', 'en', question_count=31)
        past_papers.remove(self.conn, 'a', profile['id'])
        self.assertEqual(self.conn.execute('SELECT count(*) FROM past_paper_files').fetchone()[0], 0)

    def test_selected_scope_and_reviewable_history(self):
        text = ('1. Identify the right angle in the diagram.\n'
                '2. Identify the straight angle in the diagram.\n').encode()
        profile = past_papers.upload(self.conn, 'a', 'angles.txt', base64.b64encode(text).decode())
        selected = ['CH02','CH05','CH08']
        exam = mock_exams.create(self.conn, 'a', None, 'en', profile['id'], 3, 0, selected)
        nodes, _ = engine.load_graph()
        self.assertEqual(exam['chapters'], tuple(selected))
        self.assertCountEqual([nodes[q['concept_id']]['chapter'] for q in exam['questions']], selected)
        self.assertEqual(sum(q['format']=='diagram' for q in exam['questions']), 1)
        payload = self.conn.execute('SELECT payload FROM mock_exam_items WHERE exam=? AND ordinal=0',
                                    (exam['id'],)).fetchone()[0]
        mock_exams.view(self.conn,'a',exam['id'],'answer',0,json.loads(payload)['answer'])
        mock_exams.view(self.conn,'a',exam['id'],'submit')
        record = mock_exams.summary(self.conn,'a')['history'][0]
        self.assertEqual((record['answered'],record['correct'],record['total'],record['chapters']),
                         (1,1,3,tuple(selected)))
        saved = mock_exams.view(self.conn,'a',record['id'])
        self.assertTrue(all(q['explanation'] and q['correct_answer'] for q in saved['questions']))
        with self.assertRaises(ValueError):
            mock_exams.create(self.conn,'a',None,'en',question_count=1,chapters=selected)
        with self.assertRaises(ValueError):
            mock_exams.create(self.conn,'a',None,'en',chapters=['CH02','CH02'])

    def test_pdf_extraction_and_invalid_files(self):
        import pymupdf
        with pymupdf.open() as pdf:
            page=pdf.new_page();page.insert_text((40,60),'Previous exam questions: 1. Find the sum. A: 2 B: 3 C: 4 D: 5')
            encoded=base64.b64encode(pdf.tobytes()).decode()
        profile=past_papers.upload(self.conn,'a','paper.pdf',encoded)
        self.assertGreater(profile['detected_mcq_blocks'],0)
        for filename,data in [('paper.exe','YWJj'),('paper.txt','not-base64'),('paper.txt','YQ==')]:
            with self.assertRaises(ValueError):past_papers.upload(self.conn,'a',filename,data)

    def test_papers_with_common_question_formats_and_unreadable_scans(self):
        import pymupdf
        numbered = 'Q. No. 1\nFind the measure of a right angle.\n2 – Explain the difference between a right angle and a straight angle.'
        unnumbered = 'Find the measure of a right angle.\nExplain the difference between a right angle and a straight angle.'
        for content in (numbered, unnumbered):
            paper = past_papers.upload(self.conn,'a','paper.txt',base64.b64encode(content.encode()).decode())
            self.assertEqual(paper['analysis_status'],'ready')
            self.assertEqual(paper['detected_questions'],2)
            self.assertEqual(paper['format_counts']['written'],1)
        with pymupdf.open() as pdf:
            pdf.new_page()
            data = pdf.tobytes()
        scan = past_papers.upload(self.conn,'a','scan.pdf',base64.b64encode(data).decode())
        self.assertEqual(scan['analysis_status'],'no_text')
        self.assertEqual(past_papers.download(self.conn,'a',scan['id']),('scan.pdf',data))
        with self.assertRaisesRegex(ValueError,'no detected question pattern'):
            mock_exams.create(self.conn,'a','CH02','en',scan['id'])
        other = past_papers.upload(self.conn,'a','cover.txt',base64.b64encode(b'School exam cover page').decode())
        self.assertEqual(other['analysis_status'],'no_questions')

    def test_learner_errors_change_first_exam_topic(self):
        nodes,_=engine.load_graph();practice.ensure(self.conn)
        for learner,cid in [('a','MATH6_C0003'),('b','MATH6_C0009')]:
            q=next(q for q in engine.load_bank() if q['concept_id']==cid)
            with patch.object(practice,'items',return_value=[dict(q,origin='test')]):s=practice.create(self.conn,learner,cid,'en')
            practice.respond(self.conn,learner,s['id'],0,'99999')
        a=mock_exams.paper('CH01',self.conn,'a');b=mock_exams.paper('CH01',self.conn,'b')
        self.assertEqual(a[0]['concept_id'],'MATH6_C0003')
        self.assertEqual(b[0]['concept_id'],'MATH6_C0009')
        self.assertEqual(a[0]['selection_reason'],'review_previous_errors')

    def test_exam_language_changes_presentation_not_key(self):
        exam=mock_exams.create(self.conn,'a','CH02','en')
        hi=mock_exams.view(self.conn,'a',exam['id'],language='hi')
        self.assertNotEqual(exam['questions'][0]['text'],hi['questions'][0]['text'])
        self.assertEqual(exam['deadline'],hi['deadline'])
        self.assertEqual(hi['language'],'hi')
        payload=self.conn.execute('SELECT payload FROM mock_exam_items WHERE exam=? AND ordinal=0',(exam['id'],)).fetchone()[0]
        mock_exams.view(self.conn,'a',exam['id'],'answer',0,json.loads(payload)['answer'],language='hi')
        done=mock_exams.view(self.conn,'a',exam['id'],'submit',language='hi')
        self.assertEqual(done['questions'][0]['score'],1)
        self.assertEqual(len(revision.notebook(self.conn,'a')['mistakes']),3) # Unanswered questions remain reviewable.

    def test_chat_mistakes_are_revision_cards_with_fresh_retry(self):
        book_chat.ensure(self.conn);bank=engine.load_bank();q=bank[0]
        self.conn.execute('INSERT INTO book_chat_threads VALUES (?,?,?,?,?)',('thread','a','test',q['concept_id'],'2026-01-01T00:00:00+00:00'))
        self.conn.execute('INSERT INTO book_chat_check_answers VALUES (?,?,?,?,?,?,?,?,?)',('thread','attempt',1,q['id'],q['concept_id'],'999',0,engine.VERSION,'2026-01-01T00:00:00+00:00'));self.conn.commit()
        cards=revision.notebook(self.conn,'a','hi')['daily'];self.assertEqual(len(cards),1)
        self.assertEqual(cards[0]['source'],'chat');self.assertEqual(cards[0]['language'],'hi')
        self.assertEqual(revision.notebook(self.conn,'b')['mistakes'],[])
        retry=revision.start(self.conn,'a',cards[0]['id'],'hi')
        self.assertEqual(retry['language'],'hi');self.assertNotIn('answer',retry)
        self.assertNotEqual(cards[0]['question'],retry['text'])


if __name__=='__main__':unittest.main()
