"""Compare diversity on a fixed candidate pool and fixed source-span reference."""
import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch
from collections import defaultdict
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from diagnostic import semantic_chunks as chunks,book_chat as chat
from diagnostic.evaluate_rag import relevant,aggregate
from diagnostic.evaluate_retrieval_k import scores
from diagnostic.retrieval_diversity import span,length,intersection,budgeted_prefix
from scripts.evaluate_retrieval_improvements import module

OUT=ROOT/'reports/retrieval_v5'
KS=[1,2,3,5,10]


def intervals(sources):
    result=defaultdict(list)
    for row in sources:
        location=span(row)
        if location:
            key,interval=location;result[key].append(interval)
    return result


def coverage(sources,reference):
    selected=intervals(sources)
    denominator=sum(length(parts) for parts in reference.values())
    covered=sum(intersection(parts,selected.get(key,[])) for key,parts in reference.items())
    total=sum(len(s['excerpt']) for s in sources)
    unique=sum(length(parts) for parts in selected.values())
    return {'support_span_coverage':covered/denominator if denominator else None,
            'redundant_fraction':1-unique/total if total else 0.,'context_characters':total,
            'reference_characters':denominator}


def identity(row):
    return row['url'],row['excerpt'],row.get('context_char_start'),row.get('context_char_end')


def run():
    if chunks.VERSION!='graph-diverse-page-v5':
        raise ValueError('Historical v5 comparison preserved. Use evaluate_passage_reranker.py for the current version.')
    manifest=json.loads((OUT/'baseline_manifest.json').read_text())
    for name in ('semantic_chunks.py','hybrid_retrieval.py','book_chat.py'):
        if hashlib.sha256((OUT/('baseline_'+name)).read_bytes()).hexdigest()!=manifest['diagnostic/'+name]:
            raise ValueError('Baseline modified: '+name)
    case_path=ROOT/'reports/rag_eval_cases_v1.json'
    if hashlib.sha256(case_path.read_bytes()).hexdigest()!=manifest['reports/rag_eval_cases_v1.json']:
        raise ValueError('Benchmark changed.')
    baseline=module(OUT/'baseline_semantic_chunks.py','diagnostic._coverage_baseline')
    candidate=chunks.rank_pages;rows=[];rankings=[];policy_rows=[]
    dataset=json.loads(case_path.read_text(encoding='utf8'))
    for case in dataset['cases']:
        all_sources={}
        for arm,rank in [('v4_baseline',baseline['rank_pages']),('diverse',candidate)]:
            with patch.object(chunks,'rank_pages',rank):
                sources,_=chat.retrieve_sources(case['concept_id'],case['language'],case['question'],limit=None)
            if not sources or any(s.get('retrieval')=='page excerpt fallback' for s in sources):
                raise RuntimeError('Embedding retrieval unavailable.')
            all_sources[arm]=sources
        if set(map(identity,all_sources['v4_baseline']))!=set(map(identity,all_sources['diverse'])):
            raise ValueError('Candidate pool changed: '+case['id'])
        reference=intervals([s for s in all_sources['v4_baseline'] if relevant(s,case)])
        selected=budgeted_prefix(all_sources['diverse'])
        actual,_=chat.retrieve_sources(case['concept_id'],case['language'],case['question'],limit=3,max_chars=1300)
        if list(map(identity,selected))!=list(map(identity,actual)):
            raise ValueError('Live target policy differs from evaluated prefix.')
        for policy,chosen in [('v4_fixed_two',all_sources['v4_baseline'][:2]),('bounded_three',actual)]:
            count=sum(relevant(s,case) for s in chosen)
            relevant_total=sum(relevant(s,case) for s in all_sources['v4_baseline'])
            policy_rows.append({'case_id':case['id'],'language':case['language'],'policy':policy,
                                'returned_chunks':len(chosen),'precision':count/len(chosen) if chosen else 0.,
                                'recall':count/relevant_total if relevant_total else None,
                                'hit_rate':float(count>0),**coverage(chosen,reference)})
        for arm,sources in all_sources.items():
            flags=[relevant(s,case) for s in sources]
            for k in KS:
                rows.append({'case_id':case['id'],'language':case['language'],'arm':arm,'k':k,
                             **scores(flags,k),**coverage(sources[:k],reference)})
            rankings.append({'case_id':case['id'],'language':case['language'],'arm':arm,'sources':sources})
        print(case['id']+' fixed candidate pool verified',flush=True)
    keys=['precision','recall','hit_rate','mrr','support_span_coverage','redundant_fraction','context_characters']
    summary=[]
    for lang in ('all','en','hi'):
        for k in KS:
            for arm in ('v4_baseline','diverse'):
                selected=[r for r in rows if r['k']==k and r['arm']==arm and (lang=='all' or r['language']==lang)]
                summary.append({'language':lang,'k':k,'arm':arm,'cases':len(selected),
                                'recall_defined_cases':sum(r['recall'] is not None for r in selected),
                                **aggregate(selected,keys)})
    policy_summary=[]
    for lang in ('all','en','hi'):
        for policy in ('v4_fixed_two','bounded_three'):
            selected=[r for r in policy_rows if r['policy']==policy and (lang=='all' or r['language']==lang)]
            policy_summary.append({'language':lang,'policy':policy,
                                   **aggregate(selected,['precision','recall','hit_rate','support_span_coverage','redundant_fraction','context_characters','returned_chunks'])})
    report={'created_utc':datetime.now(timezone.utc).isoformat(),'version':chunks.VERSION,
            'dataset_sha256':manifest['reports/rag_eval_cases_v1.json'],'summary':summary,'rows':rows,'rankings':rankings,
            'target_policy':{'max_items':3,'max_characters':1300,'baseline_max_characters':1300},
            'policy_summary':policy_summary,'policy_rows':policy_rows,
            'source_hashes':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in
                 ['diagnostic/semantic_chunks.py','diagnostic/hybrid_retrieval.py','diagnostic/book_chat.py','diagnostic/retrieval_diversity.py']},
            'controls':'Same candidate excerpts, pages, relevance labels and context limits. Only result order changes.',
            'limits':['Known 12-case development set; independent review pending.',
                      'Original chunk recall retained; candidates are never removed or relabelled.',
                      'Support-span coverage is a new metric, not a replacement for chunk recall.',
                      'Reference spans are the union of baseline proxy-relevant excerpts in reconstructed-page coordinates.',
                      'Coverage measures overlapping source text, not independently reviewed facts or answer correctness.',
                      'Recall and support coverage exclude cases with no relevant candidate evidence.',
                      'The live policy may return three rather than two passages; both obey a 1300-character maximum, not identical actual lengths.',
                      'Policy precision uses actual returned count; fixed-k precision remains separately reported.',
                      'No generation, final scenario evaluation or learner database changes.']}
    (OUT/'comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    lines=['# Evidence diversity and fixed-reference coverage','',report['controls'],'',
           '| Language | k | Arm | Precision | Original recall | Hit | Support-span coverage | Redundant fraction |',
           '| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |']
    for r in summary:
        lines.append('| '+r['language']+' | '+str(r['k'])+' | '+r['arm']+' | '+' | '.join(f'{r[key]:.4f}' for key in ['precision','recall','hit_rate','support_span_coverage','redundant_fraction'])+' |')
    lines+=['','## Live target-evidence policy','',
            'Original recall below uses the same full baseline pool denominator. The bounded policy uses up to three passages within the original maximum of 1300 characters. The fixed-two arm uses up to two passages.','',
            '| Language | Policy | Precision | Original recall | Hit | Support-span coverage | Redundant fraction | Mean passages | Mean chars |',
            '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for r in policy_summary:
        lines.append('| '+r['language']+' | '+r['policy']+' | '+' | '.join(f'{r[key]:.4f}' for key in
             ['precision','recall','hit_rate','support_span_coverage','redundant_fraction','returned_chunks','context_characters'])+' |')
    lines+=['','## Interpretation and limits','']+['- '+s for s in report['limits']]
    lines+=['','Reproduce: `venv/Scripts/python.exe scripts/evaluate_evidence_coverage.py`','']
    (OUT/'comparison.md').write_text('\n'.join(lines),encoding='utf8')
    for row in policy_summary:print(json.dumps(row),flush=True)
    return report


if __name__=='__main__':run()
