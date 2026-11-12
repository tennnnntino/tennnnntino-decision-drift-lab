"""Run the V1.2 JS logic regression suite through the existing Python command."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

class V12BrowserLogicTests(unittest.TestCase):
    def test_v12_node_regressions(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node runtime not installed; JS tests NOT RUN')
        result = subprocess.run([node, '--test', 'tests/v12-browser-logic.test.mjs'],
                                cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + '\n' + result.stderr)
