"""Per-learner performance from persisted responses, never inferred target scores."""
import json
import time
from collections import defaultdict
from diagnostic.engine import VERSION


def learner_progress(conn,learner):
    records=conn.execute('SELECT id,target,created,version,report IS NOT NULL FROM sessions WHERE learner=? ORDER BY created DESC,id',(learner,)).fetchall()
    observations=conn.execute('SELECT r.session_id,r.question_id,r.concept_id,r.response,r.score FROM responses r JOIN sessions s ON s.id=r.session_id WHERE s.learner=? ORDER BY r.ordinal',(learner,)).fetchall()
    by_session=defaultdict(list)
    for row in observations:
        by_session[row[0]].append(dict(zip(('question_id','concept_id','response','score'),row[1:])))
    sessions=[];by_concept=defaultdict(list)
    for sid,target,created,version,complete in records:
        answers=by_session[sid]
        valid=[r for r in answers if r['score'] is not None]
        grouped=defaultdict(list)
        for response in answers:grouped[response['concept_id']].append(response)
        concepts=[]
        for cid,rows in grouped.items():
            scored=[r for r in rows if r['score'] is not None]
            attempt={'session_id':sid,'concept_id':cid,'created':created,'version':version,'complete':bool(complete),
                     'asked':len(rows),'correct':sum(r['score']==1 for r in rows),'scorable':len(scored),
                     'unscorable':len(rows)-len(scored),'question_ids':sorted(r['question_id'] for r in rows),
                     'accuracy':round(sum(r['score']==1 for r in scored)/len(scored)*100,1) if scored else None}
            concepts.append(attempt)
            if complete:by_concept[cid].append(attempt)
        sessions.append({'id':sid,'target':target,'created':created,'version':version,'complete':bool(complete),
                         'asked':len(answers),'correct':sum(r['score']==1 for r in answers),
                         'scorable':len(valid),'unscorable':len(answers)-len(valid),
                         'concepts':concepts,'target_assessed':target in grouped})
    trends=[]
    for cid,attempts in by_concept.items():
        recent=[a for a in attempts if a['version']==VERSION and a['scorable']>0][:2]
        delta=None;label='One completed check so far'
        if len(recent)>=2:
            latest,previous=recent
            if latest['question_ids']==previous['question_ids'] and latest['scorable']==previous['scorable'] and latest['scorable']==latest['asked']:
                delta=round(latest['accuracy']-previous['accuracy'],1)
                label='Higher score on the same items' if delta>0 else 'Lower score on the same items' if delta<0 else 'Same score on the same items'
            else:label='Different questions or scoring coverage — compare with care'
        if not recent:label='No scorable completed answers yet'
        trends.append({'concept_id':cid,'attempt_count':len(attempts),'recent':recent,
                       'score_change_percentage_points':delta,'comparison':label})
    return {'sessions':sessions,'concept_trends':sorted(trends,key=lambda r:r['concept_id']),
            'completed_checks':sum(s['complete'] for s in sessions),
            'total_answers':len(observations),'current_version':VERSION,
            'notice':'Scores describe the concepts actually asked, not an untested target. Different items may have different difficulty. Repeated-item gains can reflect familiarity and are not proof of learning.'}


def workspace_progress(conn, learner):
    from diagnostic import daily_problem, learner_evidence, mock_exams, practice, revision

    practice_data = practice.analytics(conn, learner)
    exam_summary = mock_exams.summary(conn, learner)
    exams, active_exam = exam_summary['history'], exam_summary['active']
    review_cards = revision.notebook(conn, learner)
    checks = {'answered': 0, 'scored': 0, 'correct': 0}
    concepts = {}
    for row in learner_evidence.collect(conn, learner, deduplicate=False):
        cid, score, source = row.get('concept_id'), row.get('score'), row['origin']
        if source in ('diagnostic', 'chat_check', 'followup'):
            checks['answered'] += 1
            checks['scored'] += score in (0, 1)
            checks['correct'] += score == 1
        if cid:
            activity = concepts.setdefault(cid, {'answered': 0, 'scored': 0, 'correct': 0})
            activity['answered'] += 1
            activity['scored'] += score in (0, 1)
            activity['correct'] += score == 1
            if score in (0, 1) or 'latest_score' not in activity:
                activity.update(latest_score=score, source=source)
    daily_problem.ensure(conn)
    daily_answers = daily_correct = 0
    topics_attempted = set(concepts)
    for item, attempts, solved in conn.execute(
        'SELECT item,attempts,solved FROM daily_problems WHERE learner=?', (learner,),
    ):
        daily_answers += attempts
        daily_correct += solved
        if attempts:
            topics_attempted.add(json.loads(item)['concept_id'])
    exam_answers = sum(exam['answered'] for exam in exams)
    scored = sum(attempt['scorable'] for attempt in practice_data['attempts']) + checks['scored'] + exam_answers + daily_answers
    correct = sum(attempt['correct'] for attempt in practice_data['attempts']) + checks['correct'] + sum(exam['correct'] for exam in exams) + daily_correct
    return {
        **practice_data,
        'overview': {
            'completed': practice_data['completed_sessions'] + len(exams) + daily_correct,
            'answers': practice_data['total_answers'] + checks['answered'] + exam_answers + daily_answers,
            'accuracy': round(correct / scored * 100, 1) if scored else None,
            'topics': len(topics_attempted),
        },
        'checks': checks,
        'exams': {
            'completed': len(exams), 'recent': exams[:5], 'active': active_exam,
            'refresh_after_ms': max(0, round((active_exam['deadline']-time.time())*1000))
                                if active_exam and active_exam['deadline'] else None,
        },
        'daily': {'solved': daily_correct, 'attempts': daily_answers},
        'revision': {'reviewed': sum(card['reviewed'] for card in review_cards['mistakes']),
                     'completed': sum(card['due'] is None for card in review_cards['mistakes']),
                     'due': review_cards['due_count']},
        'concept_activity': concepts,
    }
