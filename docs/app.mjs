import {initChallenge} from './challenge-ui.mjs';
import {strictJSON} from './strict-json.mjs';
import {initLocalChat} from './local-chat-ui.mjs';
import {initWalkthrough} from './walkthrough-ui.mjs';
import {PURPLE} from './purple.mjs';
import {CASES} from './cases.mjs';
import {evaluateCase, stableStringify} from './engine.mjs';
import {REVIEW} from './lenses.mjs';

const $=id=>document.getElementById(id);
let latest=null;
const FEATURED=['clean-handoff','silent-rewrite','agent-self-approval','fact-promotion','revoked-decision','scope-mismatch','customer-followup','support-triage','release-go-no-go','changed-authority'];
const LABELS={
  'clean-handoff':'01 · Clean handoff',
  'silent-rewrite':'02 · Silent rewrite',
  'agent-self-approval':'03 · Agent self-approval',
  'fact-promotion':'04 · Hypothesis → fact',
  'revoked-decision':'05 · Revoked decision',
  'scope-mismatch':'06 · Scope mismatch',
  'customer-followup':'07 · Commercial follow-up',
  'support-triage':'08 · Support triage',
  'release-go-no-go':'09 · Release gate',
  'changed-authority':'10 · Authority drift',
};
function formatPct(value){return value===null?'N/A':`${(value*100).toFixed(1)}%`;}
function addCodeList(target,entries){
  target.replaceChildren();
  if(!entries.length){const p=document.createElement('p');p.className='quiet';p.textContent='No findings detected in supplied structured items.';target.append(p);return;}
  for(const entry of entries){
    const row=document.createElement('div');row.className='finding';
    const badge=document.createElement('span');badge.className='finding-code';badge.textContent=entry.code;
    const id=document.createElement('span');id.textContent=entry.item_id;
    row.append(badge,id);target.append(row);
  }
}
function setText(id,text){$(id).textContent=String(text);}
function render(caseData,origin){
  try{
    const report=evaluateCase(caseData);
    latest={caseData,report};
    const okay=report.verdict==='PASS';
    setText('verdict',report.verdict);
    $('verdict').className=`outcome ${okay?'pass':'fail'}`;
    setText('verdict-context',okay?'No structural drift found in supplied items.':'Changes or simulated approval restrictions detected.');
    setText('metric-retained',report.facts.retained.length+report.decisions.retained.length);
    setText('metric-changed',report.facts.altered.length+report.decisions.altered.length);
    setText('metric-missing',report.facts.missing.length+report.decisions.missing.length);
    setText('metric-introduced',report.facts.introduced.length+report.decisions.introduced.length);
    setText('recall',formatPct(report.metrics.decision_exact_recall));
    setText('precision',formatPct(report.metrics.decision_exact_precision));
    setText('gate',report.approval_check.result==='ALLOW_IN_SIMULATION'?'ALLOW*':'BLOCK*');
    $('gate').className=`gate-badge ${report.approval_check.result==='ALLOW_IN_SIMULATION'?'allow':'block'}`;
    setText('gate-detail', report.approval_check.reasons.length?report.approval_check.reasons.join(' · '):'Synthetic fixture rule passed. No identity authentication.');
    setText('case-id',caseData.case_id??'custom');
    setText('case-domain',caseData.domain??'custom structured comparison');
    $('source-json').textContent=JSON.stringify(caseData.source,null,2);
    $('handoff-json').textContent=JSON.stringify(caseData.handoff,null,2);
    addCodeList($('findings'),report.findings);
    $('report-json').textContent=JSON.stringify(report,null,2);
    $('form-error').textContent='';
    setText('current-origin',origin);
  }catch(error){ $('form-error').textContent=`Evaluation blocked: ${error.message}`; }
}
function showTab(tab){
  document.querySelectorAll('[data-tab]').forEach(btn=>{
    const active=btn.dataset.tab===tab;
    btn.classList.toggle('selected',active);
    btn.setAttribute('aria-selected',String(active));
    btn.tabIndex=active?0:-1; // roving tabindex: one tab stop, arrows move between tabs
  });
  document.querySelectorAll('[data-panel]').forEach(el=>el.hidden=el.dataset.panel!==tab);
}
$('scenario').replaceChildren();
for(const id of FEATURED){const o=document.createElement('option');o.value=id;o.textContent=LABELS[id];$('scenario').append(o);}
$('scenario').addEventListener('change',()=>render(CASES[$('scenario').value],'packaged synthetic fixture'));
$('edit-input').addEventListener('click',()=>{
  $('custom-case').value=JSON.stringify(CASES[$('scenario').value],null,2);
  $('custom-case').focus();
});
$('run-custom').addEventListener('click',()=>{
  try{render(strictJSON($('custom-case').value),'local editable input · not transmitted');}
  catch(error){$('form-error').textContent=`Invalid JSON: ${error.message}`;}
});
$('download').addEventListener('click',()=>{
  if(!latest)return;
  const blob=new Blob([JSON.stringify(latest.report,null,2)+'\n'],{type:'application/json'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');a.href=url;a.download='decision-drift-report.json';a.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
});
document.querySelectorAll('[data-tab]').forEach(btn=>btn.addEventListener('click',()=>showTab(btn.dataset.tab)));
render(CASES['clean-handoff'],'packaged synthetic fixture');
initChallenge();
showTab('challenge');
document.getElementById('challenge-hero-action').addEventListener('click',()=>showTab('challenge'));
initLocalChat();
initWalkthrough();
// Keyboard support for the tab list (WAI-ARIA tabs pattern, automatic activation).
document.querySelector('.tabs').addEventListener('keydown',event=>{
  const tabs=[...document.querySelectorAll('[data-tab]')];
  const current=tabs.indexOf(document.activeElement);
  if(current<0)return;
  const target={ArrowRight:(current+1)%tabs.length,ArrowLeft:(current-1+tabs.length)%tabs.length,Home:0,End:tabs.length-1}[event.key];
  if(target===undefined)return;
  event.preventDefault();
  showTab(tabs[target].dataset.tab);
  tabs[target].focus();
});

// 20-lens self-review renders measured and untested states without fabricating endorsements.
const lensCounts={PASS:0,FAIL:0,NOT_TESTED:0,NOT_APPLICABLE:0};
for(const item of REVIEW.items){
  lensCounts[item.status]=(lensCounts[item.status]||0)+1;
  const card=document.createElement('article');card.className='lens-card';
  const head=document.createElement('div');head.className='lens-head';
  const id=document.createElement('span');id.textContent=item.id;
  const state=document.createElement('strong');state.textContent=item.status;state.className='lens-state '+item.status.toLowerCase();
  head.append(id,state);
  const title=document.createElement('h4');title.textContent=item.discipline;
  const details=document.createElement('p');details.textContent=item.justification;
  const ev=document.createElement('code');ev.textContent=item.evidence;
  card.append(head,title,details,ev);$('review-grid').append(card);
}
const summary=document.createElement('p');
summary.textContent=`${lensCounts.PASS} PASS · ${lensCounts.FAIL} FAIL · ${lensCounts.NOT_TESTED} NOT TESTED. This is a repository self-review, not a human certification.`;
$('review-summary').append(summary);

// Static *snapshot* only: test outcomes must be reproduced before any public claim.
for(const t of PURPLE.tests){
  const card=document.createElement('article');card.className='lens-card';
  const head=document.createElement('div');head.className='lens-head';
  const id=document.createElement('span');id.textContent=t.id;
  const status=document.createElement('strong');status.textContent='LOCAL TEST';status.className='lens-state not_tested';
  head.append(id,status);
  const title=document.createElement('h4');title.textContent=t.attack;
  const details=document.createElement('p');details.textContent=t.defense;
  card.append(head,title,details);$('purple-grid').append(card);
}
$('purple-summary').textContent=`${PURPLE.tests.length} synthetic adversarial checks · snapshot ${PURPLE.date} · no external security certification`;
