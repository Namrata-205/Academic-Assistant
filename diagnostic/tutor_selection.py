"""Auditable, response-dependent chat selection; frozen pilot rules stay separate."""
from diagnostic import engine as e

VERSION = 'adaptive-chat-v3'


def choose(target, bank, edges, current=(), prior=(), contrast=False,exposed=()):
    """Return one item and a key-free explanation of its candidate ranking."""
    direct = set(e.prerequisites(target, edges))
    pool = [q for q in bank if q['concept_id'] in direct]
    if contrast:
        pool = [q for q in bank if q['id'].startswith('TQ_ANGLE_DISTINCTION_')]
    elif not pool:
        pool = [q for q in bank if q['concept_id'] == target]
    concepts = sorted({q['concept_id'] for q in pool})
    used = {r['question_id'] for r in [*prior, *current]}|set(exposed)
    candidates = []
    for cid in concepts:
        recent = []; seen = set()
        for row in reversed(prior):
            if row['concept_id'] == cid and row['question_id'] not in seen:
                recent.append(row); seen.add(row['question_id'])
                if len(recent) == 2: break
        observed = [r for r in current if r['concept_id'] == cid]
        evidence = list(reversed(recent)) + observed
        valid = [r for r in evidence if r['score'] is not None]
        available = sorted((q for q in pool if q['concept_id'] == cid and q['id'] not in used), key=lambda q:q['id'])
        confidence = max((float(edge.get('confidence') or 0) for edge in edges
                          if edge['source_id'] == cid and edge['target_id'] == target), default=0.)
        unresolved = e.status(evidence) == 'Insufficient evidence'
        needs_confirmation = len(valid) == 1 or bool(observed and observed[-1]['score'] is None)
        rank = (not needs_confirmation, cid == target, -confidence, cid)
        candidates.append({'concept_id':cid, 'graph_confidence':confidence,
                           'valid_observations':len(valid), 'available_items':len(available),
                           'needs_confirmation':needs_confirmation, 'unresolved':unresolved,
                           'next_item_id':available[0]['id'] if available else None,
                           'rank':rank})
    candidates.sort(key=lambda row:row['rank'])
    choice = next((row for row in candidates if row['unresolved'] and row['available_items']), None)
    exhausted = len(current) >= 3
    qid = choice['next_item_id'] if choice and not exhausted else None
    reason = ('three_question_limit' if exhausted else 'no_unused_unresolved_items' if not choice else
              'confirm_unclear_or_single_observation' if choice['needs_confirmation'] else
              'graph_prerequisite_with_available_item' if choice['concept_id'] in direct else 'target_fallback')
    audit = {'policy':VERSION, 'ordinal':len(current)+1, 'target':target,
             'selected_item_id':qid, 'selected_concept_id':choice['concept_id'] if qid else None,
             'reason':reason, 'candidates':[{k:v for k,v in row.items() if k!='rank'} for row in candidates],
             'question_budget_remaining':max(0,3-len(current))}
    return next((q for q in pool if q['id']==qid), None), audit


def prerequisite_rank_audit(target, reference_ids, bank, edges, prior=()):
    """Audit important gold prerequisites missed at ranks 3/5; never invent gold."""
    _, audit = choose(target, bank, edges, prior=prior)
    ranked = [row['concept_id'] for row in audit['candidates']]
    gold = set(reference_ids)
    return {'target':target, 'reference_prerequisites':sorted(gold), 'ranked_bank_covered_candidates':ranked,
            **{f'recall_at_{k}':len(gold & set(ranked[:k]))/len(gold) if gold else None for k in (3,5)},
            **{f'missed_at_{k}':sorted(gold-set(ranked[:k])) for k in (3,5)},
            'not_in_graph':sorted(gold-set(e.prerequisites(target,edges))),
            'without_bank_items':sorted(gold-{q['concept_id'] for q in bank})}
