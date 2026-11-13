"""Prepare draft review exports and frozen pilot fixtures (run before pilot only)."""
import csv
import json
from diagnostic import engine as e
from diagnostic.pilot import SUPPORT, DIFFICULTY, INSUFFICIENT, REPORTS


def prepare():
    REPORTS.mkdir(exist_ok=True)
    rows = [
        ('How can I recognise a right angle?', 'MATH6_C0024', SUPPORT, 'consistent', 'latin', {}),
        ('समकोण कितने डिग्री का होता है?', 'MATH6_C0024', SUPPORT, 'consistent', 'devanagari', {}),
        ('How do I recognise an acute angle?', 'MATH6_C0025', DIFFICULTY, 'consistent', 'latin', {}),
        ('न्यून कोण क्या होता है?', 'MATH6_C0025', DIFFICULTY, 'consistent', 'devanagari', {}),
        ('Help me with place value.', 'MATH6_C0038', SUPPORT, 'consistent', 'latin', {}),
        ('स्थानीय मान कैसे निकालते हैं?', 'MATH6_C0038', DIFFICULTY, 'consistent', 'devanagari', {}),
        ('How is a digit sum calculated?', 'MATH6_C0039', INSUFFICIENT, 'mixed', 'latin', {}),
        ('अंकों का योग कैसे निकालें?', 'MATH6_C0039', INSUFFICIENT, 'ambiguous', 'devanagari', {}),
        ('What makes a line segment different?', 'MATH6_C0018', SUPPORT, 'consistent', 'latin', {}),
        ('कोण की भुजाएँ क्या हैं?', 'MATH6_C0020', DIFFICULTY, 'consistent', 'devanagari', {}),
        ('How do I find a square number?', 'MATH6_C0009', SUPPORT, 'consistent', 'latin', {}),
        ('संख्या पैटर्न का अगला पद कैसे निकालें?', 'MATH6_C0003', DIFFICULTY, 'consistent', 'devanagari', {}),
        ('Is 18 an even number?', 'clarify', INSUFFICIENT, 'ambiguous', 'latin', {}),
        ('विषम संख्या कैसे पहचानें?', 'clarify', INSUFFICIENT, 'ambiguous', 'devanagari', {}),
        ('How do I add fractions?', 'clarify', INSUFFICIENT, 'ambiguous', 'latin', {}),
        ('भिन्नों का जोड़ कैसे करें?', 'clarify', INSUFFICIENT, 'ambiguous', 'devanagari', {}),
        ('Explain acute angle and place value together.', 'clarify', INSUFFICIENT, 'ambiguous', 'latin', {}),
        ('', 'clarify', INSUFFICIENT, 'ambiguous', 'latin', {}),
        ('वर्ग संख्या क्या है?', 'MATH6_C0009', INSUFFICIENT, 'mixed', 'devanagari', {}),
        ('Explain a number pattern.', 'MATH6_C0003', SUPPORT, 'consistent', 'latin', {'MATH6_C0038': DIFFICULTY}),
    ]
    cases = [dict(id=f'P{i:02}', input=text, expected_mapping=target, default_truth=truth,
                  response_mode=mode, digits=digits, concept_truth=overrides,
                  review_status='PENDING independent expected-diagnosis review',
                  oracle_origin='Author-specified synthetic learner profile; not inferred from algorithm output')
             for i, (text, target, truth, mode, digits, overrides) in enumerate(rows, 1)]
    (REPORTS / 'pilot_cases.json').write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding='utf-8')
    bank = e.load_bank()
    fields = ['id', 'concept_id', 'concept_en', 'concept_hi', 'en', 'hi', 'type', 'answer', 'scoring_rule', 'possible_difficulty', 'review_status', 'reviewer', 'review_date']
    with (REPORTS / 'question_bank.csv').open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(bank)
    with (REPORTS / 'review_checklist.csv').open('w', encoding='utf-8-sig', newline='') as f:
        fields = ['artifact_id', 'review_type', 'reviewer', 'date', 'decision', 'corrections']
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for q in bank:
            w.writerow(dict(artifact_id=q['id'], review_type='Final bilingual content/key/scoring/difficulty review', decision='PENDING'))
        w.writerow(dict(artifact_id=e.VERSION, review_type='Diagnostic decision and selection rules', decision='PENDING'))
        for c in cases:
            w.writerow(dict(artifact_id=c['id'], review_type='Independent expected mapping and diagnoses review', decision='PENDING'))


if __name__ == '__main__':
    prepare()
