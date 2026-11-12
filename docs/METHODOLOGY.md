# Methodology & limits — V1.0 LAB

## 1. What gets measured

The input contains `source.facts`, `source.decisions`, `handoff.facts`, `handoff.decisions` and a synthetic `action`. Each item must have a **unique stable string ID within its category**. Comparison is full exact JSON equality for matching IDs, independent of JSON object key order.

- `retained`: matching ID with exact object equality.
- `altered`: matching ID with any field changed.
- `missing`: source ID absent from handoff.
- `introduced`: handoff ID absent from source.
- `changed_fields`: names of differing top-level fields, not deep semantic explanation.

For reference counts, exact recall uses source size and exact precision uses handoff size. Values are null when their denominator is zero. A rewrite of a sentence with equivalent meaning is **still changed**; an item with a new ID is **introduced**, even if semantically duplicated. This is not an unstructured conversation evaluator.

## 2. Additional rule checks

- `UNSUPPORTED_FACT_PROMOTION`: `TO_CONFIRM`, `UNKNOWN` or `SUPPORTED_INFERENCE` becomes `FACT` under the same ID.
- `REACTIVATED_DECISION`: `REJECTED` or `REVOKED` becomes `ACTIVE` under the same ID.
- `AUTHORITY_CHANGED`: any exact authority field change for the same decision ID.
- Synthetic approval check: if `requires_human` is true, `human_approval` must contain `approved: true` and `actor_type: "HUMAN"`; supplied action/scope must match when present. This field does not authenticate or identify anyone and cannot authorize real actions.

Both passing and failing fixtures are tested against expected **scenario labels**. These labels are made by the test author; they are not independent ground truth on real AI agents.

## 3. Benchmark honesty

Current fixture coverage: 10 **hand-authored synthetic scenarios**. The denominator of benchmark success is the number of predefined scenarios for which the checker returns the expected synthetic verdict. It is not a claim of model performance or comparative generalization.

To make future scientific claims, add: a documented selection protocol; labelled and held-out cases; clear baselines including naive exact match; multiple paraphrase levels; false-positive and false-negative measures; inter-annotator agreement; independent adversarial review; multiple model seeds; cost/latency measures and uncertainty intervals.

## 4. Integrity, not truth

A hash is useful only when compared against a **trusted pre-established digest**. The report digest is recomputable from the output content. There is no cryptographic signature, secure timestamp, identity proof, provenance attestation or trusted audit anchor. Browser reports omit digest fields until there is one verified cross-runtime integrity contract.

## 5. Technology radar is a decision log

`technology-radar.json` is a dated, versioned design decision artifact. `ADOPT` means actually present in the repository, `TRIAL` means an experiment to build, `ASSESS` means a research topic, and `HOLD` means deliberately excluded. Neither the radar nor the demo crawls current technological news.

## 6. Independent reproduction

Run `python -m unittest discover -s tests -v`, `python -m ddlab benchmark` and (where Node.js is installed) browser-engine parity tests. A static web server is required to load ES modules under normal browser security restrictions.
