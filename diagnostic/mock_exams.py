"""Timed mock exams with server deadlines and answer keys held until submission."""
import json
import random
import time
from uuid import uuid4

from diagnostic import chat_tutor, engine, practice
from diagnostic.worked_solutions import explanation

CHAPTERS = ('CH01', 'CH02', 'CH03')
MODES = {'mixed': (720, 6), **{chapter: (480, 4) for chapter in CHAPTERS}}


def ensure(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS mock_exams (
        id TEXT PRIMARY KEY, learner TEXT NOT NULL, mode TEXT NOT NULL, language TEXT NOT NULL,
        deadline REAL NOT NULL, finished REAL, reason TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS mock_exam_items (
        exam TEXT NOT NULL, ordinal INTEGER NOT NULL, payload TEXT NOT NULL, response TEXT,
        score INTEGER, PRIMARY KEY (exam, ordinal))""")
    conn.execute('CREATE INDEX IF NOT EXISTS mock_exams_learner ON mock_exams(learner, finished)')


def paper(mode):
    nodes, _ = engine.load_graph()
    bank = engine.load_bank()
    chapters = CHAPTERS if mode == 'mixed' else (mode,)
    count = MODES[mode][1] // len(chapters)
    result = []
    for chapter in chapters:
        concepts = list(dict.fromkeys(q['concept_id'] for q in bank if nodes[q['concept_id']]['chapter'] == chapter))
        random.shuffle(concepts)
        candidates = []
        for cid in concepts:
            question = chat_tutor.practice(cid, nodes)
            if question:
                candidates.append(question)
        seen = {q['en'] for q in candidates}
        # Short chapters have fewer concepts. Generate a second variation before using bank items.
        for cid in concepts:
            if len(candidates) >= count:
                break
            for _ in range(12):
                question = chat_tutor.practice(cid, nodes)
                if not question:
                    break
                if question['en'] not in seen:
                    seen.add(question['en'])
                    candidates.append(question)
                    break
        if len(candidates) < count:
            extras = [q for q in bank if q['concept_id'] in concepts and q['en'] not in seen]
            random.shuffle(extras)
            candidates.extend(extras)
        result.extend(candidates[:count])
    return result


def close_exam(conn, exam, finished, reason):
    for ordinal, payload, answer in conn.execute(
            'SELECT ordinal,payload,response FROM mock_exam_items WHERE exam=?', (exam,)):
        score = engine.score(json.loads(payload), answer) if answer else 0
        conn.execute('UPDATE mock_exam_items SET score=? WHERE exam=? AND ordinal=?', (score or 0, exam, ordinal))
    conn.execute('UPDATE mock_exams SET finished=?,reason=? WHERE id=?', (finished, reason, exam))


def expire(conn, learner, now):
    for exam, deadline in conn.execute(
            'SELECT id,deadline FROM mock_exams WHERE learner=? AND finished IS NULL AND deadline<=?', (learner, now)):
        close_exam(conn, exam, deadline, 'expired')


def summary(conn, learner):
    ensure(conn)
    with conn:
        conn.execute('BEGIN IMMEDIATE')
        expire(conn, learner, time.time())
        rows = conn.execute("""SELECT e.id,mode,language,deadline,finished,reason,count(i.ordinal),
                    coalesce(sum(i.score),0) FROM mock_exams e JOIN mock_exam_items i ON e.id=i.exam
                    WHERE learner=? GROUP BY e.id ORDER BY deadline DESC""", (learner,)).fetchall()
    fields = ('id', 'mode', 'language', 'deadline', 'finished', 'reason', 'total', 'correct')
    entries = [dict(zip(fields, row)) for row in rows]
    return {'active': next((row for row in entries if row['finished'] is None), None),
            'history': [row for row in entries if row['finished'] is not None]}


def create(conn, learner, mode, language):
    if not isinstance(mode, str) or mode not in MODES or language not in ('en', 'hi'):
        raise ValueError('Choose an exam and English or Hindi.')
    ensure(conn)
    questions = paper(mode)
    if len(questions) != MODES[mode][1]:
        raise ValueError('This paper does not have enough questions yet.')
    with conn:
        conn.execute('BEGIN IMMEDIATE')
        now = time.time()
        expire(conn, learner, now)
        existing = conn.execute('SELECT id FROM mock_exams WHERE learner=? AND finished IS NULL', (learner,)).fetchone()
        if existing:
            exam = existing[0]
        else:
            exam = uuid4().hex
            conn.execute('INSERT INTO mock_exams VALUES (?,?,?,?,?,NULL,NULL)',
                         (exam, learner, mode, language, now + MODES[mode][0]))
            conn.executemany('INSERT INTO mock_exam_items VALUES (?,?,?,NULL,NULL)',
                             [(exam, i, json.dumps(q, ensure_ascii=False)) for i, q in enumerate(questions)])
    return view(conn, learner, exam)


def view(conn, learner, exam, action=None, ordinal=None, answer=None):
    ensure(conn)
    with conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT mode,language,deadline,finished,reason FROM mock_exams WHERE id=? AND learner=?',
                           (exam, learner)).fetchone()
        if row is None:
            raise LookupError('Exam not found.')
        mode, lang, deadline, finished, reason = row
        now = time.time()
        if finished is None:
            if now >= deadline or action == 'submit':
                finished, reason = (deadline, 'expired') if now >= deadline else (now, 'submitted')
                close_exam(conn, exam, finished, reason)
            elif action == 'answer':
                if type(ordinal) is not int or not isinstance(answer, str) or len(answer) > 500:
                    raise ValueError('Enter a short answer for a question on this paper.')
                changed = conn.execute('UPDATE mock_exam_items SET response=? WHERE exam=? AND ordinal=?',
                                       (answer.strip() or None, exam, ordinal)).rowcount
                if not changed:
                    raise LookupError('Exam question not found.')
        questions = []
        for index, payload, response, score in conn.execute(
                'SELECT ordinal,payload,response,score FROM mock_exam_items WHERE exam=? ORDER BY ordinal', (exam,)):
            q = json.loads(payload)
            item = dict(ordinal=index, text=q[lang], type=q['type'], response=response or '')
            if finished is not None:
                item.update(score=score, correct_answer=q['answer'], explanation=explanation(q, lang))
            questions.append(item)
        return dict(id=exam, mode=mode, language=lang, deadline=deadline, server_time=now, finished=finished,
                    reason=reason, questions=questions,
                    correct=sum(q['score'] for q in questions) if finished is not None else None)
