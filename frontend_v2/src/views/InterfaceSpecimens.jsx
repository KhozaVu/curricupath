import React, { useState } from 'react';
import { ArrowUpRight, Check, Search } from 'lucide-react';
import { AsyncPanel, StatusPill } from './shared';
import { Drawer } from './Shell';

// Review-only entry (?ui-review=1): isolated from academic and user state.
export default function InterfaceSpecimens() {
  const [theme,setTheme]=useState('dark');
  const [dialog,setDialog]=useState(false);
  const [notice,setNotice]=useState('');
  const [selected,setSelected]=useState('Plan');
  return <div className="app-shell specimen-shell" data-theme={theme} data-motion="reduced">
    <main className="specimen-page" inert={dialog} tabIndex={-1}>
      <header className="view-heading"><div><span className="eyebrow">CurricuPath · interface review</span><h1>One visual language.</h1><p>Shared foundations and interaction states. No personal data is used here.</p></div><button className="secondary-button" onClick={()=>setTheme(theme==='dark'?'light':'dark')}>Switch to {theme==='dark'?'Daylight':'Dusk'}</button></header>
      <div className="specimen-grid">
        <section><h2>Actions</h2><div className="specimen-actions"><button className="primary-button" onClick={()=>setNotice('Action completed.')}>Primary action <ArrowUpRight size={17} aria-hidden="true" /></button><button className="secondary-button" onClick={()=>setNotice('Secondary action completed.')}>Secondary action</button><button className="text-button" onClick={()=>setNotice('Text action completed.')}>Text action</button><button className="primary-button" disabled>Unavailable</button><button className="secondary-button" aria-busy="true" disabled>Saving…</button><button className="icon-button" aria-label="Search specimen" onClick={()=>setNotice('Search action selected.')}><Search size={18} aria-hidden="true" /></button></div></section>
        <section><h2>Selection</h2><div role="group" className="segmented" aria-label="Review views">{['Plan','Advisor','Explore'].map(value=><button key={value} className={value===selected?'active':''} aria-pressed={value===selected} onClick={()=>setSelected(value)}>{value}</button>)}</div><p>{selected} is selected.</p><div className="specimen-actions"><StatusPill tone="green">Eligible</StatusPill><StatusPill tone="gold">Clarification required</StatusPill><StatusPill>Manual review required</StatusPill><StatusPill tone="outline">Not eligible</StatusPill></div></section>
        <section><h2>Fields and validation</h2><label className="specimen-field">Module code<input name="specimen-module" autoComplete="off" spellCheck={false} placeholder="For example, ELEN4025A…" /></label><label className="specimen-field">Unrecognised entry<input name="specimen-invalid" autoComplete="off" defaultValue="UNKNOWN" aria-invalid="true" aria-describedby="specimen-error" /></label><p id="specimen-error" className="field-error">This example code is not in the catalogue. Review the code before adding it.</p><label className="motion-choice"><input type="checkbox" name="specimen-confirm" /><span><strong>Confirm a declaration</strong><small>The control and its text share one touch target.</small></span></label></section>
        <section><h2>Asynchronous states</h2><AsyncPanel loading title="Checking recorded requirements…" /><AsyncPanel title="Records are unavailable" error="The request could not finish. Your declarations are preserved." onRetry={()=>setNotice('Retry selected.')} /></section>
        <section><h2>Card and overlay</h2><button className="specimen-card" onClick={()=>setDialog(true)}><span className="eyebrow">Evidence</span><strong>A deliberately long title that stays readable across narrow screens and both colour themes</strong><span>Inspect the shared dialog <ArrowUpRight size={17} aria-hidden="true" /></span></button></section>
        <section><h2>Type and numbers</h2><h3>Understand your next connection.</h3><p>Practical body copy explains the choice. Editorial headings provide character while module codes retain a precise visual form.</p><p className="module-code">ELEN4025A · 24 credits · 1,234</p><p className="eyebrow">Source location · recorded evidence</p></section>
      </div>
      <div className="specimen-notice" role="status" aria-live="polite">{notice && <><Check size={18} aria-hidden="true" />{notice}<button className="text-button" onClick={()=>setNotice('')}>Dismiss</button></>}</div>
    </main>
    {dialog && <Drawer title="Shared overlay specimen" onClose={()=>setDialog(false)}><h3>A clear reading surface.</h3><p>Use Tab and Shift+Tab to navigate this modal. Escape or Close returns focus to the card that opened it.</p><button className="secondary-button" onClick={()=>setDialog(false)}>Return to specimens</button></Drawer>}
  </div>;
}
