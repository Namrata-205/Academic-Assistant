from diagnostic.curriculum import teaching_name
"""Original easy-to-hard exam variations with deterministic numeric/MCQ keys."""
import random
from uuid import uuid4
from diagnostic import chat_tutor


def make(cid,nodes,level,mcq=False):
    from diagnostic.curriculum_items import make as curriculum_question
    if cid not in {'MATH6_C0003','MATH6_C0006','MATH6_C0007','MATH6_C0009','MATH6_C0018','MATH6_C0020','MATH6_C0024','MATH6_C0025','MATH6_C0038','MATH6_C0039'}:
        item=curriculum_question(cid,nodes,random.randrange(1000000),level,mcq)
        if item:return item
    name=teaching_name(nodes[cid]['en']);a=random.randint(3,9);b=random.randint(2,5)
    key=None;en=hi=why=None
    if name in ('pattern','number pattern','sequence'):
        if level==1:
            en=f'Start at {a}. Add {b} once. What is the next term?';hi=f'{a} से शुरू करें। एक बार {b} जोड़ें। अगला पद क्या है?';key=a+b;why=f'{a} + {b} = {key}'
        elif level==2:
            en=f'A sequence starts at {a} and adds {b} each time. Find its fifth term.';hi=f'क्रम का पहला पद {a} है और हर बार {b} जुड़ता है। पाँचवाँ पद निकालें।';key=a+4*b;why=f'{a} + 4 × {b} = {key}'
        else:
            en=f'A sequence starts at {a} and adds {b} each time. Find the sum of its third and sixth terms.';hi=f'क्रम का पहला पद {a} है और हर बार {b} जुड़ता है। तीसरे और छठे पद का योग निकालें।';key=(a+2*b)+(a+5*b);why=f'({a} + 2 × {b}) + ({a} + 5 × {b}) = {key}'
    elif name=='square number':
        if level==1:en=f'Find {a} × {a}.';hi=f'{a} × {a} निकालें।';key=a*a;why=f'{a} × {a} = {key}'
        elif level==2:en=f'A square dot array contains {a*a} dots. How many equal rows does it have?';hi=f'वर्गाकार बिंदु व्यवस्था में {a*a} बिंदु हैं। बराबर पंक्तियाँ कितनी हैं?';key=a;why=f'{a} × {a} = {a*a}'
        else:en=f'Two square arrays have {a+b} and {a} dots per side. Find the difference in total dots.';hi=f'दो वर्गाकार व्यवस्थाओं में हर भुजा पर {a+b} और {a} बिंदु हैं। कुल बिंदुओं का अंतर निकालें।';key=(a+b)**2-a*a;why=f'{a+b} × {a+b} − {a} × {a} = {key}'
    elif name in ('odd number','even number'):
        value=a if level==1 else a+b if level==2 else a*b+b
        expression=str(a) if level==1 else f'{a} + {b}' if level==2 else f'{a} × {b} + {b}'
        en=f'Find the remainder when {expression} is divided by 2.';hi=f'{expression} को 2 से भाग देने पर शेष निकालें।';key=value%2;why=f'{value} ÷ 2: remainder / शेष {key}'
    elif name=='digit sum':
        if level<3:
            number=random.randint(100,999) if level==1 else random.randint(1000,9999);key=sum(map(int,str(number)))
            en=f'Find the digit sum of {number}.';hi=f'{number} के अंकों का योग निकालें।';why=' + '.join(str(number))+f' = {key}'
        else:
            key=a;total=3+key+5+8;en=f'The digit sum of 3□58 is {total}. Find the missing digit.';hi=f'3□58 के अंकों का योग {total} है। खाली अंक निकालें।';why=f'{total} − (3 + 5 + 8) = {key}'
    elif name=='place value':
        number=8000+a*100+27
        if a in (2,7,8):a=4;number=8427
        if level==1:en=f'Find the place value of {a} in {number}.';hi=f'{number} में {a} का स्थानीय मान निकालें।';key=a*100;why=f'{a} × 100 = {key}'
        elif level==2:en=f'Replace the hundreds digit of {number} with 1. By how much does the number decrease?';hi=f'{number} के सैकड़े का अंक 1 करें। संख्या कितनी घटेगी?';key=(a-1)*100;why=f'({a} − 1) × 100 = {key}'
        else:en=f'In {number}, replace the hundreds digit by 1 and the tens digit by 5. Find the new number.';hi=f'{number} में सैकड़े का अंक 1 और दहाई का अंक 5 करें। नई संख्या निकालें।';key=8157;why=f'8000 + 100 + 50 + 7 = {key}'
    elif name=='line segment':
        if level==1:en='How many endpoints does a line segment have?';hi='रेखाखंड के कितने अंत बिंदु होते हैं?';key=2;why='Two endpoints / दो अंत बिंदु'
        elif level==2:en=f'Points A and B are at {a} cm and {a+b} cm on a straight ruler. Find AB in cm.';hi=f'सीधे पैमाने पर A और B, {a} सेमी और {a+b} सेमी पर हैं। AB की लंबाई सेमी में निकालें।';key=b;why=f'{a+b} − {a} = {b} cm / सेमी'
        else:en=f'A, B, C lie in that order on a line. AC is {a+b+4} cm and AB is {a} cm. Find BC in cm.';hi=f'A, B, C एक रेखा पर इसी क्रम में हैं। AC = {a+b+4} सेमी और AB = {a} सेमी है। BC सेमी में निकालें।';key=b+4;why=f'{a+b+4} − {a} = {key} cm / सेमी'
    elif name=='acute angle':
        value=10*random.randint(2,8)
        if level==1:
            en=f'An acute angle measures {value}°. How many degrees below 90° is it?';hi=f'न्यून कोण {value}° का है। यह 90° से कितने अंश कम है?';key=90-value;why=f'90 − {value} = {key}°'
        elif level==2:
            en=f'Two acute angles together form 90°. One is {value}°. Find the other.';hi=f'दो न्यून कोण मिलकर 90° बनाते हैं। एक {value}° है। दूसरा निकालें।';key=90-value;why=f'90 − {value} = {key}°'
        else:
            x=a*5;y=b*5;key=90-x-y
            en=f'Three acute angles together form 90°. Two measure {x}° and {y}°. Find the third.';hi=f'तीन न्यून कोण मिलकर 90° बनाते हैं। दो कोण {x}° और {y}° हैं। तीसरा निकालें।';why=f'90 − ({x} + {y}) = {key}°'
    elif name in ('angle','right angle'):
        if level==1:
            en='How many degrees are in a quarter turn?';hi='चौथाई घुमाव में कितने अंश होते हैं?';key=90;why='360 ÷ 4 = 90 degrees / अंश'
        elif level==2:
            value=10*a;en=f'Two angles together form 180°. One measures {value}°. Find the other.';hi=f'दो कोण मिलकर 180° बनाते हैं। एक {value}° है। दूसरा निकालें।';key=180-value;why=f'180 − {value} = {key}°'
        else:
            x=a*10;y=b*10;z=90;en=f'Three angles of {x}°, {y}°, and {z}° occupy part of a full turn. Find the remaining angle.';hi=f'{x}°, {y}° और {z}° के कोण पूरे घुमाव का भाग हैं। शेष कोण निकालें।';key=360-x-y-z;why=f'360 − ({x} + {y} + {z}) = {key}°'
    if key is None:
        item=chat_tutor.practice(cid,nodes)
        if item is None:return None
        return dict(item,difficulty=level,format='mcq' if item['type']=='mcq' else 'numeric')
    why_en=why.replace('Two endpoints / दो अंत बिंदु','Two endpoints').replace('remainder / शेष','remainder').replace('cm / सेमी','cm').replace('degrees / अंश','degrees')
    why_hi=why.replace('Two endpoints / दो अंत बिंदु','दो अंत बिंदु').replace('remainder / शेष','शेष').replace('cm / सेमी','सेमी').replace('degrees / अंश','अंश')
    result=dict(id='exam-'+uuid4().hex,concept_id=cid,concept_en=nodes[cid]['en'],concept_hi=nodes[cid]['hi'],
                en=en,hi=hi,type='numeric',answer=str(key),feedback_en=why_en+'.',feedback_hi=why_hi+'।',
                difficulty=level,format='numeric',review_status='PENDING',source_references=[],
                scoring_rule='Exact final answer; other input unscorable.',possible_difficulty='Exam practice evidence, not a diagnosis.')
    if mcq:
        options=list(dict.fromkeys([key,key+1,key+2,key+3]));random.shuffle(options)
        result.update(en=en+' '+ '; '.join(f'{letter}: {value}' for letter,value in zip('ABCD',options)),
                      hi=hi+' '+ '; '.join(f'{letter}: {value}' for letter,value in zip('ABCD',options)),
                      type='mcq',format='mcq',answer='ABCD'[options.index(key)])
    return result
