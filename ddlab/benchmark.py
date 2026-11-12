"""Deterministic snapshot of the V1.4 baseline run (no timestamps, no machine data).

``python -m ddlab corpus snapshot`` must reproduce
research/handoff-benchmark-v1_4-results.json byte for byte on any machine.
The snapshot records what each baseline output and where it disagrees with the
candidate labels. It contains no rates: a confusion matrix appears only for
cases with a recorded human review.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from . import baselines, corpus

ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = ROOT / "research" / "handoff-benchmark-v1_4-results.json"


def _sha256_lf(path: Path) -> str:
    """SHA-256 after normalising CRLF to LF, so a checkout setting cannot change it."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def snapshot() -> dict[str, Any]:
    splits: dict[str, Any] = {}
    for split in corpus.SPLITS:
        doc = corpus.load_split(split)
        if doc is None:
            splits[split] = {"status": "NOT_PROVIDED"}
            continue
        run = baselines.run_baselines(doc)
        ambiguities = {c["case_id"]: corpus.derive_ambiguities(c) for c in doc["cases"]}
        splits[split] = {
            "status": "RUN", "cases": run["cases"], "label_review": run["label_review"],
            "baselines": run["baselines"],
            "rows": [{"case_id": r["case_id"], "review_state": r["review_state"],
                      "candidate_label": {"drift": r["label_drift"], "codes": r["label_codes"]},
                      "ambiguity_flags": ambiguities[r["case_id"]],
                      "exact_text": {"drift": r["baselines"]["exact_text"]["drift"],
                                     "not_verbatim": r["baselines"]["exact_text"]["detail"]["not_verbatim"]},
                      "rule_based": {"drift": r["baselines"]["rule_based"]["drift"],
                                     "codes": r["baselines"]["rule_based"]["codes"]},
                      "structured_transfer": {"drift": r["baselines"]["structured_transfer"]["drift"],
                                              "codes": r["baselines"]["structured_transfer"]["codes"]}}
                     for r in run["rows"]],
        }
    return {
        "protocol": "handoff-benchmark-v1.4",
        "reproduce": "python -m ddlab corpus snapshot",
        "claim_boundary": "Synthetic fiction, model-drafted candidate labels, trivial baselines. Disagreement counts "
                          "are a review queue, not accuracy. No rate is reported without human-reviewed labels. "
                          "Ambiguity flags are advisory and are not counted as drift.",
        "inputs_sha256_lf_normalised": {
            "research/handoff-corpus-v1_4/dev.json": _sha256_lf(corpus.CORPUS_DIR / "dev.json"),
            "research/handoff-corpus-v1_4/heldout.json": _sha256_lf(corpus.CORPUS_DIR / "heldout.json"),
            "ddlab/baselines.py": _sha256_lf(ROOT / "ddlab" / "baselines.py"),
        },
        "rule_based_thresholds": {"match": baselines.MATCH_THRESHOLD, "intro": baselines.INTRO_THRESHOLD,
                                  "tuned_on": "dev split only, against candidate labels"},
        "splits": splits,
    }
