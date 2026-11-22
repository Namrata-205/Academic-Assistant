"""Additional original prerequisite probes for chat only; human review pending."""
from diagnostic import engine as e


def load():
    nodes,_=e.load_graph();bank=e.load_bank()
    rows=[
        ('MATH6_C0036','How many objects are there altogether: 4 circles and 3 circles?','4 वृत्त और 3 वृत्त मिलाकर कुल कितनी वस्तुएँ हैं?','7'),
        ('MATH6_C0036','Write the number twenty-three using digits.','तेईस को अंकों में लिखें।','23'),
        ('MATH6_C0037','How many digits are in the number 508?','508 में कितने अंक हैं?','3'),
        ('MATH6_C0037','What is the last digit in 472?','472 का अंतिम अंक क्या है?','2'),
        ('MATH6_C0012','What number comes immediately after 39?','39 के तुरंत बाद कौन सी संख्या आती है?','40'),
        ('MATH6_C0012','What number lies between 68 and 70?','68 और 70 के बीच कौन सी संख्या आती है?','69'),
        ('MATH6_C0041','Start at 3 on a number line. Move 2 steps to the right. Where do you arrive?','संख्या रेखा पर 3 से शुरू करें। दाईं ओर 2 कदम जाएँ। आप किस संख्या पर पहुँचेंगे?','5'),
        ('MATH6_C0041','Which number is farther right on a number line: 4 or 9?','संख्या रेखा पर 4 और 9 में से कौन सी संख्या अधिक दाईं ओर है?','9')]
    for i,(cid,en,hi,key) in enumerate(rows,1):
        bank.append({'id':f'TQ_FOUNDATION_{i:02}','concept_id':cid,'concept_en':nodes[cid]['en'],'concept_hi':nodes[cid]['hi'],
            'en':en,'hi':hi,'type':'numeric','answer':key,'scoring_rule':'Exact numerical equality; other text unscorable.',
            'possible_difficulty':'Possible difficulty with this foundational item; language or calculation error may also explain the response.',
            'source_references':[],'review_status':'PENDING','provenance':'Original chat prerequisite probe, not an NCERT quotation.'})
    from diagnostic.teaching_feedback import angle_item
    bank.extend(angle_item(rotation,straight,f'TQ_ANGLE_DISTINCTION_{i:02}')
                for i,(rotation,straight) in enumerate(((0,False),(0,True),(25,False)),1))
    return bank
