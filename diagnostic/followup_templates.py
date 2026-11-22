"""Original bilingual transfer drafts with deterministic keys; review pending.

No textbook passages or prerequisite edges are invented. Unsupported source
concepts remain unavailable rather than receiving a made-up curriculum lesson.
"""
from uuid import uuid4


def body(name,seed):
    a=2+seed%8;b=1+(seed//8)%8
    def numeric(en,hi,key,why_en,why_hi):
        return dict(en=en,hi=hi,type='numeric',answer=str(key),feedback_en=why_en,feedback_hi=why_hi)
    def mcq(en,hi,yes,why_en,why_hi):
        return dict(en=en+' A: yes; B: no.',hi=hi+' A: हाँ; B: नहीं.',type='mcq',
                    answer='A' if yes else 'B',feedback_en=why_en,feedback_hi=why_hi)
    if name=='acute angle':
        angle=[25,90,115,0,55,180][seed%6];yes=0<angle<90
        return mcq(f'Is an angle of {angle}° acute?',f'क्या {angle}° का कोण न्यून है?',yes,
                   'An acute angle is greater than 0 degrees and less than 90 degrees.',
                   'न्यून कोण 0 अंश से अधिक और 90 अंश से कम होता है।')
    if name in ('odd number','even number'):
        number=20+seed%30;yes=(number%2==1)==(name=='odd number')
        return mcq(f'Is {number} an {name}?',f'क्या {number} एक '+('विषम संख्या है?' if name=='odd number' else 'सम संख्या है?'),yes,
                   f'Dividing {number} by 2 leaves remainder {number%2}.',f'{number} को 2 से भाग देने पर शेष {number%2} है।')
    if name in ('place value','digit sum','digit'):
        number=(8+seed%2)*1000+(3+seed%4)*100+27;digits=str(number)
        if name=='digit':
            return numeric(f'How many digits are in {number}?',f'{number} में कितने अंक हैं?',4,
                           f'The four digits are {", ".join(digits)}.',f'चार अंक हैं: {", ".join(digits)}।')
        if name=='place value':
            key=int(digits[1])*100;expression=f'{digits[1]} × 100 = {key}'
            return numeric(f'What is the place value of {digits[1]} in {number}?',f'{number} में {digits[1]} का स्थानीय मान क्या है?',key,
                           expression+'.',expression+'।')
        key=sum(map(int,digits));expression=' + '.join(digits)+f' = {key}'
        return numeric(f'Find the digit sum of {number}.',f'{number} के अंकों का योग निकालें।',key,expression+'.',expression+'।')
    if name in ('pattern','number pattern','sequence','visual pattern'):
        seq=[a+i*b for i in range(4)]
        return numeric(f'Add {b} each time. Continue: {", ".join(map(str,seq))}, __.',
                       f'हर बार {b} जोड़ें। क्रम आगे बढ़ाएँ: {", ".join(map(str,seq))}, __।',a+4*b,
                       f'{seq[-1]} + {b} = {a+4*b}.',f'{seq[-1]} + {b} = {a+4*b}।')
    if name=='shape pattern':
        return numeric(f'A triangle, square, circle repeat in that order. What is the position of circle number {a}?',
                       f'त्रिभुज, वर्ग, वृत्त इसी क्रम में दोहरते हैं। {a}वें वृत्त का स्थान क्या है?',3*a,
                       f'Circles occupy every third position: 3 × {a} = {3*a}.',f'वृत्त हर तीसरे स्थान पर है: 3 × {a} = {3*a}।')
    if name in ('triangular number','square number','cube number'):
        key=a*(a+1)//2 if name=='triangular number' else a**(2 if name=='square number' else 3)
        if name=='triangular number':
            seq=' + '.join(map(str,range(1,a+1)))
            return numeric(f'A triangular dot arrangement has rows of 1 through {a} dots. How many dots?',
                           f'त्रिभुजाकार बिंदु व्यवस्था की पंक्तियों में 1 से {a} तक बिंदु हैं। कुल कितने बिंदु हैं?',key,
                           f'{seq} = {key}.',f'{seq} = {key}।')
        power=2 if name=='square number' else 3;expression=' × '.join([str(a)]*power)
        return numeric(f'Calculate {expression}.',f'{expression} का मान निकालें।',key,f'{expression} = {key}.',f'{expression} = {key}।')
    if name=='powers of 2':
        exponent=2+seed%6;key=2**exponent
        return numeric(f'Start at 1 and double {exponent} times. What number do you obtain?',
                       f'1 से शुरू करके {exponent} बार दुगुना करें। कौन-सी संख्या मिलेगी?',key,
                       f'{" × ".join(["2"]*exponent)} = {key}.',f'{" × ".join(["2"]*exponent)} = {key}।')
    if name=='Virahanka numbers':
        seq=[1,2]
        for _ in range(10):seq.append(sum(seq[-2:]))
        i=seed%7;shown=seq[i:i+4];key=seq[i+4]
        return numeric(f'Each next term is the sum of the preceding two. Continue: {", ".join(map(str,shown))}, __.',
                       f'अगला पद पिछले दो पदों का योग है। आगे बढ़ाएँ: {", ".join(map(str,shown))}, __।',key,
                       f'{shown[-2]} + {shown[-1]} = {key}.',f'{shown[-2]} + {shown[-1]} = {key}।')
    if name in ('addition','subtraction','number','natural number','consecutive number','number line'):
        if name=='subtraction':key=a+b-b;expression=f'{a+b} − {b}'
        else:key=a+b;expression=f'{a} + {b}'
        return numeric(f'Calculate {expression}.',f'{expression} का मान निकालें।',key,
                       f'{expression} = {key}.',f'{expression} = {key}।')
    if name=='Collatz conjecture':
        number=3+seed%16;key=number//2 if number%2==0 else 3*number+1
        return numeric(f'For an even number divide by 2; for an odd number use 3 × n + 1. Starting at {number}, what is the next number?',
                       f'सम संख्या को 2 से भाग दें; विषम संख्या के लिए 3 × n + 1 करें। {number} से शुरू करने पर अगली संख्या क्या होगी?',key,
                       f'This single step gives {key}; it does not prove the conjecture.',f'इस एक चरण में {key} मिलता है; इससे अनुमान सिद्ध नहीं होता।')
    if name=='palindrome':
        number=100*a+10*b+a if seed%2 else 100*a+10*b+(a+1)%10;yes=str(number)==str(number)[::-1]
        return mcq(f'Does {number} read the same forwards and backwards?',f'क्या {number} आगे और पीछे से समान पढ़ी जाती है?',yes,
                   f'Reversing its digits gives {str(number)[::-1]}.',f'अंकों को उलटने पर {str(number)[::-1]} मिलता है।')
    if name=='Kaprekar number':
        number=1234+seed%5*1111;digits=str(number);large=int(''.join(sorted(digits,reverse=True)));small=int(''.join(sorted(digits)))
        return numeric(f'One Kaprekar-routine step sorts the digits of {number} in decreasing and increasing order and subtracts. What is {large} − {small}?',
                       f'कापरेकर प्रक्रिया के एक चरण में {number} के अंक घटते और बढ़ते क्रम में रखें और घटाएँ। {large} − {small} कितना है?',large-small,
                       f'{large} − {small} = {large-small}.',f'{large} − {small} = {large-small}।')
    if name=='supercell':
        return mcq(f'A cell contains {a+10}. Its immediate neighbours contain {a} and {b}. Is it greater than both?',
                   f'एक खाने में {a+10} है। उसके पास के खानों में {a} और {b} हैं। क्या यह दोनों से बड़ा है?',True,
                   f'{a+10} exceeds both neighbouring values.',f'{a+10} दोनों पास की संख्याओं से बड़ा है।')
    if name in ('estimation','rounding'):
        number=100+seed%80;key=((number+5)//10)*10
        return numeric(f'Round {number} to the nearest ten; round up when the units digit is 5.',
                       f'{number} को निकटतम दहाई में लिखें; इकाई का अंक 5 हो तो ऊपर की दहाई लें।',key,
                       f'The nearest ten is {key}.',f'निकटतम दहाई {key} है।')
    if name in ('point','line','ray','line segment','arm of angle','vertex','angle','intersecting lines'):
        label=chr(ord('P')+seed%8)
        if name in ('line','ray','line segment'):
            key={'line':0,'ray':1,'line segment':2}[name]
            return numeric(f'How many endpoints does a {name} labelled {label} have?',
                           f'{label} नाम वाली '+{'line':'रेखा','ray':'किरण','line segment':'रेखाखंड'}[name]+' के कितने अंत बिंदु होते हैं?',key,
                           f'The number of endpoints is {key}.',f'अंत बिंदुओं की संख्या {key} है।')
        if name=='point':
            return numeric(f'How many dimensions does the point {label} have?',f'बिंदु {label} की कितनी विमाएँ होती हैं?',0,
                           'A point has position but no size.', 'बिंदु का स्थान होता है, आकार नहीं।')
        if name=='intersecting lines':
            return numeric(f'Two distinct straight lines cross at {label}. How many common points do they have?',
                           f'दो अलग सीधी रेखाएँ {label} पर काटती हैं। उनके कितने उभयनिष्ठ बिंदु हैं?',1,
                           'Two distinct intersecting straight lines share one point.', 'दो अलग प्रतिच्छेदी सीधी रेखाओं का एक उभयनिष्ठ बिंदु होता है।')
        return numeric(f'Two rays start at {label} and form an angle. How many arms does this angle have?',
                       f'{label} से दो किरणें निकलकर कोण बनाती हैं। इस कोण की कितनी भुजाएँ हैं?',2,
                       f'The two rays are the arms; {label} is their common vertex.',f'दोनों किरणें भुजाएँ हैं; {label} उभयनिष्ठ शीर्ष है।')
    if name in ('straight angle','complete angle','degree','rotation','right angle'):
        if name=='straight angle':key=180;en='a half turn';hi='आधा घुमाव'
        elif name in ('complete angle','degree'):key=360;en='one full turn';hi='एक पूरा घुमाव'
        else:key=90;en='a quarter turn';hi='चौथाई घुमाव'
        turns=1+seed%4
        return numeric(f'{en.capitalize()} measures {key}°. How many degrees do {turns} such turns total?',
                       f'{hi} का माप {key}° है। ऐसे {turns} घुमावों का कुल माप कितने अंश होगा?',turns*key,
                       f'{turns} × {key} = {turns*key} degrees.',f'{turns} × {key} = {turns*key} अंश।')
    if name in ('obtuse angle','reflex angle','perpendicular','angle bisector','protractor','regular polygon','plane geometry'):
        if name=='angle bisector':
            angle=40+2*(seed%50)
            return numeric(f'A bisector divides an angle of {angle}° into equal parts. What is each part?',
                           f'समद्विभाजक {angle}° के कोण को बराबर भागों में बाँटता है। हर भाग का माप क्या है?',angle//2,
                           f'{angle} ÷ 2 = {angle//2} degrees.',f'{angle} ÷ 2 = {angle//2} अंश।')
        if name=='perpendicular':
            return numeric(f'Perpendicular lines meet at {chr(65+seed%10)}. What is their angle in degrees?',
                           f'लंब रेखाएँ {chr(65+seed%10)} पर मिलती हैं। उनके बीच का कोण कितने अंश का है?',90,
                           'Perpendicular lines form a right angle of 90 degrees.','लंब रेखाएँ 90 अंश का समकोण बनाती हैं।')
        if name=='protractor':
            angle=20+seed%12*10
            return numeric(f'A ray is aligned at 0° on a protractor; the other crosses {angle}° on the same scale. What is the angle?',
                           f'चाँदे पर एक किरण 0° पर है; दूसरी उसी पैमाने पर {angle}° पर है। कोण का माप क्या है?',angle,
                           f'Read {angle} degrees from the aligned zero.',f'उसी शून्य से {angle} अंश पढ़ें।')
        if name=='regular polygon':
            return mcq(f'A polygon has {a+1} equal sides and all angles equal. Is it regular?',
                       f'बहुभुज की {a+1} भुजाएँ बराबर हैं और सभी कोण बराबर हैं। क्या यह सम बहुभुज है?',True,
                       'Both equal sides and equal angles are required.','सभी भुजाएँ और सभी कोण बराबर होने चाहिए।')
        if name=='plane geometry':
            return numeric(f'A rectangle labelled {chr(65+seed%10)} is a plane figure. How many dimensions does it have?',
                           f'{chr(65+seed%10)} नाम वाला आयत समतल आकृति है। इसकी कितनी विमाएँ हैं?',2,
                           'A plane figure has two dimensions.','समतल आकृति की दो विमाएँ होती हैं।')
        angle=(100+seed%7*10) if name=='obtuse angle' else (190+seed%16*10)
        return mcq(f'Is {angle}° '+('greater than 90° and less than 180°?' if name=='obtuse angle' else 'greater than 180° and less than 360°?'),
                   f'क्या {angle}° '+('90° से अधिक और 180° से कम है?' if name=='obtuse angle' else '180° से अधिक और 360° से कम है?'),True,
                   'Compare the measure with the two stated bounds.','माप की तुलना दी गई दोनों सीमाओं से करें।')
    return None


def expanded(target,nodes,seed):
    from diagnostic.curriculum import teaching_name
    question=body(teaching_name(nodes[target]['en']),seed)
    if not question:return None
    return dict(question,id='practice-'+uuid4().hex,concept_id=target,concept_en=nodes[target]['en'],
                concept_hi=nodes[target]['hi'],review_status='PENDING',source_references=[],
                scoring_rule='Exact key; other input unscorable.',
                possible_difficulty='Original transfer draft; confirm independently before inferring a difficulty.')


def worked_example(name,variant):
    from diagnostic.curriculum import teaching_name
    name=teaching_name(name)
    q=body(name,variant+3)
    if not q:return None
    return {'en':q['en']+' '+q['feedback_en'],'hi':q['hi']+' '+q['feedback_hi'],
            'provenance':'Original worked example, not a quotation from NCERT; review pending.'}
