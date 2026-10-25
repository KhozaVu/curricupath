import React from 'react';
function Condition({value}) {
  if(typeof value==='string')return <span className="requirement-leaf">{value}</span>;
  if(Array.isArray(value))return <div className="requirement-group"><strong>All listed requirements (AND)</strong>{value.map((v,i)=><Condition key={i} value={v}/>)}</div>;
  if(value && typeof value==='object'){
    const key=Array.isArray(value.all_of)?'all_of':Array.isArray(value.any_of)?'any_of':null;
    if(key && Object.keys(value).length===1)return <div className="requirement-group"><strong>{key==='all_of'?'All of these (AND)':'At least one of these (OR)'}</strong>{value[key].map((v,i)=><Condition key={i} value={v}/>)}</div>;
  }
  return <p className="helper-text">This rule uses additional logic. Read the supplied plain-language requirement; the full rule is preserved below.</p>;
}
export function RequirementTree({rule}) {
  let condition=null;try{condition=JSON.parse(rule.condition_json);}catch{}
  return <div className="requirement-tree"><p className="helper-text">Recorded rule explanation. Consult the referenced source for its authoritative wording.</p><p>{rule.plain_language || 'Plain-language requirement not supplied'}</p>{condition!==null && <Condition value={condition}/>}<small>{rule.rule_id} · {rule.scope || 'Scope not supplied'} · {rule.source_id}{rule.handbook_page?` · page ${rule.handbook_page}`:''}</small><details><summary>Inspect the exact recorded condition</summary><pre>{rule.condition_json || 'Condition not supplied'}</pre></details></div>;
}
