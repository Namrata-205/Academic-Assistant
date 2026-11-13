"""Run frozen synthetic pilot fixtures. No real learner or independent-review claim."""
import csv
import hashlib
import json
from pathlib import Path
from diagnostic import engine as e

REPORTS = e.ROOT / 'reports'
CASES = REPORTS / 'pilot_cases.json'
SUPPORT = 'Evidence supports understanding'
DIFFICULTY = 'Possible prerequisite difficulty'
INSUFFICIENT = 'Insufficient evidence'


def run_case(case, method, bank, nodes, edges):
    # Preserve the original frozen pilot as a legacy-mapper benchmark.
    mapping = e.legacy_map_question(case['input'], nodes, edges)
    base = {'case_id': case['id'], 'method': method, 'input': case['input'],
            'review_status': case['review_status'], 'expected_mapping': case['expected_mapping'],
            'actual_mapping': mapping.get('concept_id', 'clarify'),
            'mapping_correct': mapping.get('concept_id', 'clarify') == case['expected_mapping']}
    current = []
    if mapping['status'] != 'mapped':
        return dict(base, questions_asked=0, correct_diagnoses=0, false_diagnoses=0,
                    unresolved_concepts=0, case_unresolved=True, observations='[]', statuses='{}')
    target = mapping['concept_id']
    for ordinal in range(3):
        question = e.select_question(target, bank, edges, current, method=method)
        if question is None:
            break
        truth = case['concept_truth'].get(question['concept_id'], case['default_truth'])
        response_mode = case['response_mode']
        if response_mode == 'ambiguous':
            response = 'not sure / शायद'
        else:
            correct = truth == SUPPORT
            if response_mode == 'mixed':
                correct = ordinal != 0
            if correct:
                response = question['answer']
                if case['digits'] == 'devanagari' and question['type'] == 'numeric':
                    response = response.translate(str.maketrans('0123456789', '०१२३४५६७८९'))
            else:
                response = next(c for c in 'ABCD' if c != question['answer']) if question['type'] == 'mcq' else str(int(question['answer']) + 1)
        current.append({'question_id': question['id'], 'concept_id': question['concept_id'],
                        'response': response, 'score': e.score(question, response)})
    report = e.make_report(target, bank, edges, current)
    correct = false = unresolved = 0
    statuses = {}
    # Opportunities are eligible bank-covered target/prerequisites, not all 53 concepts.
    for row in report['concepts']:
        c = row['concept_id']
        if c not in e.eligible(target, bank, edges):
            continue
        expected = case['concept_truth'].get(c, case['default_truth'])
        actual = row['status']
        statuses[c] = {'expected': expected, 'actual': actual, 'assessment': row['assessment']}
        if actual == INSUFFICIENT:
            unresolved += 1
        elif actual == expected:
            correct += 1
        else:
            false += 1
    return dict(base, questions_asked=len(current), correct_diagnoses=correct,
                false_diagnoses=false, unresolved_concepts=unresolved,
                case_unresolved=bool(unresolved or false),
                observations=json.dumps(current, ensure_ascii=False),
                statuses=json.dumps(statuses, ensure_ascii=False))


def run():
    cases = json.loads(CASES.read_text(encoding='utf-8'))
    nodes, edges = e.load_graph()
    bank = e.load_bank()
    results = [run_case(c, method, bank, nodes, edges) for c in cases for method in ('fixed', 'graph-guided')]
    with (REPORTS / 'pilot_results.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    totals = {}
    for method in ('fixed', 'graph-guided'):
        subset = [r for r in results if r['method'] == method]
        totals[method] = {key: sum(int(r[key]) for r in subset) for key in
                          ('mapping_correct', 'correct_diagnoses', 'false_diagnoses', 'unresolved_concepts', 'questions_asked', 'case_unresolved')}
    metadata = {'case_count': len(cases), 'case_sha256': hashlib.sha256(CASES.read_bytes()).hexdigest(),
                'bank_sha256': hashlib.sha256(e.BANK_PATH.read_bytes()).hexdigest(),
                'version': e.VERSION, 'results': totals, 'independent_review': 'PENDING',
                'study_type': 'Synthetic fixture execution, not an empirical learner study'}
    (REPORTS / 'pilot_summary.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    return metadata


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
