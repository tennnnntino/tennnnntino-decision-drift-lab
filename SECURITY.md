# Security & privacy limitations

**Do not send real personal data, authentication tokens, client conversations, medical/financial records, privileged instructions, or proprietary source files to this demonstration.** Use synthetic records.

- Browser app runs locally without intentional network requests, SDKs or analytics. A restrictive CSP is declared in `docs/index.html`. Audit the network panel before assuming an environment is isolated.
- Python CLI reads local JSON and writes only to stdout. It never executes the action described in a case and never calls a model.
- Human approvals are fixture fields, **not** authenticated credentials, cryptographic signatures or enterprise authorization.
- SHA-256 digests can detect modification relative to a trusted recorded digest. They do not prove fact truth, consent, identity, chronology, completeness or legal provenance.
- The evaluator compares structured fields **exactly**; semantically equivalent wording may be flagged as changed.
- This project is not designed to protect actual customer workflows. Do not connect it to production or expose it as a permission enforcement point.
- Synthetic threat cases are for defensive education and regression tests only.

Report a concern through the repository's issue reporting mechanism without including secrets, private data or executable exploit payloads that affect third parties.


## Purple Team status (V1.1 candidate)

A local, synthetic Red → Blue → Verify exercise is documented in
`docs/PURPLE_TEAM_PROTOCOL.md`. The current snapshot covers 24 adversarial checks.
V1.2 adds duplicate-key preflight to the browser editor and a bounded synthetic-only local-chat pilot. Remaining gaps: no full schema validation, no audited real chat-platform parser, incomplete coverage of malicious Unicode edge cases, no trusted report signatures, and **no authenticated Human Gate**.

**Reporting:** Do not place exploit details affecting other people or sensitive data
in a public issue. If this becomes a public GitHub repository, enable GitHub's
private vulnerability reporting before inviting security researchers.


## V1.2 local text pilot — new attack surface

- Only synthetic, explicitly marked, line-oriented `.txt`/`.md` files are supported.
- File and textarea sizes are bounded; raw source spans are UTF-8 byte offsets.
- Text is rendered via DOM `textContent`; it is never treated as an instruction.
- Unknown/unlabelled lines are skipped; this means **absence of an extracted decision is not proof it never existed**.
- Speaker labels, review selections and source citations are **not** trusted identities, signatures or authorizations.
- Downloaded reports contain the provided text; do not use real confidential input even though the tool has no intentional outbound API calls.
- Static page execution with CSP enabled over actual localhost HTTP **was not reproduced in this environment**; browser visual tests used in-memory injection with CSP bypassed by the test harness. A separate check is required before release.


## V1.3 challenge scope and unresolved risks

The 100-case grid is a locally generated structural regression deck (10 mutations × 10 fictional contexts), **not 100 independent adversarial penetration tests**. It cannot assert that an external agent action is safe. Input fixtures can claim `actor_type: HUMAN` without cryptographic evidence, so even an `ALLOW_IN_SIMULATION` result conveys no authenticated authority.

The browser displays data using text nodes and `textContent`. It does not intentionally transmit challenge data; browser serving and CSP in a real deployment still require independent validation. The executable JavaScript runtime and the Python evaluator independently process the same synthetic cases, but both can share specification errors.

No real company data, personal conversations, accounts or external systems are part of this challenge. To report a possible security issue, use a private channel once the repository is approved for publication. Do not include live third-party exploitation steps in public reports.


## V1.4 additions and unresolved risks

- **New input surface:** a corpus loader, a strict intake layer and a schema subset validator. They are bounded and fail closed for the 40 intake and 26 schema vectors in `contracts/`, in both runtimes. Vectors are examples, not a proof; the validator is a contract check, not a security boundary.
- **Evaluator fixes:** ten defects found by synthetic probes are fixed and pinned (`contracts/purple-v1_4-vectors.json`). Four remain open: a case can switch its own human requirement off; faithful paraphrases are flagged; the default path flags NFC against NFD text; non-canonical status spellings lose the specific reactivation signal. See `docs/PURPLE_TEAM_V1_4.md`.
- **The simulated approval is still only a fixture check.** Requiring a scope and an action makes one fail-open case fail closed. It does not authenticate anyone and must not be used as a permission point.
- **Evidence reports are unsigned.** The SHA-256 covers the canonical case JSON and detects change relative to a copy the reader already trusts. It is not a signature, a timestamp or provenance.
- **Redaction is pattern-based** (email, URL, long token, long digit run; ASCII digits only). It will miss names, addresses and anything unusual. Do not rely on it for real data; the lab still accepts synthetic input only.
- **Labels are unreviewed candidates.** Nothing derived from them, including the walkthrough classification, is a statement about correctness.
- **No conversation-provider adapter exists.** `docs/IMPORTER_ARCHITECTURE_V1_4.md` is a proposal and lists the privacy decisions required first.
- **Browser check:** CSP enforcement and the absence of outbound requests were observed once, on loopback HTTP, in one Chromium-based browser, by the same session that wrote the code. A meta-delivered CSP cannot set `frame-ancestors` or reporting; a real host should send headers. Independent repetition is still required.
- **Static guards, not sandboxing:** tests assert that no Python module imports network, process or database facilities and that no browser module contains network, storage, dynamic-code or HTML-injection APIs. A future change can remove these properties; the tests only notice the listed tokens.


## V1.4.1 additions and unresolved risks

- **Authorization policy is external, and still a simulation.** The requirement for a simulated approval no longer comes from the analysed case. Two things still do: the approval record (`human_approval`) and the action's own name and scope. A case that controls its input can therefore claim an exempt action (`prepare-draft/internal` in the packaged policy) or supply a well-formed approval. In a real system both must come from the enforcement point, with an authenticated approver. **Never present the simulated approval as real human authentication.**
- **Whoever can edit the policy file or pass `--policy` controls the gate.** The policy is validated, not signed. Protect it like configuration.
- **Policy exemptions are exact string matches.** Look-alike characters do not match and fall back to "approval required".
- **Revocation ledger** records what the comparison saw. In the unstructured corpus it is an exact-text observation; a reworded withdrawal or reactivation is not recognised.
- **Unicode handling is canonical equivalence only.** Confusable and compatibility characters are not unified and are reported as differences. NFC results can differ between Unicode versions of the two runtimes for newly assigned characters; not tested.
- **Status aliases are a fixed English list.** Anything outside it is unclassified; an unclassified new status on a revoked decision is flagged, on other items it is only a plain difference.
- **Text profiles are lexical and English-centric.** They can miss a meaning change and can flag a harmless one. They are hints for a reviewer.
- **Labelling kit:** the compiler trusts the labeller's self-declaration. It cannot detect a false one.
- **ProofPack and reports are unsigned.**

## V1.4.2 connector simulation

The separate route-bound simulation models how a connector rejects P19 when its effective operation differs from the case declaration. The route, payload, clock and approval reference must be supplied independently of the analysed case. The approval ledger is local and ephemeral. Reports explicitly record that no identity was authenticated and no external action was executed. The historical evaluator still trusts the case's declared operation for its own synthetic verdicts.
