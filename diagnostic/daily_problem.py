"""Server-graded daily practice and per-learner solve streaks."""
import json
from datetime import date, datetime, time, timedelta, timezone

from diagnostic import engine
from diagnostic.worked_solutions import explanation

INDIA = timezone(timedelta(hours=5, minutes=30))
ONE_DAY = timedelta(days=1)
CALENDAR_DAYS = 35


def ensure(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS daily_problems (
        learner TEXT NOT NULL, day TEXT NOT NULL, item TEXT NOT NULL,
        attempts INTEGER NOT NULL, solved INTEGER NOT NULL,
        PRIMARY KEY (learner,day))""")


def today():
    return datetime.now(INDIA).date()


def question_for(day):
    bank = sorted(engine.load_bank(), key=lambda item: item['id'])
    return bank[day.toordinal() % len(bank)]


def streaks(days, day):
    dates = set(days)
    cursor = day if day in dates else day - ONE_DAY
    current = 0
    while cursor in dates:
        current += 1
        cursor -= ONE_DAY
    best = running = 0
    previous = None
    for solved_day in sorted(dates):
        running = running + 1 if previous is not None and solved_day - previous == ONE_DAY else 1
        best = max(best, running)
        previous = solved_day
    return current, best


def stored(conn, learner, day):
    return conn.execute('SELECT item,attempts,solved FROM daily_problems WHERE learner=? AND day=?',
                        (learner, day.isoformat())).fetchone()


def view(conn, learner, language, day=None):
    if language not in ('en','hi'):
        raise ValueError('Choose English or Hindi.')
    ensure(conn)
    day = day or today()
    row = stored(conn, learner, day)
    item, attempts, solved = (json.loads(row[0]), row[1], bool(row[2])) if row else (question_for(day), 0, False)
    dates = {date.fromisoformat(row[0]) for row in conn.execute(
        'SELECT day FROM daily_problems WHERE learner=? AND solved=1 AND day<=?', (learner,day.isoformat()))}
    current, best = streaks(dates, day)
    start = day - timedelta(days=CALENDAR_DAYS-1)
    start -= timedelta(days=start.weekday())
    calendar = [(start+timedelta(days=i)) for i in range((day-start).days+1)]
    question = dict(id=item['id'], text=item[language], type=item['type'], concept_id=item['concept_id'])
    if item.get('diagram'):
        question['diagram'] = item['diagram']
    return dict(day=day.isoformat(), next_reset=datetime.combine(day+ONE_DAY,time.min,INDIA).timestamp(),
                question=question, attempts=attempts, solved=solved,
                feedback=explanation(item,language) if solved else None,
                current_streak=current, best_streak=best, total_solved=len(dates),
                calendar=[dict(day=cell.isoformat(),solved=cell in dates) for cell in calendar])


def answer(conn, learner, language, day, question_id, response):
    if language not in ('en','hi'):
        raise ValueError('Choose English or Hindi.')
    if not isinstance(response,str) or not response.strip() or len(response)>500:
        raise ValueError('Enter a short answer.')
    ensure(conn)
    with conn:
        conn.execute('BEGIN IMMEDIATE')
        current = today()
        if day != current.isoformat():
            raise ValueError('A new daily problem is available. Refresh the problem to continue.')
        row = stored(conn,learner,current)
        item = json.loads(row[0]) if row else question_for(current)
        if item['id'] != question_id:
            raise ValueError('Refresh the daily problem before answering.')
        if not row or not row[2]:
            score = engine.score(item,response)
            if score is None:
                raise ValueError('Enter a number or choose one of the listed options.')
            conn.execute("""INSERT INTO daily_problems VALUES (?,?,?,1,?)
                            ON CONFLICT(learner,day) DO UPDATE SET attempts=attempts+1,solved=excluded.solved""",
                         (learner,current.isoformat(),json.dumps(item,ensure_ascii=False),score))
    return view(conn,learner,language,current)
