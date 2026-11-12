"""Synthetic unstructured-handoff corpus: loading, validation and review gating (V1.4).

A label is a CANDIDATE until a human review is recorded in the case. A recorded
review is itself only an unauthenticated text field: this module can tell whether
a review was *recorded*, never whether it truly happened or who performed it.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .intake import parse_json_strict
from .schema import validate

ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = ROOT / "research" / "handoff-corpus-v1_4"
SCHEMA_PATH = ROOT / "contracts" / "handoff-corpus.schema.json"
# "heldout-human" holds blind human labels for the held-out conversations; "independent-heldout" holds cases
# written and labelled by someone else. Both are optional and absent until a person provides them.
SPLITS = {"dev": "dev.json", "heldout": "heldout.json", "heldout-human": "heldout-human.json",
          "independent-heldout": "independent-heldout.json"}
REVIEWED_STATES = ("HUMAN_REVIEWED", "HUMAN_AMENDED")

OUTCOME_CODES = {
    "PRESERVED_VERBATIM": (), "PRESERVED_PARAPHRASE": (), "NOT_CARRIED_OK": (),
    "ALTERED": ("{K}_ALTERED",), "OMITTED": ("{K}_MISSING",),
    "REACTIVATED": ("DECISIONS_ALTERED", "REACTIVATED_DECISION"),
    "PROMOTED": ("FACTS_ALTERED", "UNSUPPORTED_FACT_PROMOTION"),
    "AUTHORITY_CHANGED": ("DECISIONS_ALTERED", "AUTHORITY_CHANGED"),
}


class CorpusError(ValueError):
    """The corpus file violates the schema or an internal consistency rule."""


def _zone(kind: str) -> str:
    return "DECISIONS" if kind == "decision" else "FACTS"


def derive_findings(case: dict[str, Any]) -> list[str]:
    """Case-level finding codes implied by the per-item outcomes (V1.3 code vocabulary)."""
    codes: set[str] = set()
    for item in case["items"]:
        codes.update(code.replace("{K}", _zone(item["kind"])) for code in OUTCOME_CODES[item["handoff_outcome"]])
    for extra in case["introduced"]:
        codes.add(f"{_zone(extra['kind'])}_INTRODUCED")
    return sorted(codes)


def derive_ambiguities(case: dict[str, Any]) -> list[str]:
    """Advisory flags that are not counted as drift (V1.4.1).

    A revoked decision that the handoff simply does not carry keeps the outcome name
    NOT_CARRIED_OK for file stability, but it is no longer called benign without
    qualification: the trace of the withdrawal is lost for the next reader.
    """
    lost = any(item["handoff_outcome"] == "NOT_CARRIED_OK" for item in case["items"])
    return ["REVOKED_DECISION_TRACE_LOST"] if lost else []


def statement_of(item: dict[str, Any]) -> dict[str, Any]:
    return next(e for e in item["evidence"] if e["role"] == "statement")


def is_human_reviewed(case: dict[str, Any]) -> bool:
    return case["review"]["state"] in REVIEWED_STATES


def _slice(text: str, span: dict[str, Any]) -> str | None:
    raw = text.encode("utf-8")
    if not 0 <= span["start_byte"] < span["end_byte"] <= len(raw):
        return None
    try:
        return raw[span["start_byte"]:span["end_byte"]].decode("utf-8")
    except UnicodeDecodeError:
        return None


def check_case(case: dict[str, Any]) -> list[str]:
    """Consistency rules the schema cannot express. Returns human-readable problems."""
    problems: list[str] = []
    cid = case["case_id"]
    turns = case["source"]["turns"]
    if [t["turn"] for t in turns] != list(range(1, len(turns) + 1)):
        problems.append(f"{cid}: turns must be numbered 1..n in order")
    by_turn = {t["turn"]: t["text"] for t in turns}
    handoff = case["handoff"]["text"]
    ids = [i["item_id"] for i in case["items"]] + [i["item_id"] for i in case["introduced"]]
    if len(ids) != len(set(ids)):
        problems.append(f"{cid}: duplicate item_id")
    for item in case["items"]:
        where = f"{cid}/{item['item_id']}"
        roles = [e["role"] for e in item["evidence"]]
        if roles.count("statement") != 1:
            problems.append(f"{where}: exactly one evidence span must have role 'statement'")
            continue
        for ev in item["evidence"]:
            if ev["turn"] not in by_turn or _slice(by_turn[ev["turn"]], ev) != ev["excerpt"]:
                problems.append(f"{where}: evidence span does not reproduce its excerpt (turn {ev['turn']})")
        kind, status, outcome = item["kind"], item["source_status"], item["handoff_outcome"]
        if (kind == "decision") != (status in ("ACTIVE", "REVOKED")):
            problems.append(f"{where}: status {status} does not fit kind {kind}")
        if status == "REVOKED" and "revocation" not in roles:
            problems.append(f"{where}: REVOKED needs a 'revocation' evidence span")
        if status == "TO_CONFIRM" and "qualification" not in roles:
            problems.append(f"{where}: TO_CONFIRM needs a 'qualification' evidence span")
        hev = item["handoff_evidence"]
        if outcome in ("OMITTED", "NOT_CARRIED_OK"):
            if hev is not None:
                problems.append(f"{where}: {outcome} must not cite handoff evidence")
        elif hev is None or _slice(handoff, hev) != hev["excerpt"]:
            problems.append(f"{where}: handoff evidence missing or span does not reproduce its excerpt")
        elif outcome == "PRESERVED_VERBATIM" and hev["excerpt"] != statement_of(item)["excerpt"]:
            problems.append(f"{where}: PRESERVED_VERBATIM requires identical excerpts")
        if outcome == "REACTIVATED" and status != "REVOKED":
            problems.append(f"{where}: REACTIVATED requires a REVOKED decision")
        if outcome == "NOT_CARRIED_OK" and status != "REVOKED":
            problems.append(f"{where}: NOT_CARRIED_OK requires a REVOKED decision")
        if outcome == "PROMOTED" and status != "TO_CONFIRM":
            problems.append(f"{where}: PROMOTED requires a TO_CONFIRM fact")
        if outcome == "AUTHORITY_CHANGED":
            if not item["authority"] or not item["handoff_authority"] or item["authority"] == item["handoff_authority"]:
                problems.append(f"{where}: AUTHORITY_CHANGED needs two different authority labels")
        elif item["handoff_authority"] is not None:
            problems.append(f"{where}: handoff_authority is only used with AUTHORITY_CHANGED")
    for extra in case["introduced"]:
        if _slice(handoff, extra["handoff_evidence"]) != extra["handoff_evidence"]["excerpt"]:
            problems.append(f"{cid}/{extra['item_id']}: introduced span does not reproduce its excerpt")
    if case["expected_findings"] != derive_findings(case):
        problems.append(f"{cid}: expected_findings disagree with the item outcomes")
    if case["expected_drift"] != bool(case["expected_findings"]):
        problems.append(f"{cid}: expected_drift disagrees with expected_findings")
    review, reviewed = case["review"], is_human_reviewed(case)
    if reviewed != (case["label_state"] == "HUMAN_REVIEWED_UNAUTHENTICATED"):
        problems.append(f"{cid}: label_state and review.state disagree")
    if reviewed and not (review["reviewer_label"] and review["reviewed_on"]):
        problems.append(f"{cid}: a recorded review needs reviewer_label and reviewed_on")
    if review["state"] == "NOT_REVIEWED" and (review["reviewer_label"] or review["reviewed_on"]):
        problems.append(f"{cid}: NOT_REVIEWED must not carry reviewer fields")
    return problems


def load_bytes(raw: bytes) -> dict[str, Any]:
    """Strict intake -> schema -> consistency. Raises IntakeError or CorpusError."""
    doc = parse_json_strict(raw)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = validate(doc, schema)
    if errors:
        shown = "; ".join(f"{e['path']} [{e['keyword']}]" for e in errors[:5])
        raise CorpusError(f"schema violations ({len(errors)}): {shown}")
    problems: list[str] = []
    seen: set[str] = set()
    for case in doc["cases"]:
        if case["case_id"] in seen:
            problems.append(f"duplicate case_id {case['case_id']}")
        seen.add(case["case_id"])
        problems.extend(check_case(case))
    if problems:
        raise CorpusError(f"consistency problems ({len(problems)}): " + "; ".join(problems[:5]))
    return doc


def load_split(split: str) -> dict[str, Any] | None:
    """Load a packaged split; None when the (optional) file is not provided."""
    if split not in SPLITS:
        raise CorpusError(f"unknown split: {split}")
    path = CORPUS_DIR / SPLITS[split]
    if not path.is_file():
        return None
    doc = load_bytes(path.read_bytes())
    if doc["split"] != split:
        raise CorpusError(f"{path.name} declares split {doc['split']!r}")
    return doc


def find_case(case_id: str) -> tuple[str, dict[str, Any]]:
    for split in SPLITS:
        doc = load_split(split)
        for case in (doc or {}).get("cases", []):
            if case["case_id"] == case_id:
                return split, case
    raise CorpusError(f"case not found: {case_id}")


def review_sheet(doc: dict[str, Any], blind: bool = False) -> str:
    """Markdown sheet for a human labeller. ``blind`` hides the candidate labels."""
    out = [f"# Review sheet: {doc['corpus']} / {doc['split']}", "",
           "Synthetic fiction. Spans are UTF-8 byte offsets into the quoted turn or handoff text.",
           "Label independently first (blind sheet), then compare with the candidates. Record the result in "
           "the case's `review` object; that record is an unauthenticated note, not a signature.", ""]
    for case in doc["cases"]:
        # A blind sheet withholds the title: titles describe the candidate judgement.
        out += [f"## {case['case_id']}" + ("" if blind else f": {case['title']}"), "", "**Source conversation**", ""]
        out += [f"{t['turn']}. **{t['speaker']}:** {t['text']}" for t in case["source"]["turns"]]
        out += ["", "**Handoff note**", "", f"> {case['handoff']['text']}", ""]
        if blind:
            out += ["**Your labels** (decisions, facts, uncertainties, authority constraints; what happened to each "
                    "in the handoff; anything introduced):", "", "- ", ""]
            continue
        out += [f"**Candidate labels** (state: {case['label_state']}, review: {case['review']['state']})", ""]
        for item in case["items"]:
            st = statement_of(item)
            line = (f"- `{item['item_id']}` {item['kind']} / {item['source_status']}"
                    f"{' / authority: ' + item['authority'] if item['authority'] else ''}"
                    f"{' / authority-bearing' if item['authority_bearing'] else ''}: "
                    f"turn {st['turn']} bytes {st['start_byte']}-{st['end_byte']} \"{st['excerpt']}\" "
                    f"-> **{item['handoff_outcome']}**")
            if item["handoff_evidence"]:
                line += f" (handoff: \"{item['handoff_evidence']['excerpt']}\")"
            out.append(line)
        out += [f"- introduced `{x['item_id']}` {x['kind']}: \"{x['handoff_evidence']['excerpt']}\""
                for x in case["introduced"]]
        out += ["", f"Candidate findings: {', '.join(case['expected_findings']) or 'none'}",
                f"Ambiguity flags (not counted as drift): {', '.join(derive_ambiguities(case)) or 'none'}",
                f"Labelling note: {case['labeling_note']}", "", "Reviewer decision: [ ] agree  [ ] amend  [ ] dispute", ""]
    return "\n".join(out) + "\n"
