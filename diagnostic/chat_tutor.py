from diagnostic.curriculum import teaching_name
"""Local check -> explanation -> generated practice, using existing evidence rules."""
import json
import re
import hashlib
from uuid import uuid4
from datetime import datetime,timezone
from diagnostic import engine as e
from diagnostic.tutor_bank import load as load_tutor_bank
from diagnostic import hinglish


def ensure(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS book_chat_tutoring (thread_id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS book_chat_check_answers (thread_id TEXT, attempt_id TEXT, ordinal INTEGER, question_id TEXT, concept_id TEXT, response TEXT, score INTEGER, version TEXT, created TEXT, PRIMARY KEY(attempt_id,ordinal))')
    conn.execute('CREATE TABLE IF NOT EXISTS book_chat_practice (thread_id TEXT, item_id TEXT, response TEXT, score INTEGER)')
    conn.execute('CREATE TABLE IF NOT EXISTS book_chat_tutor_events (id TEXT PRIMARY KEY, thread_id TEXT, kind TEXT, payload TEXT, created TEXT)')


def event(conn,thread,kind,payload):
    with conn:conn.execute('INSERT INTO book_chat_tutor_events VALUES (?,?,?,?,?)',
        (uuid4().hex,thread,kind,json.dumps(payload,ensure_ascii=False),datetime.now(timezone.utc).isoformat()))


def followup_evidence(conn,learner):
    rows=conn.execute("SELECT a.payload FROM book_chat_tutor_events a JOIN book_chat_threads t ON t.id=a.thread_id WHERE t.learner=? AND a.kind='followup_answer' ORDER BY a.created",(learner,))
    unique={}
    for (payload,) in rows:
        item=json.loads(payload)
        if item.get('version')==e.VERSION:
            unique.pop(item['question_id'],None);unique[item['question_id']]=item
    return list(unique.values())


def next_check(conn,thread,state,bank,edges,current,language):
    from diagnostic.tutor_selection import choose
    q,audit=choose(state['target'],bank,edges,current,state['prior'],state.get('angle_contrast',False),
                   exposed=state.get('exposed_item_ids',()))
    event(conn,thread,'selection',audit)
    state.setdefault('selection_log',[]).append(audit)
    state['pending_item_id']=q['id'] if q else None
    save(conn,thread,state)
    if not q:return None
    return {'status':'answered','mode':'learning_check','tutor_stage':'checking','language':language,
            'concept':e.load_graph()[0][state['target']],
            'message':'One short question at a time helps choose the next step.' if language=='en' else 'एक-एक छोटे सवाल से अगला कदम चुनने में मदद मिलती है।',
            'check_question':public_question(q,language),'check_number':len(current)+1,
            'selection':audit,'paragraphs':[],'sources':[]}


def save(conn,thread,state):
    with conn:conn.execute('INSERT OR REPLACE INTO book_chat_tutoring VALUES (?,?)',(thread,json.dumps(state,ensure_ascii=False)))


def observations(conn,sid):
    return [dict(zip(('question_id','concept_id','response','score'),row)) for row in conn.execute(
        'SELECT question_id,concept_id,response,score FROM book_chat_check_answers WHERE attempt_id=? ORDER BY ordinal',(sid,))]


def history(conn,learner):
    return [dict(zip(('question_id','concept_id','response','score'),row)) for row in conn.execute(
        'SELECT a.question_id,a.concept_id,a.response,a.score FROM book_chat_check_answers a JOIN book_chat_threads t ON t.id=a.thread_id WHERE t.learner=? AND a.version=? ORDER BY a.created,a.ordinal',(learner,e.VERSION))]


def record(conn,thread,sid,q,text):
    ordinal=len(observations(conn,sid))+1
    if ordinal>3:raise ValueError('Three-question tutoring limit reached.')
    with conn:conn.execute('INSERT INTO book_chat_check_answers VALUES (?,?,?,?,?,?,?,?,?)',
        (thread,sid,ordinal,q['id'],q['concept_id'],text,e.score(q,text),e.VERSION,datetime.now(timezone.utc).isoformat()))


def select_question(target,bank,edges,current,prior,style='foundations'):
    foundations=set(e.prerequisites(target,edges))
    foundation_bank=[q for q in bank if q['concept_id'] in foundations]
    if foundation_bank:
        # A difficulty-led tutoring check assesses foundations, not the target skill.
        return e.select_question(target,foundation_bank,edges,current,prior)
    return e.select_question(target,bank,edges,current,prior)


def public_question(q,language):
    return {'id':q['id'],'text':hinglish.question(q) if hinglish.STYLE.get()=='hinglish' else q[language],'type':q['type'],'concept_id':q['concept_id'],
            'concept':q['concept_hi' if language=='hi' else 'concept_en'],
            'translations':{'en':q['en'],'hi':q['hi'],'hinglish':hinglish.question(q)},
            'concept_names':{'en':q['concept_en'],'hi':q['concept_hi']},
            **({'diagram':q['diagram']} if q.get('diagram') else {})}


def check_batch(target,bank,edges,prior):
    """Freeze up to three fresh foundation items; historical evidence cannot end this check."""
    foundations=set(e.prerequisites(target,edges))
    pool=[q for q in bank if q['concept_id'] in foundations] or [q for q in bank if q['concept_id']==target]
    used={r['question_id'] for r in prior};ordered=sorted(pool,key=lambda q:(q['id'] in used,q['concept_id'],q['id']))
    return ordered[:3]


def wants_check(text):
    return bool(re.search(r'struggl|confus|don[’\']?t understand|do not understand|practi[cs]e|test me|check my|samajh|samjht|mushkil|समझ नहीं|उलझन|अभ्यास|जाँच',text,re.I))


def tutoring_mapping(text,nodes,edges,concept_id=None):
    if concept_id in nodes:return {'status':'mapped','concept_id':concept_id}
    # "acute and right angles" is a connected comparison: right angle is a
    # prerequisite of acute angle. Cover both by checking the acute-angle path.
    if re.search(r'\b(?:acute\s+(?:angles?\s+)?and\s+right|right\s+(?:angles?\s+)?and\s+acute)\s+angles?\b',text,re.I):
        return {'status':'mapped','concept_id':'MATH6_C0025','method':'connected_angle_comparison'}
    if 'समकोण' in text and 'न्यून' in text:
        return {'status':'mapped','concept_id':'MATH6_C0025','method':'connected_angle_comparison'}
    return e.map_question(text,nodes,edges)


def practice(target,nodes):
    """Parameterised original items with exact keys, not alleged NCERT quotations."""
    if target not in nodes:return None
    seed=int(uuid4().hex[:8],16);n=25+(seed%5)*10
    from diagnostic.curriculum_items import make as curriculum_question
    if target not in {'MATH6_C0003','MATH6_C0006','MATH6_C0007','MATH6_C0009','MATH6_C0018','MATH6_C0020','MATH6_C0024','MATH6_C0025','MATH6_C0038','MATH6_C0039'}:
        item=curriculum_question(target,nodes,seed)
        if item:return item
    from diagnostic.followup_templates import expanded
    item=expanded(target,nodes,seed)
    if item:return item
    name=teaching_name(nodes[target]['en']);question=None
    if name=='acute angle':
        question={'en':f'Is an angle measuring {n}° acute? A: yes; B: no.',
                  'hi':f'क्या {n}° का कोण न्यून कोण है? A: हाँ; B: नहीं।','type':'mcq','answer':'A',
                  'feedback_en':f'{n} is greater than 0 and less than 90, so this is an acute angle.',
                  'feedback_hi':f'{n}, 0 से अधिक और 90 से कम है, इसलिए यह न्यून कोण है।'}
    elif name=='right angle':
        question={'en':'A full turn is 360°. How many degrees are in a quarter turn?',
                  'hi':'एक पूरा घुमाव 360° का है। चौथाई घुमाव कितने अंश का होगा?','type':'numeric','answer':'90',
                  'feedback_en':'360 ÷ 4 = 90°. A quarter turn is a right angle.',
                  'feedback_hi':'360 ÷ 4 = 90°। चौथाई घुमाव एक समकोण है।'}
    elif name in ('place value','digit sum'):
        number=2300+(seed%6)*100+47;digits=str(number);digit=digits[1]
        value=int(digit)*100 if name=='place value' else sum(map(int,digits))
        question={'en':f'What is the value of {digit} in {number}?' if name=='place value' else f'Find the digit sum of {number}.',
                  'hi':f'{number} में {digit} का स्थानीय मान क्या है?' if name=='place value' else f'{number} के अंकों का योग ज्ञात करें।',
                  'type':'numeric','answer':str(value),'feedback_en':f'The answer is {value}. '+(f'{digit} × 100 = {value}.' if name=='place value' else ' + '.join(digits)+f' = {value}.'),
                  'feedback_hi':f'उत्तर {value} है। '+(f'{digit} × 100 = {value}।' if name=='place value' else ' + '.join(digits)+f' = {value}।')}
    elif name=='number pattern':
        step=2+seed%5;sequence=[step*i for i in range(1,5)]
        question={'en':f'Continue this pattern: {", ".join(map(str,sequence))}, __.',
                  'hi':f'पैटर्न आगे बढ़ाएँ: {", ".join(map(str,sequence))}, __।','type':'numeric','answer':str(step*5),
                  'feedback_en':f'Add {step} each time. The next term is {step*5}.','feedback_hi':f'हर बार {step} जोड़ें। अगला पद {step*5} है।'}
    elif name=='square number':
        side=4+seed%5
        question={'en':f'A square has {side} rows of {side} dots. How many dots are there?',
                  'hi':f'एक वर्ग में बिंदुओं की {side} पंक्तियाँ हैं और हर पंक्ति में {side} बिंदु हैं। कुल कितने बिंदु हैं?',
                  'type':'numeric','answer':str(side*side),'feedback_en':f'{side} × {side} = {side*side}.','feedback_hi':f'{side} × {side} = {side*side}।'}
    elif name in ('odd number','even number'):
        number=21+2*(seed%12);odd=name=='odd number'
        question={'en':f'Is {number} an {name}? A: yes; B: no.',
                  'hi':f'क्या {number} एक {nodes[target]["hi"]} है? A: हाँ; B: नहीं।','type':'mcq','answer':'A' if odd else 'B',
                  'feedback_en':f'{number} leaves remainder 1 when divided by 2, so it is odd, not even.',
                  'feedback_hi':f'{number} को 2 से भाग देने पर शेष 1 रहता है, इसलिए यह विषम है, सम नहीं।'}
    elif name in ('number','digit','consecutive number','number line'):
        a=3+seed%7;b=2+seed%4
        en,hi,key=(f'How many counters are there in {a} counters and {b} more?',f'{a} गोटियों में {b} और मिलाएँ। कुल कितनी गोटियाँ हैं?',str(a+b)) if name=='number' else (
            ('How many digits does 6204 have?','6204 में कितने अंक हैं?','4') if name=='digit' else (
            (f'Which number comes immediately after {a+30}?',f'{a+30} के तुरंत बाद कौन सी संख्या आती है?',str(a+31)) if name=='consecutive number' else (
            f'Start at {a} on a number line and move {b} steps right. Where do you land?',f'संख्या रेखा पर {a} से {b} कदम दाईं ओर जाएँ। कहाँ पहुँचेंगे?',str(a+b))))
        question={'en':en,'hi':hi,'type':'numeric','answer':key,'feedback_en':f'The answer is {key}. '+('Count each digit: 6, 2, 0, 4.' if name=='digit' else 'Count forward one step at a time.'),
                  'feedback_hi':f'उत्तर {key} है। '+('अंक गिनें: 6, 2, 0, 4।' if name=='digit' else 'एक-एक कदम आगे गिनें।')}
    elif name in ('angle','line segment','vertex'):
        question={'en':'Rays PQ and PR start at P. Which point is the vertex of the angle? A: P; B: Q; C: R.',
                  'hi':'किरणें PQ और PR बिंदु P से शुरू होती हैं। कोण का शीर्ष कौन है? A: P; B: Q; C: R।',
                  'type':'mcq','answer':'A','feedback_en':'P is the common starting point of both rays, so P is the vertex.',
                  'feedback_hi':'P दोनों किरणों का उभयनिष्ठ प्रारंभिक बिंदु है, इसलिए P शीर्ष है।'} if name!='line segment' else {
                  'en':'A straight path has two endpoints, M and N. Is it a line segment? A: yes; B: no.',
                  'hi':'एक सीधे पथ के दो अंत बिंदु M और N हैं। क्या यह रेखाखंड है? A: हाँ; B: नहीं।','type':'mcq','answer':'A',
                  'feedback_en':'A line segment is bounded by two endpoints.','feedback_hi':'एक रेखाखंड दो अंत बिंदुओं से घिरा होता है।'}
    if not question:return None
    return dict(question,id='practice-'+uuid4().hex,concept_id=target,concept_en=nodes[target]['en'],concept_hi=nodes[target]['hi'],
                scoring_rule='Exact key; other text unscorable.',source_references=[],review_status='PENDING',
                possible_difficulty='A follow-up observation; a slip or wording difficulty is also possible.')


def fresh_practice(target,nodes,state,conn=None):
    from diagnostic.learner_evidence import content_id,collect
    seen=set(state.get('seen_practice',[]))
    if conn is not None:
        seen.update(content_id(row['item']) for row in collect(conn,state['learner']) if row.get('item'))
    for _ in range(80):
        item=practice(target,nodes)
        if item is None:return None
        identity=content_id(item)
        if identity not in seen:
            state['seen_practice']=list(state.get('seen_practice',[]))+[identity]
            return item
    return None


def finish(conn,thread,state,language):
    from diagnostic.book_chat import answer
    nodes,edges=e.load_graph();current=observations(conn,state['session_id']);bank=load_tutor_bank()
    known={q['id'] for q in bank}
    bank+= [dict(row['item'],scoring_rule=row['item'].get('scoring_rule','Exact key; other text unscorable.'),
                 source_references=row['item'].get('source_references',[]),
                 possible_difficulty=row['item'].get('possible_difficulty','Follow-up evidence, not proof of mastery.'))
            for row in state['prior'] if row.get('item') and row['question_id'] not in known]
    from diagnostic.learner_evidence import assessment
    state['prior']=assessment(state['prior'])
    report=e.make_report(state['target'],bank,edges,current,state['prior'])
    state['report']=report
    from diagnostic.teaching_feedback import teaching_decision
    decision=teaching_decision(report,state['target']);focus=decision['focus_concept_id']
    state['example_variant']=0;state['teaching_decision']=decision
    from diagnostic.teaching_feedback import contrast_explanation,angle_item
    result=contrast_explanation(language) if state.get('angle_contrast') else None
    if result is None:
        result=answer(state['original'],language,state['target'],conn=conn,learner=state['learner'],chat_evidence=history(conn,state['learner'])+followup_evidence(conn,state['learner']),
                      teaching_request=dict(decision,example_variant=0))
    effective=result.get('learning_context',{}).get('teaching_request',{}).get('focus',{}).get('id')
    if effective in nodes:focus=effective
    result['teaching_decision']=decision
    result['tutor_summary']={'questions_asked':len(current),'concepts':[{
        'concept':nodes[r['concept_id']][language], 'status':r['status'] if r['assessment']=='Assessed' else 'Unassessed',
        'concept_id':r['concept_id']} for r in report['concepts']],
        'answers':[{'question':next(q for q in bank if q['id']==r['question_id'])[language],
                    'response':r['response'],'score':r['score']} for r in current]}
    state['focus']=focus
    followup=angle_item(55,False) if state.get('angle_contrast') else fresh_practice(focus,nodes,state,conn)
    state.update(phase='practice' if followup else 'done',practice=followup)
    if followup:
        result['practice_question']=public_question(followup,language)
        result['practice_question']['source_ids']=[s['id'] for s in result.get('sources',[]) if focus in s.get('concept_ids',[s.get('concept_id')])]
        result['practice_notice']='Original transfer question. Its response is saved as follow-up evidence; one response alone cannot establish a diagnosis. Human review pending.'
    else:result['practice_notice']='No fresh local transfer item is available for this concept. Earlier answers are not counted again.'
    result['feedback_actions']=['simpler','another_example','still_confused','language_help']
    result['selection_log']=state.get('selection_log',[])
    result['tutor_stage']='explanation';save(conn,thread,state)
    return result


def handle(conn,learner,thread,text,language,concept_id=None,previous=None,check_first=False):
    """Return None for normal chat; all learner answers/evidence remain local."""
    ensure(conn);row=conn.execute('SELECT payload FROM book_chat_tutoring WHERE thread_id=?',(thread,)).fetchone()
    state=json.loads(row[0]) if row else None;nodes,edges=e.load_graph();bank=load_tutor_bank()
    if state and state.get('target') not in nodes:state=None
    composer_query=text.startswith('__chat_query__:')
    if composer_query:
        text=text[len('__chat_query__:'):].strip()
        if not text:raise ValueError('Enter a question.')
        if state and state['phase'] in ('practice','checking'):
            state['phase']='done';save(conn,thread,state)
    from diagnostic.conversation import feedback,is_followup
    # Natural-language repair requests use the same teaching path as feedback buttons.
    # A newly named concept must still be routed as a topic change.
    natural_feedback=None if text.startswith('__') else feedback(text)
    if state and natural_feedback and not text.startswith('__'):
        mapping=tutoring_mapping(text,nodes,edges,concept_id)
        if mapping.get('scope')!='outside current graph' and mapping.get('concept_id') in (None,state['target']) and not (concept_id and concept_id!=state['target']):
            if state['phase']=='checking':state['phase']='done';save(conn,thread,state)
            text='__feedback__:'+natural_feedback
    if state and state['phase']=='practice' and is_followup(text):
        state['phase']='done';save(conn,thread,state)
    if text == '__angle_compare__' and state and state.get('angle_contrast') and state['phase']=='done':
        from diagnostic.teaching_feedback import angle_comparison_item
        from diagnostic.learner_evidence import collect
        offset = sum(bool(row.get('item', {}).get('comparison')) for row in collect(conn, learner))
        q = angle_comparison_item(offset)
        state.update(phase='practice', practice=q)
        save(conn, thread, state)
        return {'status':'answered','mode':'practice','language':language,'concept':nodes[state['target']],
                'paragraphs':[],'sources':[],'practice_question':public_question(q,language)}
    if text.startswith('__feedback__:'):
        from diagnostic.teaching_feedback import ACTIONS,angle_item,contrast_explanation
        action=text.split(':',1)[1]
        if action not in ACTIONS or not state or state['phase']=='checking':raise ValueError('Feedback is available after an explanation.')
        event(conn,thread,'feedback',{'action':action,'target':state['target']})
        focus=state.get('focus',state['target'])
        previous_variant=state.get('example_variant',0)
        state['example_variant']=previous_variant+1
        instruction={'simpler':'Briefly explain using short sentences and define the terms. ',
                     'another_example':'Show a different complete worked example. ',
                     'still_confused':'Explain the foundation step by step before the target. ',
                     'language_help':'Explain the meaning of the mathematical terms simply. '}[action]
        from diagnostic.book_chat import answer
        result=contrast_explanation(language,action) if state.get('angle_contrast') else None
        if result is None:
            result=answer(instruction+nodes[state['target']][language],language,state['target'],conn=conn,learner=learner,
                          chat_evidence=history(conn,learner)+followup_evidence(conn,learner),
                          teaching_request={'mode':action,'focus_concept_id':focus,
                              'example_variant':state.get('example_variant',0),
                              'previous_example_variant':previous_variant})
        rotation=(state.get('transfer_rotation',55)+35)%360
        q=angle_item(rotation,bool(state.get('followup_count',0)%2)) if state.get('angle_contrast') else fresh_practice(focus,nodes,state,conn)
        if action in ('still_confused','simpler','language_help'):
            q=None
        state.update(phase='practice' if q else 'done',practice=q,transfer_rotation=rotation)
        save(conn,thread,state)
        if q:result['practice_question']=public_question(q,language)
        result['feedback_action']=action;result['feedback_actions']=sorted(ACTIONS)
        return result
    if state and state['phase']=='checking' and text=='__explain_now__':
        return finish(conn,thread,state,language)
    if state and state['phase']=='checking' and state.get('batch_ids'):
        if not text.startswith('__check_batch__:'):
            raise ValueError('Complete the answers in the question card before submitting.')
        try:responses=json.loads(text.split(':',1)[1])
        except (ValueError,TypeError):raise ValueError('Invalid check answers.')
        if not isinstance(responses,list) or len(responses)!=len(state['batch_ids']) or any(not isinstance(a,str) or not a.strip() or len(a)>500 for a in responses):
            raise ValueError('Answer every question or choose not sure.')
        items={q['id']:q for q in bank}
        with conn:
            for qid,response in zip(state['batch_ids'],responses):record(conn,thread,state['session_id'],items[qid],response)
        return finish(conn,thread,state,language)
    if state and state['phase']=='practice':
        q=state['practice'];score=e.score(q,text)
        # A new explanatory question leaves practice mode instead of scoring arbitrary prose.
        new_request=bool(re.match(r'^(?:explain|what|why|how|another|give me|समझाइए)',text.strip(),re.I) or wants_check(text))
        if score is not None or not new_request:
            with conn:
                conn.execute('CREATE TABLE IF NOT EXISTS book_chat_practice (thread_id TEXT, item_id TEXT, response TEXT, score INTEGER)')
                conn.execute('INSERT INTO book_chat_practice VALUES (?,?,?,?)',(thread,q['id'],text,score))
            observation={'question_id':q['id'],'concept_id':q['concept_id'],'response':text,'score':score,
                         'assessment_eligible':False,
                         'version':e.VERSION,'origin':'followup','item':q}
            # Repeating an identical generated item is not independent evidence.
            identity=json.dumps({key:q.get(key) for key in ('concept_id','en','hi','diagram')},sort_keys=True,ensure_ascii=False)
            observation['question_id']='followup-'+hashlib.sha256(identity.encode('utf-8')).hexdigest()[:24]
            observation['item']=dict(q,id=observation['question_id'])
            event(conn,thread,'followup_answer',observation)
            state['followup_count']=state.get('followup_count',0)+1
            state['phase']='done';save(conn,thread,state)
            return {'status':'answered','mode':'practice_feedback','language':language,'concept':nodes[state['target']],
                    'message':(('सही। ' if score==1 else 'आइए, इसे साथ में समझें। ') if language=='hi' else
                               ('Correct. ' if score==1 else 'Let’s work through it. '))+hinglish.feedback(q,language),
                    'paragraphs':[],'sources':[],'practice_score':score,
                    'next_action': ('compare_angles' if score == 1 and not q.get('comparison') else
                                    'another_example' if score == 1 else 'review_half_turn')
                                   if state.get('angle_contrast') else ('another_example' if score == 1 else 'review'),
                    'followup_evidence':{'concept_id':q['concept_id'],'score':score,'origin':'followup'},
                    'feedback_actions':['simpler','another_example','still_confused','language_help'],
                    'notice':'Saved as new follow-up evidence. One response alone does not establish a diagnosis.'}
    if state and state['phase']=='checking':
        current=observations(conn,state['session_id'])
        q=next((q for q in bank if q['id']==state.get('pending_item_id')),None)
        if q is None:q=select_question(state['target'],bank,edges,current,state['prior'],state.get('check_style'))
        if text=='__explain_now__':return finish(conn,thread,state,language)
        if q:
            # Do not consume a learning-check slot when the learner starts a different question.
            if re.match(r'^(?:explain|what|why|how|समझाइए)',text.strip(),re.I):
                state['phase']='done';save(conn,thread,state);state=None
            else:
                record(conn,thread,state['session_id'],q,text)
                current=observations(conn,state['session_id'])
                result=next_check(conn,thread,state,bank,edges,current,language)
                if result:return result
                return finish(conn,thread,state,language)
    from diagnostic.chat_router import plan
    contrast=bool((re.search(r'right\s+angle',text,re.I) and re.search(r'straight\s+angle',text,re.I)) or ('समकोण' in text and 'सरल कोण' in text))
    if text.startswith('__continue_angle__:'):
        from diagnostic.teaching_feedback import angle_item, angle_comparison_item, contrast_explanation
        from diagnostic.learner_evidence import collect, content_id
        compare = text.endswith(':compare')
        seen = {content_id(row['item']) for row in collect(conn, learner) if row.get('item')}
        q = next((item for i in range(2) if content_id(item := angle_comparison_item(i)) not in seen), None) if compare else None
        if not q or content_id(q) in seen:
            q = next((item for i in range(72) if content_id(item := angle_item(i*5, bool(i%2))) not in seen), None)
        target = 'MATH6_C0024'
        result = (contrast_explanation(language, 'another_example') if not compare else None) or {
            'status':'answered','mode':'practice','language':language,'concept':nodes[target],
            'paragraphs':[],'sources':[]}
        save(conn, thread, dict(target=target, focus=target, learner=learner,
                                original=nodes[target][language], angle_contrast=True,
                                phase='practice' if q else 'done', practice=q))
        if q:
            result['practice_question'] = public_question(q, language)
        else:
            result['message'] = (
                'अभी कोई नया चित्र प्रश्न उपलब्ध नहीं है।' if language=='hi' else 'No fresh diagram question is available.')
        return result
    quick_check = text.startswith('__quick_check__:')
    if quick_check or text.startswith(('__continue_topic__:', '__advance_topic__:')):
        if not isinstance(concept_id, str) or concept_id not in nodes:
            raise ValueError('Choose a curriculum topic for the quick check.')
        if not quick_check:
            from diagnostic.book_chat import answer
            state = dict(target=concept_id, focus=concept_id, learner=learner, original=nodes[concept_id][language])
            mode = 'build_on_understanding' if text.startswith('__advance_topic__:') else 'review_practice'
            result = answer(nodes[concept_id][language], language, concept_id, conn=conn, learner=learner,
                            teaching_request={'mode':mode,'focus_concept_id':concept_id,'example_variant':0})
            q = fresh_practice(concept_id, nodes, state, conn)
            state.update(practice=q, phase='practice' if q else 'done')
            save(conn, thread, state)
            if q:
                result['practice_question'] = public_question(q, language)
            result['feedback_actions'] = ['simpler','another_example','still_confused','language_help']
            return result
        routing = {'action':'check','concept_id':concept_id,'check_style':'foundations','planner':'local_quick_check'}
    else:
        routing=({'action':'check','concept_id':'MATH6_C0024','planner':'local_angle_contrast'} if contrast else
                 plan(text,nodes,edges,concept_id,previous or (state or {}).get('target')))
    target=routing.get('concept_id')
    no_check=bool(re.search(r'without (?:a |any )?(?:quiz|test|questions|check)|just explain|explain only|बिना.*(?:सवाल|जाँच|प्रश्न)',text,re.I))
    if check_first and routing['action']=='explain' and target and target!=(state or {}).get('target') and not no_check:
        routing=dict(routing,action='check',check_style='foundations',reason='new_topic_understanding_check')
    if routing['action']=='clarify':
        local=tutoring_mapping(text,nodes,edges,concept_id)
        return {'status':'clarify','language':language,'paragraphs':[],'sources':[],
                'candidates':[nodes[c] for c in local.get('candidates',[]) if c in nodes],'routing':routing}
    if routing['action']=='explain':
        from diagnostic.book_chat import answer
        result=answer(text,language,target,previous,conn,learner,chat_evidence=history(conn,learner)+followup_evidence(conn,learner))
        # Retain an explanation state so feedback works even without diagnostics.
        focus=result.get('learning_context',{}).get('teaching_request',{}).get('focus',{}).get('id',target)
        save(conn,thread,{'target':target,'original':text,'learner':learner,'phase':'done','focus':focus,'example_variant':0})
        result['feedback_actions']=['simpler','another_example','still_confused','language_help']
        result['routing']=routing
        return result
    if routing['action']=='practice':
        state={'target':target,'original':text,'learner':learner,'phase':'practice'}
        q=fresh_practice(target,nodes,state,conn)
        if q:
            state['practice']=q
            save(conn,thread,state)
            return {'status':'answered','mode':'practice','language':language,'concept':nodes[target],
                    'message':'Try this, and I’ll check your answer.' if language=='en' else 'इसे हल करें, फिर आपका उत्तर जाँचूँगा।',
                    'practice_question':public_question(q,language),'practice_notice':'New original practice variation, not copied from NCERT.',
                    'paragraphs':[],'sources':[],'routing':routing}
        state['phase']='done';save(conn,thread,state)
        return {'status':'answered','mode':'practice_unavailable','language':language,'concept':nodes[target],
                'message':'No fresh local practice variation is available. Ask for an explanation or choose another topic.' if language=='en' else
                          'कोई नया स्थानीय अभ्यास प्रश्न उपलब्ध नहीं है। व्याख्या माँगें या दूसरा विषय चुनें।',
                'paragraphs':[],'sources':[],'routing':routing}
    from diagnostic.learner_evidence import collect,assessment
    evidence=collect(conn,learner);prior=assessment(evidence)
    exposed=[r['question_id'] for r in evidence]
    from diagnostic.tutor_selection import choose
    q,_=choose(target,bank,edges,prior=prior,contrast=contrast,exposed=exposed)
    if not q:
        from diagnostic.book_chat import answer
        result=answer(text,language,target,conn=conn,learner=learner,chat_evidence=history(conn,learner))
        result['routing']=dict(routing,executed_action='explain',reason='no_unseen_bank_items')
        save(conn,thread,{'target':target,'original':text,'learner':learner,'phase':'done','focus':target})
        result['feedback_actions']=['simpler','another_example','still_confused','language_help']
        return result
    sid=uuid4().hex
    state={'target':target,'original':text,'learner':learner,'session_id':sid,'prior':prior,'phase':'checking','check_style':routing.get('check_style'),'angle_contrast':contrast,
           'exposed_item_ids':exposed}
    result=next_check(conn,thread,state,bank,edges,[],language)
    result.update({
            'message':(('Before explaining number patterns, let’s check a few basics about numbers and digits. If you mean shape patterns, tell me.' if language=='en' else 'संख्या पैटर्न समझाने से पहले संख्याओं और अंकों की कुछ बुनियादी बातें जाँचें। यदि आपका मतलब आकृतियों के पैटर्न से है, तो बताइए।') if routing.get('topic_assumption') else ('Before I explain, let’s check a foundation so I can choose the right starting point.' if language=='en' else 'समझाने से पहले एक आधारभूत बात जाँचें, ताकि सही शुरुआत चुन सकूँ।')),
            'routing':routing,
            'notice':'Tutoring answers are saved in this chat, separately from diagnostic scores. Question bank and rules await final review.'})
    return result
