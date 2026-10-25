import {ReviewHandoff} from "./ReviewHandoff";
import React, { useEffect, useRef, useState } from 'react';
import { ArrowUpRight, Plus, Copy, Trash2 } from 'lucide-react';
import { usePersistentState, getJson, downloadText, StatusPill } from './shared';
import { declarationConflicts,contextKey,makeScenario,scenarioProfile,eligibilityPayload,outcome,creditTotal,scenarioText } from '../academicWorkspace.mjs';

export function ScenarioStudio({profile,modules,onOpenModule,onSources,targetCode}) {
  const [stored,setStored,persistence]=usePersistentState('curricupath-scenarios-v1',[]);
  const drafts=Array.isArray(stored)?stored.filter(d=>d && typeof d.id==='string' && Array.isArray(d.planned) && Array.isArray(d.assumedCompleted) && Array.isArray(d.removedCompleted) && d.terms && typeof d.terms==='object'):[];
  const [active,setActive]=useState(drafts[0]?.id || '');
  const draft=drafts.find(d=>d.id===active);
  const [target,setTarget]=useState(targetCode || '');
  const [query,setQuery]=useState('');
  const [result,setResult]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[confirmation,setConfirmation]=useState('');
  const generation=useRef(0),controller=useRef(null);
  const stale=draft && draft.baseKey!==contextKey(profile);
  const signature=JSON.stringify(draft);
  useEffect(()=>{generation.current++;controller.current?.abort();setBusy(false);setResult(null);setError('');},[signature,contextKey(profile),target]);
  useEffect(()=>()=>{generation.current++;controller.current?.abort();},[]);
  useEffect(()=>{if(targetCode)setTarget(targetCode);},[targetCode]);
  const newDraft=()=>{const next=makeScenario(profile);setStored([...drafts.slice(-7),next]);setActive(next.id);setConfirmation('');};
  const patch=change=>setStored(drafts.map(d=>d.id===active?{...d,...change}:d));
  const toggle=(field,code)=>patch({[field]:draft[field].includes(code)?draft[field].filter(c=>c!==code):[...draft[field],code]});
  const check=async()=>{
    if(!draft || stale || !target || busy)return;
    if(declarationConflicts(profile).length){setError('Your declarations contain conflicting module states. Resolve these in Profile before evaluating.');return;}
    const invalid=[...draft.planned,...draft.assumedCompleted,...draft.removedCompleted].filter(c=>!modules.some(m=>m.course_code===c));
    if(invalid.length){setError(`Catalogue records are unavailable for ${invalid.join(', ')}. Review these assumptions before evaluating.`);return;}
    const token=++generation.current;controller.current=new AbortController();setBusy(true);setError('');setResult(null);
    try {
      const evaluate=p=>getJson('/eligibility',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(eligibilityPayload(p,target)),signal:controller.current.signal});
      const [baseline,scenario,record]=await Promise.all([evaluate(profile),evaluate(scenarioProfile(profile,draft)),getJson(`/modules/${target}`,{signal:controller.current.signal})]);
      if(token===generation.current)setResult({baseline,scenario,record,code:target,at:new Date().toISOString(),profileKey:contextKey(profile),draftKey:signature});
    } catch(e){if(token===generation.current && e.name!=='AbortError')setError(`The comparison could not finish. ${e.message}`);}
    finally{if(token===generation.current)setBusy(false);}
  };
  const credits=draft?creditTotal(scenarioProfile(profile,draft).planned,modules):null;
  return <section className="scenario-studio" aria-labelledby="scenario-heading">
    <header className="workspace-heading"><div><span className="eyebrow">A safe space for possibilities</span><h2 id="scenario-heading">What if your next chapter looked different?</h2><p>Try assumptions in a separate draft. Your declared history stays untouched.</p></div><button className="secondary-button" onClick={newDraft} disabled={!profile.programme || !modules.length}><Plus size={16} aria-hidden="true"/>New hypothetical plan</button></header>
    {drafts.length>0 && <label className="workspace-field">Local drafts<select value={active} onChange={e=>{setActive(e.target.value);setConfirmation('');}}><option value="">Choose a draft…</option>{drafts.map(d=><option key={d.id} value={d.id}>{d.name} · {d.programme}</option>)}</select></label>}
    {!draft && <div className="scenario-empty"><span className="scenario-orbit" aria-hidden="true">↗</span><h3>A possibility, not a declaration.</h3><p>Create a draft to arrange modules, try completed-module assumptions and compare recorded requirement outcomes.</p></div>}
    {draft && <>
      <div className="scenario-context"><StatusPill tone="gold">Hypothetical plan</StatusPill><span>{draft.programme} · {persistence==='saved'?'Remembered on this device':'Local persistence unavailable'}</span></div>
      {profile.reviewNote?.trim() && <p className="workspace-warning">Your declared review circumstance is included in both evaluations. Assumptions cannot resolve an academic concession or human-review decision.</p>}
      {stale && <p className="workspace-warning" role="status">Your profile changed since this draft was created. Evaluation is paused. Start a new draft from the current profile; this older draft remains available to read and export.</p>}
      <div className="scenario-grid">
        <div><label className="workspace-field">Draft name<input name="scenario-name" autoComplete="off" maxLength={70} value={draft.name} onChange={e=>patch({name:e.target.value})}/></label>
          <div className="workspace-toolbar"><button className="text-button" onClick={()=>{const next={...structuredClone(draft),id:crypto.randomUUID(),name:`${draft.name.slice(0,55)} · copy`};setStored([...drafts.slice(-7),next]);setActive(next.id);}}><Copy size={15} aria-hidden="true"/>Duplicate draft</button><button className="text-button" onClick={()=>setConfirmation('reset')}>Reset assumptions</button><button className="text-button" onClick={()=>setConfirmation('delete')}><Trash2 size={15} aria-hidden="true"/>Delete draft</button></div>
          {confirmation && <div className="workspace-warning" role="alert"><p>{confirmation==='delete'?'Delete this local draft? Your actual history and other drafts are preserved.':'Reset this draft to your current declared plan? Its hypothetical changes will be removed.'}</p><button className="secondary-button" onClick={()=>{if(confirmation==='delete'){setStored(drafts.filter(d=>d.id!==active));setActive('');}else patch({...makeScenario(profile,draft.name),id:draft.id});setConfirmation('');}}>Confirm {confirmation}</button><button className="text-button" onClick={()=>setConfirmation('')}>Keep draft</button></div>}
          <label className="workspace-field">Add a planned module<select value="" onChange={e=>{if(e.target.value)patch({planned:[...draft.planned,e.target.value],terms:{...draft.terms,[e.target.value]:'1'}});}}><option value="">Choose a module…</option>{modules.filter(m=>!draft.planned.includes(m.course_code)).map(m=><option key={m.course_code} value={m.course_code}>{m.course_code} · {m.course_name}</option>)}</select></label>
          <p className="helper-text">Terms are your intentions. Module availability, weekly hours and timetable compatibility are not verified by this placement.</p>
          <div className="scenario-terms">{['1','2','unassigned'].map(term=><section key={term}><h3>{term==='unassigned'?'Unassigned':`Intended term ${term}`}</h3>{draft.planned.filter(code=>(draft.terms[code] || 'unassigned')===term).map(code=><div className="scenario-module" key={code}><button className="text-button" onClick={()=>onOpenModule(code)}>{code}<ArrowUpRight size={14} aria-hidden="true"/></button><span>{modules.find(m=>m.course_code===code)?.course_name || 'Catalogue record unavailable'}</span><label>Move {code}<select value={term} onChange={e=>patch({terms:{...draft.terms,[code]:e.target.value}})}>{['1','2','unassigned'].map(t=><option key={t} value={t}>{t==='unassigned'?'Unassigned':`Term ${t}`}</option>)}</select></label><button className="text-button" aria-label={`Remove ${code} from hypothetical plan`} onClick={()=>patch({planned:draft.planned.filter(c=>c!==code)})}>Remove</button></div>)}</section>)}</div>
          <p className="scenario-credit-total">{credits.missing.length?`${credits.total} known credits; incomplete total (${credits.missing.join(', ')})`:`${credits.total} recorded NQF credits planned after completion assumptions`}. Modules assumed completed are excluded. This is not a timetable or a degree-progress percentage.</p>
        </div>
        <div className="scenario-assumptions"><span className="eyebrow">Explicit assumptions</span><h3>What would you like to test?</h3><label className="history-confirmation"><input type="checkbox" checked={draft.historyConfirmed} onChange={e=>patch({historyConfirmed:e.target.checked})}/><span><strong>Assume history is complete for this draft</strong><small>This does not confirm your actual profile.</small></span></label>
          <details><summary>Assume a module has been completed ({draft.assumedCompleted.length})</summary><label className="workspace-field">Find an assumption<input name="scenario-assumption" autoComplete="off" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Module code or name…"/></label><div className="assumption-list">{modules.filter(m=>`${m.course_code} ${m.course_name}`.toLowerCase().includes(query.toLowerCase()) && !profile.completed.includes(m.course_code)).map(m=><label key={m.course_code}><input type="checkbox" checked={draft.assumedCompleted.includes(m.course_code)} onChange={()=>toggle('assumedCompleted',m.course_code)}/><span>{m.course_code} · {m.course_name}</span></label>)}</div></details>
          {profile.completed.length>0 && <details><summary>Test without a declared completed module</summary>{profile.completed.map(code=><label className="assumption-option" key={code}><input type="checkbox" checked={draft.removedCompleted.includes(code)} onChange={()=>toggle('removedCompleted',code)}/>Exclude {code} only in this draft</label>)}</details>}
          <label className="workspace-field">Module to evaluate<select value={target} onChange={e=>setTarget(e.target.value)}><option value="">Choose a target module…</option>{modules.map(m=><option key={m.course_code} value={m.course_code}>{m.course_code} · {m.course_name}</option>)}</select></label>
          <button className="primary-button" onClick={check} disabled={!target || stale || busy} aria-busy={busy}>{busy?'Comparing recorded requirements…':'Compare declared and hypothetical outcomes'}</button>
          {busy && <button className="text-button" onClick={()=>{generation.current++;controller.current?.abort();setBusy(false);}}>Cancel comparison</button>}
          {error && <p className="workspace-warning" role="alert">{error}</p>}
        </div>
      </div>
      {result && <section className="scenario-results" aria-live="polite"><div className="section-label"><h3>{result.code}: two contexts, one evaluator.</h3><button className="secondary-button" onClick={()=>onSources(result.record)}>Inspect supporting rules</button></div><div className="outcome-grid">{[['Declared context',result.baseline],['Hypothetical context',result.scenario]].map(([label,value])=><section key={label}><span className="eyebrow">{label}</span><StatusPill tone={outcome(value).tone}>{outcome(value).label}</StatusPill><ul>{value.reasons?.map(reason=><li key={reason}>{reason}</li>)}</ul>{[...(value.requirements?.prerequisites || []),...(value.requirements?.corequisites || [])].map(r=><p key={r.rule_id}><strong>{r.rule_id}</strong> · {r.description} · {r.satisfied?'Satisfied for this context':'Not demonstrated for this context'} · {r.source_id}</p>)}<ReviewHandoff result={value} profile={label==='Declared context'?profile:scenarioProfile(profile,draft)} recordedAt={result.at} scope={label}/><p className="helper-text">{value.needs_clarification?'Missing facts must be clarified.':value.manual_review_required?'Available evidence requires human review.':'A recorded-rule result, not an official registration decision.'}</p></section>)}</div><p className="helper-text">Offering and timetable coverage may be unavailable. No clash-free or registration guarantee is inferred.</p></section>}
      <details className="workspace-export"><summary>Preview and export this hypothetical plan</summary><p>The export includes the profile context and assumptions shown below. Review it before sharing.</p><pre role="region" tabIndex={0} aria-label="Export preview">{scenarioText(draft,profile,modules,result)}</pre><button className="secondary-button" onClick={()=>downloadText('curricupath-hypothetical-plan.txt',scenarioText(draft,profile,modules,result))}>Export hypothetical plan</button></details>
    </>}
  </section>;
}
