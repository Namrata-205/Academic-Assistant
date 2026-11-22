"""Original, bounded teaching scaffolds for verified curriculum concepts.

These are authored explanations, not extracted quotations or model responses.
Teacher review is still required. Only direct, available source support enables them.
"""
CARDS = {
 'acute angle': (
  'An angle measures how far one arm turns away from the other. A right angle is a quarter-turn: 90°. An acute angle is a smaller opening: greater than 0° but less than 90°.',
  'Imagine opening a book a little, then opening it to a square corner. The smaller opening is acute. The length of the pages does not determine the angle; the amount of opening does.',
  'कोण बताता है कि एक भुजा दूसरी भुजा से कितनी घूमी है। समकोण एक चौथाई घुमाव है: 90°। न्यून कोण का खुलाव इससे कम होता है: 0° से अधिक और 90° से कम।',
  'किताब को थोड़ा खोलिए, फिर समकोण जितना खोलिए। पहले वाला छोटा खुलाव न्यून कोण है। पन्नों की लंबाई नहीं, उनके बीच का खुलाव देखिए।'),
 'right angle': (
  'A right angle measures 90°. It is one quarter of a complete turn. “Right” names the size of the angle; it does not mean the angle must point to the right.',
  'Trace two neighbouring edges of a rectangular sheet. Their corner makes a right angle. Rotate the sheet: the corner still has the same opening.',
  'समकोण 90° का कोण है। यह पूरे घुमाव का एक चौथाई है। इसका नाम कोण का माप बताता है, दाईं दिशा में होना नहीं।',
  'आयताकार कागज की पास वाली दो धारियाँ देखिए। वे कोने पर समकोण बनाती हैं। कागज घुमाने पर भी उस कोने का खुलाव नहीं बदलता।'),
 'straight angle': (
  'A straight angle measures 180°: half a complete turn. Its two arms point in opposite directions from the same endpoint.',
  'Start facing forward and turn halfway around. You now face the opposite direction. That half-turn is twice a 90° quarter-turn.',
  'सरल कोण 180° का होता है: पूरे घुमाव का आधा। इसकी दोनों भुजाएँ एक ही अंतिम बिंदु से विपरीत दिशाओं में जाती हैं।',
  'सामने देखकर खड़े हों और आधा घुमाव लें। अब आप उलटी दिशा में देखेंगे। यह आधा घुमाव 90° के दो चौथाई घुमावों के बराबर है।'),
 'angle': (
  'Draw a dot O. From O, draw one arrow to the right and another arrow slanting upwards. Both start at the same dot. The opening between their directions is an angle.',
  'The arrows show two rays: each starts at O and keeps going in one direction. They are the arms of the angle. O is the vertex, which means the meeting point. Turn one arm further away: the opening grows, but O stays in the same place.',
  'एक बिंदु O बनाएँ। O से एक तीर दाईं ओर और दूसरा तिरछा ऊपर की ओर बनाएँ। दोनों एक ही बिंदु से शुरू होते हैं। उनकी दिशाओं के बीच का खुलाव कोण है।',
  'ये तीर दो किरणें दिखाते हैं। हर किरण O से शुरू होकर एक दिशा में आगे जाती रहती है। ये कोण की भुजाएँ हैं। मिलने वाला बिंदु O उसका शीर्ष है। एक भुजा को दूसरी से और दूर घुमाएँ: खुलाव बढ़ता है, लेकिन O वहीं रहता है।'),
 'vertex': (
  'The vertex is the dot where the two arms of an angle meet. You can find it by following both arms back to their shared starting point.',
  'Try it on paper: make a dot O. Draw two arrows from O, one to the right and one upwards. Follow each arrow backwards with your finger. Both bring you to O, so O is the vertex. The arrows are the arms; the dot is the vertex. Making an arrow longer does not change that meeting point.',
  'कोण की दोनों भुजाएँ जिस बिंदु पर मिलती हैं, उसे शीर्ष कहते हैं। दोनों भुजाओं पर पीछे की ओर चलकर उनके एक ही शुरुआती बिंदु तक पहुँचिए। वही शीर्ष है।',
  'कागज पर O नाम का बिंदु बनाएँ। O से एक तीर दाईं ओर और एक ऊपर की ओर बनाएँ। उँगली से दोनों तीरों पर पीछे की ओर चलें। दोनों बार O पर पहुँचेंगे, इसलिए O शीर्ष है। तीर भुजाएँ हैं और मिलने वाला बिंदु शीर्ष है। तीर लंबा करने पर भी मिलने वाला बिंदु नहीं बदलता।'),
 'number pattern': (
  'A number pattern follows a rule. To find a possible rule, compare neighbouring numbers and test the same rule on every step shown.',
  'For 3, 6, 9, 12, each step adds 3. So a continuation using that rule is 15. A short list can fit more than one rule; explain the rule you chose.',
  'संख्या पैटर्न एक नियम का पालन करता है। संभावित नियम खोजने के लिए पास-पास की संख्याओं की तुलना करें और हर दिए गए चरण पर वही नियम जाँचें।',
  '3, 6, 9, 12 में हर बार 3 जुड़ता है। इसी नियम से अगली संख्या 15 होगी। छोटी सूची के कई नियम हो सकते हैं, इसलिए अपना चुना नियम भी बताएँ।'),
 'odd number': (
  'An odd whole number cannot be split into two equal whole-number groups: dividing by 2 leaves remainder 1.',
  'Put 7 counters into pairs. Three pairs use 6 counters and one is left over. That leftover is why 7 is odd.',
  'विषम पूर्ण संख्या को दो बराबर पूर्ण-संख्या समूहों में नहीं बाँट सकते। 2 से भाग देने पर शेष 1 रहता है।',
  '7 गोटियों के जोड़े बनाएँ। तीन जोड़ों में 6 गोटियाँ लगती हैं और एक बचती है। इसलिए 7 विषम है।'),
 'even number': (
  'An even whole number can be split into two equal whole-number groups. Dividing by 2 leaves no remainder.',
  'Pair up 8 counters. Four pairs use all 8, with nothing left over. This is why 8 is even.',
  'सम पूर्ण संख्या को दो बराबर पूर्ण-संख्या समूहों में बाँट सकते हैं। 2 से भाग देने पर शेष 0 होता है।',
  '8 गोटियों के जोड़े बनाएँ। चार जोड़ों में सारी गोटियाँ लग जाती हैं और कोई नहीं बचती। इसलिए 8 सम है।'),
 'digit sum': (
  'The digit sum adds the individual digits of a number. It does not add their place values.',
  'For 352, separate the digits: 3, 5 and 2. Add 3 + 5 = 8, then 8 + 2 = 10. The digit sum is 10; the original number remains 352.',
  'अंकों का योग निकालने के लिए संख्या के अलग-अलग अंक जोड़ते हैं, उनके स्थानीय मान नहीं।',
  '352 के अंक 3, 5 और 2 हैं। पहले 3 + 5 = 8, फिर 8 + 2 = 10। अंकों का योग 10 है; मूल संख्या 352 ही रहती है।'),
 'square number': (
  'A square number is made by multiplying a whole number by itself. You can arrange that many objects in equal rows and columns.',
  'Arrange 9 dots in 3 rows with 3 dots in each row. There are 3 × 3 = 9 dots, so 9 is a square number. Multiplying by 2 would double a number, not square it.',
  'किसी पूर्ण संख्या को उसी से गुणा करने पर वर्ग संख्या मिलती है। इतनी वस्तुओं को बराबर पंक्तियों और स्तंभों में लगा सकते हैं।',
  '9 बिंदुओं को 3 पंक्तियों में रखें, हर पंक्ति में 3 बिंदु। 3 × 3 = 9, इसलिए 9 वर्ग संख्या है। 2 से गुणा करना दुगुना करना है, वर्ग करना नहीं।'),
}


def explain(name, sources, language, request):
    from diagnostic.curriculum import teaching_name
    name=teaching_name(name)
    if name not in CARDS:
        return None
    focus = request.get('focus', {}).get('id')
    source = next((s for s in sources if s.get('support_relation', 'direct') == 'direct'
                   and focus in s.get('concept_ids', [s.get('concept_id')])), None)
    if not source:
        return None
    definition, analogy = CARDS[name][2:] if language == 'hi' else CARDS[name][:2]
    repair = request.get('mode') in ('still_confused', 'simpler', 'another_example')
    from diagnostic.teaching_feedback import original_example_paragraph
    example = original_example_paragraph(request, sources, language)
    if example:
        example=dict(example,text=example['text'].removeprefix('Original worked example: ').removeprefix('मौलिक हल किया हुआ उदाहरण: '))
    if repair and name in ('angle','vertex'):
        letter=['O','P','S','T'][request.get('example_variant',0)%4]
        text=(f'एक बिंदु {letter} बनाएँ। उसी बिंदु से अलग-अलग दिशाओं में दो तीर बनाएँ। अब दोनों तीरों पर पीछे की ओर उँगली चलाएँ। दोनों बार {letter} पर पहुँचते हैं। इसलिए {letter} शीर्ष है। एक तीर को और लंबा बनाएँ: मिलने वाला बिंदु अब भी {letter} ही है। भुजा की लंबाई बदलती है, शीर्ष नहीं।' if language=='hi' else
              f'Make a dot {letter}. Draw two arrows from that dot in different directions. Now trace each arrow backwards with your finger. Both lead to {letter}, so {letter} is the vertex. Extend one arrow: the meeting point is still {letter}. You changed the length of an arm, not where the arms meet.')
        example={'text':text,'citations':[source['id']],'evidence':source['excerpt'],
                 'kind':'original_worked_example','review_status':'PENDING'}
    if repair and name=='acute angle':
        angle=[35,50,70,95,110,180][request.get('example_variant',0)%6]
        yes=angle<90
        text=(f'एक नया उदाहरण: {angle}°। पहले जाँचें: यह 0° से अधिक है। अब 90° से तुलना करें: {angle}° '+
              ('90° से कम है, इसलिए दोनों शर्तें पूरी हैं। यह न्यून कोण है।' if yes else '90° से अधिक है। छोटी खुलावट की शर्त पूरी नहीं है, इसलिए यह न्यून कोण नहीं है।') if language=='hi' else
              f'Try a new example: {angle}°. First check that it is greater than 0°. It is. Next compare it with 90°: {angle}° '+
              ('is smaller than 90°, so both conditions hold. It is acute.' if yes else 'is larger than 90°. That fails the smaller-opening condition, so it is not acute.'))
        example={'text':text,'citations':[source['id']],'evidence':source['excerpt'],
                 'kind':'original_worked_example','review_status':'PENDING'}
    paragraphs = []
    texts = [analogy, definition] if repair else [definition, analogy]
    if repair and example:
        texts = [definition if name in ('angle','vertex') else analogy if request.get('example_variant',0)%2 else definition]
    for text in texts:
        paragraphs.append({'text': text, 'citations': [source['id']], 'evidence': source['excerpt'],
                           'kind': 'authored_explanation', 'review_status': 'PENDING'})
    if repair and example:
        paragraphs.append(example)
    question=('इस चित्र में दोनों तीर किस बिंदु से शुरू होते हैं?' if language=='hi' else 'In your drawing, which point do both arrows start from?') if name in ('angle','vertex') else (
        'किस हिस्से पर रुक गए: शब्दों का अर्थ, या उदाहरण का कोई चरण?' if language=='hi' else 'Which part should we unpack next: the words, or a step in the example?')
    paragraphs.append({'text':question,
                       'citations': [], 'kind': 'teaching_question'})
    return paragraphs


def lesson(target,nodes,sources,language,request):
    """Teach the requested topic even when personalization selects a foundation."""
    focus=request.get('focus',{}).get('id')
    target_request=dict(request,focus={'id':target})
    result=explain(nodes[target]['en'],sources,language,target_request)
    if not result:
        from diagnostic.curriculum_content import fact
        from diagnostic.curriculum_items import make
        import re
        info=fact(target)
        source=next((s for s in sources if target in s.get('concept_ids',[s.get('concept_id')]) and s.get('support_relation','direct')=='direct'),None)
        if not info or not source:return None
        text=info[1 if language=='hi' else 0]
        result=[{'text':text,'citations':[source['id']],'evidence':source['excerpt'],'kind':'authored_explanation','review_status':'PENDING'}]
        item=make(target,nodes,request.get('example_variant',0)+7)
        if item:
            prompt=item[language];answer=item['answer']
            if item['type']=='mcq':
                match=re.search(r'(?:^|\s)'+answer+r':\s*(.*?)(?=;\s*[A-D]:|$)',prompt)
                answer=match[1].strip() if match else answer
                prompt=re.split(r'\s+[A-D]:\s*',prompt)[0]
            if answer!=text:
                label='एक उदाहरण: ' if language=='hi' else 'Try this example: '
                worked=label+prompt+(' उत्तर: ' if language=='hi' else ' Answer: ')+str(answer)+'. '+item['feedback_'+language]
                result.append({'text':worked,'citations':[source['id']],'evidence':source['excerpt'],'kind':'original_worked_example','review_status':'PENDING'})
    if focus in nodes and focus!=target:
        foundation=explain(nodes[focus]['en'],sources,language,request)
        if foundation:result=foundation[:1]+result
    return result
