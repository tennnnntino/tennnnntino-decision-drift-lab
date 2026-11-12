"""Cross-runtime behavioral parity on all packaged synthetic fixtures."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from ddlab.core import evaluate

ROOT=Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('node'), 'Node.js not present: browser parity needs Node.js')
class BrowserParity(unittest.TestCase):
    def test_browser_and_python_agree(self):
        javascript='''
          import {CASES} from './docs/cases.mjs';
          import {evaluateCase} from './docs/engine.mjs';
          console.log(JSON.stringify(Object.fromEntries(Object.entries(CASES).map(([id,c])=>[id,evaluateCase(c)]))));
        '''
        proc=subprocess.run(['node','--input-type=module','-e',javascript],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(proc.returncode,0,proc.stderr)
        results=json.loads(proc.stdout)
        self.assertEqual(len(results),10)
        for file in (ROOT/'examples').glob('*.json'):
            c=json.loads(file.read_text(encoding='utf-8'))
            py=evaluate(c)
            js=results[c['case_id']]
            with self.subTest(case=c['case_id']):
                for k in ('verdict','facts','decisions','approval_check','findings','metrics'):
                    self.assertEqual(py[k],js[k],k)
