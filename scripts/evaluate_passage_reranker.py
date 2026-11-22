"""Cross-encoder experiment on the unchanged saved v5 candidate pool."""
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from statistics import mean,median
from datetime import datetime,timezone
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from diagnostic import passage_reranker as ce
from diagnostic import book_chat as chat
from diagnostic.evaluate_rag import relevant,aggregate
from diagnostic.evaluate_retrieval_k import scores
from diagnostic.retrieval_diversity import budgeted_prefix
from scripts.evaluate_evidence_coverage import intervals,coverage,identity

OUT=ROOT/'reports/retrieval_v6'


def run():
    baseline_path=ROOT/'reports/retrieval_v5/comparison.json'
    saved=json.loads(baseline_path.read_text(encoding='utf8'))
    manifest=json.loads((OUT/'baseline_manifest.json').read_text())
    for name,digest in saved['source_hashes'].items():
        snapshot=OUT/('baseline_'+Path(name).name)
        if hashlib.sha256(snapshot.read_bytes()).hexdigest()!=digest:
            raise ValueError('Saved v5 source and snapshot do not match: '+name)
    case_path=ROOT/'reports/rag_eval_cases_v1.json'
    if hashlib.sha256(case_path.read_bytes()).hexdigest()!=manifest['reports/rag_eval_cases_v1.json']:
        raise ValueError('Benchmark changed.')
    cases={c['id']:c for c in json.loads(case_path.read_text(encoding='utf8'))['cases']}
    started=time.perf_counter();ce.runtime();load_seconds=time.perf_counter()-started
    rows=[];rankings=[];timing=[]
    for saved_row in saved['rankings']:
        if saved_row['arm']!='diverse':continue
        case=cases[saved_row['case_id']];baseline=saved_row['sources']
        ce.score_passages.cache_clear()
        started=time.perf_counter();candidate=ce.rerank(baseline,case['question'])
        elapsed=time.perf_counter()-started
        if set(map(identity,baseline))!=set(map(identity,candidate)):
            raise ValueError('Reranker changed the candidate pool.')
        with patch.dict(os.environ,{'ATLAS_RERANKER':'on'}):
            live,_=chat.retrieve_sources(case['concept_id'],case['language'],case['question'],limit=None)
            live_selected,_=chat.retrieve_sources(case['concept_id'],case['language'],case['question'],limit=3,max_chars=1300)
        if any(s.get('reranker_status')=='unavailable' for s in live):
            raise RuntimeError('Live cross-encoder fell back unexpectedly.')
        if list(map(identity,live))!=list(map(identity,candidate)):
            raise ValueError('Live reranker does not reproduce the saved-pool experiment: '+case['id'])
        if list(map(identity,live_selected))!=list(map(identity,budgeted_prefix(candidate))):
            raise ValueError('Live context budget differs from experiment.')
        reference=intervals([s for s in baseline if relevant(s,case)])
        total=sum(relevant(s,case) for s in baseline)
        timing.append({'case_id':case['id'],'language':case['language'],'seconds':elapsed,
                       'pairs_scored':min(len(baseline),ce.SHORTLIST)})
        for arm,sources in [('v5_baseline',baseline),('cross_encoder',candidate)]:
            selected=budgeted_prefix(sources)
            flags=[relevant(s,case) for s in sources]
            count=sum(relevant(s,case) for s in selected)
            rows.append({'case_id':case['id'],'language':case['language'],'arm':arm,
                         'precision':count/len(selected) if selected else 0.,
                         'recall':count/total if total else None,'hit_rate':float(count>0),
                         'returned_chunks':len(selected),**coverage(selected,reference),
                         'fixed_k':{str(k):scores(flags,k) for k in [1,2,3,5,10]}})
            rankings.append({'case_id':case['id'],'language':case['language'],'arm':arm,'sources':sources})
        print(case['id']+' '+f'{elapsed:.3f}s cross-encoder, fixed pool verified',flush=True)
    keys=['precision','recall','hit_rate','support_span_coverage','redundant_fraction','returned_chunks','context_characters']
    summary=[]
    for lang in ('all','en','hi'):
        for arm in ('v5_baseline','cross_encoder'):
            selected=[r for r in rows if r['arm']==arm and (lang=='all' or r['language']==lang)]
            summary.append({'language':lang,'arm':arm,'cases':len(selected),**aggregate(selected,keys)})
    report={'created_utc':datetime.now(timezone.utc).isoformat(),'summary':summary,'rows':rows,'rankings':rankings,
            'baseline_report_sha256':hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
            'dataset_sha256':manifest['reports/rag_eval_cases_v1.json'],
            'reranker_manifest':json.loads((ce.MODEL/'manifest.json').read_text()),
            'reranker_source_sha256':hashlib.sha256((ROOT/'diagnostic/passage_reranker.py').read_bytes()).hexdigest(),
            'live_source_hashes':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in
                 ['diagnostic/semantic_chunks.py','diagnostic/hybrid_retrieval.py','diagnostic/book_chat.py','diagnostic/retrieval_diversity.py','diagnostic/passage_reranker.py']},
            'live_policy_verified':True,
            'model_load_seconds':load_seconds,'uncached_pair_scoring_mean_seconds':mean(t['seconds'] for t in timing),
            'uncached_pair_scoring_median_seconds':median(t['seconds'] for t in timing),'timings':timing,
            'controls':'Same saved v5 candidate pool, query, labels, up-to-three-passage policy and 1300-character maximum.',
            'limits':['Known 12-case development set; no independent relevance or answer-correctness review.',
                      'Only the top 20 hybrid/diversity candidates are cross-encoder scored; the remaining pool is retained.',
                      'Original recall uses the same complete candidate-pool denominator in both arms.',
                      'Support-span coverage is a separate overlap-adjusted text metric, not fact recall.',
                      'Timing is uncached pair scoring on CPU after model load; it excludes initial retrieval and generation.',
                      'No LLM generation, final scenarios, or learner database changes.']}
    (OUT/'comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    lines=['# Cross-encoder reranking development experiment','',report['controls'],'',
           '| Language | Arm | Precision | Original recall | Hit | Support-span coverage | Mean passages | Mean chars |',
           '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for row in summary:
        lines.append('| '+row['language']+' | '+row['arm']+' | '+' | '.join(f'{row[k]:.4f}' for k in
                     ['precision','recall','hit_rate','support_span_coverage','returned_chunks','context_characters'])+' |')
    lines+=['',f'Model load: {load_seconds:.3f}s. Mean uncached cross-encoder scoring: {report["uncached_pair_scoring_mean_seconds"]:.3f}s per query.',
            '', '## Limits','']+['- '+s for s in report['limits']]
    lines+=['','Reproduce: `venv/Scripts/python.exe scripts/evaluate_passage_reranker.py`','']
    (OUT/'comparison.md').write_text('\n'.join(lines),encoding='utf8')
    for row in summary:print(json.dumps(row),flush=True)
    return report


if __name__=='__main__':run()
