"""Reproducible development metrics. No LLM judge or fabricated human ratings.

Run: python -m diagnostic.evaluate_rag --generation-cases 2
"""
import argparse
import csv
import hashlib
import json
import time
import tempfile
import unicodedata
from datetime import datetime,timezone
from statistics import mean
from pathlib import Path
from unittest.mock import patch
from diagnostic import engine as e,book_chat as chat,semantic_chunks as chunks

OUT=e.ROOT/'reports'


def ratio(n,d):return n/d if d else None


def normalize(text):
    return ' '.join(unicodedata.normalize('NFKC',text).replace('\u200d','').replace('\u200c','').casefold().split())


def relevant(source,case):
    return source['pdf_page'] in case['pdf_pages'] and all(normalize(term) in normalize(source['excerpt']) for term in case['evidence_all'])


def retrieval_scores(relevances):
    return {'hit_at_1':float(any(relevances[:1])), 'hit_at_2':float(any(relevances[:2])),
            'mrr_at_2':next((1/(i+1) for i,value in enumerate(relevances[:2]) if value),0.),
            'precision_at_2':sum(relevances[:2])/2}


def aggregate(rows,keys):
    return {key:mean(values) if (values:=[r[key] for r in rows if r[key] is not None]) else None for key in keys}


def write_csv(path,rows):
    if not rows:return
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def mapping_metrics():
    path=OUT/'semantic_holdout_v2.json';dataset=json.loads(path.read_text(encoding='utf-8'))
    nodes,edges=e.load_graph();results=[]
    for case in dataset['cases']:
        actual=e.map_question(case['question'],nodes,edges).get('concept_id','clarify')
        results.append({'id':case['id'],'expected':case['expected'],'actual':actual})
    mapped=[r for r in results if r['actual']!='clarify'];unsupported=[r for r in results if r['expected']=='clarify']
    expected_mapped=[r for r in results if r['expected']!='clarify']
    return {'cases':len(results),'accuracy':ratio(sum(r['actual']==r['expected'] for r in results),len(results)),
            'mapped_precision':ratio(sum(r['actual']==r['expected'] for r in mapped),len(mapped)),
            'supported_concept_recall':ratio(sum(r['actual']==r['expected'] for r in expected_mapped),len(expected_mapped)),
            'clarification_recall':ratio(sum(r['actual']=='clarify' for r in unsupported),len(unsupported)),
            'false_mapping_rate':ratio(sum(r['actual']!='clarify' and r['actual']!=r['expected'] for r in results),len(results)),
            'dataset_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'review_status':dataset['review_status'],'results':results}


def personalisation_metrics():
    from diagnostic.chat_context import context
    nodes,edges=e.load_graph();target='MATH6_C0025';foundation='MATH6_C0020'
    questions=[q for q in e.load_bank() if q['concept_id']==foundation][:2]
    fixtures=[('unassessed',[],'Unassessed'),('difficulty',[0,0],'Possible prerequisite difficulty'),
              ('understanding',[1,1],'Evidence supports understanding'),('mixed',[1,0],'Insufficient evidence'),
              ('one_error',[0],'Insufficient evidence'),('unscorable',[None,None],'Insufficient evidence')]
    results=[]
    with tempfile.TemporaryDirectory() as tmp:
        conn=e.connect(Path(tmp)/'evaluation.sqlite3')
        try:
            for name,scores,expected in fixtures:
                sid=e.new_session(conn,name,target,'graph-guided',[])
                for i,score in enumerate(scores):
                    conn.execute('INSERT INTO responses VALUES (?,?,?,?,?,?)',(sid,i,questions[i]['id'],foundation,'synthetic',score))
                conn.commit();output=context(conn,name,target,nodes,edges)
                actual=next(r['status'] for r in output['learning_evidence'] if r['concept_id']==foundation)
                results.append({'case':name,'check':'evidence_status','passed':actual==expected})
                stranger=context(conn,'unrelated-learner',target,nodes,edges)
                results.append({'case':name,'check':'learner_isolation','passed':all(c['status']=='Unassessed' for c in stranger['learning_evidence'])})
                if name=='difficulty':results.append({'case':name,'check':'weak_foundation_first','passed':output['selected_prerequisites'][0]==foundation})
            background={'items':[{'concept_ids':[foundation],'topic':'angle','source_signal':'Source report suggests further checking','source_status':'pending'}]}
            with patch('diagnostic.chat_context.imported_reports.linked_context',return_value=background):
                output=context(conn,'background-only',target,nodes,edges)
            results.append({'case':'imported_pending','check':'background_not_promoted_to_diagnosis',
                            'passed':bool(output['imported_background']) and all(c['status']=='Unassessed' for c in output['learning_evidence'])})
        finally:conn.close()
    write_csv(OUT/'rag_personalisation_results.csv',results)
    return {'synthetic_checks':len(results),'passed':sum(r['passed'] for r in results),
            'pass_rate':ratio(sum(r['passed'] for r in results),len(results)),
            'interpretation':'Functional policy checks, not educational effectiveness or personalised explanation quality.'}


def run(generation_cases=0):
    path=OUT/'rag_eval_cases_v1.json';dataset=json.loads(path.read_text(encoding='utf-8'));rows=[];review=[]
    for case in dataset['cases']:
        print('Retrieval '+case['id'],flush=True)
        # Cold caches are reset per case. Model runtime can remain warm from earlier cases.
        chunks.page_index.cache_clear();start=time.perf_counter()
        sources,_=chat.retrieve_sources(case['concept_id'],case['language'],case['question'])
        cold=time.perf_counter()-start;start=time.perf_counter()
        warm,_=chat.retrieve_sources(case['concept_id'],case['language'],case['question'])
        elapsed=time.perf_counter()-start
        flags=[relevant(s,case) for s in sources]
        all_sources,_=chat.retrieve_sources(case['concept_id'],case['language'],case['question'],limit=None)
        total_relevant=sum(relevant(s,case) for s in all_sources)
        row={'case_id':case['id'],'language':case['language'],**retrieval_scores(flags),
             'recall_at_2':ratio(sum(flags[:2]),total_relevant),'relevant_in_search_pool':total_relevant,
             'semantic_retrieval':all(s.get('retrieval') in ('semantic cosine similarity','hybrid BM25 + semantic RRF') for s in sources) and bool(sources),
             'cold_page_cache_seconds':round(cold,4),'warm_page_cache_seconds':round(elapsed,4),
             'retrieved_pages':json.dumps([s['pdf_page'] for s in sources]),'question':case['question']}
        rows.append(row)
        review.append({'case_id':case['id'],'question':case['question'],'language':case['language'],
                       'retrieved_passages':json.dumps(sources,ensure_ascii=False),'answer':'',
                       'relevance_1_to_5':'','mathematical_correctness_1_to_5':'','source_support_1_to_5':'',
                       'hindi_terminology_1_to_5':'','personalisation_1_to_5':'','reviewer':'','review_notes':''})
    generation=[]
    # Interleave language pairs rather than selecting only English cases.
    for case in dataset['cases'][:generation_cases]:
        print('Generation '+case['id'],flush=True);start=time.perf_counter()
        answer=chat.answer(case['question'],case['language'],case['concept_id'])
        sources={s['id']:s for s in answer.get('sources',[])};paragraphs=answer.get('paragraphs',[])
        cited=sum(bool(p.get('citations')) for p in paragraphs)
        valid=sum(all(s in sources for s in p.get('citations',[])) and bool(p.get('citations')) for p in paragraphs)
        spans=sum(any(normalize(p.get('evidence','')) in normalize(sources[s]['excerpt']) for s in p.get('citations',[]) if s in sources) and len(p.get('evidence',''))>=20 for p in paragraphs)
        generation.append({'case_id':case['id'],'language':case['language'],'status':answer['status'],'mode':answer.get('mode'),
                           'latency_seconds':round(time.perf_counter()-start,4),'paragraphs':len(paragraphs),
                           'cited_paragraphs':cited,'valid_citation_paragraphs':valid,'exact_evidence_paragraphs':spans})
        next(r for r in review if r['case_id']==case['id'])['answer']=json.dumps(answer,ensure_ascii=False)
    keys=['hit_at_1','hit_at_2','mrr_at_2','precision_at_2','recall_at_2','cold_page_cache_seconds','warm_page_cache_seconds']
    paragraphs=sum(r['paragraphs'] for r in generation)
    summary={'created_utc':datetime.now(timezone.utc).isoformat(),'evaluation_type':'Synthetic development evaluation, not learner outcome evidence',
             'review_status':dataset['review_status'],'cases_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
             'catalog_sha256':hashlib.sha256((e.ROOT/'diagnostic/textbook_catalog.json').read_bytes()).hexdigest(),
             'chunk_config':{'version':chunks.VERSION,'break_cosine':chunks.BREAK_SIMILARITY,'max_chars':chunks.MAX_CHARS},
             'model_status':chat.model_status(),'retrieval':{'cases':len(rows),**aggregate(rows,keys),
                 'recall_defined_cases':sum(r['recall_at_2'] is not None for r in rows),
                 'no_relevant_evidence_cases':sum(r['relevant_in_search_pool']==0 for r in rows),
                 'by_language':{lang:aggregate([r for r in rows if r['language']==lang],keys) for lang in ('en','hi')}},
             'mapping':mapping_metrics(),
             'personalisation':personalisation_metrics(),
             'generation':{'cases':len(generation),'generated_answer_rate':ratio(sum(r['mode']=='generated' for r in generation),len(generation)),
                 'fallback_rate':ratio(sum(r['mode']=='extractive' for r in generation),len(generation)),
                 'citation_coverage':ratio(sum(r['cited_paragraphs'] for r in generation),paragraphs),
                 'citation_id_validity':ratio(sum(r['valid_citation_paragraphs'] for r in generation),paragraphs),
                 'exact_evidence_span_rate':ratio(sum(r['exact_evidence_paragraphs'] for r in generation),paragraphs),
                 'mean_latency_seconds':mean(r['latency_seconds'] for r in generation) if generation else None},
             'human_quality_metrics':{'status':'Not measured; reviewer worksheet supplied','correctness':None,'faithfulness':None,'terminology':None,'helpfulness':None},
             'limitations':['Known development cases, independent review pending; no statistical generalisation.',
               'Retrieval relevance is an explicit page-and-substring proxy, not human-rated semantic relevance. Precision@2 uses two slots; missing results count as failures.',
               'Concept IDs are supplied to retrieval tests; mapping is evaluated separately. Search is limited to catalogued concept pages.',
               'Recall@2 is macro-averaged only over cases with at least one proxy-relevant chunk in the scoped search pool; zero-evidence cases are reported separately. This is not corpus-wide recall.',
               'No baseline superiority claim: no comparable retrieval baseline was run.',
               'Citation IDs and copied evidence do not establish factual entailment. Excerpt fallbacks can score perfectly on structural checks.',
               'Generation without a learner history does not measure personalised answer quality. No real learner improvement was measured.',
               'Latency is sequential on this machine; cold page cache does not mean cold OS or model cache.']}
    write_csv(OUT/'rag_retrieval_results.csv',rows);write_csv(OUT/'rag_generation_results.csv',generation)
    # Preserve completed reviews: each run gets a new worksheet.
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    write_csv(OUT/f'rag_human_review_{stamp}.csv',review)
    (OUT/'rag_metrics.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Development evaluation results','',summary['evaluation_type']+'. Independent review pending.','',
           '| Metric | Value |','| --- | --- |']
    for name,value in [('Retrieval cases',len(rows)),*[(k,summary['retrieval'][k]) for k in keys],
                       ('Recall-defined cases',summary['retrieval']['recall_defined_cases']),
                       ('Cases without relevant evidence',summary['retrieval']['no_relevant_evidence_cases']),
                       *[(f'Mapping {k}',summary['mapping'][k]) for k in ('cases','accuracy','mapped_precision','supported_concept_recall','clarification_recall','false_mapping_rate')],
                       *[(f'Personalisation {k}',summary['personalisation'][k]) for k in ('synthetic_checks','passed','pass_rate')],
                       *[(f'Generation {k}',v) for k,v in summary['generation'].items()]]:
        lines.append(f'| {name} | {value:.4f} |' if isinstance(value,float) else f'| {name} | {value if value is not None else "Not measured"} |')
    lines+=['','All proportions are 0–1. Latencies are seconds. Hit@k: any proxy-relevant passage in the first k results. MRR@2: reciprocal rank of the first relevant passage, zero if absent. Precision@2: relevant retrieved passages / 2. Mapping accuracy includes correct clarification. Mapped precision conditions on a returned concept. Supported recall conditions on an expected concept; clarification recall conditions on an expected clarification. False-mapping rate uses all mapping cases as denominator.','',
            'Recall@2 = relevant chunks retrieved in the first two / all proxy-relevant chunks in the concept-scoped search pool. Average only cases with nonzero relevant evidence; zero-evidence cases are separately counted. This differs from Hit@2 and is not corpus-wide recall.',
            '', 'Generation rates use tested requests; citation rates use returned paragraphs (including excerpt fallbacks). Zero denominators are not measured. Human correctness, faithfulness, terminology and learning benefit remain unmeasured.','',
            '## Limits','',*['- '+x for x in summary['limitations']]]
    (OUT/'rag_results.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--generation-cases',type=int,default=0)
    args=parser.parse_args()
    if not 0<=args.generation_cases<=12:parser.error('generation-cases must be between 0 and 12')
    run(args.generation_cases)
