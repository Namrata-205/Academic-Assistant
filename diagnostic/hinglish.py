"""Request-scoped Hinglish style. English sources and immutable scoring keys stay unchanged."""
import re
from contextvars import ContextVar

STYLE=ContextVar('chat_response_style',default='en')


def detect(text,requested='en'):
    if requested=='hi':return 'hi'
    if requested=='hinglish':return 'hinglish'
    tokens=set(re.findall(r'[a-z]+',text.casefold()))
    markers={'mujhe','mujhko','mera','meri','mere','nahi','nahin','samajh','samajhta','samajhti','samjhta','samjhti','samjha','samjhao','samjhana','theek','kaise','kya','mein','hain','hai','hota','hoti','aata','aati','sawal','sawaal','batao','thoda','ache','achhe','samajhta','samajhata'}
    return 'hinglish' if len(tokens&markers)>=2 else 'en'


QUESTIONS={
 'TQ_FOUNDATION_01':'4 circles aur 3 circles milakar kul kitni cheezein hongi?',
 'TQ_FOUNDATION_02':'Teiis ko digits mein likho.',
 'TQ_FOUNDATION_03':'508 mein kitne digits hain?',
 'TQ_FOUNDATION_04':'472 ka aakhri digit kaunsa hai?',
 'TQ_FOUNDATION_05':'39 ke turant baad kaunsa number aata hai?',
 'TQ_FOUNDATION_06':'68 aur 70 ke beech kaunsa number aata hai?',
 'TQ_FOUNDATION_07':'Number line par 3 se shuru karo. Right ki taraf 2 steps jao. Kis number par pahunchoge?',
 'TQ_FOUNDATION_08':'Number line par 4 aur 9 mein se kaunsa number zyada right par hai?',
 'DQ_0018_1':'Ek line segment ke kitne endpoints hote hain?',
 'DQ_0018_2':'Kiski fixed length aur do endpoints hote hain? A: line; B: ray; C: line segment; D: plane.',
 'DQ_0018_3':'Ek segment points A aur B ko jodta hai. Yahan kitne endpoints hain?',
 'DQ_0020_1':'Ek angle banane ke liye kitni arms chahiye?',
 'DQ_0020_2':'Angle ki dono arms jahan milti hain, us point ko kya kehte hain? A: centre; B: vertex; C: length; D: plane.',
 'DQ_0020_3':'Angle kaise banta hai? A: ek common endpoint wali do rays; B: ek point; C: do alag points; D: sirf ek line segment.',
 'DQ_0024_1':'Ek right angle kitne degrees ka hota hai?',
 'DQ_0024_3':'Square ke ek corner par angle kitne degrees ka hota hai?',
 'DQ_0025_3':'Acute angle kya hota hai? A: exactly 90°; B: 0° se bada aur 90° se chhota; C: exactly 180°; D: 180° se bada.'}


def question(q):
    if q['id'] in QUESTIONS:return QUESTIONS[q['id']]
    text=q['en']
    substitutions=[
        (r'^Write the next number:', 'Agla number likho:'),
        (r'^Continue this pattern:', 'Is pattern ko aage badhao:'),
        (r'^Which number is odd\?', 'Kaunsa number odd hai?'),
        (r'^Which number is even\?', 'Kaunsa number even hai?'),
        (r'^Which is a square number\?', 'Kaunsa square number hai?'),
        (r'^Which is a right angle\?', 'Kaunsa right angle hai?'),
        (r'^Which angle is acute\?', 'Kaunsa angle acute hai?')]
    for pattern,replacement in substitutions:
        if re.search(pattern,text):return re.sub(pattern,replacement,text)
    match=re.search(r'(?:place value|value) of (\d) in (\d+)',text,re.I)
    if match:return f'{match[2]} mein {match[1]} ki place value kya hai?'
    match=re.search(r'(?:sum of the digits of|digit sum of) (\d+)',text,re.I)
    if match:return f'{match[1]} ke saare digits ko jodne par kitna milega?'
    match=re.search(r'(?:What is|Calculate) (\d+) squared',text)
    if match:return f'{match[1]} ka square, yaani {match[1]} × {match[1]}, kitna hoga?'
    return 'Chalo, yeh sawal try karo: '+text


def localize(result):
    if STYLE.get()=='hi':
        if result.get('mode')=='learning_check':result['notice']='इस बातचीत के उत्तर यहीं सहेजे जाते हैं। नैदानिक अंक अलग रहते हैं। प्रश्नों और निर्णय-नियमों की अंतिम समीक्षा बाकी है।'
        elif result.get('mode')=='generated':result['notice']='संदर्भ पहचान और सहायक उद्धरण जाँचे गए हैं। हर गणितीय दावे की सत्यता इससे सिद्ध नहीं होती; पाठ्यपुस्तक से मिलान करें।'
        elif result.get('mode')=='practice_feedback':
            result['message']=result.get('message','').replace('Correct. ','सही उत्तर। ').replace('Let’s work through it. ','इसे समझते हैं। ')
            result['notice']='यह केवल अभ्यास पर प्रतिक्रिया है। इससे नया निदान नहीं होता।'
        elif result.get('mode')=='extractive':result['notice']='व्याख्या उपलब्ध नहीं थी या स्रोत-जाँच पूरी नहीं हुई, इसलिए पाठ्यपुस्तक के सीधे अंश दिखाए गए हैं। ये अंश हैं, नई व्याख्या नहीं।'
        return result
    if STYLE.get()!='hinglish':return result
    result['language']='hinglish'
    if result.get('mode')=='learning_check':
        result['message']='Samjhane se pehle kuch basics check karte hain, taaki pata chale kahan se shuru karna hai.' if result.get('check_number')==1 else 'Ek chhota sawal aur try karo; phir saath mein samjhenge.'
        if result.get('routing',{}).get('topic_assumption'):result['message']='Number patterns samjhane se pehle numbers aur digits ke basics check karte hain. Agar tumhara matlab shapes se hai, toh bata dena.'
        result['notice']='Ye answers isi chat mein save honge. Diagnostic scores alag rahenge.'
    if result.get('mode')=='practice_feedback':
        result['message']=('Bilkul sahi! ' if result.get('practice_score')==1 else 'Chalo, isko step by step dekhte hain. ')+result.get('message','')
    if result.get('mode')=='practice':result['message']='Yeh sawal try karo; phir tumhara answer check karenge.'
    return result
