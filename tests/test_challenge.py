"""Generated regression deck: correctness of declared reference scenarios only."""
import json
from pathlib import Path
import unittest
from ddlab.challenge import generate_cases, run_challenge
from ddlab.core import evaluate

ROOT = Path(__file__).resolve().parents[1]

class ChallengeDeckTests(unittest.TestCase):
    def test_100_generated_cases_unique_ids(self):
        cases = generate_cases()
        self.assertEqual(len(cases), 100)
        self.assertEqual(len({e['case']['case_id'] for e in cases}), 100)
        self.assertEqual(len({e['meta']['context'] for e in cases}), 10)
        self.assertEqual(len({e['meta']['attack'] for e in cases}), 10)

    def test_expected_verdicts_and_signal_coverage(self):
        result = run_challenge()
        self.assertEqual(result['matched'], 100, result['unmatched'])
        self.assertEqual(sum(r['actual']=='PASS' for r in result['cases']), 10)
        self.assertEqual(sum(r['actual']=='FAIL' for r in result['cases']), 90)
        self.assertEqual(sum(bool(r['gate_reasons']) for r in result['cases']), 30)

    def test_packaged_json_is_deterministically_generated(self):
        package = json.loads((ROOT/'research'/'generated-challenge-100.json').read_text('utf-8'))
        self.assertEqual(package['cases'], generate_cases())
        self.assertIn('not independently human-labelled', package['disclaimer'])

    def test_known_benign_and_adversarial_controls(self):
        deck = generate_cases()
        for e in deck:
            rep = evaluate(e['case'])
            self.assertEqual(rep['verdict'],e['meta']['expected_verdict'])
            if e['meta']['attack']=='promotion':
                self.assertIn('UNSUPPORTED_FACT_PROMOTION',{f['code'] for f in rep['findings']})
            if e['meta']['attack']=='self-approval':
                self.assertFalse(rep['approval_check']['authenticated'])
                self.assertIn('NO_SYNTHETIC_HUMAN_APPROVAL',rep['approval_check']['reasons'])

    def test_static_html_contains_explicit_limitations(self):
        html=(ROOT/'docs'/'index.html').read_text('utf-8')
        self.assertIn('not an agent-security certification', html)
        self.assertIn('100 independent research samples', html)
        self.assertNotIn('real-world security guaranteed', html)

if __name__=='__main__': unittest.main()
