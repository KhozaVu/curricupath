import { Check, ChevronRight, ShieldCheck, Search, X } from "lucide-react";
import React from "react";

import { useState } from "react";

import { HistoryImport } from "./HistoryImport";
import { assignedState, moveDeclaration, declarationConflicts, HISTORY_FIELDS } from "../academicWorkspace.mjs";
import { INTERESTS, CAREER_GOALS, AsyncPanel, usePersistentState, downloadText } from "./shared";
function ChoiceChips({ options, selected, onToggle, name }) {
  return (
    <div className="choice-chips">
      {options.map(([value, label]) => (
        <label
          className={`choice-chip ${selected.includes(value) ? "selected" : ""}`}
          key={value}
        >
          <input
            type="checkbox"
            name={name}
            checked={selected.includes(value)}
            onChange={() => onToggle(value)}
          />
          {selected.includes(value) && <Check size={13} />}
          <span>{label}</span>
        </label>
      ))}
    </div>
  );
}

function ModuleSelector({
  modules,
  completed,
  current,
  planned,
  repeating,
  onToggle,
  loading,
  error,
  onRetry,
}) {
  const [selectionMode, setSelectionMode] = useState("completed");
  const [query, setQuery] = useState("");
  const [yearFilter, setYearFilter] = useState("all");
  const selections = { completed, current, planned, repeating };
  const selected = selections[selectionMode];
  const matching = modules.filter(
    (module) =>
      (yearFilter === "all" || String(module.year_of_study) === yearFilter) &&
      `${module.course_code} ${module.course_name}`
        .toLowerCase()
        .includes(query.trim().toLowerCase()),
  );
  const grouped = matching.reduce((groups, module) => {
    (groups[module.year_of_study] ||= []).push(module);
    return groups;
  }, {});

  return (
    <section className="profile-card module-history-card" id="profile-history" data-profile-section="history">
      <div className="card-heading split-heading">
        <div>
          <span>Step 2</span>
          <h2>Which modules have you done?</h2>
        </div>
        <div role="group" className="mode-tabs" aria-label="Module selection type">
          {[
            ["completed", "Completed"],
            ["current", "Current"],
            ["planned", "Planned"],
            ["repeating", "Repeating"],
          ].map(([value, label]) => (
            <button
              key={value}
              className={selectionMode === value ? "active" : ""}
              onClick={() => setSelectionMode(value)}
              aria-pressed={selectionMode === value}
            >
              {label}
              <b>{selections[value].length}</b>
            </button>
          ))}
        </div>
      </div>
      <p className="helper-text">
        Grouped by year. Mark a module Repeating only if you must take it again.
      </p>
      <div className="history-filters">
        <label className="inline-search">
          <Search size={17} />
          <input
            aria-label="Find a module in your history"
            placeholder="Module code or name…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          {query && (
            <button
              className="icon-button"
              aria-label="Clear module history search"
              onClick={() => setQuery("")}
            >
              <X size={16} />
            </button>
          )}
        </label>
        <label>
          Year
          <select
            aria-label="Filter module history by year"
            value={yearFilter}
            onChange={(event) => setYearFilter(event.target.value)}
          >
            <option value="all">All years</option>
            {[...new Set(modules.map((module) => module.year_of_study))]
              .sort()
              .map((year) => (
                <option key={year} value={year}>
                  Year {year}
                </option>
              ))}
          </select>
        </label>
      </div>
      {!loading && modules.length > 0 && (
        <p className="history-filter-summary" role="status">
          {matching.length} modules shown · Selecting as {selectionMode}
          {!matching.length && ". Try another year or search."}
        </p>
      )}
      {(loading || error) && (
        <AsyncPanel
          loading={loading}
          title={
            error
              ? "Your curriculum could not be loaded"
              : "Loading curriculum modules…"
          }
          error={error}
          onRetry={onRetry}
        />
      )}
      {!loading && !error && !modules.length && (
        <div className="empty-panel">
          Choose a programme to load its curriculum.
        </div>
      )}
      {!loading &&
        Object.entries(grouped).map(([year, yearModules]) => (
          <div className="year-group" key={year}>
            <div className="year-label">
              <span>Year {year}</span>
              <small>{yearModules.length} modules</small>
            </div>
            <div className="module-chips">
              {yearModules.map((module) => {
                const checked = selected.includes(module.course_code);
                return (
                  <button
                    key={`${selectionMode}-${module.course_code}`}
                    className={`module-chip ${checked ? "selected" : ""}`}
                    onClick={() => onToggle(selectionMode, module.course_code)}
                    aria-pressed={checked}
                  >
                    <strong>{module.course_code}</strong>
                    <span>{module.course_name}</span>
                    {checked && <Check size={14} />}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
    </section>
  );
}

export function ProfilePage({
  profile,
  setProfile: commitProfile,
  persistence,
  modules,
  loading,
  error,
  onRetry,
  onSave,
}) {
  const [storedStep,setStep]=usePersistentState('curricupath-profile-step-v1',profile.programme?'all':'basics');
  const step=['basics','history','preferences','all'].includes(storedStep)?storedStep:'all';
  const [undo,setUndo]=useState(null);
  const [pendingMove,setPendingMove]=useState(null);
  const [feedback,setFeedback]=useState('');
  const setProfile = update => {
    const next=typeof update==='function'?update(profile):update;
    setUndo(profile);commitProfile(next);setFeedback('Profile updated. Changes are remembered on this device.');
  };
  const toggleList = (field,value)=>setProfile({...profile,[field]:profile[field].includes(value)?profile[field].filter(item=>item!==value):[...profile[field],value]});
  const toggleModule = (field,code)=>{
    const previous=assignedState(profile,code);
    if(previous && previous!==field){setPendingMove({field,code,previous});return;}
    setProfile(moveDeclaration(profile,code,field));
  };

  const conflicts=declarationConflicts(profile);
  const unavailable=!loading && !error ? [...new Set(HISTORY_FIELDS.flatMap(key=>profile[key] || []))].filter(code=>!modules.some(m=>m.course_code===code)) : [];
  return (
    <div className="page-content profile-page" data-profile-step={step}>
      <div role="group" className="profile-stepper" aria-label="Profile setup steps">{[['basics','1 · Programme'],['history','2 · History'],['preferences','3 · Preferences (optional)'],['all','Review all']].map(([value,label])=><button key={value} aria-pressed={step===value} className={step===value?'active':''} onClick={()=>setStep(value)}>{label}</button>)}</div>
      <div className="profile-edit-feedback"><span role="status">{persistence==='error'?'Local saving failed. Keep this page open and export your declarations before leaving.':feedback || 'Edit your declarations at your own pace. Optional preferences can wait.'}</span>{undo && <button className="secondary-button" onClick={()=>{commitProfile(undo);setUndo(null);setFeedback('Previous profile restored.');}}>Undo last profile change</button>}</div>
      {pendingMove && <div className="workspace-warning" role="alert"><p>{pendingMove.code} is currently {pendingMove.previous}. Move it to {pendingMove.field}?</p><button className="secondary-button" onClick={()=>{setProfile(moveDeclaration(profile,pendingMove.code,pendingMove.field));setPendingMove(null);}}>Confirm module move</button><button className="text-button" onClick={()=>setPendingMove(null)}>Keep current declaration</button></div>}
      {conflicts.length>0 && <section className="workspace-warning" role="alert"><h2>Resolve conflicting declarations</h2><p>Each module needs one declared state. Evaluation is paused until you choose which state to retain.</p>{conflicts.map(item=><div key={item.code}><p>{item.code}: {item.states.join(', ')}</p>{item.states.map(field=><button className="secondary-button" key={field} onClick={()=>setProfile({...profile,...Object.fromEntries(HISTORY_FIELDS.map(key=>[key,key===field?[...new Set(profile[key])]:profile[key].filter(c=>c!==item.code)]))})}>Keep {item.code} as {field}</button>)}</div>)}</section>}
      {unavailable.length>0 && <p className="workspace-warning">Declarations outside the loaded programme catalogue: {unavailable.join(', ')}. These have been retained. Review your programme and declarations before requesting advice.</p>}
      <nav className="profile-section-nav" aria-label="Profile sections">
        {[
          ["profile-basics", "Programme"],
          ["profile-history", "Module history"],
          ["profile-record", "Record confirmation"],
          ["profile-preferences", "Interests"],
        ].map(([id, label]) => (
          <button
            className="text-button"
            key={id}
            onClick={() =>
              { setStep("all"); requestAnimationFrame(()=>document.getElementById(id)?.scrollIntoView({ block: "start" })); }
            }
          >
            {label}
          </button>
        ))}
      </nav>
      <div className="profile-setup-summary">
        <span>
          <strong>{profile.programme || "Programme not chosen"}</strong>
          <small>
            {
              [
                ...new Set([
                  ...(profile.completed || []),
                  ...(profile.current || []),
                  ...(profile.planned || []),
                  ...(profile.repeating || []),
                ]),
              ].length
            }{" "}
            declared modules
          </small>
        </span>
        <span className="history-completeness">
          {profile.historyConfirmed
            ? "History declared complete"
            : "Unselected history stays unknown"}
        </span>
      </div>
      <div className="prototype-notice">
        <ShieldCheck size={17} />
        <span>Your profile stays in this browser.</span>
      </div>
      <section className="profile-card" id="profile-basics" data-profile-section="basics">
        <div className="card-heading">
          <span>Step 1</span>
          <h2>Where are you in the curriculum?</h2>
        </div>
        <label className="name-field">
          What should we call you?{" "}
          <input
            value={profile.name || ""}
            onChange={(event) =>
              setProfile({ ...profile, name: event.target.value })
            }
            placeholder="Your first name (optional)"
            maxLength={60}
          />
        </label>
        <div className="field-grid three-columns">
          <label>
            Study stage
            <select
              value={profile.stage}
              onChange={(event) =>
                setProfile({ ...profile, stage: event.target.value })
              }
            >
              <option value="year_1">First year</option>
              <option value="year_2">Second year</option>
              <option value="year_3_semester_1">Third year, Semester 1</option>
              <option value="year_3_semester_2">Third year, Semester 2</option>
              <option value="year_4_semester_1">Fourth year, Semester 1</option>
              <option value="year_4_semester_2">Fourth year, Semester 2</option>
            </select>
          </label>
          <label>
            Programme
            <select
              value={profile.programme}
              onChange={(event) =>
                setProfile({ ...profile, programme: event.target.value, historyConfirmed:false })
              }
            >
              <option value="">Choose programme</option>
              <option value="EFA03">Electrical Engineering (EFA03)</option>
              <option value="EFA04">Information Engineering (EFA04)</option>
            </select>
          </label>
          <label>
            Stream
            <select
              value={profile.stream}
              onChange={(event) =>
                setProfile({ ...profile, stream: event.target.value })
              }
            >
              <option value="general">General</option>
              <option value="power">Power</option>
              <option value="communications">Communications</option>
              <option value="control_robotics">Control and robotics</option>
              <option value="software_data">Software and data</option>
            </select>
          </label>
        </div>
      </section>

      <div data-profile-section="history"><HistoryImport profile={profile} modules={modules} onApply={setProfile} /></div>
      <ModuleSelector
        modules={modules}
        completed={profile.completed}
        current={profile.current}
        planned={profile.planned}
        repeating={profile.repeating || []}
        onToggle={toggleModule}
        loading={loading}
        error={error}
        onRetry={onRetry}
      />

      <section
        className="profile-card history-confirmation-card"
        id="profile-record" data-profile-section="history"
      >
        <label className="history-confirmation">
          <input
            type="checkbox"
            checked={Boolean(profile.historyConfirmed)}
            onChange={(event) =>
              setProfile({ ...profile, historyConfirmed: event.target.checked })
            }
          />
          <span>
            <strong>My module selections are complete</strong>
            <small>
              If unchecked, anything you did not select stays unknown and the
              advisor will ask.
            </small>
          </span>
        </label>
      </section>

      <section className="profile-card" data-profile-section="history">
        <div className="card-heading">
          <span>Step 3 — optional</span>
          <h2>Anything unusual about your record?</h2>
          <p>
            A concession, a transfer, or a result that looks wrong. The advisor
            will not guess on these.
          </p>
        </div>
        <label className="field-label" htmlFor="manual-review-note">
          Optional
        </label>
        <input
          id="manual-review-note"
          type="text"
          maxLength={300}
          autoComplete="off"
          placeholder="e.g. a concession was granted but no letter is on record…"
          value={profile.reviewNote || ""}
          onChange={(event) =>
            setProfile({ ...profile, reviewNote: event.target.value })
          }
        />
      </section>

      <section className="profile-card" id="profile-preferences" data-profile-section="preferences">
        <div className="card-heading">
          <span>Step 4 — optional</span>
          <h2>What should suggestions lean toward?</h2>
        </div>
        <div className="preference-grid">
          <div>
            <label className="field-label">Interest areas</label>
            <ChoiceChips
              options={INTERESTS}
              selected={profile.interests}
              onToggle={(value) => toggleList("interests", value)}
              name="interests"
            />
          </div>
          <div>
            <label className="field-label">Career goals</label>
            <ChoiceChips
              options={CAREER_GOALS}
              selected={profile.careers}
              onToggle={(value) => toggleList("careers", value)}
              name="careers"
            />
          </div>
        </div>
        <div className="field-grid preference-controls">
          <label>
            Preferred workload
            <select
              value={profile.workload}
              onChange={(event) =>
                setProfile({ ...profile, workload: event.target.value })
              }
            >
              <option value="">No preference</option>
              <option value="light">Light</option>
              <option value="moderate">Moderate</option>
              <option value="heavy">Heavy</option>
            </select>
          </label>

        </div>
        <p className="helper-text">
          Preferences guide the prompts you choose. They never override
          programme, prerequisite, corequisite, or exclusion rules.
        </p>
      </section>

      {step!=='all' && <div className="workspace-toolbar"><button className="text-button" onClick={()=>setStep(step==='preferences'?'history':'basics')}>Previous step</button><button className="secondary-button" onClick={()=>setStep(step==='basics'?'history':step==='history'?'preferences':'all')}>{step==='history'?'Optional preferences':step==='preferences'?'Review all declarations':'Continue to module history'}</button>{step==='history' && <button className="text-button" onClick={()=>setStep('all')}>Skip preferences and review</button>}</div>}
      <details className="workspace-export"><summary>Preview and export your declarations</summary><p>This includes your module history, preferences and review note. Review the personal information before sharing.</p><pre role="region" tabIndex={0} aria-label="Export preview">{JSON.stringify(profile,null,2)}</pre><button className="secondary-button" onClick={()=>downloadText('curricupath-declared-profile.json',JSON.stringify({exportedAt:new Date().toISOString(),profile},null,2))}>Export declared profile</button></details>
      <div className="save-profile-bar">
        <div>
          <strong>{profile.programme || "No programme selected"}</strong>
          <span>
            {profile.completed.length} completed, {profile.current.length}{" "}
            current, {profile.planned.length} planned,{" "}
            {(profile.repeating || []).length} repeating | history{" "}
            {profile.historyConfirmed ? "confirmed" : "incomplete"}
          </span>
        </div>
        <button
          className="primary-button"
          disabled={!profile.programme}
          onClick={onSave}
        >
          Save degree profile <ChevronRight size={18} />
        </button>
      </div>
    </div>
  );
}
