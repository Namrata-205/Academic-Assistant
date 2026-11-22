"""Deterministic mapping, selection, scoring, reports, and local persistence."""
import csv
import json
import re
import sqlite3
import unicodedata
import zipfile
import posixpath
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
VERSION = 'diagnostic-v1'
STATUS_CODES = {'Evidence supports understanding': 1, 'Possible prerequisite difficulty': 2,
                'Insufficient evidence': 3}
BANK_PATH = ROOT / 'diagnostic' / 'question_bank_v2.json'
RULES = ('Maximum 3 new questions. Eligible concepts: target plus direct incoming '
         'prerequisites with bank items; exclude self-loops. Fixed: concept ID then item ID. '
         'Graph-guided: finish checking a concept with one valid observation first; '
         'otherwise direct prerequisites before target, descending graph confidence, '
         'then concept ID. Pick the lowest unused item ID. Use at most two most recent '
         'same-version historical observations per concept, never repeat their items. '
         'Stop when budget exhausted or no unresolved eligible item remains. '
         'Two correct and no incorrect: understanding; two incorrect and no correct: '
         'possible difficulty; mixed, one observation, or no valid observations: insufficient. '
         'Invalid answers consume a question but supply no knowledge evidence. '
         'Untested in this interaction remains unassessed even if historical evidence exists.')


def normalize(value):
    value = unicodedata.normalize('NFKC', str(value)).lower().strip()
    return ''.join(str(unicodedata.digit(c)) if c.isdigit() else c for c in value)


def graph_source_path():
    directory=ROOT/'assets'/'NCERT_Knowledge_Graph'
    for name in ('prerequisite_edges_v2.csv','prerequisite_edges.csv','prerequisite_edges.xlsx'):
        if (directory/name).exists():return directory/name
    raise FileNotFoundError('Graph source missing: expected prerequisite_edges.csv or prerequisite_edges.xlsx.')


def load_graph_rows(path=None):
    path=Path(path) if path is not None else graph_source_path()
    if path.suffix.lower()=='.csv':
        with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
    # Read the first Excel worksheet using standard-library OOXML support.
    # Preserve the workbook and use no Excel installation or authoring dependency.
    ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(path) as z:
        strings=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            strings=[''.join(n.itertext()) for n in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',ns)]
        workbook=ET.fromstring(z.read('xl/workbook.xml'))
        first=workbook.find('m:sheets/m:sheet',ns)
        rid=first.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
        rel=next(r for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels')) if r.attrib['Id']==rid)
        target=rel.attrib['Target']
        sheet=target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join('xl',target))
        rows=[]
        for row in ET.fromstring(z.read(sheet)).findall('m:sheetData/m:row',ns):
            values={}
            for cell in row.findall('m:c',ns):
                col=0
                for letter in re.match(r'[A-Z]+',cell.attrib['r'])[0]:col=col*26+ord(letter)-64
                value=cell.find('m:v',ns)
                text=value.text or '' if value is not None else ''
                if cell.attrib.get('t')=='s':text=strings[int(text)] if text else ''
                elif cell.attrib.get('t')=='inlineStr':text=''.join(cell.find('m:is',ns).itertext())
                elif cell.attrib.get('t')=='b':text='True' if text=='1' else 'False'
                values[col-1]=text
            rows.append(values)
        if not rows:return []
        width=max(rows[0])+1;headers=[rows[0].get(i,'').strip() for i in range(width)]
        return [{key:row.get(i,'') for i,key in enumerate(headers) if key} for row in rows[1:] if any(row.values())]


def load_graph():
    edges=load_graph_rows()
    nodes = {}
    for e in edges:
        e['confidence_available']=bool(str(e.get('confidence','')).strip())
        e['confidence']=e.get('confidence') or '0'
        for side in ('source', 'target'):
            key = e[side + '_id']
            node={'id':key,'en':e[side+'_en'],'hi':e[side+'_hi'],'chapter':e[side+'_chapter']}
            if key in nodes and nodes[key]!=node:raise ValueError('Conflicting graph labels for '+key)
            nodes[key]=node
    return nodes, edges


def load_bank():
    return json.loads(BANK_PATH.read_text(encoding='utf-8'))


def references(edge):
    return {'passage_ids': edge.get('supporting_passage_ids', ''),
            'validation_status': edge.get('validation_status', 'PENDING'),
            'source_text_verified': False}


def prerequisites(target, edges):
    return sorted({e['source_id'] for e in edges
                   if e['target_id'] == target and e['source_id'] != target})


def describe_concept(target, nodes, edges):
    """Structured concept, incoming graph prerequisites and verified book locations."""
    from diagnostic.textbooks import catalog
    if target not in nodes:
        raise LookupError('Concept not found.')
    material = catalog().get('concepts', {})
    def describe(cid):
        return dict(nodes[cid], textbook=material.get(cid),
                    graph_references=[references(r) for r in edges
                                      if r['source_id'] == cid and r['target_id'] == target])
    return {'concept': describe(target),
            'prerequisites': [describe(cid) for cid in prerequisites(target, edges)],
            'graph_review': 'Proposed prerequisite relationships; human review pending.'}


def enrich_report(report):
    """Also supports older saved reports without altering their recorded diagnoses."""
    from diagnostic.textbooks import catalog
    material = catalog().get('concepts', {})
    for row in report['concepts']:
        row['status_code'] = STATUS_CODES.get(row['status']) if row['assessment'] == 'Assessed' else None
        row['textbook'] = material.get(row['concept_id'])
    report['decision_rule_review'] = {'status': 'PENDING human review',
                                      'first_ai_review': 'Completed; not independent human validation'}
    return report


def legacy_map_question(text, nodes, edges):
    """Conservative whole-term mapper; lexical matches are not probabilities."""
    text = normalize(text)
    if not text:
        return {'status': 'clarify', 'candidates': [], 'reason': 'Enter a question in English or Hindi.'}
    aliases = {'MATH6_C0024': ['90 degree angle', '90° angle', '90 डिग्री का कोण'],
               'MATH6_C0025': ['less than 90 degrees', '90 डिग्री से कम'],
               'MATH6_C0038': ['value of the digit', 'अंक का स्थानीय मान'],
               'MATH6_C0039': ['sum of digits', 'sum of the digits'],
               'MATH6_C0003': ['number series', 'संख्या श्रृंखला']}
    hits = []
    for key, node in nodes.items():
        from diagnostic.curriculum import search_terms
        terms = [*search_terms(node), *aliases.get(key, [])]
        if node['en'].endswith('number'):
            terms.append(node['en'] + 's')
        matches = [t for t in terms if re.search(r'(?<!\w)' + re.escape(normalize(t)) + r'(?!\w)', text)]
        if matches:
            hits.append((key, max(matches, key=len)))
    # Suppress generic substrings, such as "angle" inside "right angle".
    hits = [(k, term) for k, term in hits if not any(
        normalize(term) != normalize(other) and normalize(term) in normalize(other)
        for _, other in hits)]
    candidates = sorted({k for k, _ in hits})
    if len(candidates) != 1:
        return {'status': 'clarify', 'candidates': candidates,
                'reason': 'Choose the intended concept/chapter or rephrase using a concept name. '
                          'No reliable unique lexical match.'}
    target = candidates[0]
    return {'status': 'mapped', 'concept_id': target, 'candidates': candidates,
            'method': 'unique explicit bilingual term/alias (not semantic certainty)',
            'prerequisites': prerequisites(target, edges),
            'references': [references(e) for e in edges if e['target_id'] == target]}


def map_question(text, nodes, edges):
    from diagnostic.semantic_mapper import mapping
    result=mapping(str(text)[:4000],nodes)
    if result['status']=='mapped':
        result['prerequisites']=prerequisites(result['concept_id'],edges)
        result['references']=[references(e) for e in edges if e['target_id']==result['concept_id']]
    return result


def score(question, response):
    value = normalize(response)
    if question['type'] == 'mcq':
        value = value.upper()
        if value not in ('A', 'B', 'C', 'D'):
            return None
        return int(value == question['answer'])
    if not re.fullmatch(r'[+-]?\d+(?:\.\d+)?', value):
        return None
    return int(float(value) == float(question['answer']))


def status(observations):
    valid = [r['score'] for r in observations if r['score'] is not None]
    if len(valid) >= 2 and all(s == 1 for s in valid):
        return 'Evidence supports understanding'
    if len(valid) >= 2 and all(s == 0 for s in valid):
        return 'Possible prerequisite difficulty'
    return 'Insufficient evidence'


def eligible(target, bank, edges):
    assessed = {q['concept_id'] for q in bank}
    return [c for c in prerequisites(target, edges) if c in assessed] + ([target] if target in assessed else [])


def select_question(target, bank, edges, current, prior=(), method='graph-guided'):
    if len(current) >= 3:
        return None
    concepts = eligible(target, bank, edges)
    confidence = {c: max([float(e.get('confidence') or 0) for e in edges
                         if e['source_id'] == c and e['target_id'] == target] or [0]) for c in concepts}
    evidence = {}
    for c in concepts:
        evidence[c] = [r for r in prior if r['concept_id'] == c][-2:] + [r for r in current if r['concept_id'] == c]
    used = {r['question_id'] for rows in evidence.values() for r in rows}
    if method == 'fixed':
        ordered = sorted(bank, key=lambda q: (q['concept_id'], q['id']))
    else:
        def rank(c):
            valid = [r for r in evidence[c] if r['score'] is not None]
            return (0 if len(valid) == 1 else 1, c == target, -confidence[c], c)
        ordered = sorted(bank, key=lambda q: (*rank(q['concept_id']), q['id']) if q['concept_id'] in concepts else (9, True, 0, q['concept_id'], q['id']))
    for q in ordered:
        c = q['concept_id']
        if c not in concepts or q['id'] in used:
            continue
        if method != 'fixed' and status(evidence[c]) != 'Insufficient evidence':
            continue
        return q
    return None


def make_report(target, bank, edges, current, prior=()):
    lookup = {q['id']: q for q in bank}
    rows = []
    for concept in sorted(set(prerequisites(target, edges) + [target])):
        asked = [r for r in current if r['concept_id'] == concept]
        historical = [r for r in prior if r['concept_id'] == concept][-2:] if asked else []
        rows.append({'concept_id': concept, 'role': 'target' if concept == target else 'prerequisite',
                     'status': status(historical + asked) if asked else 'Insufficient evidence',
                     'assessment': 'Assessed' if asked else 'Unassessed',
                     'observations': [dict(r, question_en=lookup[r['question_id']]['en'],
                                           question_hi=lookup[r['question_id']]['hi'],
                                           correct_answer=lookup[r['question_id']]['answer'],
                                           scoring_rule=lookup[r['question_id']]['scoring_rule'],
                                           possible_difficulty=lookup[r['question_id']]['possible_difficulty'],
                                           source_references=lookup[r['question_id']]['source_references'],
                                           evidence_origin='current interaction' if r in asked else 'saved history')
                                      for r in historical + asked],
                     'references': [references(e) for e in edges
                                    if (e['source_id'] == concept and e['target_id'] == target)
                                    or (concept == target and e['target_id'] == target)]})
    return enrich_report({'version': VERSION, 'review_status': 'PROVISIONAL — human review pending',
            'target': target, 'question_count': len(current), 'rules': RULES, 'concepts': rows,
            'limitations': 'Proposed graph edges; passage IDs have not been checked against textbook text. '
                            'A correct answer is evidence for this item, not proof of mastery.'})


def connect(path=None):
    path = Path(path) if path else ROOT / 'diagnostic' / 'history.sqlite3'
    conn = sqlite3.connect(path, timeout=10)
    conn.execute('CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, learner TEXT, version TEXT, target TEXT, method TEXT, created TEXT, prior TEXT, report TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS responses (session_id TEXT, ordinal INTEGER, question_id TEXT, concept_id TEXT, response TEXT, score INTEGER, PRIMARY KEY(session_id, ordinal))')
    conn.execute('CREATE TABLE IF NOT EXISTS external_profile_links (learner TEXT PRIMARY KEY,student_id TEXT NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS student_learning_spaces (student_id TEXT PRIMARY KEY,learner TEXT UNIQUE NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS session_external_context (session_id TEXT PRIMARY KEY,payload TEXT NOT NULL)')
    conn.commit()
    return conn


def history(conn, learner):
    records = conn.execute('SELECT r.question_id,r.concept_id,r.response,r.score,s.id FROM responses r JOIN sessions s ON s.id=r.session_id WHERE s.learner=? AND s.version=? ORDER BY s.created,r.ordinal', (learner, VERSION)).fetchall()
    return [dict(zip(('question_id','concept_id','response','score','session_id'), r)) for r in records]


def new_session(conn, learner, target, method, prior):
    sid = uuid4().hex
    with conn:
        conn.execute('INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?)', (sid, learner, VERSION, target, method, datetime.now(timezone.utc).isoformat(), json.dumps(prior), None))
    return sid


def save_response(conn, sid, question, response):
    with conn:
        count = conn.execute('SELECT count(*) FROM responses WHERE session_id=?', (sid,)).fetchone()[0]
        if count >= 3:
            raise ValueError('Three-question budget exhausted')
        item = {'question_id': question['id'], 'concept_id': question['concept_id'],
                'response': response, 'score': score(question, response), 'session_id': sid}
        conn.execute('INSERT INTO responses VALUES (?,?,?,?,?,?)', (sid, count + 1, item['question_id'], item['concept_id'], response, item['score']))
    return item
