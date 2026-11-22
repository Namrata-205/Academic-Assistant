"""Create a first-pass concept-ID glossary; refuses to overwrite review work."""
import json
from diagnostic import engine as e
from diagnostic.bilingual_quality import check_pair

DEFINITIONS = {
 'angle':('Two rays with a common endpoint form an angle.','एक उभयनिष्ठ प्रारंभिक बिंदु वाली दो किरणें कोण बनाती हैं।'),
 'vertex':('The common endpoint of the rays forming an angle is its vertex.','कोण बनाने वाली किरणों का उभयनिष्ठ प्रारंभिक बिंदु उसका शीर्ष है।'),
 'right angle':('A right angle measures 90 degrees.','समकोण का माप 90 अंश है।'),
 'straight angle':('A straight angle measures 180 degrees.','सरल कोण का माप 180 अंश है।'),
 'acute angle':('An acute angle is greater than 0 degrees and smaller than 90 degrees.','न्यून कोण 0 अंश से अधिक और 90 अंश से कम होता है।'),
 'obtuse angle':('An obtuse angle is greater than 90 degrees and smaller than 180 degrees.','अधिक कोण 90 अंश से अधिक और 180 अंश से कम होता है।'),
 'reflex angle':('A reflex angle is greater than 180 degrees and smaller than 360 degrees.','प्रतिवर्ती कोण 180 अंश से अधिक और 360 अंश से कम होता है।'),
 'complete angle':('A complete angle measures 360 degrees.','पूर्ण कोण का माप 360 अंश है।'),
 'arm of angle':('The 2 rays forming an angle are its arms.','कोण बनाने वाली 2 किरणें उसकी भुजाएँ हैं।'),
 'degree':('One full turn contains 360 degrees.','एक पूर्ण घुमाव में 360 अंश होते हैं।'),
 'line segment':('A line segment has 2 endpoints.','रेखाखंड के 2 अंत बिंदु होते हैं।'),
 'ray':('A ray has 1 starting point and extends endlessly in one direction.','किरण का 1 प्रारंभिक बिंदु होता है और यह एक दिशा में अनंत तक जाती है।'),
 'number pattern':('A number pattern follows a rule. For example: 2, 4, 6, 8 adds 2 each time.','संख्या पैटर्न एक नियम का पालन करता है। उदाहरण: 2, 4, 6, 8 में हर बार 2 जोड़ते हैं।'),
 'odd number':('An odd number leaves remainder 1 on division by 2.','विषम संख्या को 2 से भाग देने पर शेष 1 रहता है।'),
 'even number':('An even number leaves remainder 0 on division by 2.','सम संख्या को 2 से भाग देने पर शेष 0 रहता है।'),
 'square number':('A square number is a number multiplied by itself: 4 × 4 = 16.','किसी संख्या को उसी से गुणा करने पर वर्ग संख्या मिलती है: 4 × 4 = 16।'),
 'digit':('A digit is one of the symbols 0 to 9.','अंक 0 से 9 तक के चिह्नों में से एक है।'),
 'number':('A number can describe how many objects a collection contains.','संख्या बता सकती है कि किसी समूह में कितनी वस्तुएँ हैं।'),
 'number line':('Numbers increase as we move right on a number line.','संख्या रेखा पर दाईं ओर जाने पर संख्याएँ बढ़ती हैं।'),
 'consecutive number':('Consecutive whole numbers differ by 1.','क्रमागत पूर्ण संख्याओं में 1 का अंतर होता है।'),
 'digit sum':('The digit sum of 352 is 3 + 5 + 2 = 10.','352 के अंकों का योग 3 + 5 + 2 = 10 है।'),
 'place value':('In 3452, the digit 4 is in the hundreds place: 4 × 100 = 400.','3452 में अंक 4 सैकड़े के स्थान पर है: 4 × 100 = 400।')}


def run():
    from diagnostic.book_chat import GLOSSARY
    path=e.ROOT/'diagnostic/bilingual_glossary.json'
    if path.exists():raise FileExistsError('Preserve completed glossary reviews; author a new version instead.')
    nodes,_=e.load_graph(); concepts={}
    for cid,node in nodes.items():
        if node['en'] not in DEFINITIONS:continue
        en,hi=DEFINITIONS[node['en']]
        parity=check_pair(en,hi)
        if not parity['passed']:raise ValueError((cid,parity))
        concepts[cid]={'concept_id':cid,'en':node['en'],'hi':GLOSSARY.get(node['en'],node['hi']),
                       'definition_en':en,'definition_hi':hi,'invariant_check':parity,
                       'review_status':'PENDING','reviewer':'','reviewed_at':'',
                       'provenance':'AI-authored glossary draft; textbook support remains separately cited.'}
    path.write_text(json.dumps({'version':'bilingual-glossary-v1','concepts':concepts},ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':run()
