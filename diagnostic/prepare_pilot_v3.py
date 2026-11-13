"""Repair transport-corrupted draft fixtures; never tune labels to measured results."""
import json
from diagnostic import engine as e


def prepare():
    root=e.ROOT/'reports';path=root/'pilot_final_v3_cases.json'
    if path.exists():raise ValueError('Version 3 already frozen; do not overwrite.')
    data=json.loads((root/'pilot_final_v2_cases.json').read_text(encoding='utf-8'))
    hindi={2:'समकोण का माप क्या होता है?',4:'न्यून कोण को समझाइए।',6:'स्थानीय मान समझाइए।',
           8:'अंकों का योग कैसे ज्ञात करें?',10:'रेखाखंड समझाइए।',12:'कोण कैसे बनता है?',
           14:'वर्ग संख्या समझाइए।',16:'भिन्नों को जोड़ना समझाइए।',18:'विषम संख्या समझाइए।'}
    for i,case in enumerate(data['cases'],1):
        if i in hindi:case['input']=hindi[i]
        for cid in sorted({q['concept_id'] for q in e.load_bank()}):
            mode=case['concept_modes'].get(cid,case['response_mode'])
            for j,q in enumerate(sorted([q for q in e.load_bank() if q['concept_id']==cid],key=lambda q:q['id'])):
                if mode=='ambiguous':answer='मुझे नहीं पता' if case['language']=='hi' else 'not sure'
                elif mode=='correct' or (mode=='mixed' and j!=0):answer=q['answer']
                else:answer=next(c for c in 'ABCD' if c!=q['answer']) if q['type']=='mcq' else str(int(q['answer'])+1)
                if case['language']=='hi' and q['type']=='numeric':answer=answer.translate(str.maketrans('0123456789','०१२३४५६७८९'))
                case['responses'][q['id']]=answer
    data['version']='pilot-final-candidate-v3'
    data['revision_reason']='Correct Hindi transport corruption in v2 inputs/responses. English inputs, modes and expected labels unchanged. V2 is invalid and retained for audit.'
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    (root/'pilot_final_v2_INVALID.md').write_text('Version 2 is INVALID: Hindi inputs/responses were replaced by question marks during export. Do not use its metrics. Version 3 corrects the transport encoding only; modes, expected labels and English queries are unchanged.\n',encoding='utf-8')


if __name__=='__main__':prepare()
