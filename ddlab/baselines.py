"""Three trivial baselines for unstructured handoff drift (V1.4). No model calls.

B0 exact_text          labelled source statements must appear byte-for-byte in the handoff.
                       Uses label *spans* (where the statements are), never label outcomes.
B1 rule_based          label-free cue-phrase extraction and token-overlap matching.
B2 structured_transfer the V1.3 exact comparer run on a structured encoding derived from
                       the item labels. It stands for "a person normalised both sides by
                       hand"; it is a procedure reference, not an independent measurement.

Confusion matrices are produced only for cases whose labels carry a recorded
human review. For unreviewed cases the runner lists disagreements with the
candidate labels as a review queue and reports no rates.
"""
from __future__ import annotations

import re
from typing import Any

from .core import evaluate
from .corpus import derive_findings, is_human_reviewed, statement_of
from .recovery import split_sentences

# Tuned on the DEV split only, against model-drafted candidate labels (tune_rule_based()).
# The held-out split must never be used to change these values.
MATCH_THRESHOLD = 0.34
INTRO_THRESHOLD = 0.25

BASELINES = ("exact_text", "rule_based", "structured_transfer")

_STOP = frozenset("""a an the and or but so to of in on at by for from with as is are was were be been being it its this that
these those i me my we our you your he she they them their his her there here now then than also just yes no okay ok
do does did will would shall have has had if into out up down all any some each other own same too very s t can could
should may might must not only until before after once while because since about over under again more most""".split())
_NEGATION = frozenset("not no never without nothing cannot neither nor".split())
_UNCERTAIN = re.compile(r"\b(probably|maybe|might|may|possibly|unverified|unconfirmed|uncertain|hypothesis|estimate|"
                        r"suspect|roughly|apparently|not (?:yet )?(?:been )?(?:confirmed|verified|guaranteed)|"
                        r"not sure|not de-duplicated)\b", re.I)
_REVOKE = re.compile(r"\b(scrap|cancel|cancelled|drop|skip|forget|withdraw|withdrawn|no longer|on second thought|"
                     r"scratch that|call off|is off|take \w+(?: \w+)? off)\b", re.I)
_CORRECT = re.compile(r"\b(correction|actually|instead|my mistake|wrong|sorry)\b", re.I)
_DIRECTIVE = re.compile(r"\b(let's|please|do not|don't|never|must|need|only|keep|stay|book|order|send|draft|prepare|ship|"
                        r"schedule|move|update|create|export|remove|renew|enrol|compare|write|get|add|take|arrange|say|"
                        r"go with|publish|treat|leave|check|summarise|offer|agreed|sign|signs|approve|approved)\b", re.I)
_APPROVAL = re.compile(r"\b(approve|approved|approval|sign|signs|release|authorised)\b", re.I)
_TOKEN = re.compile(r"\d+(?:[.,:]\d+)*|[^\W\d_]+")
_NOT_NAMES = frozenset("monday tuesday wednesday thursday friday saturday sunday january february march april may june "
                       "july august september october november december i".split())


def _tokens(text: str) -> list[str]:
    out = []
    for tok in _TOKEN.findall(text.lower().replace("n't", " not")):
        if tok[0].isdigit():
            out.append(tok.replace(",", ""))
            continue
        for suffix in ("ing", "ed", "es", "s"):
            if len(tok) > len(suffix) + 3 and tok.endswith(suffix):
                tok = tok[: -len(suffix)]
                break
        out.append(tok)
    return out


def _content(text: str) -> set[str]:
    return {t for t in _tokens(text) if t not in _STOP}


def _numbers(text: str) -> set[str]:
    return {t for t in _tokens(text) if t[0].isdigit()}


def _negated(text: str) -> bool:
    return any(t in _NEGATION for t in _tokens(text))


def _names(text: str) -> set[str]:
    words = re.findall(r"[^\W\d_]+", text)
    return {w for w in words[1:] if w[0].isupper() and w.lower() not in _NOT_NAMES}


def _containment(part: set[str], whole: set[str]) -> float:
    return len(part & whole) / len(part) if part else 0.0


# --------------------------------------------------------------------------- B0
def exact_text(case: dict[str, Any]) -> dict[str, Any]:
    handoff = case["handoff"]["text"]
    missing = [i["item_id"] for i in case["items"]
               if i["source_status"] != "REVOKED" and statement_of(i)["excerpt"] not in handoff]
    return {"drift": bool(missing), "codes": None, "detail": {"not_verbatim": missing},
            "note": "Cannot tell paraphrase from change; ignores status, authority and additions."}


# --------------------------------------------------------------------------- B1
def _extract_source(case: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for turn in case["source"]["turns"]:
        assistant = turn["speaker"].lower() == "assistant"
        for sentence in split_sentences(turn["text"]):
            text = sentence["text"]
            content = _content(text)
            if text.endswith("?"):
                continue
            live = [c for c in candidates if c["state"] == "current"]
            if not assistant and _REVOKE.search(text):
                decisions = [c for c in live if c["kind"] == "decision"]
                if decisions:
                    target = max(decisions, key=lambda c: (_containment(content, c["content"]), c["order"]))
                    target["state"] = "revoked"
                continue
            if len(content) < 2:
                continue
            if assistant and any(_containment(content, c["content"]) >= 0.6 for c in candidates):
                continue  # the assistant echoing an earlier statement
            kind = "decision" if not assistant and _DIRECTIVE.search(text) else "fact"
            cand = {"text": text, "content": content, "kind": kind, "turn": turn["turn"], "order": len(candidates),
                    "state": "current", "uncertain": bool(_UNCERTAIN.search(text))}
            if not assistant and _CORRECT.search(text) and live:
                previous = max(live, key=lambda c: (_containment(content, c["content"]), c["order"]))
                if _containment(content, previous["content"]) > 0:
                    previous["state"] = "superseded"
            candidates.append(cand)
    return candidates


def _handoff_units(case: dict[str, Any]) -> list[dict[str, Any]]:
    units = []
    for sentence in split_sentences(case["handoff"]["text"]):
        for part in sentence["text"].split(";"):
            part = part.strip()
            if part:
                units.append({"text": part, "content": _content(part)})
    return units


def rule_based(case: dict[str, Any], match: float = MATCH_THRESHOLD, intro: float = INTRO_THRESHOLD) -> dict[str, Any]:
    source = _extract_source(case)
    units = _handoff_units(case)
    codes: set[str] = set()
    trace = []

    def best(content: set[str]) -> tuple[float, dict[str, Any] | None]:
        scored = [(_containment(content, u["content"]), u) for u in units]
        return max(scored, key=lambda s: s[0], default=(0.0, None))

    for cand in source:
        zone = "DECISIONS" if cand["kind"] == "decision" else "FACTS"
        score, unit = best(cand["content"])
        found = unit is not None and score >= match
        signal = "retained"
        if cand["state"] == "superseded":
            current = [c for c in source if c["state"] == "current" and c["order"] > cand["order"]]
            if found and all(best(c["content"])[0] < score for c in current):
                codes.add(f"{zone}_ALTERED")
                signal = "stale-version-present"
            else:
                signal = "superseded"
        elif cand["state"] == "revoked":
            if found and not (_negated(unit["text"]) or _REVOKE.search(unit["text"])):
                codes.update(("DECISIONS_ALTERED", "REACTIVATED_DECISION"))
                signal = "reactivated"
            else:
                signal = "revoked"
        elif not found:
            codes.add(f"{zone}_MISSING")
            signal = "missing"
        else:
            if cand["uncertain"] and not _UNCERTAIN.search(unit["text"]):
                codes.update(("FACTS_ALTERED", "UNSUPPORTED_FACT_PROMOTION"))
                signal = "promoted"
            if _negated(cand["text"]) != _negated(unit["text"]):
                codes.add(f"{zone}_ALTERED")
                signal = "polarity-changed"
            numbers = _numbers(cand["text"])
            if numbers and _numbers(unit["text"]) and not numbers <= _numbers(unit["text"]):
                codes.add(f"{zone}_ALTERED")
                signal = "number-changed"
            if _APPROVAL.search(cand["text"]) and _APPROVAL.search(unit["text"]):
                before, after = _names(cand["text"]), _names(unit["text"])
                if before and after and not before & after:
                    codes.update(("DECISIONS_ALTERED", "AUTHORITY_CHANGED"))
                    signal = "authority-changed"
        trace.append({"turn": cand["turn"], "kind": cand["kind"], "state": cand["state"],
                      "uncertain": cand["uncertain"], "signal": signal, "score": round(score, 3), "text": cand["text"]})

    everything = [_content(s["text"]) for t in case["source"]["turns"] for s in split_sentences(t["text"])]
    for unit in units:
        if len(unit["content"]) < 3:
            continue
        if max((_containment(unit["content"], c) for c in everything), default=0.0) < intro:
            zone = "DECISIONS" if _DIRECTIVE.search(unit["text"]) else "FACTS"
            codes.add(f"{zone}_INTRODUCED")
            trace.append({"turn": None, "kind": zone.lower()[:-1], "state": "handoff-only", "uncertain": False,
                          "signal": "introduced", "score": 0.0, "text": unit["text"]})
    return {"drift": bool(codes), "codes": sorted(codes), "detail": {"candidates": trace},
            "note": "Keyword and token-overlap heuristics; no understanding of meaning, quoting or scope."}


# --------------------------------------------------------------------------- B2
def structured_encoding(case: dict[str, Any]) -> dict[str, Any]:
    """Encode the item labels as a V1.3 structured case (ids, text, status, authority)."""
    source: dict[str, list] = {"facts": [], "decisions": []}
    handoff: dict[str, list] = {"facts": [], "decisions": []}
    for item in case["items"]:
        zone = "decisions" if item["kind"] == "decision" else "facts"
        before = {"id": item["item_id"], "text": statement_of(item)["excerpt"], "status": item["source_status"]}
        if item["kind"] == "decision":
            before["authority"] = item["authority"]
        source[zone].append(before)
        outcome = item["handoff_outcome"]
        if outcome in ("OMITTED", "NOT_CARRIED_OK"):
            continue
        after = dict(before)
        if outcome == "ALTERED":
            after["text"] = item["handoff_evidence"]["excerpt"]
        elif outcome == "REACTIVATED":
            after["status"] = "ACTIVE"
        elif outcome == "PROMOTED":
            after["status"] = "FACT"
        elif outcome == "AUTHORITY_CHANGED":
            after["authority"] = item["handoff_authority"]
        handoff[zone].append(after)
    for extra in case["introduced"]:
        zone = "decisions" if extra["kind"] == "decision" else "facts"
        handoff[zone].append({"id": extra["item_id"], "text": extra["handoff_evidence"]["excerpt"], "status": "UNKNOWN"})
    return {"case_id": case["case_id"], "source": source, "handoff": handoff,
            "action": {"name": "handoff-review", "scope": "internal", "requires_human": False}}


def structured_transfer(case: dict[str, Any]) -> dict[str, Any]:
    report = evaluate(structured_encoding(case))
    codes = sorted({f["code"] for f in report["findings"]})
    return {"drift": bool(codes), "codes": codes, "detail": {"verdict": report["verdict"]},
            "note": "Derived from the item labels: agreement with them is by construction, except where the "
                    "labelling policy and the V1.3 comparer differ (for example a revoked decision that is not carried)."}


_FUNCTIONS = {"exact_text": exact_text, "rule_based": rule_based, "structured_transfer": structured_transfer}


# --------------------------------------------------------------------------- runner
def _matrix(rows: list[dict[str, Any]], name: str) -> dict[str, int]:
    cells = {"true_positive": 0, "false_positive": 0, "false_negative": 0, "true_negative": 0}
    for row in rows:
        labelled, predicted = row["label_drift"], row["baselines"][name]["drift"]
        key = ("true_" if labelled == predicted else "false_") + ("positive" if predicted else "negative")
        cells[key] += 1
    return cells


def run_baselines(doc: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for case in doc["cases"]:
        rows.append({"case_id": case["case_id"], "review_state": case["review"]["state"],
                     "human_reviewed": is_human_reviewed(case), "label_drift": case["expected_drift"],
                     "label_codes": derive_findings(case),
                     "baselines": {name: fn(case) for name, fn in _FUNCTIONS.items()}})
    reviewed = [r for r in rows if r["human_reviewed"]]
    unreviewed = [r for r in rows if not r["human_reviewed"]]
    summary = {}
    for name in BASELINES:
        queue = [{"case_id": r["case_id"], "candidate_label_drift": r["label_drift"],
                  "baseline_drift": r["baselines"][name]["drift"]}
                 for r in unreviewed if r["baselines"][name]["drift"] != r["label_drift"]]
        summary[name] = {
            "confusion_matrix": _matrix(reviewed, name) if reviewed else None,
            "confusion_matrix_basis": (f"{len(reviewed)} case(s) with a recorded, unauthenticated human review"
                                       if reviewed else "WITHHELD: no human-reviewed labels in this split"),
            "unreviewed_review_queue": {
                "meaning": "Disagreement with MODEL-DRAFTED candidate labels. A list of cases to look at, not accuracy.",
                "cases_compared": len(unreviewed), "disagreements": len(queue), "cases": queue},
        }
    return {"protocol": "handoff-benchmark-v1.4", "corpus": doc["corpus"], "split": doc["split"],
            "cases": len(rows), "label_review": {"human_reviewed": len(reviewed), "not_reviewed": len(unreviewed)},
            "claim_boundary": "Synthetic fiction and trivial baselines. No semantic evaluation, no model, "
                              "no accuracy claim without human-reviewed labels.",
            "baselines": summary, "rows": rows}


def tune_rule_based(dev_doc: dict[str, Any]) -> dict[str, Any]:
    """Grid search on DEV only. Objective: fewest case-level disagreements with the candidate
    labels, then highest mean code-set overlap, then the smallest thresholds."""
    if dev_doc["split"] != "dev":
        raise ValueError("thresholds may only be tuned on the dev split")
    grid = []
    for match in (0.34, 0.4, 0.5, 0.6, 0.67, 0.75):
        for intro in (0.2, 0.25, 0.34, 0.4, 0.5):
            disagreements, overlap = 0, 0.0
            for case in dev_doc["cases"]:
                result = rule_based(case, match, intro)
                expected = set(derive_findings(case))
                disagreements += result["drift"] != case["expected_drift"]
                union = expected | set(result["codes"])
                overlap += len(expected & set(result["codes"])) / len(union) if union else 1.0
            grid.append({"match": match, "intro": intro, "case_disagreements": disagreements,
                         "mean_code_overlap": round(overlap / len(dev_doc["cases"]), 4)})
    grid.sort(key=lambda g: (g["case_disagreements"], -g["mean_code_overlap"], g["match"], g["intro"]))
    return {"best": grid[0], "grid": grid, "objective": "agreement with candidate labels on dev (not accuracy)"}
