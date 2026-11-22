"""Read-only, learner-scoped evidence across activities; no inferred mastery."""
import hashlib
import json
from diagnostic import engine as e


def content_id(item):
    data={key:item.get(key) for key in ('concept_id','en','hi','type','diagram','answer')}
    return hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:24]


def collect(conn,learner,extra=(),*,deduplicate=True):
    result=[]
    if conn is not None:
        tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        dates={(sid,qid):created for sid,qid,created in conn.execute(
            'SELECT s.id,r.question_id,s.created FROM responses r JOIN sessions s ON s.id=r.session_id WHERE s.learner=? AND s.version=?',(learner,e.VERSION))}
        for row in e.history(conn,learner):
            result.append(dict(row,created=dates.get((row.get('session_id'),row['question_id']),''),
                               origin='diagnostic',assessment_eligible=True))
        if {'book_chat_check_answers','book_chat_threads'}<=tables:
            for qid,cid,response,score,created in conn.execute(
                'SELECT a.question_id,a.concept_id,a.response,a.score,a.created FROM book_chat_check_answers a JOIN book_chat_threads t ON t.id=a.thread_id WHERE t.learner=? AND a.version=? ORDER BY a.created,a.ordinal',(learner,e.VERSION)):
                result.append(dict(question_id=qid,concept_id=cid,response=response,score=score,created=created,
                                   origin='chat_check',assessment_eligible=True))
        if {'book_chat_tutor_events','book_chat_threads'}<=tables:
            for payload,created in conn.execute(
                "SELECT a.payload,a.created FROM book_chat_tutor_events a JOIN book_chat_threads t ON t.id=a.thread_id WHERE t.learner=? AND a.kind='followup_answer' ORDER BY a.created",(learner,)):
                row=json.loads(payload)
                if row.get('version')==e.VERSION:
                    result.append(dict(row,created=created,origin='followup',assessment_eligible=False))
        if {'practice_sessions','practice_items'}<=tables:
            for payload,response,score,created,version,cid in conn.execute(
                'SELECT i.payload,i.response,i.score,i.answered,s.version,s.concept_id FROM practice_items i JOIN practice_sessions s ON s.id=i.session_id WHERE s.learner=? AND i.answered IS NOT NULL ORDER BY i.answered,i.ordinal',(learner,)):
                if version!='topic-practice-v1':continue
                item=json.loads(payload);item.setdefault('concept_id',cid)
                result.append(dict(question_id=item.get('id',content_id(item)),concept_id=item.get('concept_id'),
                                   response=response,score=score,created=created,origin='topic_practice',
                                   content_id=content_id(item),item=item,assessment_eligible=False))
        if {'mock_exams','mock_exam_items'}<=tables:
            for payload,response,score,finished in conn.execute(
                'SELECT i.payload,i.response,i.score,s.finished FROM mock_exam_items i JOIN mock_exams s ON s.id=i.exam WHERE s.learner=? AND s.finished IS NOT NULL AND i.response IS NOT NULL ORDER BY s.finished,i.ordinal',(learner,)):
                from datetime import datetime,timezone
                item=json.loads(payload);created=datetime.fromtimestamp(finished,timezone.utc).isoformat()
                result.append(dict(question_id=item.get('id',content_id(item)),concept_id=item.get('concept_id'),
                                   response=response,score=score,created=created,origin='mock_exam',
                                   content_id=content_id(item),item=item,assessment_eligible=False))
    # Old in-flight callers may also provide rows already collected above.
    known={(r['question_id'],r.get('response'),r.get('score')) for r in result}
    for row in extra:
        if (row['question_id'],row.get('response'),row.get('score')) not in known:
            result.append(dict(row,created=row.get('created',''),origin=row.get('origin','chat_check'),
                               assessment_eligible=row.get('assessment_eligible',row.get('origin')!='followup')))
    result.sort(key=lambda r:r.get('created',''))
    if not deduplicate:
        return result
    unique={}
    for row in result:
        if row.get('item') and not row.get('assessment_eligible',True):
            row['content_id']=content_id(row['item'])
        key=(row.get('content_id',row['question_id']),row['assessment_eligible'])
        unique.pop(key,None);unique[key]=row
    return list(unique.values())


def next_step(conn, learner):
    nodes, _ = e.load_graph()
    seen = set()
    for row in reversed(collect(conn, learner)):
        cid = row.get('concept_id')
        if cid not in nodes or cid in seen or (row.get('score') not in (0,1) and row['origin']!='followup'):
            continue
        seen.add(cid)
        if row['origin'] == 'followup':
            return dict(concept_id=cid, reason='followup_correct' if row['score']==1 else 'followup_review',
                        angle_contrast=bool(row.get('item', {}).get('diagram') or row.get('item', {}).get('comparison')) and cid=='MATH6_C0024')
        if row['score'] == 0:
            return dict(concept_id=cid, reason='recent_miss')
    return None


def assessment(rows):
    return [r for r in rows if r.get('assessment_eligible',r.get('origin') not in ('followup','topic_practice','mock_exam'))]
