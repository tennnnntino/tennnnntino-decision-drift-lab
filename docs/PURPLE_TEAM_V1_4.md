# Purple team record V1.4

Synthetic inputs, one machine, one working session on 2026-11-12. This is a regression record for
a local research prototype. It is not a penetration test, an audit or a security certification.

Machine-readable evidence: `contracts/purple-v1_4-vectors.json` (15 probes with the behaviour
observed **before** on the unmodified V1.3 candidate and the behaviour **enforced** now), executed
by `tests/v14-contracts.test.mjs` and `tests/test_v14_parity.py`.

## RED: probes against both evaluators

Each probe is a small structured case fed to the Python reference (`ddlab/core.py`) and to the
browser engine (`docs/engine.mjs`). To reproduce the "before" column, run the same `case_json`
through the V1.3 package.

| ID | Class | Probe | Before (Python / JS) | Now (both) | Status |
|---|---|---|---|---|---|
| P01 | false negative | a field changes from `1` to `true` | PASS / FAIL | FAIL `DECISIONS_ALTERED` | fixed |
| P02 | false negative | a field changes from `0` to `false` | PASS / FAIL | FAIL `FACTS_ALTERED` | fixed |
| P03 | false negative | human approval naming no scope and no action, used for an external send | PASS / PASS | FAIL, `APPROVAL_SCOPE_UNSPECIFIED`, `APPROVAL_ACTION_UNSPECIFIED` | fixed |
| P04 | false negative | arrays in place of the source and handoff objects | rejected / **PASS** | rejected | fixed |
| P05 | parity | array in place of the action | rejected / evaluated | rejected | fixed |
| P06 | false negative | the case sets `requires_human: false` although its decision text demands approval | PASS / PASS | PASS | **open** |
| P07 | false negative | integer above 2^53 changed by one | FAIL / **PASS** | rejected | fixed |
| P08 | false positive | faithful paraphrase of a decision | FAIL / FAIL | FAIL | **open, by design** |
| P09 | false positive | same visible text in NFC and NFD | FAIL / FAIL | FAIL | **open** |
| P10 | missed signal | revoked decision returns with status `active` (lower case) | FAIL without `REACTIVATED_DECISION` | same | **open** |
| P11 | control | `1` versus `1.0` | PASS / PASS | PASS | unchanged |
| P12 | false negative | `facts: null` on both sides | rejected / **PASS** | rejected | fixed |
| P13 | parity | `action: null` | rejected / evaluated | rejected | fixed |
| P14 | parity | `requires_human: null` | rejected / default applied | rejected | fixed |
| P15 | false negative | human approval naming a scope but no action | PASS / PASS | FAIL, `APPROVAL_ACTION_UNSPECIFIED` | fixed |

Ten probes exposed a defect that is now fixed, four remain open, one is a control.

## BLUE: what changed, and only that

- `ddlab/core.py`: item comparison uses JSON-typed equality (`ddlab/schema.strict_equal`) instead
  of Python `==`; integers beyond 2^53-1 and non-finite numbers are rejected; an otherwise valid
  simulated human approval must name both a scope and an action.
- `docs/engine.mjs`: arrays are no longer accepted where objects are required; an explicit `null`
  no longer falls back to a default; the same number and approval rules as Python.

No fixture, generated control or expected verdict was edited. The approval rule adds reasons only
when an approval is otherwise explicit, so reports for existing fixtures are byte-identical in
every field, digests included (checked against the V1.3 package for all 110 cases).

## PURPLE: positive and negative controls re-run

| Control | Before fixes | After fixes |
|---|---|---|
| Python suite | 61 passed | 107 passed (61 original + 46 new) |
| Node suites | 26 passed | 41 passed (26 original + 15 new) |
| Generated deck | 100/100 matched (10 PASS, 90 FAIL) | 100/100 matched (10 PASS, 90 FAIL) |
| Packaged fixtures | 10/10 | 10/10 |
| Python/JS parity, 110 structured cases | equal | equal |
| Python/JS parity, 15 probes | 8 diverged | 0 diverge |

Timeline (UTC, one automated session, not a team repair-time metric): first RED reproduction
00:33:18; last four probes added 00:48:44; fix applied 00:49:15; all suites green 00:49:38.
About sixteen minutes from first reproduction to verified fix, with unrelated work in between.

## New and remaining limitations

1. **P06, the action block is self-declared.** A case file can turn the human requirement off.
   Nothing links the decision text "never send without approval" to `action.requires_human`.
   Closing this needs either semantics or a source-side declaration of the requirement; neither
   is implemented. The simulated gate remains a fixture check, never an enforcement point.
2. **P08, paraphrase.** Exact comparison flags faithful rewording. Measured as a recurring false
   positive in `research/HANDOFF_BENCHMARK_PROTOCOL_V1_4.md`.
3. **P09, normal forms.** The default path flags NFC against NFD as altered. The strict path
   (`evaluate --strict-schema`, `validate`) rejects non-NFC input with a clear code instead.
4. **P10, free-text statuses.** Status values are not an enumeration, so a non-canonical spelling
   loses the specific signal, although the verdict is still FAIL.
5. **New in V1.4:** rejecting unsafe integers means a legitimate case carrying a 64-bit identifier
   as a JSON number is now refused. Identifiers should be strings.
6. **New in V1.4:** the schema validator implements a subset of JSON Schema and refuses schemas
   that use anything else. It is a contract check, not a security boundary.
7. Default `evaluate` (without `--strict-schema`) keeps the V1.1 reader for backward
   compatibility and does not apply the character policy.

## Useful failures of the new baselines

See section 6 of `research/HANDOFF_BENCHMARK_PROTOCOL_V1_4.md`: exact text misses a reactivated
revocation (HH-06), rules flag a verbatim copy (HD-01) and miss quoted text turned into an action
(HD-24), and the structured comparer disagrees with the labelling policy on revoked decisions that
are simply not carried (HD-07, HH-04). These are pinned as tests so that a future change which
silently "improves" them is noticed.

## Real browser check: localhost over HTTP with the CSP in place

Performed once on 2026-11-12 on the development workstation.

- **Browser:** the desktop coding assistant's built-in browser pane, Chromium 156 engine
  (user agent `Chrome/156.0.8078.75`). Not stock Chrome, Firefox or Safari.
- **Serving:** `python -m http.server 8765 --bind 127.0.0.1 --directory docs`, plain HTTP.
- **Observed:**
  - Page and 15 same-origin files loaded with status 200; first load produced no console message.
  - The only other request was the browser's own `/favicon.ico` to the same loopback origin (404).
    No request left the loopback address.
  - The CSP is delivered by the `<meta>` element (the static server sends no CSP header) and was
    enforced. Deliberate probes from the page context were each blocked with a
    `securitypolicyviolation` event in `enforce` disposition: same-origin `fetch` and external
    `fetch` (`connect-src`), an injected inline script (`script-src-elem`), an injected inline
    style (`style-src-elem`), an external image (`img-src`) and `eval` (`script-src`). The external
    probes targeted a reserved documentation address and were blocked before any connection.
  - "RUN ALL 100 CONTROLS" showed `100 / 100`. The JSON editor refused the unsafe-integer case and
    the array-as-state case with the new messages. The local chat demo extracted 3 + 3 candidates.
  - No horizontal overflow at viewport widths 375, 468 and 1009 px.
- **Keyboard, in that browser:** with focus on the first tab, ArrowRight moved to and activated
  the next tab, End activated the last; exactly one tab was in the tab order; Tab moved into the
  panel and then to NEXT; Enter four times reached step 5 of 5 with focus handed to BACK when NEXT
  became disabled; the live region read "Step 5 of 5: Evidence you can share".
- **Accessibility tree, in that browser:** nine `tab` and nine `tabpanel` roles and a `status`
  role for the step indicator were exposed.

### Not tested

- Any screen reader (no assistive technology was run; only roles and names were inspected).
- Stock Chrome, Firefox, Safari, mobile browsers, and browser zoom or forced-colours modes.
- CSP delivered as an HTTP header, HTTPS hosting, and any hosting other than the loopback server.
- A packet capture; "no outbound request" rests on the browser's request list and the server log.
- The report download click in the browser (the report builder itself is covered by Node tests).
- Colour contrast measurement, and the optional `tools/inmemory_browser_smoke.py` harness
  (Playwright is not installed on this machine).
- Independent review of any of the above by a second person.


---

# V1.4.1 addendum (2026-11-12, second session)

Evidence: `contracts/purple-v1_4-vectors.json` now holds 28 probes with three observations each:
on the unmodified V1.3 package, on the unmodified V1.4 package, and the behaviour enforced now.
Both runtimes must produce exactly the recorded result, including finding order.

## What V1.4 still got wrong

V1.4 reported "0 of 15 probes diverge". That was true of those 15. Thirteen new probes found four
more divergences or instabilities that V1.4 still had, plus the gaps that this pass set out to close.

| ID | Class | Probe | V1.4 (Python / JS) | Now (both) | Status |
|---|---|---|---|---|---|
| P06 | false negative | the case sets `requires_human: false` for an external send | PASS / PASS | FAIL, `CASE_WAIVER_IGNORED` | fixed |
| P09 | false positive | same text in NFC and NFD | FAIL / FAIL | PASS, advisory `UNICODE_NORMALIZATION_ONLY` | fixed |
| P10 | missed signal | revoked decision returns as `active` | FAIL without signal | FAIL, `REACTIVATED_DECISION`, advisory | fixed |
| P16 | parity | 1 of 32 retained: a rounding tie | 0.0312 / 0.0313 | 0.0313 | fixed |
| P17 | determinism | nine promoted facts | 12 different report digests over 12 hash seeds | 1 digest | fixed |
| P18 | false negative | the case carries its own policy and a waiver | PASS / PASS | FAIL, advisory `CASE_POLICY_FIELD_IGNORED` | fixed |
| P19 | false negative | the case names itself `prepare-draft/internal` | PASS / PASS | PASS | **open** |
| P20 | missed signal | a revoked decision is not carried | `DECISIONS_MISSING` only | plus `REVOKED_DECISION_TRACE_LOST`, ledger `NOT_CARRIED` | fixed |
| P21 | missed signal | `revoked ` returns as `Enabled` | no reactivation signal | `REACTIVATED_DECISION` | fixed |
| P22 | false positive | one identifier in NFC and NFD | missing plus introduced | PASS with advisory | fixed |
| P23 | missed signal | revoked decision returns as `archived` | no specific signal | `REVOKED_STATUS_CHANGED` | fixed |
| P24 | control | full-width letters versus ASCII | FAIL | FAIL | unchanged |
| P25 | triage | rewording that drops "never ... without" | FAIL | FAIL, `negation_changed: true` | hint added |
| P26 | false negative | two identifiers that collide after NFC | accepted as two items | rejected | fixed |
| P27 | parity | authority absent versus `null` | no signal / `AUTHORITY_CHANGED` | no signal | fixed |
| P28 | parity | change list for ids `a` and `B` | `B, a` / `a, B` | `B, a` | fixed |
| P08 | false positive | faithful paraphrase | FAIL | FAIL, with a text profile | **open, by design** |

Totals over 28 probes: 10 fixed in V1.4, 13 fixed in V1.4.1, 2 open, 2 controls, 1 hint added.
Divergences between Python and JavaScript: 12 in V1.3, 4 in V1.4, 0 now.

## What changed

- `ddlab/policy.py`, `contracts/authorization-policy.json` and its schema, `docs/policy.mjs`
  (generated): the approval requirement is external. `ddlab/core.py` and `docs/engine.mjs` consult
  it and ignore waivers and policy-like fields in the case.
- Both engines: revocation ledger and two new findings, NFC-keyed identifiers and canonical
  equivalence, status alias table, text profile on changed text, sorted iteration, code-point
  ordering, integer half-up rounding, absent authority equals null.
- One pre-existing test (`tests/test_core.py::test_empty_comparison`) encoded the vulnerable
  behaviour and was rewritten. Everything else from V1.0 to V1.3 is untouched and green.

## Controls re-run

| Control | V1.4 | V1.4.1 |
|---|---|---|
| Python suite | 107 passed | 140 passed |
| Node suites | 41 passed | 43 passed |
| Generated deck | 100/100 | 100/100 |
| Packaged fixtures | 10/10 | 10/10 |
| 110 pre-existing cases: verdict, findings, comparison lists, metrics, gate | reference | identical |
| 110 pre-existing cases: full report bytes | reference | **changed** (new report fields, schema 1.1) |
| Python/JS parity over full structured reports, 110 cases | not checked on the new fields | equal |

## Limitations after V1.4.1

1. **P19, self-declared action.** The policy is external, but it is matched against the action
   name and scope that the case itself declares. A case can call an external send
   "prepare-draft". Closing this needs the action to come from the system that would execute it.
2. **The approval record is still a fixture field** and authenticates nobody.
3. **P08, paraphrase.** Flagged as before. The text profile is a lexical, English-centric hint.
4. Canonical equivalence only: confusable and compatibility characters are differences.
5. The status alias list is fixed and English.
6. Whoever can change the policy file or pass `--policy` controls the gate.
7. Report digests from V1.3 and V1.4 are not comparable with V1.4.1 digests.

## Browser re-check

See the end of this file for the V1.4.1 localhost observation.

## V1.4.1 localhost observation

Once, 2026-11-12, same workstation and same built-in Chromium 156 browser pane, page served by
`python -m http.server` on `127.0.0.1:8765`:

- 17 same-origin files loaded with status 200, including the new `policy.mjs` and `schema.mjs`;
  no console message on load; no request off loopback.
- An external `fetch` probe was blocked by `connect-src 'none'` (enforce).
- "RUN ALL 100 CONTROLS" showed `100 / 100`. The packaged `customer-followup` fixture showed
  PASS / ALLOW* through the policy exemption.
- A case typed into the editor with `requires_human: false` for an external send and its own
  `policy` field showed FAIL with `NO_SYNTHETIC_HUMAN_APPROVAL · CASE_WAIVER_IGNORED`.
- The walkthrough's step 4 listed the withdrawn decision D3 with its turns and trace; the step 5
  report had `report_schema` 1.4.1 and one ledger entry. No horizontal overflow.
- Not repeated in V1.4.1: the full keyboard pass and the other CSP probes of V1.4 (the page
  structure and CSP did not change). Still not tested: screen readers, other browsers.
