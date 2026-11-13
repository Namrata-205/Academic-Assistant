"""Local JSON API and React production server. Run: python server.py."""
import argparse
import json
import mimetypes
import re
import socket
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from diagnostic import engine as e
from diagnostic import textbooks
from diagnostic import imported_reports
from diagnostic import learner_study
from diagnostic.progress import learner_progress
from diagnostic import book_chat
from diagnostic import practice

DOWNLOADS = {'question_bank.json': e.BANK_PATH, **{name: e.ROOT / 'reports' / name for name in (
    'question_bank.csv', 'review_checklist.csv', 'review_notes.md', 'pilot_cases.json',
    'pilot_results.csv', 'pilot_summary.json', 'pilot_error_analysis.md')}}


@contextmanager
def database():
    conn = e.connect()
    try:
        yield conn
    finally:
        conn.close()


def public_question(question):
    if question is None:
        return None
    return {k: question[k] for k in ('id', 'concept_id', 'concept_en', 'concept_hi', 'en', 'hi', 'type')}


def session_view(conn, sid, learner):
    row = conn.execute('SELECT target,method,prior,report FROM sessions WHERE id=? AND learner=? AND version=?', (sid, learner, e.VERSION)).fetchone()
    if not row:
        raise LookupError('Interaction not found for this learner code.')
    target, method, prior_json, saved_report = row
    prior = json.loads(prior_json)
    current = [dict(zip(('question_id', 'concept_id', 'response', 'score'), r), session_id=sid)
               for r in conn.execute('SELECT question_id,concept_id,response,score FROM responses WHERE session_id=? ORDER BY ordinal', (sid,))]
    _, edges = e.load_graph()
    bank = e.load_bank()
    question = None if saved_report else e.select_question(target, bank, edges, current, prior, method)
    report = json.loads(saved_report) if saved_report else None
    if question is None and report is None:
        report = e.make_report(target, bank, edges, current, prior)
        conn.execute('UPDATE sessions SET report=? WHERE id=?', (json.dumps(report, ensure_ascii=False), sid))
        conn.commit()
    if report is not None:
        e.enrich_report(report)
        report['selection_method'] = method
        report['study_plan'] = textbooks.study_plan(report)
    context_row = conn.execute('SELECT payload FROM session_external_context WHERE session_id=?',(sid,)).fetchone()
    context = json.loads(context_row[0]) if context_row else None
    if report is not None and context is not None:
        report['external_context'] = context
    return {'id': sid, 'target': target, 'method': method, 'answered': len(current),
            'question': public_question(question), 'report': report, 'history_count': len(prior),
            'external_context': context}


class Handler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        self.send_bytes(json.dumps(data, ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8', status)

    def send_bytes(self, data, content_type, status=200):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store' if 'json' in content_type else 'no-cache')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path)
        query = parse_qs(path.query)
        try:
            if path.path == '/api/bootstrap':
                nodes, edges = e.load_graph()
                links = [{'id': f'e{i}', 'source': r['source_id'], 'target': r['target_id'],
                          'reasoning': r['reasoning'], 'confidence': r['confidence'],
                          'evidence': r.get('supporting_passage_ids', ''),
                          'status': r.get('validation_status', 'PENDING'),
                          'cycle': r.get('cycle_flag', '').lower() in ('true', '1', 'yes')}
                         for i, r in enumerate(edges)]
                self.send_json({'nodes': list(nodes.values()), 'links': links,
                                'bank': e.load_bank(), 'rules': e.RULES, 'version': e.VERSION,
                                'pilot': json.loads((e.ROOT / 'reports' / 'pilot_summary.json').read_text()),
                                'textbooks': textbooks.catalog()})
            elif path.path.startswith('/api/textbooks/'):
                parts = path.path.split('/')
                if len(parts) != 5:
                    raise LookupError('Textbook not found.')
                _, _, _, language, filename = parts
                if not any(d['language'] == language and d['filename'] == filename for d in textbooks.catalog()['documents']):
                    raise LookupError('Textbook not found.')
                file = e.ROOT / 'assets' / 'textbooks' / language / filename
                self.send_bytes(file.read_bytes(), 'application/pdf')
            elif path.path == '/api/sessions':
                learner = query.get('learner', [''])[0].strip()
                with database() as conn:
                    rows = conn.execute('SELECT id,target,created,report IS NOT NULL FROM sessions WHERE learner=? AND version=? ORDER BY created DESC', (learner, e.VERSION)).fetchall()
                    self.send_json({'sessions': [dict(zip(('id', 'target', 'created', 'complete'), r)) for r in rows],
                                    'response_count': len(e.history(conn, learner))})
            elif path.path == '/api/chat/status':
                self.send_json(book_chat.model_status())
            elif path.path == '/api/chat/threads':
                with database() as conn:
                    self.send_json({'threads':book_chat.threads(conn,query.get('learner',[''])[0].strip())})
            elif path.path.startswith('/api/chat/threads/'):
                with database() as conn:
                    self.send_json({'messages':book_chat.messages(conn,query.get('learner',[''])[0].strip(),path.path.rsplit('/',1)[-1])})
            elif path.path == '/api/progress':
                with database() as conn:
                    self.send_json(learner_progress(conn,query.get('learner',[''])[0].strip()))
            elif path.path == '/api/practice/analytics':
                with database() as conn:self.send_json(practice.analytics(conn,query.get('learner',[''])[0].strip()))
            elif path.path.startswith('/api/practice/sessions/'):
                with database() as conn:self.send_json(practice.view(conn,query.get('learner',[''])[0].strip(),path.path.rsplit('/',1)[-1]))
            elif path.path == '/api/study/export':
                with database() as conn:
                    self.send_json(learner_study.export(conn))
            elif path.path.startswith('/api/concepts/'):
                nodes, edges = e.load_graph()
                self.send_json(e.describe_concept(path.path.rsplit('/',1)[-1],nodes,edges))
            elif path.path == '/api/profiles':
                self.send_json(imported_reports.list_profiles(
                    query.get('search',[''])[0][:100],
                    int(query.get('page',['1'])[0]),
                    query.get('gaps_only',['false'])[0]=='true'))
            elif path.path == '/api/profile':
                learner = query.get('learner',[''])[0]
                with database() as conn:
                    link = conn.execute('SELECT student_id FROM external_profile_links WHERE learner=?',(learner,)).fetchone()
                self.send_json({'profile': imported_reports.profile_summary(imported_reports.get_profile(link[0])) if link else None,
                                'available': imported_reports.STORE.exists()})
            elif path.path.startswith('/api/sessions/'):
                sid = path.path.rsplit('/', 1)[-1]
                with database() as conn:
                    self.send_json(session_view(conn, sid, query.get('learner', [''])[0]))
            elif path.path.startswith('/api/download/'):
                name = unquote(path.path.rsplit('/', 1)[-1])
                file = DOWNLOADS.get(name)
                if file is None or not file.exists():
                    raise LookupError('File not found.')
                self.send_bytes(file.read_bytes(), mimetypes.guess_type(name)[0] or 'application/octet-stream')
            elif path.path.startswith('/api/'):
                raise LookupError('Endpoint not found.')
            else:
                dist = (e.ROOT / 'dist').resolve()
                file = (dist / unquote(path.path).lstrip('/')).resolve()
                if not file.is_relative_to(dist):
                    raise LookupError('File not found.')
                if not file.is_file():
                    file = dist / 'index.html'
                if not file.exists():
                    self.send_bytes(b'React build missing. Run npm install and npm run build.', 'text/plain', 503)
                else:
                    self.send_bytes(file.read_bytes(), mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
        except LookupError as ex:
            self.send_json({'error': str(ex)}, 404)
        except Exception:
            self.send_json({'error': 'Unable to load data. Check the local server logs and source files.'}, 500)

    def do_POST(self):
        try:
            # Local app: reject cross-origin browser mutations. Vite proxy preserves Host.
            origin = self.headers.get('Origin')
            host = self.headers.get('Host', '')
            if origin and urlparse(origin).netloc != host:
                self.send_json({'error': 'Cross-origin requests are not allowed.'}, 403)
                return
            length = int(self.headers.get('Content-Length', 0))
            if length < 1 or length > 65536:
                raise ValueError('Request is empty or too large.')
            body = json.loads(self.rfile.read(length))
            path = urlparse(self.path).path
            if path == '/api/map':
                nodes, edges = e.load_graph()
                mapping=e.map_question(str(body.get('question', ''))[:4000], nodes, edges)
                if mapping['status']=='mapped':
                    mapping['details']=e.describe_concept(mapping['concept_id'],nodes,edges)
                self.send_json(mapping)
                return
            if path == '/api/study/start':
                with database() as conn:
                    sid,learner=learner_study.enrol(conn,body.get('participant_code',''),body.get('target'),body.get('consent'))
                    state=session_view(conn,sid,learner)
                    self.send_json({'session':state,'learner':learner,'protocol':learner_study.PROTOCOL})
                return
            learner = str(body.get('learner', '')).strip()
            if not learner or len(learner) > 100:
                raise ValueError('Enter a learner code of 1–100 characters.')
            with database() as conn:
                if path == '/api/reset':
                    practice.ensure(conn)
                    book_chat.ensure(conn)
                    with conn:
                        for table in ('book_chat_tutoring','book_chat_check_answers','book_chat_practice'):
                            conn.execute(f'DELETE FROM {table} WHERE thread_id IN (SELECT id FROM book_chat_threads WHERE learner=?)',(learner,))
                        conn.execute('DELETE FROM book_chat_messages WHERE thread_id IN (SELECT id FROM book_chat_threads WHERE learner=?)',(learner,))
                        conn.execute('DELETE FROM book_chat_threads WHERE learner=?',(learner,))
                        conn.execute('DELETE FROM responses WHERE session_id IN (SELECT id FROM sessions WHERE learner=?)',(learner,))
                        conn.execute('DELETE FROM session_external_context WHERE session_id IN (SELECT id FROM sessions WHERE learner=?)',(learner,))
                        conn.execute('DELETE FROM sessions WHERE learner=?',(learner,))
                        conn.execute('DELETE FROM external_profile_links WHERE learner=?',(learner,))
                        conn.execute('DELETE FROM practice_items WHERE session_id IN (SELECT id FROM practice_sessions WHERE learner=?)',(learner,))
                        conn.execute('DELETE FROM practice_sessions WHERE learner=?',(learner,))
                    self.send_json({'cleared': True})
                elif path == '/api/chat/message':
                    self.send_json(book_chat.send(conn,learner,body.get('message',''),body.get('language','en'),body.get('thread_id'),body.get('concept_id')))
                elif path == '/api/practice/sessions':
                    self.send_json(practice.create(conn,learner,body.get('concept_id'),body.get('language','en')),201)
                elif path.startswith('/api/practice/sessions/') and path.endswith('/answer'):
                    self.send_json(practice.respond(conn,learner,path.split('/')[-2],body.get('ordinal'),body.get('response','')))
                elif path == '/api/profile/select':
                    student_id=str(body.get('student_id','')).strip()
                    if not student_id or len(student_id)>100:raise ValueError('Choose a learner profile.')
                    self.send_json(imported_reports.select_learning_space(conn,student_id))
                elif path == '/api/profile/link':
                    student_id = str(body.get('student_id','')).strip()
                    if not student_id or len(student_id)>100:
                        raise ValueError('Enter the student ID from your earlier report.')
                    profile = imported_reports.get_profile(student_id)
                    with conn:
                        conn.execute('INSERT OR REPLACE INTO external_profile_links VALUES (?,?)',(learner,student_id))
                    self.send_json({'profile':imported_reports.profile_summary(profile)})
                elif path == '/api/profile/unlink':
                    with conn:
                        conn.execute('DELETE FROM external_profile_links WHERE learner=?',(learner,))
                    self.send_json({'profile':None})
                elif path == '/api/sessions':
                    target = body.get('target')
                    nodes, edges = e.load_graph()
                    if target not in nodes or not e.eligible(target, e.load_bank(), edges):
                        raise ValueError('No diagnostic questions cover this concept or its prerequisites yet.')
                    sid = e.new_session(conn, learner, target, 'graph-guided', e.history(conn, learner))
                    context = imported_reports.linked_context(conn,learner,target,nodes,edges)
                    if context is not None:
                        with conn:
                            conn.execute('INSERT INTO session_external_context VALUES (?,?)',(sid,json.dumps(context,ensure_ascii=False)))
                    self.send_json(session_view(conn, sid, learner), 201)
                elif re.fullmatch(r'/api/sessions/[a-f0-9]{32}/(?:answer|finish)', path):
                    sid = path.split('/')[-2]
                    # Lock before reading the pending item to reject double/stale submissions.
                    conn.execute('BEGIN IMMEDIATE')
                    view = session_view(conn, sid, learner)
                    if view['report']:
                        raise ValueError('This interaction is already complete.')
                    if path.endswith('/answer'):
                        if body.get('question_id') != view['question']['id']:
                            raise ValueError('This question has already been answered. Reload the interaction.')
                        question = next(q for q in e.load_bank() if q['id'] == body['question_id'])
                        response = str(body.get('response', ''))[:1000]
                        e.save_response(conn, sid, question, response)
                    else:
                        conn.execute('UPDATE sessions SET report=? WHERE id=?', (json.dumps(self._finish_report(conn, sid), ensure_ascii=False), sid))
                        conn.commit()
                    self.send_json(session_view(conn, sid, learner))
                else:
                    raise LookupError('Endpoint not found.')
        except (ValueError, json.JSONDecodeError) as ex:
            self.send_json({'error': str(ex)}, 400)
        except LookupError as ex:
            self.send_json({'error': str(ex)}, 404)
        except Exception as ex:
            print(f'API error: {type(ex).__name__}: {ex}')
            self.send_json({'error': 'The request could not be completed. Please try again.'}, 500)

    @staticmethod
    def _finish_report(conn, sid):
        target, prior = conn.execute('SELECT target,prior FROM sessions WHERE id=?', (sid,)).fetchone()
        current = [dict(zip(('question_id', 'concept_id', 'response', 'score'), r), session_id=sid)
                   for r in conn.execute('SELECT question_id,concept_id,response,score FROM responses WHERE session_id=? ORDER BY ordinal', (sid,))]
        return e.make_report(target, e.load_bank(), e.load_graph()[1], current, json.loads(prior))


class LocalHTTPServer(ThreadingHTTPServer):
    def server_bind(self):
        # Windows otherwise permits two copies to share the same listening port.
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            self.allow_reuse_address = False
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    http = LocalHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Concept Atlas: http://127.0.0.1:{args.port}', flush=True)
    http.serve_forever()
