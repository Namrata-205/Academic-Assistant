"""Author 60 paired scenario drafts and a blind review pack without predictions."""
import csv
import argparse
import hashlib
import json
import sys
from importlib import metadata
from datetime import datetime,timezone
from pathlib import Path
from diagnostic import engine as e,textbooks
from diagnostic.tutor_bank import load
from diagnostic.bilingual_quality import check_pair

TARGETS = [
 ('MATH6_C0003','development','Continue the pattern 5, 10, 15, 20.','5, 10, 15, 20 का पैटर्न आगे बढ़ाइए।'),
 ('MATH6_C0009','development','Explain why 36 can form a square arrangement.','समझाइए कि 36 बिंदुओं से वर्गाकार व्यवस्था क्यों बन सकती है।'),
 ('MATH6_C0006','final_candidate','How can I decide whether 47 is odd?','मैं कैसे तय करूँ कि 47 विषम है?'),
 ('MATH6_C0007','final_candidate','How can I decide whether 58 is even?','मैं कैसे तय करूँ कि 58 सम है?'),
 ('MATH6_C0024','development','Why does a quarter turn measure 90 degrees?','एक चौथाई घुमाव का माप 90 अंश क्यों है?'),
 ('MATH6_C0025','development','Explain why an angle of 35 degrees is acute.','समझाइए कि 35 अंश का कोण न्यून कोण क्यों है।'),
 ('MATH6_C0026','final_candidate','How do I classify an angle of 125 degrees?','मैं 125 अंश के कोण का वर्गीकरण कैसे करूँ?'),
 ('MATH6_C0027','final_candidate','How do I classify an angle of 240 degrees?','मैं 240 अंश के कोण का वर्गीकरण कैसे करूँ?'),
 ('MATH6_C0038','development','Explain the value of 6 in 4625.','4625 में 6 का स्थानीय मान समझाइए।'),
 ('MATH6_C0039','development','How do I find the digit sum of 673?','मैं 673 के अंकों का योग कैसे निकालूँ?'),
 ('MATH6_C0036','final_candidate','How does 8 represent a collection of objects?','8 वस्तुओं के समूह को कैसे दर्शाता है?'),
 ('MATH6_C0041','final_candidate','Start at 7 and move 4 steps right on a number line.','संख्या रेखा पर 7 से शुरू करके 4 कदम दाईं ओर चलिए।')]

PROFILES={
 'prerequisite_gap':('I need help with a foundation before this topic.','इस विषय से पहले मुझे एक आधारभूत बात समझने में मदद चाहिए।',
                     'Consistently incorrect independent items on the author-designated foundation; other items correct.'),
 'no_apparent_gap':('Please check what I already understand.','कृपया जाँचें कि मैं क्या समझता हूँ।',
                    'All item responses correct; conclude only about foundations actually tested.'),
 'calculation_slip':('I may have made a calculation slip; please check.','शायद मुझसे गणना में चूक हुई है; कृपया जाँचें।',
                     'One numerical error, remaining items correct; mixed responses must not establish a gap.'),
 'language_confusion':('I am not sure what the question words mean.','मुझे प्रश्न के शब्दों का अर्थ स्पष्ट नहीं है।',
                      'Initial item needs wording clarification; all other items correct. Language cause is an author hypothesis, not inferred from a wrong answer.'),
 'insufficient_evidence':('I cannot give a clear answer yet.','अभी मैं स्पष्ट उत्तर नहीं दे सकता।',
                          'All initial responses unscorable; insufficient evidence, with unasked foundations unassessed.')}

FROZEN_FILES=['diagnostic/chat_tutor.py','diagnostic/tutor_selection.py','diagnostic/tutor_bank.py',
              'diagnostic/book_chat.py','diagnostic/chat_provider.py','diagnostic/chat_router.py',
              'diagnostic/semantic_chunks.py','diagnostic/semantic_mapper.py','diagnostic/bilingual_glossary.json',
              'diagnostic/bilingual_quality.py','diagnostic/teaching_feedback.py','diagnostic/question_bank.json',
              'diagnostic/textbook_catalog.json','src/AngleDiagram.jsx','src/ChatTutor.jsx','src/BookChat.jsx',
              'requirements.txt','requirements-semantic.txt','package-lock.json']


def settings_manifest():
    from diagnostic.chat_provider import configuration,DEFAULT_GEMINI_MODEL
    config=configuration()
    packages={}
    for name in ('PyMuPDF','pypdfium2','wordfreq','numpy'):
        try:packages[name]=metadata.version(name)
        except metadata.PackageNotFoundError:packages[name]='not installed in venv'
    model_manifest=e.ROOT/'assets/models/multilingual-minilm/manifest.json'
    return {'files':{name:hashlib.sha256((e.ROOT/name).read_bytes()).hexdigest() for name in FROZEN_FILES},
            'graph_sha256':hashlib.sha256(e.graph_source_path().read_bytes()).hexdigest(),
            'python':sys.version,'packages':packages,
            'embedding_model_manifest_sha256':hashlib.sha256(model_manifest.read_bytes()).hexdigest() if model_manifest.exists() else None,
            'provider':config.get('ATLAS_CHAT_PROVIDER','gemini'),
            'model':config.get('ATLAS_CHAT_MODEL',DEFAULT_GEMINI_MODEL),'question_limit':3}


def wrong(q):
    return next(letter for letter in 'ABCD' if letter!=q['answer']) if q['type']=='mcq' else str(int(q['answer'])+1)


def passage_records(cid,language):
    from diagnostic.book_chat import page_content
    cat=textbooks.catalog(); material=cat['concepts'].get(cid,{})
    version=material.get('versions',{}).get(language)
    if not version:return [{'concept_id':cid,'availability':'unavailable'}]
    filename=version['read_url'].split('/')[-1].split('#')[0]
    path=e.ROOT/'assets/textbooks'/language/filename
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    expected=next(d['sha256'] for d in cat['documents'] if d['filename']==filename and d['language']==language)
    if digest!=expected:raise ValueError('Textbook changed; rebuild catalog before authoring cases.')
    page=version['read_pdf_page']
    excerpt=' '.join(page_content(str(path),page,path.stat().st_mtime_ns))
    return [{'concept_id':cid,'chapter_title':version['chapter_title'],'section':version['section'],
             'pdf_page':page,'printed_page':version['read_printed_page'],'url':version['read_url'],
             'sha256':digest,'excerpt':excerpt,'relation':material.get('relation','unspecified'),
             'availability':'available' if excerpt else 'empty','review_status':'PENDING'}]


def build():
    nodes,edges=e.load_graph();bank=load();covered={q['concept_id'] for q in bank};cases=[]
    for target,split,en,hi in TARGETS:
        direct=sorted(set(e.prerequisites(target,edges)) & covered)
        if not direct:raise ValueError('Scenario target needs a bank-covered foundation: '+target)
        focus=direct[0] # Author designation, not a system prediction; reviewer may disagree.
        focus_items=sorted((q for q in bank if q['concept_id']==focus),key=lambda q:q['id'])
        numerical=next((q for q in focus_items if q['type']=='numeric'),focus_items[0])
        for profile,(suffix_en,suffix_hi,reason) in PROFILES.items():
            case_id=f'SC{len(cases)+1:03}'
            variants={}
            for language,question in [('en',en+' '+suffix_en),('hi',hi+' '+suffix_hi)]:
                responses={q['id']:q['answer'] for q in bank}
                if profile=='prerequisite_gap':
                    for q in focus_items:responses[q['id']]=wrong(q)
                elif profile=='calculation_slip':responses[numerical['id']]=wrong(numerical)
                elif profile=='language_confusion':responses[focus_items[0]['id']]='Please explain the wording' if language=='en' else 'कृपया प्रश्न के शब्द समझाइए'
                elif profile=='insufficient_evidence':responses={q['id']:'not sure' if language=='en' else 'मुझे नहीं पता' for q in bank}
                variants[language]={'question':question,'responses':responses,
                                    'clarification_responses':{q['id']:q['answer'] for q in bank},
                                    'textbook_passages':passage_records(target,language)+passage_records(focus,language)}
            pair=check_pair(variants['en']['question'],variants['hi']['question'])
            if not pair['passed']:raise ValueError((case_id,pair))
            cases.append({'id':case_id,'family_id':target,'split':split,'chapter':nodes[target]['chapter'],
                          'target_concept_id':target,'author_focus_concept_id':focus,'profile':profile,
                          'draft_expected_result':{'gap_concepts':[focus] if profile=='prerequisite_gap' else [],
                            'evidence_expectation':'Insufficient evidence' if profile in ('calculation_slip','insufficient_evidence') else
                            'Confirm wording before interpreting the response' if profile=='language_confusion' else
                            'Possible prerequisite difficulty' if profile=='prerequisite_gap' else 'Evidence supports understanding'},
                          'label_reason':reason,'review_status':'PENDING','translation_invariants':pair,'variants':variants})
    return {'version':'learner-scenarios-v1','created_utc':datetime.now(timezone.utc).isoformat(),
            'status':'AI-authored synthetic drafts; independent review required before final evaluation.',
            'settings':settings_manifest(),'bank':bank,'cases':cases,
            'protocol':{'distinct_scenarios':60,'language_variants':120,'development':30,'final_candidate':30,
                        'split_unit':'concept family; both languages and all five profiles stay together',
                        'response_access':'A method receives only the response for the item it actually asks.',
                        'limitations':['Same fixed question bank across cases; these are synthetic response profiles, not learners.',
                                       'Final candidates are not an unseen human benchmark. Do not tune settings against them.',
                                       'A calculation-slip or language-confusion cause cannot be established by score patterns alone.',
                                       'Related-only source records are not direct lessons. Review source suitability independently.']}}


def validate(data):
    cases=data['cases'];ids={case['id'] for case in cases}
    if len(cases)!=60 or len(ids)!=60:raise ValueError('Expected 60 distinct paired scenarios.')
    families={};bank={q['id'] for q in data['bank']}
    for case in cases:
        family=case['family_id']
        if family in families and families[family]!=case['split']:raise ValueError('Family split leakage')
        families[family]=case['split']
        if set(case['variants'])!={'en','hi'}:raise ValueError('Missing language pair')
        for variant in case['variants'].values():
            if set(variant['responses'])!=bank:raise ValueError('Incomplete potential-item response pack')
        if not check_pair(case['variants']['en']['question'],case['variants']['hi']['question'])['passed']:
            raise ValueError('Translation invariant mismatch')
    return {'scenarios':60,'variants':120,'families':len(families),'reviewed':sum(c['review_status']=='APPROVED' for c in cases)}


def run(output=None):
    root=Path(output) if output else e.ROOT/'reports/scenarios_v1'
    if root.exists():raise FileExistsError('Refusing to overwrite a frozen scenario or review pack.')
    data=build();data['freeze_id']=root.name;validate(data);root.mkdir(parents=True)
    (root/'cases.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    fields=['case_id','family_id','split','question_en','question_hi','item_pack','passages',
            'reviewer_profile','reviewer_gap_concepts','reviewer_expected_result','label_reason',
            'translation_meaning_checked','passages_checked','decision','reviewer','reviewed_at','notes']
    with (root/'blind_review.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for case in data['cases']:
            writer.writerow({'case_id':case['id'],'family_id':case['family_id'],'split':case['split'],
                'question_en':case['variants']['en']['question'],'question_hi':case['variants']['hi']['question'],
                'item_pack':json.dumps([dict(q,responses={lang:case['variants'][lang]['responses'][q['id']] for lang in ('en','hi')}) for q in data['bank']],ensure_ascii=False),
                'passages':json.dumps({lang:case['variants'][lang]['textbook_passages'] for lang in ('en','hi')},ensure_ascii=False)})
    (root/'manifest.json').write_text(json.dumps({'cases_sha256':hashlib.sha256((root/'cases.json').read_bytes()).hexdigest(),
        'validation':validate(data),'protocol':data['protocol'],'settings':data['settings']},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(validate(data)))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path)
    run(parser.parse_args().output)
