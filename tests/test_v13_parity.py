"""Full 100 generated scenarios: reference Python vs independent JS evaluator."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest
from ddlab.challenge import generate_cases
from ddlab.core import evaluate

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(shutil.which('node'),'Node.js not installed — V1.3 parity NOT RUN')
class ChallengeBrowserParity(unittest.TestCase):
    def test_100_cross_runtime_structural_checks(self):
        script='''
          import {CHALLENGE_DECK} from './docs/challenge-deck.mjs';
          import {evaluateCase} from './docs/engine.mjs';
          const reports=CHALLENGE_DECK.map(({case:c})=>({case_id:c.case_id,report:evaluateCase(c)}));
          console.log(JSON.stringify(reports));
        '''
        proc=subprocess.run(['node','--input-type=module','-e',script],cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(proc.returncode,0,proc.stderr)
        results=json.loads(proc.stdout)
        self.assertEqual(len(results),100)
        by_id={e['case_id']:e['report'] for e in results}
        for entry in generate_cases():
            c=entry['case']; py=evaluate(c); js=by_id[c['case_id']]
            with self.subTest(case=c['case_id']):
                for field in ('verdict','facts','decisions','approval_check','findings','metrics'):
                    # Each engine is implemented independently; this is parity, not ground truth.
                    self.assertEqual(py[field],js[field],field)

    def test_v13_node_regressions(self):
        proc=subprocess.run(['node','--test','tests/v13-challenge.test.mjs'],cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(proc.returncode,0,proc.stdout+'\n'+proc.stderr)
