"""Compare frozen expectations without tuning the mapper to reported errors."""
import hashlib
import json
from diagnostic.engine import ROOT,load_graph,map_question,legacy_map_question

def evaluate():
    path=ROOT/'reports/semantic_holdout_v2.json'
    dataset=json.loads(path.read_text(encoding='utf-8'));nodes,edges=load_graph()
    results=[]
    for method,mapper in [('legacy',legacy_map_question),('semantic-v2',map_question)]:
        for case in dataset['cases']:
            output=mapper(case['question'],nodes,edges)
            actual=output.get('concept_id','clarify')
            results.append({'id':case['id'],'method':method,'question':case['question'],'expected':case['expected'],
                            'actual':actual,'correct':actual==case['expected'],'abstained':actual=='clarify',
                            'false_mapping':actual!='clarify' and actual!=case['expected'],
                            'mapping_method':output.get('method',''), 'similarity':output.get('similarity')})
    summary={method:{'cases':len(dataset['cases']),
                     'expectation_matches':sum(r['correct'] for r in results if r['method']==method),
                     'false_mappings':sum(r['false_mapping'] for r in results if r['method']==method),
                     'clarifications':sum(r['abstained'] for r in results if r['method']==method)} for method in ('legacy','semantic-v2')}
    model_manifest=json.loads((ROOT/'assets/models/multilingual-minilm/manifest.json').read_text(encoding='utf-8'))
    from diagnostic.semantic_mapper import MIN_SIMILARITY,MIN_MARGIN
    output={'case_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'expectation_review':dataset['review_status'],
            'model_repository':model_manifest['repository'],'model_revision':model_manifest['revision'],
            'minimum_similarity':MIN_SIMILARITY,'minimum_margin':MIN_MARGIN,
            'summary':summary,'results':results,'limitation':'Small development holdout, not an independently reviewed measure of semantic understanding.'}
    (ROOT/'reports/semantic_mapping_results_v2.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2));return output

if __name__=='__main__':evaluate()
