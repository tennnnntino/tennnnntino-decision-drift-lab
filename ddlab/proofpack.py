"""ProofPack V1.4 (build V1.4.1): one evidence row per result.

Every row answers the same eight questions:

    source            where the passage is (file, digest, case, turn, byte span)
    exact_passage     the words themselves
    decision          what the passage is taken to be, and by whom
    detected_change   what happened to it in the handoff, and who says so
    rules_applied     the numbered rules that produced the result
    result            the outcome
    uncertainty       what the method cannot tell
    human_validation  whether a person has confirmed it

The pack is generated, deterministic and synthetic. It is unsigned: digests let a
reader detect change against a copy they already trust and prove nothing else.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from . import baselines, corpus
from .evidence import redact
from .policy import load_policy, policy_digest
from .recovery import classify_recovery, revocation_ledger, split_sentences

ROOT = Path(__file__).resolve().parents[1]
PROOFPACK_JSON = ROOT / "research" / "proofpack-v1_4.json"
PROOFPACK_MD = ROOT / "research" / "PROOFPACK_V1_4.md"
VECTORS = ROOT / "contracts" / "purple-v1_4-vectors.json"
MAX_PASSAGE = 300

RULES = {
    "R-EXACT-1": "A labelled source statement counts as carried only if it appears byte for byte in the handoff note.",
    "R-EXACT-2": "Structured items are compared exactly; a changed text gets a lexical profile (shared words, negation, numbers) as a triage hint, never as a verdict.",
    "R-REVOKED-1": "A decision withdrawn in the conversation is never carried forward; it always goes to the owner.",
    "R-REVOKED-2": "A withdrawn decision keeps a ledger entry with its source spans whatever the handoff says; if the handoff drops it, that is flagged.",
    "R-UNCERTAIN-1": "A statement that was unconfirmed in the conversation stays unconfirmed.",
    "R-AUTH-1": "A statement that says who may approve, or forbids acting without approval, is not transferable by text.",
    "R-SUPERSEDED-1": "If an earlier, corrected wording appears in the handoff, the item goes to the owner.",
    "R-INTRO-1": "A handoff statement without a supporting source statement is reported: as introduced by the label, as unanchored by the exact check.",
    "R-POLICY-1": "Whether a simulated human approval is required is decided by the external policy. A case can ask for more caution, never for less.",
    "R-POLICY-2": "The policy matches the action name and scope the case declares; the lab does not verify that declaration.",
    "R-APPROVAL-1": "A simulated approval counts only if it is explicit, typed HUMAN, and names both the scope and the action. It is never authentication.",
    "R-TYPE-1": "Values are compared as JSON values: a boolean never equals a number; an absent authority equals an explicit null.",
    "R-NUM-1": "Numbers that are non-finite or integers beyond 2^53-1 are rejected, because two runtimes cannot both represent them.",
    "R-NFC-1": "Canonically equivalent Unicode (NFC versus NFD) is the same text and the same identifier; compatibility forms are not.",
    "R-STATUS-1": "Status tokens are matched after trimming, ASCII upper-casing and separator unification, through a fixed alias table.",
    "R-ORDER-1": "Reports are deterministic: sorted identifiers, code-point order, integer half-up rounding, in both runtimes.",
    "R-INPUT-1": "Malformed structure (arrays or explicit nulls where objects are required) is rejected, not defaulted.",
    "R-B0": "Baseline B0 flags a case when any labelled, non-revoked statement is not verbatim in the note.",
    "R-B1": "Baseline B1 flags a case from cue phrases and word overlap; thresholds were tuned on the dev split only.",
    "R-B2": "Baseline B2 runs the structured comparer on an encoding derived from the labels.",
    "R-LABEL-1": "A label is a candidate until a review is recorded; a recorded review is an unauthenticated text field.",
}

_U_CANDIDATE = "The label (kind, status, outcome) is a model-drafted candidate that no person has reviewed."
_U_NOT_VERBATIM = "Exact matching cannot tell whether the statement is missing, changed or only reworded."
_U_VERBATIM = "Verbatim presence does not show that the surrounding text left its meaning intact."
_U_REVOKED = "A reworded reactivation, or a reworded mention of the withdrawal, is not recognised."
_U_BASELINE = "Baselines do not understand meaning; agreement or disagreement with a candidate label is not accuracy."
_U_PROBE = "Synthetic probe on a structured fixture. The simulated approval authenticates nobody."


def _sha256_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _clip(text: str) -> str:
    text = redact(text)[0]
    return text if len(text) <= MAX_PASSAGE else text[:MAX_PASSAGE] + "…"


def _validation(case: dict[str, Any]) -> dict[str, Any]:
    review = case["review"]
    recorded = corpus.is_human_reviewed(case)
    return {"state": "RECORDED_UNAUTHENTICATED" if recorded else "NONE", "review_state": review["state"],
            "reviewer_label": review["reviewer_label"], "reviewed_on": review["reviewed_on"]}


def _case_rows(split: str, file_ref: dict[str, str], case: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    speakers = {t["turn"]: t["speaker"] for t in case["source"]["turns"]}
    recovery = {r["item_id"]: r for r in classify_recovery(case)["items"]}
    ledger = {e["item_id"]: e for e in revocation_ledger(case)}
    validation = _validation(case)
    reviewed = validation["state"] != "NONE"
    prefix = "human:" if split == "heldout-human" else ""  # the same case ids exist in the candidate split
    for item in case["items"]:
        st = corpus.statement_of(item)
        rec = recovery[item["item_id"]]
        rules = ["R-EXACT-1", "R-LABEL-1"]
        uncertainty = [] if reviewed else [_U_CANDIDATE]
        if item["source_status"] == "REVOKED":
            rules += ["R-REVOKED-1", "R-REVOKED-2"]
            uncertainty.append(_U_REVOKED)
        else:
            uncertainty.append(_U_VERBATIM if rec["verbatim_in_handoff"] else _U_NOT_VERBATIM)
        if item["source_status"] == "TO_CONFIRM":
            rules.append("R-UNCERTAIN-1")
        if item["authority_bearing"]:
            rules.append("R-AUTH-1")
        if any(e["role"] == "superseded" for e in item["evidence"]):
            rules.append("R-SUPERSEDED-1")
        entry = ledger.get(item["item_id"])
        if entry and entry["ambiguity"]:
            uncertainty.append(entry["ambiguity"])
        rows.append({
            "result_id": f"{prefix}{case['case_id']}/{item['item_id']}", "category": "corpus-item",
            "source": {**file_ref, "split": split, "case_id": case["case_id"], "turn": st["turn"],
                       "speaker": speakers[st["turn"]], "start_byte": st["start_byte"], "end_byte": st["end_byte"]},
            "exact_passage": _clip(st["excerpt"]),
            "decision": {"kind": item["kind"], "source_status": item["source_status"], "authority": item["authority"],
                         "authority_bearing": item["authority_bearing"],
                         "related_passages": [{"role": e["role"], "turn": e["turn"], "passage": _clip(e["excerpt"])}
                                              for e in item["evidence"] if e["role"] != "statement"]},
            "detected_change": {
                "label_outcome": item["handoff_outcome"],
                "label_origin": "HUMAN_RECORDED_UNAUTHENTICATED" if reviewed else "MODEL_DRAFTED_CANDIDATE",
                "handoff_passage": _clip(item["handoff_evidence"]["excerpt"]) if item["handoff_evidence"] else None,
                "handoff_authority": item["handoff_authority"],
                "exact_text_check": "VERBATIM_IN_HANDOFF" if rec["verbatim_in_handoff"] else "NOT_VERBATIM_IN_HANDOFF",
                "revocation_trace": entry["trace"] if entry else None},
            "rules_applied": rules,
            "result": {"recovery": rec["recovery"], "reasons": rec["reasons"]},
            "uncertainty": uncertainty,
            "human_validation": validation,
        })
    anchored = {s["text"] for s in split_sentences(case["handoff"]["text"])} - \
               {s["text"] for s in classify_recovery(case)["unanchored_handoff_statements"]}
    for extra in case["introduced"]:
        span = extra["handoff_evidence"]
        sentence = next((s["text"] for s in split_sentences(case["handoff"]["text"]) if span["excerpt"] in s["text"]), None)
        rows.append({
            "result_id": f"{prefix}{case['case_id']}/{extra['item_id']}", "category": "corpus-introduced",
            "source": {**file_ref, "split": split, "case_id": case["case_id"], "turn": None, "speaker": "handoff note",
                       "start_byte": span["start_byte"], "end_byte": span["end_byte"]},
            "exact_passage": _clip(span["excerpt"]),
            "decision": {"kind": extra["kind"], "source_status": None, "authority": None, "authority_bearing": False,
                         "related_passages": [], "note": "No source statement; the passage exists only in the handoff note."},
            "detected_change": {"label_outcome": "INTRODUCED",
                                "label_origin": "HUMAN_RECORDED_UNAUTHENTICATED" if reviewed else "MODEL_DRAFTED_CANDIDATE",
                                "handoff_passage": _clip(span["excerpt"]), "handoff_authority": None,
                                "exact_text_check": "SENTENCE_ANCHORED" if sentence in anchored else "SENTENCE_UNANCHORED",
                                "revocation_trace": None},
            "rules_applied": ["R-INTRO-1", "R-LABEL-1"],
            "result": {"recovery": "OWNER_RECONFIRMATION_REQUIRED", "reasons": ["INTRODUCED_IN_HANDOFF"]},
            "uncertainty": ([] if reviewed else [_U_CANDIDATE]) + [
                "The exact check sees only that the sentence has no verbatim source; it cannot tell an invention from a rewording."],
            "human_validation": validation,
        })
    return rows


def _comparator_row(split: str, file_ref: dict[str, str], case: dict[str, Any]) -> dict[str, Any]:
    b0, b1, b2 = baselines.exact_text(case), baselines.rule_based(case), baselines.structured_transfer(case)
    ambiguities = corpus.derive_ambiguities(case)
    flags = {"exact_text": b0["drift"], "rule_based": b1["drift"], "structured_transfer": b2["drift"]}
    differing = sorted(name for name, drift in flags.items() if drift != case["expected_drift"])
    validation = _validation(case)
    reviewed = validation["state"] != "NONE"
    handoff = case["handoff"]["text"]
    uncertainty = ([] if reviewed else [_U_CANDIDATE]) + [_U_BASELINE]
    if ambiguities:
        uncertainty.append("A revoked decision is not carried: not counted as drift by the labelling policy, flagged as an ambiguity.")
    return {
        "result_id": f"{'human:' if split == 'heldout-human' else ''}{case['case_id']}/CASE", "category": "corpus-case",
        "source": {**file_ref, "split": split, "case_id": case["case_id"], "turn": None, "speaker": "handoff note",
                   "start_byte": 0, "end_byte": len(handoff.encode("utf-8"))},
        "exact_passage": _clip(handoff),
        "decision": {"label_findings": corpus.derive_findings(case), "label_drift": case["expected_drift"],
                     "ambiguity_flags": ambiguities,
                     "label_origin": "HUMAN_RECORDED_UNAUTHENTICATED" if reviewed else "MODEL_DRAFTED_CANDIDATE"},
        "detected_change": {"exact_text": {"drift": b0["drift"], "not_verbatim": b0["detail"]["not_verbatim"]},
                            "rule_based": {"drift": b1["drift"], "codes": b1["codes"]},
                            "structured_transfer": {"drift": b2["drift"], "codes": b2["codes"]}},
        "rules_applied": ["R-B0", "R-B1", "R-B2", "R-LABEL-1"],
        "result": {"baselines_differing_from_label": differing,
                   "reading": "review queue entry" if differing else "no baseline differs from the label"},
        "uncertainty": uncertainty,
        "human_validation": validation,
    }


def _probe_rows() -> list[dict[str, Any]]:
    doc = json.loads(VECTORS.read_text(encoding="utf-8"))
    rows = []
    for vector in doc["vectors"]:
        expected = vector["expected"]
        before = vector["observed_v1_3"]
        rows.append({
            "result_id": f"PROBE/{vector['id']}", "category": "engine-probe",
            "source": {"file": "contracts/purple-v1_4-vectors.json", "file_sha256": _sha256_lf(VECTORS), "split": None,
                       "case_id": vector["name"], "turn": None, "speaker": "synthetic fixture", "start_byte": None, "end_byte": None,
                       "case_json_sha256": hashlib.sha256(vector["case_json"].encode("utf-8")).hexdigest()},
            "exact_passage": _clip(vector["case_json"]),
            "decision": {"probe_class": vector["class"], "claim": vector["title"]},
            "detected_change": {"v1_3_python": before["python"].get("verdict", "REJECTED"),
                                "v1_3_javascript": before["javascript"].get("verdict", "REJECTED"),
                                "v1_4_python": vector["observed_v1_4"]["python"].get("verdict", "REJECTED"),
                                "v1_4_javascript": vector["observed_v1_4"]["javascript"].get("verdict", "REJECTED"),
                                "now_findings": sorted(set(expected.get("findings", []))),
                                "now_gate_reasons": expected.get("reasons", []),
                                "now_advisories": expected.get("advisories", [])},
            "rules_applied": [vector["rule"]],
            "result": {"now_both_runtimes": "REJECTED" if expected["rejected"] else expected["verdict"], "status": vector["status"]},
            "uncertainty": [_U_PROBE] + (["Open limitation: the behaviour is documented, not corrected."]
                                         if vector["status"] == "OPEN_LIMITATION" else []),
            "human_validation": {"state": "NONE", "review_state": "NOT_REVIEWED", "reviewer_label": None, "reviewed_on": None},
        })
    return rows


def build() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    inputs: dict[str, str] = {}
    for split, name in corpus.SPLITS.items():
        doc = corpus.load_split(split)
        if doc is None:
            continue
        rel = f"research/handoff-corpus-v1_4/{name}"
        file_ref = {"file": rel, "file_sha256": _sha256_lf(corpus.CORPUS_DIR / name)}
        inputs[rel] = file_ref["file_sha256"]
        for case in doc["cases"]:
            rows.extend(_case_rows(split, file_ref, case))
            rows.append(_comparator_row(split, file_ref, case))
    rows.extend(_probe_rows())
    inputs["contracts/purple-v1_4-vectors.json"] = _sha256_lf(VECTORS)
    inputs["ddlab/baselines.py"] = _sha256_lf(ROOT / "ddlab" / "baselines.py")
    policy = load_policy()
    by_category: dict[str, int] = {}
    for row in rows:
        by_category[row["category"]] = by_category.get(row["category"], 0) + 1
    return {
        "proofpack": "decision-drift-lab-proofpack-v1.4", "build": "V1.4.1", "reproduce": "python -m ddlab proofpack",
        "claim_boundary": "Synthetic fiction and synthetic fixtures. Labels are model-drafted candidates unless a row says a review "
                          "was recorded. No semantic evaluation, no model call, no authenticated approval, no signature.",
        "inputs_sha256_lf_normalised": inputs,
        "authorization_policy": {"policy_id": policy["policy_id"], "sha256": policy_digest(policy),
                                 "exempt_actions": [f"{e['name']}/{e['scope']}" for e in policy["exempt_actions"]]},
        "rules": RULES,
        "summary": {"rows": len(rows), "by_category": by_category,
                    "rows_with_recorded_human_validation": sum(r["human_validation"]["state"] != "NONE" for r in rows),
                    "corpus_items_recoverable_verbatim": sum(r["category"] == "corpus-item" and r["result"]["recovery"] == "RECOVERABLE_VERBATIM" for r in rows),
                    "corpus_items_owner_reconfirmation": sum(r["category"] == "corpus-item" and r["result"]["recovery"] != "RECOVERABLE_VERBATIM" for r in rows)},
        "rows": rows,
        "attestation": {"signed": False, "statement": "Unsigned. Compare the input digests with copies you already trust."},
    }


def _cell(text: Any) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def render_markdown(pack: dict[str, Any]) -> str:
    s = pack["summary"]
    out = ["# ProofPack V1.4 (build V1.4.1)", "",
           "**Generated file. Synthetic. Unsigned.** Reproduce with `python -m ddlab proofpack --format md`.", "",
           pack["claim_boundary"], "",
           f"- Rows: {s['rows']} ({', '.join(f'{k}: {v}' for k, v in sorted(s['by_category'].items()))})",
           f"- Rows with a recorded human validation: **{s['rows_with_recorded_human_validation']}**",
           f"- Corpus items carried word for word: {s['corpus_items_recoverable_verbatim']}; "
           f"sent back to the owner: {s['corpus_items_owner_reconfirmation']}",
           f"- Authorization policy: `{pack['authorization_policy']['policy_id']}` "
           f"(`{pack['authorization_policy']['sha256'][:16]}…`), exempt: {', '.join(pack['authorization_policy']['exempt_actions'])}",
           "", "## Inputs (SHA-256, line endings normalised)", ""]
    out += [f"- `{path}`: `{digest}`" for path, digest in sorted(pack["inputs_sha256_lf_normalised"].items())]
    out += ["", "## Rules", ""] + [f"- **{rule}** {text}" for rule, text in pack["rules"].items()]
    header = ["| Result | Source | Exact passage | Decision | Change detected | Rules | Result | Uncertainty | Human validation |",
              "|---|---|---|---|---|---|---|---|---|"]

    def validation(row: dict[str, Any]) -> str:
        v = row["human_validation"]
        return "none" if v["state"] == "NONE" else f"recorded by {v['reviewer_label']} on {v['reviewed_on']} (unauthenticated)"

    out += ["", "## Corpus items", ""] + header
    for row in pack["rows"]:
        if row["category"] not in ("corpus-item", "corpus-introduced"):
            continue
        src, dec, chg = row["source"], row["decision"], row["detected_change"]
        where = (f"{src['case_id']} turn {src['turn']} ({src['speaker']}), bytes {src['start_byte']}-{src['end_byte']}"
                 if src["turn"] else f"{src['case_id']} handoff note, bytes {src['start_byte']}-{src['end_byte']}")
        decision = f"{dec['kind']}" + (f" / {dec['source_status']}" if dec["source_status"] else " / not in source")
        if dec["authority"]:
            decision += f" / authority {dec['authority']}"
        if dec["authority_bearing"]:
            decision += " / authority-bearing"
        decision += "".join(f"; {p['role']} t{p['turn']}: \"{p['passage']}\"" for p in dec["related_passages"])
        change = f"{chg['label_outcome']} ({'human' if chg['label_origin'].startswith('HUMAN') else 'candidate'}); {chg['exact_text_check']}"
        if chg["handoff_passage"] and row["category"] == "corpus-item":
            change += f"; note: \"{chg['handoff_passage']}\""
        if chg["revocation_trace"]:
            change += f"; trace: {chg['revocation_trace']}"
        result = row["result"]["recovery"] + (f": {', '.join(row['result']['reasons'])}" if row["result"]["reasons"] else "")
        out.append("| " + " | ".join(_cell(x) for x in (
            row["result_id"], where, f"\"{row['exact_passage']}\"", decision, change, ", ".join(row["rules_applied"]),
            result, " ".join(row["uncertainty"]), validation(row))) + " |")
    out += ["", "## Case-level comparators (review queue, not accuracy)", ""] + header
    for row in pack["rows"]:
        if row["category"] != "corpus-case":
            continue
        dec, chg = row["decision"], row["detected_change"]
        decision = ("label: " + (", ".join(dec["label_findings"]) or "no finding")
                    + (f"; ambiguity: {', '.join(dec['ambiguity_flags'])}" if dec["ambiguity_flags"] else ""))
        change = (f"B0 {'flags' if chg['exact_text']['drift'] else 'clear'}; "
                  f"B1 {', '.join(chg['rule_based']['codes']) or 'clear'}; "
                  f"B2 {', '.join(chg['structured_transfer']['codes']) or 'clear'}")
        result = ("differs from label: " + ", ".join(row["result"]["baselines_differing_from_label"])
                  if row["result"]["baselines_differing_from_label"] else "no baseline differs")
        out.append("| " + " | ".join(_cell(x) for x in (
            row["result_id"], f"{row['source']['case_id']} handoff note ({row['source']['split']})", f"\"{row['exact_passage']}\"",
            decision, change, ", ".join(row["rules_applied"]), result, " ".join(row["uncertainty"]), validation(row))) + " |")
    out += ["", "## Engine probes", ""] + header
    for row in pack["rows"]:
        if row["category"] != "engine-probe":
            continue
        chg = row["detected_change"]
        change = (f"V1.3 {chg['v1_3_python']}/{chg['v1_3_javascript']}; V1.4 {chg['v1_4_python']}/{chg['v1_4_javascript']} (Python/JS); now: "
                  + (", ".join(chg["now_findings"] + chg["now_gate_reasons"] + chg["now_advisories"]) or "nothing reported"))
        out.append("| " + " | ".join(_cell(x) for x in (
            row["result_id"], f"purple vectors, {row['source']['case_id']}", f"`{row['exact_passage']}`",
            f"{row['decision']['probe_class']}: {row['decision']['claim']}", change, ", ".join(row["rules_applied"]),
            f"{row['result']['now_both_runtimes']} ({row['result']['status']})", " ".join(row["uncertainty"]), validation(row))) + " |")
    out += ["", pack["attestation"]["statement"], ""]
    return "\n".join(out)
