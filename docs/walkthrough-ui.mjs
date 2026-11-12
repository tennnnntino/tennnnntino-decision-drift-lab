/* Five-step walkthrough of one fictional interrupted session. Local only.
   Every piece of case text reaches the page through textContent; nothing from the
   case is parsed as markup, evaluated or sent anywhere. */
import {WALKTHROUGH_CASE, WALKTHROUGH_SPLIT} from './walkthrough-case.mjs';
import {classifyRecovery, buildReport, revocationLedger} from './walkthrough.mjs';

const $ = id => document.getElementById(id);
const el = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
};
const ENCODER = new TextEncoder();
const DECODER = new TextDecoder();

const REASONS = {
  REVOKED_IN_SOURCE: 'Withdrawn during the conversation. Do not act on it.',
  REVOKED_TEXT_PRESENT_IN_HANDOFF: 'The note still contains the withdrawn wording.',
  REVOCATION_TRACE_NOT_VERBATIM_IN_HANDOFF: 'The note shows neither the decision nor its withdrawal word for word, so the next reader cannot see it was withdrawn.',
  NOT_VERBATIM_IN_HANDOFF: 'Not in the note word for word. It may be missing, changed or only reworded; an exact check cannot tell which.',
  UNCERTAIN_IN_SOURCE: 'Was unconfirmed in the conversation, so it stays unconfirmed.',
  AUTHORITY_NOT_TRANSFERABLE_BY_TEXT: 'Says who may approve, or what must not happen without approval. A note cannot carry that authority.',
  SUPERSEDED_VERSION_PRESENT_IN_HANDOFF: 'The note contains an earlier version that was corrected.',
};
const ROLE_LABEL = {statement: '', superseded: ' (corrected later)', revocation: ' (withdraws it)', qualification: ' (hedge)'};

const STEPS = [
  {title: '1 · The work so far',
    lead: 'Mara is arranging lighting hire with an assistant. Highlighted passages are the statements someone would act on. They are candidate labels drafted by a model; no person has reviewed them yet.'},
  {title: '2 · The interruption',
    lead: 'The session ends in the middle of the task. Whoever continues, a new session or a colleague, receives only this note.'},
  {title: '3 · What survived word for word',
    lead: 'These statements are in the note byte for byte, and nothing about them calls for a person. They can be carried forward together with their source reference.'},
  {title: '4 · What needs the owner',
    lead: 'Everything else goes back to Mara before anyone acts on it. The check is deliberately strict: a faithful rewording lands here too, because exact matching cannot judge meaning.'},
  {title: '5 · Evidence you can share',
    lead: 'An unsigned report: source references, review state, what the exact check found, and its limits. The digest lets a reader detect a changed case against a copy they already trust. It proves nothing about authorship or truth.'},
];

let step = 0;
let recovery = null;
let report = null;

function markedTurn(turn, spans) {
  const bytes = ENCODER.encode(turn.text);
  const para = el('p', 'wt-turn');
  para.append(el('strong', 'wt-speaker', `${turn.turn}. ${turn.speaker}: `));
  let cursor = 0;
  for (const span of [...spans].sort((a, b) => a.start_byte - b.start_byte)) {
    if (span.start_byte < cursor) continue; // overlapping label spans: show the first only
    para.append(DECODER.decode(bytes.slice(cursor, span.start_byte)));
    const mark = el('mark', `wt-mark wt-${span.role}`, DECODER.decode(bytes.slice(span.start_byte, span.end_byte)));
    para.append(mark, el('span', 'wt-tag', ` [${span.item_id}${ROLE_LABEL[span.role] ?? ''}]`));
    cursor = span.end_byte;
  }
  para.append(DECODER.decode(bytes.slice(cursor)));
  return para;
}

function statementOf(itemId) {
  return WALKTHROUGH_CASE.items.find(i => i.item_id === itemId).evidence.find(e => e.role === 'statement');
}

function renderBody() {
  const body = $('wt-body');
  body.replaceChildren();
  const c = WALKTHROUGH_CASE;
  if (step === 0) {
    for (const turn of c.source.turns) {
      const spans = c.items.flatMap(i => i.evidence.filter(e => e.turn === turn.turn).map(e => ({...e, item_id: i.item_id})));
      body.append(markedTurn(turn, spans));
    }
  } else if (step === 1) {
    body.append(el('blockquote', 'wt-note', c.handoff.text));
    body.append(el('p', 'quiet', 'The conversation itself is no longer available to the person or agent who picks this up.'));
  } else if (step === 2) {
    const list = el('ul', 'wt-list');
    for (const item of recovery.items.filter(i => i.recovery === 'RECOVERABLE_VERBATIM')) {
      const st = statementOf(item.item_id);
      const li = el('li', 'wt-ok');
      li.append(el('strong', '', `${item.item_id} · ${item.kind}`), el('span', '', ` “${st.excerpt}”`),
        el('small', '', `source: turn ${st.turn}, bytes ${st.start_byte}–${st.end_byte}`));
      list.append(li);
    }
    if (!list.children.length) list.append(el('li', '', 'Nothing survived word for word.'));
    body.append(list);
  } else if (step === 3) {
    const list = el('ul', 'wt-list');
    for (const item of recovery.items.filter(i => i.recovery !== 'RECOVERABLE_VERBATIM')) {
      const st = statementOf(item.item_id);
      const li = el('li', 'wt-ask');
      li.append(el('strong', '', `${item.item_id} · ${item.kind} · ${item.source_status}`), el('span', '', ` “${st.excerpt}”`));
      const why = el('ul', 'wt-reasons');
      for (const reason of item.reasons) why.append(el('li', '', REASONS[reason] ?? reason));
      li.append(why);
      list.append(li);
    }
    body.append(list);
    body.append(el('h5', 'wt-sub', 'Withdrawn decisions: the trace is kept whatever the note says'));
    const withdrawn = el('ul', 'wt-list');
    for (const entry of revocationLedger(c)) {
      const li = el('li', 'wt-ask');
      li.append(el('strong', '', `${entry.item_id} · withdrawn`), el('span', '', ` “${entry.statement_ref.excerpt}”`),
        el('small', '', `stated in turn ${entry.statement_ref.turn}; withdrawn in turn ${entry.revocation_refs.map(r => r.turn).join(', ')}; note: ${entry.trace}`));
      withdrawn.append(li);
    }
    if (!withdrawn.children.length) withdrawn.append(el('li', '', 'None in this conversation.'));
    body.append(withdrawn);
    body.append(el('h5', 'wt-sub', 'Sentences in the note with no word-for-word source'));
    const loose = el('ul', 'wt-list');
    for (const sentence of recovery.unanchored_handoff_statements) loose.append(el('li', 'wt-ask', `“${sentence.text}”`));
    if (!loose.children.length) loose.append(el('li', '', 'None.'));
    body.append(loose);
  } else {
    if (!report) { body.append(el('p', 'quiet', 'Preparing the report…')); return; }
    const facts = el('dl', 'wt-facts');
    const row = (term, value) => { facts.append(el('dt', '', term), el('dd', '', value)); };
    row('Case', `${report.case_ref.case_id} (${report.case_ref.split} split, synthetic)`);
    row('Label state', `${report.review.label_state} · review ${report.review.state} · not authenticated`);
    row('Carry forward', String(report.recovery.summary.recoverable_verbatim));
    row('Ask the owner', String(report.recovery.summary.owner_reconfirmation_required));
    row('Unanchored note sentences', String(report.recovery.summary.unanchored_handoff_statements));
    row('Input digest (SHA-256, not a signature)', report.input_digest.value);
    body.append(facts, el('pre', 'report-data', JSON.stringify(report, null, 2)));
  }
}

function render() {
  $('wt-title').textContent = STEPS[step].title;
  $('wt-lead').textContent = STEPS[step].lead;
  // The live region announces the new step; keyboard focus stays on the stepper so Enter keeps advancing.
  $('wt-progress').textContent = `Step ${step + 1} of ${STEPS.length}: ${STEPS[step].title.slice(4)}`;
  const back = $('wt-back'), next = $('wt-next');
  const focused = document.activeElement;
  back.disabled = step === 0;
  next.disabled = step === STEPS.length - 1;
  if (focused === next && next.disabled) back.focus();
  if (focused === back && back.disabled) next.focus();
  renderBody();
}

function download() {
  if (!report) return;
  const blob = new Blob([JSON.stringify(report, null, 2) + '\n'], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `handoff-evidence-${report.case_ref.case_id}.json`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function initWalkthrough() {
  try {
    recovery = classifyRecovery(WALKTHROUGH_CASE);
  } catch (error) {
    $('wt-lead').textContent = `Walkthrough unavailable: ${error.message}`;
    return;
  }
  $('wt-back').addEventListener('click', () => { if (step > 0) { step--; render(); } });
  $('wt-next').addEventListener('click', () => { if (step < STEPS.length - 1) { step++; render(); } });
  $('wt-download').addEventListener('click', download);
  render();
  buildReport(WALKTHROUGH_CASE, WALKTHROUGH_SPLIT).then(built => {
    report = built;
    $('wt-download').disabled = false;
    if (step === STEPS.length - 1) renderBody();
  }).catch(error => {
    $('wt-export-status').textContent = `Report unavailable: ${error.message}`;
  });
}
