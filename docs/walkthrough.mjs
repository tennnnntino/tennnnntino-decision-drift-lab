/** Recovery classification and evidence report for an interrupted handoff (V1.4).
 * Browser mirror of ddlab/recovery.py and ddlab/evidence.py (profile "portable").
 * Pure functions: no DOM, no network, no storage. Case text is only ever compared,
 * sliced and copied as data.
 *
 * RECOVERABLE_VERBATIM means: the labelled source statement is in the handoff note
 * byte for byte, and it is not revoked, not uncertain, carries no authority, and no
 * superseded version of it is present. Everything else goes to the owner. This is
 * an exact-text check, not a judgement about meaning.
 */
import {stableStringify} from './engine.mjs';

export const REPORT_SCHEMA = '1.4.1';
export const MAX_EXCERPT = 200;
const RECOVERABLE = 'RECOVERABLE_VERBATIM';
const RECONFIRM = 'OWNER_RECONFIRMATION_REQUIRED';
const NOT_CARRIED_AMBIGUITY = 'Not carried into the handoff. The labelling policy does not count this as drift, but the next reader can no longer see that the decision was withdrawn. Confirm with the owner.';
const ENCODER = new TextEncoder();
const byteLength = text => ENCODER.encode(text).length;

const OUTCOME_CODES = {
  PRESERVED_VERBATIM: [], PRESERVED_PARAPHRASE: [], NOT_CARRIED_OK: [],
  ALTERED: ['{K}_ALTERED'], OMITTED: ['{K}_MISSING'],
  REACTIVATED: ['DECISIONS_ALTERED', 'REACTIVATED_DECISION'],
  PROMOTED: ['FACTS_ALTERED', 'UNSUPPORTED_FACT_PROMOTION'],
  AUTHORITY_CHANGED: ['DECISIONS_ALTERED', 'AUTHORITY_CHANGED'],
};

export const LIMITATIONS = Object.freeze([
  'Synthetic fiction only; nothing here was observed in a real workflow.',
  'Labels are candidates until a human review is recorded; a recorded review is an unauthenticated text field.',
  'Exact-text and rule-based comparators do not understand meaning; a faithful paraphrase is reported as a difference.',
  'A reworded reactivation, a changed scope or a dropped condition can go unnoticed by every comparator here.',
  'The revocation ledger records exact-text observations; a reworded mention of a withdrawal is not recognised.',
  'The digest is a SHA-256 of the canonical case JSON. It is not a signature, timestamp or proof of authorship or truth.',
  'Redaction is pattern-based (email, URL, long token, long digit run). It is not a data-loss-prevention control.',
  'No model was called and no action was executed, approved or authorised.',
]);

// ASCII-only classes and explicit lookarounds so Python and JavaScript agree exactly.
const REDACTIONS = [
  ['EMAIL', /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g],
  ['URL', /(?<![A-Za-z0-9])https?:\/\/[^ \t\r\n<>"']+/g],
  ['TOKEN', /(?<![A-Za-z0-9_-])(?=[A-Za-z0-9_-]*[0-9])(?=[A-Za-z0-9_-]*[A-Za-z])[A-Za-z0-9_-]{24,}(?![A-Za-z0-9_-])/g],
  ['NUMBER', /(?<![0-9])[0-9](?:[ -]?[0-9]){8,}(?![0-9])/g],
];

export function redact(text) {
  let count = 0;
  for (const [label, pattern] of REDACTIONS) {
    text = text.replace(pattern, () => { count++; return `[REDACTED:${label}]`; });
  }
  return {text, count};
}

/** Split after . ! ? followed by a space or the end. Offsets are UTF-8 bytes. */
export function splitSentences(text) {
  const out = [];
  const emit = (start, end) => {
    while (start < end && text[start] === ' ') start++;
    while (end > start && text[end - 1] === ' ') end--;
    if (end > start) out.push({text: text.slice(start, end), start_byte: byteLength(text.slice(0, start)), end_byte: byteLength(text.slice(0, end))});
  };
  let start = 0;
  for (let i = 0; i < text.length; i++) {
    if ('.!?'.includes(text[i]) && (i + 1 === text.length || text[i + 1] === ' ')) { emit(start, i + 1); start = i + 1; }
  }
  emit(start, text.length);
  return out;
}

const statementOf = item => {
  const statements = item.evidence.filter(e => e.role === 'statement');
  if (statements.length !== 1) throw new Error(`${item.item_id}: exactly one statement span is required`);
  return statements[0];
};

export function deriveFindings(c) {
  const codes = new Set();
  const zone = kind => (kind === 'decision' ? 'DECISIONS' : 'FACTS');
  for (const item of c.items) {
    const mapped = Object.hasOwn(OUTCOME_CODES, item.handoff_outcome) ? OUTCOME_CODES[item.handoff_outcome] : null;
    if (!mapped) throw new Error(`Unknown handoff outcome: ${item.handoff_outcome}`);
    for (const code of mapped) codes.add(code.replace('{K}', zone(item.kind)));
  }
  for (const extra of c.introduced) codes.add(`${zone(extra.kind)}_INTRODUCED`);
  return [...codes].sort();
}

export function exactText(c) {
  const handoff = c.handoff.text;
  const notVerbatim = c.items.filter(i => i.source_status !== 'REVOKED' && !handoff.includes(statementOf(i).excerpt)).map(i => i.item_id);
  return {drift: notVerbatim.length > 0, not_verbatim: notVerbatim};
}

export function classifyRecovery(c) {
  const handoff = c.handoff.text;
  const seen = new Set();
  const anchors = [];
  const items = c.items.map(item => {
    if (seen.has(item.item_id)) throw new Error(`duplicate item_id: ${item.item_id}`);
    seen.add(item.item_id);
    const statement = statementOf(item);
    const verbatim = handoff.includes(statement.excerpt);
    const reasons = [];
    if (item.source_status === 'REVOKED') {
      reasons.push('REVOKED_IN_SOURCE');
      if (verbatim) reasons.push('REVOKED_TEXT_PRESENT_IN_HANDOFF');
      // V1.4.1: the handoff shows neither the decision nor its withdrawal word for word.
      else if (!item.evidence.some(e => e.role === 'revocation' && handoff.includes(e.excerpt))) reasons.push('REVOCATION_TRACE_NOT_VERBATIM_IN_HANDOFF');
    } else if (!verbatim) reasons.push('NOT_VERBATIM_IN_HANDOFF');
    if (item.source_status === 'TO_CONFIRM') reasons.push('UNCERTAIN_IN_SOURCE');
    if (item.authority_bearing) reasons.push('AUTHORITY_NOT_TRANSFERABLE_BY_TEXT');
    if (item.evidence.some(e => e.role === 'superseded' && handoff.includes(e.excerpt))) reasons.push('SUPERSEDED_VERSION_PRESENT_IN_HANDOFF');
    const recovery = reasons.length ? RECONFIRM : RECOVERABLE;
    if (recovery === RECOVERABLE) anchors.push(statement.excerpt);
    return {item_id: item.item_id, kind: item.kind, source_status: item.source_status, recovery, reasons, verbatim_in_handoff: verbatim,
      source_ref: {turn: statement.turn, start_byte: statement.start_byte, end_byte: statement.end_byte}};
  });
  const unanchored = splitSentences(handoff).filter(s => !anchors.some(a => s.text.includes(a)));
  return {items, unanchored_handoff_statements: unanchored,
    summary: {recoverable_verbatim: items.filter(i => i.recovery === RECOVERABLE).length,
      owner_reconfirmation_required: items.filter(i => i.recovery === RECONFIRM).length,
      unanchored_handoff_statements: unanchored.length},
    method: 'exact-substring check on labelled source statements; no semantic evaluation'};
}

/** Every revoked decision with its source spans, whatever the handoff did with it (V1.4.1). */
export function revocationLedger(c) {
  const handoff = c.handoff.text;
  return c.items.filter(item => item.source_status === 'REVOKED').map(item => {
    const statement = statementOf(item);
    const revocations = item.evidence.filter(e => e.role === 'revocation');
    const stated = handoff.includes(statement.excerpt);
    const withdrawn = revocations.some(e => handoff.includes(e.excerpt));
    const trace = withdrawn ? 'REVOCATION_WORDING_PRESENT' : stated ? 'REVOKED_TEXT_PRESENT_WITHOUT_REVOCATION_WORDING' : 'NO_VERBATIM_TRACE_IN_HANDOFF';
    return {item_id: item.item_id, statement_ref: {...statement}, revocation_refs: revocations.map(e => ({...e})),
      statement_verbatim_in_handoff: stated, revocation_verbatim_in_handoff: withdrawn, trace, label_outcome: item.handoff_outcome,
      ambiguity: item.handoff_outcome === 'NOT_CARRIED_OK' ? NOT_CARRIED_AMBIGUITY : null};
  });
}

export async function sha256Hex(text) {
  const subtle = globalThis.crypto?.subtle;
  if (!subtle) throw new Error('SHA-256 is unavailable here; open the page from localhost or HTTPS');
  const digest = await subtle.digest('SHA-256', ENCODER.encode(text));
  return [...new Uint8Array(digest)].map(b => b.toString(16).padStart(2, '0')).join('');
}

/** Unsigned, data-minimised report. Same content as ddlab.evidence.build_report(profile="portable"). */
export async function buildReport(c, split, {includeText = false} = {}) {
  let replacements = 0;
  const clip = text => {
    const r = redact(text);
    replacements += r.count;
    const points = Array.from(r.text);
    return points.length <= MAX_EXCERPT ? r.text : points.slice(0, MAX_EXCERPT).join('') + '…';
  };
  const ref = (span, withTurn) => span === null ? null : {
    ...(withTurn ? {turn: span.turn, role: span.role} : {}),
    start_byte: span.start_byte, end_byte: span.end_byte, excerpt: clip(span.excerpt)};
  const samples = c.items.map(i => ({item_id: i.item_id, kind: i.kind, source_status: i.source_status,
    authority_bearing: i.authority_bearing, label_outcome: i.handoff_outcome,
    source_refs: i.evidence.map(e => ref(e, true)), handoff_ref: ref(i.handoff_evidence, false)}));
  const introduced = c.introduced.map(x => ({item_id: x.item_id, kind: x.kind, handoff_ref: ref(x.handoff_evidence, false)}));
  const comparators = {label_findings: deriveFindings(c), exact_text: exactText(c),
    rule_based: {status: 'PYTHON_ONLY'}, structured_transfer: {status: 'PYTHON_ONLY'}};
  const recovery = classifyRecovery(c);
  for (const sentence of recovery.unanchored_handoff_statements) sentence.text = clip(sentence.text);
  const ledger = revocationLedger(c).map(entry => ({...entry, statement_ref: ref(entry.statement_ref, true), revocation_refs: entry.revocation_refs.map(e => ref(e, true))}));
  const report = {
    report_type: 'synthetic-handoff-evidence-report', report_schema: REPORT_SCHEMA, profile: 'portable', synthetic_only: true,
    case_ref: {corpus: 'handoff-corpus-v1.4', split, case_id: c.case_id, domain: c.domain, title: clip(c.title)},
    input_digest: {algorithm: 'sha256', value: await sha256Hex(stableStringify(c)),
      scope: 'canonical JSON of the case object (sorted keys, compact separators, UTF-8)', is_signature: false},
    review: {label_state: c.label_state, state: c.review.state, reviewer_label: c.review.reviewer_label,
      reviewed_on: c.review.reviewed_on, authenticated: false},
    samples, introduced, candidate_extraction: {status: 'PYTHON_ONLY'}, comparators, recovery, revocation_ledger: ledger,
    limitations: [...LIMITATIONS],
    attestation: {signed: false, statement: 'Unsigned. Compare input_digest with a copy you already trust; it cannot vouch for itself.'},
  };
  if (includeText) {
    report.full_text = {turns: c.source.turns.map(t => ({turn: t.turn, speaker: clip(t.speaker), text: clip(t.text)})), handoff: clip(c.handoff.text)};
  }
  report.redaction = {method: 'pattern-based: EMAIL, URL, TOKEN, NUMBER', replacements, full_text_included: includeText};
  return report;
}
