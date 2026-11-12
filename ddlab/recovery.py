"""What survives an interrupted session verbatim, and what the owner must reconfirm (V1.4).

Deliberately conservative and purely textual. An item is RECOVERABLE_VERBATIM only
when its labelled source statement appears byte-for-byte in the handoff note and
nothing about it calls for a person: it is not revoked, not uncertain, does not
carry authority, and no superseded version of it is present. Everything else is
OWNER_RECONFIRMATION_REQUIRED, with reasons.

This is not a semantic judgement. A faithful paraphrase is sent to the owner too;
a reworded reactivation of a revoked decision cannot be recognised, which is why
every revoked item goes to the owner. docs/walkthrough.mjs mirrors this module.
"""
from __future__ import annotations

from typing import Any

RECOVERABLE = "RECOVERABLE_VERBATIM"
RECONFIRM = "OWNER_RECONFIRMATION_REQUIRED"
NOT_CARRIED_AMBIGUITY = ("Not carried into the handoff. The labelling policy does not count this as drift, but the next "
                         "reader can no longer see that the decision was withdrawn. Confirm with the owner.")
_ENDERS = ".!?"


def split_sentences(text: str) -> list[dict[str, Any]]:
    """Split after . ! ? followed by a space or the end. Offsets are UTF-8 bytes."""
    out: list[dict[str, Any]] = []
    start, n = 0, len(text)
    i = 0
    while i < n:
        if text[i] in _ENDERS and (i + 1 == n or text[i + 1] == " "):
            _emit(text, start, i + 1, out)
            start = i + 1
        i += 1
    _emit(text, start, n, out)
    return out


def _emit(text: str, start: int, end: int, out: list[dict[str, Any]]) -> None:
    while start < end and text[start] == " ":
        start += 1
    while end > start and text[end - 1] == " ":
        end -= 1
    if end > start:
        out.append({"text": text[start:end], "start_byte": len(text[:start].encode("utf-8")),
                    "end_byte": len(text[:end].encode("utf-8"))})


def classify_recovery(case: dict[str, Any]) -> dict[str, Any]:
    handoff = case["handoff"]["text"]
    seen: set[str] = set()
    items = []
    anchors: list[str] = []
    for item in case["items"]:
        if item["item_id"] in seen:
            raise ValueError(f"duplicate item_id: {item['item_id']}")
        seen.add(item["item_id"])
        statements = [e for e in item["evidence"] if e["role"] == "statement"]
        if len(statements) != 1:
            raise ValueError(f"{item['item_id']}: exactly one statement span is required")
        statement = statements[0]
        verbatim = statement["excerpt"] in handoff
        reasons = []
        if item["source_status"] == "REVOKED":
            reasons.append("REVOKED_IN_SOURCE")
            if verbatim:
                reasons.append("REVOKED_TEXT_PRESENT_IN_HANDOFF")
            elif not any(e["role"] == "revocation" and e["excerpt"] in handoff for e in item["evidence"]):
                # V1.4.1: the handoff shows neither the decision nor its withdrawal word for word.
                reasons.append("REVOCATION_TRACE_NOT_VERBATIM_IN_HANDOFF")
        elif not verbatim:
            reasons.append("NOT_VERBATIM_IN_HANDOFF")
        if item["source_status"] == "TO_CONFIRM":
            reasons.append("UNCERTAIN_IN_SOURCE")
        if item["authority_bearing"]:
            reasons.append("AUTHORITY_NOT_TRANSFERABLE_BY_TEXT")
        if any(e["role"] == "superseded" and e["excerpt"] in handoff for e in item["evidence"]):
            reasons.append("SUPERSEDED_VERSION_PRESENT_IN_HANDOFF")
        recovery = RECONFIRM if reasons else RECOVERABLE
        if recovery == RECOVERABLE:
            anchors.append(statement["excerpt"])
        items.append({"item_id": item["item_id"], "kind": item["kind"], "source_status": item["source_status"],
                      "recovery": recovery, "reasons": reasons, "verbatim_in_handoff": verbatim,
                      "source_ref": {"turn": statement["turn"], "start_byte": statement["start_byte"],
                                     "end_byte": statement["end_byte"]}})
    unanchored = [s for s in split_sentences(handoff) if not any(a in s["text"] for a in anchors)]
    return {
        "items": items,
        "unanchored_handoff_statements": unanchored,
        "summary": {"recoverable_verbatim": sum(i["recovery"] == RECOVERABLE for i in items),
                    "owner_reconfirmation_required": sum(i["recovery"] == RECONFIRM for i in items),
                    "unanchored_handoff_statements": len(unanchored)},
        "method": "exact-substring check on labelled source statements; no semantic evaluation",
    }


def revocation_ledger(case: dict[str, Any]) -> list[dict[str, Any]]:
    """Every revoked decision with its source spans, whatever the handoff did with it (V1.4.1).

    The ledger keeps the withdrawal verifiable after a handoff that dropped it. ``trace`` is an
    exact-text observation; a reworded mention of the withdrawal is not recognised.
    """
    handoff = case["handoff"]["text"]
    out = []
    for item in case["items"]:
        if item["source_status"] != "REVOKED":
            continue
        statement = next(e for e in item["evidence"] if e["role"] == "statement")
        revocations = [e for e in item["evidence"] if e["role"] == "revocation"]
        stated = statement["excerpt"] in handoff
        withdrawn = any(e["excerpt"] in handoff for e in revocations)
        trace = ("REVOCATION_WORDING_PRESENT" if withdrawn
                 else "REVOKED_TEXT_PRESENT_WITHOUT_REVOCATION_WORDING" if stated
                 else "NO_VERBATIM_TRACE_IN_HANDOFF")
        out.append({"item_id": item["item_id"], "statement_ref": dict(statement),
                    "revocation_refs": [dict(e) for e in revocations],
                    "statement_verbatim_in_handoff": stated, "revocation_verbatim_in_handoff": withdrawn,
                    "trace": trace, "label_outcome": item["handoff_outcome"],
                    "ambiguity": NOT_CARRIED_AMBIGUITY if item["handoff_outcome"] == "NOT_CARRIED_OK" else None})
    return out
