import {resolveSourceReference} from "./collectionModel.mjs";
import sourceManifest from "./sourceManifest.json" with {type:"json"};
export const HISTORY_FIELDS = ['completed','current','planned','repeating'];
export function contextKey(profile) {
  return JSON.stringify({programme:profile.programme,stage:profile.stage,stream:profile.stream,historyConfirmed:Boolean(profile.historyConfirmed),reviewNote:profile.reviewNote || '',interests:[...(profile.interests || [])].sort(),careers:[...(profile.careers || [])].sort(),workload:profile.workload || '',format:profile.format || '',...Object.fromEntries(HISTORY_FIELDS.map(key=>[key,[...(profile[key] || [])].sort()]))});
}
export function declarationConflicts(profile) {
  const codes=[...new Set(HISTORY_FIELDS.flatMap(key=>profile[key] || []))];
  return codes.map(code=>({code,states:HISTORY_FIELDS.filter(key=>(profile[key] || []).includes(code))})).filter(item=>item.states.length>1);
}
export function assignedState(profile,code) { return HISTORY_FIELDS.find(key=>(profile[key] || []).includes(code)); }
export function moveDeclaration(profile,code,field) {
  if(!HISTORY_FIELDS.includes(field))throw new Error('Unsupported declaration state');
  const removing=(profile[field] || []).includes(code);
  const next={...profile,...Object.fromEntries(HISTORY_FIELDS.map(key=>[key,(profile[key] || []).filter(value=>value!==code)]))};
  if(!removing)next[field]=[...next[field],code];
  return next;
}
export function previewCodes(text,modules,profile,field) {
  const entries=String(text).toUpperCase().split(/[\s,;]+/).filter(Boolean);
  const tokens=entries.slice(0,150);
  const seen=new Set(), valid=[],unknown=[],duplicates=[],moves=[];
  for(const token of tokens){
    const code=modules.find(m=>m.course_code===token || (!token.endsWith('A') && m.course_code===`${token}A`))?.course_code;
    if(!code){unknown.push(token);continue;}
    if(seen.has(code)){duplicates.push(code);continue;}seen.add(code);valid.push(code);
    const previous=assignedState(profile,code);if(previous && previous!==field)moves.push({code,from:previous,to:field});
  }
  return {valid,unknown,duplicates,moves,truncated:entries.length>150};
}
export function applyPreview(profile,preview,field) {
  return preview.valid.reduce((next,code)=>(next[field] || []).includes(code)?next:moveDeclaration(next,code,field),profile);
}
export function makeScenario(profile,name='A possible next chapter') {
  return {id:globalThis.crypto?.randomUUID?.() || `draft-${Date.now()}`,name,createdAt:new Date().toISOString(),baseKey:contextKey(profile),programme:profile.programme,assumedCompleted:[],removedCompleted:[],historyConfirmed:Boolean(profile.historyConfirmed),terms:Object.fromEntries((profile.planned || []).map(code=>[code,'1'])),planned:[...(profile.planned || [])]};
}
export function scenarioProfile(profile,draft) {
  const completed=[...new Set([...(profile.completed || []).filter(c=>!draft.removedCompleted.includes(c)),...draft.assumedCompleted])];
  const planned=draft.planned.filter(c=>!completed.includes(c));
  return {...profile,completed,current:(profile.current || []).filter(c=>!completed.includes(c)&&!planned.includes(c)),repeating:(profile.repeating || []).filter(c=>!completed.includes(c)&&!planned.includes(c)),planned,historyConfirmed:draft.historyConfirmed};
}
export function eligibilityPayload(profile,code) {
  return {manual_review_reasons:profile.reviewNote?.trim()?[profile.reviewNote.trim()]:[],course_code:code,programme_code:profile.programme,completed_modules:profile.completed || [],current_modules:profile.current || [],planned_modules:profile.planned || [],repeating_modules:profile.repeating || [],module_history_confirmed:Boolean(profile.historyConfirmed),module_states:Object.fromEntries(HISTORY_FIELDS.flatMap(field=>(profile[field] || []).map(c=>[c,field==='repeating'?'not_completed':field])))};
}
export function outcome(result) {
  if(!result)return {label:'Not evaluated',tone:'outline'};
  if(result.completed)return {label:'Declared complete',tone:'blue'};
  if(result.manual_review_required)return {label:'Manual review required',tone:'gold'};
  if(result.needs_clarification)return {label:'Clarification required',tone:'gold'};
  if(!['eligible','ineligible'].includes(result.decision) && typeof result.eligible!=='boolean')return {label:'Outcome unavailable',tone:'gold'};
  if(result.eligible)return {label:'Eligible',tone:'green'};
  return {label:'Not eligible',tone:'outline'};
}
export function creditTotal(codes,modules) {
  let total=0;const missing=[];
  for(const code of [...new Set(codes)]){const value=modules.find(m=>m.course_code===code)?.nqf_credits;if(value===null || value===undefined || value==='' || !Number.isFinite(Number(value)))missing.push(code);else total+=Number(value);}
  return {total,missing};
}
export function scenarioText(draft,profile,modules,evaluation) {
  const lines=[`CurricuPath hypothetical plan: ${draft.name}`,`Exported ${new Date().toISOString()}`,`Programme ${draft.programme}`,'Hypothetical inputs; actual module history was not changed.',`Profile context: ${draft.baseKey===contextKey(profile)?'current':'changed since draft creation'}`,`Original declared context: ${draft.baseKey}`,`Assumed history complete: ${draft.historyConfirmed?'yes':'no'}`,`Assumed completed: ${draft.assumedCompleted.join(', ') || 'none'}`,`Removed completed assumptions: ${draft.removedCompleted.join(', ') || 'none'}`,'Term placement is a personal intention. Offering and timetable feasibility are not confirmed.',''];
  for(const code of draft.planned){const module=modules.find(m=>m.course_code===code);lines.push(`${code} · ${module?.course_name || 'Catalogue record unavailable'} · intended term ${draft.terms[code] || 'unassigned'} · ${module?.source_id || 'Source not supplied'}${module?.handbook_page?` page ${module.handbook_page}`:''}`);}
  if(evaluation){lines.push('',`Checked ${evaluation.at} · ${evaluation.stale?'historical result':'see profile/draft context'}`,`Target ${evaluation.code}`,`Declared context: ${outcome(evaluation.baseline).label}`,`Hypothetical context: ${outcome(evaluation.scenario).label}`);for(const result of [evaluation.baseline,evaluation.scenario])for(const reason of result?.reasons || [])lines.push(reason);for(const result of [evaluation.baseline,evaluation.scenario])for(const step of result?.rule_trace || [])lines.push(`${step.gate}: ${(step.rule_ids || []).join(', ')}`);for(const result of [evaluation.baseline,evaluation.scenario])for(const key of ['unresolved_predicates','evidence_issues'])if(result?.[key]?.length)lines.push(`${key}: ${JSON.stringify(result[key])}`);}
  lines.push('Catalogue version: not supplied by the scenario evaluation endpoint.');
  return lines.join('\n');
}
function withNestedEvidence(data) {
  const module=data.module || {};
  const listed=[...(data.modules || []),...(data.recommendations || []),...(data.module_matches || [])].filter(item=>item && item.source_id);
  return {...data,
    rules:[...(data.rules || []),...(module.rules || [])],
    sources:[...(data.sources || []),...(module.sources || []),...[data.programme_profile,...(data.programme_comparison?.profiles || [])].filter(p=>p && p.source).map(p=>p.source)],
    citations:[...(data.citations || []),...listed.map(item=>({source_id:item.source_id,page:item.handbook_page,title:item.title && item.provider?item.title:undefined}))]};
}

export function evidenceRecords(rawData={}) {
  const data=withNestedEvidence(rawData);
  const records=[...(data.rules || []).map(r=>({id:r.source_id,explanation:r.plain_language,page:r.handbook_page,rule:r.rule_id})),...(data.citations || []).map(c=>({id:c.source_id,title:c.title,page:c.page})),...(data.sources || []).map(s=>({id:s.source_id,title:s.title,status:s.verification_status,url:s.url,locator:s.locator,version:s.version || s.academic_year || s.edition_year,pageOffset:s.handbook_page_offset,date:s.review_date || s.audit_date})),...(data.source?[{id:data.source.source_id,title:data.source.title,status:data.source.verification_status,url:data.source.url,date:data.audit?.audit_date,version:data.source.version || data.source.academic_year || data.source.edition_year,pageOffset:data.source.handbook_page_offset}]:[])];
  if(data.source_id)records.push({id:data.source_id,title:data.title,page:data.page,version:data.version || data.academic_year,date:data.access_date});
  return records.map(r=>{
    const supplied=Object.fromEntries(Object.entries(records.find(item=>item.id===r.id && (item.status || item.version || item.url)) || {}).filter(([,value])=>value!==undefined && value!==null && value!==''));
    const source=resolveSourceReference(supplied,sourceManifest[r.id]);
    return {...source,...r,title:r.title || source.title,explanation:r.explanation,status:r.status || source.status,version:r.version || source.version || null,date:r.date || source.date,url:r.url || source.url,locator:r.locator || source.locator,pageOffset:source.pageOffset,sha256:source.sha256};
  }).filter((r,index)=>r.id && records.findIndex(other=>other.id===r.id && other.page===r.page && other.rule===r.rule)===index);
}

export function reviewText({result,profile,includeHistory=false,recordedAt,scope,exportedAt,historical=false}) {
 const pack=result.manual_review_package || {};const rules=[...new Set([...(pack.affected_rules || []),...(result.rule_trace || []).flatMap(step=>step.rule_ids || [])])];
 const lines=['CurricuPath academic review note · local draft',`Prepared ${exportedAt}`,`Context: ${scope}`,`Recorded result time: ${recordedAt || 'not supplied'}`,`Result context: ${historical?'historical; re-evaluate before acting':'see original supplied declarations'}`,`Module: ${result.course_code || 'not supplied'}`,`Programme: ${result.programme_code || profile?.programme || 'not supplied'}`,'Outcome: Manual review required; no official decision or registration approval.',`Recorded reason: ${pack.reason || (result.reasons || []).join('; ') || 'not supplied'}`,`Affected rules: ${rules.join(', ') || 'not supplied'}`,`Evidence issues: ${JSON.stringify(pack.evidence_issues || result.evidence_issues || [])}`,'Nothing has been sent to an adviser. Review private circumstances before manually sharing this file.'];
 if(includeHistory && profile)lines.push('Original declared module history (explicitly included):',JSON.stringify({programme:profile.programme,historyConfirmed:Boolean(profile.historyConfirmed),...Object.fromEntries(HISTORY_FIELDS.map(k=>[k,profile[k] || []]))},null,2));else lines.push('Declared module history: excluded.');
 return lines.join('\n');
}
