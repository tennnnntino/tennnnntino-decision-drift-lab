"""Shareable synthetic evidence report (V1.4): references, review state, comparator
findings, limitations and an input digest.

The report is data minimised by default: it cites spans and short excerpts, not
whole transcripts, and every text field passes a pattern-based redaction. The
digest lets a reader detect that a case changed relative to a copy they already
trust. It is not a signature and proves nothing about who wrote the case, when,
or whether it is true. docs/walkthrough.mjs builds the same report in the browser
(profile "portable", without the Python-only comparators).
"""
from __future__ import annotations

import re
from typing import Any

from .baselines import exact_text, rule_based, structured_transfer
from .core import digest
from .corpus import derive_findings
from .recovery import classify_recovery, revocation_ledger

REPORT_SCHEMA = "1.4.1"
MAX_EXCERPT = 200
PYTHON_ONLY = {"status": "PYTHON_ONLY"}

# ASCII-only classes and explicit lookarounds so Python and JavaScript agree exactly.
_REDACTIONS = (
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("URL", re.compile(r"(?<![A-Za-z0-9])https?://[^ \t\r\n<>\"']+")),
    ("TOKEN", re.compile(r"(?<![A-Za-z0-9_-])(?=[A-Za-z0-9_-]*[0-9])(?=[A-Za-z0-9_-]*[A-Za-z])[A-Za-z0-9_-]{24,}(?![A-Za-z0-9_-])")),
    ("NUMBER", re.compile(r"(?<![0-9])[0-9](?:[ -]?[0-9]){8,}(?![0-9])")),
)

LIMITATIONS = (
    "Synthetic fiction only; nothing here was observed in a real workflow.",
    "Labels are candidates until a human review is recorded; a recorded review is an unauthenticated text field.",
    "Exact-text and rule-based comparators do not understand meaning; a faithful paraphrase is reported as a difference.",
    "A reworded reactivation, a changed scope or a dropped condition can go unnoticed by every comparator here.",
    "The revocation ledger records exact-text observations; a reworded mention of a withdrawal is not recognised.",
    "The digest is a SHA-256 of the canonical case JSON. It is not a signature, timestamp or proof of authorship or truth.",
    "Redaction is pattern-based (email, URL, long token, long digit run). It is not a data-loss-prevention control.",
    "No model was called and no action was executed, approved or authorised.",
)


def redact(text: str) -> tuple[str, int]:
    total = 0
    for label, pattern in _REDACTIONS:
        text, count = pattern.subn(f"[REDACTED:{label}]", text)
        total += count
    return text, total


class _Redactor:
    def __init__(self) -> None:
        self.replacements = 0

    def clip(self, text: str) -> str:
        text, count = redact(text)
        self.replacements += count
        return text if len(text) <= MAX_EXCERPT else text[:MAX_EXCERPT] + "…"


def _ref(span: dict[str, Any] | None, red: _Redactor, with_turn: bool) -> dict[str, Any] | None:
    if span is None:
        return None
    out: dict[str, Any] = {}
    if with_turn:
        out["turn"] = span["turn"]
        out["role"] = span["role"]
    out.update(start_byte=span["start_byte"], end_byte=span["end_byte"], excerpt=red.clip(span["excerpt"]))
    return out


def build_report(case: dict[str, Any], split: str, profile: str = "full", include_text: bool = False) -> dict[str, Any]:
    if profile not in ("full", "portable"):
        raise ValueError("profile must be 'full' or 'portable'")
    red = _Redactor()
    samples = [{"item_id": i["item_id"], "kind": i["kind"], "source_status": i["source_status"],
                "authority_bearing": i["authority_bearing"], "label_outcome": i["handoff_outcome"],
                "source_refs": [_ref(e, red, True) for e in i["evidence"]],
                "handoff_ref": _ref(i["handoff_evidence"], red, False)} for i in case["items"]]
    introduced = [{"item_id": x["item_id"], "kind": x["kind"], "handoff_ref": _ref(x["handoff_evidence"], red, False)}
                  for x in case["introduced"]]
    b0 = exact_text(case)
    comparators: dict[str, Any] = {"label_findings": derive_findings(case),
                                   "exact_text": {"drift": b0["drift"], "not_verbatim": b0["detail"]["not_verbatim"]}}
    if profile == "full":
        b1, b2 = rule_based(case), structured_transfer(case)
        extraction: dict[str, Any] = {"status": "RUN", "method": "rule_based cue phrases and token overlap (B1)",
                                      "candidates": [{**c, "text": red.clip(c["text"])} for c in b1["detail"]["candidates"]]}
        comparators["rule_based"] = {"drift": b1["drift"], "codes": b1["codes"]}
        comparators["structured_transfer"] = {"drift": b2["drift"], "codes": b2["codes"]}
    else:
        extraction = dict(PYTHON_ONLY)
        comparators["rule_based"] = dict(PYTHON_ONLY)
        comparators["structured_transfer"] = dict(PYTHON_ONLY)
    recovery = classify_recovery(case)
    for sentence in recovery["unanchored_handoff_statements"]:
        sentence["text"] = red.clip(sentence["text"])
    ledger = revocation_ledger(case)
    for entry in ledger:
        entry["statement_ref"] = _ref(entry["statement_ref"], red, True)
        entry["revocation_refs"] = [_ref(e, red, True) for e in entry["revocation_refs"]]
    report: dict[str, Any] = {
        "report_type": "synthetic-handoff-evidence-report",
        "report_schema": REPORT_SCHEMA,
        "profile": profile,
        "synthetic_only": True,
        "case_ref": {"corpus": "handoff-corpus-v1.4", "split": split, "case_id": case["case_id"],
                     "domain": case["domain"], "title": red.clip(case["title"])},
        "input_digest": {"algorithm": "sha256", "value": digest(case),
                         "scope": "canonical JSON of the case object (sorted keys, compact separators, UTF-8)",
                         "is_signature": False},
        "review": {"label_state": case["label_state"], "state": case["review"]["state"],
                   "reviewer_label": case["review"]["reviewer_label"], "reviewed_on": case["review"]["reviewed_on"],
                   "authenticated": False},
        "samples": samples,
        "introduced": introduced,
        "candidate_extraction": extraction,
        "comparators": comparators,
        "recovery": recovery,
        "revocation_ledger": ledger,
        "limitations": list(LIMITATIONS),
        "attestation": {"signed": False,
                        "statement": "Unsigned. Compare input_digest with a copy you already trust; it cannot vouch for itself."},
    }
    if include_text:
        report["full_text"] = {"turns": [{"turn": t["turn"], "speaker": red.clip(t["speaker"]), "text": red.clip(t["text"])}
                                         for t in case["source"]["turns"]],
                               "handoff": red.clip(case["handoff"]["text"])}
    report["redaction"] = {"method": "pattern-based: EMAIL, URL, TOKEN, NUMBER", "replacements": red.replacements,
                           "full_text_included": include_text}
    return report


def render_markdown(report: dict[str, Any]) -> str:
    ref, review, rec = report["case_ref"], report["review"], report["recovery"]
    lines = [f"# Synthetic handoff evidence report: {ref['case_id']}", "",
             f"*{ref['title']}* ({ref['corpus']}, split `{ref['split']}`, domain `{ref['domain']}`)", "",
             "**Synthetic fiction. Unsigned. Not evidence about any real workflow.**", "",
             f"- Input digest (SHA-256, not a signature): `{report['input_digest']['value']}`",
             f"- Label state: `{review['label_state']}`; review: `{review['state']}`"
             f"{' by ' + review['reviewer_label'] + ' on ' + review['reviewed_on'] if review['reviewer_label'] else ''}"
             " (unauthenticated)",
             f"- Redaction replacements: {report['redaction']['replacements']}", "",
             "## What survived verbatim", ""]
    by_id = {s["item_id"]: s for s in report["samples"]}
    recoverable = [i for i in rec["items"] if i["recovery"] == "RECOVERABLE_VERBATIM"]
    for item in recoverable:
        statement = next(r for r in by_id[item["item_id"]]["source_refs"] if r["role"] == "statement")
        lines.append(f"- `{item['item_id']}` ({item['kind']}): \"{statement['excerpt']}\" "
                     f"[turn {statement['turn']}, bytes {statement['start_byte']}-{statement['end_byte']}]")
    if not recoverable:
        lines.append("- Nothing.")
    lines += ["", "## What the owner must reconfirm", ""]
    for item in rec["items"]:
        if item["recovery"] == "RECOVERABLE_VERBATIM":
            continue
        statement = next(r for r in by_id[item["item_id"]]["source_refs"] if r["role"] == "statement")
        lines.append(f"- [ ] `{item['item_id']}` ({item['kind']}, {item['source_status']}): \"{statement['excerpt']}\" "
                     f"[turn {statement['turn']}]: {', '.join(item['reasons'])}")
    lines += ["", "## Revoked decisions (trace kept whatever the handoff says)", ""]
    for entry in report["revocation_ledger"]:
        st = entry["statement_ref"]
        withdrawn = "; ".join(f'"{r["excerpt"]}" [turn {r["turn"]}]' for r in entry["revocation_refs"])
        lines.append(f'- `{entry["item_id"]}`: "{st["excerpt"]}" [turn {st["turn"]}, bytes {st["start_byte"]}-{st["end_byte"]}], '
                     f'withdrawn by {withdrawn}. Handoff: {entry["trace"]}.'
                     + (f' **Ambiguity:** {entry["ambiguity"]}' if entry["ambiguity"] else ""))
    if not report["revocation_ledger"]:
        lines.append("- None in this case.")
    lines += ["", "## Handoff statements with no verbatim source anchor", ""]
    lines += [f"- [ ] \"{s['text']}\" [handoff bytes {s['start_byte']}-{s['end_byte']}]"
              for s in rec["unanchored_handoff_statements"]] or ["- None."]
    comp = report["comparators"]
    lines += ["", "## Comparator findings", "",
              f"- Candidate label findings: {', '.join(comp['label_findings']) or 'none'}",
              f"- Exact text (B0): drift={comp['exact_text']['drift']}; not verbatim: "
              f"{', '.join(comp['exact_text']['not_verbatim']) or 'none'}"]
    for key, name in (("rule_based", "Rule-based (B1)"), ("structured_transfer", "Structured transfer (B2)")):
        entry = comp[key]
        lines.append(f"- {name}: " + ("not run in this profile" if "status" in entry
                                      else f"drift={entry['drift']}; {', '.join(entry['codes']) or 'none'}"))
    lines += ["", "## Limitations", ""] + [f"- {text}" for text in report["limitations"]]
    return "\n".join(lines) + "\n"


def render_checklist(report: dict[str, Any]) -> str:
    """Plain-text reconfirmation checklist for the person resuming the work."""
    rec, ref = report["recovery"], report["case_ref"]
    by_id = {s["item_id"]: s for s in report["samples"]}

    def statement(item_id: str) -> dict[str, Any]:
        return next(r for r in by_id[item_id]["source_refs"] if r["role"] == "statement")

    lines = [f"RECOVERY CHECKLIST  {ref['case_id']}  ({ref['title']})",
             f"labels: {report['review']['label_state']} / review: {report['review']['state']}  (synthetic, unsigned)", "",
             f"CARRY ON ({rec['summary']['recoverable_verbatim']}): present word for word in the handoff"]
    lines += [f"  + {i['item_id']}  \"{statement(i['item_id'])['excerpt']}\"  [turn {i['source_ref']['turn']}]"
              for i in rec["items"] if i["recovery"] == "RECOVERABLE_VERBATIM"]
    lines += ["", f"ASK THE OWNER ({rec['summary']['owner_reconfirmation_required']}):"]
    lines += [f"  ? {i['item_id']}  \"{statement(i['item_id'])['excerpt']}\"  [turn {i['source_ref']['turn']}]  "
              f"{', '.join(i['reasons'])}" for i in rec["items"] if i["recovery"] != "RECOVERABLE_VERBATIM"]
    lines += ["", f"UNANCHORED HANDOFF STATEMENTS ({rec['summary']['unanchored_handoff_statements']}): "
                  "no word-for-word source; treat as unverified"]
    lines += [f"  ! \"{s['text']}\"" for s in rec["unanchored_handoff_statements"]]
    lines += ["", f"WITHDRAWN IN THE CONVERSATION ({len(report['revocation_ledger'])}): never act on these; the trace is kept here"]
    lines += [f'  x {e["item_id"]}  "{e["statement_ref"]["excerpt"]}"  [turn {e["statement_ref"]["turn"]}]  handoff: {e["trace"]}'
              + ("  AMBIGUOUS: not carried" if e["ambiguity"] else "") for e in report["revocation_ledger"]]
    lines += ["", "Exact-text check only. It cannot judge meaning and cannot authorise anything."]
    return "\n".join(lines) + "\n"
