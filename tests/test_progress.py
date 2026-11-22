import tempfile
import unittest
from pathlib import Path
from diagnostic import engine as e
from diagnostic.progress import learner_progress, workspace_progress


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
    def test_workspace_progress_refreshes_from_saved_activity(self):
        from diagnostic import book_chat, daily_problem, mock_exams, practice, revision
        from unittest.mock import patch
        import json

        with tempfile.TemporaryDirectory() as tmp:
            conn=e.connect(Path(tmp)/'workspace.sqlite3')
            try:
                learner='learner-one'
                first=workspace_progress(conn,learner)
                self.assertEqual(first['checks']['answered'],0)
                self.assertEqual(first['exams']['completed'],0)
                self.assertEqual(first['overview'],{'completed':0,'answers':0,'accuracy':None,'topics':0})
                start=book_chat.send(conn,learner,'__continue_angle__:compare','en')
                item=start['message']['practice_question']
                book_chat.send(conn,learner,'__quiz_answer__:'+json.dumps({'question_id':item['id'],'answer':'B'}),
                               'en',start['thread_id'])
                exam=mock_exams.create(conn,learner,'CH02','en',question_count=1,minutes=0)
                mock_exams.view(conn,learner,exam['id'],'submit')
                card=revision.notebook(conn,learner)['daily'][0]
                retry=revision.start(conn,learner,card['id'])
                row=conn.execute('SELECT retry_payload FROM mistake_reviews WHERE learner=?',(learner,)).fetchone()
                revision.answer(conn,learner,card['id'],retry['id'],json.loads(row[0])['answer'])
                fresh=workspace_progress(conn,learner)
                self.assertEqual(fresh['checks'],{'answered':1,'scored':1,'correct':1})
                self.assertEqual(fresh['exams']['recent'][0]['id'],exam['id'])
                self.assertEqual(fresh['revision']['reviewed'],1)
                self.assertEqual(fresh['concept_activity']['MATH6_C0024']['latest_score'],1)
                self.assertEqual(fresh['overview'],{'completed':1,'answers':1,'accuracy':100.0,'topics':1})
                bank_item=next(q for q in e.load_bank() if q['concept_id']=='MATH6_C0003')
                with patch.object(practice,'items',return_value=[dict(bank_item,origin='test')]):
                    attempt=practice.create(conn,learner,'MATH6_C0003','en')
                practice.respond(conn,learner,attempt['id'],0,bank_item['answer'])
                day=daily_problem.today()
                item=daily_problem.question_for(day)
                daily_problem.answer(conn,learner,'en',day.isoformat(),item['id'],item['answer'])
                expected_topics=len({'MATH6_C0024','MATH6_C0003',item['concept_id']})
                self.assertEqual(workspace_progress(conn,learner)['overview'],
                                 {'completed':3,'answers':3,'accuracy':100.0,'topics':expected_topics})
                self.assertEqual(workspace_progress(conn,'learner-two')['overview'],first['overview'])
            finally:
                conn.close()

    def test_workspace_reports_active_exam_and_refreshes_after_deadline(self):
        from contextlib import closing
        from diagnostic import mock_exams
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp, closing(e.connect(Path(tmp)/'expiry.sqlite3')) as conn:
            with patch.object(mock_exams.time,'time',return_value=1000):
                exam=mock_exams.create(conn,'student','CH02','en',question_count=1,minutes=1)
                progress=workspace_progress(conn,'student')
                self.assertEqual(progress['exams']['active']['id'],exam['id'])
                self.assertEqual(progress['exams']['refresh_after_ms'],60000)
            with patch.object(mock_exams.time,'time',return_value=1061):
                progress=workspace_progress(conn,'student')
                self.assertIsNone(progress['exams']['active'])
                self.assertIsNone(progress['exams']['refresh_after_ms'])
                self.assertEqual(progress['exams']['recent'][0]['reason'],'expired')
                self.assertEqual(progress['revision']['due'],1)

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
