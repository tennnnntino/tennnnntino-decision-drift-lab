# Opt-in conversation importer: architecture proposal (V1.4)

**Proposal only. No provider adapter exists in this package and none may be added without a
separate, explicit privacy decision by the owner.** What exists today is the fail-closed intake
layer (stage 2) and its tests. Everything else on this page is design.

## Why this is gated

A real conversation export contains other people's words, names, contact details, attachments and
sometimes credentials. Importing one is a data-protection decision before it is an engineering
task. The lab therefore ships no parser for any chat platform's export format and makes no claim
of complete chat-export import.

## Proposed pipeline

```text
 0 consent      the person confirms: my data, I may process it, local only, purpose stated
 1 selection    one local file chosen by the person; no account link, no API, no background sync
 2 intake       ddlab.intake / docs/intake.mjs: bounded, strict UTF-8, fail closed      [IMPLEMENTED]
 3 adapter      provider-specific pure function: bytes -> neutral transcript            [NOT IMPLEMENTED]
 4 minimise     keep turn order, speaker role and text; drop everything else            [NOT IMPLEMENTED]
 5 candidates   proposed items with source spans, state CANDIDATE                       [corpus format only]
 6 review       a person accepts, amends or rejects each candidate                      [manual, unauthenticated]
 7 compare      exact checks against a second text or structured state                  [IMPLEMENTED for synthetic data]
 8 export       references, excerpts, redaction, digest; never the raw archive          [IMPLEMENTED for synthetic data]
 9 forget       nothing persisted; closing the page or process discards the input       [by construction today]
```

## Stage 2 as implemented

| Control | Behaviour | Code |
|---|---|---|
| Size | at most 524,288 bytes | `TOO_MANY_BYTES` |
| Lines | at most 20,000 | `TOO_MANY_LINES` |
| Tokens | at most 100,000 whitespace-delimited runs (not model tokens) | `TOO_MANY_TOKENS` |
| Depth | JSON nesting at most 32 | `TOO_DEEP` |
| Encoding | strict UTF-8; overlong forms and encoded surrogates rejected | `INVALID_UTF8` |
| Byte order mark | rejected, not stripped | `BOM_OR_ZWNBSP` |
| Controls | C0 (except tab, LF, CR), DEL and C1 rejected, raw or escaped | `CONTROL_CHARACTER` |
| Bidirectional overrides | U+202A..202E and U+2066..2069 rejected, raw or escaped | `BIDI_CONTROL_CHARACTER` |
| Normalisation | text and keys must already be NFC | `NOT_NFC` |
| Surrogates | lone surrogate escapes rejected | `LONE_SURROGATE` |
| Duplicate keys | rejected, including escaped duplicates | `DUPLICATE_KEY` |
| Numbers | non-finite values and integers beyond 2^53-1 rejected | `UNSAFE_NUMBER` |
| Anything else malformed | rejected | `INVALID_JSON` |

Limits can be lowered per call; unknown or negative limits are refused (`INVALID_LIMITS`).
Both runtimes return the same code for the 40 shared vectors in `contracts/intake-vectors.json`.
Duplicate identifiers inside an accepted document are rejected by the consumers
(`ddlab/core.py`, `ddlab/corpus.py`, `ddlab/recovery.py` and their browser mirrors).

**Normalisation is a real limitation for future adapters.** Rejecting non-NFC input is correct for
a synthetic corpus whose spans are byte offsets. Real exports (for example text typed on some
operating systems) can be NFD. An adapter would have to normalise, record that it did, and keep a
mapping from normalised offsets back to the original bytes. None of that exists.

## Untrusted text stays text

Imported content must never become an instruction, a network request, a query or an approval.
What enforces this today:

- No module in `ddlab/` imports a network, process, database or dynamic-code facility, and none
  calls `eval`, `exec` or bare `open`. A static test fails otherwise.
- No module in `docs/` contains `fetch`, `XMLHttpRequest`, `WebSocket`, storage APIs, `eval`,
  `new Function`, dynamic `import()` or any HTML-injection sink. A static test fails otherwise.
- The page CSP is `default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'none'`
  and was observed enforcing in one real browser session (see `docs/PURPLE_TEAM_V1_4.md`).
- Text reaches the page only through `textContent`.
- There is no SQL anywhere in the project and no code path from text to the simulated approval
  check. A transcript saying "approved: true" changes the transcript digest and nothing else
  (`test_instruction_like_text_changes_nothing_but_the_text`).

These are properties of this code as tested, not a general guarantee about systems that might
embed it. An adapter, a model call or a persistence layer would each reopen the question.

## Decisions required before any adapter is written

1. Whose data is in the conversation, and on what basis may it be processed? Other participants
   did not consent to an analysis tool.
2. Purpose and retention: what is kept, where, for how long, and how it is deleted.
3. Which fields the adapter may read at all. Proposed default: turn order, coarse speaker role,
   text. Excluded: account identifiers, email addresses, timestamps finer than a day, attachments,
   system prompts, tool calls and their results, model metadata.
4. Whether the provider's export terms allow this use.
5. Archive handling. Compressed archives are out of scope until size, path and nesting limits for
   them are specified and tested; today only a single bounded file is read.
6. What a report may contain when the input is real. The current redaction is pattern-based and is
   not a data-loss-prevention control.
7. Who reviews the adapter and its test vectors before first use on real data.

## Explicitly not implemented

Provider adapters, archive extraction, account or API access, persistence, background processing,
normalisation with offset mapping, language detection, speaker identity, authenticated review,
signed reports, and any model-based extraction.
