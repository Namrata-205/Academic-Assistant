"""Compare metadata-aware graph retrieval with previous and graph-only retrieval."""
import hashlib
import json
import subprocess
from pathlib import Path
from unittest.mock import patch
from diagnostic import book_chat as chat, semantic_chunks as chunks
from diagnostic.evaluate_rag import relevant, retrieval_scores, aggregate, ratio


def run():
    source=subprocess.check_output(['git','show','HEAD:diagnostic/semantic_chunks.py']).decode('utf-8')
    baseline={'__name__':'diagnostic._baseline_chunks'}
    exec(compile(source,'baseline_chunks.py','exec'),baseline)
    path=Path('reports/rag_eval_cases_v1.json')
    dataset=json.loads(path.read_text(encoding='utf-8'))
    keys=['hit_at_1','hit_at_2','mrr_at_2','precision_at_2','recall_at_2']
    results={}
    for name,rank in [('previous',baseline['rank_pages']),('graph_only',baseline['rank_pages']),('graph_metadata',chunks.rank_pages)]:
        rows=[]
        chunks.page_index.cache_clear();chunks.contextual_vectors.cache_clear()
        baseline['page_index'].cache_clear()
        # The graph-only arm uses the same graph chunks but plain cosine ranking.
        original=baseline['rank_pages'].__globals__['page_index']
        if name=='graph_only':baseline['rank_pages'].__globals__['page_index']=chunks.page_index
        try:
            with patch.object(chunks,'rank_pages',rank):
                for case in dataset['cases']:
                    sources,_=chat.retrieve_sources(case['concept_id'],case['language'],case['question'],limit=None)
                    if not sources or any(s.get('retrieval')!='semantic cosine similarity' for s in sources):
                        raise RuntimeError('Embedding retrieval unavailable: '+case['id'])
                    flags=[relevant(s,case) for s in sources]
                    rows.append({'case_id':case['id'],'language':case['language'],**retrieval_scores(flags),
                                 'recall_at_2':ratio(sum(flags[:2]),sum(flags)),
                                 'chunks':len(sources),'relevant_chunks':sum(flags),'top_sources':sources[:2]})
        finally:baseline['rank_pages'].__globals__['page_index']=original
        results[name]={'metrics':aggregate(rows,keys),'by_language':{lang:aggregate([r for r in rows if r['language']==lang],keys) for lang in ('en','hi')},'rows':rows}
        print(name,json.dumps(results[name]['metrics']),flush=True)
    report={'cases':len(dataset['cases']),'dataset_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'review_status':dataset['review_status'],'candidate':chunks.VERSION,
            'baseline_source_sha256':hashlib.sha256(source.encode()).hexdigest(),
            'weights':{'evidence':.75,'contextual_metadata':.15,'concept_coverage':.10},'results':results,
            'limitations':['Development cases, independent review pending; no held-out accuracy claim.',
                           'Relevance uses page and substring matches, not generated answer correctness.',
                           'Recall denominators depend on chunk boundaries.',
                           'Graph arms include a corrected Hindi sentence delimiter.']}
    Path('reports/graph_metadata_comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':run()
