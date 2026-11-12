/* Shared observation helpers for the V1.4 Node tests and the Python parity test.
   Run directly (`node tests/v14-observe.mjs`) to print every JavaScript observation as JSON. */
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {CASES} from '../docs/cases.mjs';
import {CHALLENGE_DECK} from '../docs/challenge-deck.mjs';
import {evaluateCase} from '../docs/engine.mjs';
import {IntakeError, parseJsonStrict, readTextStrict} from '../docs/intake.mjs';
import {SchemaError, validate} from '../docs/schema.mjs';
import {buildReport, classifyRecovery, redact} from '../docs/walkthrough.mjs';

const root = new URL('../', import.meta.url);
export const readJson = relative => JSON.parse(readFileSync(new URL(relative, root), 'utf8'));
export const readText = relative => readFileSync(new URL(relative, root), 'utf8');

export function vectorBytes(vector) {
  if (vector.input_b64 !== undefined) return new Uint8Array(Buffer.from(vector.input_b64, 'base64'));
  if (vector.repeat) return new TextEncoder().encode(vector.repeat.unit.repeat(vector.repeat.count));
  return new TextEncoder().encode(vector.input_utf8);
}

export function observeIntake(vector) {
  try {
    (vector.kind === 'text' ? readTextStrict : parseJsonStrict)(vectorBytes(vector), vector.limits);
    return 'OK';
  } catch (error) {
    if (error instanceof IntakeError) return error.code;
    throw error;
  }
}

export function observeSchema(vector, caseSchema) {
  try {
    return validate(vector.instance, vector.schema === 'case' ? caseSchema : vector.inline_schema);
  } catch (error) {
    if (error instanceof SchemaError) return 'SCHEMA_ERROR';
    throw error;
  }
}

export function observeProbe(vector) {
  try {
    const report = evaluateCase(JSON.parse(vector.case_json));
    return {rejected: false, verdict: report.verdict, findings: report.findings.map(f => f.code).sort(),
      findings_in_order: report.findings.map(f => `${f.code}:${f.item_id}`),
      gate: report.approval_check.result, reasons: report.approval_check.reasons,
      advisories: report.advisories.map(a => a.code).sort(),
      ledger: report.revocation_ledger.map(e => [e.id, e.handoff_state]),
      decision_exact_recall: report.metrics.decision_exact_recall,
      change_order: report.facts.changes.map(c => c.id),
      text_profiles: ['facts', 'decisions'].flatMap(zone => report[zone].changes.filter(c => c.text_profile).map(c => c.text_profile))};
  } catch {
    return {rejected: true};
  }
}

export async function observeAll() {
  const caseSchema = readJson('contracts/case.schema.json');
  const corpus = ['dev', 'heldout'].flatMap(split =>
    readJson(`research/handoff-corpus-v1_4/${split}.json`).cases.map(c => ({split, c})));
  const reports = {};
  const recovery = {};
  for (const {split, c} of corpus) {
    recovery[c.case_id] = classifyRecovery(c);
    reports[c.case_id] = await buildReport(c, split);
  }
  return {
    intake: Object.fromEntries(readJson('contracts/intake-vectors.json').vectors.map(v => [v.id, observeIntake(v)])),
    schema: Object.fromEntries(readJson('contracts/schema-vectors.json').vectors.map(v => [v.id, observeSchema(v, caseSchema)])),
    redaction: Object.fromEntries(readJson('contracts/redaction-vectors.json').vectors.map(v => [v.id, redact(v.input)])),
    purple: Object.fromEntries(readJson('contracts/purple-v1_4-vectors.json').vectors.map(v => [v.id, observeProbe(v)])),
    recovery, reports,
    structured: Object.fromEntries([...Object.values(CASES), ...CHALLENGE_DECK.map(e => e.case)].map(c => {
      const {verdict, facts, decisions, approval_check, findings, advisories, revocation_ledger, metrics} = evaluateCase(c);
      return [c.case_id, {verdict, facts, decisions, approval_check, findings, advisories, revocation_ledger, metrics}];
    })),
  };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  process.stdout.write(JSON.stringify(await observeAll()));
}
