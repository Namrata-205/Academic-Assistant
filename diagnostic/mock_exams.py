"""Timed mock exams with server deadlines and answer keys held until submission."""
import json
import random
import re
from collections import Counter
import time
from uuid import uuid4

from diagnostic import engine, past_papers
from diagnostic.worked_solutions import explanation

from diagnostic.curriculum import CHAPTERS as CURRICULUM_CHAPTERS
CHAPTERS = tuple(row[0] for row in CURRICULUM_CHAPTERS)
MODES = {'mixed': (1800, 20), **{chapter: (480, 4) for chapter in CHAPTERS}}


def ensure(conn):
    past_papers.ensure(conn)
    conn.execute('CREATE TABLE IF NOT EXISTS mock_exam_settings (exam TEXT PRIMARY KEY,pattern_id TEXT,description TEXT)')
    conn.execute("""CREATE TABLE IF NOT EXISTS mock_exams (
        id TEXT PRIMARY KEY, learner TEXT NOT NULL, mode TEXT NOT NULL, language TEXT NOT NULL,
        deadline REAL NOT NULL, finished REAL, reason TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS mock_exam_items (
        exam TEXT NOT NULL, ordinal INTEGER NOT NULL, payload TEXT NOT NULL, response TEXT,
        score INTEGER, PRIMARY KEY (exam, ordinal))""")
    conn.execute('CREATE INDEX IF NOT EXISTS mock_exams_learner ON mock_exams(learner, finished)')


MAX_QUESTIONS = 30
MAX_MINUTES = 180


def format_plan(count, profile):
    counts = (profile or {}).get('format_counts', {})
    supported = {kind: counts.get(kind, 0) for kind in ('mcq','short_answer','diagram')}
    total = sum(supported.values())
    if not total:
        ratio = (profile or {}).get('mcq_ratio', .5) if not counts else .5
        supported = {'mcq':ratio,'short_answer':1-ratio}
        total = 1
    used = Counter()
    for index in range(count):
        kind = max(supported, key=lambda key: (index+1)*supported[key]/total-used[key])
        used[kind] += 1
        yield kind


def question_key(item):
    return (re.split(r'\s+A:\s',item['en'],maxsplit=1)[0],
            json.dumps(item.get('diagram'),sort_keys=True))


def scope(mode):
    return CHAPTERS if mode == 'mixed' else tuple(mode.split(','))


def paper(mode,conn=None,learner=None,profile=None,count=None):
    from diagnostic.learner_evidence import collect
    from diagnostic.exam_questions import make
    nodes,_=engine.load_graph();bank=engine.load_bank()
    chapters = scope(mode)
    count = MODES.get(mode, MODES['mixed'])[1] if count is None else count
    levels = [1]*round(.3*count) + [2]*(count-2*round(.3*count)) + [3]*round(.3*count)
    observations = collect(conn,learner) if conn is not None else []
    missed = Counter(row['concept_id'] for row in observations if row.get('score')==0)
    topics = {topic['concept_id']:topic['count'] for topic in (profile or {}).get('topics', [])}
    seen = {question_key(row['item']) for row in observations if row.get('item') and row['item'].get('en')}
    usage = Counter()
    chapter_concepts = {chapter:list(dict.fromkeys(q['concept_id'] for q in bank
                         if nodes[q['concept_id']]['chapter']==chapter)) for chapter in chapters}
    chapter_order = sorted(chapters, key=lambda chapter: -max(
        (min(missed[cid],3)+min(topics.get(cid,0),3) for cid in chapter_concepts[chapter]), default=0))
    result = []
    assignment = [chapter_order[index%len(chapter_order)] for index in range(count)]
    formats = list(format_plan(count,profile))
    # Move diagram slots onto the angle chapter while keeping chapter coverage.
    diagram_slots = [i for i, kind in enumerate(formats) if kind=='diagram' and assignment[i]!='CH02']
    angle_slots = [i for i, chapter in enumerate(assignment) if chapter=='CH02' and formats[i]!='diagram']
    for diagram, angle in zip(diagram_slots, angle_slots):
        formats[diagram], formats[angle] = formats[angle], formats[diagram]
    for chapter,level,desired in zip(assignment,levels,formats):
        concepts = chapter_concepts[chapter][:]
        random.shuffle(concepts)
        concepts.sort(key=lambda cid:(usage[cid],-min(missed[cid],3)-min(topics.get(cid,0),3)))
        item = None
        if desired=='diagram' and chapter=='CH02':
            from diagnostic.teaching_feedback import angle_item
            rotations = list(range(0,360,5))
            random.shuffle(rotations)
            for rotation in rotations:
                candidate = angle_item(rotation, bool((rotation//5)%2))
                if question_key(candidate) not in seen:
                    item = dict(candidate,difficulty=level,format='diagram')
                    break
        requested_type = 'mcq' if desired=='mcq' else 'numeric'
        for require_type in (True,False):
            if item:
                break
            for cid in concepts:
                for _ in range(20):
                    candidate = make(cid,nodes,level,requested_type=='mcq')
                    if (candidate and question_key(candidate) not in seen
                            and (not require_type or candidate['type']==requested_type)):
                        item = candidate
                        break
                if item:
                    break
        if not item:
            raise ValueError('Not enough fresh questions in this scope. Choose fewer questions or a wider scope.')
        cid = item['concept_id']
        usage[cid] += 1
        item['selection_reason'] = ('review_previous_errors' if missed[cid] else
                                    'past_paper_topic' if cid in topics else 'chapter_coverage')
        seen.add(question_key(item))
        result.append(item)
    return result


def close_exam(conn, exam, finished, reason):
    for ordinal, payload, answer in conn.execute(
            'SELECT ordinal,payload,response FROM mock_exam_items WHERE exam=?', (exam,)):
        score = engine.score(json.loads(payload), answer) if answer else 0
        conn.execute('UPDATE mock_exam_items SET score=? WHERE exam=? AND ordinal=?', (score or 0, exam, ordinal))
    conn.execute('UPDATE mock_exams SET finished=?,reason=? WHERE id=?', (finished, reason, exam))


def expire(conn, learner, now):
    for exam, deadline in conn.execute(
            'SELECT id,deadline FROM mock_exams WHERE learner=? AND finished IS NULL AND deadline>0 AND deadline<=?', (learner, now)):
        close_exam(conn, exam, deadline, 'expired')


def summary(conn, learner):
    ensure(conn)
    with conn:
        conn.execute('BEGIN IMMEDIATE')
        expire(conn, learner, time.time())
        rows = conn.execute("""SELECT e.id,mode,language,deadline,finished,reason,count(i.ordinal),
                    coalesce(sum(i.score),0), count(i.response) FROM mock_exams e JOIN mock_exam_items i ON e.id=i.exam
                    WHERE learner=? GROUP BY e.id ORDER BY e.finished DESC, e.rowid DESC""", (learner,)).fetchall()
    fields = ('id', 'mode', 'language', 'deadline', 'finished', 'reason', 'total', 'correct', 'answered')
    entries = [dict(zip(fields, row)) for row in rows]
    for row in entries:
        row['deadline'] = row['deadline'] or None
        row['chapters'] = scope(row['mode'])
    return {'active': next((row for row in entries if row['finished'] is None), None),
            'history': [row for row in entries if row['finished'] is not None],
            'past_papers':past_papers.list_profiles(conn,learner)}


def create(conn, learner, mode, language,pattern_id=None,question_count=None,minutes=None,chapters=None):
    if language not in ('en','hi'):
        raise ValueError('Choose English or Hindi.')
    if chapters is not None:
        if (not isinstance(chapters,list) or not 1<=len(chapters)<=len(CHAPTERS)
                or any(not isinstance(c,str) or c not in CHAPTERS for c in chapters)
                or len(set(chapters))!=len(chapters)):
            raise ValueError('Choose one or more different curriculum chapters.')
        mode = ','.join(c for c in CHAPTERS if c in chapters)
    elif not isinstance(mode, str) or mode not in MODES:
        raise ValueError('Choose a chapter or a mixed exam.')
    default_duration, default_count = MODES.get(mode, MODES['mixed'])
    count = default_count if question_count is None else question_count
    if type(count) is not int or not 1 <= count <= MAX_QUESTIONS:
        raise ValueError(f'Choose between 1 and {MAX_QUESTIONS} questions.')
    if chapters is not None and count < len(chapters):
        raise ValueError('Choose at least one question per selected chapter.')
    if minutes is not None and (type(minutes) is not int or not 0 <= minutes <= MAX_MINUTES):
        raise ValueError(f'Choose a time from 1 to {MAX_MINUTES} minutes or an untimed exam.')
    if pattern_id is not None and not isinstance(pattern_id,str):
        raise ValueError('Choose a saved past paper.')
    duration = default_duration if minutes is None else minutes*60
    ensure(conn)
    with conn:
        conn.execute('BEGIN IMMEDIATE')
        now = time.time()
        expire(conn, learner, now)
        existing = conn.execute('SELECT id FROM mock_exams WHERE learner=? AND finished IS NULL', (learner,)).fetchone()
        if existing:
            exam = existing[0]
        else:
            profile = past_papers.get(conn,learner,pattern_id) if pattern_id else None
            if profile and profile.get('analysis_status', 'ready') != 'ready':
                raise ValueError('This past paper has no detected question pattern. Choose a different paper or use the standard pattern.')
            questions = paper(mode,conn,learner,profile,count)
            now = time.time()
            exam = uuid4().hex
            conn.execute('INSERT INTO mock_exams VALUES (?,?,?,?,?,NULL,NULL)',
                         (exam, learner, mode, language, now + duration if duration else 0))
            conn.executemany('INSERT INTO mock_exam_items VALUES (?,?,?,NULL,NULL)',
                             [(exam, i, json.dumps(q, ensure_ascii=False)) for i, q in enumerate(questions)])
            conn.execute('INSERT INTO mock_exam_settings VALUES (?,?,?)',(exam,pattern_id,
                'Easy to difficult; prior saved errors guide topic selection. Question drafts are not a mastery test.'))
    return view(conn, learner, exam)


def view(conn, learner, exam, action=None, ordinal=None, answer=None,language=None):
    ensure(conn)
    with conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT mode,language,deadline,finished,reason FROM mock_exams WHERE id=? AND learner=?',
                           (exam, learner)).fetchone()
        if row is None:
            raise LookupError('Exam not found.')
        mode, lang, deadline, finished, reason = row
        if language in ('en','hi'):lang=language
        now = time.time()
        if finished is None:
            expired = bool(deadline and now >= deadline)
            if expired or action == 'submit':
                finished, reason = (deadline, 'expired') if expired else (now, 'submitted')
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
            item = dict(ordinal=index, text=q[lang], type=q['type'], response=response or '',
                        concept_id=q.get('concept_id'),difficulty=q.get('difficulty'),format=q.get('format',q['type']),
                        selection_reason=q.get('selection_reason','chapter_coverage'))
            if q.get('diagram'):
                item['diagram'] = q['diagram']
            if finished is not None:
                item.update(score=score, correct_answer=q['answer'], explanation=explanation(q, lang))
            questions.append(item)
        return dict(id=exam, mode=mode, chapters=scope(mode), language=lang, deadline=deadline or None, server_time=now, finished=finished,
                    reason=reason, questions=questions,
                    correct=sum(q['score'] for q in questions) if finished is not None else None)
