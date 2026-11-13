"""Current-mapper paired synthetic pilot; immutable item-level response fixtures."""
import csv
import hashlib
import json
import re
from datetime import datetime,timezone
from diagnostic import engine as e

OUT=e.ROOT/'reports'
CASES=OUT/'pilot_final_v3_cases.json'


def validate_cases(dataset,bank):
    cases=dataset['cases']
    if len(cases)!=20 or len({c['id'] for c in cases})!=20:raise ValueError('Expected twenty distinct cases.')
    for case in cases:
        if case['language']=='hi' and case['input'] and not re.search('[\u0900-\u097f]',case['input']):
            raise ValueError('Hindi input is missing Devanagari text; check export encoding.')
        if set(case['responses'])!={q['id'] for q in bank}:raise ValueError('Each case needs exactly one frozen response per bank item.')
        if any('?' in value for value in case['responses'].values()):raise ValueError('Corrupted or placeholder response in frozen case.')


def write_csv(path,rows):
    if not rows:return
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def run_case(case,method,bank,nodes,edges):
    mapping=e.map_question(case['input'],nodes,edges);actual=mapping.get('concept_id','clarify')
    current=[]
    if mapping['status']=='mapped':
        for _ in range(3):
            q=e.select_question(actual,bank,edges,current,method=method)
            if q is None:break
            response=case['responses'][q['id']]
            current.append({'question_id':q['id'],'concept_id':q['concept_id'],'response':response,'score':e.score(q,response)})
    correct=false=unresolved=insufficient_matches=not_evaluable=0;statuses=[]
    expected_target=case['expected_mapping']
    opportunities=e.eligible(expected_target,bank,edges) if expected_target!='clarify' else []
    report=e.make_report(actual,bank,edges,current) if actual!='clarify' else None
    report_rows={r['concept_id']:r for r in (report or {}).get('concepts',[])}
    for cid in opportunities:
        row=report_rows.get(cid);assessed=bool(row and row['assessment']=='Assessed')
        status=row['status'] if assessed else 'Unassessed';expected=case['expected_statuses'][cid]
        if status in ('Unassessed','Insufficient evidence'):
            unresolved+=1
            insufficient_matches+=status=='Insufficient evidence' and expected=='Insufficient evidence'
        elif status==expected:correct+=1
        else:false+=1
        statuses.append({'concept_id':cid,'expected':expected,'actual':status,'assessed':assessed})
    for cid,row in report_rows.items():
        if cid not in opportunities and row['assessment']=='Assessed':not_evaluable+=1
    return {'case_id':case['id'],'language':case['language'],'response_mode':case['response_mode'],'method':method,
            'expected_mapping':expected_target,'actual_mapping':actual,'mapping_correct':actual==expected_target,
            'mapping_reason':mapping.get('reason',mapping.get('method','')),
            'correct_diagnoses':correct,'false_diagnoses':false,'unresolved_concepts':unresolved,
            'insufficient_evidence_agreements':insufficient_matches,'off_target_assessed_concepts':not_evaluable,
            'case_unresolved':bool(unresolved or actual!=expected_target),
            'questions_asked':len(current),'question_ids':json.dumps([r['question_id'] for r in current]),
            'observations':json.dumps(current,ensure_ascii=False),'statuses':json.dumps(statuses,ensure_ascii=False)}


def run():
    dataset=json.loads(CASES.read_text(encoding='utf-8'));bank=e.load_bank();nodes,edges=e.load_graph()
    if hashlib.sha256(e.BANK_PATH.read_bytes()).hexdigest()!=dataset['bank_sha256']:
        raise ValueError('Question bank changed since case freeze; create a separately versioned pilot.')
    validate_cases(dataset,bank)
    results=[run_case(case,method,bank,nodes,edges) for case in dataset['cases'] for method in ('fixed','graph-guided')]
    keys=['mapping_correct','correct_diagnoses','false_diagnoses','unresolved_concepts','insufficient_evidence_agreements',
          'off_target_assessed_concepts','case_unresolved','questions_asked']
    totals={method:{key:sum(int(row[key]) for row in results if row['method']==method) for key in keys} for method in ('fixed','graph-guided')}
    metadata={'created_utc':datetime.now(timezone.utc).isoformat(),'study_type':dataset['study_type'],
              'independent_review':'PENDING','case_count':20,'max_questions':3,'history':'empty per method and case',
              'case_sha256':hashlib.sha256(CASES.read_bytes()).hexdigest(),'bank_sha256':dataset['bank_sha256'],
              'graph_sha256':hashlib.sha256(e.graph_source_path().read_bytes()).hexdigest(),
              'rules':e.RULES,'mapper':'current production map_question','results':totals,'case_results':results}
    write_csv(OUT/'pilot_final_v3_results.csv',results)
    (OUT/'pilot_final_v3_summary.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    # Separate expected-label and blind-review files. Never overwrite filled reviewer files.
    blind=[];expected=[]
    for case in dataset['cases']:
        relevant=e.eligible(case['expected_mapping'],bank,edges) if case['expected_mapping']!='clarify' else []
        expected.append({'case_id':case['id'],'expected_mapping':case['expected_mapping'],
                         'expected_statuses':json.dumps({cid:case['expected_statuses'][cid] for cid in relevant}),
                         'review_status':case['review_status']})
        blind.append({'case_id':case['id'],'input':case['input'],'language':case['language'],
                      'item_response_pack':json.dumps([{'question_id':q['id'],'concept':q['concept_en'],'question_en':q['en'],
                          'question_hi':q['hi'],'response':case['responses'][q['id']],'answer_key':q['answer']} for q in bank],ensure_ascii=False),
                      'reviewer_expected_mapping':'','reviewer_concept_statuses':'','reviewer':'','reviewed_at':'','notes':''})
    write_csv(OUT/'pilot_final_v3_draft_expectations.csv',expected)
    review_path=OUT/'pilot_final_v3_blind_review.csv'
    if not review_path.exists():write_csv(review_path,blind)
    lines=['# Paired diagnostic pilot — final candidate v3','',
           '**Synthetic cases; independent expectation review pending. Not a real-learner study.**','',
           'Twenty cases were frozen before this execution, separately from development tests. The inputs use known development topics; this is not a claim of an unseen holdout. Existing legacy pilot files remain unchanged.','',
           '| Measure | Fixed | Graph-guided |','| --- | ---: | ---: |']
    for key in keys:lines.append(f"| {key.replace('_',' ')} | {totals['fixed'][key]} | {totals['graph-guided'][key]} |")
    lines+=['','## Per-case comparison','','C = correct conclusive labels; F = false conclusive labels; U = unresolved eligible concepts; Q = questions. Expected clarifications with no diagnosis are successful routing, not unresolved diagnostic cases.','',
            '| Case | Language | Response profile | Mapping matches | Fixed C/F/U/Q | Guided C/F/U/Q |',
            '| --- | --- | --- | --- | --- | --- |']
    for case in dataset['cases']:
        pair=[r for r in results if r['case_id']==case['id']];a,b=pair
        fmt=lambda r:'/'.join(str(r[k]) for k in ('correct_diagnoses','false_diagnoses','unresolved_concepts','questions_asked'))
        lines.append(f"| {case['id']} | {case['language']} | {case['response_mode']} | {a['mapping_correct']} | {fmt(a)} | {fmt(b)} |")
    lines+=['','## Protocol and metric definitions','',
            '- The same bank, empty initial history, eligible target/direct-prerequisite concepts and maximum three questions are used by both methods. Neither method receives the simulated learner profile.',
            '- Fixed selection sorts concept ID then item ID and is response-independent. Graph-guided selection uses the production rule below and can stop before three questions. Both use the same scoring and decision rules.',
            '- Each item has one frozen response per case, independent of method and question order. Hindi numerical responses use Devanagari digits. No student records are written.',
            '- Correct/false diagnoses count conclusive concept labels against the draft synthetic profile. Insufficient evidence and unassessed concepts are unresolved, not correct/false diagnoses; appropriate insufficient-label agreements are separately counted.',
            '- Opportunity counts use bank-covered targets and direct prerequisites for the EXPECTED mapped target, so unexpected clarification cannot remove a case from the denominator. Off-target assessments are separately reported.',
            '- An expected clarification is successful routing, with no diagnostic opportunity. An incorrect mapping or clarification makes a case unresolved. Cases may include multiple concept opportunities.',
            '- This compares question-selection strategies, not prerequisite-graph construction or RAG retrieval. Both methods use the graph to define eligible concepts, so no causal claim about the graph itself follows.','',e.RULES,'',
            '## Observed outcomes and limits','']
    wrong=[r['case_id'] for r in results if r['method']=='fixed' and not r['mapping_correct']]
    lines.append('Mapping disagreements against draft expectations: '+(', '.join(wrong) if wrong else 'none')+'.')
    lines.append(f"Graph-guided used {totals['fixed']['questions_asked']-totals['graph-guided']['questions_asked']} fewer questions overall. This is an observed stopping/selection difference on these fixtures, not proof of greater educational usefulness.")
    for case in dataset['cases']:
        rows=[r for r in results if r['case_id']==case['id']]
        if any(r['unresolved_concepts'] or not r['mapping_correct'] or r['false_diagnoses'] for r in rows):
            reasons=[]
            if not rows[0]['mapping_correct']:reasons.append('mapping mismatch/clarification: '+rows[0]['mapping_reason'])
            if case['response_mode']=='mixed':reasons.append('mixed answers do not support a conclusive concept label')
            if case['response_mode']=='ambiguous' and case['expected_mapping']!='clarify':reasons.append('unclear responses consume budget but provide no knowledge evidence')
            if any(r['unresolved_concepts'] for r in rows):reasons.append('limited evidence and/or untested eligible concepts remain unresolved within the three-question budget')
            if any(r['false_diagnoses'] for r in rows):reasons.append('a conclusive label disagrees with the draft profile; independent item/evidence review required')
            lines.append('- '+case['id']+': '+'; '.join(reasons)+'.')
    lines+=['','Review `pilot_final_v3_blind_review.csv` independently before consulting the draft expectations or method outputs. The item pack provides all potential item responses, not an actual sequence of thirty asked questions. An independent reviewer can disagree with the author; preserve disagreements and version any revised cases. Do not label this study final or independently validated until review is completed.','',
            'Synthetic responses omit guessing, language barriers, fatigue and genuine misconceptions. The bank, decision rules and graph remain provisional. Zero false diagnoses does not imply perfect accuracy when many concepts remain unresolved. No real learning gain or statistically established superiority is claimed.']
    (OUT/'pilot_final_v3_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return metadata


if __name__=='__main__':print(json.dumps(run()['results'],indent=2))
