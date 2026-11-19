import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from diagnostic import engine, mock_exams, practice, revision

LEARNER = 'learner-review-test'


class StudyToolsTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.conn = engine.connect(Path(self.directory.name) / 'history.sqlite3')
        self.addCleanup(self.conn.close)

    def test_historical_mistake_has_worked_solution_and_spaced_retries(self):
        original = engine.load_bank()[0]
        with patch.object(practice, 'items', return_value=[dict(original, origin='test')]):
            session = practice.create(self.conn, LEARNER, original['concept_id'], 'en')
        practice.respond(self.conn, LEARNER, session['id'], 0, '99999')

        notebook = revision.notebook(self.conn, LEARNER)
        card = notebook['daily'][0]
        self.assertEqual(card['response'], '99999')
        self.assertIn('12 + 3 = 15', card['explanation'])
        self.assertEqual(revision.notebook(self.conn, 'other')['mistakes'], [])
        correct = []
        for round_number in range(3):
            question = revision.start(self.conn, LEARNER, card['id'])
            self.assertNotEqual(card['question'], question['text'])
            self.assertEqual(revision.start(self.conn, LEARNER, card['id']), question)
            self.assertNotIn('answer', question)
            payload = self.conn.execute('SELECT retry_payload FROM mistake_reviews').fetchone()[0]
            result = revision.answer(self.conn, LEARNER, card['id'], question['id'], json.loads(payload)['answer'])
            correct.append(result['streak'])
            with self.assertRaises(ValueError):
                revision.answer(self.conn, LEARNER, card['id'], question['id'], '15')
            if round_number < 2:
                self.assertEqual(revision.notebook(self.conn, LEARNER)['daily'], [])
                with self.assertRaises(ValueError):
                    revision.start(self.conn, LEARNER, card['id'])
                with self.conn:
                    self.conn.execute('UPDATE mistake_reviews SET due=0')
        self.assertEqual(correct, [1, 2, 3])
        self.assertIsNone(revision.notebook(self.conn, LEARNER)['mistakes'][0]['due'])

    def test_exam_counts_down_saved_answers_and_expires_once(self):
        with patch.object(mock_exams.time, 'time', return_value=1000):
            initial = mock_exams.create(self.conn, LEARNER, 'mixed', 'hi')
            exam = initial['id']
            self.assertEqual(initial['deadline'], 1720)
            self.assertEqual(len(initial['questions']), 6)
            self.assertNotIn('correct_answer', initial['questions'][0])
            with self.assertRaises(LookupError):
                mock_exams.view(self.conn, 'other', exam)
            self.assertEqual(mock_exams.create(self.conn, LEARNER, 'CH02', 'en')['id'], exam)
            wrong = '99999' if initial['questions'][0]['type'] == 'numeric' else 'Z'
            saved = mock_exams.view(self.conn, LEARNER, exam, 'answer', 0, wrong)
            self.assertEqual(saved['questions'][0]['response'], wrong)
        with patch.object(mock_exams.time, 'time', return_value=1721):
            expired = mock_exams.view(self.conn, LEARNER, exam, 'answer', 0, 'A')
            self.assertEqual(expired['questions'][0]['response'], wrong)
            self.assertEqual(expired['finished'], 1720)
            self.assertEqual(expired['reason'], 'expired')
            self.assertEqual(expired['correct'], 0)
            self.assertIn('correct_answer', expired['questions'][0])
            self.assertIsNone(mock_exams.summary(self.conn, LEARNER)['active'])
            self.assertEqual(mock_exams.view(self.conn, LEARNER, exam, 'submit')['reason'], 'expired')
            self.assertEqual(revision.notebook(self.conn, LEARNER)['daily'][0]['source'], 'exam')

    def test_all_papers_can_be_built(self):
        for mode, (_, count) in mock_exams.MODES.items():
            with self.subTest(mode=mode):
                questions = mock_exams.paper(mode)
                self.assertEqual(len(questions), count)
                self.assertEqual(len({q['en'] for q in questions}), count)
