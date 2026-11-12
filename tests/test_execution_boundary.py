"""Replay route-bound attack and control cases in both runtimes."""
import json
from pathlib import Path
import subprocess
import unittest

from ddlab.execution import SimulatedConnector


def scenarios():
    send = {"name": "send-document", "scope": "external", "requires_human": False}
    draft = {"name": "prepare-draft", "scope": "internal", "requires_human": False}
    request = {"target": "demo-target", "content": "Synthetic content", "tenant": "demo"}
    connector = SimulatedConnector()
    results = []

    def attempt(claim=send, route="send", now=1, approval_id=None, **overrides):
        results.append(connector.attempt(claim, route=route, request={**request, **overrides},
                                         now=now, approval_id=approval_id))

    attempt(draft, route="draft")
    attempt(draft)
    attempt({**send, "human_approval": {"approved": True, "actor_type": "HUMAN"}})
    attempt(route="unknown")
    connector.approve("A", "send", request, 5)
    attempt(approval_id="A", target="different")
    attempt(approval_id="A", content="different")
    attempt(approval_id="A", tenant="different")
    attempt(approval_id="A")
    attempt(approval_id="A")
    connector.approve("B", "send", request, 5)
    connector.revoke("B")
    attempt(approval_id="B")
    connector.approve("C", "send", request, 5)
    attempt(approval_id="C", now=5)
    connector.approve("D", "draft", request, 5)
    attempt(approval_id="D")
    return results


class ExecutionBoundaryTests(unittest.TestCase):
    def test_cross_runtime_attack_and_control_cases(self):
        reports = scenarios()
        self.assertEqual([r["reason"] for r in reports], [
            None, "DECLARATION_MISMATCH", "APPROVAL_MISSING", "INVALID_EXECUTION_CONTEXT",
            "APPROVAL_BINDING_MISMATCH", "APPROVAL_BINDING_MISMATCH", "APPROVAL_BINDING_MISMATCH",
            None, "APPROVAL_CONSUMED", "APPROVAL_REVOKED", "APPROVAL_EXPIRED", "APPROVAL_BINDING_MISMATCH",
        ])
        self.assertEqual(reports[1]["effective"], {"name": "send-document", "scope": "external"})
        self.assertTrue(all(not r["authenticated"] and not r["executed"] for r in reports))
        root = Path(__file__).resolve().parents[1]
        output = subprocess.check_output(["node", "tests/execution-observe.mjs"], cwd=root, text=True)
        self.assertEqual(reports, json.loads(output))
