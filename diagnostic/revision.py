"""Reviews derive from saved mistakes; spacing and retry grading stay on the server."""
import json
import time
from uuid import uuid4

from diagnostic import chat_tutor, engine, mock_exams, practice
from diagnostic.worked_solutions import explanation

INTERVALS = (86_400, 3 * 86_400)
DAILY_LIMIT = 5


def ensure(conn):
    practice.ensure(conn)
    mock_exams.ensure(conn)
    conn.execute("""CREATE TABLE IF NOT EXISTS mistake_reviews (
        learner TEXT NOT NULL, mistake TEXT NOT NULL, streak INTEGER NOT NULL, due REAL,
        retry_id TEXT, retry_payload TEXT, last_text TEXT, PRIMARY KEY (learner, mistake))""")


def source_rows(conn, learner):
    return conn.execute("""
        SELECT 'practice', s.id, i.ordinal, s.concept_id, s.language, i.payload, i.response,
               CAST(strftime('%s', i.answered) AS REAL) AS missed
        FROM practice_sessions s JOIN practice_items i ON s.id=i.session_id
        WHERE s.learner=? AND i.score=0
        UNION ALL
        SELECT 'exam', e.id, i.ordinal, NULL, e.language, i.payload, i.response, e.finished
        FROM mock_exams e JOIN mock_exam_items i ON e.id=i.exam
        WHERE e.learner=? AND e.finished IS NOT NULL AND i.score=0 AND i.response IS NOT NULL
        ORDER BY missed DESC
        """, (learner, learner))


def entries(conn, learner):
    ensure(conn)
    with conn:
        conn.execute('BEGIN IMMEDIATE')
        now = time.time()
        mock_exams.expire(conn, learner, now)
        rows = source_rows(conn, learner).fetchall()
        states = {row[0]: row[1:] for row in conn.execute(
            'SELECT mistake,streak,due,retry_id,retry_payload,last_text FROM mistake_reviews WHERE learner=?', (learner,))}
    mistakes = []
    for source, session, ordinal, cid, language, payload, answer, _ in rows:
        key = f'{source}-{session}-{ordinal}'
        q = json.loads(payload)
        streak, due, retry_id, retry_payload, last_text = states.get(key, (0, 0, None, None, None))
        mistakes.append((dict(id=key, source=source, concept_id=cid or q['concept_id'], language=language,
                              question=q[language], response=answer, correct_answer=q['answer'],
                              explanation=explanation(q, language), reference=q.get('source'), streak=streak,
                              due=due, ready=due is not None and due <= now),
                         retry_id, retry_payload, last_text))
    return mistakes


def notebook(conn, learner):
    cards = [card for card, *_ in entries(conn, learner)]
    due = sorted((card for card in reversed(cards) if card['ready']), key=lambda card: card['due'])
    return {'mistakes': cards, 'daily': due[:DAILY_LIMIT], 'due_count': len(due)}


def variant(card, last_text):
    cid, language = card['concept_id'], card['language']
    nodes, _ = engine.load_graph()
    for _ in range(16):
        q = chat_tutor.practice(cid, nodes)
        if not q:
            break
        if q[language] not in (card['question'], last_text):
            return q
    for q in engine.load_bank():
        if q['concept_id'] == cid and q[language] not in (card['question'], last_text):
            return q
    for q in practice.items(cid, language, nodes):
        if q[language] not in (card['question'], last_text):
            return q
    raise ValueError('A different question is unavailable for this topic right now.')


def start(conn, learner, key):
    entry = next((row for row in entries(conn, learner) if row[0]['id'] == key), None)
    if entry is None:
        raise LookupError('Mistake not found.')
    card, retry, payload, last_text = entry
    if not card['ready']:
        raise ValueError('This review is not due yet.')
    if payload is None:
        question = variant(card, last_text)
        with conn:
            conn.execute('BEGIN IMMEDIATE')
            if not any(f'{row[0]}-{row[1]}-{row[2]}' == key for row in source_rows(conn, learner)):
                raise LookupError('Mistake not found.')
            # An older request may have generated a variant while another tab graded it.
            conn.execute("""INSERT INTO mistake_reviews VALUES (?,?,0,0,?,?,NULL)
                         ON CONFLICT(learner,mistake) DO UPDATE SET retry_id=excluded.retry_id,
                         retry_payload=excluded.retry_payload WHERE due<=? AND retry_id IS NULL AND last_text IS ?""",
                         (learner, key, uuid4().hex, json.dumps(question, ensure_ascii=False), time.time(), last_text))
            retry, payload = conn.execute('SELECT retry_id,retry_payload FROM mistake_reviews WHERE learner=? AND mistake=?',
                                          (learner, key)).fetchone()
        if not payload:
            raise ValueError('This review is no longer due.')
    q = json.loads(payload)
    return {'id': retry, 'text': q[card['language']], 'type': q['type'], 'language': card['language']}


def answer(conn, learner, key, retry, response):
    if not isinstance(retry, str) or not isinstance(response, str) or not response.strip() or len(response) > 500:
        raise ValueError('Enter a short answer to the review question.')
    entry = next((row for row in entries(conn, learner) if row[0]['id'] == key), None)
    if entry is None:
        raise LookupError('Mistake not found.')
    language = entry[0]['language']
    with conn:
        conn.execute('BEGIN IMMEDIATE')
        saved = conn.execute('SELECT streak,retry_payload FROM mistake_reviews WHERE learner=? AND mistake=? AND retry_id=?',
                             (learner, key, retry)).fetchone()
        if saved is None:
            raise ValueError('This review was already answered. Open the current review.')
        streak, payload = saved
        q = json.loads(payload)
        score = engine.score(q, response)
        if score is None:
            raise ValueError('Enter a number or choose one of the listed options.')
        streak = streak + 1 if score else 0
        now = time.time()
        due = None if streak > len(INTERVALS) else now + (INTERVALS[streak - 1] if streak else 0)
        conn.execute("""UPDATE mistake_reviews SET streak=?,due=?,retry_id=NULL,retry_payload=NULL,last_text=?
                     WHERE learner=? AND mistake=?""", (streak, due, q[language], learner, key))
    return {'correct': bool(score), 'answer': q['answer'], 'explanation': explanation(q, language),
            'streak': streak, 'due': due}
