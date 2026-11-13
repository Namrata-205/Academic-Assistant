"""Compare retrieval depths using one unchanged ranking and relevance rule per case."""
import argparse
import hashlib
import json
from datetime import datetime,timezone
from diagnostic import book_chat as chat,semantic_chunks as chunks
from diagnostic.evaluate_rag import OUT,aggregate,ratio,relevant,write_csv


def scores(flags,k):
    if k<1:raise ValueError('k must be positive')
    count=sum(flags[:k]);total=sum(flags)
    return {'precision':count/k,'recall':ratio(count,total),
            'hit_rate':float(count>0),
            'mrr':next((1/(i+1) for i,value in enumerate(flags[:k]) if value),0.),
            'returned_chunks':min(k,len(flags)),'relevant_in_pool':total}


def run(ks):
    path=OUT/'rag_eval_cases_v1.json';dataset=json.loads(path.read_text(encoding='utf-8'))
    rows=[];rankings=[]
    for case in dataset['cases']:
        print(case['id'],flush=True)
        sources,_=chat.retrieve_sources(case['concept_id'],case['language'],case['question'],limit=None)
        flags=[relevant(source,case) for source in sources]
        rankings.append({'case_id':case['id'],'language':case['language'],'question':case['question'],
                         'relevance_flags':flags,'ranked_sources':sources})
        for k in ks:
            rows.append({'case_id':case['id'],'language':case['language'],'k':k,**scores(flags,k)})
    keys=['precision','recall','hit_rate','mrr','returned_chunks']
    summary=[]
    for language in ('all','en','hi'):
        for k in ks:
            selected=[row for row in rows if row['k']==k and (language=='all' or row['language']==language)]
            summary.append({'language':language,'k':k,'cases':len(selected),
                            'recall_defined_cases':sum(r['recall'] is not None for r in selected),
                            **aggregate(selected,keys)})
    metadata={'created_utc':datetime.now(timezone.utc).isoformat(),'review_status':dataset['review_status'],
              'cases_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
              'catalog_sha256':hashlib.sha256((OUT.parent/'diagnostic/textbook_catalog.json').read_bytes()).hexdigest(),
              'chunk_config':{'version':chunks.VERSION,'break_cosine':chunks.BREAK_SIMILARITY,'max_chars':chunks.MAX_CHARS},
              'ks':ks,'summary':summary,'rankings':rankings,
              'limits':['Development cases with page-and-substring relevance proxy; independent review pending.',
                        'One fixed ranking per case, truncated at each k. No generation calls or live app retrieval settings changed.',
                        'Precision uses k slots, with missing results counting as irrelevant. Recall excludes zero-evidence cases.',
                        'Recall is within concept-scoped catalogued pages, not the full textbook corpus.',
                        f"MRR and Hit@k use all {len(rankings)} cases, including {sum(not any(r['relevance_flags']) for r in rankings)} cases with no proxy-relevant chunk in the scoped pool.",
                        'Selecting k on these cases is development tuning, not an independently validated optimum.']}
    write_csv(OUT/'rag_k_comparison.csv',summary);write_csv(OUT/'rag_k_case_results.csv',rows)
    (OUT/'rag_k_comparison.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Retrieval depth comparison','',
           '| Language | k | Precision@k | Recall@k | MRR@k | Hit@k | Cases | Recall-defined cases |',
           '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for row in summary:
        lines.append(f"| {row['language']} | {row['k']} | {row['precision']:.4f} | {row['recall']:.4f} | {row['mrr']:.4f} | {row['hit_rate']:.4f} | {row['cases']} | {row['recall_defined_cases']} |")
    lines+=['','Precision = relevant chunks in top k / k. Recall = relevant chunks in top k / all proxy-relevant chunks in the scoped pool, averaged only where that denominator is positive. MRR = mean reciprocal rank of the first relevant result within k; absent relevant results score zero. Hit@k = proportion of cases with any relevant top-k result. Values are proportions, not percentages.','',*['- '+limit for limit in metadata['limits']]]
    (OUT/'rag_k_comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return metadata


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--ks',type=int,nargs='+',default=[1,2,3,5,10]);args=parser.parse_args()
    if any(k<1 for k in args.ks):parser.error('k must be positive')
    run(sorted(set(args.ks)))
