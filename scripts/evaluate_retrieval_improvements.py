"""Paired, offline development comparison against a preserved local baseline.

Does not edit benchmarks, frozen scenarios, old reports, or learner databases.
"""
import hashlib
import argparse
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from diagnostic import book_chat as chat,semantic_chunks as chunks
from diagnostic.evaluate_rag import relevant,retrieval_scores,aggregate,ratio

OUT=ROOT/'reports/retrieval_v3'


def audit_sources():
    """Check citation fidelity and budgets across every catalogued concept."""
    from diagnostic import engine
    nodes,_=engine.load_graph();rows=[]
    for cid,node in nodes.items():
        for lang in ('en','hi'):
            sources,_=chat.retrieve_sources(cid,lang,node[lang]);checks=[]
            for source in sources:
                filename=source['url'].split('/')[-1].split('#')[0]
                path=ROOT/'assets/textbooks'/lang/filename
                page=' '.join(' '.join(chat.page_content(str(path),source['pdf_page'],path.stat().st_mtime_ns)).split())
                checks.append({'chunk_id':source.get('chunk_id'),'pdf_page':source['pdf_page'],
                               'verbatim_normalized_page_span':source['excerpt'] in page,
                               'within_character_budget':len(source['excerpt'])<=chunks.MAX_CHARS,
                               'language_matches':source['language']==lang})
            rows.append({'concept_id':cid,'language':lang,'sources':len(sources),'checks':checks})
    checks=[c for row in rows for c in row['checks']]
    result={'concepts':len(nodes),'language_requests':len(rows),'returned_passages':len(checks),
            'unavailable_requests':sum(not r['sources'] for r in rows),
            'violations':[c for c in checks if not all(c[k] for k in ['verbatim_normalized_page_span','within_character_budget','language_matches'])],
            'rows':rows,'interpretation':'Structural source-integrity audit, not semantic relevance or correctness.'}
    (OUT/'source_integrity.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)
    if result['violations']:raise RuntimeError('Source integrity check failed.')
    return result


def module(path,name):
    scope={'__name__':name,'__file__':str(path)}
    exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),scope)
    return scope


def run():
    if chunks.VERSION!='graph-context-page-v3':
        raise ValueError('This historical comparison requires v3 code. Use evaluate_hybrid_retrieval.py for v4; old reports are preserved.')
    manifest=json.loads((OUT/'baseline_manifest.json').read_text())
    dataset_path=ROOT/'reports/rag_eval_cases_v1.json'
    if hashlib.sha256(dataset_path.read_bytes()).hexdigest()!=manifest['reports/rag_eval_cases_v1.json']:
        raise ValueError('Development benchmark changed since baseline capture.')
    for original,snapshot in [('diagnostic/semantic_chunks.py','baseline_semantic_chunks.py'),
                              ('diagnostic/book_chat.py','baseline_book_chat.py')]:
        if hashlib.sha256((OUT/snapshot).read_bytes()).hexdigest()!=manifest[original]:
            raise ValueError('Preserved baseline changed: '+snapshot)
    baseline=module(OUT/'baseline_semantic_chunks.py','diagnostic._retrieval_v3_baseline')
    old_chat=module(OUT/'baseline_book_chat.py','diagnostic._retrieval_v3_chat')
    dataset=json.loads(dataset_path.read_text(encoding='utf-8'))
    results={}
    def baseline_same_context(pages,query,limit=3):
        rows=baseline['rank_pages'](pages,query,limit=None);unique={}
        lookup={(meta['url'],page):(filename,mtime) for filename,page,mtime,meta in pages}
        for row in rows:
            filename,mtime=lookup[(row['url'],row['pdf_page'])]
            texts,_=baseline['page_index'](filename,row['pdf_page'],mtime)
            evidence,_,_=chunks.evidence_context(texts,row['chunk_index'])
            updated=dict(row,matched_excerpt=row['excerpt'],excerpt=evidence)
            unique.setdefault((row['url'],evidence),updated)
        return list(unique.values())[:limit]

    def candidate_anchors(pages,query,limit=3):
        with patch.object(chunks,'evidence_context',side_effect=lambda texts,i:(texts[i],i,i+1)):
            return candidate_rank(pages,query,limit)

    candidate_rank=chunks.rank_pages
    keys=['hit_at_1','hit_at_2','mrr_at_2','precision_at_2','recall_at_2','anchor_hit_at_1','anchor_hit_at_2','page_hit_at_1','page_hit_at_2','evidence_available','mean_top2_chars']
    for name,retrieve,rank in [('baseline',old_chat['retrieve_sources'],baseline['rank_pages']),
                               ('baseline_same_context',old_chat['retrieve_sources'],baseline_same_context),
                               ('candidate_anchors',chat.retrieve_sources,candidate_anchors),
                               ('candidate',chat.retrieve_sources,candidate_rank)]:
        rows=[];start=time.perf_counter()
        with patch.object(chunks,'rank_pages',rank):
            for case in dataset['cases']:
                sources,_=retrieve(case['concept_id'],case['language'],case['question'],limit=None)
                if not sources or any(s.get('retrieval')!='semantic cosine similarity' for s in sources):
                    raise RuntimeError('Embedding retrieval unavailable: '+case['id'])
                flags=[relevant(s,case) for s in sources]
                anchor_flags=[relevant(dict(s,excerpt=s.get('matched_excerpt',s['excerpt'])),case) for s in sources]
                page_flags=[s['pdf_page'] in case['pdf_pages'] for s in sources]
                rows.append({'case_id':case['id'],'language':case['language'],**retrieval_scores(flags),
                             'recall_at_2':ratio(sum(flags[:2]),sum(flags)),
                             'anchor_hit_at_1':float(any(anchor_flags[:1])),
                             'anchor_hit_at_2':float(any(anchor_flags[:2])),
                             'page_hit_at_1':float(any(page_flags[:1])),
                             'page_hit_at_2':float(any(page_flags[:2])),
                             'evidence_available':float(any(flags)),
                             'mean_top2_chars':sum(len(s['excerpt']) for s in sources[:2])/2,
                             'top_sources':sources[:2]})
        results[name]={'metrics':aggregate(rows,keys),
                       'by_language':{lang:aggregate([r for r in rows if r['language']==lang],keys) for lang in ('en','hi')},
                       'elapsed_seconds':time.perf_counter()-start,'rows':rows}
        print(name,json.dumps(results[name]['metrics']),flush=True)
    report={'dataset_sha256':manifest['reports/rag_eval_cases_v1.json'],'cases':len(dataset['cases']),
            'candidate':chunks.VERSION,'review_status':dataset['review_status'],'results':results,
            'source_hashes':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in ['diagnostic/semantic_chunks.py','diagnostic/book_chat.py']},
            'limitations':['Known development cases; independent review pending; not held-out accuracy.',
                           'Original page-and-substring relevance rules unchanged.',
                           'Context windows change chunks and recall denominators; inspect Hit/MRR and passages as well.',
                           'Page-hit does not measure passage sufficiency or mathematical correctness.',
                           'Elapsed time includes caches and model startup; not a controlled latency comparison.']}
    (OUT/'comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Retrieval v3 development comparison','',
           'Same 12 known development cases and unchanged page/substring relevance rules. Independent review pending.','',
           '| Arm | Evidence Hit@1 | Hit@2 | MRR@2 | Precision@2 | Chunk recall@2 | Anchor Hit@1 | Mean excerpt chars |',
           '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for name,result in results.items():
        m=result['metrics']
        lines.append('| '+name+' | '+' | '.join(f'{m[k]:.4f}' for k in ['hit_at_1','hit_at_2','mrr_at_2','precision_at_2','recall_at_2','anchor_hit_at_1','mean_top2_chars'])+' |')
    lines+=['','## Language-specific evidence retrieval','',
            '| Language | Arm | Hit@1 | Hit@2 | MRR@2 |',
            '| --- | --- | ---: | ---: | ---: |']
    for lang in ('en','hi'):
        for name in ('baseline','candidate'):
            m=results[name]['by_language'][lang]
            lines.append('| '+lang+' | '+name+' | '+' | '.join(f'{m[k]:.4f}' for k in ['hit_at_1','hit_at_2','mrr_at_2'])+' |')
    lines+=['','## Interpretation','',
            'Evidence metrics score the actual returned excerpt; anchor metrics score the text used for ranking before neighboring evidence is added.',
            'The same-context baseline isolates the benefit of evidence expansion from ranking changes. All expanded excerpts remain bounded to 650 characters and one page.',
            'Chunk recall denominators change with overlapping contexts. Do not present its change as corpus-wide recall or hide a regression.',
            'No benchmark labels were changed. Experiments used no cloud generation, learner database, or final scenario cases.',
            'attempt_01.json and attempt_02.json preserve the initial unsuccessful development experiments.',
            'The two place-value cases lack matching evidence in the candidate pool; related activities are not a verified direct lesson.',
            'These results do not establish mathematical correctness, held-out accuracy, statistical superiority, or learning benefit.','',
            'Reproduce: `venv/Scripts/python.exe scripts/evaluate_retrieval_improvements.py`']
    (OUT/'comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--audit-sources',action='store_true',help='Audit all concept citations instead of rerunning metrics.')
    args=parser.parse_args()
    if args.audit_sources:audit_sources()
    else:run()
