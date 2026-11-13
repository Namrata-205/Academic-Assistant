"""Scoped learner evidence and bounded, reproducible prerequisite expansion."""
from diagnostic import engine as e,imported_reports


def context(conn,learner,target,nodes,edges,extra_observations=()):
    direct=e.prerequisites(target,edges)
    relevant={target,*direct};observations=(e.history(conn,learner) if conn is not None else [])+list(extra_observations)
    evidence=[]
    for cid in sorted(relevant):
        # Most recent observations on distinct items, never repeated attempts as independent evidence.
        seen=set();recent=[]
        for row in reversed(observations):
            if row['concept_id']==cid and row['question_id'] not in seen:
                seen.add(row['question_id']);recent.append({'score':row['score']})
                if len(recent)==3:break
        evidence.append({'concept_id':cid,'concept':nodes[cid]['en'],
                         'status':e.status(recent) if recent else 'Unassessed',
                         'valid_observations':sum(r['score'] is not None for r in recent),
                         'source':'saved learning checks'})
    imported=imported_reports.linked_context(conn,learner,target,nodes,edges) if conn is not None else None
    background=[{k:item[k] for k in ('concept_ids','topic','source_signal','source_status')} for item in (imported or {}).get('items',[])]
    weak={r['concept_id'] for r in evidence if r['status']=='Possible prerequisite difficulty'}
    suggested={cid for item in background if item['source_status'] in ('confirmed','pending','revision') for cid in item['concept_ids']}
    bank_concepts={q['concept_id'] for q in e.load_bank()}
    def rank(cid):
        confidence=max((float(edge.get('confidence') or 0) for edge in edges if edge['source_id']==cid and edge['target_id']==target),default=0)
        # Prefer concrete, bank-covered foundations over broad chapter-level nodes
        # when no learner evidence distinguishes them. This does not infer mastery.
        return (cid not in weak,cid not in suggested,cid not in bank_concepts,-confidence,cid)
    selected=sorted(direct,key=rank)[:2]
    return {'prerequisites':[{'concept_id':cid,'concept':nodes[cid]['en'],'selected_for_explanation':cid in selected} for cid in direct],
            'selected_prerequisites':selected,'learning_evidence':evidence,'imported_background':background,
            'notice':'Saved checks are limited evidence, not mastery. Imported reports are separate background without assessment dates. Graph relationships await human review. Unassessed concepts are not weaknesses.'}
