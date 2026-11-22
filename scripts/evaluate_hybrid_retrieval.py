"""Offline paired v3/hybrid comparison. Same pages, chunks, context, and labels."""
import hashlib
import argparse
import json
import math
import sys
import time
from statistics import mean,median
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from diagnostic import book_chat as chat,semantic_chunks as chunks
from diagnostic.evaluate_rag import relevant,retrieval_scores,aggregate,ratio
from scripts.evaluate_retrieval_improvements import module

OUT=ROOT/'reports/retrieval_v4'


def run():
    if chunks.VERSION!='graph-hybrid-page-v4':
        raise ValueError('Historical v4 report preserved. Use evaluate_evidence_coverage.py for the current retrieval version.')
    manifest=json.loads((OUT/'baseline_manifest.json').read_text())
    dataset_path=ROOT/'reports/rag_eval_cases_v1.json'
    for original,snapshot in [('diagnostic/semantic_chunks.py','baseline_semantic_chunks.py'),
                              ('diagnostic/book_chat.py','baseline_book_chat.py')]:
        if hashlib.sha256((OUT/snapshot).read_bytes()).hexdigest()!=manifest[original]:
            raise ValueError('Baseline changed: '+snapshot)
    if hashlib.sha256(dataset_path.read_bytes()).hexdigest()!=manifest['reports/rag_eval_cases_v1.json']:
        raise ValueError('Benchmark changed.')
    baseline=module(OUT/'baseline_semantic_chunks.py','diagnostic._v4_baseline')
    candidate=chunks.rank_pages
    dataset=json.loads(dataset_path.read_text(encoding='utf8'));results={}
    keys=['hit_at_1','hit_at_2','mrr_at_2','precision_at_2','recall_at_2','anchor_hit_at_1','anchor_hit_at_2']
    for name,rank in [('v3_baseline',baseline['rank_pages']),('hybrid',candidate)]:
        rows=[]
        with patch.object(chunks,'rank_pages',rank):
            for case in dataset['cases']:
                started=time.perf_counter()
                sources,_=chat.retrieve_sources(case['concept_id'],case['language'],case['question'],limit=None)
                elapsed=time.perf_counter()-started
                if not sources or any(s.get('retrieval')=='page excerpt fallback' for s in sources):
                    raise RuntimeError('Embedding retrieval unavailable: '+case['id'])
                flags=[relevant(s,case) for s in sources]
                anchors=[relevant(dict(s,excerpt=s.get('matched_excerpt',s['excerpt'])),case) for s in sources]
                rows.append({'case_id':case['id'],'language':case['language'],**retrieval_scores(flags),
                             'recall_at_2':ratio(sum(flags[:2]),sum(flags)),
                             'anchor_hit_at_1':float(any(anchors[:1])),'anchor_hit_at_2':float(any(anchors[:2])),
                             'elapsed_seconds':elapsed,'candidate_count':len(sources),'top_sources':sources[:2]})
        results[name]={'metrics':aggregate(rows,keys),
                       'by_language':{lang:aggregate([r for r in rows if r['language']==lang],keys) for lang in ('en','hi')},
                       'rows':rows}
        print(name,json.dumps(results[name]['metrics']),flush=True)
    # All cases have been run once above. Alternate arm order to reduce timing
    # bias; include retrieval work but no generation, and report startup apart.
    timings=[]
    arms=[('v3_baseline',baseline['rank_pages']),('hybrid',candidate)]
    for repeat in range(3):
        for case in dataset['cases']:
            for name,rank in (arms if repeat%2==0 else list(reversed(arms))):
                with patch.object(chunks,'rank_pages',rank):
                    started=time.perf_counter()
                    chat.retrieve_sources(case['concept_id'],case['language'],case['question'],limit=2)
                    timings.append({'arm':name,'case_id':case['id'],'language':case['language'],
                                    'repeat':repeat,'seconds':time.perf_counter()-started})
    latency={}
    for name,_ in arms:
        selected=[t['seconds'] for t in timings if t['arm']==name]
        latency[name]={'requests':len(selected),'mean_seconds':mean(selected),'median_seconds':median(selected),
                       'p95_seconds':sorted(selected)[math.ceil(.95*len(selected))-1],
                       'by_language':{lang:mean(t['seconds'] for t in timings if t['arm']==name and t['language']==lang) for lang in ('en','hi')}}
    report={'candidate_version':chunks.VERSION,'cases':len(dataset['cases']),
            'dataset_sha256':manifest['reports/rag_eval_cases_v1.json'],'review_status':dataset['review_status'],
            'controls':'Identical concept-scoped pages, graph anchors, 650-character context budget, evidence labels, and model.',
            'configuration':{'bm25_k1':1.2,'bm25_b':.75,'rrf_k':60,'keyword_input':'anchor text only'},
            'results':results,'warm_latency':latency,'timing_rows':timings,
            'source_hashes':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
                     ['diagnostic/semantic_chunks.py','diagnostic/hybrid_retrieval.py','diagnostic/book_chat.py']},
            'limitations':['Known 12-case development set; independent review pending; not held-out accuracy.',
                           'Page/substring proxy is not human-rated relevance or mathematical correctness.',
                           'Expanded evidence and ranking anchors are scored separately.',
                           'Recall denominators may vary after context deduplication.',
                           'Per-case elapsed time includes caches/model startup and is not a fair latency comparison.']}
    (OUT/'comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    lines=['# Hybrid retrieval development comparison','',report['controls'],'',
           '| Arm | Evidence Hit@1 | Hit@2 | MRR@2 | Precision@2 | Recall@2 | Anchor Hit@1 | Anchor Hit@2 |',
           '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for name,result in results.items():lines.append('| '+name+' | '+' | '.join(f'{result["metrics"][k]:.4f}' for k in keys)+' |')
    lines+=['','## By language','','| Language | Arm | Evidence Hit@1 | Anchor Hit@1 | MRR@2 |',
            '| --- | --- | ---: | ---: | ---: |']
    for lang in ('en','hi'):
        for name,result in results.items():
            m=result['by_language'][lang]
            lines.append('| '+lang+' | '+name+' | '+' | '.join(f'{m[k]:.4f}' for k in ['hit_at_1','anchor_hit_at_1','mrr_at_2'])+' |')
    lines+=['','## Warm retrieval latency','',
            'Three repeats per case per arm, alternating arm order after initial case execution. Includes retrieval and excludes generation and model loading.','',
            '| Arm | Requests | Mean seconds | Median seconds | P95 seconds |',
            '| --- | ---: | ---: | ---: | ---: |']
    for name,m in latency.items():
        lines.append(f'| {name} | {m["requests"]} | {m["mean_seconds"]:.4f} | {m["median_seconds"]:.4f} | {m["p95_seconds"]:.4f} |')
    lines+=['','## Limits','']+['- '+limit for limit in report['limitations']]
    lines+=['','Reproduce: `venv/Scripts/python.exe scripts/evaluate_hybrid_retrieval.py`','']
    (OUT/'comparison.md').write_text('\n'.join(lines),encoding='utf8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--audit-sources',action='store_true')
    args=parser.parse_args()
    if args.audit_sources:
        from scripts import evaluate_retrieval_improvements as audit
        with patch.object(audit,'OUT',OUT):audit.audit_sources()
    else:run()
