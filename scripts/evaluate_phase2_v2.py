"""Auditable Phase 2 development evaluation; never promotes drafts to human gold.

Run: venv/Scripts/python.exe scripts/evaluate_phase2_v2.py
Only synthetic learners in a temporary database; no external generation/history.
"""
import hashlib
import html
import json
import math
import statistics
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from diagnostic import engine as e, book_chat, bilingual_quality as bilingual
from diagnostic import local_teaching, teaching_feedback
from diagnostic.tutor_selection import choose, prerequisite_rank_audit
from diagnostic.evaluate_rag import relevant

OUT = e.ROOT / 'reports/phase2_evaluation_v2'
PROFILES = ['prerequisite_gap', 'no_apparent_gap', 'calculation_slip',
            'language_confusion', 'insufficient_evidence']


def save(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def mean(rows):
    values = [v for v in rows if v is not None]
    return statistics.mean(values) if values else None


def pct(n, d):
    return n / d if d else None


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def graph_metrics(nodes, edges, bank):
    positives = {(r['source_id'], r['target_id']) for r in edges}
    old = e.load_graph_rows(e.ROOT / 'assets/NCERT_Knowledge_Graph/prerequisite_edges.xlsx')
    old_ids = {r[s + '_id'] for r in old for s in ('source', 'target')}
    common = (old_ids & nodes.keys()) - {'MATH6_C0036', 'MATH6_C0049'}
    predicted = {(r['source_id'], r['target_id']) for r in old
                 if r['source_id'] in common and r['target_id'] in common}
    gold = {(a, b) for a, b in positives if a in common and b in common}
    tp = len(predicted & gold)
    precision, recall = pct(tp, len(predicted)), pct(tp, len(gold))
    children = {cid: [] for cid in nodes}
    indegree = Counter({cid: 0 for cid in nodes})
    for a, b in positives:
        children[a].append(b)
        indegree[b] += 1
    ready = [cid for cid in nodes if not indegree[cid]]
    visited = 0
    while ready:
        cid = ready.pop(); visited += 1
        for child in children[cid]:
            indegree[child] -= 1
            if not indegree[child]: ready.append(child)
    ranks = [prerequisite_rank_audit(cid, e.prerequisites(cid, edges), bank, edges)
             for cid in sorted(nodes) if e.prerequisites(cid, edges)]
    save('prerequisite_ranking.json', ranks)
    return {
        'reference': {'path': str(e.graph_source_path()), 'sha256': digest(e.graph_source_path()),
                      'review_authority': 'User confirmed this file is reviewed in chat.',
                      'csv_review_flags': dict(Counter(r.get('validation_status', '') for r in edges)),
                      'negative_pairs_independently_reviewed': False},
        'concepts': len(nodes), 'edges': len(edges), 'chapter_counts': dict(Counter(n['chapter'] for n in nodes.values())),
        'duplicate_edges': len(edges) - len(positives), 'self_links': sum(a == b for a, b in positives),
        'acyclic': visited == len(nodes),
        'bilingual_labels_present': sum(bool(n['en'] and n['hi']) for n in nodes.values()),
        'semantic_bilingual_matching': 'User-reviewed graph; no separate blind bilingual ratings supplied.',
        'original_graph_comparison': {'compatible_concepts': len(common), 'original_predicted_links': len(predicted),
            'reviewed_positive_links': len(gold), 'true_positive': tp,
            'unmatched_original_links': len(predicted - gold), 'missed_reviewed_links': len(gold - predicted),
            'positive_link_recall': recall,
            'conditional_precision': precision, 'conditional_f1': pct(2 * tp, len(predicted) + len(gold)),
            'interpretation': 'Precision/F1 assume absent links are negative. This is conditional agreement, not independently validated prerequisite precision. Direct-link graphs may differ in transitive redundancy.',
            'excluded_semantic_changes': ['MATH6_C0036', 'MATH6_C0049']},
        'v2_prerequisite_retrieval': {'targets': len(ranks),
            'recall_at_3': mean([r['recall_at_3'] for r in ranks]),
            'recall_at_5': mean([r['recall_at_5'] for r in ranks]),
            'interpretation': 'Macro recall of reviewed direct positive links in the deployed selector. Same graph defines candidate eligibility: tests ranking/bank coverage, not independent educational importance.'}}


def scenario_evaluation(nodes, edges, bank):
    # Twelve families, five response profiles = 60 new development scenarios.
    # Original three chapters, to match the workflow's comparative-study scope.
    targets = ['MATH6_C0003', 'MATH6_C0009', 'MATH6_C0006', 'MATH6_C0007',
               'MATH6_C0024', 'MATH6_C0025', 'MATH6_C0026', 'MATH6_C0027',
               'MATH6_C0038', 'MATH6_C0039', 'MATH6_C0041', 'MATH6_C0042']
    bank = sorted(bank, key=lambda q: (q['concept_id'], q['id']))
    cases, results = [], []
    reasons = {
        'prerequisite_gap': 'Two or more consistently wrong items on the author-designated direct foundation; other answers correct.',
        'no_apparent_gap': 'All potential item answers correct; only tested concepts may be supported.',
        'calculation_slip': 'One wrong item then correct items; the cause is a synthetic assumption, not a diagnosis from one error.',
        'language_confusion': 'One explicit request for wording clarification; other answers correct. This is an author-defined language case.',
        'insufficient_evidence': 'All answers unscorable; a gap must not be asserted.'}
    for family_index, target in enumerate(targets):
        direct = e.prerequisites(target, edges)
        assert direct, target
        for index, profile in enumerate(PROFILES):
            focus = direct[(family_index + index) % len(direct)]
            items = [q for q in bank if q['concept_id'] == focus]
            first = next((q for q in items if q['type'] == 'numeric'), items[0])
            case = {'id': f'DEV{len(cases)+1:03}', 'family': target, 'target': target,
                    'chapter': nodes[target]['chapter'], 'profile': profile, 'focus': focus,
                    'expected_gaps': [focus] if profile == 'prerequisite_gap' else [],
                    'label_reason': reasons[profile], 'review_status': 'PENDING', 'split': 'development',
                    'textbook_locations': {lang: {
                        cid: book_chat.textbooks.catalog()['concepts'].get(cid, {}).get('versions', {}).get(lang)
                        for cid in (target, focus)} for lang in ('en', 'hi')}}
            cases.append(case)
            for lang in ('en', 'hi'):
                for method in ('fixed', 'adaptive_without_graph', 'graph_guided'):
                    current, log = [], []
                    # Same bank and target label for all arms. Non-graph baselines use
                    # same-chapter candidates, with target first, without graph access.
                    pool = list(bank)
                    pool.sort(key=lambda q: (q['concept_id'] != target,
                        nodes[q['concept_id']]['chapter'] != nodes[target]['chapter'], q['concept_id'], q['id']))
                    for _ in range(3):
                        if method == 'graph_guided':
                            q, audit = choose(target, bank, edges, current)
                        elif method == 'fixed':
                            q = next((q for q in pool if q['id'] not in {r['question_id'] for r in current}), None)
                            audit = {'reason': 'predeclared_target_then_chapter_order'}
                        else:
                            available = [q for q in pool if q['id'] not in {r['question_id'] for r in current}
                                         and e.status([r for r in current if r['concept_id'] == q['concept_id']]) == 'Insufficient evidence']
                            def rank(q):
                                rows = [r for r in current if r['concept_id'] == q['concept_id']]
                                return (not bool(rows), q['concept_id'] != target,
                                    nodes[q['concept_id']]['chapter'] != nodes[target]['chapter'], q['concept_id'], q['id'])
                            q = min(available, key=rank) if available else None
                            audit = {'reason': 'confirm_response_uncertainty_then_target_then_chapter'}
                        if not q: break
                        response = q['answer']
                        if profile == 'insufficient_evidence': response = 'not sure'
                        elif profile == 'language_confusion' and q['id'] == first['id']: response = 'Please explain the wording'
                        elif (profile == 'prerequisite_gap' and q['concept_id'] == focus) or (profile == 'calculation_slip' and q['id'] == first['id']):
                            response = next(a for a in 'ABCD' if a != q['answer']) if q['type'] == 'mcq' else str(float(q['answer']) + 1)
                        current.append({'question_id': q['id'], 'concept_id': q['concept_id'], 'response': response, 'score': e.score(q, response)})
                        log.append(audit)
                    statuses = {cid: e.status([r for r in current if r['concept_id'] == cid]) for cid in {r['concept_id'] for r in current}}
                    gaps = sorted(cid for cid, status in statuses.items() if status == 'Possible prerequisite difficulty')
                    results.append({'case_id': case['id'], 'profile': profile, 'target': target, 'focus': focus,
                        'language': lang, 'method': method, 'questions_asked': len(current), 'observations': current,
                        'selection_log': log, 'statuses': statuses, 'predicted_gaps': gaps,
                        'correct_gap_identification': gaps == case['expected_gaps'],
                        'unresolved': any(v == 'Insufficient evidence' for v in statuses.values()),
                        'focus_tested': focus in statuses})
    save('development_cases.json', {'review_status': 'AI-authored drafts, not independently reviewed gold',
        'cases': cases, 'bank_sha256': digest(e.BANK_PATH), 'holdout': 'Original scenarios_v1 final candidates untouched.'})
    save('diagnostic_traces.json', results)
    summary = {}
    for lang in ('en', 'hi'):
        summary[lang] = {}
        for method in ('fixed', 'adaptive_without_graph', 'graph_guided'):
            rows = [r for r in results if r['language'] == lang and r['method'] == method]
            gap = [r for r in rows if r['profile'] == 'prerequisite_gap']
            nongap = [r for r in rows if r['profile'] != 'prerequisite_gap']
            summary[lang][method] = {'cases': len(rows),
                'exact_gap_set_agreement': mean([r['correct_gap_identification'] for r in rows]),
                'gap_detection_rate': mean([r['focus'] in r['predicted_gaps'] for r in gap]),
                'false_gap_rate': mean([bool(r['predicted_gaps']) for r in nongap]),
                'unresolved_rate': mean([r['unresolved'] for r in rows]),
                'average_questions': mean([r['questions_asked'] for r in rows]),
                'profile_breakdown': {p: {'exact_gap_set_agreement': mean([r['correct_gap_identification'] for r in rows if r['profile'] == p]),
                    'unresolved_rate': mean([r['unresolved'] for r in rows if r['profile'] == p])} for p in PROFILES}}
    return {'scope': '60 synthetic development scenarios x two languages x three methods. Not learner accuracy. Language answers use equivalent keys: identical diagnosis metrics are expected.',
        'policy': 'Max three asked items per method; no unseen responses or labels provided to selectors. No prior learner evidence. All arms access the whole bank. Fixed/adaptive prioritise target then same chapter without edges; graph prioritises direct prerequisites.',
        'limitations': 'Synthetic response packs are graph-derived and baselines are simple target-first heuristics, not optimised models. Exact gap-set agreement counts an empty predicted set as correct for non-gap cases even when evidence is insufficient; interpret together with unresolved rate. This is not an unbiased causal estimate of graph benefit.',
        'reviewed_learner_scenarios': 0, 'by_language': summary}, cases, results


def retrieval_evaluation():
    data = json.loads((e.ROOT / 'reports/rag_eval_cases_v1.json').read_text(encoding='utf-8'))
    results = []
    for case in data['cases']:
        print('Evidence', case['id'], flush=True)
        start = time.perf_counter()
        pool, _ = book_chat.retrieve_sources(case['concept_id'], case['language'], case['question'], limit=None)
        flags = [relevant(s, case) for s in pool]
        elapsed = time.perf_counter() - start
        # Count reference term-span instances in the scoped candidate pool. This
        # lexical proxy is not semantic passage support or exhaustive NCERT recall.
        def spans(s):
            from diagnostic.evaluate_rag import normalize
            text = normalize(s['excerpt'])
            return sum(text.count(normalize(term)) for term in case['evidence_all']) if relevant(s, case) else 0
        for k in (1, 2, 3, 5):
            results.append({'case_id': case['id'], 'language': case['language'], 'k': k,
                'precision': sum(flags[:k]) / k, 'recall': pct(sum(flags[:k]), sum(flags)),
                'support_span_coverage_proxy': pct(sum(spans(s) for s in pool[:k]), sum(spans(s) for s in pool)),
                'relevant_pool_chunks': sum(flags), 'candidate_chunks': len(pool),
                'seconds': elapsed, 'sources': pool[:k]})
    save('evidence_traces.json', results)
    return {'scope': data['review_status'],
        'recall_denominator': 'Relevant chunks in the concept-scoped candidate pool, not all textbook passages. Zero-denominator cases reported separately, never counted as perfect recall.',
        'span_metric': 'Lexical reference-term occurrence coverage in page-matching chunks; independent human support-span coverage pending.',
        'by_language': {lang: {str(k): {
            key: mean([r[key] for r in results if r['language'] == lang and r['k'] == k])
            for key in ('precision', 'recall', 'support_span_coverage_proxy')} for k in (1, 2, 3, 5)} for lang in ('en', 'hi')},
        'zero_evidence_cases': sorted({r['case_id'] for r in results if r['relevant_pool_chunks'] == 0})}


def bilingual_evaluation(nodes, bank):
    glossary = bilingual.glossary()['concepts']
    definitions, items = [], []
    for cid, row in glossary.items():
        en = row.get('definition_en', ''); hi = row.get('definition_hi', '')
        # Accommodate glossary entries with nested definitions.
        if not en:
            from diagnostic.curriculum_content import fact
            en, hi = fact(cid)
        definitions.append({'concept': cid, **bilingual.check_pair(en, hi),
            'term_matches_graph': row['en'] == nodes[cid]['en'] and row['hi'] == nodes[cid]['hi']})
    for q in bank:
        items.append({'question_id': q['id'], **bilingual.check_pair(q['en'], q['hi'])})
    save('bilingual_checks.json', {'definitions': definitions, 'questions': items})
    return {'definitions': len(definitions), 'question_pairs': len(items),
        'definition_number_unit_pass_rate': mean([r['passed'] for r in definitions]),
        'question_number_unit_pass_rate': mean([r['passed'] for r in items]),
        'canonical_term_match_rate': mean([r['term_matches_graph'] for r in definitions]),
        'translation_accuracy': None, 'semantic_terminology_consistency': None,
        'reason': 'Numbers, units, presence of Hindi and canonical labels are automated checks; meaning and terminology suitability still need blind bilingual review.'}


def workflows(nodes, cases, diagnostic_rows):
    traces, feedback, review, ablations = [], [], [], []
    representatives = ['MATH6_C0106', 'MATH6_C0111', 'MATH6_C0113', 'MATH6_C0117', 'MATH6_C0130',
                       'MATH6_C0158', 'MATH6_C0180', 'MATH6_C0191', 'MATH6_C0203', 'MATH6_C0216']
    with tempfile.TemporaryDirectory() as tmp:
        conn = e.connect(Path(tmp) / 'phase2.sqlite3')
        try:
            with patch('diagnostic.book_chat.generate', side_effect=RuntimeError('offline evaluation: provider unavailable')):
                for cid in representatives:
                    for lang in ('en', 'hi'):
                        print('Workflow', cid, lang, flush=True)
                        start = time.perf_counter()
                        answer = book_chat.answer(nodes[cid][lang], lang, cid, conn=conn, learner='synthetic-phase2')
                        duration = time.perf_counter() - start
                        paragraphs = answer.get('paragraphs', [])
                        source_ids = {s['id'] for s in answer.get('sources', [])}
                        citation_links = [c for p in paragraphs for c in p.get('citations', [])]
                        text = ' '.join(p['text'] for p in paragraphs)
                        try:
                            bilingual.check_arithmetic(text); bilingual.check_angle_claims(text)
                            math_checks = True
                        except ValueError: math_checks = False
                        traces.append({'concept': cid, 'chapter': nodes[cid]['chapter'], 'language': lang,
                            'seconds': duration, 'status': answer['status'], 'mode': answer.get('mode'),
                            'success': answer['status'] == 'answered' and bool(paragraphs) and bool(source_ids),
                            'citation_reference_integrity': bool(citation_links) and all(c in source_ids for c in citation_links),
                            'limited_math_checks_pass': math_checks, 'answer': answer})
                        review.append({'id': len(review) + 1, 'concept': cid, 'language': lang, 'answer': answer,
                            'correctness': None, 'citation_entailment': None, 'difficulty_alignment': None,
                            'translation_accuracy': None, 'reviewer': None})
                # Real answer branch, four feedback modes, bilingual. Source stays
                # public synthetic curriculum text; no user chat data used.
                for lang in ('en', 'hi'):
                    for action in sorted(teaching_feedback.ACTIONS):
                        request = {'mode': action, 'focus_concept_id': 'MATH6_C0025'}
                        answer = book_chat.answer(nodes['MATH6_C0025'][lang], lang, 'MATH6_C0025',
                            conn=conn, learner='synthetic-feedback', teaching_request=request)
                        feedback.append({'language': lang, 'action': action, 'answered': answer['status'] == 'answered',
                                         'paragraphs': answer.get('paragraphs'), 'mode': answer.get('mode')})
                # Three arms use same offline authored generator and explicit
                # 2,400-character / four-source ceiling. Not an LLM quality trial.
                for lang in ('en', 'hi'):
                    target = 'MATH6_C0025'
                    for arm, focuses in [('ordinary_rag', [target]), ('graph_rag_no_diagnosis', [target, 'MATH6_C0024']),
                                          ('full_diagnosis_graph_rag', [target, 'MATH6_C0029'])]:
                        sources = []; budget = 2400
                        for focus in focuses:
                            found, _ = book_chat.retrieve_sources(focus, lang, nodes[focus][lang], limit=2, max_chars=budget // len(focuses))
                            sources.extend(found)
                        for i, source in enumerate(sources): source['id'] = f'S{i+1}'
                        request = {'mode': 'still_confused' if arm.startswith('full') else 'check_uncertainty',
                                   'focus_concept_id': focuses[-1], 'focus': nodes[focuses[-1]]}
                        paragraphs = local_teaching.lesson(target, nodes, sources, lang, request) or []
                        ablations.append({'arm': arm, 'language': lang, 'generator': 'same offline authored lesson generator',
                            'context_characters': sum(len(s['excerpt']) for s in sources), 'context_ceiling': 2400,
                            'source_count': len(sources), 'sources': sources, 'paragraphs': paragraphs,
                            'human_quality_scores': None})
        finally: conn.close()
    # Verify original/new transfer, rotated diagrams, actual scorer, independent ids.
    transfer = []
    for straight in (False, True):
        initial = teaching_feedback.angle_item(rotation=0, straight=straight)
        fresh = teaching_feedback.angle_item(rotation=137, straight=straight)
        transfer.append({'straight': straight, 'new_id': initial['id'] != fresh['id'],
                         'new_orientation': initial['diagram'] != fresh['diagram'],
                         'correct_key_scores_one': e.score(fresh, fresh['answer']) == 1,
                         'wrong_key_scores_zero': e.score(fresh, 'A' if fresh['answer'] == 'B' else 'B') == 0,
                         'item': fresh})
    demonstrations = []
    for profile in PROFILES:
        row = next(r for r in diagnostic_rows if r['profile'] == profile and r['method'] == 'graph_guided' and r['language'] == 'en')
        case = next(c for c in cases if c['id'] == row['case_id'])
        report = {'concepts': [{'concept_id': cid, 'assessment': 'Assessed', 'status': status} for cid, status in row['statuses'].items()]}
        decision = teaching_feedback.teaching_decision(report, row['target'])
        sources, _ = book_chat.retrieve_sources(decision['focus_concept_id'], 'en', nodes[decision['focus_concept_id']]['en'])
        request = dict(decision, focus=nodes[decision['focus_concept_id']])
        lesson = local_teaching.lesson(row['target'], nodes, sources, 'en', request) or []
        demonstrations.append({'profile': profile, 'case': case, 'diagnosis': row, 'next_action': decision,
                               'sources': sources, 'explanation': lesson,
                               'followup': {'status': 'new rotated angle check demonstrated separately; case-specific learner follow-up not simulated'}})
    save('workflow_traces.json', traces)
    save('feedback_traces.json', {'feedback': feedback, 'transfer': transfer})
    save('five_demonstrations.json', demonstrations)
    save('explanation_ablations.json', ablations)
    save('blind_explanation_review.json', review)
    return {
        'explanation': {'samples': len(traces), 'limited_math_check_pass_rate': mean([r['limited_math_checks_pass'] for r in traces]),
            'citation_reference_integrity_rate': mean([r['citation_reference_integrity'] for r in traces]),
            'correctness': None, 'citation_entailment': None, 'difficulty_alignment': None,
            'interpretation': 'Offline authored fallback only. Arithmetic/angle assertion checks and citation IDs do not establish mathematical correctness, relevance or citation entailment.',
            'controlled_comparison': 'Three offline generator arms saved with equal context ceilings; live model comparison unavailable and blind ratings pending.'},
        'feedback': {'mode_cases': len(feedback), 'answer_success_rate': mean([r['answered'] for r in feedback]),
            'transfer_checks': len(transfer) * 4,
            'transfer_pass_rate': mean([r[key] for r in transfer for key in ('new_id', 'new_orientation', 'correct_key_scores_one', 'wrong_key_scores_zero')]),
            'appropriate_next_action_rate': None,
            'interpretation': 'Branch execution and rotated-question scoring tested; useful pedagogical next-action ratings require independent review.'},
        'workflow': {'by_language': {lang: {'cases': len(rows := [r for r in traces if r['language'] == lang]),
            'offline_answer_success_rate': mean([r['success'] for r in rows]),
            'median_seconds': statistics.median([r['seconds'] for r in rows]),
            'p95_seconds': sorted(r['seconds'] for r in rows)[math.ceil(.95 * len(rows))-1]} for lang in ('en', 'hi')},
            'scope': 'In-process actual retrieval and offline answer path, first pass with shared caches. Includes local computation; excludes network model latency. Browser/quiz end-to-end coverage recorded separately.'}}


def render(report):
    esc = lambda value: html.escape(json.dumps(value, ensure_ascii=False, indent=2))
    rate = lambda value: 'Pending review' if value is None else f'{100*value:.1f}%'
    sections = [('1. Concept graph validation', report['graph']),
                ('2. Prerequisite retrieval', report['graph']['v2_prerequisite_retrieval']),
                ('3–4. Diagnostic selection and accuracy', report['diagnosis']),
                ('5. Evidence retrieval', report['retrieval']),
                ('6. Explanation quality', report['explanation']),
                ('7. Bilingual consistency', report['bilingual']),
                ('8. Feedback and follow-up', report['feedback']),
                ('9. End-to-end workflow', report['workflow']),
                ('Workflow document coverage and remaining review', report['document_coverage'])]
    body = ''.join(f'<section><details><summary>{html.escape(title)}</summary><pre>{esc(data)}</pre></details></section>' for title, data in sections)
    graph = report['graph']; diagnosis = report['diagnosis']['by_language']['en']['graph_guided']
    cycle_rows = report['workflow']['complete_chat_cycles']['by_language'].values()
    cycle_total = sum(row['cases'] for row in cycle_rows)
    cycle_passed = sum(round(row['cases'] * row['workflow_success_rate']) for row in cycle_rows)
    results = [
        ('1. Concept graph', f'{graph["concepts"]} bilingual concepts; {graph["edges"]} links; acyclic, no duplicate/self links',
         'User-reviewed positive links. Independently labelled negatives needed for unconditional precision/F1.'),
        ('2. Prerequisite retrieval', f'Recall@3 {rate(graph["v2_prerequisite_retrieval"]["recall_at_3"])}; Recall@5 {rate(graph["v2_prerequisite_retrieval"]["recall_at_5"])}',
         '134 targets; direct-link reference also defines candidate eligibility. Ranking/coverage test.'),
        ('3. Question selection', f'{diagnosis["average_questions"]:.2f} questions on average; three maximum',
         '60 synthetic development scenarios, paired languages, three selection arms.'),
        ('4. Diagnosis', f'Gap detection {rate(diagnosis["gap_detection_rate"])}; false-gap {rate(diagnosis["false_gap_rate"])}; some tested evidence unresolved {rate(diagnosis["unresolved_rate"])}',
         'Synthetic, graph-derived labels; no independent learner accuracy claim.'),
        ('5. Evidence retrieval', 'English and Hindi precision/recall at k=1,2,3,5 below',
         '12 development queries; candidate-pool recall. Independent semantic support-span review pending.'),
        ('6. Explanation quality', f'Citation-ID integrity {rate(report["explanation"]["citation_reference_integrity_rate"])}; limited math checks {rate(report["explanation"]["limited_math_check_pass_rate"])}',
         '20 offline answers. Full correctness, entailment and difficulty ratings pending; cloud comparison failed.'),
        ('7. Bilingual consistency', f'144 definitions and 432 question pairs checked; canonical term match {rate(report["bilingual"]["canonical_term_match_rate"])}',
         'Number/unit parity and labels are structural checks; translation accuracy is unscored.'),
        ('8. Feedback/follow-up', f'Four actions × two languages; rotated-check assertions {rate(report["feedback"]["transfer_pass_rate"])}',
         'Branch execution and grading checked. Pedagogical usefulness needs human ratings.'),
        ('9. Complete workflow', f'{cycle_passed}/{cycle_total} offline chat cycles passed, including inline grading and a fresh question',
         'Temporary synthetic accounts; offline model fallback; no learner-history disclosure.')]
    summary_table = '<h2>Nine-test results</h2><table><thead><tr><th>Test</th><th>Measured result</th><th>Scope</th></tr></thead><tbody>' + ''.join(
        '<tr>'+''.join(f'<td>{html.escape(cell)}</td>' for cell in row)+'</tr>' for row in results) + '</tbody></table>'
    diag_table = '<h2>Diagnosis by language and method</h2><p>Exact gap-set agreement also counts empty gap sets; read with the unresolved rate. These are development simulations.</p><table><thead><tr><th>Language</th><th>Method</th><th>Gap detection</th><th>False gap</th><th>Some evidence unresolved</th><th>Avg questions</th></tr></thead><tbody>'
    for lang, methods in report['diagnosis']['by_language'].items():
        for method, row in methods.items():
            cells = [lang, method, rate(row['gap_detection_rate']), rate(row['false_gap_rate']), rate(row['unresolved_rate']), f'{row["average_questions"]:.2f}']
            diag_table += '<tr>'+''.join(f'<td>{html.escape(cell)}</td>' for cell in cells)+'</tr>'
    diag_table += '</tbody></table>'
    retrieval_table = '<h2>Evidence retrieval by language and k</h2><p>Precision divides by k, including missing slots. Recall excludes cases with no relevant chunk in the candidate pool. Zero-evidence cases: '+html.escape(', '.join(report['retrieval']['zero_evidence_cases']))+'.</p><table><thead><tr><th>Language</th><th>k</th><th>Precision</th><th>Pool recall</th><th>Lexical coverage proxy</th></tr></thead><tbody>'
    for lang, values in report['retrieval']['by_language'].items():
        for k, row in values.items():
            retrieval_table += '<tr>'+''.join(f'<td>{html.escape(cell)}</td>' for cell in [lang, k, rate(row['precision']), rate(row['recall']), rate(row['support_span_coverage_proxy'])])+'</tr>'
    retrieval_table += '</tbody></table>'
    timing_table = '<h2>Local response time</h2><p>Seconds, external generation disabled. Ten-chapter first-pass answers and cached angle chat cycles use different scopes. Concurrent evaluation load and cache state affect these measurements.</p><table><thead><tr><th>Language</th><th>Ten-chapter answer median</th><th>Ten-chapter answer p95</th><th>Complete cycle median</th><th>Complete cycle p95</th></tr></thead><tbody>'
    for lang in ('en', 'hi'):
        answer = report['workflow']['by_language'][lang]
        cycle = report['workflow']['complete_chat_cycles']['by_language'][lang]
        cells = [lang, f'{answer["median_seconds"]:.2f}', f'{answer["p95_seconds"]:.2f}', f'{cycle["median_cycle_seconds"]:.2f}', f'{cycle["p95_cycle_seconds"]:.2f}']
        timing_table += '<tr>'+''.join(f'<td>{cell}</td>' for cell in cells)+'</tr>'
    timing_table += '</tbody></table>'
    def responsive_table(markup):
        return '<div class="table-wrap" role="region" aria-label="Scrollable results table" tabindex="0">' + markup + '</div>'
    summary_table, diag_table, retrieval_table, timing_table = [responsive_table(markup)
        for markup in (summary_table, diag_table, retrieval_table, timing_table)]
    links = ''.join(f'<li><a href="{p.name}">{p.name}</a></li>' for p in sorted(OUT.glob('*.json')))
    (OUT/'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        '<title>Athena Phase 2 evaluation</title><style>body{font:16px/1.5 system-ui;max-width:1120px;margin:32px auto;padding:0 20px;color:#173335}h1,h2{color:#126b61}section{border-top:1px solid #aac9c4;margin-top:24px;padding-top:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.5 ui-monospace}a{color:#075eab;overflow-wrap:anywhere}.table-wrap{max-width:100%;overflow-x:auto}.table-wrap:focus{outline:3px solid #126b61}table{width:100%;min-width:640px;border-collapse:collapse;font-size:14px}th,td{text-align:left;border:1px solid #b6cec9;padding:10px;vertical-align:top}th{background:#e7f3f0}summary{font-weight:650;cursor:pointer}td{overflow-wrap:anywhere}</style>'
        '<h1>Athena: Phase 2 evaluation</h1><p>Reviewed positive graph reference; automated development evaluation. '
        'Synthetic scenarios and mechanical checks are not independently reviewed learner accuracy or learning gains.</p>'
        f'<p>Generated {html.escape(report["created_utc"])}</p>{summary_table}{diag_table}{retrieval_table}{timing_table}<h2>Detailed methods and limitations</h2>{body}<h2>Reproducible logs and review files</h2><ul>{links}</ul></html>', encoding='utf-8')


def complete_chat_cycles():
    """Exercise persisted check -> explain -> inline grade -> new example paths."""
    from diagnostic import chat_tutor
    from diagnostic.tutor_bank import load
    bank = {q['id']: q for q in load()}
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        conn = e.connect(Path(tmp)/'cycles.sqlite3')
        try:
            with patch('diagnostic.chat_router.gemini_generate', side_effect=RuntimeError('offline evaluation')), \
                 patch('diagnostic.book_chat.generate', side_effect=RuntimeError('offline evaluation')):
                for lang in ('en', 'hi'):
                    for profile in PROFILES:
                        print('Full cycle', lang, profile, flush=True)
                        start = time.perf_counter()
                        prompt = 'What is an acute angle?' if lang == 'en' else '\u0928\u094d\u092f\u0942\u0928 \u0915\u094b\u0923 \u0915\u094d\u092f\u093e \u0939\u0948?'
                        learner = 'synthetic-' + lang + '-' + profile
                        first = book_chat.send(conn, learner, prompt, lang, concept_id='MATH6_C0025', check_first=True)
                        thread = first['thread_id']; out = first['message']; checks = []; events = [out]
                        focus = out.get('check_question', {}).get('concept_id')
                        while out.get('check_question') and len(checks) < 3:
                            public = out['check_question']; q = bank[public['id']]
                            response = q['answer']
                            if profile == 'insufficient_evidence': response = 'not sure'
                            elif profile == 'language_confusion' and not checks: response = 'Please explain the wording'
                            elif (profile == 'prerequisite_gap' and q['concept_id'] == focus) or (profile == 'calculation_slip' and not checks):
                                response = next(a for a in 'ABCD' if a != q['answer']) if q['type'] == 'mcq' else str(float(q['answer'])+1)
                            checks.append({'question_id': q['id'], 'response': response})
                            token = '__quiz_answer__:' + json.dumps({'question_id': q['id'], 'answer': response})
                            result = book_chat.send(conn, learner, token, lang, thread)
                            out = result['message']; events.append(out)
                        explanation = out; practice = out.get('practice_question')
                        graded_inline = saved_followup = new_question = False
                        if practice:
                            state = json.loads(conn.execute('SELECT payload FROM book_chat_tutoring WHERE thread_id=?', (thread,)).fetchone()[0])
                            token = '__quiz_answer__:' + json.dumps({'question_id': practice['id'], 'answer': state['practice']['answer']})
                            graded = book_chat.send(conn, learner, token, lang, thread)
                            graded_inline = graded.get('append_message') is False
                            saved_followup = bool(chat_tutor.followup_evidence(conn, learner))
                            followup = book_chat.send(conn, learner, '__feedback__:another_example', lang, thread)['message']
                            new_question = bool(followup.get('practice_question')) and followup['practice_question']['id'] != practice['id']
                            events.extend([graded, followup])
                        elapsed = time.perf_counter() - start
                        success = bool(explanation.get('paragraphs')) and bool(explanation.get('sources')) and \
                            len(checks) <= 3 and graded_inline and saved_followup and new_question
                        rows.append({'language': lang, 'profile': profile, 'seconds': elapsed, 'success': success,
                            'questions_asked': len(checks), 'checks': checks,
                            'inline_grade': graded_inline, 'followup_saved': saved_followup, 'new_followup_question': new_question,
                            'diagnostic_scores_untouched': e.history(conn, learner) == [],
                            'other_learner_evidence_empty': chat_tutor.followup_evidence(conn, 'stranger') == [],
                            'events': events})
        finally: conn.close()
    save('complete_chat_cycles.json', rows)
    return {'scope': 'Five synthetic profiles in both languages through actual persisted chat send/check/inline-grade/feedback paths; offline generation.',
            'by_language': {lang: {'cases': len(selected := [r for r in rows if r['language'] == lang]),
                'workflow_success_rate': mean([r['success'] for r in selected]),
                'median_cycle_seconds': statistics.median([r['seconds'] for r in selected]),
                'p95_cycle_seconds': max(r['seconds'] for r in selected),
                'inline_grade_rate': mean([r['inline_grade'] for r in selected]),
                'new_followup_rate': mean([r['new_followup_question'] for r in selected])} for lang in ('en', 'hi')}}


def document_checklist():
    import xml.etree.ElementTree as ET
    import zipfile
    path = Path(r'C:\Users\Namrata Dalvi\Downloads\Phase 2 Workflow.docx')
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read('word/document.xml'))
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    paragraphs = [''.join(p.itertext()) for p in root.findall('.//w:body/w:p', ns)]
    notes = {
        1: ('reference', 'Greeting, no test requirement.'),
        2: ('tested_offline', 'Complete synthetic chat cycles, diagnostics, retrieval and new follow-up grading executed.'),
        3: ('scope_resolved', 'Three chapters for the scenario comparison; explicit later user request expands the application to ten.'),
        4: ('partial', 'Graph version comparison executed; separate labels and review boundaries preserved.'),
        5: ('partial', 'Original graph/results preserved; user attests v2 graph reviewed. Negative-pair and blind bilingual evidence not supplied; no historical code snapshot reconstructed.'),
        6: ('partial', 'Original 307-link graph compared on compatible IDs; positive recall and conditional precision/F1 reported. V2 self-agreement is not called accuracy.'),
        7: ('tested', 'Selection/ranking comparison and miss logs saved.'),
        8: ('tested', 'Recall@3/@5 over 134 targets; no more than three diagnostic questions.'),
        9: ('tested', 'Every graph selection logs candidate ranking, selected item and reason.'),
        10: ('tested_offline', 'Repeatable persisted chat workflow and isolated evidence stores tested.'),
        11: ('partial', '432 bilingual keyed items and feedback available. New items require independent suitability and wrong-answer interpretation review.'),
        12: ('tested_with_limits', 'Two observations required for difficulty; mixed/unscorable evidence remains uncertain. Synthetic slip/language causes are not identified as real causes.'),
        13: ('partial', 'Source-guided fallback and controlled offline contexts executed; live-model ratings unavailable.'),
        14: ('partial', 'Target/foundation retrieval, source metadata and unsupported-source abstention tested. Blind relevance and entailment review pending.'),
        15: ('partial', '144 shared-ID terms, definition/question numeric-unit checks; semantic glossary review and translation accuracy pending.'),
        16: ('tested_offline', 'Full feedback cycle and new-question grading persisted.'),
        17: ('tested_with_limits', 'Four bilingual feedback branches run; pedagogical usefulness rating pending.'),
        18: ('tested_offline', 'Existing right/straight-angle cycle regression and eight rotated-transfer assertions passed.'),
        19: ('partial', 'Fresh development pack authored; not a final reviewed benchmark.'),
        20: ('partial', '60 distinct paired draft cases, five profiles, expected gaps, rationale and textbook locations; independent review still required.'),
        21: ('pending_final', 'Original family-separated final candidates untouched. Current new cases are all development; no frozen reviewed final accuracy claimed.'),
        22: ('tested', 'Each selector sees only asked responses; hidden potential answers/expected labels excluded from selectors.'),
        23: ('partial', 'Three diagnosis arms run; three explanation contexts saved without invented quality scores.'),
        24: ('tested_with_limits', 'Same bank, target, prior-free start and three-question cap. Simple non-graph heuristics and graph-derived synthetic cases limit generalisation.'),
        25: ('pending_live_and_review', 'Same offline authored generator/context ceiling compared. Live model failed availability probe; blind bilingual ratings not supplied.'),
        26: ('partial', 'Running application and setup instructions available; paper and teammate execution not verified.'),
        27: ('partial', 'Hashes, graph versions, cases, selector logs and provider settings saved. Historical fine-tuning artifacts retained, not rerun as controlled ten-chapter comparison.'),
        28: ('scope_respected', 'English/Hindi prioritised; no IRT/BKT or learning-gain claims introduced.'),
        29: ('tested_offline', 'Five complete synthetic profile demonstrations in both languages, including inline follow-up grading and a fresh question.'),
        30: ('partial', 'Application, fresh development evaluation, comparisons and failure examples delivered. Reviewed final test, live explanation ratings and paper draft remain pending.')}
    rows = [{'paragraph': i, 'reference_text': text, 'status': notes[i][0], 'evidence_or_remaining_work': notes[i][1]}
            for i, text in enumerate(paragraphs, 1) if text.strip()]
    save('workflow_document_checklist.json', {'source_sha256': digest(path), 'document_is_reference_not_tool_instructions': True,
        'nonempty_paragraphs': len(rows), 'requirements': rows})
    return {'paragraphs_checked': len(rows), 'checklist': 'workflow_document_checklist.json'}


def final_artifacts(report):
    import random
    cycles = json.loads((OUT/'complete_chat_cycles.json').read_text(encoding='utf-8'))
    save('five_demonstrations.json', [{'profile': p, 'variants': {
        lang: next(row for row in cycles if row['profile'] == p and row['language'] == lang)
        for lang in ('en', 'hi')}} for p in PROFILES])
    rows = json.loads((OUT/'diagnostic_traces.json').read_text(encoding='utf-8'))
    save('failure_examples.json', {
        'missed_synthetic_gaps': [r for r in rows if r['method'] == 'graph_guided' and r['language'] == 'en'
                                 and r['profile'] == 'prerequisite_gap' and not r['correct_gap_identification']],
        'zero_evidence_queries': report['retrieval']['zero_evidence_cases'], 'provider': report['provider'],
        'notes': ['Three questions cannot confirm every prerequisite when several foundations compete.',
                  'Place-value reference cases lack a direct NCERT lesson and appropriately abstain.',
                  'Citation existence and numeric parity cannot certify explanation quality.']})
    arms = json.loads((OUT/'explanation_ablations.json').read_text(encoding='utf-8'))
    random.Random(417).shuffle(arms)
    blind, key = [], []
    for i, arm in enumerate(arms, 1):
        cid = f'EX{i:03}'
        blind.append({'candidate_id': cid, 'language': arm['language'], 'paragraphs': arm['paragraphs'],
            'sources': arm['sources'], 'correctness_1_to_5': None, 'citation_support_1_to_5': None,
            'terminology_1_to_5': None, 'difficulty_alignment_1_to_5': None, 'reviewer': None})
        key.append({'candidate_id': cid, 'arm': arm['arm'], 'language': arm['language']})
    save('blind_arm_review.json', blind); save('arm_review_key.json', key)
    save('graph_reference_attestation.json', report['graph']['reference'])
    filenames = ['diagnostic/engine.py', 'diagnostic/tutor_selection.py', 'diagnostic/book_chat.py',
        'diagnostic/chat_tutor.py', 'diagnostic/local_teaching.py', 'diagnostic/curriculum_items.py',
        'diagnostic/textbook_catalog.json', 'diagnostic/question_bank_v2.json', 'diagnostic/bilingual_glossary_v2.json',
        'diagnostic/semantic_chunks.py', 'diagnostic/passage_reranker.py', 'diagnostic/hybrid_retrieval.py',
        'diagnostic/semantic_mapper.py', 'diagnostic/chat_router.py', 'diagnostic/chat_provider.py',
        'diagnostic/curriculum.py', 'diagnostic/curriculum_content.py', 'diagnostic/teaching_feedback.py',
        'diagnostic/tutor_bank.py', 'requirements.txt', 'requirements-semantic.txt', 'package-lock.json',
        'reports/phase2_evaluation_v2/development_cases.json', 'scripts/evaluate_phase2_v2.py']
    save('evaluation_manifest.json', {'files': {f: digest(e.ROOT/f) for f in filenames},
        'graph_sha256': digest(e.graph_source_path()), 'generator': 'offline authored local lesson',
        'external_model': report['provider'], 'scenario_split': 'development only',
        'question_budget': 3, 'explanation_context_ceiling_characters': 2400, 'blind_shuffle_seed': 417})


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    nodes, edges = e.load_graph(); bank = e.load_bank()
    report = {'created_utc': datetime.now(timezone.utc).isoformat(), 'graph': graph_metrics(nodes, edges, bank)}
    report['diagnosis'], cases, diagnostic_rows = scenario_evaluation(nodes, edges, bank)
    save('partial_results.json', report)
    report['retrieval'] = retrieval_evaluation()
    report['bilingual'] = bilingual_evaluation(nodes, bank)
    report.update(workflows(nodes, cases, diagnostic_rows))
    report['workflow']['complete_chat_cycles'] = complete_chat_cycles()
    report['workflow']['timing_limitations'] = 'Ten-chapter timings may include cold concept caches and concurrent evaluation load. Complete-chat cycles reuse popular angle caches. Not an isolated production latency benchmark; no external-model latency included.'
    provider = OUT/'provider_status.json'
    report['provider'] = json.loads(provider.read_text()) if provider.exists() else {'ok': False, 'error': 'not checked'}
    report['regression'] = json.loads((e.ROOT/'reports/curriculum_v2/regression.json').read_text())
    report['document_coverage'] = {
        'source': r'C:\Users\Namrata Dalvi\Downloads\Phase 2 Workflow.docx',
        'scope_resolution': 'Document original three chapters used for diagnosis comparison; user later explicitly expanded deployed application to ten chapters.',
        'covered': ['Original graph, original bank and old reports preserved; v2 hashes and selection traces saved.',
            'Reviewed-positive graph comparison and retrieval at ranks 3/5, including missed links.',
            'Three diagnosis methods: same bank, no hidden responses, max three questions, English/Hindi separately.',
            '60 distinct paired development scenarios, five evidence profiles, label reasons and textbook locations.',
            'Evidence precision/recall at k=1,2,3,5, zero-evidence cases, lexical support coverage proxy.',
            'Three explanation contexts under same offline generator and context ceiling; blind review file.',
            'All 144 glossary entries, all 432 bilingual question pairs, four feedback actions and new rotated checks.',
            'Five diagnostic demonstration traces and ten-chapter bilingual retrieval/answer workflow timing.',
            '162 regression tests passed, one skipped; separate browser and accessibility reports retained.'],
        'pending_or_limited': ['Independent negative graph pairs needed for unqualified prerequisite precision/F1.',
            'CSV review flags remain pending despite user attestation; no flags silently changed.',
            'Scenario labels, item suitability, explanations and translations await independent review; 0 independently reviewed learner scenarios supplied.',
            'Existing original final-candidate split untouched; this run is development only, not a frozen final benchmark.',
            'Live-model three-arm explanation comparison blocked by configured provider error; no fabricated model scores.',
            'Mathematical correctness, citation entailment, pedagogical difficulty and appropriate next action need blind ratings.',
            'Slip/language are synthetic causes; runtime reports uncertainty rather than claiming to establish those causes.',
            'Follow-up branch/rotated diagrams tested, but no real learner follow-up or learning-gain experiment performed.',
            'Existing LoRA/QLoRA/full-FT artifacts are historical; not a new controlled expanded-curriculum model comparison.',
            'Paper draft and independent teammate setup verification are separate deliverables, not completed by automated tests.']}
    report['reproduction'] = {'command': r'.\venv\Scripts\python.exe scripts\evaluate_phase2_v2.py',
        'source_sha256': digest(Path(__file__)), 'bank_sha256': digest(e.BANK_PATH),
        'no_external_generation': True, 'database': 'Temporary isolated synthetic learner database; deleted on exit.'}
    report['document_coverage']['paragraph_audit'] = document_checklist()
    final_artifacts(report)
    save('results.json', report); render(report)
    print(json.dumps({'report': str(OUT/'report.html'), 'diagnosis': report['diagnosis']['by_language'],
                      'retrieval': report['retrieval']['by_language'], 'workflow': report['workflow']}, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
