import {extractChatCandidates,localReview,compareReviewedCandidates,SYNTHETIC_CHAT,MAX_CHAT_BYTES} from './chat-workflow.mjs';
const chatEl=id=>document.getElementById(id);
let state=null, lastReport=null;
function setStatus(message){chatEl('chat-status').textContent=message;}
function clearReview(){state=null;lastReport=null;chatEl('chat-source-items').replaceChildren();chatEl('chat-target-items').replaceChildren();chatEl('chat-results').textContent='No comparison yet.';}
function sourceList(target,records,key){
  target.replaceChildren();
  if(!records.length){const p=document.createElement('p');p.textContent='No explicit markers found — extraction incomplete or unsupported format.';target.append(p);return;}
  for(let i=0;i<records.length;i++){
    const item=records[i],card=document.createElement('div');card.className='chat-candidate';
    const label=document.createElement('strong');label.textContent=`${item.kind} [${item.id}] · ${item.speaker} · line ${item.span.line} · bytes ${item.span.start_byte}-${item.span.end_byte}`;
    const body=document.createElement('p');body.textContent=item.text;
    const flag=document.createElement('small');flag.textContent=item.revocation_cited?'REVOCATION MARKER FOUND — REVIEW ONLY':item.conflict?'DUPLICATE ID — REVIEW ONLY':'UNVERIFIED CANDIDATE';
    const select=document.createElement('select');select.setAttribute('aria-label',`Local review ${key} ${item.kind} ${item.id}`);
    for(const [value,caption] of [['CANDIDATE','Not reviewed'],['ACCEPTED_FOR_COMPARISON','Include in exact comparison'],['MANUAL_REVIEW','Needs further human review'],['REJECTED','Reject candidate']]){
      const o=document.createElement('option');o.value=value;o.textContent=caption;select.append(o);
    }
    select.addEventListener('change',()=>{
      try{records[i] = select.value==='CANDIDATE'?{...item,state:'CANDIDATE'}:localReview({...records[i],state:'CANDIDATE'},select.value);
        lastReport=null;chatEl('chat-results').textContent='Review changed. Run comparison again.';setStatus('Local review updated (not authenticated).');}
      catch(e){select.value=records[i].state;setStatus(`Review blocked: ${e.message}`);}
    });
    card.append(label,body,flag,select);target.append(card);
  }
}
function analyse(){
  clearReview();
  if(!chatEl('chat-consent').checked){setStatus('Please acknowledge synthetic-only, local processing first.');return;}
  try{
    const source=extractChatCandidates(chatEl('chat-source').value);
    const handoff=extractChatCandidates(chatEl('chat-target').value);
    state={source,handoff};
    sourceList(chatEl('chat-source-items'),source.candidates,'source');
    sourceList(chatEl('chat-target-items'),handoff.candidates,'handoff');
    setStatus(`${source.candidates.length} source / ${handoff.candidates.length} target candidates. ${source.unresolvedRevocations.length+handoff.unresolvedRevocations.length} unresolved revocations. Review individually.`);
  }catch(e){setStatus(`Extraction blocked: ${e.message}`);}
}
function compare(){
  if(!state){setStatus('First extract and review the candidates.');return;}
  if(state.source.unresolvedRevocations.length||state.handoff.unresolvedRevocations.length){setStatus('Unresolved revocation marker detected; comparison blocked.');return;}
  try{
    const before=state.source.candidates,after=state.handoff.candidates;
    if([...before,...after].some(c=>c.state==='CANDIDATE')){
      setStatus('Unreviewed candidates remain. Mark each candidate before comparing.');return;
    }
    const comparison=compareReviewedCandidates(before,after);
    if(comparison.source_count+comparison.restored_count===0){setStatus('Nothing accepted for comparison; no fidelity conclusion.');return;}
    lastReport={schema:'local-chat-handoff-v1',mode:'OFFLINE_SYNTHETIC_EXPLICIT_LABELS',
      source:before.map(c=>({id:c.id,kind:c.kind,speaker_label_unverified:c.speaker,state:c.state,source_span:c.span,text:c.text,revocation_cited:c.revocation_cited,conflict:c.conflict})),
      target:after.map(c=>({id:c.id,kind:c.kind,speaker_label_unverified:c.speaker,state:c.state,source_span:c.span,text:c.text,revocation_cited:c.revocation_cited,conflict:c.conflict})),
      comparison,
      warnings:['Not a semantic benchmark','Review flag is not authenticated permission','Report has no trusted signature or source attestation','Local download contains synthetic text and must be handled appropriately']};
    chatEl('chat-results').textContent=JSON.stringify({comparison,warning:'No identity verification or semantic assurance.'},null,2);
    setStatus('Exact comparison complete; limitations included. No external action performed.');
  }catch(e){setStatus(`Comparison blocked: ${e.message}`);}
}
function download(){if(!lastReport){setStatus('No reviewed report available.');return;}
  const blob=new Blob([JSON.stringify(lastReport,null,2)+'\n'],{type:'application/json'});
  const href=URL.createObjectURL(blob),a=document.createElement('a');a.href=href;a.download='local-chat-handoff-report.json';a.click();setTimeout(()=>URL.revokeObjectURL(href),1000);
}
async function loadFile(ev,target){
  const file=ev.target.files?.[0];if(!file)return;
  if(file.size>MAX_CHAT_BYTES){setStatus('File exceeds 128 KiB limit.');ev.target.value='';return;}
  if(!/\.(txt|md)$/i.test(file.name)){setStatus('Only .txt or .md local synthetic files supported.');ev.target.value='';return;}
  try{const t=await file.text();extractChatCandidates(t);chatEl(target).value=t;clearReview();setStatus('Local file read. No network upload. Confirm synthetic content and click Extract.');}
  catch(e){setStatus(`File rejected: ${e.message}`);}finally{ev.target.value='';}
}
export function initLocalChat(){
  chatEl('chat-load-example').addEventListener('click',()=>{
    chatEl('chat-source').value=SYNTHETIC_CHAT;
    chatEl('chat-target').value=SYNTHETIC_CHAT.replace('Never send it without explicit human approval','Send after preparing the draft');
    chatEl('chat-consent').checked=true;clearReview();setStatus('Synthetic example loaded. Click Extract, review items, then compare.');
  });
  chatEl('chat-extract').addEventListener('click',analyse);
  chatEl('chat-compare').addEventListener('click',compare);
  chatEl('chat-download').addEventListener('click',download);
  chatEl('chat-reset').addEventListener('click',()=>{
    chatEl('chat-source').value='';chatEl('chat-target').value='';chatEl('chat-consent').checked=false;clearReview();setStatus('Local workspace cleared (downloaded reports are not deleted).');
  });
  chatEl('chat-source').addEventListener('input',()=>{clearReview();setStatus('Input changed. Extract again.');});
  chatEl('chat-target').addEventListener('input',()=>{clearReview();setStatus('Input changed. Extract again.');});
  chatEl('chat-source-file').addEventListener('change',e=>loadFile(e,'chat-source'));
  chatEl('chat-target-file').addEventListener('change',e=>loadFile(e,'chat-target'));
}
