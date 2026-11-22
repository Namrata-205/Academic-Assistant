from tests.legacy_curriculum import frozen_v1
import json
import tempfile
import unittest
from pathlib import Path
from diagnostic import engine as e


class DiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._legacy=frozen_v1();cls._legacy.__enter__();cls.addClassCleanup(cls._legacy.__exit__,None,None,None)
        cls.nodes, cls.edges = e.load_graph()
        cls.bank = e.load_bank()

    def observations(self, answers):
        qs = [q for q in self.bank if q['concept_id'] == 'MATH6_C0038']
        return [{'question_id': q['id'], 'concept_id': q['concept_id'], 'response': a,
                 'score': e.score(q, a)} for q, a in zip(qs, answers)]

    def test_bank_structure_and_keys(self):
        self.assertEqual(len(self.bank), 30)
        self.assertEqual(len({q['concept_id'] for q in self.bank}), 10)
        self.assertEqual(len({q['id'] for q in self.bank}), 30)
        for q in self.bank:
            self.assertTrue(q['en'] and q['hi'] and q['scoring_rule'] and q['possible_difficulty'])
            self.assertEqual(e.score(q, q['answer']), 1)
            self.assertIsNone(e.score(q, 'perhaps'))

    def test_requested_report_codes_and_verified_mapping_details(self):
        target='MATH6_C0038'
        for answers,code in [(['400','700'],1),(['401','701'],2),(['400','701'],3)]:
            report=e.make_report(target,self.bank,self.edges,self.observations(answers))
            row=next(c for c in report['concepts'] if c['concept_id']==target)
            self.assertEqual(row['status_code'],code)
            self.assertTrue(row['textbook']['location_verified'])
            self.assertTrue(all(c['status_code'] is None for c in report['concepts'] if c['assessment']=='Unassessed'))
        details=e.describe_concept('MATH6_C0025',self.nodes,self.edges)
        self.assertEqual(details['concept']['en'],'acute angle')
        self.assertIn('MATH6_C0020',[c['id'] for c in details['prerequisites']])
        self.assertEqual(details['concept']['textbook']['versions']['en']['read_printed_page'],31)
        self.assertIn('PENDING',report['decision_rule_review']['status'])

    def test_mapping_unique_and_ambiguous(self):
        for text in ('Explain a right angle.', 'समकोण को समझाइए।'):
            self.assertEqual(e.map_question(text, self.nodes, self.edges)['concept_id'], 'MATH6_C0024')
        for text in ('odd number', 'even number', 'fractions', '', 'place value and acute angle'):
            self.assertEqual(e.map_question(text, self.nodes, self.edges)['status'], 'clarify')

    def test_scoring_and_conservative_decisions(self):
        self.assertEqual(e.score(self.bank[-6], '४००'), 1)
        self.assertEqual(e.status(self.observations(['400'])), 'Insufficient evidence')
        self.assertEqual(e.status(self.observations(['401', '701'])), 'Possible prerequisite difficulty')
        self.assertEqual(e.status(self.observations(['400', '700'])), 'Evidence supports understanding')
        self.assertEqual(e.status(self.observations(['401', '700', '60'])), 'Insufficient evidence')

    def test_single_error_gets_check_and_budget(self):
        current = []
        for _ in range(3):
            q = e.select_question('MATH6_C0038', self.bank, self.edges, current)
            self.assertIsNotNone(q)
            current.append({'question_id': q['id'], 'concept_id': q['concept_id'], 'response': 'wrong', 'score': 0 if not current else 1})
        self.assertIsNone(e.select_question('MATH6_C0038', self.bank, self.edges, current))
        self.assertEqual(len({r['question_id'] for r in current}), 3)

    def test_unasked_is_unassessed_and_cycles_do_not_recurse(self):
        report = e.make_report('MATH6_C0025', self.bank, self.edges, [])
        self.assertTrue(all(r['assessment'] == 'Unassessed' for r in report['concepts']))
        self.assertTrue(all(r['status'] == 'Insufficient evidence' for r in report['concepts']))

    def test_storage_isolation_and_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = e.connect(Path(tmp) / 'history.sqlite3')
            sid = e.new_session(conn, 'learner-a', 'MATH6_C0038', 'graph-guided', [])
            q = next(q for q in self.bank if q['concept_id'] == 'MATH6_C0038')
            e.save_response(conn, sid, q, '४००')
            self.assertEqual(e.history(conn, 'learner-a')[0]['score'], 1)
            self.assertEqual(e.history(conn, 'learner-b'), [])
            conn.close()
            conn = e.connect(Path(tmp) / 'history.sqlite3')
            self.assertEqual(len(e.history(conn, 'learner-a')), 1)
            conn.close()

    def test_saved_budget_and_report_traceability(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = e.connect(Path(tmp) / 'history.sqlite3')
            sid = e.new_session(conn, 'trace-test', 'MATH6_C0038', 'graph-guided', [])
            current = []
            for response in ('401', '700', '60'):
                q = e.select_question('MATH6_C0038', self.bank, self.edges, current)
                current.append(e.save_response(conn, sid, q, response))
            with self.assertRaises(ValueError):
                e.save_response(conn, sid, q, '60')
            report = e.make_report('MATH6_C0038', self.bank, self.edges, current)
            row = next(r for r in report['concepts'] if r['role'] == 'target')
            self.assertEqual(row['status'], 'Insufficient evidence')
            self.assertEqual(len(row['observations']), 3)
            self.assertIn('scoring_rule', row['observations'][0])
            self.assertIn('source_references', row['observations'][0])
            conn.close()

    def test_historical_item_not_repeated(self):
        prior = self.observations(['401'])
        q = e.select_question('MATH6_C0038', self.bank, self.edges, [], prior)
        self.assertNotEqual(q['id'], prior[0]['question_id'])
        report = e.make_report('MATH6_C0038', self.bank, self.edges, [], prior)
        self.assertEqual(report['concepts'][-1]['assessment'], 'Unassessed')


if __name__ == '__main__':
    unittest.main()
