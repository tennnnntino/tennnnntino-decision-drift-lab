# Purple Team — Controlled, Reproducible and Limited

## Scope

This exercise tests only the standalone local prototype with **synthetic fixtures**.
There is no permission to scan external services, customer accounts, other repositories
or production environments. No exploits are run against third parties.

## Four roles

- **Red:** proposes a falsifiable failure mode and a minimal, inert fixture.
- **Blue:** implements the boundary or explains why it is out of scope.
- **Purple:** reruns both the attack fixture and legitimate regression paths.
- **Reviewer:** separates observed results, assumptions and untested conditions.

## Reproducible local execution

```bash
python -m unittest discover -s tests -q
python -m ddlab benchmark
node --check docs/engine.mjs
node --check docs/app.mjs
```

Current snapshot: 24 purple tests added to 29 existing tests = 53 passing tests
on the author's environment, 2026-11-11. **Rerun before trusting this number.**
The UI shows a frozen snapshot, not a security telemetry service.

## V1 → V1.1 demonstrated defensive delta

| Control | Before | After | Reproduce |
|---|---|---|---|
| Duplicate keys in CLI JSON | second value was silently accepted | `INPUT_ERROR` | R02, R03 |
| Oversized CLI input padded with whitespace | file consumed without early bound | `INPUT_ERROR` | R01 |
| Pathological nesting | accepted or raised non-domain exceptions | bounded/controlled error | R07, R24 |
| Nonstandard `NaN` input | eventually rejected while serializing | rejected during parsing | R04 |

A passing unit test means this specific fixture passed on this implementation.
It does **not** establish the absence of vulnerabilities.

## Important known gaps / attack surface

1. Browser `JSON.parse` does **not** reject duplicate raw JSON keys (unresolved).
2. Full schema validation is not implemented (unresolved).
3. The approval simulator processes synthetic flags: no authenticated human identity.
4. Reports are hashed, not signed and not anchored in independent trusted storage.
5. No actual AI model or raw chat import; prompt-injection defenses in a live model
   are NOT tested by treating an inert text field as data.
6. Static checks for CSP, APIs and DOM safety are not equivalent to dynamic pen testing.
7. No external independent security review or formal OWASP ASVS coverage claim.

## Next gate: purple test coverage for offline chat import

Test consent handling, size limits, malformed exports, conflicting source offsets,
source-local-only references, personal-data minimization, secret redaction,
multiple speakers, untrusted content, pathological nesting and deterministic replay.
All extracted decisions must remain *candidates* until human review. Before adding a
model adapter, set up independent source grounding and a human-adjudicated evaluation.

## Responsible disclosure

For any eventual public version, enable private vulnerability reporting and supply a
security contact/policy. Do not publish real-user content or weaponized payloads in issues.
Document scope, observed impact, reproducer, defensive patch and retest evidence.
