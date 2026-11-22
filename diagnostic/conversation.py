"""Bounded, thread-scoped teaching context; never assessment or account records."""
from contextvars import ContextVar
import json
import re

CURRENT = ContextVar('teaching_conversation', default=())


def feedback(text):
    text = re.sub(r"[’‘]", "'", text.strip().casefold())
    if re.search(r"did(?:n't| not) understand|don(?:'t| not) (?:understand|get it)|(?:cannot|can't|not able to) understand|still (?:confused|lost)|not (?:clear|understood)|samajh?\s*(?:nahi|nahin)|nahi\s*samajh|समझ\s*(?:नहीं|नही)|नहीं\s*(?:आया|समझ)", text):
        return 'still_confused'
    if re.search(r'another example|different example|one more example|एक और उदाहरण|aur example', text):
        return 'another_example'
    if re.search(r'simpler|more simply|easy words|simplify|सरल|आसान भाषा', text):
        return 'simpler'
    return None


def is_followup(text):
    return bool(feedback(text) or re.search(r'\b(?:explain|show) (?:it|that|this)(?: again)?\b',text,re.I) or re.match(
        r'^(?:why\b|how (?:did|does|do|is|can|come)\b|what (?:about|does|do you mean)\b|explain (?:more|again|that|this|simply)|tell me more|and then\b|but\b|क्यों|कैसे|फिर|मतलब)', text.strip(), re.I))


def load(conn, learner, thread):
    if not conn.execute('SELECT 1 FROM book_chat_threads WHERE id=? AND learner=?', (thread, learner)).fetchone():
        return ()
    rows = conn.execute('SELECT role,payload FROM book_chat_messages WHERE thread_id=? ORDER BY rowid DESC LIMIT 8', (thread,)).fetchall()
    turns = []
    for role, raw in reversed(rows):
        payload = json.loads(raw)
        if role == 'user':
            text = payload.get('text', '')
        else:
            text = '\n'.join(filter(None, [payload.get('message', ''), *[p.get('text', '') for p in payload.get('paragraphs', [])]]))
        if text:
            turns.append({'role': role, 'text': text[:1800]})
    return tuple(turns)
