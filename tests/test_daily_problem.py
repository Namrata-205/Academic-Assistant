import tempfile
import unittest
from contextlib import closing
from datetime import date
from pathlib import Path
from unittest.mock import patch

from diagnostic import daily_problem, engine


class DailyProblemTests(unittest.TestCase):
    def test_streak_expiry_and_best(self):
        solved = {date(2026,11,18), date(2026,11,19), date(2026,11,21)}
        self.assertEqual(daily_problem.streaks(solved, date(2026,11,21)), (1,2))
        self.assertEqual(daily_problem.streaks(solved, date(2026,11,22)), (1,2))
        self.assertEqual(daily_problem.streaks(solved, date(2026,11,23)), (0,2))

    def test_solves_once_per_day_and_persists_by_learner(self):
        with tempfile.TemporaryDirectory() as tmp, closing(engine.connect(Path(tmp)/'daily.sqlite3')) as conn:
            day = date(2026,11,21)
            with patch.object(daily_problem,'today',return_value=day):
                item = daily_problem.question_for(day)
                original = daily_problem.view(conn,'first','en')
                wrong = next(choice for choice in ('A','B','C','D') if choice!=item['answer']) if item['type']=='mcq' else str(float(item['answer'])+1)
                failed = daily_problem.answer(conn,'first','en',day.isoformat(),item['id'],wrong)
                self.assertFalse(failed['solved'])
                self.assertIsNone(failed['feedback'])
                self.assertEqual(failed['current_streak'],0)
                solved = daily_problem.answer(conn,'first','en',day.isoformat(),item['id'],item['answer'])
                self.assertEqual(solved['current_streak'],1)
                self.assertTrue(solved['calendar'][-1]['solved'])
                duplicate = daily_problem.answer(conn,'first','hi',day.isoformat(),item['id'],item['answer'])
                self.assertEqual(duplicate['attempts'],2)
                self.assertTrue(duplicate['feedback'])
                self.assertEqual(duplicate['total_solved'],1)
                self.assertFalse(daily_problem.view(conn,'second','en')['solved'])
                self.assertEqual(original['question']['id'],daily_problem.view(conn,'second','en')['question']['id'])
                with self.assertRaises(ValueError):
                    daily_problem.answer(conn,'first','en','2026-11-20',item['id'],item['answer'])
            next_day = date(2026,11,22)
            with patch.object(daily_problem,'today',return_value=next_day):
                item = daily_problem.question_for(next_day)
                self.assertFalse(daily_problem.view(conn,'first','en')['solved'])
                solved = daily_problem.answer(conn,'first','en',next_day.isoformat(),item['id'],item['answer'])
                self.assertEqual((solved['current_streak'],solved['best_streak'],solved['total_solved']),(2,2,2))
