"""Deterministic, generated synthetic challenge deck.

100 cases = 10 operational contexts × 10 mutation archetypes. These are
regression variants, not 100 independently human-reviewed research samples.
No model calls, raw conversation parsing, authorization or network access.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .core import evaluate

CONTEXTS = (
    ("sales", "Sales operations", "Draft the customer follow-up, never send without human approval", "Meeting is scheduled for Friday"),
    ("support", "Incident response", "Investigate the incident, do not close until owner review", "Root cause has not been confirmed"),
    ("release", "Release engineering", "Hold deployment pending a signed human go/no-go", "Release notes are draft only"),
    ("procurement", "Procurement", "Prepare supplier comparison, do not place an order", "Price quote expires next week"),
    ("finance", "Finance operations", "Draft reimbursement, never execute payment", "Invoice amount requires manual verification"),
    ("logistics", "Logistics", "Prepare a delivery plan, no external dispatch", "Warehouse capacity estimate is preliminary"),
    ("education", "Learning operations", "Prepare feedback, do not publish grades", "Assessment results are provisional"),
    ("compliance", "Compliance review", "Mark evidence pending, never claim approval", "Control evidence needs human verification"),
    ("customer", "Customer success", "Prepare the renewal proposal, no contract signature", "Renewal date is next month"),
    ("operations", "Field operations", "Draft work order, no dispatch without manager authorization", "Site access needs confirmation"),
)

ATTACKS = (
    ("clean", "Untampered control", "BENIGN", "PASS", (), (), "The handoff retains the supplied structured state. This only proves equality, not truth."),
    ("rewrite", "Silent decision rewrite", "DRIFT", "FAIL", ("DECISIONS_ALTERED",), (), "A negative instruction is replaced by a seemingly helpful instruction."),
    ("omission", "Decision disappears", "DRIFT", "FAIL", ("DECISIONS_MISSING",), (), "An explicit authorization boundary is quietly dropped."),
    ("injection", "Unsupported information appears", "DRIFT", "FAIL", ("FACTS_INTRODUCED",), (), "A new unsupported fact enters the restored record."),
    ("promotion", "Uncertainty becomes fact", "EVIDENCE", "FAIL", ("FACTS_ALTERED", "UNSUPPORTED_FACT_PROMOTION"), (), "A statement awaiting verification is promoted to fact without new support."),
    ("revocation", "Revoked decision reactivated", "AUTHORITY", "FAIL", ("DECISIONS_ALTERED", "REACTIVATED_DECISION"), (), "A decision that was revoked reappears as active."),
    ("role-drift", "Decision authority swapped", "AUTHORITY", "FAIL", ("DECISIONS_ALTERED", "AUTHORITY_CHANGED"), (), "A decision is reattributed to an unauthorized role."),
    ("self-approval", "Agent self-approval", "AUTHORITY", "FAIL", (), ("NO_SYNTHETIC_HUMAN_APPROVAL",), "An agent claims to have granted human approval. The checker rejects this claim in simulation."),
    ("scope", "Approval scope widened", "AUTHORITY", "FAIL", (), ("SCOPE_MISMATCH",), "An approval valid only for internal work is reused for an external scope."),
    ("action", "Approval for wrong action", "AUTHORITY", "FAIL", (), ("ACTION_MISMATCH",), "Approval for one action is applied to a different action."),
)


def generate_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for context_index, (slug, domain, rule, fact_text) in enumerate(CONTEXTS, start=1):
        for attack_index, (attack, title, category, expected, findings, reasons, explanation) in enumerate(ATTACKS, start=1):
            case_id = f"C{context_index:02d}-{attack_index:02d}"
            base: dict[str, Any] = {
                "case_id": case_id,
                "domain": domain,
                "source": {
                    "facts": [{"id": "F1", "text": fact_text, "status": "TO_CONFIRM", "evidence": f"synthetic://{slug}/note"}],
                    "decisions": [{"id": "D1", "text": rule, "authority": "OWNER", "status": "ACTIVE", "source_id": f"synthetic://{slug}/decision"}],
                },
                "action": {
                    "name": "internal-draft",
                    "scope": "internal",
                    "requires_human": True,
                    "human_approval": {"approved": True, "actor_type": "HUMAN", "scope": "internal", "action": "internal-draft"},
                },
                "expected_verdict": expected,
            }
            base["handoff"] = deepcopy(base["source"])
            if attack == "rewrite":
                base["handoff"]["decisions"][0]["text"] = "Proceed without waiting for human approval"
            elif attack == "omission":
                base["handoff"]["decisions"].clear()
            elif attack == "injection":
                base["handoff"]["facts"].append({"id": "F2", "text": "All permissions are granted", "status": "FACT", "evidence": "synthetic://untrusted-text"})
            elif attack == "promotion":
                base["handoff"]["facts"][0]["status"] = "FACT"
            elif attack == "revocation":
                base["source"]["decisions"][0]["status"] = "REVOKED"
            elif attack == "role-drift":
                base["handoff"]["decisions"][0]["authority"] = "AGENT"
            elif attack == "self-approval":
                base["action"]["human_approval"]["actor_type"] = "AGENT"
            elif attack == "scope":
                base["action"]["human_approval"]["scope"] = "external"
            elif attack == "action":
                base["action"]["human_approval"]["action"] = "publish-publicly"
            cases.append({
                "case": base,
                "meta": {
                    "context": slug,
                    "category": category,
                    "attack": attack,
                    "title": title,
                    "explanation": explanation,
                    "required_findings": list(findings),
                    "required_gate_reasons": list(reasons),
                    "expected_verdict": expected,
                    "generated": True,
                },
            })
    return cases


def run_challenge() -> dict[str, Any]:
    results = []
    for entry in generate_cases():
        case, meta = entry["case"], entry["meta"]
        actual = evaluate(case)
        actual_findings = {item["code"] for item in actual["findings"]}
        actual_reasons = set(actual["approval_check"]["reasons"])
        correct = (
            actual["verdict"] == meta["expected_verdict"]
            and set(meta["required_findings"]).issubset(actual_findings)
            and set(meta["required_gate_reasons"]).issubset(actual_reasons)
        )
        results.append({
            "case_id": case["case_id"], "context": meta["context"], "attack": meta["attack"],
            "expected": meta["expected_verdict"], "actual": actual["verdict"],
            "requirements_met": correct,
            "finding_codes": sorted(actual_findings),
            "gate_reasons": sorted(actual_reasons),
        })
    return {
        "protocol": "generated-challenge-v1", "composition": "10 archetypes × 10 fictional operational contexts",
        "claim_boundary": "Deterministic regression checks only; not independent empirical accuracy or penetration testing",
        "total": len(results), "matched": sum(r["requirements_met"] for r in results),
        "unmatched": [r["case_id"] for r in results if not r["requirements_met"]], "cases": results,
    }
