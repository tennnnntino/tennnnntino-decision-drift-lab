import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ddlab.core import canonical_json, compare_items, digest, evaluate

ROOT=Path(__file__).resolve().parents[1]


def fixture(name):
    return json.loads((ROOT/'examples'/f'{name}.json').read_text(encoding='utf-8'))


class ValidatorTests(unittest.TestCase):
    def test_all_packaged_cases_match_expected(self):
        cases=list((ROOT/'examples').glob('*.json'))
        self.assertGreaterEqual(len(cases),10)
        for f in cases:
            with self.subTest(path=f):
                case=json.loads(f.read_text(encoding='utf-8'))
                self.assertEqual(evaluate(case)['verdict'],case['expected_verdict'])

    def test_flags_exact_change(self):
        report=evaluate(fixture('silent_rewrite'))
        self.assertIn('F1',report['facts']['altered'])
        self.assertIn('F2',report['facts']['missing'])
        self.assertIn('F99',report['facts']['introduced'])
        self.assertEqual(report['metrics']['fact_exact_recall'],0)

    def test_rejects_self_approval(self):
        report=evaluate(fixture('agent_self_approval'))
        self.assertEqual(report['approval_check']['result'],'BLOCK_IN_SIMULATION')
        self.assertFalse(report['approval_check']['authenticated'])

    def test_detects_fact_promotion(self):
        self.assertIn('UNSUPPORTED_FACT_PROMOTION', [x['code'] for x in evaluate(fixture('fact_promotion'))['findings']])

    def test_detects_revoked_reactivation(self):
        self.assertIn('REACTIVATED_DECISION',[x['code'] for x in evaluate(fixture('revoked_decision'))['findings']])

    def test_detects_scope_mismatch(self):
        self.assertIn('SCOPE_MISMATCH',evaluate(fixture('scope_mismatch'))['approval_check']['reasons'])

    def test_change_authority(self):
        self.assertIn('AUTHORITY_CHANGED',[x['code'] for x in evaluate(fixture('changed_authority'))['findings']])

    def test_digest_stable_across_object_key_order(self):
        self.assertEqual(digest({'b':2,'a':1}),digest({'a':1,'b':2}))

    def test_no_truth_claims(self):
        self.assertTrue(any('do not prove truth' in x for x in evaluate(fixture('clean_handoff'))['limitations']))

    def test_no_denominator_fabrication(self):
        c=fixture('clean_handoff');c['source']['decisions']=[];c['handoff']['decisions']=[]
        self.assertIsNone(evaluate(c)['metrics']['decision_exact_recall'])

    def test_duplicate_fails_closed(self):
        c=fixture('clean_handoff');c['handoff']['facts'].append(c['handoff']['facts'][0])
        with self.assertRaisesRegex(ValueError,'duplicate'): evaluate(c)

    def test_null_vs_missing_field_is_reported(self):
        c=fixture('clean_handoff')
        c['source']['facts'][0]['optional']=None
        report=evaluate(c)
        self.assertEqual(report['verdict'],'FAIL')
        self.assertIn('optional',report['facts']['changes'][0]['changed_fields'])

    def test_missing_id_fails_closed(self):
        c=fixture('clean_handoff');c['handoff']['facts'][0].pop('id')
        with self.assertRaisesRegex(ValueError,'nonempty'): evaluate(c)

    def test_size_limit(self):
        c=fixture('clean_handoff');c['source']['facts'][0]['text']='x'*600_000
        with self.assertRaisesRegex(ValueError,'limit'): evaluate(c)

    def test_excessive_list(self):
        c=fixture('clean_handoff');c['source']['facts']=[{'id':str(i)} for i in range(1001)]
        with self.assertRaisesRegex(ValueError,'too many'): evaluate(c)

    def test_case_input_not_mutated(self):
        c=fixture('clean_handoff');before=canonical_json(c);evaluate(c)
        self.assertEqual(before,canonical_json(c))

    def test_report_digest_reproducible(self):
        self.assertEqual(evaluate(fixture('clean_handoff'))['report_sha256'],evaluate(fixture('clean_handoff'))['report_sha256'])

    def test_invalid_approval_type(self):
        c=fixture('clean_handoff');c['action']['requires_human']='false'
        with self.assertRaisesRegex(ValueError,'boolean'): evaluate(c)

    def test_no_approval_still_allows_draft_only_if_requires_false(self):
        self.assertEqual(evaluate(fixture('customer_followup'))['verdict'],'PASS')

    def test_empty_comparison(self):
        # V1.4.1: a case can no longer waive the human requirement for itself. An empty comparison
        # passes only for an action that the EXTERNAL policy exempts.
        c={'case_id':'empty','source':{},'handoff':{},'action':{'name':'prepare-draft','scope':'internal','requires_human':False}}
        self.assertEqual(evaluate(c)['verdict'],'PASS')
        self.assertIsNone(evaluate(c)['metrics']['decision_exact_precision'])
        unnamed={'case_id':'empty','source':{},'handoff':{},'action':{'requires_human':False}}
        report=evaluate(unnamed)
        self.assertEqual(report['verdict'],'FAIL')
        self.assertIn('CASE_WAIVER_IGNORED',report['approval_check']['reasons'])

    def test_benchmark_cli(self):
        p=subprocess.run([sys.executable,'-m','ddlab','benchmark'],cwd=ROOT, capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout)['total'],10)

    def test_fail_cli_returns_one(self):
        p=subprocess.run([sys.executable,'-m','ddlab','evaluate','examples/silent_rewrite.json'],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(p.returncode,1,p.stderr)

    def test_input_rejects_malformatted_json(self):
        with tempfile.NamedTemporaryFile('w',suffix='.json',delete=False) as f:
            f.write('bad {');name=f.name
        try:
            p=subprocess.run([sys.executable,'-m','ddlab','evaluate',name],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.returncode,2)
        finally:
            Path(name).unlink()


if __name__=='__main__': unittest.main()
