"""Development-only response oracle: methods see only answers they ask for."""
import argparse
import json
from pathlib import Path
from diagnostic import engine as e
from diagnostic.tutor_selection import choose


class Responses:
    def __init__(self,variant,bank):
        self._responses=variant['responses'];self._bank={q['id']:q for q in bank};self.asked=[]

    def ask(self,item_id):
        if len(self.asked)>=3:raise ValueError('Three-question limit reached')
        if item_id in self.asked:raise ValueError('An item may not be repeated')
        if item_id not in self._bank:raise ValueError('Unknown item')
        self.asked.append(item_id)
        return self._responses[item_id]


def run(root):
    data=json.loads((Path(root)/'cases.json').read_text(encoding='utf-8'));nodes,edges=e.load_graph()
    # Final-candidate records are never passed to this runner.
    results=[]
    for case in (row for row in data['cases'] if row['split']=='development'):
        for language,variant in case['variants'].items():
            oracle=Responses(variant,data['bank']);current=[];log=[]
            for _ in range(3):
                q,audit=choose(case['target_concept_id'],data['bank'],edges,current)
                log.append(audit)
                if not q:break
                response=oracle.ask(q['id'])
                current.append({'question_id':q['id'],'concept_id':q['concept_id'],
                                'response':response,'score':e.score(q,response)})
            results.append({'case_id':case['id'],'language':language,'questions_asked':len(current),
                            'observations':current,'selection_log':log,
                            'status_by_tested_concept':{cid:e.status([r for r in current if r['concept_id']==cid]) for cid in {r['concept_id'] for r in current}}})
    report={'kind':'Development functional replay, not independent diagnostic accuracy',
            'variants':len(results),'final_candidates_evaluated':0,'results':results}
    output=Path(root)/'development_replay.json'
    if output.exists():raise FileExistsError('Preserve replay logs; use a new output version.')
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'variants':len(results),'final_candidates_evaluated':0,'max_questions':max(r['questions_asked'] for r in results)}))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=e.ROOT/'reports/scenarios_v1')
    run(parser.parse_args().root)
