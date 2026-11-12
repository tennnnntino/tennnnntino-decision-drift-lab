/* Decision Drift Lab browser evaluator; consistent with the Python reference on synthetic fixtures.
   V1.4.1 mirrors ddlab/core.py: external authorization policy, revocation ledger, canonical Unicode
   equivalence, status normalisation, deterministic ordering and rounding. */
import {DEFAULT_POLICY, POLICY_LIKE_KEYS, POLICY_SCHEMA} from './policy.mjs';
import {validate} from './schema.mjs';

const MAX_CASE_BYTES = 524288;
const MAX_NESTING_DEPTH = 64;
const isPlainObject = v => v !== null && typeof v === 'object' && !Array.isArray(v);
// V1.4: an absent key takes the default; an explicit null does not (same as the Python reference).
const field = (obj, key, fallback) => Object.hasOwn(obj, key) ? obj[key] : fallback;

// Status vocabulary. Matching trims, upper-cases ASCII letters and unifies space, hyphen and underscore.
export const STATUS_CLASSES = {
  ACTIVE: ['ACTIVE', 'ENABLED', 'APPROVED', 'REINSTATED', 'IN_FORCE'],
  REVOKED: ['REVOKED', 'REJECTED', 'CANCELLED', 'CANCELED', 'WITHDRAWN', 'RESCINDED'],
  FACT: ['FACT', 'CONFIRMED', 'VERIFIED'],
  UNCERTAIN: ['TO_CONFIRM', 'UNKNOWN', 'SUPPORTED_INFERENCE', 'UNCONFIRMED', 'UNVERIFIED', 'HYPOTHESIS', 'TBC'],
};
const STATUS_LOOKUP = new Map(Object.entries(STATUS_CLASSES).flatMap(([name, aliases]) => aliases.map(a => [a, name])));
const NEGATIONS = new Set(['not', 'no', 'never', 'without', 'cannot', 'nothing', 'none', 'neither', 'nor', 'dont',
  'doesnt', 'didnt', 'wont', 'cant', 'mustnt', 'shouldnt', 'isnt', 'arent']);

/** Code point order, the order Python's sorted() uses for strings. */
function byCodePoint(a, b) {
  const x = Array.from(a), y = Array.from(b);
  for (let i = 0; i < Math.min(x.length, y.length); i++) {
    const d = x[i].codePointAt(0) - y[i].codePointAt(0);
    if (d) return d;
  }
  return x.length - y.length;
}

function stableStringify(x){
  if(Array.isArray(x)) return `[${x.map(stableStringify).join(',')}]`;
  if(x && typeof x === 'object') return `{${Object.keys(x).sort().map(k => `${JSON.stringify(k)}:${stableStringify(x[k])}`).join(',')}}`;
  return JSON.stringify(x);
}

/** NFC-normalise every string, keys included. Canonical equivalence only, never NFKC. */
function nfc(value) {
  if (typeof value === 'string') return value.normalize('NFC');
  if (Array.isArray(value)) return value.map(nfc);
  if (isPlainObject(value)) return Object.fromEntries(Object.entries(value).map(([k, v]) => [k.normalize('NFC'), nfc(v)]));
  return value;
}

/** Returns [class or null, spelled exactly as a known token]. */
export function statusClass(value) {
  if (typeof value !== 'string') return [null, true];
  const key = value.normalize('NFC').replace(/^[ \t\n\r]+|[ \t\n\r]+$/g, '').replace(/[a-z]/g, ch => ch.toUpperCase()).replace(/[ _-]+/g, '_');
  const name = STATUS_LOOKUP.get(key) ?? null;
  return [name, name === null || STATUS_LOOKUP.has(value)];
}

/** Lexical triage hints for a changed text. Not a judgement about meaning. */
export function textProfile(before, after) {
  const words = text => text.replace(/[A-Z]/g, ch => ch.toLowerCase()).replace(/['’]/g, '').match(/[a-z0-9]+/g) ?? [];
  const a = words(before), b = words(after);
  const sa = new Set(a), sb = new Set(b);
  const nonAscii = /[^\x00-\x7F]/.test(before + after);
  const digits = set => [...set].filter(t => /^[0-9]+$/.test(t)).sort().join(',');
  return {
    formatting_only: a.length > 0 && a.length === b.length && a.every((t, i) => t === b[i]) && !nonAscii,
    source_tokens: sa.size, handoff_tokens: sb.size, shared_tokens: [...sa].filter(t => sb.has(t)).length,
    negation_changed: [...sa].some(t => NEGATIONS.has(t)) !== [...sb].some(t => NEGATIONS.has(t)),
    numbers_changed: digits(sa) !== digits(sb),
    non_ascii_content: nonAscii,
  };
}

const index = (array, label) => {
  if (!Array.isArray(array)) throw new Error(`${label} must be an array`);
  if (array.length > 1000) throw new Error(`${label} exceeds item limit`);
  const map = new Map();
  for (const item of array) {
    if (!isPlainObject(item) || typeof item.id !== 'string' || !item.id) throw new Error(`${label}: invalid item ID`);
    // V1.4.1: identifiers are keyed by their NFC form, so two spellings of one id cannot coexist.
    const id = item.id.normalize('NFC');
    if (Array.from(id).length > 120) throw new Error(`${label}: invalid item ID`);
    if (map.has(id)) throw new Error(`${label}: duplicate ID ${id}`);
    map.set(id, item);
  }
  return map;
};

function comparison(a,b,zone){
  const original=index(a,`source.${zone}`), handoff=index(b,`handoff.${zone}`);
  const retained=[], altered=[], missing=[], introduced=[], normalised=[], changes=[];
  for(const id of [...original.keys()].sort(byCodePoint)){
    if (!handoff.has(id)){missing.push(id);continue;}
    const before=original.get(id), after=handoff.get(id);
    if(stableStringify(before)===stableStringify(after)){retained.push(id);continue;}
    const old=nfc(before), next=nfc(after);
    // V1.4.1: canonically equivalent Unicode is the same text; reported as an advisory only.
    if(stableStringify(old)===stableStringify(next)){retained.push(id);normalised.push(id);continue;}
    altered.push(id);
    const changed=[...new Set([...Object.keys(old),...Object.keys(next)])]
      .filter(k=>Object.hasOwn(old,k)!==Object.hasOwn(next,k)||stableStringify(old[k])!==stableStringify(next[k])).sort(byCodePoint);
    const entry={id,changed_fields:changed};
    if(changed.includes('text')&&typeof old.text==='string'&&typeof next.text==='string')entry.text_profile=textProfile(old.text,next.text);
    changes.push(entry);
  }
  for(const id of [...handoff.keys()].sort(byCodePoint)) if(!original.has(id)) introduced.push(id);
  return [{retained,altered,missing,introduced,changes,source_total:original.size,handoff_total:handoff.size},normalised];
}

// V1.4.1: integer half-up rounding to four decimals, identical in Python and JavaScript.
function ratio(num,denom){return denom ? Math.floor((2*num*10000+denom)/(2*denom))/10000 : null;}

function checkNesting(value){
  const stack=[[value,0]];
  let seen=0;
  while(stack.length){
    const [item,depth]=stack.pop();
    if(++seen>50000)throw new Error('Case exceeds structural node limit');
    if(depth>MAX_NESTING_DEPTH)throw new Error('Case nesting exceeds safety depth limit');
    if(Array.isArray(item))for(const child of item)stack.push([child,depth+1]);
    else if(item && typeof item==='object')for(const child of Object.values(item))stack.push([child,depth+1]);
    // V1.4: a number JavaScript cannot represent exactly is rejected, not compared.
    else if(typeof item==='number'&&(!Number.isFinite(item)||(Number.isInteger(item)&&!Number.isSafeInteger(item))))throw new Error('Case contains a non-finite or unsafe integral number');
  }
}

/** Validate an operator-supplied policy. Fails closed. */
export function checkPolicy(policy){
  const errors=validate(policy,POLICY_SCHEMA);
  if(errors.length)throw new Error(`Policy schema violations (${errors.length}): ${errors.slice(0,5).map(e=>`${e.path} [${e.keyword}]`).join('; ')}`);
  const pairs=policy.exempt_actions.map(e=>`${e.name}\u0000${e.scope}`);
  if(new Set(pairs).size!==pairs.length)throw new Error('Policy lists the same exempt action twice');
  return policy;
}
const isExempt=(policy,name,scope)=>typeof name==='string'&&typeof scope==='string'&&policy.exempt_actions.some(e=>e.name===name&&e.scope===scope);

/** `policy` is the operator's policy and is never read from the case `c`. */
export function evaluateCase(c, policy = DEFAULT_POLICY){
  if(!c || typeof c!=='object' || Array.isArray(c))throw new Error('Case must be an object');
  checkPolicy(policy);
  checkNesting(c);
  if(new TextEncoder().encode(stableStringify(c)).length > MAX_CASE_BYTES)throw new Error('Case too large');
  if(!isPlainObject(c.source) || !isPlainObject(c.handoff)) throw new Error('Missing source or handoff object');
  const sf=field(c.source,'facts',[]),sd=field(c.source,'decisions',[]),hf=field(c.handoff,'facts',[]),hd=field(c.handoff,'decisions',[]);
  const [facts,factsNormalised]=comparison(sf,hf,'facts'),[decisions,decisionsNormalised]=comparison(sd,hd,'decisions');
  const act=field(c,'action',{});
  if(!isPlainObject(act))throw new Error('Invalid action or approval');
  const declared=field(act,'requires_human',true);
  if(typeof declared!=='boolean')throw new Error('requires_human must be boolean');
  const ap=field(act,'human_approval',{});
  if(!isPlainObject(ap))throw new Error('Invalid action or approval');
  // V1.4.1: the requirement comes from the external policy. The case may tighten it, never waive it.
  const exempt=isExempt(policy,field(act,'name',null),field(act,'scope',null));
  const needs=declared||!exempt;
  const waiverIgnored=!declared&&!exempt;
  const explicit=ap.approved===true&&ap.actor_type==='HUMAN';
  const scopeMatches=!Object.hasOwn(ap,'scope') || ap.scope===act.scope;
  const actionMatches=!Object.hasOwn(ap,'action') || ap.action===act.name;
  // V1.4: an approval that names no scope or no action is not a blanket approval.
  const scopeStated=Object.hasOwn(ap,'scope'),actionStated=Object.hasOwn(ap,'action');
  const permitted=!needs || (explicit&&scopeMatches&&actionMatches&&scopeStated&&actionStated);
  const reasons=[];
  if(needs){if(!explicit)reasons.push('NO_SYNTHETIC_HUMAN_APPROVAL');if(!scopeMatches)reasons.push('SCOPE_MISMATCH');if(!actionMatches)reasons.push('ACTION_MISMATCH');
    if(explicit&&!scopeStated)reasons.push('APPROVAL_SCOPE_UNSPECIFIED');if(explicit&&!actionStated)reasons.push('APPROVAL_ACTION_UNSPECIFIED');
    if(waiverIgnored)reasons.push('CASE_WAIVER_IGNORED');}
  const findings=[];
  const notes=new Map();
  const note=(code,id)=>notes.set(`${code}\u0000${id}`,{code,item_id:id});
  for(const [zone,comp,normalised] of [['facts',facts,factsNormalised],['decisions',decisions,decisionsNormalised]]){
    for(const state of ['altered','missing','introduced'])for(const id of comp[state])findings.push({code:`${zone.toUpperCase()}_${state.toUpperCase()}`,item_id:id});
    for(const id of normalised)note('UNICODE_NORMALIZATION_ONLY',id);
  }
  const classes=(items,label)=>{
    const indexed=index(items,label),out=new Map();
    for(const [id,item] of indexed){
      const [name,canonical]=statusClass(field(item,'status',null));
      out.set(id,name);
      if(!canonical)note('NONCANONICAL_STATUS',id);
    }
    return [indexed,out];
  };
  const [fBefore,fBeforeClass]=classes(sf,'source.facts'),[fAfter,fAfterClass]=classes(hf,'handoff.facts');
  // V1.4.1: sorted iteration, so the report does not depend on input order or runtime.
  for(const id of [...fBefore.keys()].sort(byCodePoint)){
    if(fAfter.has(id)&&fBeforeClass.get(id)==='UNCERTAIN'&&fAfterClass.get(id)==='FACT')findings.push({code:'UNSUPPORTED_FACT_PROMOTION',item_id:id});
  }
  const [dBefore,dBeforeClass]=classes(sd,'source.decisions'),[dAfter,dAfterClass]=classes(hd,'handoff.decisions');
  const ledger=[];
  for(const id of [...dBefore.keys()].sort(byCodePoint)){
    const before=dBefore.get(id),after=dAfter.get(id);
    if(dBeforeClass.get(id)==='REVOKED'){
      // V1.4.1: a revoked decision keeps a trace in the report whatever the handoff did with it.
      const current=dAfterClass.get(id);
      let state;
      if(after===undefined){state='NOT_CARRIED';findings.push({code:'REVOKED_DECISION_TRACE_LOST',item_id:id});}
      else if(current==='REVOKED')state='CARRIED_AS_REVOKED';
      else if(current==='ACTIVE'){state='REACTIVATED';findings.push({code:'REACTIVATED_DECISION',item_id:id});}
      else{state='STATUS_CHANGED';findings.push({code:'REVOKED_STATUS_CHANGED',item_id:id});}
      ledger.push({id,source_status:field(before,'status',null),handoff_state:state,source_item:before});
    }
    // An absent authority and an explicit null are the same thing, as in the Python reference.
    if(after!==undefined&&stableStringify(nfc(before.authority??null))!==stableStringify(nfc(after.authority??null)))findings.push({code:'AUTHORITY_CHANGED',item_id:id});
  }
  const ignored=POLICY_LIKE_KEYS.filter(k=>Object.hasOwn(c,k)||Object.hasOwn(act,k));
  if(ignored.length)note('CASE_POLICY_FIELD_IGNORED',ignored.join(','));
  const advisories=[...notes.values()].sort((x,y)=>byCodePoint(x.code,y.code)||byCodePoint(x.item_id,y.item_id));
  return {
    report_schema:'1.1',case_id:field(c,'case_id','unnamed'),verdict:!findings.length&&permitted?'PASS':'FAIL',
    facts,decisions,
    approval_check:{result:permitted?'ALLOW_IN_SIMULATION':'BLOCK_IN_SIMULATION',requires_human:needs,reasons,authenticated:false,
      requirement_source:'EXTERNAL_POLICY',policy_id:policy.policy_id,policy_exempt:exempt,case_declared_requires_human:declared},
    findings,advisories,revocation_ledger:ledger,
    metrics:{decision_exact_recall:ratio(decisions.retained.length,decisions.source_total),decision_exact_precision:ratio(decisions.retained.length,decisions.handoff_total),fact_exact_recall:ratio(facts.retained.length,facts.source_total),fact_exact_precision:ratio(facts.retained.length,facts.handoff_total)},
    claims:['Deterministic structural equality','No action executed','Synthetic scenario only'],
    limitations:['No semantic equivalence detection','No LLM evaluation','No authenticated authorization','Hashes do not prove truth, identity or completeness','Only supplied structured items can be evaluated',
      'The approval requirement comes from an external policy; the approval record and the action name are still supplied by the case and are not authenticated',
      'Advisories and text profiles are lexical hints, not judgements about meaning']
  };
}
export { stableStringify };
