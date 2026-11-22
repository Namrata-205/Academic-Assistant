"""Export proposed bank expansion for review; never modify the runtime bank."""
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from diagnostic import engine,chat_tutor,textbooks
from diagnostic.tutor_bank import load
from diagnostic.followup_templates import expanded
from diagnostic.bilingual_quality import check_pair


def run():
    out=ROOT/'reports/personalization_v1';out.mkdir(exist_ok=True)
    destination=out/'bank_expansion_drafts.json'
    if destination.exists():raise ValueError('Existing draft pack preserved; create a new version to revise it.')
    nodes,_=engine.load_graph();bank=load();covered={q['concept_id'] for q in bank};catalog=textbooks.catalog()
    drafts=[];followups=[]
    for cid,node in nodes.items():
        if chat_tutor.practice(cid,nodes):followups.append(cid)
        if cid in covered:continue
        seen=set()
        for seed in range(16):
            q=expanded(cid,nodes,seed)
            if not q:break
            if q['en'] in seen:continue
            seen.add(q['en']);q['id']=f'REVIEW-{cid}-{len(seen)}'
            material=catalog.get('concepts',{}).get(cid,{})
            refs={lang:{k:v[k] for k in ('read_url','read_pdf_page','section') if k in v}
                  for lang,v in material.get('versions',{}).items()}
            drafts.append(dict(q,chapter=node['chapter'],catalog_references=refs,
                               support_relation=material.get('relation','unavailable'),
                               bilingual_checks=check_pair(q['en'],q['hi']),reviewer='',reviewed_at='',
                               independence_review='PENDING: parameter and label variations may test the same skill.',
                               source_support_review='PENDING: catalogue links are not proof this item is supported.'))
            if len(seen)==2:break
    report={'status':'AI-authored original drafts; independent educator review required. NOT loaded into the diagnostic bank.',
            'runtime_bank_items':len(bank),'runtime_bank_concepts':len(covered),'followup_supported_concepts':len(followups),
            'graph_concepts':len(nodes),'proposed_additional_concepts':len({q['concept_id'] for q in drafts}),
            'draft_items':drafts,'followup_concept_ids':followups,
            'runtime_bank_sha256':hashlib.sha256((ROOT/'diagnostic/question_bank.json').read_bytes()).hexdigest()}
    destination.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:(len(v) if k=='draft_items' else v) for k,v in report.items() if k!='followup_concept_ids'}))


if __name__=='__main__':run()
