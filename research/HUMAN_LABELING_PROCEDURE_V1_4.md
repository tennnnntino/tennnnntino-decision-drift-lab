# Human labelling procedure V1.4

**Status: prepared, not run. No human label exists in this package.**
Two jobs are described: (A) blind labelling of the 12 existing held-out cases, and (B) writing
and labelling at least 20 new, independent cases. Both end in a file the tools can read, and only
then do confusion matrices appear.

Nothing in this procedure can prove that a person did the work or who they are. The record is a
self-declaration. Keep the evidence listed in section 6 outside the package.

## 1. Roles

| Role | Does | Must not have |
|---|---|---|
| Coordinator | hands out the kit, seals files, runs the tools | (may have seen everything) |
| Labeller A | job A, blind | read `ddlab/baselines.py`, the candidate labels, any non-blind sheet, the results snapshot, the ProofPack, the protocol's review-queue table |
| Author-labeller B | job B, own cases and labels | the same, and ideally has not read the 37 existing conversations |
| Second labeller (optional) | repeats job A or labels B's cases blind | the same |

The author of the existing corpus, the baselines and the candidate labels cannot be labeller A or B.
One person may do both A and B, but do A first.

## 2. What the labeller receives

Only these files, by a channel that does not include the rest of the package:

- `research/labeling-kit/heldout-blind-form.json` (job A): 12 conversations and notes, empty label
  slots, no titles, no candidate labels.
- `research/labeling-kit/independent-case-template.json` (job B).
- Sections 3 and 4 of this page.

Do **not** send `research/handoff-corpus-v1_4/heldout.json`, the review sheet without `--blind`,
`research/proofpack-v1_4.json`, `research/PROOFPACK_V1_4.md` or the benchmark protocol: each of them
reveals the candidate labels. Titles are withheld on purpose ("Signer replaced" gives the answer away).

Before sending, the coordinator records the SHA-256 of the kit file. The form also carries
`source_text_sha256`; the compiler refuses a form whose conversations or notes were edited.

## 3. How to label (given to the labeller)

For each case, read the conversation, then the handoff note, and list what someone would act on.

1. **What to list.** Decisions, constraints, facts that drive an action, and open uncertainties.
   Not greetings or acknowledgements. If you would not act on it, do not list it.
2. **Quote, do not paraphrase.** Give the turn number and an exact quote. The quote must occur
   exactly once in that turn; lengthen it if it is ambiguous. You never count bytes: the compiler
   computes the spans.
3. **Kind and status.** `decision` with `ACTIVE` or `REVOKED`; `fact` with `FACT` or `TO_CONFIRM`.
   Use `REVOKED` when the conversation withdrew the decision, and quote the words that withdrew it
   under `revocation`. Use `TO_CONFIRM` when the speaker hedged, and quote the hedge under
   `qualification`. If a statement was corrected, the corrected wording is the `statement` and the
   earlier wording goes under `superseded`.
4. **Authority.** `authority` is the person or role the conversation names as deciding (or null).
   `authority_bearing` is true when the item says who may approve, or forbids acting without approval.
5. **Outcome in the note.**
   - `PRESERVED_VERBATIM`: same words.
   - `PRESERVED_PARAPHRASE`: different words, and a careful reader would act identically.
   - `ALTERED`: the note says something a careful reader would act on differently.
   - `OMITTED`: an active decision, fact or uncertainty is not in the note.
   - `NOT_CARRIED_OK`: a **revoked** decision that the note simply does not mention.
     This is recorded, kept in a ledger and flagged as an ambiguity; it is not counted as drift.
   - `REACTIVATED`: a revoked decision that the note presents as active or pending.
   - `PROMOTED`: an uncertain fact that the note states as fact.
   - `AUTHORITY_CHANGED`: the note names a different approver; give it under `handoff_authority`.
   For every outcome except `OMITTED` and `NOT_CARRIED_OK`, quote the passage of the note in
   `handoff_quote`.
6. **Introduced.** List statements in the note that nothing in the conversation supports. Text
   that a speaker merely quoted from someone else is not that speaker's instruction.
7. **When unsure,** choose, and say why in the case `note`. Disagreement is information; do not
   try to guess what was expected.
8. **Sign the form.** `labeller.label` (name or pseudonym), `labeller.date`, and the three
   independence answers as `true` or `false`. Answer truthfully: a form that says you saw the
   candidates or the baseline code is refused as blind, and that is the correct outcome.

## 4. Job B: writing independent cases

- At least **20** cases, all your own invention. No real people, organisations, conversations or
  customer data. State this in `data_rights`.
- Three to eight turns, natural phrasing, one handoff note per case, each case in a different setting.
- Roughly one third faithful notes (some verbatim, some reworded) and two thirds with a real
  change. Vary the changes: omission, alteration, a lost correction, a reactivated withdrawal, a
  promoted estimate, a changed approver, a dropped condition, something invented.
- Include a few cases you find genuinely hard to label. They are worth more than the easy ones.
- Do not look at the 37 existing cases for inspiration if you can avoid it.
- Label your own cases with the rules of section 3, in the same form.

A second labeller labelling B's cases blind is the only way to get inter-human agreement. Without
it, say that there was one labeller.

## 5. Compiling and reading the result (coordinator)

```bash
# job A
python -m ddlab corpus compile completed-heldout-form.json > research/handoff-corpus-v1_4/heldout-human.json
python -m ddlab corpus validate
python -m ddlab corpus agreement --human research/handoff-corpus-v1_4/heldout-human.json
python -m ddlab corpus baselines --split heldout-human --summary-only

# job B
python -m ddlab corpus compile completed-independent-form.json > research/handoff-corpus-v1_4/independent-heldout.json
python -m ddlab corpus validate
python -m ddlab corpus baselines --split independent-heldout --summary-only

# then regenerate what depends on the corpus, and say so in the changelog
python -m ddlab corpus snapshot > research/handoff-benchmark-v1_4-results.json
python -m ddlab proofpack > research/proofpack-v1_4.json
python -m ddlab proofpack --format md > research/PROOFPACK_V1_4.md
```

The compiler refuses a form that is unsigned, declares itself non-blind, changes the text, quotes
ambiguously, labels nothing in a case, or (job B) has fewer than 20 cases.

How to read the outputs:

- `corpus agreement` compares the human labels with the model-drafted candidates: a case-level
  table, Cohen's kappa (unstable at n = 12; report the table), finding codes on each side, and item
  matches by overlapping source span. **Agreement is not accuracy.** Where they differ, neither is
  right by default; discuss and record the adjudication.
- `corpus baselines` on a human-labelled split prints the first confusion matrices. With 12 or 20
  cases, report counts, not percentages, and no confidence claims.
- `heldout.json` (candidates) is never edited. The human labels live beside it.

## 6. Evidence to keep, outside the package

- The hash of each kit file as sent, and of each completed form as received.
- Who labelled, when, how long it took (self-reported), and what they were given.
- The independence answers, and any contact between labeller and coordinator about specific cases.
- Adjudication notes for every disagreement that was resolved, and the list of those left open.

## 7. What may be said afterwards

With job A only: "12 cases, one human labeller, agreement table versus model-drafted candidates;
baseline counts on human labels". With job B: the same for 20 or more independent cases, and that
is the first result that does not depend on the author of the baselines. In both cases: synthetic
fiction, small numbers, no semantic evaluation, one labeller unless a second was used.
