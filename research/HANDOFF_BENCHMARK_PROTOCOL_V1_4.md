# Unstructured Handoff Benchmark Protocol V1.4

**Status: experiment scaffold with candidate labels. No accuracy result exists yet.**
Everything below is reproducible on one machine with Python and Node and no network.

## 1. Question

A conversation produces decisions, corrections, revocations, facts, open uncertainties and
authority constraints. Someone then writes a free-text handoff note. Which of those items survive
the note, which are changed, and how much of that can trivial, model-free checks see?

The V1.3 deck of 100 generated structured variants cannot answer this: it compares structures the
generator itself wrote. V1.4 adds a small corpus of naturally phrased text instead of more variants.

## 2. Corpus

`research/handoff-corpus-v1_4/`, validated by `contracts/handoff-corpus.schema.json` and
`ddlab/corpus.py` (`python -m ddlab corpus validate`).

| Split | File | Cases | Candidate benign | Candidate drift |
|---|---|---|---|---|
| dev | `dev.json` | 25 | 8 | 17 |
| heldout | `heldout.json` | 12 | 4 | 8 |
| heldout-human | `heldout-human.json` | **not provided** (blind human labels for the 12 held-out conversations) | | |
| independent-heldout | `independent-heldout.json` | **not provided** (20 or more cases written and labelled by someone else) | | |

Each case holds a fictional mini-conversation (3 to 8 turns), a handoff note, and item labels:

- `kind` (decision or fact), `source_status` (ACTIVE, REVOKED, FACT, TO_CONFIRM), the authority
  named in the conversation, and whether the item is *authority bearing* (it says who may approve,
  or what must not happen without approval).
- `evidence`: one `statement` span, plus `superseded`, `revocation` or `qualification` spans where
  the conversation corrected, withdrew or hedged the statement. Spans are **UTF-8 byte offsets**
  into the turn text and carry the excerpt; the loader rejects a span that does not reproduce it.
- `handoff_outcome`: PRESERVED_VERBATIM, PRESERVED_PARAPHRASE, NOT_CARRIED_OK, ALTERED, OMITTED,
  REACTIVATED, PROMOTED or AUTHORITY_CHANGED, with the handoff span where one exists.
- `introduced`: statements in the note that no source statement supports.
- `expected_findings`: derived mechanically from the outcomes, in the V1.3 code vocabulary.

All 37 conversations are newly written fiction in 37 different settings. No real person,
organisation, conversation or customer record was used.

## 3. Label state: candidates, not truth

Every label in this package was **drafted by an AI model**: `label_state` is
`CANDIDATE_MODEL_DRAFTED` and `review.state` is `NOT_REVIEWED` in all 37 cases. **No human has
reviewed any label.** A candidate label is a proposal for a reviewer, not ground truth.

To review:

The full procedure, with roles and what a labeller may see, is in
`research/HUMAN_LABELING_PROCEDURE_V1_4.md`. In short:

1. The labeller fills in the blind form `research/labeling-kit/heldout-blind-form.json`
   (`python -m ddlab corpus kit`), quoting passages. It contains no title and no candidate label.
2. `python -m ddlab corpus compile form.json` computes the spans and writes a corpus file with the
   review recorded. The candidate file is never edited; human labels live beside it as
   `heldout-human.json`.
3. `python -m ddlab corpus agreement --human heldout-human.json` compares the two labellings.
4. `python -m ddlab corpus validate` must still pass.

A non-blind review of the candidates remains possible by editing a case's `review` object
(`HUMAN_REVIEWED`, `HUMAN_AMENDED` or `DISPUTED`), but it is weaker evidence than blind labels.

The review record is a text field anyone can type. The tools can tell that a review was recorded;
they cannot tell that it happened or who did it.

### Labelling policy used for the candidates (open to the reviewer)

- Label what someone would act on: decisions, constraints, facts that drive an action, open
  uncertainties. Greetings and acknowledgements are not labelled.
- **Q1 (revised in V1.4.1).** A revoked decision that the note simply does not mention keeps the
  outcome name `NOT_CARRIED_OK` and is **not counted as drift**, but it is no longer called benign:
  the next reader cannot see that the decision was withdrawn. Every output now flags it as the
  ambiguity `REVOKED_DECISION_TRACE_LOST`, the evidence report keeps the withdrawn decision and its
  source spans in a revocation ledger, and the structured comparer reports the same code as a
  finding. A revoked decision shown as active is `REACTIVATED`. A human labeller may decide
  differently; that is one of the things blind labelling is for.
- **Q2.** The reason given for a revocation is not labelled; a fact that motivates a correction or
  a constraint is.
- **Q3.** A paraphrase is benign when a careful reader would act identically on both wordings.
- **Q4.** Quoted third-party text is not an instruction from the speaker who quotes it.

## 4. Splits and what "held-out" means here

- The held-out file was written in the same pass as the dev file, before any baseline code
  existed, and its digest was recorded (`fe6b5fcf…e3852`, 2026-11-12T00:40:23Z).
- The rule-based baseline was written and tuned looking only at dev outputs, then frozen
  (`ddlab/baselines.py`, `5b337e0a…c2ee`, 2026-11-12T00:46:36Z).
- The baselines were then run on held-out **once**. Nothing in `baselines.py` changed afterwards;
  `research/handoff-benchmark-v1_4-results.json` records all three hashes and
  `tests/test_v14_corpus.py` fails if the snapshot stops reproducing.

V1.4.1 changed the structured comparer (`ddlab/core.py`), which B2 calls: for the two cases with
a revoked decision that is not carried, B2 now reports `REVOKED_DECISION_TRACE_LOST` next to
`DECISIONS_MISSING`. No case-level flag changed, the corpus files and `baselines.py` are
byte-identical, and the snapshot was regenerated. This is recorded here because it is a second run
on held-out, caused by an engine change and not by tuning.

**This held-out split is not independent.** The same author wrote the dev cases, the held-out
cases, every candidate label and the baseline rules, and had read the held-out text before writing
the rules. It protects against tuning thresholds on those 12 cases; it does not provide an
unbiased sample. A genuinely independent set must be written and labelled by a person who has not
seen `baselines.py`, and saved as `independent-heldout.json`. Until then that split, and
`heldout-human`, report `NOT_PROVIDED` and exit code 3.

## 5. Baselines (`ddlab/baselines.py`, no model calls)

| | Baseline | Sees | Idea |
|---|---|---|---|
| B0 | `exact_text` | label spans, not outcomes | every labelled, non-revoked source statement must appear byte for byte in the note |
| B1 | `rule_based` | text only | cue phrases for directives, revocations, corrections and hedges; token-overlap matching; number, polarity and name checks |
| B2 | `structured_transfer` | the item labels | encode both sides as V1.3 structured items and run the V1.3 exact comparer |

B2 stands for "a person normalised both sides by hand". Because the encoding is derived from the
labels, its agreement with them is by construction and is **not a measurement**. It is kept as the
procedure reference and because it exposes where the labelling policy and the V1.3 comparer differ.

B1 thresholds (`match` 0.34, `intro` 0.25) come from a grid search on dev against the candidate
labels (`python -m ddlab corpus tune`). That objective is agreement with unreviewed candidates.

## 6. What is reported, and what is withheld

`python -m ddlab corpus baselines --split dev|heldout` and `python -m ddlab corpus snapshot`.

- **Confusion matrices are computed only over cases with a recorded human review.** With none, the
  field is `null` and says `WITHHELD`. No precision, recall or accuracy figure is produced.
- For unreviewed cases the runner lists where a baseline's case-level flag differs from the
  candidate label. This is a **review queue**: a list of cases to look at, not a score.

Review queue recorded in the snapshot (candidate labels, not accuracy):

| Split | B0 exact_text | B1 rule_based | B2 structured_transfer |
|---|---|---|---|
| dev (25) | HD-02, 03, 04, 05, 06, 08 flagged, candidate benign | HD-01, 02, 04, 05, 06, 08 flagged, candidate benign | HD-07 flagged, candidate benign |
| heldout (12) | HH-01, 02, 03 flagged, candidate benign; **HH-06 not flagged, candidate drift** | HH-01, 02, 03, 04 flagged, candidate benign | HH-04 flagged, candidate benign |

### Failure cases worth keeping (pinned in `tests/test_v14_corpus.py`)

1. **Paraphrase is flagged.** B0 flags every benign paraphrase (HD-02 "ready by Thursday" versus
   "finished by Thursday"). Expected for exact matching; this is the cost the V1.3 engine also has.
2. **A reactivated revocation is invisible to exact text.** In HH-06 the withdrawn renewal is
   listed as pending in the note. B0 skips revoked items, so it reports no drift.
3. **Rules flag the word-for-word control.** B1 flags HD-01, a verbatim copy, because the source
   sentence also names the rejected alternative ("not 150 like last week") and the note has a
   header line with no source.
4. **Quoted untrusted text becomes an action unnoticed.** In HD-24 the note turns a quoted
   suspicious email into an open action. B1 does not report it as introduced, since the words do
   occur in the conversation.
5. **Policy gap, now an explicit ambiguity.** B2 reports `DECISIONS_MISSING` and
   `REVOKED_DECISION_TRACE_LOST` when a revoked decision is simply not carried (HD-07, HH-04). The
   labelling policy does not count it as drift. Since V1.4.1 both sides say the same thing in
   different registers: the label flags an ambiguity, the comparer raises a finding, and the trace
   is kept in the ledger. The case-level disagreement stays in the review queue on purpose.
6. **Compound decisions.** B1 reports HH-04 as a reactivation: one sentence ordered two things,
   one was withdrawn, and the rules cannot split it.

## 7. What this does not show

- Any property of an AI model. No model produced the handoff notes; they were written to contain
  specific phenomena.
- Semantic correctness. No comparator here understands meaning.
- Base rates. Twelve benign and twenty-five drifting cases were chosen, not sampled.
- Generalisation beyond short, tidy, English, single-topic exchanges.
- Label quality. Until reviewed, the candidates may be wrong or inconsistent.

## 8. If a language model is ever added as a comparator

Not implemented and not approved. It would need, recorded per run: provider and exact model
identifier, prompt, parameters, number of repetitions, variance across repetitions, cost, date,
and an explicit owner decision for each external route. Local-only inference would need the same
record minus the route approval. Held-out text must not be used for prompt development.

## 9. Reproduce

```bash
python -m ddlab corpus validate
python -m ddlab corpus tune
python -m ddlab corpus baselines --split dev --summary-only
python -m ddlab corpus baselines --split heldout --summary-only
python -m ddlab corpus snapshot        # must equal research/handoff-benchmark-v1_4-results.json
python -m ddlab proofpack              # must equal research/proofpack-v1_4.json
python -m unittest discover -s tests -q
node --test tests/v12-browser-logic.test.mjs tests/v13-challenge.test.mjs tests/v14-contracts.test.mjs
```
