"""Public teaching controls and original, rotated angle transfer questions."""
from uuid import uuid4
from diagnostic import engine as e

ACTIONS = {'simpler','another_example','still_confused','language_help'}
LABELS={
 'en':{'simpler':'Simpler explanation','another_example':'Show another example','still_confused':'I still don’t understand','language_help':'Explain the terms'},
 'hi':{'simpler':'सरल भाषा में समझाइए','another_example':'एक और उदाहरण','still_confused':'अभी भी समझ नहीं आया','language_help':'शब्दों का अर्थ समझाइए'}}


def feedback_label(action,language):
    return LABELS.get(language,LABELS['en']).get(action,action)


INSTRUCTIONS = {
 'build_on_understanding':'Build on the checked foundations. Keep their recap brief, explain the target, and give a new transfer task. Do not claim mastery.',
 'check_uncertainty':'Evidence is limited or mixed. Explain the target cautiously, clarify the named foundation, and ask a fresh check. Do not label a prerequisite gap.',
 'review_practice':'Recent practice suggests this foundation may benefit from review. Give a brief recap and a fresh check without treating practice scores as a diagnosis.',
 'simpler':'Use short sentences, define each technical term, and give one small worked example.',
 'another_example':'Give a different complete worked example from the previous teaching example.',
 'still_confused':'Start with the named foundation, explain it step by step, then connect it to the target. Do not infer a diagnosis.',
 'language_help':'Clarify the canonical mathematical terms in the chosen answer language. Keep all numbers, units and mathematical meaning unchanged.',
 'angle_contrast':'Contrast a right angle (90 degrees) with a straight angle (180 degrees). Rotation changes orientation, not angle measure.'}


def public_teaching_request(request):
    nodes,_=e.load_graph()
    mode=request.get('mode')
    if mode not in INSTRUCTIONS:return {}
    focus=request.get('focus',{})
    cid=request.get('focus_concept_id') or (focus.get('id') if isinstance(focus,dict) else None)
    result={'mode':mode,'instruction':INSTRUCTIONS[mode]}
    if cid in nodes:result['focus']={k:nodes[cid][k] for k in ('id','en','hi')}
    variant=request.get('example_variant')
    if type(variant) is int and 0<=variant<=10000:
        result['example_variant']=variant
        from diagnostic.followup_templates import worked_example
        example=worked_example(nodes[cid]['en'],variant) if cid in nodes else None
        if example:result['worked_example']=example
    previous=request.get('previous_example_variant')
    if type(previous) is int and 0<=previous<=10000 and cid in nodes:
        from diagnostic.followup_templates import worked_example
        result['previous_example_variant']=previous
        example=worked_example(nodes[cid]['en'],previous)
        if example:result['previous_worked_example']=example
    return result


def original_example_paragraph(request,sources,language):
    request=public_teaching_request(request)
    if not request.get('worked_example'):return None
    cid=request.get('focus',{}).get('id')
    source=next((s for s in sources if cid in s.get('concept_ids',[s.get('concept_id')])
                 and s.get('support_relation','direct')=='direct'),None)
    if not source:return None
    from diagnostic.bilingual_quality import check_arithmetic
    text=request['worked_example'][language];check_arithmetic(text)
    label='Original worked example: ' if language=='en' else 'मौलिक हल किया हुआ उदाहरण: '
    return {'text':label+text,'citations':[source['id']],'evidence':source['excerpt'],
            'kind':'original_worked_example','review_status':'PENDING'}


def teaching_decision(report,target):
    assessed=[r for r in report['concepts'] if r['assessment']=='Assessed']
    gaps=[r for r in assessed if r['status']=='Possible prerequisite difficulty']
    if gaps:
        chosen=next((r for r in gaps if r['concept_id']!=target),gaps[0])
        return {'mode':'still_confused','focus_concept_id':chosen['concept_id'],'reason':'consistent_difficulty_evidence'}
    if assessed and all(r['status']=='Evidence supports understanding' for r in assessed):
        return {'mode':'build_on_understanding','focus_concept_id':target,'reason':'checked_foundations_supported'}
    unclear=next((r['concept_id'] for r in assessed if r['status']=='Insufficient evidence'),target)
    return {'mode':'check_uncertainty','focus_concept_id':unclear,'reason':'limited_mixed_or_unassessed_evidence'}


def context_decision(context,target):
    selected=context.get('selected_prerequisites',[])
    evidence={r['concept_id']:r for r in context.get('learning_evidence',[])}
    weak=next((cid for cid in [*selected,target] if evidence.get(cid,{}).get('status')=='Possible prerequisite difficulty'),None)
    if weak:return {'mode':'still_confused','focus_concept_id':weak,'reason':'saved_check_difficulty'}
    review=next((r['concept_id'] for r in context.get('activity_evidence',[]) if r['incorrect'] and r['concept_id'] in [*selected,target]),None)
    if review:return {'mode':'review_practice','focus_concept_id':review,'reason':'activity_review_signal_not_diagnosis'}
    if selected and all(evidence.get(cid,{}).get('status')=='Evidence supports understanding' for cid in selected):
        return {'mode':'build_on_understanding','focus_concept_id':target,'reason':'saved_checked_foundations_supported'}
    return {'mode':'check_uncertainty','focus_concept_id':target,'reason':'limited_saved_evidence'}


def angle_item(rotation=0, straight=False, item_id=None):
    angle=180 if straight else 90
    return {'id':item_id or 'transfer-'+uuid4().hex,'concept_id':'MATH6_C0024',
            'concept_en':'right angle','concept_hi':'समकोण','type':'mcq','answer':'B' if straight else 'A',
            'en':'Identify the angle in the diagram. A: right angle; B: straight angle.',
            'hi':'चित्र में कोण पहचानें। A: समकोण; B: सरल कोण।',
            'diagram':{'kind':'angle','degrees':angle,'rotation':rotation},
            'feedback_en':f'The angle measures {angle}°. Turning the whole diagram does not change its measure.',
            'feedback_hi':f'कोण का माप {angle}° है। पूरे चित्र को घुमाने से उसका माप नहीं बदलता।',
            'review_status':'PENDING','possible_difficulty':'May confuse angle measure with orientation; confirm before drawing conclusions.',
            'source_references':[],'scoring_rule':'Exact MCQ key; other input unscorable.'}


def angle_comparison_item(variant=0):
    item = dict(angle_item(), diagram=None, comparison=True)
    if variant % 2:
        item.update(en='How many right angles together make a straight angle? A: 1; B: 2; C: 4.',
                    hi='कितने समकोण मिलकर एक सरल कोण बनाते हैं? A: 1; B: 2; C: 4।',
                    answer='B', feedback_en='180° ÷ 90° = 2.', feedback_hi='180° ÷ 90° = 2।')
    else:
        item.update(en='How much larger is a straight angle than a right angle? A: 45°; B: 90°; C: 180°.',
                    hi='सरल कोण समकोण से कितना बड़ा है? A: 45°; B: 90°; C: 180°।',
                    answer='B', feedback_en='180° − 90° = 90°.', feedback_hi='180° − 90° = 90°।')
    return item


def contrast_explanation(language,action=None):
    """Fail closed unless both catalogued definitions have numeric source support."""
    from diagnostic.book_chat import retrieve_sources,canonical
    from diagnostic.bilingual_quality import numeric_text
    sources=[]
    for cid,measure in [('MATH6_C0024',90),('MATH6_C0023',180)]:
        matches,_=retrieve_sources(cid,language,f'{measure} '+('right angle' if measure==90 else 'straight angle'),limit=None)
        source=next((s for s in matches if str(measure) in numeric_text(s['excerpt'])),None)
        if source is None and cid=='MATH6_C0023':
            # The catalogued right-angle measurement page also explicitly derives
            # the straight angle's 180-degree measure (both language editions).
            matches,_=retrieve_sources('MATH6_C0024',language,'180 straight angle',limit=None)
            label='straight angle' if language=='en' else 'सरल कोण'
            source=next((s for s in matches if '180' in numeric_text(s['excerpt']) and label in s['excerpt']),None)
            if source:source=dict(source,concept_ids=['MATH6_C0023','MATH6_C0024'])
        if not source:return None
        sources.append(dict(source,id=f'S{len(sources)+1}'))
    from diagnostic import hinglish
    if hinglish.STYLE.get()=='hinglish':language='hi'
    texts=(['A right angle measures 90°. Compare it with a straight angle.',
            'A straight angle measures 180°, so it is larger than a right angle.'] if language=='en' else
           ['समकोण का माप 90° है। इसकी तुलना सरल कोण से करें।',
            'सरल कोण का माप 180° है, इसलिए यह समकोण से बड़ा है।'])
    if action=='simpler':
        texts=(['A right angle is 90°.','A straight angle is 180°. These are different angle sizes.'] if language=='en' else
               ['समकोण 90° का होता है।','सरल कोण 180° का होता है। इन कोणों के आकार अलग हैं।'])
    elif action=='language_help':
        texts=(['The term right angle means an angle of 90°.','The term straight angle means an angle of 180°.'] if language=='en' else
               ['समकोण का अर्थ 90° के माप वाला कोण है।','सरल कोण का अर्थ 180° के माप वाला कोण है।'])
    elif action=='another_example':
        texts=(['Imagine a clock hand moving from 12 to 3 and then to 6.',
                '90 + 90 = 180°. Together they make one straight angle.'] if language=='en' else
               ['घड़ी की सुई को 12 से 3 और फिर 6 तक जाते हुए सोचें।',
                '90 + 90 = 180°। दोनों मिलकर एक सरल कोण बनाते हैं।'])
    elif action=='still_confused':
        texts=(['First identify one right angle: 90°.',
                'A straight angle needs twice this turn: 90 + 90 = 180°.'] if language=='en' else
               ['पहले एक समकोण पहचानें: 90°।',
                'सरल कोण के लिए इसका दोगुना घुमाव चाहिए: 90 + 90 = 180°।'])
    if hinglish.STYLE.get()=='hinglish':texts=[hinglish.romanize(text) for text in texts]
    return {'status':'answered','mode':'source_backed_template','language':language,
            'concept':e.load_graph()[0]['MATH6_C0024'],
            'paragraphs':[{'text':text,'citations':[s['id']],'evidence':canonical(s['excerpt']),
                           'kind':'explanation'} for text,s in zip(texts,sources)],
            'sources':sources,'notice':'Original explanation using the cited angle definitions. Independent bilingual review pending.'}
