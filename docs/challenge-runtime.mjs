/* Independent browser-side runtime for generated, synthetic regression deck.
   These controls do NOT measure model accuracy, identity or production security. */
import {evaluateCase} from './engine.mjs';

export function runChallenge(deck) {
  if (!Array.isArray(deck) || deck.length !== 100) throw new Error('Expected exactly 100 generated controls');
  const seen = new Set();
  const rows = deck.map((entry) => {
    const c = entry.case, m = entry.meta;
    if (!c || !m || typeof c.case_id !== 'string' || seen.has(c.case_id)) throw new Error('Invalid or duplicate challenge case');
    seen.add(c.case_id);
    const report = evaluateCase(c);
    const findingCodes = new Set(report.findings.map(f => f.code));
    const gateReasons = new Set(report.approval_check.reasons);
    const requirementsMet = report.verdict === m.expected_verdict &&
      m.required_findings.every(f => findingCodes.has(f)) &&
      m.required_gate_reasons.every(r => gateReasons.has(r));
    return {case_id:c.case_id,context:m.context,attack:m.attack,category:m.category,
      expected:m.expected_verdict,actual:report.verdict,requirements_met:requirementsMet,
      finding_codes:[...findingCodes].sort(),gate_reasons:[...gateReasons].sort(),report};
  });
  return {protocol:'generated-challenge-v1',composition:'10 archetypes × 10 fictional operational contexts',
    claim_boundary:'Deterministic regression checks only; not independent empirical accuracy or penetration testing',
    total:rows.length,matched:rows.filter(r=>r.requirements_met).length,
    unmatched:rows.filter(r=>!r.requirements_met).map(r=>r.case_id),cases:rows};
}
