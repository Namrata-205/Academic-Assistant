"""Store learner-owned papers and analyse readable text locally."""
import base64
import hashlib
import json
import re
from collections import Counter
from datetime import datetime,timezone
from diagnostic import engine
from diagnostic.curriculum import search_terms
from uuid import uuid4

MAX_BYTES=5*1024*1024


def ensure(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS past_paper_profiles (id TEXT PRIMARY KEY,learner TEXT NOT NULL,name TEXT NOT NULL,created TEXT NOT NULL,sha256 TEXT NOT NULL,profile TEXT NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS past_paper_files (id TEXT PRIMARY KEY, contents BLOB NOT NULL)')


def extract(filename,encoded):
    if not isinstance(filename,str) or not isinstance(encoded,str):raise ValueError('Choose a PDF or UTF-8 text paper.')
    if len(encoded)>MAX_BYTES*4//3+8:raise ValueError('Paper must be no larger than 5 MB.')
    try:data=base64.b64decode(encoded,validate=True)
    except (ValueError,TypeError):raise ValueError('Invalid uploaded file.')
    if not data or len(data)>MAX_BYTES:raise ValueError('Paper must be no larger than 5 MB.')
    if filename.lower().endswith('.pdf'):
        import pymupdf
        try:
            with pymupdf.open(stream=data,filetype='pdf') as pdf:
                if pdf.needs_pass:raise ValueError('Please upload an unlocked PDF.')
                if len(pdf)>30:raise ValueError('Upload a paper with at most 30 pages.')
                text='\n'.join(page.get_text() for page in pdf)
        except ValueError:raise
        except Exception:raise ValueError('This PDF could not be read.')
    elif filename.lower().endswith('.txt'):
        try:text=data.decode('utf-8-sig')
        except UnicodeError:raise ValueError('Text papers must use UTF-8 encoding.')
    else:raise ValueError('Upload a PDF or .txt paper.')
    if filename.lower().endswith('.txt') and len(text.strip()) < 3:
        raise ValueError('The text file contains too little text to be a paper.')
    return text[:80000], data


QUESTION_START = re.compile(
    r'^[^\S\n]*(?:\(?\d{1,3}[^\S\n]*[).:–—-](?=[^\d]|$)[^\S\n]*'
    r'|(?:q(?:uestion)?|प्रश्न)\.?\s*(?:no\.?\s*)?\d{1,3}(?=\D|$)[^\S\n]*[).:–—-]?[^\S\n]*)',
    re.M|re.I,
)
QUESTION_PROMPT = re.compile(
    r'^\s*(?:find|calculate|evaluate|solve|simplify|write|draw|construct|identify|choose|explain|justify|'
    r'compare|convert|complete|fill|what|which|how|why)\b|[?？]\s*$|'
    r'(?:ज्ञात कीजिए|हल कीजिए|निकालिए|बताइए|लिखिए|समझाइए|बनाइए|चुनिए|कीजिए)[।?]?\s*$',
    re.I,
)
OPTION = re.compile(r'(?:^|\s)[(]?([A-Dअआइईकखगघ])[).:]\s', re.I)
WRITTEN = re.compile(r'\b(?:explain|justify|prove|show (?:that|your work)|describe|why)\b|समझाइए|कारण|सिद्ध', re.I)
DIAGRAM = re.compile(r'\b(?:diagram|figure|draw|construct|sketch)\b|चित्र|आकृति|रचना कीजिए', re.I)


def analyse(text):
    starts = list(QUESTION_START.finditer(text))
    blocks = [text[m.end():starts[i+1].start() if i+1<len(starts) else len(text)]
              for i,m in enumerate(starts)]
    blocks = [block for block in blocks if block.strip()]
    if not blocks:
        # Detect unnumbered prompts and keep their wrapped lines and answer options together.
        for line in text.splitlines():
            if QUESTION_PROMPT.search(line):
                blocks.append(line)
            elif blocks and line.strip():
                blocks[-1] += '\n' + line
        # Some PDF extractors put the prompt and options on the same line as a heading.
        if not blocks and len({m.casefold() for m in OPTION.findall(text)}) >= 2:
            blocks = [text]
    counts = dict.fromkeys(('mcq','short_answer','written','diagram'), 0)
    topics = Counter()
    nodes, _ = engine.load_graph()
    aliases = []
    for cid, node in nodes.items():
        if not node['chapter'].startswith('CH'):
            continue
        for term in search_terms(node):
            if len(term) >= 4:
                aliases.append((term.casefold(), cid))
    # Prefer specific names over shorter overlapping names such as "angle".
    aliases.sort(key=lambda pair: (-len(pair[0]), pair[0], pair[1]))
    for block in blocks:
        options = {m.casefold() for m in OPTION.findall(block)}
        kind = ('mcq' if len(options)>=2 else 'diagram' if DIAGRAM.search(block) else
                'written' if WRITTEN.search(block) else 'short_answer')
        counts[kind] += 1
        prompt = OPTION.split(block, maxsplit=1)[0].casefold()
        found = set()
        for term,cid in aliases:
            if cid in found:
                continue
            pattern = r'(?<!\w)'+re.escape(term)+r'(?:s)?(?!\w)'
            if re.search(pattern,prompt):
                found.add(cid)
                prompt = re.sub(pattern, ' ', prompt)
        topics.update(found)
    rankings = sorted(topics.items(), key=lambda pair: (-pair[1], pair[0]))
    return dict(mcq_ratio=round(counts['mcq']/len(blocks), 3) if blocks else .5,
                detected_questions=len(blocks), detected_mcq_blocks=counts['mcq'],
                formats=[kind for kind,count in counts.items() if count],
                format_counts=counts,
                topics=[dict(concept_id=cid, count=count) for cid,count in rankings])


def upload(conn,learner,filename,encoded):
    ensure(conn)
    text,data=extract(filename,encoded)
    digest=hashlib.sha256(data).hexdigest()
    profile=analyse(text)
    profile['analysis_status'] = ('ready' if profile['detected_questions'] else
                                  'no_questions' if text.strip() else 'no_text')
    pid=uuid4().hex
    name=filename.replace('\\','/').split('/')[-1][:120]
    with conn:
        conn.execute('BEGIN IMMEDIATE')
        saved=conn.execute('''SELECT p.id FROM past_paper_profiles p JOIN past_paper_files f ON p.id=f.id
                              WHERE p.learner=? AND p.sha256=?''',(learner,digest)).fetchone()
        if saved:
            pid=saved[0]
            conn.execute('UPDATE past_paper_profiles SET profile=? WHERE id=?',(json.dumps(profile),pid))
        else:
            if conn.execute('SELECT count(*) FROM past_paper_profiles WHERE learner=?',(learner,)).fetchone()[0]>=10:
                raise ValueError('Keep up to 10 past papers. Remove an older one first.')
            conn.execute('INSERT INTO past_paper_profiles VALUES (?,?,?,?,?,?)',
                (pid,learner,name,datetime.now(timezone.utc).isoformat(),digest,json.dumps(profile)))
            conn.execute('INSERT INTO past_paper_files VALUES (?,?)',(pid,data))
    return get(conn,learner,pid)


def download(conn,learner,pid):
    ensure(conn)
    saved=conn.execute('SELECT name,contents FROM past_paper_profiles p JOIN past_paper_files f ON f.id=p.id WHERE learner=? AND p.id=?',
                       (learner,pid)).fetchone()
    if saved is None:
        raise LookupError('Saved paper not found.')
    return saved


def get(conn,learner,pid):
    ensure(conn);row=conn.execute('SELECT id,name,created,profile,EXISTS(SELECT 1 FROM past_paper_files f WHERE f.id=past_paper_profiles.id) FROM past_paper_profiles WHERE learner=? AND id=?',(learner,pid)).fetchone()
    if row is None:raise LookupError('Paper pattern not found.')
    return dict(id=row[0],name=row[1],created=row[2],has_file=bool(row[4]),**json.loads(row[3]))


def list_profiles(conn,learner):
    ensure(conn)
    return [dict(id=r[0],name=r[1],created=r[2],has_file=bool(r[4]),**json.loads(r[3])) for r in conn.execute(
        'SELECT id,name,created,profile,EXISTS(SELECT 1 FROM past_paper_files f WHERE f.id=past_paper_profiles.id) FROM past_paper_profiles WHERE learner=? ORDER BY created DESC',(learner,))]


def remove(conn,learner,pid):
    ensure(conn)
    with conn:
        if not conn.execute('DELETE FROM past_paper_profiles WHERE learner=? AND id=?',(learner,pid)).rowcount:
            raise LookupError('Paper pattern not found.')
        conn.execute('DELETE FROM past_paper_files WHERE id=?',(pid,))
    return {'removed':True}
