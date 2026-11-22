"""Export selection shortlists; compute missed gold prerequisites only after review."""
import argparse
import json
from pathlib import Path
from diagnostic import engine as e
from diagnostic.tutor_bank import load
from diagnostic.tutor_selection import choose,prerequisite_rank_audit


def run(reference_path=None):
    nodes,edges=e.load_graph();bank=load();covered={q['concept_id'] for q in bank}
    references=json.loads(Path(reference_path).read_text(encoding='utf-8')) if reference_path else []
    gold={row['target']:row for row in references if row.get('review_status')=='APPROVED' and row.get('reviewer')}
    result=[];review=[]
    for target in sorted(nodes):
        direct=e.prerequisites(target,edges)
        if not direct:continue
        _,audit=choose(target,bank,edges)
        row={'target':target,'target_en':nodes[target]['en'],'target_hi':nodes[target]['hi'],
             'all_graph_prerequisites':direct,'without_bank_items':sorted(set(direct)-covered),
             'candidate_ranking':audit['candidates'],
             'review_status':'APPROVED' if target in gold else 'PENDING'}
        if target in gold:row['reference_metrics']=prerequisite_rank_audit(target,gold[target]['important_prerequisites'],bank,edges)
        result.append(row)
        review.append({'target':target,'important_prerequisites':[],'reason':'','review_status':'PENDING','reviewer':''})
    report={'policy':'adaptive-chat-v2','reviewed_targets':len(gold),'targets':result,
            'interpretation':'No prerequisite recall is claimed without independently reviewed important-prerequisite labels. These are graph and bank coverage diagnostics.'}
    (e.ROOT/'reports/prerequisite_selection_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    review_path=e.ROOT/'reports/prerequisite_reference_review.json'
    if not review_path.exists():review_path.write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'targets':len(result),'reviewed_targets':len(gold)}))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--references',type=Path)
    args=parser.parse_args();run(args.references)
