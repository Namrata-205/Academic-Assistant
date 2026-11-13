"""Real-response collection and export; no synthetic data is labelled learner data."""
import hashlib
import json
import secrets
from datetime import datetime,timezone
from diagnostic import engine as e

PROTOCOL='learner-study-v1'


def ensure(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS learner_study (participant_hash TEXT PRIMARY KEY,session_id TEXT UNIQUE,method TEXT,protocol TEXT,created TEXT,bank_hash TEXT,graph_hash TEXT)')
    conn.commit()


def enrol(conn,participant_code,target,consent):
    if consent is not True:raise ValueError('Confirm voluntary participation before starting.')
    if not isinstance(participant_code,str) or not 3<=len(participant_code.strip())<=80:
        raise ValueError('Enter a pseudonymous participant code of 3–80 characters.')
    nodes,edges=e.load_graph()
    if target not in nodes or not e.eligible(target,e.load_bank(),edges):raise ValueError('Choose a bank-covered topic.')
    ensure(conn)
    digest=hashlib.sha256((PROTOCOL+':'+participant_code.strip()).encode()).hexdigest()
    existing=conn.execute('SELECT session_id FROM learner_study WHERE participant_hash=?',(digest,)).fetchone()
    if existing:return existing[0],'study-'+digest
    method=secrets.choice(['fixed','graph-guided'])
    learner='study-'+digest
    sid=e.new_session(conn,learner,target,method,[])
    graph_path=e.graph_source_path()
    with conn:
        conn.execute('INSERT INTO learner_study VALUES (?,?,?,?,?,?,?)',
                     (digest,sid,method,PROTOCOL,datetime.now(timezone.utc).isoformat(),
                      hashlib.sha256(e.BANK_PATH.read_bytes()).hexdigest(),hashlib.sha256(graph_path.read_bytes()).hexdigest()))
    return sid,learner


def export(conn):
    ensure(conn)
    result=[]
    for record in conn.execute('SELECT participant_hash,session_id,method,protocol,created,bank_hash,graph_hash FROM learner_study ORDER BY created'):
        digest,sid,method,protocol,created,bank_hash,graph_hash=record
        target,saved_report=conn.execute('SELECT target,report FROM sessions WHERE id=?',(sid,)).fetchone()
        responses=[dict(zip(('question_id','concept_id','response','score'),r)) for r in conn.execute('SELECT question_id,concept_id,response,score FROM responses WHERE session_id=? ORDER BY ordinal',(sid,))]
        result.append({'study_id':sid,'participant_hash':digest,'method':method,'protocol':protocol,
                       'target':target,'created':created,'bank_sha256':bank_hash,'graph_sha256':graph_hash,
                       'questions_asked':len(responses),'responses':responses,
                       'report':json.loads(saved_report) if saved_report else None,'data_origin':'real participant entry (not independently verified)',
                       'independent_expected_statuses':{},'reviewer':'','review_status':'PENDING'})
    return {'protocol':PROTOCOL,'record_count':len(result),'records':result,
            'limitation':'No educational-effectiveness conclusion until actual completed cases and independent expected diagnoses are available.'}


def analyse(reviewed_export):
    """Count reviewed concept opportunities, not unreviewed outputs as gold labels."""
    results={m:{'reviewed_cases':0,'correct_diagnoses':0,'false_diagnoses':0,'unresolved_concepts':0,'questions_asked':0} for m in ('fixed','graph-guided')}
    for row in reviewed_export.get('records',[]):
        if not row.get('report') or row.get('review_status')!='APPROVED' or not row.get('reviewer'):
            continue
        gold=row.get('independent_expected_statuses',{})
        if not gold:continue
        totals=results[row['method']];totals['reviewed_cases']+=1;totals['questions_asked']+=row['questions_asked']
        actual={c['concept_id']:c for c in row['report']['concepts']}
        for cid,expected in gold.items():
            current=actual.get(cid)
            if not current or current['assessment']!='Assessed' or current['status']=='Insufficient evidence':totals['unresolved_concepts']+=1
            elif current['status']==expected:totals['correct_diagnoses']+=1
            else:totals['false_diagnoses']+=1
    return {'protocol':PROTOCOL,'results':results,'educational_usefulness_established':False,
            'note':'Descriptive comparison only. Reviewed cases, allocation balance, dropout, topic mix and independent transfer tasks require interpretation.'}


if __name__=='__main__':
    import argparse
    from pathlib import Path
    parser=argparse.ArgumentParser();parser.add_argument('reviewed_export');parser.add_argument('--output',default='reports/real_learner_results.json')
    args=parser.parse_args();output=analyse(json.loads(Path(args.reviewed_export).read_text(encoding='utf-8')))
    Path(args.output).write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(output,indent=2))
