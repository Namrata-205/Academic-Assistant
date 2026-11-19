"""Grounded background context from external reports, never item-level evidence."""
import csv
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from diagnostic.engine import ROOT

STORE = ROOT / 'diagnostic' / 'imported_reports.sqlite3'

FIRST_NAMES = ['Aarav','Aanya','Vihaan','Diya','Arjun','Isha','Kabir','Meera','Rohan','Saanvi','Aditya','Anaya','Ishaan','Kavya','Reyansh','Tara','Vivaan','Nisha','Krish','Riya','Atharv','Avni','Dhruv','Siya','Dev','Myra','Yash','Anika','Ved','Aditi','Neil','Zoya']
LAST_NAMES = ['Mehta','Shah','Rao','Kapoor','Nair','Patel','Joshi','Iyer','Verma','Das','Sen','Sinha','Kulkarni','Bose','Malhotra','Pillai','Desai','Bhat','Menon','Reddy','Sethi','Anand','Dutta','Bajaj','Saxena','Chopra','Mishra','Shetty','Bansal','Suri','Prasad','Arora']


def display_name(student_id):
    """Stable display alias only; no real-name claim or change to source identifiers."""
    raw=str(student_id)
    index=int(raw) if raw.isdecimal() else int(hashlib.sha256(raw.encode()).hexdigest()[:8],16)
    return f'{FIRST_NAMES[index%32]} {chr(65+(index//1024)%26)}. {LAST_NAMES[(index//32)%32]}'

# Explicit semantic crosswalk. A broad external topic is not an exact concept match.
TOPICS = {
    'place value': (['MATH6_C0038'], 'exact'),
    'rotation': (['MATH6_C0034'], 'exact'),
    'measuring angles': (['MATH6_C0020','MATH6_C0024','MATH6_C0025','MATH6_C0029','MATH6_C0030'], 'related'),
    'types, naming and estimating': (['MATH6_C0020','MATH6_C0021','MATH6_C0024','MATH6_C0025','MATH6_C0026'], 'related'),
    'basic angle facts (straight line, opposite, around a point, etc)': (['MATH6_C0020','MATH6_C0023','MATH6_C0024','MATH6_C0025'], 'related'),
    'squares, cubes, etc': (['MATH6_C0009','MATH6_C0010'], 'related'),
}


def terms(value):
    return [part.strip() for part in (value or '').split('|') if part.strip()]


def import_files(student_path, gap_path, db_path=None):
    """Preserve originals as JSON payloads with source hashes; atomic, repeatable import."""
    with Path(student_path).open(encoding='utf-8-sig', newline='') as f:
        reader=csv.DictReader(f)
        if not {'student_id','answered','correct','recommended_revision'}.issubset(reader.fieldnames or []):
            raise ValueError('Student report is missing required columns.')
        students=list(reader)
    with Path(gap_path).open(encoding='utf-8-sig', newline='') as f:
        reader=csv.DictReader(f)
        if not {'student_id','gap_topic','status','diagnostic_mode'}.issubset(reader.fieldnames or []):
            raise ValueError('Gap report is missing required columns.')
        gaps=list(reader)
    ids=[r['student_id'].strip() for r in students]
    if len(set(ids))!=len(ids) or '' in ids:
        raise ValueError('Student IDs must be non-empty and unique.')
    id_set=set(ids)
    if any(g['student_id'].strip() not in id_set for g in gaps):
        raise ValueError('Gap report references a student missing from the summary report.')
    db_path=Path(db_path) if db_path is not None else STORE
    db_path.parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(db_path)
    manifest={'imported_at':datetime.now(timezone.utc).isoformat(),
              'files':[{'name':Path(p).name,'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in (student_path,gap_path)],
              'student_count':len(students),'gap_count':len(gaps),
              'limitation':'Aggregate retrospective reports, not this app’s diagnostic question responses. Assessment dates are not supplied.'}
    try:
        with conn:
            conn.execute('CREATE TABLE IF NOT EXISTS students (id TEXT PRIMARY KEY,payload TEXT NOT NULL)')
            conn.execute('CREATE TABLE IF NOT EXISTS gaps (student_id TEXT NOT NULL,payload TEXT NOT NULL)')
            conn.execute('CREATE INDEX IF NOT EXISTS gaps_by_student ON gaps(student_id)')
            conn.execute('CREATE TABLE IF NOT EXISTS metadata (id INTEGER PRIMARY KEY,payload TEXT NOT NULL)')
            conn.execute('DELETE FROM students');conn.execute('DELETE FROM gaps')
            conn.executemany('INSERT INTO students VALUES (?,?)',[(r['student_id'].strip(),json.dumps(r,ensure_ascii=False)) for r in students])
            conn.executemany('INSERT INTO gaps VALUES (?,?)',[(r['student_id'].strip(),json.dumps(r,ensure_ascii=False)) for r in gaps])
            conn.execute('INSERT OR REPLACE INTO metadata VALUES (1,?)',(json.dumps(manifest,ensure_ascii=False),))
    finally:
        conn.close()
    return manifest


def get_profile(student_id, db_path=None):
    path=Path(db_path) if db_path is not None else STORE
    if not path.exists():
        raise ValueError('No earlier reports have been imported on this computer.')
    conn=sqlite3.connect(f'{path.as_uri()}?mode=ro',uri=True)
    try:
        row=conn.execute('SELECT payload FROM students WHERE id=?',(student_id,)).fetchone()
        if not row:
            raise LookupError('No earlier report matches that student ID. Check the ID and try again.')
        return {'student':json.loads(row[0]),
                'gaps':[json.loads(r[0]) for r in conn.execute('SELECT payload FROM gaps WHERE student_id=?',(student_id,))],
                'provenance':json.loads(conn.execute('SELECT payload FROM metadata WHERE id=1').fetchone()[0])}
    finally:
        conn.close()


def profile_summary(profile):
    student=profile['student']
    subjects=[]
    for key,label in [('number','Number'),('algebra','Algebra'),('geometry_and_measure','Geometry & measurement')]:
        value=student.get(key+'_percentage','')
        try:
            percentage=float(value) if value!='' else None
        except (ValueError,TypeError):
            percentage=None
        subjects.append({'name':label,'percentage':percentage,
                         'category':student.get(key+'_category','') or 'Not recorded',
                         'trend':student.get(key+'_trend','') or 'insufficient data'})
    return {'student_id':student['student_id'], 'display_name':display_name(student['student_id']),
            'name_note':'Generated profile nickname; the supplied reports contain IDs, not student names.',
            'answered':student.get('answered',''), 'correct':student.get('correct',''),
            'overall_percentage':student.get('overall_percentage',''),
            'strong_subjects':terms(student.get('strong_subjects')),
            'weak_subjects':terms(student.get('weak_subjects')),
            'strong_topics':terms(student.get('strong_topics')),
            'practice_topics':terms(student.get('weak_topics_by_severity')),
            'subjects':subjects,
            'revision_topics':terms(student.get('recommended_revision')),
            'revision_concepts':list(dict.fromkeys(
                concept for topic in terms(student.get('recommended_revision'))
                for concept in TOPICS.get(topic.casefold(), ([], None))[0])),
            'gap_count':len(profile['gaps']),
            'notice':'Earlier imported report linked. It informs feedback, not current scores or confirmed understanding.'}


def select_learning_space(conn,student_id):
    """Stable server-side profile identity; browser cache is no longer authoritative."""
    from uuid import uuid4
    profile=get_profile(student_id)
    row=conn.execute('SELECT learner FROM student_learning_spaces WHERE student_id=?',(student_id,)).fetchone()
    if row:
        learner=row[0]
    else:
        # Recover an already linked space with saved checks rather than starting empty.
        previous=conn.execute('SELECT p.learner,count(s.id) AS attempts FROM external_profile_links p LEFT JOIN sessions s ON s.learner=p.learner WHERE p.student_id=? GROUP BY p.learner ORDER BY attempts DESC,p.learner LIMIT 1',(student_id,)).fetchone()
        learner=previous[0] if previous else 'student-'+uuid4().hex
    with conn:
        conn.execute('INSERT OR IGNORE INTO student_learning_spaces VALUES (?,?)',(student_id,learner))
        canonical=conn.execute('SELECT learner FROM student_learning_spaces WHERE student_id=?',(student_id,)).fetchone()[0]
        conn.execute('INSERT OR REPLACE INTO external_profile_links VALUES (?,?)',(canonical,student_id))
    return {'learner':canonical,'profile':profile_summary(profile)}


def list_profiles(search='',page=1,gaps_only=False,db_path=None):
    path=Path(db_path) if db_path is not None else STORE
    if not path.exists():
        return {'students':[],'total':0,'page':1,'pages':1,'available':False}
    page=max(1,int(page));size=20
    conn=sqlite3.connect(f'{path.as_uri()}?mode=ro',uri=True)
    try:
        filters=[];args=[]
        if search:
            conn.create_function('display_alias',1,display_name)
            filters.append('(instr(s.id,?)>0 OR instr(lower(display_alias(s.id)),lower(?))>0)');args.extend([search.strip(),search.strip()])
        if gaps_only:
            filters.append('EXISTS(SELECT 1 FROM gaps g WHERE g.student_id=s.id)')
        where=' WHERE '+' AND '.join(filters) if filters else ''
        total=conn.execute('SELECT count(*) FROM students s'+where,args).fetchone()[0]
        pages=max(1,(total+size-1)//size);page=min(page,pages)
        rows=conn.execute('SELECT s.id,(SELECT count(*) FROM gaps g WHERE g.student_id=s.id) FROM students s'+where+' ORDER BY length(s.id),s.id LIMIT ? OFFSET ?',args+[size,(page-1)*size]).fetchall()
        return {'students':[{'student_id':r[0],'display_name':display_name(r[0]),'gap_count':r[1]} for r in rows],
                'total':total,'page':page,'pages':pages,'available':True}
    finally:conn.close()


def context_for_target(profile,target,nodes,edges):
    relevant={target,*[r['source_id'] for r in edges if r['target_id']==target]}
    student=profile['student']
    candidates=[]
    by_topic={g['gap_topic'].casefold():g for g in profile['gaps']}
    # Preserve source order and include flagged, recommended and strong topics.
    names=list(dict.fromkeys([g['gap_topic'] for g in profile['gaps']]+terms(student.get('recommended_revision'))+terms(student.get('strong_topics'))))
    for topic in names:
        match=TOPICS.get(topic.casefold())
        if not match or not relevant.intersection(match[0]):
            continue
        gap=by_topic.get(topic.casefold())
        if gap:
            status=gap['status']
            signal={'confirmed':'Source report flags a gap','pending':'Source report suggests further checking',
                    'inconclusive':'Source report has inconclusive evidence','not_supported':'Source report did not support a gap'}.get(status,'Source status is unrecognised')
        else:
            status='revision' if topic in terms(student.get('recommended_revision')) else 'strength'
            signal='Source report recommends revision' if status=='revision' else 'Source report lists this as a strength'
        concepts=[c for c in match[0] if c in relevant and c in nodes]
        candidates.append({'topic':topic,'source_status':status,'source_signal':signal,
                           'mapping':match[1],'concept_ids':concepts,
                           'concept_names':[nodes[c]['en'] for c in concepts],
                           'source_evidence':gap.get('evidence_from_scores','') if gap else '',
                           'source_attempts':gap.get('prerequisite_attempts','') if gap else '',
                           'source_accuracy':gap.get('prerequisite_accuracy','') if gap else '',
                           'needed_for_topics':terms(gap.get('needed_for_weak_topics','')) if gap else [],
                           'source_foundations':terms(gap.get('foundational_concepts','')) if gap else [],
                           'diagnostic_mode':gap.get('diagnostic_mode','not supplied') if gap else 'summary only',
                           'diagnostic_items':gap.get('diagnostic_items','') if gap else '',
                           'diagnostic_accuracy':gap.get('diagnostic_accuracy','') if gap else ''})
    return {'student_id':student['student_id'],'items':candidates[:5],
            'unmapped_topic_count':sum(topic.casefold() not in TOPICS for topic in names),
            'provenance':profile['provenance'],
            'notice':'Imported background only. Source labels are not this app’s diagnoses. Broad topic matches do not establish concept mastery or difficulty. Assessment dates are not supplied.'}


def linked_context(conn,learner,target,nodes,edges):
    row=conn.execute('SELECT student_id FROM external_profile_links WHERE learner=?',(learner,)).fetchone()
    if not row:
        return None
    return context_for_target(get_profile(row[0]),target,nodes,edges)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('student_report');parser.add_argument('gap_report')
    args=parser.parse_args()
    print(json.dumps(import_files(args.student_report,args.gap_report),indent=2))
