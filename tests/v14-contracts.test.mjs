import test from 'node:test';
import assert from 'node:assert/strict';
import {readdirSync} from 'node:fs';
import {CASES} from '../docs/cases.mjs';
import {CHALLENGE_DECK} from '../docs/challenge-deck.mjs';
import {validate} from '../docs/schema.mjs';
import {DEFAULT_LIMITS, IntakeError, readTextStrict} from '../docs/intake.mjs';
import {buildReport, classifyRecovery, redact, splitSentences} from '../docs/walkthrough.mjs';
import {WALKTHROUGH_CASE, WALKTHROUGH_SPLIT} from '../docs/walkthrough-case.mjs';
import {observeIntake, observeProbe, observeSchema, readJson, readText} from './v14-observe.mjs';

const html = readText('docs/index.html');
const caseSchema = readJson('contracts/case.schema.json');

test('V14-I: every shared intake vector yields the declared code', () => {
  const vectors = readJson('contracts/intake-vectors.json').vectors;
  assert.ok(vectors.length >= 40);
  for (const v of vectors) assert.equal(observeIntake(v), v.expect, `${v.id}: ${v.why}`);
});
test('V14-I: declared default bounds and non-byte input refusal', () => {
  assert.deepEqual({...DEFAULT_LIMITS}, {max_bytes: 524288, max_lines: 20000, max_tokens: 100000, max_depth: 32});
  assert.throws(() => readTextStrict('already decoded'), error => error instanceof IntakeError && error.code === 'EXPECTED_BYTES');
});
test('V14-S: every shared schema vector yields the declared violations', () => {
  const vectors = readJson('contracts/schema-vectors.json').vectors;
  assert.ok(vectors.length >= 26);
  for (const v of vectors) assert.deepEqual(observeSchema(v, caseSchema), v.expect, `${v.id}: ${v.why}`);
});
test('V14-S: all 10 fixtures and 100 generated controls satisfy the case schema', () => {
  const cases = [...Object.values(CASES), ...CHALLENGE_DECK.map(e => e.case)];
  assert.equal(cases.length, 110);
  for (const c of cases) assert.deepEqual(validate(c, caseSchema), [], c.case_id);
});
test('V14-S: both corpus splits satisfy the corpus schema', () => {
  const schema = readJson('contracts/handoff-corpus.schema.json');
  for (const split of ['dev', 'heldout']) assert.deepEqual(validate(readJson(`research/handoff-corpus-v1_4/${split}.json`), schema), [], split);
});
test('V14-R: every shared redaction vector', () => {
  for (const v of readJson('contracts/redaction-vectors.json').vectors) {
    assert.deepEqual(redact(v.input), {text: v.output, count: v.replacements}, v.id);
  }
});
test('V14-P: purple-team probes behave as recorded after the fixes', () => {
  const doc = readJson('contracts/purple-v1_4-vectors.json');
  assert.equal(doc.vectors.length, 28);
  for (const v of doc.vectors) assert.deepEqual(observeProbe(v), v.expected, `${v.id}: ${v.title}`);
  const fixed = doc.vectors.filter(v => v.status.startsWith('FIXED_IN_'));
  assert.equal(fixed.length, 23);
  // Every fixed probe really behaved differently in at least one runtime of the version it was fixed from.
  for (const v of fixed) {
    const before = v.status === 'FIXED_IN_V1_4' ? v.observed_v1_3 : v.observed_v1_4;
    assert.ok(JSON.stringify(before.python) !== JSON.stringify(v.expected) || JSON.stringify(before.javascript) !== JSON.stringify(v.expected), v.id);
  }
  assert.deepEqual(doc.vectors.filter(v => v.status === 'OPEN_LIMITATION').map(v => v.id), ['P08', 'P19']);
  assert.deepEqual(doc.observed.python_hash_seed_variation_p17.v1_4_1, {seeds_tried: 12, distinct_finding_orders: 1, distinct_report_digests: 1});
});
test('V14-W: walkthrough case separates verbatim survivors from owner reconfirmation', () => {
  const result = classifyRecovery(WALKTHROUGH_CASE);
  assert.deepEqual(result.items.filter(i => i.recovery === 'RECOVERABLE_VERBATIM').map(i => i.item_id), ['D1', 'D2']);
  assert.deepEqual(result.summary, {recoverable_verbatim: 2, owner_reconfirmation_required: 5, unanchored_handoff_statements: 4});
  assert.throws(() => classifyRecovery({...WALKTHROUGH_CASE, items: [WALKTHROUGH_CASE.items[0], WALKTHROUGH_CASE.items[0]]}), /duplicate item_id/);
});
test('V14-W: browser report satisfies the report schema and claims nothing it cannot back', async () => {
  const report = await buildReport(WALKTHROUGH_CASE, WALKTHROUGH_SPLIT);
  assert.deepEqual(validate(report, readJson('contracts/evidence-report.schema.json')), []);
  assert.equal(report.attestation.signed, false);
  assert.equal(report.input_digest.is_signature, false);
  assert.equal(report.review.authenticated, false);
  assert.equal(report.review.state, 'NOT_REVIEWED');
  assert.equal(Object.hasOwn(report, 'full_text'), false);
  assert.match(report.input_digest.value, /^[0-9a-f]{64}$/);
});
test('V14-W: sentence offsets are UTF-8 bytes', () => {
  const text = 'Costs 0.42 per unit. Café at 15:00! Done';
  const parts = splitSentences(text);
  assert.deepEqual(parts.map(p => p.text), ['Costs 0.42 per unit.', 'Café at 15:00!', 'Done']);
  const raw = new TextEncoder().encode(text);
  for (const p of parts) assert.equal(new TextDecoder().decode(raw.slice(p.start_byte, p.end_byte)), p.text);
});
test('V14-N: no browser module can reach the network, storage or dynamic code', () => {
  const forbidden = ['fetch(', 'XMLHttpRequest', 'WebSocket', 'sendBeacon', 'EventSource', 'importScripts', 'import(',
    'eval(', 'new Function', 'innerHTML', 'outerHTML', 'insertAdjacentHTML', 'document.write', 'localStorage',
    'sessionStorage', 'indexedDB', 'document.cookie', 'setAttribute(\'on', 'http://', 'https://'];
  const modules = readdirSync(new URL('../docs/', import.meta.url)).filter(name => name.endsWith('.mjs'));
  assert.ok(modules.includes('walkthrough-ui.mjs') && modules.includes('intake.mjs') && modules.includes('policy.mjs'));
  for (const name of modules) {
    const source = readText(`docs/${name}`);
    for (const token of forbidden) assert.equal(source.includes(token), false, `${name} contains ${token}`);
  }
});
test('V14-N: page keeps a restrictive CSP and loads only same-origin files', () => {
  const csp = /<meta http-equiv="Content-Security-Policy" content="([^"]+)">/.exec(html)?.[1] ?? '';
  for (const directive of ["default-src 'none'", "script-src 'self'", "style-src 'self'", "connect-src 'none'", "base-uri 'none'", "form-action 'none'"]) {
    assert.ok(csp.includes(directive), directive);
  }
  assert.equal(/unsafe-inline|unsafe-eval|\*/.test(csp), false);
  assert.equal(/\son[a-z]+=/i.test(html), false, 'no inline event handlers');
  assert.equal(/<script(?![^>]*\ssrc="app\.mjs")/.test(html), false, 'only the module entry point');
  assert.equal(/style="/.test(html), false, 'no inline styles');
});
test('V14-A: tabs follow the ARIA tabs pattern', () => {
  const tabs = [...html.matchAll(/<button type="button"( class="selected")? role="tab" aria-selected="(true|false)" data-tab="([a-z]+)" id="tab-([a-z]+)" aria-controls="panel-([a-z]+)">/g)];
  assert.equal(tabs.length, 9);
  assert.equal(tabs.filter(t => t[2] === 'true').length, 1);
  for (const [, , , name, id, controls] of tabs) {
    assert.equal(id, name);
    assert.equal(controls, name);
    assert.ok(html.includes(`data-panel="${name}" id="panel-${name}" role="tabpanel" aria-labelledby="tab-${name}" tabindex="0"`), name);
  }
  assert.ok(/<nav class="tabs" role="tablist" aria-label="[^"]+">/.test(html));
  const app = readText('docs/app.mjs');
  for (const key of ['ArrowRight', 'ArrowLeft', 'Home', 'End']) assert.ok(app.includes(key), key);
  assert.ok(app.includes('btn.tabIndex=active?0:-1'));
});
test('V14-A: controls are reachable and named for keyboard and screen-reader users', () => {
  for (const button of html.matchAll(/<button\b[^>]*>/g)) assert.ok(button[0].includes('type="button"'), button[0]);
  for (const field of html.matchAll(/<(textarea|select)\b[^>]*>/g)) {
    const id = /\sid="([^"]+)"/.exec(field[0])?.[1];
    assert.ok(/aria-label="[^"]+"/.test(field[0]) || html.includes(`<label for="${id}"`), field[0]);
  }
  for (const input of html.matchAll(/<input\b[^>]*>/g)) {
    const id = /\sid="([^"]+)"/.exec(input[0])?.[1];
    assert.ok(html.includes(`<label for="${id}"`) || html.includes(`<label>${input[0]}`), input[0]);
  }
  assert.ok(html.includes('<a class="skip-link" href="#workspace">'));
  assert.ok(html.includes('<html lang="en">'));
  assert.ok(html.includes('id="wt-progress" role="status" aria-live="polite"'));
  assert.ok(html.includes('id="wt-stage" class="audit-panel wt-stage" aria-labelledby="wt-title" tabindex="-1"'));
  const css = readText('docs/style.css');
  assert.ok(css.includes('[role=tabpanel]:focus-visible') && css.includes('button:focus-visible'));
  assert.ok(css.includes('prefers-reduced-motion'));
});
test('V14-A: walkthrough text never enters the page as markup', () => {
  const ui = readText('docs/walkthrough-ui.mjs');
  assert.ok(ui.includes('textContent'));
  assert.equal(/\.html\(|DOMParser|createContextualFragment|srcdoc/.test(ui), false);
});
test('V141-P: browser engine takes the approval requirement from the external policy only', async () => {
  const {evaluateCase, checkPolicy} = await import('../docs/engine.mjs');
  const {DEFAULT_POLICY} = await import('../docs/policy.mjs');
  const decision = {id: 'D1', text: 'Draft only, never send without human approval', authority: 'OWNER', status: 'ACTIVE'};
  const make = action => ({case_id: 't', source: {decisions: [{...decision}]}, handoff: {decisions: [{...decision}]}, action});
  const waived = evaluateCase({...make({name: 'send-external-email', scope: 'external', requires_human: false}), policy: {default: 'NO_APPROVAL_REQUIRED'}});
  assert.equal(waived.verdict, 'FAIL');
  assert.deepEqual(waived.approval_check.reasons, ['NO_SYNTHETIC_HUMAN_APPROVAL', 'CASE_WAIVER_IGNORED']);
  assert.equal(waived.approval_check.requirement_source, 'EXTERNAL_POLICY');
  assert.equal(waived.approval_check.authenticated, false);
  assert.deepEqual(waived.advisories, [{code: 'CASE_POLICY_FIELD_IGNORED', item_id: 'policy'}]);
  assert.equal(evaluateCase(make({name: 'prepare-draft', scope: 'internal', requires_human: false})).verdict, 'PASS');
  const strict = {policy_id: 'no-exemptions', policy_version: '1.0', default: 'HUMAN_APPROVAL_REQUIRED', exempt_actions: []};
  assert.equal(evaluateCase(make({name: 'prepare-draft', scope: 'internal', requires_human: false}), strict).verdict, 'FAIL');
  assert.throws(() => checkPolicy({...strict, default: 'NO_APPROVAL_REQUIRED'}), /Policy schema/);
  assert.throws(() => evaluateCase(make({}), {...DEFAULT_POLICY, extra: 1}), /Policy schema/);
});
test('V141-L: browser report and walkthrough keep the revocation trace', async () => {
  const {revocationLedger} = await import('../docs/walkthrough.mjs');
  const dev = readJson('research/handoff-corpus-v1_4/dev.json').cases;
  const hd07 = dev.find(c => c.case_id === 'HD-07');
  const [entry] = revocationLedger(hd07);
  assert.equal(entry.trace, 'NO_VERBATIM_TRACE_IN_HANDOFF');
  assert.match(entry.ambiguity, /Confirm with the owner/);
  const report = await buildReport(hd07, 'dev');
  assert.equal(report.revocation_ledger.length, 1);
  assert.ok(report.recovery.items.find(i => i.item_id === 'D2').reasons.includes('REVOCATION_TRACE_NOT_VERBATIM_IN_HANDOFF'));
  assert.deepEqual(validate(report, readJson('contracts/evidence-report.schema.json')), []);
  assert.equal(revocationLedger(WALKTHROUGH_CASE)[0].trace, 'REVOKED_TEXT_PRESENT_WITHOUT_REVOCATION_WORDING');
});
