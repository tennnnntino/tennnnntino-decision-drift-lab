# Changelog

## V1.4.2 — Private candidate
- Added a route-bound P19 connector simulation in Python and JavaScript, with a local CLI demonstration.
- The simulated connector checks a separately supplied route and binds approvals to tenant, target and content. It rejects absent, modified, revoked, expired and consumed approvals.
- Added 12 matched cross-runtime observations. Historical evaluator, fixtures and ProofPack retain their declaration-only semantics.

## V1.4.1 — Private candidate (2026-11-12)
- **External authorization policy.** The requirement for a simulated human approval now comes from `contracts/authorization-policy.json` or an operator file (`evaluate --policy`), validated by strict intake and a schema whose only default is `HUMAN_APPROVAL_REQUIRED`. A case can tighten the requirement, never waive it (`CASE_WAIVER_IGNORED`); policy-like fields inside a case are ignored and flagged (`CASE_POLICY_FIELD_IGNORED`). The browser engine mirrors this through the generated `docs/policy.mjs`.
- **Behaviour change:** a case with `requires_human: false` passes only if the external policy exempts its declared action name and scope. The V1.0 test `test_empty_comparison` encoded the old behaviour and was rewritten. The fixture `customer_followup` still passes, through the policy exemption for `prepare-draft/internal`.
- **Revocation trace.** Reports carry a `revocation_ledger` with every revoked source decision and what the handoff did with it; a dropped one raises `REVOKED_DECISION_TRACE_LOST`, an unknown new status `REVOKED_STATUS_CHANGED`. Evidence reports, the checklist and the walkthrough show the ledger. In the corpus, `NOT_CARRIED_OK` keeps its name for file stability but is now flagged as an ambiguity and no longer described as benign. Corpus files and candidate labels are unchanged.
- **Unicode.** Canonically equivalent text and identifiers (NFC/NFD) compare equal with an advisory (`UNICODE_NORMALIZATION_ONLY`); identifiers that collide after normalisation are rejected; compatibility forms remain differences.
- **Statuses.** Fixed alias table with trimming, ASCII case folding and separator unification; non-canonical spellings raise the advisory `NONCANONICAL_STATUS` and no longer hide a reactivation.
- **Paraphrase.** Not corrected. Changed text carries a `text_profile` (shared words, negation changed, numbers changed, formatting only) as a triage hint.
- **Determinism and parity.** Fixed: metric rounding tie (0.0312 in Python, 0.0313 in JavaScript), report order and digest depending on Python's hash seed, change-list order by locale, absent versus null authority. These four existed in V1.4.
- **Reports** now use `report_schema` `1.1` (structured evaluator) and `1.4.1` (evidence report); V1.3 and V1.4 report digests are not comparable with V1.4.1 digests. Verdicts, findings, comparison lists, metrics and gate results of all 110 pre-existing cases are unchanged; the only additions are ledger entries for the eleven cases with a revoked decision.
- **Labelling kit:** `corpus kit`, `corpus template`, `corpus compile`, `corpus agreement`, optional split `heldout-human`, blind sheets without titles, and `research/HUMAN_LABELING_PROCEDURE_V1_4.md`. No human label is packaged.
- **ProofPack:** `python -m ddlab proofpack` and `research/PROOFPACK_V1_4.md`, 184 rows, none with a recorded human validation.
- Purple vectors: 28 probes (10 fixed in V1.4, 13 fixed in V1.4.1, 2 open, 2 controls, 1 hint). The baseline code and both corpus files are byte-identical to V1.4; the results snapshot was regenerated because the structured comparer now reports the trace-lost finding.
- Still open: semantic evaluation, human and independent labels, the case naming its own action, authenticated approval, signed provenance, independent review, license.
- No GitHub push, commit, deployment, external service, model call or real data.

## V1.4 — Private candidate (2026-11-12)
- Added a synthetic **unstructured handoff corpus**: 37 fictional mini-conversations with handoff notes (25 dev, 12 held-out), item labels with UTF-8 byte spans, and a strict loader. **All labels are model-drafted candidates; no human review has been performed.** The held-out split is same-author and not independent; the independent split is declared `NOT_PROVIDED`.
- Added three model-free baselines (exact text, rule-based, structured transfer), a dev-only threshold search, a deterministic results snapshot and review gating: **no confusion matrix or rate is produced without human-reviewed labels.** Six baseline failure cases are pinned as tests.
- Added fail-closed intake (`ddlab/intake.py`, `docs/intake.mjs`) and a JSON Schema subset validator (`ddlab/schema.py`, `docs/schema.mjs`) with shared vectors enforced in both runtimes; new CLI commands `validate`, `corpus`, `recover`, `report` and the opt-in `evaluate --strict-schema`.
- **Fixed ten evaluator defects** found by synthetic RED probes: Python equated booleans with numbers; the browser engine accepted arrays and explicit nulls where Python rejected them; integers beyond 2^53-1 were compared instead of rejected; a simulated human approval naming no scope or no action was accepted. Reports for all 110 pre-existing cases are byte-identical to V1.3.
- **Behaviour change:** cases containing integers beyond 2^53-1 or non-finite numbers are now rejected by both engines; an explicit simulated approval must name a scope and an action.
- Added browser tab 09 (interrupted-workflow walkthrough), an unsigned, data-minimised evidence report with pattern-based redaction, ARIA tab semantics with arrow-key navigation, and a skip link.
- Observed once in one Chromium-based browser over real HTTP on `127.0.0.1`: CSP enforced, no outbound request, keyboard operation works. **Not tested:** screen readers, other browsers, header-delivered CSP, user trials.
- Still open: semantic evaluation, human-reviewed and independent labels, linking decision text to the action requirement, free-text statuses, authenticated approval, signed provenance, independent security review, license.
- No GitHub push, commit, deployment, external service, model call or real data.

## V1.3 — Private candidate (2026-11-12)
- Shipped an interactive **Break the Handoff** attack/defense inspection workbench, local browser execution, filters, synthetic case export, downloadable results and responsive layout.
- Generated a **10-archetype × 10-context = 100-case synthetic regression deck**. It is not 100 independently validated or human-labelled cases. Correctly rejected negative cases are expected results, not real security attacks.
- Added an independent Python challenge CLI, Node regression checks, 100-case Python/JS structural parity, an opt-in sample CI pipeline and loopback-only start scripts.
- Ran the browser UI at 1440px / 390px in an **in-memory harness**, executed the 100 controls there without JavaScript page errors; real localhost browser navigation was blocked and real CSP behavior remains unverified.
- No public GitHub operation, deployment, customer data, secret import, or agent action.
- Owner Human Gate remains required for any release.


## V1.2 — Private candidate (2026-11-12)
- Added strict duplicate-object-key detection for the browser JSON editor, including escaped Unicode duplicates.
- Added local-only synthetic text handoff pilot with speaker-labelled markers, source byte spans, explicit manual review, revocation and conflict flags, exact comparison and local JSON download.
- Added 22 Node adversarial tests and Python unittest wrapper; verified UI in an in-memory Chromium harness at 1440px and 390px.
- **Blocked:** real localhost HTTP navigation by test environment policy; CSP must still be tested with actual serving.
- Remaining gaps: full schema enforcement, real chat-platform import, semantic evaluation, authenticated approvals, independent SAST/DAST and signed provenance.
- No GitHub push, public deployment, real data or production access.


## V1.1 — Private candidate (2026-11-11)
- Added 24 controlled Purple Team regression cases (53 total unit tests locally).
- Hardened bounded CLI input reading; rejects duplicate JSON object keys and invalid non-finite literals.
- Added nesting and structural node limits in Python and JavaScript; browser byte limit now UTF-8-aware.
- Added public-neutral threat model, reproducible Purple Team protocol and a sixth browser tab.
- **Known remaining gaps:** browser duplicate raw JSON keys, actual identity/authentication, schema enforcement, signed evidence and independent security review.
- No public deployment or publication authorised.

## 1.0 LAB — 2026-11-11

- Added a separately runnable, dependency-free Python reference engine and CLI.
- Added ten fully synthetic executable scenarios across handoff, commercial drafting, support and release operations.
- Added explicit fact-promotion, revoked-decision, authority-change and scope-mismatch findings.
- Added exact recall/precision with null-denominator handling and reproducible report hashes.
- Added independent browser interface with local JSON editing and report download.
- Added static technology decision radar, 20-lens engineering review, methodology and publication gate.
- Added browser/Python parity tests, input-bounds and regression checks.
- Did not add any model connector, real user authentication or live business-data access.
