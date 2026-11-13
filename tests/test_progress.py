import tempfile
import unittest
from pathlib import Path
from diagnostic import engine as e
from diagnostic.progress import learner_progress


class ProgressTests(unittest.TestCase):
    def test_persisted_scores_compare_actual_checked_concepts_and_isolate_learners(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'history.sqlite3';conn=e.connect(path)
            q=next(q for q in e.load_bank() if q['id']=='DQ_0003_1')
            for answer in ('16','15'):
                sid=e.new_session(conn,'learner-one','MATH6_C0006','graph-guided',[])
                e.save_response(conn,sid,q,answer)
                with conn:conn.execute('UPDATE sessions SET report=? WHERE id=?',('{}',sid))
            sid=e.new_session(conn,'learner-two','MATH6_C0006','graph-guided',[])
            e.save_response(conn,sid,q,'not sure')
            conn.close();conn=e.connect(path)
            try:
                progress=learner_progress(conn,'learner-one')
                self.assertEqual(progress['completed_checks'],2)
                self.assertEqual(progress['total_answers'],2)
                self.assertFalse(progress['sessions'][0]['target_assessed'])
                self.assertEqual(progress['concept_trends'][0]['concept_id'],'MATH6_C0003')
                self.assertEqual(progress['concept_trends'][0]['score_change_percentage_points'],100)
                self.assertIn('same items',progress['concept_trends'][0]['comparison'])
                other=learner_progress(conn,'learner-two')
                self.assertEqual(other['total_answers'],1)
                self.assertEqual(other['sessions'][0]['unscorable'],1)
            finally:conn.close()
    def test_different_items_are_not_labelled_improvement(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn=e.connect(Path(tmp)/'history.sqlite3');bank=e.load_bank()
            try:
                for qid,answer in [('DQ_0038_1','401'),('DQ_0038_2','700')]:
                    sid=e.new_session(conn,'learner','MATH6_C0038','graph-guided',[])
                    e.save_response(conn,sid,next(q for q in bank if q['id']==qid),answer)
                    with conn:conn.execute('UPDATE sessions SET report=? WHERE id=?',('{}',sid))
                trend=learner_progress(conn,'learner')['concept_trends'][0]
                self.assertIsNone(trend['score_change_percentage_points'])
                self.assertIn('Different questions',trend['comparison'])
            finally:conn.close()


if __name__=='__main__':unittest.main()
