import React,{useState} from 'react';
import {reviewText} from '../academicWorkspace.mjs';
import {downloadText} from './shared';
export function ReviewHandoff({result,profile,recordedAt,scope='Recorded answer',historical=false}){
 const [includeHistory,setIncludeHistory]=useState(false),[exportedAt]=useState(()=>new Date().toISOString());
 if(!result?.manual_review_required && result?.decision!=='manual_review_required')return null;
 const text=reviewText({result,profile,includeHistory,recordedAt,scope,exportedAt,historical});
 return <details className="review-handoff"><summary>Prepare a review note · {scope}</summary><p>The recorded result needs an academic reviewer. This is a local draft, not an official decision or a sent review request. The stated reason may contain private circumstances; inspect it before sharing it yourself.</p>{historical && <p className="workspace-warning">This is a historical result. Re-evaluate before acting.</p>}<label className="review-history-choice"><input type="checkbox" checked={includeHistory} onChange={e=>setIncludeHistory(e.target.checked)}/><span>Include original declared module history in this export</span></label><p className="helper-text">Profile name, preferences and conversations are excluded. Review circumstances may contain identifying details. Module history is excluded unless you select it.</p><pre role="region" tabIndex={0} aria-label={`Review note preview · ${scope}`}>{text}</pre><button className="secondary-button" onClick={()=>downloadText('curricupath-review-note.txt',text)}>Export review note</button></details>;
}
