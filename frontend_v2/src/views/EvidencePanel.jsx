import React, { useState } from 'react';
import { offlineReading,sourceLocation } from '../collectionModel.mjs';
import { evidenceRecords } from '../academicWorkspace.mjs';
import { CopyButton, downloadText } from './shared';

export function evidenceText(data) {
  return evidenceRecords(data).map(record=>`${record.id}${record.rule?` · rule ${record.rule}`:''}${record.page?` · page ${record.page}`:''}\n${record.title || 'Title not supplied'}${record.explanation?`\nRecorded rule explanation: ${record.explanation}`:''}${record.status?`\nRecorded verification: ${record.status}`:''}${record.date?`\nRecorded review date: ${record.date}`:''}${record.locator?`\nLocation: ${record.locator}`:''}\nRecorded version: ${record.version || 'not supplied'}`).join('\n\n');
}
export function EvidencePanel({data,compact=false}) {
  const [explanation,setExplanation]=useState('');
  const issueText=`Evidence issue draft\nSubject: ${data.course_code || data.title || 'Recorded result'}\n${evidenceText(data)}\n\nYour explanation: ${explanation}`;
  const records=evidenceRecords(data);
  return <section className={`evidence-panel ${compact?'is-compact':''}`} aria-label="Recorded evidence">
    <div className="section-label"><h3>Recorded evidence</h3><CopyButton label="Copy evidence references" text={evidenceText(data) || 'No references supplied'}/></div>
    <p className="helper-text">Source verification and recorded dates describe this catalogue record. They do not imply that current availability or enrolment was checked today.</p>
    {records.length?records.map((record,index)=><div className="evidence-reference" key={`${record.id}-${record.rule}-${index}`}><strong>{record.id}</strong><p>{record.title || 'Source title not supplied'}</p>{record.explanation && <p className="helper-text">Recorded rule explanation: {record.explanation}</p>}<div className="evidence-reference-meta">{record.rule && <span>Rule {record.rule}</span>}{record.page && <span>Recorded page {record.page}</span>}<span>{record.status?`Recorded status: ${record.status.replaceAll('_',' ')}`:'Verification status not supplied here'}</span>{record.date && <span>Recorded review date: {record.date}</span>}{record.locator && <span>{record.locator}</span>}<span>Recorded version: {record.version || 'not supplied'}</span></div>{sourceLocation(record) ? <a href={sourceLocation(record)} target="_blank" rel="noreferrer">Open recorded source{record.page ? ` · page ${record.page}` : ''}</a> : <p className="helper-text">No verified accessible link is available here. The source identifier and recorded location above remain copyable.</p>}</div>):<p className="workspace-warning">No source reference was supplied here. Inspect the evidence register before relying on this result.</p>}
    {data.evidence_issues?.length>0 && <div className="workspace-warning"><h4>Evidence gaps</h4><ul>{data.evidence_issues.map((issue,index)=><li key={index}>{typeof issue==='string'?issue:JSON.stringify(issue)}</li>)}</ul></div>}
    {!compact && <button className="text-button" onClick={()=>downloadText("curricupath-evidence-reading.html",offlineReading("Recorded evidence",evidenceText(data)),"text/html")}>Export offline reading copy</button>}
    {!compact && <details className="issue-draft"><summary>Prepare a local evidence issue</summary><p>This draft is not sent anywhere. Review the identifiers and add an explanation before sharing it yourself.</p><label className="workspace-field">Your evidence issue explanation<textarea name="evidence-issue" autoComplete="off" rows={3} value={explanation} onChange={e=>setExplanation(e.target.value)} maxLength={2000}/></label><pre role="region" tabIndex={0} aria-label="Export preview">{issueText}</pre><button className="secondary-button" onClick={()=>downloadText('curricupath-evidence-issue.txt',issueText)}>Export local issue draft</button></details>}
  </section>;
}
