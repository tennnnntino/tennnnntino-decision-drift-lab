"""V1.4 contracts in the Python runtime: fail-closed intake, schema subset, redaction.

The same vector files are executed by tests/v14-contracts.test.mjs; cross-runtime
agreement on *observed* behaviour is asserted in tests/test_v14_parity.py.
"""
import ast
import base64
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ddlab.challenge import generate_cases
from ddlab.evidence import redact
from ddlab.intake import DEFAULT_LIMITS, IntakeError, parse_json_strict, read_text_strict
from ddlab.schema import SchemaError, validate

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"


def load(name):
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))


def vector_bytes(vector):
    if "input_b64" in vector:
        return base64.b64decode(vector["input_b64"])
    if "repeat" in vector:
        return (vector["repeat"]["unit"] * vector["repeat"]["count"]).encode("utf-8")
    return vector["input_utf8"].encode("utf-8")


def observe_intake(vector):
    reader = read_text_strict if vector["kind"] == "text" else parse_json_strict
    try:
        reader(vector_bytes(vector), vector.get("limits"))
    except IntakeError as exc:
        return exc.code
    return "OK"


def observe_schema(vector, case_schema):
    schema = case_schema if vector["schema"] == "case" else vector["inline_schema"]
    try:
        return validate(vector["instance"], schema)
    except SchemaError:
        return "SCHEMA_ERROR"


class IntakeVectors(unittest.TestCase):
    def test_every_intake_vector(self):
        vectors = load("intake-vectors.json")["vectors"]
        self.assertGreaterEqual(len(vectors), 40)
        for vector in vectors:
            with self.subTest(vector=vector["id"], why=vector["why"]):
                self.assertEqual(observe_intake(vector), vector["expect"])

    def test_default_bounds_are_declared(self):
        self.assertEqual(DEFAULT_LIMITS, {"max_bytes": 524288, "max_lines": 20000, "max_tokens": 100000, "max_depth": 32})

    def test_non_bytes_input_is_refused(self):
        with self.assertRaises(IntakeError) as ctx:
            read_text_strict("already decoded")
        self.assertEqual(ctx.exception.code, "EXPECTED_BYTES")

    def test_accepted_text_is_returned_unchanged(self):
        raw = "Café — draft only".encode("utf-8")
        self.assertEqual(read_text_strict(raw).encode("utf-8"), raw)

    def test_cli_strict_schema_rejects_what_the_default_path_accepts(self):
        # A hidden right-to-left override inside an escaped JSON string.
        case = json.loads((ROOT / "examples" / "clean_handoff.json").read_text(encoding="utf-8"))
        text = json.dumps(case).replace("clean-handoff", "clean\\u202ehandoff")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "case.json"
            path.write_text(text, encoding="utf-8")
            base = [sys.executable, "-m", "ddlab", "evaluate", str(path)]
            default = subprocess.run(base, cwd=ROOT, capture_output=True, text=True, timeout=20)
            strict = subprocess.run(base + ["--strict-schema"], cwd=ROOT, capture_output=True, text=True, timeout=20)
        self.assertEqual(default.returncode, 0, default.stderr)
        self.assertEqual(strict.returncode, 2)
        self.assertIn("BIDI_CONTROL_CHARACTER", strict.stderr)


class SchemaVectors(unittest.TestCase):
    def test_every_schema_vector(self):
        case_schema = load("case.schema.json")
        vectors = load("schema-vectors.json")["vectors"]
        self.assertGreaterEqual(len(vectors), 26)
        for vector in vectors:
            with self.subTest(vector=vector["id"], why=vector["why"]):
                self.assertEqual(observe_schema(vector, case_schema), vector["expect"])

    def test_all_packaged_fixtures_satisfy_the_case_schema(self):
        schema = load("case.schema.json")
        fixtures = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((ROOT / "examples").glob("*.json"))]
        self.assertEqual(len(fixtures), 10)
        for case in fixtures + [entry["case"] for entry in generate_cases()]:
            with self.subTest(case=case["case_id"]):
                self.assertEqual(validate(case, schema), [])

    def test_packaged_schemas_use_only_supported_keywords(self):
        for name in ("case.schema.json", "handoff-corpus.schema.json", "evidence-report.schema.json"):
            with self.subTest(schema=name):
                validate({}, load(name))  # raises SchemaError on any unsupported keyword reached

    def test_cli_validate_reports_violations(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            path.write_text('{"case_id":"x","source":[],"handoff":{},"action":{}}', encoding="utf-8")
            proc = subprocess.run([sys.executable, "-m", "ddlab", "validate", str(path)], cwd=ROOT,
                                  capture_output=True, text=True, timeout=20)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(json.loads(proc.stdout)["violations"], [{"path": "/source", "keyword": "type"}])


class RedactionVectors(unittest.TestCase):
    def test_every_redaction_vector(self):
        for vector in load("redaction-vectors.json")["vectors"]:
            with self.subTest(vector=vector["id"]):
                self.assertEqual(redact(vector["input"]), (vector["output"], vector["replacements"]))


class UntrustedTextStaysData(unittest.TestCase):
    """Static guard: the V1.4 Python modules have no way to execute, fetch, query or shell out."""

    ALLOWED_IMPORTS = {"__future__", "argparse", "hashlib", "json", "math", "pathlib", "re", "sys", "typing",
                       "unicodedata", "copy"}
    FORBIDDEN_NAMES = {"eval", "exec", "compile", "__import__", "open"}  # bare builtins; path.open / re.compile are fine
    FORBIDDEN_ATTRS = {"system", "popen", "urlopen", "run", "Popen", "connect", "execute"}

    def test_modules_import_only_inert_standard_library(self):
        for path in sorted((ROOT / "ddlab").glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name.split(".")[0] for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    names = [(node.module or "").split(".")[0]]
                for name in names:
                    with self.subTest(module=path.name, imported=name):
                        self.assertIn(name, self.ALLOWED_IMPORTS)
                if isinstance(node, ast.Call):
                    with self.subTest(module=path.name, line=node.lineno):
                        if isinstance(node.func, ast.Name):
                            self.assertNotIn(node.func.id, self.FORBIDDEN_NAMES)
                        elif isinstance(node.func, ast.Attribute):
                            self.assertNotIn(node.func.attr, self.FORBIDDEN_ATTRS)


if __name__ == "__main__":
    unittest.main()
