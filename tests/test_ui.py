"""Streamlit interaction smoke test; uses an isolated temporary database."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from diagnostic import engine as e


@unittest.skipUnless(importlib.util.find_spec('streamlit'), 'Run with the project venv for Streamlit UI checks')
class UIIntegrationTests(unittest.TestCase):
    def test_diagnostic_save_report_resume_and_review(self):
        from streamlit.testing.v1 import AppTest

        def click(app, label):
            next(b for b in app.button if b.label == label).click().run()
            self.assertFalse(app.exception, str(app.exception))

        original_connect = e.connect
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / 'history.sqlite3'
            with patch('diagnostic.engine.connect', side_effect=lambda: original_connect(db)):
                at = AppTest.from_file(str(e.ROOT / 'app.py')).run(timeout=30)
                at.radio[0].set_value('Diagnostic').run()
                at.text_input[0].set_value('test-learner').run()
                at.text_area[0].set_value('Help with place value.')
                click(at, 'Identify concept')
                click(at, 'Start a new three-question diagnostic')
                for answer in ('not sure',)*3:
                    at.text_input[-1].set_value(answer)
                    click(at, 'Submit response')
                self.assertTrue(any('Diagnostic report' in h.value for h in at.subheader))
                conn = original_connect(db)
                sid, report = conn.execute('SELECT id,report FROM sessions').fetchone()
                self.assertEqual(json.loads(report)['question_count'], 3)
                self.assertEqual(len(e.history(conn, 'test-learner')), 3)
                conn.close()
                reopened = AppTest.from_file(str(e.ROOT / 'app.py')).run(timeout=30)
                reopened.radio[0].set_value('Diagnostic').run()
                reopened.text_input[0].set_value('test-learner').run()
                reopened.selectbox[0].set_value(sid).run()
                click(reopened, 'Open saved interaction')
                self.assertTrue(any('Diagnostic report' in h.value for h in reopened.subheader))
                reopened.text_area[0].set_value('What about algebra?')
                click(reopened, 'Identify concept')
                self.assertTrue(any('Clarify the intended concept' in s.label for s in reopened.selectbox))
                reopened.radio[0].set_value('Review & pilot').run()
                self.assertFalse(reopened.exception, str(reopened.exception))


if __name__ == '__main__':
    unittest.main()
