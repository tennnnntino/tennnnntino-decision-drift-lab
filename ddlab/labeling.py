"""Human labelling support (V1.4.1): blind forms, a form compiler and an agreement report.

A labeller works on a *form*: conversations and handoff notes with empty label
slots, quoting passages instead of counting bytes. ``compile_form`` turns a
completed form into a corpus file with computed spans and a recorded review.

Nothing here can verify that a person filled the form, who they are, or that
their independence declaration is true. The compiler refuses forms that declare
themselves non-blind; it cannot detect a false declaration.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from . import corpus

FORM_VERSION = "handoff-label-form-v1"
TARGETS = ("heldout-human", "independent-heldout")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_ROLE_FIELDS = (("superseded", "superseded"), ("revocation", "revocation"), ("qualification", "qualification"))

INSTRUCTIONS = [
    "Label alone, before looking at any candidate label, review sheet with labels, or the baseline code.",
    "For each case list what someone would act on: decisions, constraints, facts that drive an action, open uncertainties.",
    "Quote passages exactly as written. A quote must occur exactly once in its turn (or in the handoff note); lengthen it if needed.",
    "kind: decision | fact. status: ACTIVE or REVOKED for decisions, FACT or TO_CONFIRM for facts.",
    "authority: the person or role the conversation names as deciding, or null. authority_bearing: true when the item says who may approve or forbids acting without approval.",
    "statement: the current wording. superseded: earlier wording that was corrected. revocation: the words that withdrew it. qualification: the hedge that makes a fact uncertain.",
    "outcome: PRESERVED_VERBATIM | PRESERVED_PARAPHRASE | NOT_CARRIED_OK (revoked and simply absent) | ALTERED | OMITTED | REACTIVATED | PROMOTED | AUTHORITY_CHANGED.",
    "handoff_quote: the passage of the note that carries, changes or contradicts the item; null for OMITTED and NOT_CARRIED_OK.",
    "introduced: statements in the note that nothing in the conversation supports.",
    "Fill in labeller.label (a name or pseudonym), labeller.date (YYYY-MM-DD) and all three independence answers with true or false.",
]


class LabelFormError(ValueError):
    """The form is incomplete, not blind by its own declaration, or does not match the source text."""


def _text_digest(cases: list[dict[str, Any]]) -> str:
    """Digest of the text a labeller sees (ids, speakers, turns, note), independent of any label."""
    view = [{"case_id": c["case_id"], "turns": [[t["speaker"], t["text"]] for t in c["source"]["turns"]],
             "handoff": c["handoff"]["text"]} for c in sorted(cases, key=lambda c: c["case_id"])]
    canonical = json.dumps(view, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _labeller_slot() -> dict[str, Any]:
    return {"label": None, "date": None,
            "independence": {"has_read_baseline_code": None, "has_seen_candidate_labels": None, "wrote_these_cases": None}}


def blind_form(doc: dict[str, Any]) -> dict[str, Any]:
    """Form for labelling an existing split blind. Titles are withheld: they describe the candidate judgement."""
    return {
        "form": FORM_VERSION, "target_split": "heldout-human", "source_split": doc["split"],
        "source_text_sha256": _text_digest(doc["cases"]),
        "labeller": _labeller_slot(), "instructions": INSTRUCTIONS,
        "cases": [{"case_id": c["case_id"],
                   "turns": [{"turn": t["turn"], "speaker": t["speaker"], "text": t["text"]} for t in c["source"]["turns"]],
                   "handoff": c["handoff"]["text"], "items": [], "introduced": [], "note": ""} for c in doc["cases"]],
    }


def independent_template() -> dict[str, Any]:
    """Empty form for writing and labelling new, independent cases."""
    return {
        "form": FORM_VERSION, "target_split": "independent-heldout", "source_split": None, "source_text_sha256": None,
        "data_rights": None,
        "labeller": _labeller_slot(),
        "instructions": INSTRUCTIONS + [
            "Write at least 20 new fictional cases yourself. No real people, organisations, conversations or customer data.",
            "Each case needs a case_id (letters, digits, - or _), a domain, a title, 3 to 8 turns and a handoff note.",
            "Aim for roughly one third faithful handoffs (verbatim and paraphrased) and two thirds with a real change.",
            "State in data_rights that the text is your own fiction and may be used in this corpus.",
            "Replace the placeholder case below; a case_id starting with EXAMPLE is refused by the compiler.",
        ],
        "cases": [{
            "case_id": "EXAMPLE-01", "domain": "replace-me", "title": "Replace me",
            "turns": [{"turn": 1, "speaker": "Name", "text": "Replace with your own invented conversation."},
                      {"turn": 2, "speaker": "Assistant", "text": "Replace."}],
            "handoff": "Replace with the handoff note.",
            "items": [{"item_id": "D1", "kind": "decision", "status": "ACTIVE", "authority": None, "authority_bearing": False,
                       "statement": {"turn": 1, "quote": "Replace"}, "superseded": [], "revocation": [], "qualification": [],
                       "outcome": "OMITTED", "handoff_quote": None, "handoff_authority": None}],
            "introduced": [{"item_id": "X1", "kind": "fact", "handoff_quote": "Replace", "note": ""}],
            "note": "",
        }],
    }


def _span(text: str, quote: Any, where: str) -> dict[str, Any]:
    if not isinstance(quote, str) or not quote:
        raise LabelFormError(f"{where}: a quote is required")
    count = text.count(quote)
    if count != 1:
        raise LabelFormError(f"{where}: the quote occurs {count} times; it must occur exactly once (lengthen or correct it)")
    start = text.index(quote)
    return {"start_byte": len(text[:start].encode("utf-8")), "end_byte": len(text[:start + len(quote)].encode("utf-8")),
            "excerpt": quote}


def _labeller(form: dict[str, Any], target: str) -> tuple[str, str, str]:
    who = form["labeller"]
    label, date, answers = who["label"], who["date"], who["independence"]
    if not isinstance(label, str) or not label.strip() or len(label) > 60:
        raise LabelFormError("labeller.label must be a name or pseudonym (1 to 60 characters)")
    if not isinstance(date, str) or not _DATE.fullmatch(date):
        raise LabelFormError("labeller.date must be YYYY-MM-DD")
    keys = ("has_read_baseline_code", "has_seen_candidate_labels", "wrote_these_cases")
    if any(not isinstance(answers.get(k), bool) for k in keys):
        raise LabelFormError("answer all three independence questions with true or false")
    if answers["has_read_baseline_code"] or answers["has_seen_candidate_labels"]:
        raise LabelFormError("this form declares the labels are not blind; they cannot be compiled as blind labels")
    if answers["wrote_these_cases"] != (target == "independent-heldout"):
        raise LabelFormError("wrote_these_cases must be true for independent-heldout and false for heldout-human")
    declaration = ("Self-declared by the labeller, unauthenticated: has not read the baseline code; has not seen the "
                   "candidate labels; " + ("wrote these cases." if answers["wrote_these_cases"] else "did not write these cases."))
    return label.strip(), date, declaration


def compile_form(form: Any) -> dict[str, Any]:
    """Turn a completed label form into a validated corpus document. Raises LabelFormError."""
    try:
        return _compile(form)
    except (KeyError, TypeError, AttributeError, IndexError) as exc:
        raise LabelFormError(f"form is malformed or incomplete: {type(exc).__name__}: {exc}") from None


def _compile(form: Any) -> dict[str, Any]:
    if not isinstance(form, dict) or form.get("form") != FORM_VERSION:
        raise LabelFormError(f"not a {FORM_VERSION} document")
    target = form["target_split"]
    if target not in TARGETS:
        raise LabelFormError(f"target_split must be one of {', '.join(TARGETS)}")
    label, date, declaration = _labeller(form, target)
    source_by_id: dict[str, dict[str, Any]] = {}
    if target == "heldout-human":
        source = corpus.load_split(form["source_split"]) if form["source_split"] in ("dev", "heldout") else None
        if source is None:
            raise LabelFormError("heldout-human forms must name the packaged source split they were generated from")
        source_by_id = {c["case_id"]: c for c in source["cases"]}
        rights, authoring = source["provenance"]["data_rights"], "FICTIONAL_MODEL_DRAFTED_TEXT_HUMAN_LABELS"
    else:
        rights, authoring = form["data_rights"], "FICTIONAL_HUMAN_WRITTEN_AND_LABELLED"
        if not isinstance(rights, str) or len(rights.strip()) < 20:
            raise LabelFormError("data_rights must state that the text is the author's own fiction and may be used here")
        if len(form["cases"]) < 20:
            raise LabelFormError(f"an independent held-out set needs at least 20 cases; this form has {len(form['cases'])}")
    cases = []
    for entry in form["cases"]:
        cid = entry["case_id"]
        if isinstance(cid, str) and cid.upper().startswith("EXAMPLE"):
            raise LabelFormError("replace the EXAMPLE placeholder case")
        turns = [{"turn": t["turn"], "speaker": t["speaker"], "text": t["text"]} for t in entry["turns"]]
        texts = {t["turn"]: t["text"] for t in turns}
        handoff = entry["handoff"]
        if not entry["items"]:
            raise LabelFormError(f"{cid}: no item was labelled")
        items = []
        for item in entry["items"]:
            where = f"{cid}/{item['item_id']}"
            evidence = [{"turn": item["statement"]["turn"], "role": "statement",
                         **_span(texts[item["statement"]["turn"]], item["statement"]["quote"], f"{where}/statement")}]
            for field, role in _ROLE_FIELDS:
                for ref in item.get(field) or []:
                    evidence.append({"turn": ref["turn"], "role": role, **_span(texts[ref["turn"]], ref["quote"], f"{where}/{field}")})
            quote = item["handoff_quote"]
            if item["outcome"] == "PRESERVED_VERBATIM" and quote is None:
                quote = item["statement"]["quote"]
            items.append({
                "item_id": item["item_id"], "kind": item["kind"], "source_status": item["status"],
                "authority": item["authority"], "authority_bearing": item["authority_bearing"], "evidence": evidence,
                "handoff_outcome": item["outcome"],
                "handoff_evidence": None if quote is None else _span(handoff, quote, f"{where}/handoff_quote"),
                "handoff_authority": item.get("handoff_authority"),
            })
        introduced = [{"item_id": x["item_id"], "kind": x["kind"], "note": x.get("note") or "",
                       "handoff_evidence": _span(handoff, x["handoff_quote"], f"{cid}/{x['item_id']}/handoff_quote")}
                      for x in entry["introduced"]]
        base = source_by_id.get(cid)
        case = {
            "case_id": cid, "domain": base["domain"] if base else entry["domain"],
            "title": base["title"] if base else entry["title"],
            "source": {"turns": turns}, "handoff": {"text": handoff}, "items": items, "introduced": introduced,
            "expected_findings": [], "expected_drift": False,
            "label_state": "HUMAN_REVIEWED_UNAUTHENTICATED",
            "review": {"state": "HUMAN_REVIEWED", "reviewer_label": label, "reviewed_on": date,
                       "note": "Blind labels compiled from a label form."},
            "labeling_note": entry.get("note") or "",
        }
        case["expected_findings"] = corpus.derive_findings(case)
        case["expected_drift"] = bool(case["expected_findings"])
        cases.append(case)
    if target == "heldout-human":
        if sorted(c["case_id"] for c in cases) != sorted(source_by_id):
            raise LabelFormError("the form must contain exactly the cases of its source split")
        if _text_digest(cases) != _text_digest(list(source_by_id.values())) or form["source_text_sha256"] != _text_digest(cases):
            raise LabelFormError("conversation or handoff text differs from the packaged source split")
    doc = {"corpus": "handoff-corpus-v1.4", "corpus_schema": "1.0", "split": target,
           "provenance": {"authoring": authoring, "label_state": "HUMAN_LABELLED_BLIND_UNAUTHENTICATED",
                          "human_review": "RECORDED_BY_SELF_DECLARATION", "data_rights": rights.strip(),
                          "independence": declaration},
           "cases": cases}
    try:
        return corpus.load_bytes(json.dumps(doc, ensure_ascii=False).encode("utf-8"))
    except ValueError as exc:
        raise LabelFormError(f"compiled labels are not a valid corpus: {exc}") from None


def _overlap(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return a["turn"] == b["turn"] and a["start_byte"] < b["end_byte"] and b["start_byte"] < a["end_byte"]


def agreement(candidate: dict[str, Any], human: dict[str, Any]) -> dict[str, Any]:
    """Compare two labellings of the same cases. Agreement is not accuracy: neither side is ground truth."""
    left = {c["case_id"]: c for c in candidate["cases"]}
    right = {c["case_id"]: c for c in human["cases"]}
    if sorted(left) != sorted(right):
        raise LabelFormError("both files must label the same cases")
    table = {"both_drift": 0, "candidate_only_drift": 0, "human_only_drift": 0, "both_benign": 0}
    codes = {"both": 0, "candidate_only": 0, "human_only": 0}
    items = {"matched": 0, "same_kind": 0, "same_status": 0, "same_outcome": 0, "candidate_unmatched": 0, "human_unmatched": 0}
    rows = []
    for cid in sorted(left):
        a, b = left[cid], right[cid]
        key = ("both_drift" if a["expected_drift"] and b["expected_drift"] else "candidate_only_drift" if a["expected_drift"]
               else "human_only_drift" if b["expected_drift"] else "both_benign")
        table[key] += 1
        ca, cb = set(a["expected_findings"]), set(b["expected_findings"])
        codes["both"] += len(ca & cb)
        codes["candidate_only"] += len(ca - cb)
        codes["human_only"] += len(cb - ca)
        used: set[int] = set()
        differing = []
        for item in a["items"]:
            sa = corpus.statement_of(item)
            match = next((i for i, other in enumerate(b["items"])
                          if i not in used and _overlap(sa, corpus.statement_of(other))), None)
            if match is None:
                items["candidate_unmatched"] += 1
                continue
            used.add(match)
            other = b["items"][match]
            items["matched"] += 1
            items["same_kind"] += item["kind"] == other["kind"]
            items["same_status"] += item["source_status"] == other["source_status"]
            items["same_outcome"] += item["handoff_outcome"] == other["handoff_outcome"]
            if item["handoff_outcome"] != other["handoff_outcome"]:
                differing.append({"candidate_item": item["item_id"], "human_item": other["item_id"],
                                  "candidate_outcome": item["handoff_outcome"], "human_outcome": other["handoff_outcome"]})
        items["human_unmatched"] += len(b["items"]) - len(used)
        rows.append({"case_id": cid, "case_level": key, "candidate_findings": sorted(ca), "human_findings": sorted(cb),
                     "outcome_differences": differing})
    n = len(left)
    agree = table["both_drift"] + table["both_benign"]
    p_candidate = (table["both_drift"] + table["candidate_only_drift"]) / n
    p_human = (table["both_drift"] + table["human_only_drift"]) / n
    expected = p_candidate * p_human + (1 - p_candidate) * (1 - p_human)
    kappa = None if expected >= 1 else round((agree / n - expected) / (1 - expected), 4)
    return {
        "report": "label-agreement-v1.4",
        "meaning": "Agreement between model-drafted candidate labels and one self-declared human labeller. "
                   "Not accuracy: neither side is ground truth, and one labeller gives no inter-human agreement.",
        "cases": n, "case_level_drift": table, "case_level_agreement": {"agree": agree, "of": n},
        "cohen_kappa_case_level": kappa,
        "kappa_note": "null when chance agreement is 1; unstable for small n. Report the table, not only kappa.",
        "finding_codes": codes, "items": items, "per_case": rows,
        "human_review": {"reviewers": sorted({c["review"]["reviewer_label"] or "" for c in human["cases"]}),
                         "authenticated": False},
    }
