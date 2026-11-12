/* Local one-click interactive comparison: no network, no user-derived HTML. */
import {CHALLENGE_DECK} from './challenge-deck.mjs';
import {runChallenge} from './challenge-runtime.mjs';

const $=id=>document.getElementById(id);
const DOWNLOAD_TIMEOUT_MS=1000;
let result=null;
let selected='C01-01';
const byId=new Map(CHALLENGE_DECK.map(e=>[e.case.case_id,e]));

function text(id,value){$(id).textContent=String(value);}
function downloadData(data, filename){
  const blob=new Blob([JSON.stringify(data,null,2)+'\n'],{type:'application/json'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');a.href=url;a.download=filename;a.click();
  setTimeout(()=>URL.revokeObjectURL(url),DOWNLOAD_TIMEOUT_MS);
}
function prepareSelector(){
  const domains=[...new Map(CHALLENGE_DECK.map(e=>[e.meta.context,e.case.domain])).entries()];
  const attacks=[...new Map(CHALLENGE_DECK.map(e=>[e.meta.attack,e.meta.title])).entries()];
  const options=(id,values)=>{
    for(const [value,label] of values){const opt=document.createElement('option');opt.value=value;opt.textContent=label;$(id).append(opt);}
  };
  options('challenge-context', [['all','All 10 contexts'],...domains]);
  options('challenge-attack', [['all','All 10 attack archetypes'],...attacks]);
}
function inspect(id){
  const entry=byId.get(id);if(!entry)return;
  selected=id;
  const {case:c,meta:m}=entry;
  const row=result?.cases.find(r=>r.case_id===id);
  text('challenge-selected',`${id} / ${m.title}`);
  text('challenge-selected-domain',c.domain.toUpperCase());
  text('challenge-story',m.explanation);
  text('challenge-before',JSON.stringify(c.source,null,2));
  text('challenge-after',JSON.stringify(c.handoff,null,2));
  text('challenge-action',JSON.stringify(c.action,null,2));
  if(row){
    const found=[...row.finding_codes,...row.gate_reasons];
    text('challenge-detection',found.length?found.join('  ·  '):'No structural drift detected');
    text('challenge-expected',`${m.expected_verdict} EXPECTED  /  ${row.actual} OBSERVED`);
    $('challenge-expected').className=row.requirements_met?'check-matched':'check-unmatched';
    $('challenge-selected-state').textContent=row.requirements_met?'CONTROL MATCHED':'CONTROL MISMATCH';
    $('challenge-selected-state').className=row.requirements_met?'state-ok':'state-risk';
  }else{
    text('challenge-detection','Run the controls to compare expected and observed behavior.');
    text('challenge-expected',`${m.expected_verdict} EXPECTED · NOT RUN`);
    text('challenge-selected-state','NOT RUN');
    $('challenge-selected-state').className='state-idle';
  }
  document.querySelectorAll('.challenge-cell').forEach(b=>b.classList.toggle('active',b.dataset.id===id));
}
function drawGrid(){
  const ctx=$('challenge-context').value,atk=$('challenge-attack').value;
  const entries=CHALLENGE_DECK.filter(e=>(ctx==='all'||e.meta.context===ctx)&&(atk==='all'||e.meta.attack===atk));
  const target=$('challenge-grid');target.replaceChildren();
  for(const e of entries){
    const row=result?.cases.find(r=>r.case_id===e.case.case_id);
    const btn=document.createElement('button');btn.type='button';btn.dataset.id=e.case.case_id;
    btn.className=`challenge-cell ${row?(row.requirements_met?(row.actual==='PASS'?'control-pass':'control-block'):'control-miss'):'control-untested'}`;
    if(e.case.case_id===selected)btn.classList.add('active');
    btn.textContent=e.case.case_id;
    btn.title=`${e.case.domain}: ${e.meta.title} · ${row?(row.requirements_met?'matched':'mismatch'):'not run'}`;
    btn.setAttribute('aria-label',btn.title);
    btn.addEventListener('click',()=>inspect(e.case.case_id));
    target.append(btn);
  }
  text('challenge-visible',`${entries.length} displayed / 100 generated cases`);
  if(entries.length && !entries.some(e=>e.case.case_id===selected))inspect(entries[0].case.case_id);
}
export function initChallenge(){
  prepareSelector();
  $('challenge-context').addEventListener('change',drawGrid);
  $('challenge-attack').addEventListener('change',drawGrid);
  $('challenge-run').addEventListener('click',()=>{
    const started=performance.now();
    try{
      result=runChallenge(CHALLENGE_DECK);
      const elapsed=Math.round((performance.now()-started)*10)/10;
      text('challenge-counter',`${result.matched} / ${result.total}`);
      text('challenge-runtime',`${elapsed.toFixed(1)} ms · THIS BROWSER`);
      text('challenge-status',result.unmatched.length?'MISMATCHES REQUIRE REVIEW':'ALL GENERATED CONTROLS MATCH');
      $('challenge-status').className=result.unmatched.length?'risk-text':'good-text';
      text('challenge-run-status',`Executed locally: ${result.matched}/${result.total} expected outcomes and required signals matched. This is regression coverage, not model accuracy.`);
      $('challenge-export').disabled=false;
      drawGrid();inspect(selected);
    }catch(error){text('challenge-run-status',`Unable to complete: ${error.message}`);}
  });
  $('challenge-export').addEventListener('click',()=>{
    if(!result)return;
    const {cases,...meta}=result;
    // Deliberately omit full input content: synthetic compact reproducible summary only.
    downloadData({...meta,cases:cases.map(({report,...row})=>row)},'decision-drift-lab-generated-challenge-results.json');
  });
  $('challenge-case-export').addEventListener('click',()=>{
    const entry=byId.get(selected);if(entry)downloadData(entry.case,`${selected.toLowerCase()}-synthetic.json`);
  });
  drawGrid();inspect(selected);
}
