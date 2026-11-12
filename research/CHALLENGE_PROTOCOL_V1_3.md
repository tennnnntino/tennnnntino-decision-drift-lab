# Generated Challenge Protocol V1.3 — deliberately falsifiable

## Exact scope

**100 deterministic synthetic regression variants** were generated as a Cartesian product of:

- **10 fictional operating contexts**: sales, support, release, procurement, finance, logistics, education, compliance, customer success and field operations.
- **10 transformation archetypes**: clean control, rewrite, omission, new unsupported fact, uncertainty promotion, revoked decision reactivation, authority replacement, agent self-approval, scope mismatch and wrong-action approval.

The generated deck is in `research/generated-challenge-100.json` (an export of `ddlab.challenge.generate_cases`). The browser also imports the corresponding `docs/challenge-deck.mjs` snapshot. **These are not 100 independently designed, human-annotated or model-executed scenarios.**

## Reference outcome

Every case declares an expected PASS/FAIL outcome. Negative cases additionally declare at least one required signal, such as `AUTHORITY_CHANGED`, `REACTIVATED_DECISION`, `SCOPE_MISMATCH` or `NO_SYNTHETIC_HUMAN_APPROVAL`. A control matches only when the observed verdict and all required signals appear. No real action is performed.

A negative fixture that correctly returns FAIL **counts as a successful regression check**, not as an application failure or a real attack succeeded.

## Reproduce

```bash
python -m ddlab challenge --summary-only
python -m unittest discover -s tests -q
node --test tests/v13-challenge.test.mjs
```

The browser's “RUN ALL 100 CONTROLS” button executes the JavaScript evaluator locally; the Python CLI executes an independently written Python implementation. A separate parity test compares structural outputs on the 100 variants. Agreement between two programs **does not** establish ground truth, robustness on unseen attacks, semantic equivalence or protection of a production agent.

## What is measured

- Expected outcome matches (integer count).
- Required findings present (set containment).
- Required simulated approval-rejection reasons present (set containment).
- A local UI execution time (non-standardized and **not** comparable across machines).

## Threats the deck cannot measure

The synthetic program cannot authenticate human approvals, accept real cross-platform conversation archives, judge semantically equivalent paraphrases, prove sources are true, detect every possible injection, or validate secure deployment. Its simulated approval fields can be authored by anyone controlling an input JSON file.

The deck represents *regression breadth*, not independently sampled accuracy. A future public benchmark needs held-out human-annotated cases, independent reviewers, confusion matrices, base-rate documentation, confidence intervals, independent application security testing and a clear data provenance policy.

## Purple-team workflow

1. **RED** supplies an independently reproducible synthetic negative case.
2. **BLUE** records the expected signal, code change and regression test.
3. **PURPLE** runs both the known-good positive control and the attack case, observes whether the failure is prevented, and documents residual gaps.
4. **HUMAN GATE** explicitly authorizes any public release of specific bytes after security and rights review.

No testing against third-party systems, identities or live services is in scope.
