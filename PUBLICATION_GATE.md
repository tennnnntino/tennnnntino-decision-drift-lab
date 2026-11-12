# Publication gate (human decision required)

This package is a **candidate for publication**, not permission to publish.

- [ ] Confirm this is a **new repository** with no previous private history or remote.
- [ ] Confirm no other project name, architecture, owner credential or internal prompt appears in files or commit history.
- [ ] Confirm all demo records are synthetic and rights are clear.
- [ ] Confirm no `.env`, archives, logs, customer datasets, API keys or unreviewed binary assets.
- [ ] Run tests and benchmark on the intended machine and record the exact results.
- [ ] Test the static page with a local server, including narrow screens and keyboard navigation.
- [ ] Run an independent secret scan / repository security review before making it public.
- [ ] Decide the software license and contribution policy with due consideration of IP strategy.
- [ ] Have the project owner explicitly approve the specific publication version.
- [ ] Only then enable a public GitHub repository and optional static page hosting.

Never publish automatically and never copy a large existing private repository into a public one.


## Security additions before any public release

- [ ] Independently run the Python suite, 22 V1.2 Node regressions and 10 packaged fixtures on the publication artifact.
- [ ] Verify `SHA256SUMS.txt` from an independently retained trusted copy.
- [ ] Verify the V1.2 browser strict parser, including Unicode duplicate keys, and disclose residual parser limitations.
- [ ] Confirm local static page loads by real network serving with CSP intact.
- [ ] Run independently configured secret scanning and static code security analysis.
- [ ] Run a third-party or separate-reviewer challenge on synthetic data.
- [ ] Classify outstanding high/critical weaknesses and either fix or stop release.
- [ ] Verify no claims of actual authentication, full semantic equivalence or flawless security.
- [ ] Set up private vulnerability reporting before inviting community security testing.


## V1.2 mandatory gate — not completed

- [ ] Run the actual static app with CSP enabled over localhost or a staging host (environment blocked this here).
- [ ] Verify no outbound requests, unexpected browser persistence, or dangerous file access using real network instrumentation.
- [ ] Review accessibility and keyboard use with the new manual-review controls.
- [ ] Verify source byte offsets with an independent parser and stress-test Unicode edge cases.
- [ ] Run an independent dependency and secret audit and review artifact origin/rights.
- [ ] Confirm report wording never implies an authenticated approval or a complete chat export.
- [ ] Obtain explicit owner authorization for a **specific artifact** before public release.


## V1.3 specific release blockers

- [ ] Reproduce `python -m ddlab challenge --summary-only` and both Node suites on the exact ZIP bytes proposed for publication.
- [ ] Run Chromium over real localhost HTTP (not an in-memory CSP-bypassing harness), verify CSP, console, keyboard behavior, horizontal overflow, absence of outbound requests and file input protections.
- [ ] Verify that 100 case variants are described as generated controls rather than independent research samples.
- [ ] Review and approve `.github/workflows/verify.yml` and its pinned dependency before enabling CI in a public repository.
- [ ] Have a second person or independent scanner check the final ZIP for project identifiers, credentials and rights-unclear materials.
- [ ] No license, no production hardening certification and no independently observed operational outcome have yet been established.
- [ ] **OWNER explicitly authorizes a precise SHA-256 package hash and destination** before any publish, push or public hosting.


## V1.4 specific release blockers

Observed in V1.4, by the authoring session only, and therefore **not** ticked: real HTTP on `127.0.0.1` with the CSP enforced, no outbound request, keyboard operation, no horizontal overflow at three widths, in one Chromium-based browser (`docs/PURPLE_TEAM_V1_4.md`).

- [ ] A human reviews the candidate labels, or the corpus stays described everywhere as model-drafted candidates.
- [ ] Before any accuracy, precision, recall or "benchmark" wording: an independent held-out set written and labelled by someone who has not seen `ddlab/baselines.py`, with reviewer agreement reported.
- [ ] Confirm that no document, post or screenshot presents the review queue or the 37 cases as measured accuracy.
- [ ] Repeat the localhost and CSP check on a second machine and browser; add a screen-reader pass (not done at all in V1.4).
- [ ] Decide whether the two behaviour changes (unsafe numbers rejected; approvals must name scope and action) are acceptable for existing users of the V1.3 fixtures format.
- [ ] Second-person review of the 37 conversations for accidental resemblance to real people, organisations or events, and of all new files for project identifiers or secrets.
- [ ] Reproduce on the exact ZIP bytes: `python -m unittest discover -s tests -q` (107), the three Node suites (41), `python -m ddlab challenge --summary-only` (100/100), `python -m ddlab benchmark` (10/10), `python -m ddlab corpus snapshot` equal to the packaged results file, `sha256sum -c SHA256SUMS.txt`.
- [ ] No provider adapter, model call or real conversation is added without a separate, recorded privacy decision.
- [ ] No user-benefit or time-saving statement before an actual user trial (`research/USER_TRIAL_PROTOCOL_V1_4.md` has not been run).
- [ ] **OWNER explicitly authorizes the precise SHA-256 of the V1.4 package and the destination** before any publish, push or public hosting. License and reporting channel remain undecided.


## V1.4.1 specific release blockers

- [ ] Accept or reject the V1.4.1 behaviour change: a case with `requires_human: false` now passes only through a policy exemption, and one V1.0 test was rewritten accordingly.
- [ ] Review the packaged policy (`contracts/authorization-policy.json`): two exemptions, each with a rationale. Decide whether any exemption should ship at all.
- [ ] Confirm no text presents the simulated approval, the policy or a recorded review as authentication.
- [ ] Run the human labelling procedure (job A, then job B) or keep every description at "model-drafted candidates, no human review".
- [ ] After any human labelling: regenerate the results snapshot and the ProofPack, record adjudications outside the package, and re-run this gate.
- [ ] Reproduce on the exact ZIP bytes: `python -m unittest discover -s tests -q` (140), the three Node suites (43), `python -m ddlab challenge --summary-only` (100/100), `python -m ddlab benchmark` (10/10), `python -m ddlab corpus snapshot` and `python -m ddlab proofpack` equal to the packaged files, `sha256sum -c SHA256SUMS.txt`.
- [ ] Repeat the localhost and CSP check independently; screen-reader pass still not done.
- [ ] **OWNER explicitly authorizes the precise SHA-256 of the V1.4.1 package and the destination** before any publish, push or public hosting. License and reporting channel remain undecided.
