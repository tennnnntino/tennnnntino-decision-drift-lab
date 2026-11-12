"""V1.4 cross-runtime parity: Python and JavaScript must OBSERVE the same thing.

Parity means two independently written implementations agree. It does not mean
either is right, and it says nothing about meaning, identity or security.
"""
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from ddlab import corpus
from ddlab.challenge import generate_cases
from ddlab.core import evaluate
from ddlab.evidence import build_report, redact
from ddlab.recovery import classify_recovery

from test_v14_contracts import load, observe_intake, observe_schema  # same directory (discover -s tests)

ROOT = Path(__file__).resolve().parents[1]


def observe_probe(vector):
    try:
        report = evaluate(json.loads(vector["case_json"]))
    except (ValueError, RecursionError, OverflowError):
        return {"rejected": True}
    return {"rejected": False, "verdict": report["verdict"], "findings": sorted(f["code"] for f in report["findings"]),
            "findings_in_order": [f"{f['code']}:{f['item_id']}" for f in report["findings"]],
            "gate": report["approval_check"]["result"], "reasons": report["approval_check"]["reasons"],
            "advisories": sorted(a["code"] for a in report["advisories"]),
            "ledger": [[e["id"], e["handoff_state"]] for e in report["revocation_ledger"]],
            "decision_exact_recall": report["metrics"]["decision_exact_recall"],
            "change_order": [c["id"] for c in report["facts"]["changes"]],
            "text_profiles": [c["text_profile"] for zone in ("facts", "decisions") for c in report[zone]["changes"]
                              if "text_profile" in c]}


@unittest.skipUnless(shutil.which("node"), "Node.js not installed: V1.4 parity NOT RUN")
class V14Parity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        proc = subprocess.run(["node", "tests/v14-observe.mjs"], cwd=ROOT, capture_output=True, text=True,
                              encoding="utf-8", timeout=120)
        if proc.returncode != 0:
            raise AssertionError(proc.stderr)
        cls.js = json.loads(proc.stdout)
        cls.cases = [(doc["split"], case) for doc in (corpus.load_split("dev"), corpus.load_split("heldout"))
                     for case in doc["cases"]]

    def test_intake_codes_agree(self):
        for vector in load("intake-vectors.json")["vectors"]:
            with self.subTest(vector=vector["id"]):
                self.assertEqual(observe_intake(vector), self.js["intake"][vector["id"]])

    def test_schema_violations_agree(self):
        case_schema = load("case.schema.json")
        for vector in load("schema-vectors.json")["vectors"]:
            with self.subTest(vector=vector["id"]):
                self.assertEqual(observe_schema(vector, case_schema), self.js["schema"][vector["id"]])

    def test_redaction_agrees(self):
        for vector in load("redaction-vectors.json")["vectors"]:
            text, count = redact(vector["input"])
            with self.subTest(vector=vector["id"]):
                self.assertEqual({"text": text, "count": count}, self.js["redaction"][vector["id"]])

    def test_purple_probes_agree_with_record_and_between_runtimes(self):
        doc = load("purple-v1_4-vectors.json")
        for vector in doc["vectors"]:
            with self.subTest(vector=vector["id"], title=vector["title"]):
                observed = observe_probe(vector)
                self.assertEqual(observed, vector["expected"])
                self.assertEqual(observed, self.js["purple"][vector["id"]], "the two evaluators must not diverge")
        self.assertEqual(len(doc["vectors"]), 28)
        open_items = sorted(v["id"] for v in doc["vectors"] if v["status"] == "OPEN_LIMITATION")
        self.assertEqual(open_items, ["P08", "P19"])

    def test_full_structured_reports_agree_on_all_110_existing_cases(self):
        fields = ("verdict", "facts", "decisions", "approval_check", "findings", "advisories", "revocation_ledger", "metrics")
        fixtures = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((ROOT / "examples").glob("*.json"))]
        cases = fixtures + [entry["case"] for entry in generate_cases()]
        self.assertEqual(len(cases), 110)
        for case in cases:
            report = evaluate(case)
            with self.subTest(case=case["case_id"]):
                self.assertEqual({k: report[k] for k in fields}, self.js["structured"][case["case_id"]])

    def test_policy_snapshot_matches_the_contract(self):
        proc = subprocess.run([sys.executable, "tools/build_policy_module.py", "--check"], cwd=ROOT,
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_recovery_classification_agrees_on_all_37_cases(self):
        self.assertEqual(len(self.cases), 37)
        for _, case in self.cases:
            with self.subTest(case=case["case_id"]):
                self.assertEqual(classify_recovery(case), self.js["recovery"][case["case_id"]])

    def test_portable_reports_and_digests_agree_on_all_37_cases(self):
        for split, case in self.cases:
            with self.subTest(case=case["case_id"]):
                self.assertEqual(build_report(case, split, profile="portable"), self.js["reports"][case["case_id"]])

    def test_walkthrough_snapshot_matches_the_corpus(self):
        proc = subprocess.run([sys.executable, "tools/build_walkthrough_case.py", "--check"], cwd=ROOT,
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_v14_node_suite(self):
        proc = subprocess.run(["node", "--test", "tests/v14-contracts.test.mjs"], cwd=ROOT, capture_output=True,
                              text=True, encoding="utf-8", timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stdout + "\n" + proc.stderr)


if __name__ == "__main__":
    unittest.main()
