"""Rebuild the original item bank. Run manually; never overwrites review records."""
import json
from pathlib import Path
from diagnostic.engine import load_graph, references

# Each row: concept suffix, three item specifications, possible difficulty.
SPECS = [
 ('0003', [
  ('Write the next number: 3, 6, 9, 12, __.', 'अगली संख्या लिखिए: 3, 6, 9, 12, __।', '15'),
  ('Write the next number: 2, 4, 8, 16, __.', 'अगली संख्या लिखिए: 2, 4, 8, 16, __।', '32'),
  ('Write the next number: 20, 17, 14, 11, __.', 'अगली संख्या लिखिए: 20, 17, 14, 11, __।', '8')],
  'May have difficulty identifying or applying the stated number pattern; check arithmetic separately.'),
 ('0006', [
  ('Which number is odd? A: 12; B: 15; C: 18; D: 20.', 'कौन-सी संख्या विषम है? A: 12; B: 15; C: 18; D: 20।', 'B'),
  ('Which number is odd? A: 24; B: 30; C: 37; D: 42.', 'कौन-सी संख्या विषम है? A: 24; B: 30; C: 37; D: 42।', 'C'),
  ('Which number is odd? A: 51; B: 62; C: 74; D: 86.', 'कौन-सी संख्या विषम है? A: 51; B: 62; C: 74; D: 86।', 'A')],
  'May confuse odd and even numbers or the units-digit parity rule.'),
 ('0007', [
  ('Which number is even? A: 13; B: 21; C: 28; D: 35.', 'कौन-सी संख्या सम है? A: 13; B: 21; C: 28; D: 35।', 'C'),
  ('Which number is even? A: 41; B: 56; C: 63; D: 79.', 'कौन-सी संख्या सम है? A: 41; B: 56; C: 63; D: 79।', 'B'),
  ('Which number is even? A: 91; B: 83; C: 75; D: 60.', 'कौन-सी संख्या सम है? A: 91; B: 83; C: 75; D: 60।', 'D')],
  'May confuse even and odd numbers or divisibility by two.'),
 ('0009', [
  ('A square has 4 rows with 4 dots in each row. How many dots are there?', 'एक वर्ग में 4 पंक्तियाँ हैं और हर पंक्ति में 4 बिंदु हैं। कुल कितने बिंदु हैं?', '16'),
  ('What is 7 squared (7 × 7)?', '7 का वर्ग (7 × 7) कितना है?', '49'),
  ('Which is a square number? A: 12; B: 18; C: 25; D: 30.', 'कौन-सी संख्या वर्ग संख्या है? A: 12; B: 18; C: 25; D: 30।', 'C')],
  'May confuse square numbers with doubling; multiplication or language may also explain an error.'),
 ('0018', [
  ('How many endpoints does a line segment have?', 'एक रेखाखंड के कितने अंत बिंदु होते हैं?', '2'),
  ('Which has a fixed length and two endpoints? A: line; B: ray; C: line segment; D: plane.', 'किसकी लंबाई निश्चित होती है और दो अंत बिंदु होते हैं? A: रेखा; B: किरण; C: रेखाखंड; D: समतल।', 'C'),
  ('A segment joins points A and B. How many endpoints are named?', 'एक रेखाखंड बिंदु A और B को जोड़ता है। कितने अंत बिंदुओं के नाम दिए गए हैं?', '2')],
  'May not distinguish a line segment from a line or ray.'),
 ('0020', [
  ('How many arms form an angle?', 'एक कोण की कितनी भुजाएँ होती हैं?', '2'),
  ('What is the common endpoint of the arms of an angle called? A: centre; B: vertex; C: length; D: plane.', 'कोण की भुजाओं के उभयनिष्ठ अंत बिंदु को क्या कहते हैं? A: केंद्र; B: शीर्ष; C: लंबाई; D: समतल।', 'B'),
  ('Which forms an angle? A: two rays with a common endpoint; B: one point; C: two separate points; D: one segment alone.', 'कौन कोण बनाता है? A: उभयनिष्ठ अंत बिंदु वाली दो किरणें; B: एक बिंदु; C: दो अलग बिंदु; D: केवल एक रेखाखंड।', 'A')],
  'May not identify angle arms and their common endpoint.'),
 ('0024', [
  ('How many degrees are in a right angle?', 'समकोण में कितने डिग्री होते हैं?', '90'),
  ('Which is a right angle? A: 45°; B: 60°; C: 90°; D: 120°.', 'कौन-सा कोण समकोण है? A: 45°; B: 60°; C: 90°; D: 120°।', 'C'),
  ('What is the angle in degrees at a corner of a square?', 'वर्ग के एक कोने का कोण कितने डिग्री का होता है?', '90')],
  'May not connect a right angle with 90 degrees; shape knowledge may also affect the square item.'),
 ('0025', [
  ('Which angle is acute? A: 35°; B: 90°; C: 120°; D: 180°.', 'कौन-सा कोण न्यून कोण है? A: 35°; B: 90°; C: 120°; D: 180°।', 'A'),
  ('Which angle is acute? A: 180°; B: 100°; C: 90°; D: 70°.', 'कौन-सा कोण न्यून कोण है? A: 180°; B: 100°; C: 90°; D: 70°।', 'D'),
  ('An acute angle is: A: exactly 90°; B: greater than 0° and less than 90°; C: exactly 180°; D: greater than 180°.', 'न्यून कोण होता है: A: ठीक 90°; B: 0° से अधिक और 90° से कम; C: ठीक 180°; D: 180° से अधिक।', 'B')],
  'May confuse acute, right, and obtuse angles or the strict 90-degree boundary.'),
 ('0038', [
  ('What is the place value of 4 in 3452?', '3452 में 4 का स्थानीय मान क्या है?', '400'),
  ('What is the place value of 7 in 5721?', '5721 में 7 का स्थानीय मान क्या है?', '700'),
  ('What is the place value of 6 in 268?', '268 में 6 का स्थानीय मान क्या है?', '60')],
  'May confuse face value and place value or misidentify the position of a digit.'),
 ('0039', [
  ('Find the sum of the digits of 352.', '352 के अंकों का योग ज्ञात कीजिए।', '10'),
  ('Find the sum of the digits of 409.', '409 के अंकों का योग ज्ञात कीजिए।', '13'),
  ('Find the sum of the digits of 1263.', '1263 के अंकों का योग ज्ञात कीजिए।', '12')],
  'May confuse a digit with its place value; an addition error may also explain the response.'),
]


def build():
    nodes, edges = load_graph()
    bank = []
    for suffix, items, difficulty in SPECS:
        concept = 'MATH6_C' + suffix
        for index, (en, hi, answer) in enumerate(items, 1):
            kind = 'mcq' if answer in ('A', 'B', 'C', 'D') else 'numeric'
            bank.append({'id': f'DQ_{suffix}_{index}', 'concept_id': concept,
                         'concept_en': nodes[concept]['en'], 'concept_hi': nodes[concept]['hi'],
                         'en': en, 'hi': hi, 'type': kind, 'answer': answer,
                         'scoring_rule': '1 for exact correct option letter (case insensitive); 0 for another A-D letter; other text is unscorable.' if kind == 'mcq' else '1 for numerically equal answer; 0 for another number; other text is unscorable. Devanagari digits accepted.',
                         'possible_difficulty': difficulty, 'version': 'diagnostic-v1',
                         'review_status': 'PENDING', 'reviewer': '', 'review_date': '',
                         'provenance': 'Original development item; not quoted from NCERT.',
                         'source_references': [references(e) for e in edges if e['target_id'] == concept],
                         'source_verification': 'Passage IDs inherited from provisional graph; textbook text unavailable.'})
    (Path(__file__).parent / 'question_bank.json').write_text(json.dumps(bank, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    build()
