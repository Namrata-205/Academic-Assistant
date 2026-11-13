"""Per-learner performance from persisted responses, never inferred target scores."""
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
