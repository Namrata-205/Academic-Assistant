"""Local check -> explanation -> generated practice, using existing evidence rules."""
import json
import re
from uuid import uuid4
from datetime import datetime,timezone
from diagnostic import engine as e
from diagnostic.tutor_bank import load as load_tutor_bank
from diagnostic import hinglish


def ensure(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS book_chat_tutoring (thread_id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS book_chat_check_answers (thread_id TEXT, attempt_id TEXT, ordinal INTEGER, question_id TEXT, concept_id TEXT, response TEXT, score INTEGER, version TEXT, created TEXT, PRIMARY KEY(attempt_id,ordinal))')
    conn.execute('CREATE TABLE IF NOT EXISTS book_chat_practice (thread_id TEXT, item_id TEXT, response TEXT, score INTEGER)')


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
            'concept_names':{'en':q['concept_en'],'hi':q['concept_hi']}}


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
    seed=int(uuid4().hex[:8],16);n=25+(seed%5)*10
    name=nodes[target]['en'];question=None
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
    return dict(question,id='practice-'+uuid4().hex,concept_id=target,concept_en=nodes[target]['en'],concept_hi=nodes[target]['hi'])


def finish(conn,thread,state,language):
    from diagnostic.book_chat import answer
    nodes,edges=e.load_graph();current=observations(conn,state['session_id']);bank=load_tutor_bank()
    report=e.make_report(state['target'],bank,edges,current,state['prior'])
    state['report']=report
    result=answer(state['original'],language,state['target'],conn=conn,learner=state['learner'],chat_evidence=history(conn,state['learner']))
    result['tutor_summary']={'questions_asked':len(current),'concepts':[{
        'concept':nodes[r['concept_id']][language], 'status':r['status'] if r['assessment']=='Assessed' else 'Unassessed',
        'concept_id':r['concept_id']} for r in report['concepts']],
        'answers':[{'question':next(q for q in bank if q['id']==r['question_id'])[language],
                    'response':r['response'],'score':r['score']} for r in current]}
    focus=next((r['concept_id'] for r in report['concepts'] if r['assessment']=='Assessed'
                and r['status']=='Possible prerequisite difficulty'),state['target'])
    followup=practice(focus,nodes)
    state.update(phase='practice' if followup else 'done',practice=followup)
    if followup:
        result['practice_question']=public_question(followup,language)
        result['practice_question']['source_ids']=[s['id'] for s in result.get('sources',[]) if focus in s.get('concept_ids',[s.get('concept_id')])]
        result['practice_notice']='New practice variation, not copied from NCERT. It is not used to diagnose a difficulty. Human review pending.'
    result['tutor_stage']='explanation';save(conn,thread,state)
    return result


def handle(conn,learner,thread,text,language,concept_id=None,previous=None):
    """Return None for normal chat; all learner answers/evidence remain local."""
    ensure(conn);row=conn.execute('SELECT payload FROM book_chat_tutoring WHERE thread_id=?',(thread,)).fetchone()
    state=json.loads(row[0]) if row else None;nodes,edges=e.load_graph();bank=load_tutor_bank()
    if text.startswith('__chat_query__:'):
        text=text[len('__chat_query__:'):].strip()
        if not text:raise ValueError('Enter a question.')
        if state and state['phase']=='practice':
            state['phase']='done';save(conn,thread,state)
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
            state['phase']='done';save(conn,thread,state)
            return {'status':'answered','mode':'practice_feedback','language':language,'concept':nodes[state['target']],
                    'message':('Correct. ' if score==1 else 'Let’s work through it. ')+q['feedback_'+language],
                    'paragraphs':[],'sources':[],'practice_score':score,
                    'notice':'Practice feedback only; this answer does not establish a new diagnosis.'}
    if state and state['phase']=='checking':
        current=observations(conn,state['session_id'])
        q=select_question(state['target'],bank,edges,current,state['prior'],state.get('check_style'))
        if text=='__explain_now__':return finish(conn,thread,state,language)
        if q:
            # Do not consume a learning-check slot when the learner starts a different question.
            if re.match(r'^(?:explain|what|why|how|समझाइए)',text.strip(),re.I):
                state['phase']='done';save(conn,thread,state);state=None
            else:
                record(conn,thread,state['session_id'],q,text)
                current=observations(conn,state['session_id'])
                q=select_question(state['target'],bank,edges,current,state['prior'],state.get('check_style'))
                if q:
                    return {'status':'answered','mode':'learning_check','tutor_stage':'checking','language':language,
                            'concept':nodes[state['target']],'message':'One more short question will help me choose where to start.' if language=='en' else 'एक छोटा सवाल और, ताकि समझाने की सही शुरुआत चुन सकूँ।',
                            'check_question':public_question(q,language),'check_number':len(current)+1,'paragraphs':[],'sources':[]}
                return finish(conn,thread,state,language)
    from diagnostic.chat_router import plan
    routing=plan(text,nodes,edges,concept_id,previous or (state or {}).get('target'))
    target=routing.get('concept_id')
    if routing['action']=='clarify':
        local=tutoring_mapping(text,nodes,edges,concept_id)
        return {'status':'clarify','language':language,'paragraphs':[],'sources':[],
                'candidates':[nodes[c] for c in local.get('candidates',[]) if c in nodes],'routing':routing}
    if routing['action']=='explain':
        from diagnostic.book_chat import answer
        result=answer(text,language,target,previous,conn,learner,chat_evidence=history(conn,learner))
        result['routing']=routing
        return result
    if routing['action']=='practice':
        q=practice(target,nodes)
        if q:
            state={'target':target,'original':text,'learner':learner,'phase':'practice','practice':q}
            save(conn,thread,state)
            return {'status':'answered','mode':'practice','language':language,'concept':nodes[target],
                    'message':'Try this, and I’ll check your answer.' if language=='en' else 'इसे हल करें, फिर आपका उत्तर जाँचूँगा।',
                    'practice_question':public_question(q,language),'practice_notice':'New original practice variation, not copied from NCERT.',
                    'paragraphs':[],'sources':[],'routing':routing}
    prior=e.history(conn,learner)+history(conn,learner)
    batch=check_batch(target,bank,edges,prior)
    q=batch[0] if batch else None
    if not q:
        from diagnostic.book_chat import answer
        result=answer(text,language,target,conn=conn,learner=learner,chat_evidence=history(conn,learner))
        result['routing']=dict(routing,executed_action='explain',reason='no_unseen_bank_items')
        return result
    sid=uuid4().hex
    state={'target':target,'original':text,'learner':learner,'session_id':sid,'prior':prior,'phase':'checking','check_style':routing.get('check_style')}
    state['batch_ids']=[item['id'] for item in batch]
    save(conn,thread,state)
    return {'status':'answered','mode':'learning_check','tutor_stage':'checking','language':language,'concept':nodes[target],
            'message':(('Before explaining number patterns, let’s check a few basics about numbers and digits. If you mean shape patterns, tell me.' if language=='en' else 'संख्या पैटर्न समझाने से पहले संख्याओं और अंकों की कुछ बुनियादी बातें जाँचें। यदि आपका मतलब आकृतियों के पैटर्न से है, तो बताइए।') if routing.get('topic_assumption') else ('Before I explain, let’s check a foundation so I can choose the right starting point.' if language=='en' else 'समझाने से पहले एक आधारभूत बात जाँचें, ताकि सही शुरुआत चुन सकूँ।')),
            'check_question':public_question(q,language),'check_questions':[public_question(item,language) for item in batch],'check_number':1,'paragraphs':[],'sources':[],'routing':routing,
            'notice':'Tutoring answers are saved in this chat, separately from diagnostic scores. Question bank and rules await final review.'}
