"""Validate independent review records; final readiness also checks frozen settings."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from diagnostic import engine as e
from diagnostic.prepare_scenarios import settings_manifest,validate,PROFILES


def readiness(root,review_path=None,final=False):
    root=Path(root);case_path=root/'cases.json'
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    if hashlib.sha256(case_path.read_bytes()).hexdigest()!=manifest['cases_sha256']:
        raise ValueError('Frozen scenario file changed; create a new version.')
    data=json.loads(case_path.read_text(encoding='utf-8'));validation=validate(data)
    with Path(review_path or root/'blind_review.csv').open(encoding='utf-8-sig',newline='') as handle:
        rows=list(csv.DictReader(handle))
    lookup={row['case_id']:row for row in rows}
    if len(lookup)!=len(rows) or set(lookup)!={case['id'] for case in data['cases']}:
        raise ValueError('Review must contain exactly one record per scenario.')
    nodes,_=e.load_graph();approved=[];pending=[];issues=[]
    for case in data['cases']:
        row=lookup[case['id']]
        if row.get('decision')!='APPROVED':pending.append(case['id']);continue
        required=('reviewer','reviewed_at','label_reason','reviewer_expected_result')
        if any(not row.get(key,'').strip() for key in required):issues.append(case['id']+': missing review fields');continue
        if row.get('translation_meaning_checked')!='YES' or row.get('passages_checked')!='YES':
            issues.append(case['id']+': translation/source review incomplete');continue
        if row.get('reviewer_profile') not in PROFILES:issues.append(case['id']+': invalid profile');continue
        try:gaps=json.loads(row['reviewer_gap_concepts'])
        except (ValueError,TypeError):issues.append(case['id']+': gap concepts must be a JSON list');continue
        if not isinstance(gaps,list) or any(cid not in nodes for cid in gaps):issues.append(case['id']+': unknown gap concept');continue
        approved.append(case['id'])
    settings_match=data['settings']==settings_manifest()
    result={**validation,'independently_approved':len(approved),'pending':pending,'issues':issues,
            'frozen_settings_match':settings_match,'final_ready':not pending and not issues and settings_match}
    if final and not result['final_ready']:raise ValueError('Final evaluation is gated: finish independent review and preserve frozen settings. '+json.dumps(result))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=e.ROOT/'reports/scenarios_v1')
    parser.add_argument('--review',type=Path);parser.add_argument('--final',action='store_true')
    args=parser.parse_args();print(json.dumps(readiness(args.root,args.review,args.final),indent=2))
