# Threat Model — Offline Structured Handoff Lab V1.1

## Assets

- Input examples and user-supplied local JSON (untrusted).
- Consistency of reported drift findings.
- User privacy (no intentional external exfiltration).
- Claim integrity (must not imply authenticated authority).
- Source-code and build integrity before publication.

## Boundaries

Browser-provided JSON and command-line files are untrusted data. The evaluator has no
operational authority and does not execute case actions. The browser and Python reference
are two independent implementations; parity tests are not proofs of semantic fidelity.

## Highest-value threats and mitigations

| Threat | Control | Residual risk |
|---|---|---|
| Oversized or malformed CLI input | Bounded bytes, strict JSON, UTF-8 and depth | Pathological valid inputs still deserve fuzzing |
| Duplicate keys hiding instruction changes | CLI rejects duplicate keys | V1.2 bounded strict pre-parser rejects duplicates; still needs fuzzing and schema enforcement |
| Mutation of decision authority / status | Exact structural comparison and specific findings | Semantically equivalent text may be mislabeled |
| Synthetic self-approval or action scope mismatch | Fail-closed simulated checks | No authenticated actor or authorization service |
| HTML injection in visible findings | `textContent`, restrictive CSP | Browser test suite not an independent XSS audit |
| Modified JSON report | Canonical SHA-256 digest | No trusted anchor or signing; recomputation is possible |
| Hidden external transfer | No intentional fetch; restrictive CSP | Hosted page and platform/network need independent verification |
| Supply-chain compromise | Dependency-free Python reference; source review | No full SBOM provenance, CodeQL or Scorecard results yet |

## Never claim

- Security without flaws / zero-risk.
- Actual human authorization from JSON flags.
- Cryptographic proof of truth from a digest.
- 100% preservation of original conversations.
- A certification or external pentest without independent evidence.
