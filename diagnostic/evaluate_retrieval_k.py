"""Compare retrieval depths using one unchanged ranking and relevance rule per case."""
import argparse
import hashlib
import json
from pathlib import Path
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


def run(ks,output_dir=None):
    if not ks or any(k<1 for k in ks):raise ValueError('Use positive retrieval depths.')
    ks=sorted(set(ks))
    destination=Path(output_dir) if output_dir is not None else OUT
    destination.mkdir(parents=True,exist_ok=True)
    path=OUT/'rag_eval_cases_v1.json';dataset=json.loads(path.read_text(encoding='utf-8'))
    rows=[];rankings=[]
    for case in dataset['cases']:
        print(case['id'],flush=True)
        sources,_=chat.retrieve_sources(case['concept_id'],case['language'],case['question'],limit=None)
        if not sources or any(s.get('retrieval')=='page excerpt fallback' for s in sources):
            raise RuntimeError('Embedding retrieval unavailable: '+case['id'])
        flags=[relevant(source,case) for source in sources]
        anchors=[relevant(dict(source,excerpt=source.get('matched_excerpt',source['excerpt'])),case) for source in sources]
        rankings.append({'case_id':case['id'],'language':case['language'],'question':case['question'],
                         'relevance_flags':flags,'anchor_relevance_flags':anchors,'ranked_sources':sources})
        for k in ks:
            anchor_scores=scores(anchors,k)
            rows.append({'case_id':case['id'],'language':case['language'],'k':k,**scores(flags,k),
                         'anchor_hit_rate':anchor_scores['hit_rate'],'anchor_mrr':anchor_scores['mrr'],
                         'context_characters':sum(len(s['excerpt']) for s in sources[:k])})
    keys=['precision','recall','hit_rate','mrr','returned_chunks','anchor_hit_rate','anchor_mrr','context_characters']
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
              'source_hashes':{name:hashlib.sha256((OUT.parent/name).read_bytes()).hexdigest() for name in
                              ['diagnostic/semantic_chunks.py','diagnostic/hybrid_retrieval.py','diagnostic/book_chat.py']},
              'ks':ks,'summary':summary,'rankings':rankings,
              'limits':['Development cases with page-and-substring relevance proxy; independent review pending.',
                        'One fixed ranking per case, truncated at each k. No generation calls or live app retrieval settings changed.',
                        'Precision uses k slots, with missing results counting as irrelevant. Recall excludes zero-evidence cases.',
                        'Recall is within concept-scoped catalogued pages, not the full textbook corpus.',
                        f"MRR and Hit@k use all {len(rankings)} cases, including {sum(not any(r['relevance_flags']) for r in rankings)} cases with no proxy-relevant chunk in the scoped pool.",
                        'Selecting k on these cases is development tuning, not an independently validated optimum.']}
    write_csv(destination/'rag_k_comparison.csv',summary);write_csv(destination/'rag_k_case_results.csv',rows)
    (destination/'rag_k_comparison.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Retrieval depth comparison','',
           '| Language | k | Precision@k | Recall@k | MRR@k | Hit@k | Cases | Recall-defined cases |',
           '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for row in summary:
        lines.append(f"| {row['language']} | {row['k']} | {row['precision']:.4f} | {row['recall']:.4f} | {row['mrr']:.4f} | {row['hit_rate']:.4f} | {row['cases']} | {row['recall_defined_cases']} |")
    lines+=['','## Ranking anchors and context cost','',
            '| Language | k | Anchor Hit@k | Anchor MRR@k | Mean returned chunks | Mean context characters |',
            '| --- | ---: | ---: | ---: | ---: | ---: |']
    for row in summary:
        lines.append(f"| {row['language']} | {row['k']} | {row['anchor_hit_rate']:.4f} | {row['anchor_mrr']:.4f} | {row['returned_chunks']:.2f} | {row['context_characters']:.1f} |")
    lines+=['','Precision = relevant chunks in top k / k. Recall = relevant chunks in top k / all proxy-relevant chunks in the scoped pool, averaged only where that denominator is positive. MRR = mean reciprocal rank of the first relevant result within k; absent relevant results score zero. Hit@k = proportion of cases with any relevant top-k result. Values are proportions, not percentages.',
            'Anchor metrics score the original passage before neighboring context is added. Context characters include overlap and are not tokenizer counts. This is a retrieval-only sweep; larger k has not been evaluated for generated-answer quality.','',*['- '+limit for limit in metadata['limits']]]
    (destination/'rag_k_comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return metadata


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--ks',type=int,nargs='+',default=[1,2,3,5,10])
    parser.add_argument('--output-dir',type=Path,default=OUT);args=parser.parse_args()
    if any(k<1 for k in args.ks):parser.error('k must be positive')
    run(sorted(set(args.ks)),args.output_dir)
