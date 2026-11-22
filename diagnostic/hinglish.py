"""Request-scoped Hinglish style. English sources and immutable scoring keys stay unchanged."""
import re
from contextvars import ContextVar

STYLE=ContextVar('chat_response_style',default='en')


MARKERS = set(('mujhe muje mujhko mera meri mere nahi nahin nhi nai samajh samajhta samajhti samjhta '
               'samjhti samjha samjhao samjhana samjhaao samjhaiye samjhaaye kaise kese kya mein main hai hain '
               'hota hoti hote aata aati sawal sawaal batao bataiye bataye thoda thodi aur karo karein kijiye '
               'likho nikalo wala wali hum tum aap yeh ye isko usko yaani kyun kyu kyon matlab zyada kam tak').split())
STRONG = set('mujhe muje mujhko nahi nahin nhi samajh samjha samjhao samjhaao samjhaiye batao bataiye bataye kaise kese kya'.split())


def detect(text,requested='en'):
    if requested in ('hi','hinglish'):
        return requested
    tokens=set(re.findall(r'[a-z]+',text.casefold()))
    if tokens & STRONG or len(tokens & MARKERS)>=2:
        return 'hinglish'
    if re.search(r'[\u0900-\u097f]',text):
        return 'hi'
    return 'en'


_CONSONANTS = dict(zip('कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहळक़ख़ग़ज़ड़ढ़फ़',
    'k kh g gh ng ch chh j jh ny t th d dh n t th d dh n p ph b bh m y r l v sh sh s h l q kh g z r rh f'.split()))
_VOWELS = dict(zip('अआइईउऊऋएऐओऔऑ', 'a aa i ee u oo ri e ai o au o'.split()))
_MARKS = dict(zip('ािीुूृेैोौॉ', 'aa i ee u oo ri e ai o au o'.split()))
_TERMS = {'समकोण':'right angle','सरल कोण':'straight angle','न्यून कोण':'acute angle','अधिक कोण':'obtuse angle',
          'रेखाखंड':'line segment','स्थानीय मान':'place value','अंकों का योग':'digit sum','संख्या पैटर्न':'number pattern',
          'पूर्ण घुमाव':'full turn','घड़ी की सुई':'clock hand','चित्र':'diagram','कोण':'angle','सवाल':'sawaal',
          'प्रश्न':'question','उदाहरण':'example','उत्तर':'answer','में':'mein','नहीं':'nahi','हैं':'hain',
          'है':'hai','कहते':'kehte','लिए':'liye','कीजिए':'kijiye','देखिए':'dekhiye','खुलाव':'khulaav'}


def romanize(text):
    for term, label in sorted(_TERMS.items(), key=lambda pair:-len(pair[0])):
        text=re.sub(r'(?<![\u0900-\u097f])'+re.escape(term)+r'(?![\u0900-\u097f])',label,text)
    def word(match):
        value=match[0]
        output=[]
        for i,char in enumerate(value):
            following=value[i+1:i+2]
            if char in _CONSONANTS:
                output.append(_CONSONANTS[char]+('a' if following and following not in _MARKS and following!='्' else ''))
            elif char in _VOWELS:
                output.append(_VOWELS[char])
            elif char in _MARKS:
                output.append(_MARKS[char])
            elif char in 'ंँ':
                output.append('n')
            elif char=='ः':
                output.append('h')
            elif char not in '़्':
                output.append(char)
        return ''.join(output)
    text=text.translate(str.maketrans('०१२३४५६७८९।॥','0123456789..'))
    return re.sub(r'[\u0900-\u0963]+',word,text)


def authored(paragraphs):
    return [dict(p,text=romanize(p['text'])) for p in paragraphs]


def feedback(q, language):
    return romanize(q.get('feedback_hi') or q.get('feedback_en','')) if STYLE.get()=='hinglish' else q.get('feedback_'+language,'')


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
    translated = romanize(q.get('hi',''))
    numbers = lambda value: sorted(re.findall(r'\d+',value))
    options = lambda value: re.findall(r'\b[A-D]:',value)
    if translated and numbers(translated)==numbers(text) and options(translated)==options(text):
        return translated
    return 'Chalo, yeh sawaal try karo: '+text


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
        message=result.get('message','').removeprefix('Correct. ').removeprefix('Let’s work through it. ')
        result['message']=('Bilkul sahi! ' if result.get('practice_score')==1 else 'Chalo, isko step by step dekhte hain. ')+message
    if result.get('status')=='clarify':
        result['message']='Aap kis concept ke baare mein pooch rahe hain?'
    if result.get('status')=='insufficient_sources':
        result['message']='Is topic ko samjhane ke liye textbook mein seedha reference nahi mila.'
    if result.get('mode')=='extractive':
        result['message']='Abhi Hinglish mein explanation tayyar nahi ho paayi. Kitab ke asli passages neeche hain.'
    if result.get('mode')=='practice_unavailable':
        result['message']='Abhi is topic ka naya practice sawaal nahi mila. Explanation maango ya doosra topic chuno.'
    if result.get('mode')=='practice':result['message']='Yeh sawal try karo; phir tumhara answer check karenge.'
    return result
