"""Extend stable legacy items with distinct original probes for the active graph."""
import json
from collections import Counter
from diagnostic import engine
from diagnostic.curriculum_items import make


def build():
    nodes,_=engine.load_graph()
    bank=json.loads((engine.ROOT/'diagnostic/question_bank.json').read_text(encoding='utf-8'))
    covered={q['concept_id'] for q in bank}
    for q in bank:
        q['concept_en']=nodes[q['concept_id']]['en'];q['concept_hi']=nodes[q['concept_id']]['hi']
    for cid in nodes:
        if cid in covered:continue
        seen=set()
        for seed in range(6):
            q=make(cid,nodes,seed,1)
            if not q:raise ValueError('No curriculum question: '+cid)
            identity=(q['en'],q['hi'])
            if identity in seen:continue
            seen.add(identity)
            q.update(id=f'CQ2_{cid}_{len(seen)}',version=engine.VERSION,reviewer='',review_date='')
            bank.append(q)
            if len(seen)==3:break
        if len(seen)<2:raise ValueError('Not enough distinct probes: '+cid)
    target=engine.ROOT/'diagnostic/question_bank_v2.json'
    target.write_text(json.dumps(bank,ensure_ascii=False,indent=2),encoding='utf-8')
    from diagnostic.curriculum_content import fact
    from diagnostic.bilingual_quality import check_pair
    glossary={}
    for cid,node in nodes.items():
        en,hi=fact(cid);parity=check_pair(en,hi)
        if not parity['passed']:raise ValueError('Bilingual definition invariant failed: '+cid)
        glossary[cid]=dict(concept_id=cid,en=node['en'],hi=node['hi'],definition_en=en,definition_hi=hi,
            invariant_check=parity,review_status='PENDING',reviewer='',reviewed_at='',
            provenance='Original bilingual curriculum-v2 draft; source references are separately audited.')
    (engine.ROOT/'diagnostic/bilingual_glossary_v2.json').write_text(json.dumps({'version':'bilingual-glossary-v2','concepts':glossary},ensure_ascii=False,indent=2),encoding='utf-8')
    counts=Counter(nodes[q['concept_id']]['chapter'] for q in bank)
    print(json.dumps({'items':len(bank),'concepts':len({q['concept_id'] for q in bank}),'chapters':dict(counts)}))


if __name__=='__main__':build()
