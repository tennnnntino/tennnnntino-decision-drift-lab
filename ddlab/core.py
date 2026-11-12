"""Small, auditable structured-handoff evaluator.

This module never executes actions, authenticates people or calls AI models.
Exact JSON item equality is intentionally conservative, not semantic equivalence.

V1.4.1: the requirement for a simulated human approval comes from an external
policy (ddlab/policy.py), never from the case; revoked decisions keep a ledger
entry even when the handoff drops them; canonically equivalent Unicode is not
reported as a change; status spellings are normalised; reports are deterministic.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import re
from typing import Any
import unicodedata

from .policy import POLICY_LIKE_KEYS, check_policy, is_exempt, load_policy, policy_digest
from .schema import strict_equal

MAX_CASE_BYTES = 524_288
MAX_NESTING_DEPTH = 64
MAX_SAFE_INTEGER = 9_007_199_254_740_991  # 2**53 - 1: beyond this a JavaScript reader loses integer precision
SCHEMA_VERSION = "1.1"

# Status vocabulary. Matching trims, upper-cases ASCII letters and unifies space, hyphen and underscore.
STATUS_CLASSES = {
    "ACTIVE": ("ACTIVE", "ENABLED", "APPROVED", "REINSTATED", "IN_FORCE"),
    "REVOKED": ("REVOKED", "REJECTED", "CANCELLED", "CANCELED", "WITHDRAWN", "RESCINDED"),
    "FACT": ("FACT", "CONFIRMED", "VERIFIED"),
    "UNCERTAIN": ("TO_CONFIRM", "UNKNOWN", "SUPPORTED_INFERENCE", "UNCONFIRMED", "UNVERIFIED", "HYPOTHESIS", "TBC"),
}
_STATUS_LOOKUP = {alias: name for name, aliases in STATUS_CLASSES.items() for alias in aliases}
_ASCII_UPPER = str.maketrans("abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
_ASCII_LOWER = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")
_SEPARATORS = re.compile(r"[ _-]+")
_WORD = re.compile(r"[a-z0-9]+")
_NEGATIONS = frozenset(("not", "no", "never", "without", "cannot", "nothing", "none", "neither", "nor", "dont",
                        "doesnt", "didnt", "wont", "cant", "mustnt", "shouldnt", "isnt", "arent"))


def validate_nesting(value: Any, max_depth: int = MAX_NESTING_DEPTH) -> None:
    """Reject deeply nested or cyclic/unbounded object graphs before encoding.

    A direct Python caller may pass structures that JSON input cannot represent.
    This is a resource-safety check, not a JSON-schema validation.
    """
    pending = [(value, 0)]
    examined = 0
    while pending:
        item, depth = pending.pop()
        examined += 1
        if examined > 50_000:
            raise ValueError("case exceeds structural node limit")
        if depth > max_depth:
            raise ValueError("case nesting exceeds safety depth limit")
        if isinstance(item, dict):
            pending.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            pending.extend((child, depth + 1) for child in item)
        elif isinstance(item, bool):
            continue
        elif isinstance(item, int):
            # V1.4: a value two runtimes cannot both represent is rejected, not compared.
            if abs(item) > MAX_SAFE_INTEGER:
                raise ValueError("case contains an integer outside the IEEE-754 safe range")
        elif isinstance(item, float):
            if not math.isfinite(item) or (item.is_integer() and abs(item) > MAX_SAFE_INTEGER):
                raise ValueError("case contains a non-finite or unsafe integral number")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _nfc(value: Any) -> Any:
    """NFC-normalise every string, keys included. Canonical equivalence only, never NFKC."""
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_nfc(v) for v in value]
    if isinstance(value, dict):
        return {unicodedata.normalize("NFC", k): _nfc(v) for k, v in value.items()}
    return value


def status_class(value: Any) -> tuple[str | None, bool]:
    """Return (class or None, spelled exactly as a known token)."""
    if not isinstance(value, str):
        return None, True
    key = _SEPARATORS.sub("_", unicodedata.normalize("NFC", value).strip(" \t\n\r").translate(_ASCII_UPPER))
    name = _STATUS_LOOKUP.get(key)
    return name, name is None or value in _STATUS_LOOKUP


def text_profile(before: str, after: str) -> dict[str, Any]:
    """Lexical triage hints for a changed text. Not a judgement about meaning."""
    def words(text: str) -> list[str]:
        return _WORD.findall(text.translate(_ASCII_LOWER).replace("'", "").replace("’", ""))

    a, b = words(before), words(after)
    sa, sb = set(a), set(b)
    non_ascii = any(ord(ch) > 0x7F for ch in before + after)
    return {
        "formatting_only": bool(a) and a == b and not non_ascii,
        "source_tokens": len(sa), "handoff_tokens": len(sb), "shared_tokens": len(sa & sb),
        "negation_changed": bool(sa & _NEGATIONS) != bool(sb & _NEGATIONS),
        "numbers_changed": {t for t in sa if t.isdigit()} != {t for t in sb if t.isdigit()},
        "non_ascii_content": non_ascii,
    }


def _index(items: Any, zone: str) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list):
        raise ValueError(f"{zone} must be a list")
    result: dict[str, dict[str, Any]] = {}
    if len(items) > 1000:
        raise ValueError(f"{zone} has too many items")
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
            raise ValueError(f"{zone}: each item must have a nonempty string id")
        # V1.4.1: identifiers are keyed by their NFC form, so two spellings of one id cannot coexist.
        identifier = unicodedata.normalize("NFC", item["id"])
        if len(identifier) > 120:
            raise ValueError(f"{zone}: id too long")
        if identifier in result:
            raise ValueError(f"{zone}: duplicate id: {identifier}")
        result[identifier] = item
    return result


def _compare(source: Any, handoff: Any, zone: str) -> tuple[dict[str, Any], list[str]]:
    before = _index(source, f"source.{zone}")
    after = _index(handoff, f"handoff.{zone}")
    retained, altered, normalised = [], [], []
    for key in sorted(before.keys() & after.keys()):
        # V1.4: JSON-typed equality. Python's == treats True and 1 (and False and 0) as equal.
        if strict_equal(before[key], after[key]):
            retained.append(key)
        elif strict_equal(_nfc(before[key]), _nfc(after[key])):
            # V1.4.1: canonically equivalent Unicode is the same text; reported as an advisory only.
            retained.append(key)
            normalised.append(key)
        else:
            altered.append(key)
    changes = []
    for identifier in altered:
        old, new = _nfc(before[identifier]), _nfc(after[identifier])
        entry: dict[str, Any] = {
            "id": identifier,
            "changed_fields": sorted(k for k in (old.keys() | new.keys())
                                     if (k in old) != (k in new) or not strict_equal(old.get(k), new.get(k))),
        }
        if "text" in entry["changed_fields"] and isinstance(old.get("text"), str) and isinstance(new.get("text"), str):
            entry["text_profile"] = text_profile(old["text"], new["text"])
        changes.append(entry)
    return ({"retained": retained, "altered": altered, "missing": sorted(before.keys() - after.keys()),
             "introduced": sorted(after.keys() - before.keys()), "changes": changes,
             "source_total": len(before), "handoff_total": len(after)}, normalised)


def compare_items(source: Any, handoff: Any, zone: str) -> dict[str, Any]:
    return _compare(source, handoff, zone)[0]


def _gate(action: Any, policy: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(action, dict):
        raise ValueError("action must be an object")
    declared = action.get("requires_human", True)
    if not isinstance(declared, bool):
        raise ValueError("action.requires_human must be a boolean")
    approval = action.get("human_approval", {})
    if not isinstance(approval, dict):
        raise ValueError("human_approval must be an object")
    # V1.4.1: the requirement comes from the external policy. The case may tighten it, never waive it.
    exempt = is_exempt(policy, action.get("name"), action.get("scope"))
    requires_human = declared or not exempt
    waiver_ignored = not declared and not exempt
    explicit = approval.get("approved") is True and approval.get("actor_type") == "HUMAN"
    scope_matches = ("scope" not in approval or approval.get("scope") == action.get("scope"))
    action_matches = ("action" not in approval or approval.get("action") == action.get("name"))
    # V1.4: an approval that names no scope or no action is not a blanket approval.
    scope_stated, action_stated = "scope" in approval, "action" in approval
    # This is a fixture-level simulation, NOT identity verification.
    allowed_in_simulation = not requires_human or (
        explicit and scope_matches and action_matches and scope_stated and action_stated)
    reasons = []
    if requires_human:
        if not explicit:
            reasons.append("NO_SYNTHETIC_HUMAN_APPROVAL")
        if not scope_matches:
            reasons.append("SCOPE_MISMATCH")
        if not action_matches:
            reasons.append("ACTION_MISMATCH")
        if explicit and not scope_stated:
            reasons.append("APPROVAL_SCOPE_UNSPECIFIED")
        if explicit and not action_stated:
            reasons.append("APPROVAL_ACTION_UNSPECIFIED")
        if waiver_ignored:
            reasons.append("CASE_WAIVER_IGNORED")
    return {"result": "ALLOW_IN_SIMULATION" if allowed_in_simulation else "BLOCK_IN_SIMULATION",
            "requires_human": requires_human, "reasons": reasons,
            "authenticated": False,
            "requirement_source": "EXTERNAL_POLICY", "policy_id": policy["policy_id"],
            "policy_exempt": exempt, "case_declared_requires_human": declared}


def _ratio(num: int, denom: int) -> float | None:
    # V1.4.1: integer half-up rounding to four decimals, identical in Python and JavaScript.
    return (2 * num * 10_000 + denom) // (2 * denom) / 10_000 if denom else None


def evaluate(case: dict[str, Any], policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """Evaluate one structured case. ``policy`` is the operator's policy and is never read from ``case``."""
    if not isinstance(case, dict):
        raise ValueError("case must be an object")
    policy = load_policy() if policy is None else check_policy(policy)
    validate_nesting(case)
    if len(canonical_json(case).encode("utf-8")) > MAX_CASE_BYTES:
        raise ValueError("case exceeds safety size limit")
    source, handoff = case.get("source"), case.get("handoff")
    if not isinstance(source, dict) or not isinstance(handoff, dict):
        raise ValueError("source and handoff must be objects")
    facts, facts_normalised = _compare(source.get("facts", []), handoff.get("facts", []), "facts")
    decisions, decisions_normalised = _compare(source.get("decisions", []), handoff.get("decisions", []), "decisions")
    gate = _gate(case.get("action", {}), policy)
    issues: list[dict[str, Any]] = []
    notes: set[tuple[str, str]] = set()
    for zone, comparison, normalised in (("facts", facts, facts_normalised), ("decisions", decisions, decisions_normalised)):
        for status in ("altered", "missing", "introduced"):
            for item_id in comparison[status]:
                issues.append({"code": f"{zone.upper()}_{status.upper()}", "item_id": item_id})
        notes.update(("UNICODE_NORMALIZATION_ONLY", item_id) for item_id in normalised)

    def classes(items: Any, zone: str) -> tuple[dict[str, dict[str, Any]], dict[str, str | None]]:
        indexed = _index(items, zone)
        out = {}
        for item_id, item in indexed.items():
            out[item_id], canonical = status_class(item.get("status"))
            if not canonical:
                notes.add(("NONCANONICAL_STATUS", item_id))
        return indexed, out

    source_facts, source_fact_class = classes(source.get("facts", []), "source.facts")
    handoff_facts, handoff_fact_class = classes(handoff.get("facts", []), "handoff.facts")
    # V1.4.1: sorted iteration. Set order used to depend on the process hash seed.
    for item_id in sorted(source_facts.keys() & handoff_facts.keys()):
        if source_fact_class[item_id] == "UNCERTAIN" and handoff_fact_class[item_id] == "FACT":
            issues.append({"code": "UNSUPPORTED_FACT_PROMOTION", "item_id": item_id})
    source_decisions, source_decision_class = classes(source.get("decisions", []), "source.decisions")
    handoff_decisions, handoff_decision_class = classes(handoff.get("decisions", []), "handoff.decisions")
    ledger: list[dict[str, Any]] = []
    for item_id in sorted(source_decisions):
        before, after = source_decisions[item_id], handoff_decisions.get(item_id)
        if source_decision_class[item_id] == "REVOKED":
            # V1.4.1: a revoked decision keeps a trace in the report whatever the handoff did with it.
            current = handoff_decision_class.get(item_id)
            if after is None:
                state = "NOT_CARRIED"
                issues.append({"code": "REVOKED_DECISION_TRACE_LOST", "item_id": item_id})
            elif current == "REVOKED":
                state = "CARRIED_AS_REVOKED"
            elif current == "ACTIVE":
                state = "REACTIVATED"
                issues.append({"code": "REACTIVATED_DECISION", "item_id": item_id})
            else:
                state = "STATUS_CHANGED"
                issues.append({"code": "REVOKED_STATUS_CHANGED", "item_id": item_id})
            ledger.append({"id": item_id, "source_status": before.get("status"), "handoff_state": state,
                           "source_item": before})
        if after is not None and not strict_equal(_nfc(before.get("authority")), _nfc(after.get("authority"))):
            issues.append({"code": "AUTHORITY_CHANGED", "item_id": item_id})
    action = case.get("action", {})
    ignored = sorted(k for k in POLICY_LIKE_KEYS if k in case or k in action)
    if ignored:
        notes.add(("CASE_POLICY_FIELD_IGNORED", ",".join(ignored)))
    clean = not issues and gate["result"] == "ALLOW_IN_SIMULATION"
    score = {
        "decision_exact_recall": _ratio(len(decisions["retained"]), decisions["source_total"]),
        "decision_exact_precision": _ratio(len(decisions["retained"]), decisions["handoff_total"]),
        "fact_exact_recall": _ratio(len(facts["retained"]), facts["source_total"]),
        "fact_exact_precision": _ratio(len(facts["retained"]), facts["handoff_total"]),
    }
    output: dict[str, Any] = {
        "report_schema": SCHEMA_VERSION, "case_id": case.get("case_id", "unnamed"),
        "verdict": "PASS" if clean else "FAIL", "facts": facts, "decisions": decisions,
        "approval_check": gate, "findings": issues,
        "advisories": [{"code": code, "item_id": item_id} for code, item_id in sorted(notes)],
        "revocation_ledger": ledger, "metrics": score,
        "input_sha256": digest(case), "policy_sha256": policy_digest(policy),
        "claims": ["Deterministic structural equality", "No action executed", "Synthetic scenario only"],
        "limitations": ["No semantic equivalence detection", "No LLM evaluation",
                        "No authenticated authorization", "Hashes do not prove truth, identity or completeness",
                        "Only supplied structured items can be evaluated",
                        "The approval requirement comes from an external policy; the approval record and the "
                        "action name are still supplied by the case and are not authenticated",
                        "Advisories and text profiles are lexical hints, not judgements about meaning"],
    }
    output["report_sha256"] = digest(output)
    return deepcopy(output)
