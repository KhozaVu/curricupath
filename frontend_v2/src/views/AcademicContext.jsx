import React from 'react';
import { historySummary } from '../experienceModel.mjs';
export function AcademicContext({profile,onEdit}) {
  const history=historySummary(profile);
  return <details className="academic-context" open={!profile.historyConfirmed}><summary><span>{profile.programme} · {history.label}</span><span>Context used for guidance</span></summary><p>{history.text}</p><dl>{[['completed','Declared completed'],['current','Declared current'],['planned','Declared planned'],['repeating','Declared repeating']].map(([key,label])=><div key={key}><dt>{label}</dt><dd>{profile[key]?.join(', ') || (profile.historyConfirmed?'None declared':'Not supplied · unknown')}</dd></div>)}</dl>{profile.reviewNote && <p>Declared review circumstance: {profile.reviewNote}</p>}<button className="text-button" onClick={onEdit}>Edit context before asking</button></details>;
}
