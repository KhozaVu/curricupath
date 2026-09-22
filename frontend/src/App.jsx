import {
  Award,
  BookOpen,
  Bot,
  BriefcaseBusiness,
  Check,
  ChevronLeft,
  ChevronRight,
  CircleUserRound,
  Database,
  ExternalLink,
  GraduationCap,
  LibraryBig,
  LockKeyhole,
  Menu,
  MessageSquareText,
  RefreshCw,
  Route,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Trophy,
  Moon,
  Sun,
  X,
} from "lucide-react";
import React from "react";
import { useEffect, useRef, useState } from "react";

const PAGE_META = {
  profile: ["Profile setup", "Tell the advisor about your stage, programme and module history"],
  advisor: ["Curriculum advisor", "Ask about pathways, electives and prerequisite gates"],
  library: ["Course library", "Verified public courses with ratings and source trails"],
  careers: ["Career paths", "Explore course options connected to a professional direction"],
  journey: ["My journey", "Your pathway progress across study years"],
  achievements: ["Achievements", "Milestones unlocked as your journey progresses"],
  evidence: ["Evidence & sources", "Every recommendation traces to a dated source"],
};

const NAVIGATION = [
  ["profile", CircleUserRound, "Profile setup"],
  ["advisor", MessageSquareText, "Curriculum advisor"],
  ["library", LibraryBig, "Course library"],
  ["careers", BriefcaseBusiness, "Career paths"],
  ["journey", Route, "My journey"],
  ["achievements", Award, "Achievements"],
  ["evidence", Database, "Evidence & sources"],
];

const INITIAL_MESSAGES = [
  {
    role: "assistant",
    text: "Ask about module eligibility, a curriculum year, a verified public course, or a career path.",
    suggestions: [
      "module eligibility",
      "Recommend EFA04 year 4 electives for machine learning",
      "Find an electric circuits course",
    ],
  },
];

const INTERESTS = [
  ["machine_learning", "Machine learning"],
  ["software", "Software development"],
  ["electric_circuits", "Electric circuits"],
  ["control", "Control systems"],
  ["communications", "Communications"],
  ["networking", "Networking"],
  ["cybersecurity", "Cybersecurity"],
  ["data_science", "Data science"],
];

const CAREER_GOALS = [
  ["graduate_engineer", "Graduate engineer"],
  ["postgraduate_study", "Postgraduate study"],
  ["data_science", "Data or ML role"],
  ["embedded_systems", "Embedded systems"],
  ["product_systems", "Product and systems"],
];

const titleCase = value => String(value ?? "")
  .replaceAll("_", " ")
  .replace(/\b\w/g, letter => letter.toUpperCase());

const moduleCodes = value => [...new Set(
  String(value ?? "")
    .split(/[\s,;]+/)
    .map(code => code.trim().toUpperCase())
    .filter(Boolean),
)];

function readJson(key, fallback) {
  try {
    const value = localStorage.getItem(key);
    return value === null ? fallback : JSON.parse(value);
  } catch {
    return fallback;
  }
}

async function getJson(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
  return data;
}

function usePersistentState(key, initialValue) {
  const [value, setValue] = useState(() => readJson(key, initialValue));
  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(value));
  }, [key, value]);
  return [value, setValue];
}

function usePersistentString(key, initialValue = "") {
  const [value, setValue] = useState(() => localStorage.getItem(key) || initialValue);
  useEffect(() => {
    if (value) localStorage.setItem(key, value);
    else localStorage.removeItem(key);
  }, [key, value]);
  return [value, setValue];
}

function Stars({ rating, scale = 5 }) {
  const percentage = Math.max(0, Math.min(100, (Number(rating) / Number(scale || 5)) * 100));
  return (
    <span className="rating-display" aria-label={`Rated ${rating} out of ${scale}`}>
      <span className="stars" aria-hidden="true">
        <span>★★★★★</span>
        <span className="stars-fill" style={{ width: `${percentage}%` }}>★★★★★</span>
      </span>
      <span className="rating-number">{rating}/{scale}</span>
    </span>
  );
}

function StatusPill({ children, tone = "blue" }) {
  return <span className={`status-pill ${tone}`}>{children}</span>;
}

function Sidebar({ page, collapsed, mobileOpen, ready, summary, onNavigate, onToggle, onClose }) {
  return (
    <>
      <aside className={`sidebar ${collapsed ? "collapsed" : ""} ${mobileOpen ? "mobile-open" : ""}`}>
        <div className="brand-block">
          <div className="brand-mark"><GraduationCap size={24} /></div>
          {!collapsed && (
            <div>
              <strong>CurricuPath</strong>
              <span>Evidence-led guidance</span>
            </div>
          )}
          <button className="mobile-close" onClick={onClose} aria-label="Close navigation"><X /></button>
        </div>

        {!collapsed && (
          <p className="brand-description">AI-assisted curriculum guidance for Wits EIE students.</p>
        )}

        <nav aria-label="Main navigation">
          {NAVIGATION.map(([id, Icon, label]) => {
            const locked = id === "advisor" && !ready;
            return (
              <button
                key={id}
                className={`nav-item ${page === id ? "active" : ""} ${locked ? "locked" : ""}`}
                onClick={() => onNavigate(id)}
                title={collapsed ? label : undefined}
                aria-label={locked ? `${label}, complete profile setup first` : label}
              >
                <Icon size={18} />
                {!collapsed && <span>{label}</span>}
                {!collapsed && locked && <LockKeyhole className="nav-lock" size={13} />}
              </button>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          {!collapsed && summary && (
            <div className="catalogue-mini">
              <ShieldCheck size={17} />
              <div><strong>{summary.verified_sources}</strong><span>verified sources</span></div>
            </div>
          )}
          {!collapsed && <small>Prototype only. Not an official registration tool.</small>}
          <button className="collapse-button" onClick={onToggle} aria-label={collapsed ? "Expand navigation" : "Retract navigation"}>
            {collapsed ? <ChevronRight size={18} /> : <><ChevronLeft size={18} /><span>Retract</span></>}
          </button>
        </div>
      </aside>
      {mobileOpen && <button className="sidebar-scrim" onClick={onClose} aria-label="Close navigation overlay" />}
    </>
  );
}

function PageHeader({ page, onMenu, onReset, theme, onThemeChange }) {
  const [title, subtitle] = PAGE_META[page];
  return (
    <header className="page-header">
      <button className="menu-button" onClick={onMenu} aria-label="Open navigation"><Menu /></button>
      <div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <div className="header-actions">
        <div className="theme-switch" role="group" aria-label="Colour theme">
          <button className={theme === "light" ? "active" : ""} onClick={() => onThemeChange("light")} aria-pressed={theme === "light"}><Sun size={14} /><span>Light</span></button>
          <button className={theme === "dark" ? "active" : ""} onClick={() => onThemeChange("dark")} aria-pressed={theme === "dark"}><Moon size={14} /><span>Dark</span></button>
        </div>
        <button className="secondary-button reset-button" onClick={onReset}><RefreshCw size={15} />Reset session</button>
      </div>
    </header>
  );
}

function ChoiceChips({ options, selected, onToggle, name }) {
  return (
    <div className="choice-chips">
      {options.map(([value, label]) => (
        <label className={`choice-chip ${selected.includes(value) ? "selected" : ""}`} key={value}>
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

function ModuleSelector({ modules, completed, current, planned, onToggle, loading }) {
  const [selectionMode, setSelectionMode] = useState("completed");
  const selected = selectionMode === "completed" ? completed : selectionMode === "current" ? current : planned;
  const grouped = modules.reduce((groups, module) => {
    (groups[module.year_of_study] ||= []).push(module);
    return groups;
  }, {});

  return (
    <section className="profile-card module-history-card">
      <div className="card-heading split-heading">
        <div><span>Module history</span><h2>Select your curriculum modules</h2></div>
        <div className="mode-tabs" role="tablist" aria-label="Module selection type">
          {[["completed", "Completed"], ["current", "Current"], ["planned", "Planned"]].map(([value, label]) => (
            <button
              key={value}
              className={selectionMode === value ? "active" : ""}
              onClick={() => setSelectionMode(value)}
              role="tab"
              aria-selected={selectionMode === value}
            >
              {label}<b>{value === "completed" ? completed.length : value === "current" ? current.length : planned.length}</b>
            </button>
          ))}
        </div>
      </div>
      <p className="helper-text">Modules are separated by year. Choose a tab, then click each module that belongs in that part of your profile.</p>
      {loading && <div className="empty-panel">Loading curriculum modules...</div>}
      {!loading && !modules.length && <div className="empty-panel">Choose a programme to load its curriculum.</div>}
      {!loading && Object.entries(grouped).map(([year, yearModules]) => (
        <div className="year-group" key={year}>
          <div className="year-label"><span>Year {year}</span><small>{yearModules.length} modules</small></div>
          <div className="module-chips">
            {yearModules.map(module => {
              const checked = selected.includes(module.course_code);
              return (
                <button
                  key={`${selectionMode}-${module.course_code}`}
                  className={`module-chip ${checked ? "selected" : ""}`}
                  onClick={() => onToggle(selectionMode, module.course_code)}
                  aria-pressed={checked}
                >
                  <strong>{module.course_code}</strong><span>{module.course_name}</span>
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

function ProfilePage({ profile, setProfile, modules, loading, onSave }) {
  const toggleList = (field, value) => {
    setProfile(current => ({
      ...current,
      [field]: current[field].includes(value)
        ? current[field].filter(item => item !== value)
        : [...current[field], value],
    }));
  };
  const toggleModule = (field, code) => {
    setProfile(current => {
      const removing = current[field].includes(code);
      const next = {
        ...current,
        completed: current.completed.filter(item => item !== code),
        current: current.current.filter(item => item !== code),
        planned: current.planned.filter(item => item !== code),
      };
      if (!removing) next[field] = [...next[field], code];
      return next;
    });
  };

  return (
    <div className="page-content profile-page">
      <div className="prototype-notice"><ShieldCheck size={17} /><span>Your profile stays in this browser. Eligibility remains deterministic and source-based.</span></div>
      <section className="profile-card">
        <div className="card-heading"><span>Academic details</span><h2>Where are you in the curriculum?</h2></div>
        <div className="field-grid three-columns">
          <label>Study stage
            <select value={profile.stage} onChange={event => setProfile({...profile, stage: event.target.value})}>
              <option value="year_1">First year</option>
              <option value="year_2">Second year</option>
              <option value="year_3_semester_1">Third year, Semester 1</option>
              <option value="year_3_semester_2">Third year, Semester 2</option>
              <option value="year_4_semester_1">Fourth year, Semester 1</option>
              <option value="year_4_semester_2">Fourth year, Semester 2</option>
            </select>
          </label>
          <label>Programme
            <select value={profile.programme} onChange={event => setProfile({...profile, programme: event.target.value})}>
              <option value="">Choose programme</option>
              <option value="EFA03">Electrical Engineering (EFA03)</option>
              <option value="EFA04">Information Engineering (EFA04)</option>
            </select>
          </label>
          <label>Stream
            <select value={profile.stream} onChange={event => setProfile({...profile, stream: event.target.value})}>
              <option value="general">General</option>
              <option value="power">Power</option>
              <option value="communications">Communications</option>
              <option value="control_robotics">Control and robotics</option>
              <option value="software_data">Software and data</option>
            </select>
          </label>
        </div>
      </section>

      <ModuleSelector
        modules={modules}
        completed={profile.completed}
        current={profile.current}
        planned={profile.planned}
        onToggle={toggleModule}
        loading={loading}
      />

      <section className="profile-card history-confirmation-card">
        <label className="history-confirmation">
          <input
            type="checkbox"
            checked={Boolean(profile.historyConfirmed)}
            onChange={event => setProfile({...profile, historyConfirmed: event.target.checked})}
          />
          <span><strong>My module selections are complete</strong><small>When checked, unselected modules are treated as not completed. When unchecked, they remain unknown and the advisor may ask for clarification.</small></span>
        </label>
      </section>

      <section className="profile-card">
        <div className="card-heading"><span>Interests & preferences</span><h2>What should suggestions lean toward?</h2></div>
        <div className="preference-grid">
          <div><label className="field-label">Interest areas</label><ChoiceChips options={INTERESTS} selected={profile.interests} onToggle={value => toggleList("interests", value)} name="interests" /></div>
          <div><label className="field-label">Career goals</label><ChoiceChips options={CAREER_GOALS} selected={profile.careers} onToggle={value => toggleList("careers", value)} name="careers" /></div>
        </div>
        <div className="field-grid preference-controls">
          <label>Preferred workload
            <select value={profile.workload} onChange={event => setProfile({...profile, workload: event.target.value})}>
              <option value="">No preference</option><option value="light">Light</option><option value="moderate">Moderate</option><option value="heavy">Heavy</option>
            </select>
          </label>
          <label>Preferred learning format
            <select value={profile.format} onChange={event => setProfile({...profile, format: event.target.value})}>
              <option value="">No preference</option><option value="online">Online</option><option value="in_person">In person</option><option value="hybrid">Hybrid</option>
            </select>
          </label>
        </div>
        <p className="helper-text">Preferences guide the prompts you choose. They never override programme, prerequisite, corequisite, or exclusion rules.</p>
      </section>

      <div className="save-profile-bar">
        <div><strong>{profile.programme || "No programme selected"}</strong><span>{profile.completed.length} completed, {profile.current.length} current, {profile.planned.length} planned | history {profile.historyConfirmed ? "confirmed" : "incomplete"}</span></div>
        <button className="primary-button" disabled={!profile.programme} onClick={onSave}>Save profile and open advisor <ChevronRight size={18} /></button>
      </div>
    </div>
  );
}

function ResultModuleCard({ item, onOpen }) {
  const info = item.course_information;
  return (
    <button className="chat-result-card" onClick={() => onOpen(item.course_code)}>
      <span className="result-card-top"><StatusPill>{item.course_code}</StatusPill><span className="result-card-status">{item.profile_status ? titleCase(item.profile_status) : <ChevronRight size={16} />}</span></span>
      <strong>{item.course_name}</strong>
      <small>{item.nqf_credits} credits | NQF level {item.nqf_level}</small>
      {info?.cbo_available && (
        <div className="result-facts">
          <span><b>Lecturer</b>{info.lecturer || "Not stated"}</span>
          <span><b>Content</b>{info.scope || "Not stated"}</span>
        </div>
      )}
    </button>
  );
}

function ProfileCourseGroup({ title, items, onOpenModule }) {
  if (!items?.length) return null;
  return (
    <section className="profile-course-group">
      <h3>{title} <span>{items.length}</span></h3>
      {items.map(item => <ResultModuleCard key={item.course_code} item={item} onOpen={onOpenModule} />)}
    </section>
  );
}

function ProgrammeProfileCard({ item }) {
  return (
    <section className="programme-profile-result">
      <div className="result-card-top"><StatusPill>{item.programme_code}</StatusPill><small>{item.duration_years} years | {titleCase(item.study_mode)}</small></div>
      <h3>{item.programme_name}</h3>
      <p>{item.focus}</p>
      <div className="programme-careers">
        <strong>Career opportunities</strong>
        <div className="tag-row">{item.career_opportunities.map(career => <span key={career}>{career}</span>)}</div>
      </div>
      {item.source?.url && <a href={item.source.url} target="_blank" rel="noreferrer">View official Wits programme page <ExternalLink size={13} /></a>}
    </section>
  );
}

function RecommendationCard({ item, isMatch, onSelect, onOpenModule }) {
  const title = item.title || `${item.course_code} - ${item.course_name}`;
  const unmet = [
    ...(item.eligibility?.requirements?.prerequisites || []),
    ...(item.eligibility?.requirements?.corequisites || []),
  ].filter(requirement => !requirement.satisfied);
  const metadata = item.provider
    ? `${item.provider} | ${titleCase(item.level)} | ${titleCase(item.workload)} workload`
    : isMatch
      ? "Select this module"
      : `Year ${item.year_of_study} | ${titleCase(item.requirement_type)}`;

  return (
    <button
      className="chat-result-card"
      onClick={() => isMatch ? onSelect(item.course_code) : item.course_code && onOpenModule(item.course_code)}
    >
      <span className="result-card-top">
        <StatusPill tone={item.provider ? "gold" : "blue"}>{item.course_code || item.provider}</StatusPill>
        {item.score != null && <small>{Math.round(item.score * 100)}% match</small>}
      </span>
      <strong>{title}</strong>
      <small>{metadata}</small>
      {item.matched_tags?.length > 0 && <span className="match-tags">Matches: {item.matched_tags.map(titleCase).join(", ")}</span>}
      {item.eligibility?.assessed && (
        <span className={item.eligibility.completed ? "eligibility-completed" : item.eligibility.eligible ? "eligibility-ok" : "eligibility-warning"}>
          {item.eligibility.completed ? "Completed" : item.eligibility.eligible ? "Eligible with your declared history" : "Not currently eligible"}
        </span>
      )}
      {unmet.length > 0 && <span className="requirements">Needs: {unmet.map(item => item.description).join("; ")}</span>}
      {item.provider_url && <a href={item.provider_url} target="_blank" rel="noreferrer" onClick={event => event.stopPropagation()}>View verified course <ExternalLink size={13} /></a>}
    </button>
  );
}

function ChatMessage({ message, onPrompt, onOpenModule }) {
  const data = message.data;
  const records = data?.recommendations || data?.modules?.slice(0, 12) || data?.module_matches || [];
  return (
    <article className={`message ${message.role}`}>
      {message.role === "assistant" && <span className="avatar"><Bot size={17} /></span>}
      <div className="bubble">
        <strong>{message.role === "user" ? "You" : data?.system === "handbook_rag" ? "Handbook RAG (experimental)" : "CurricuPath"}</strong>
        <p>{message.text}</p>
        {message.suggestions?.length > 0 && (
          <div className="prompt-row">{message.suggestions.map(prompt => <button key={prompt} onClick={() => onPrompt(prompt)}>{prompt}</button>)}</div>
        )}
        {data?.clarification_options?.length > 0 && (
          <div className="prompt-row">{data.clarification_options.map(option => <button key={option} onClick={() => onPrompt(option)}>{option}</button>)}</div>
        )}
        {data?.ranking_mode && <small className="message-note">Ranking: {titleCase(data.ranking_mode)}</small>}
        {data?.review && <small className="message-note">Response check: {data.review.status === "reviewed" ? "Independent review passed" : data.review.status === "rejected" ? "Response blocked by safety checks" : "Deterministic checks passed"}</small>}
        {data?.preferences_applied && <small className="message-note">Preferences: {titleCase(data.preferences_applied.difficulty)} difficulty, {titleCase(data.preferences_applied.workload)} workload</small>}
        {data?.system === "handbook_rag" && data.decision && <small className="message-note">Baseline decision: {titleCase(data.decision)}</small>}
        {data?.citations?.length > 0 && (
          <ul className="citation-list">{data.citations.map(citation => <li key={`${citation.source_id}-${citation.page}`}>{citation.source_id} &middot; {citation.page}</li>)}</ul>
        )}
        {data?.module && <ResultModuleCard item={data.module} onOpen={onOpenModule} />}
        {data?.programme_profile && <ProgrammeProfileCard item={data.programme_profile} />}
        {data?.credit_summary && <CreditSummary summary={data.credit_summary} />}
        {data?.career_options && <CareerOptions options={data.career_options} />}
        {data?.programme_comparison && (
          <div className="programme-comparison-results">
            {data.programme_comparison.recommended_programme_code && <small className="message-note">Closer fit for the stated interest: {data.programme_comparison.recommended_programme_code}</small>}
            {data.programme_comparison.profiles.map(profile => <ProgrammeProfileCard key={profile.programme_code} item={profile} />)}
          </div>
        )}
        {data?.profile_courses && (
          <div className="profile-course-groups">
            <ProfileCourseGroup title="Completed modules" items={data.profile_courses.completed} onOpenModule={onOpenModule} />
            <ProfileCourseGroup title="Currently taking" items={data.profile_courses.current} onOpenModule={onOpenModule} />
          </div>
        )}
        {records.map((item, index) => (
          <RecommendationCard
            key={item.course_id || `${item.course_code}-${index}`}
            item={item}
            isMatch={Boolean(data?.module_matches)}
            onSelect={onPrompt}
            onOpenModule={onOpenModule}
          />
        ))}
      </div>
    </article>
  );
}

function CreditSummary({ summary }) {
  return (
    <section className="credit-summary">
      <strong>{summary.total_nqf_credits} NQF credits in the catalogue</strong>
      <div>{summary.years.map(year => <span key={year.year_of_study}>Year {year.year_of_study}: <b>{year.total_credits}</b> credits</span>)}</div>
      <small>Elective credits use the recorded number of choices required.</small>
    </section>
  );
}

function CareerOptions({ options }) {
  return <div className="career-options">{options.map(option => <section className="career-option" key={option.career_tag}><strong>{option.display_name}</strong><p>{option.description}</p>{option.supporting_courses.length > 0 && <small>Supporting courses: {option.supporting_courses.join(", ")}</small>}</section>)}</div>;
}

function AdvisorPage({ profile, rankingMode, setRankingMode, system, setSystem, handbookRagDemoEnabled, sessionId, setSessionId, messages, setMessages, onEditProfile, onOpenModule }) {
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const logRef = useRef(null);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const askAdvisor = async rawText => {
    const text = String(rawText ?? "").trim();
    if (!text || sending) return;
    setInput("");
    setMessages(current => [...current, { role: "user", text }, { role: "assistant", text: "Checking the audited curriculum data...", waiting: true }]);
    setSending(true);
    try {
      const data = await getJson("/advisor", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          message: text,
          session_id: sessionId,
          programme_code: profile.programme || null,
          completed_modules: moduleCodes(profile.completed.join(",")),
          current_modules: moduleCodes(profile.current.join(",")),
          planned_modules: moduleCodes(profile.planned.join(",")),
          module_states: Object.fromEntries([
            ...profile.completed.map(code => [code, "completed"]),
            ...profile.current.map(code => [code, "current"]),
            ...profile.planned.map(code => [code, "planned"]),
          ]),
          module_history_confirmed: Boolean(profile.historyConfirmed),
          ranking_mode: rankingMode,
          system,
        }),
      });
      if (data.system !== "handbook_rag") {
        setSessionId(data.session_id);
        sessionStorage.setItem("curricupath-session", data.session_id);
      }
      if (data.recommendations?.length) localStorage.setItem("curricupath-first-recommendation", "true");
      setMessages(current => [...current.filter(message => !message.waiting), { role: "assistant", text: data.answer, data }]);
    } catch (error) {
      setMessages(current => [...current.filter(message => !message.waiting), { role: "assistant", text: `I could not complete that request: ${error.message}` }]);
    } finally {
      setSending(false);
    }
  };

  const clearConversation = async () => {
    if (sessionId) await fetch(`/advisor/sessions/${sessionId}`, { method: "DELETE" });
    setSessionId(null);
    sessionStorage.removeItem("curricupath-session");
    setMessages([{ role: "assistant", text: "Conversation cleared. What would you like to plan next?", suggestions: INITIAL_MESSAGES[0].suggestions }]);
  };

  return (
    <div className="page-content advisor-page">
      <div className="prototype-notice"><ShieldCheck size={17} /><span>Experimental prototype. Recommendations are checked against local curriculum rules and source records.</span></div>
      {system === "handbook_rag" && (
        <div className="prototype-notice baseline-notice"><ShieldCheck size={17} /><span>Experimental comparison baseline: retrieval and an LLM only, not checked against curriculum rules. Not an official CurricuPath decision.</span></div>
      )}
      <div className="advisor-profile-bar">
        <div className="profile-summary"><span className="ready-dot"><Check size={13} /></span><div><strong>{profile.programme} profile ready</strong><small>{profile.completed.length} completed | {profile.current.length} current | {profile.planned.length} planned</small></div></div>
        <div className="advisor-actions">
          {handbookRagDemoEnabled && (
            <div className="system-toggle">
              <button type="button" className={system === "curricupath" ? "active" : ""} onClick={() => setSystem("curricupath")}>CurricuPath</button>
              <button type="button" className={system === "handbook_rag" ? "active" : ""} onClick={() => setSystem("handbook_rag")}>Handbook RAG (baseline)</button>
            </div>
          )}
          <label>Course ranking<select value={rankingMode} onChange={event => setRankingMode(event.target.value)}><option value="deterministic">Deterministic</option><option value="prototype">Prototype model</option></select></label>
          <button className="text-button" onClick={onEditProfile}>Edit profile</button>
        </div>
      </div>
      <section className="chat-panel">
        <div className="chat-toolbar"><div><span>Conversation</span><h2>Ask CurricuPath</h2></div><button className="text-button" onClick={clearConversation}>New conversation</button></div>
        <div className="message-log" ref={logRef} aria-live="polite">
          {messages.map((message, index) => <ChatMessage key={`${message.role}-${index}`} message={message} onPrompt={askAdvisor} onOpenModule={onOpenModule} />)}
        </div>
        <div className="quick-context">
          <span>Try asking:</span>
          {INITIAL_MESSAGES[0].suggestions.map(prompt => <button key={prompt} onClick={() => askAdvisor(prompt)}>{prompt}</button>)}
        </div>
        <form className="composer" onSubmit={event => { event.preventDefault(); askAdvisor(input); }}>
          <input value={input} onChange={event => setInput(event.target.value)} placeholder="Ask about electives, prerequisites, a module, or a career path..." maxLength={2000} />
          <button disabled={sending || !input.trim()} aria-label="Send message"><Send size={18} /><span>Send</span></button>
        </form>
      </section>
    </div>
  );
}

function CourseCard({ course, onOpen }) {
  return (
    <button className="course-card" onClick={() => onOpen(course.course_id)}>
      <div className="course-card-top"><span>{course.provider}</span><Stars rating={course.rating_mean} scale={course.rating_scale} /></div>
      <h3>{course.title}</h3>
      <p>{course.description}</p>
      <div className="tag-row"><StatusPill>{titleCase(course.category)}</StatusPill><StatusPill tone="outline">{titleCase(course.level)}</StatusPill></div>
      <div className="course-card-bottom"><span>{Number(course.rating_count).toLocaleString()} ratings</span><strong>{titleCase(course.workload)} workload</strong></div>
    </button>
  );
}

function LibraryPage({ courses, loading, onOpen }) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [level, setLevel] = useState("");
  const [provider, setProvider] = useState("");
  const [workload, setWorkload] = useState("");
  const filtered = courses.filter(course => {
    const haystack = [course.title, course.description, ...course.topic_tags, ...course.interest_tags, ...course.career_tags].join(" ").toLowerCase().replaceAll("_", " ");
    return (!query || haystack.includes(query.toLowerCase()))
      && (!category || course.category === category)
      && (!level || course.level === level)
      && (!provider || course.provider === provider)
      && (!workload || course.workload === workload);
  });
  const categories = [...new Set(courses.map(course => course.category))].sort();
  const providers = [...new Set(courses.map(course => course.provider))].sort();
  return (
    <div className="page-content">
      <div className="filter-panel">
        <label className="search-control">Search<span><Search size={17} /><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search courses and topics..." /></span></label>
        <label>Category<select value={category} onChange={event => setCategory(event.target.value)}><option value="">All categories</option>{categories.map(value => <option key={value} value={value}>{titleCase(value)}</option>)}</select></label>
        <label>Level<select value={level} onChange={event => setLevel(event.target.value)}><option value="">All levels</option><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option></select></label>
        <label>Workload<select value={workload} onChange={event => setWorkload(event.target.value)}><option value="">Any</option><option value="light">Light</option><option value="moderate">Moderate</option><option value="heavy">Heavy</option></select></label>
        <label>Provider<select value={provider} onChange={event => setProvider(event.target.value)}><option value="">All providers</option>{providers.map(value => <option key={value}>{value}</option>)}</select></label>
      </div>
      <div className="results-count">{loading ? "Loading courses..." : `${filtered.length} verified courses found`}</div>
      <div className="course-grid">{filtered.map(course => <CourseCard key={course.course_id} course={course} onOpen={onOpen} />)}</div>
      {!loading && !filtered.length && <div className="empty-panel">No verified courses match these filters.</div>}
    </div>
  );
}

function CareersPage({ careers, loading, onOpenCourse }) {
  const [selected, setSelected] = useState(0);
  const path = careers[selected];
  return (
    <div className="page-content career-page">
      <div className="career-nav">
        <div className="card-heading"><span>Controlled career tags</span><h2>Choose a direction</h2></div>
        {careers.map((career, index) => <button className={selected === index ? "active" : ""} key={career.career_tag} onClick={() => setSelected(index)}><span>{career.display_name}</span><b>{career.course_count}</b></button>)}
      </div>
      <div className="career-content">
        {loading && <div className="empty-panel">Loading career paths...</div>}
        {!loading && !path && <div className="empty-panel">No career-tagged courses are available.</div>}
        {path && <><div className="card-heading"><span>Career pathway</span><h2>{path.display_name}</h2><p>Related interests: {path.related_interests.map(titleCase).join(", ") || "Not specified"}</p></div><div className="course-grid compact">{path.courses.map(course => <CourseCard key={course.course_id} course={course} onOpen={onOpenCourse} />)}</div></>}
      </div>
    </div>
  );
}

function JourneyPage({ modules, profile }) {
  const total = modules.length;
  const completedCount = modules.filter(module => profile.completed.includes(module.course_code)).length;
  const percentage = total ? Math.round((completedCount / total) * 100) : 0;
  const activeModules = modules.filter(module => profile.completed.includes(module.course_code) || profile.current.includes(module.course_code) || profile.planned.includes(module.course_code));
  const grouped = activeModules.reduce((groups, module) => {
    (groups[module.year_of_study] ||= []).push(module);
    return groups;
  }, {});
  return (
    <div className="page-content journey-page">
      <section className="journey-overview">
        <div className="progress-ring" style={{ "--progress": `${percentage * 3.6}deg` }}><span>{percentage}%</span></div>
        <div><span>Overall progress</span><h2>{completedCount} of {total} curriculum records completed</h2><p>Based only on the modules selected in your profile.</p></div>
        <div className="journey-stat"><strong>{profile.current.length + profile.planned.length}</strong><span>current or planned</span></div>
      </section>
      <section className="timeline-card">
        <div className="card-heading"><span>Pathway timeline</span><h2>Your selected modules by year</h2></div>
        {!activeModules.length && <div className="empty-panel">Select completed, current, or planned modules in Profile setup to build your journey.</div>}
        {Object.entries(grouped).map(([year, yearModules]) => (
          <div className="timeline-row" key={year}>
            <div className="timeline-year"><span>Year</span><strong>{year}</strong></div>
            <div className="timeline-modules">{yearModules.map(module => {
              const status = profile.completed.includes(module.course_code) ? "completed" : profile.current.includes(module.course_code) ? "current" : "planned";
              return <div className={`timeline-module ${status}`} key={module.course_code}><strong>{module.course_code}</strong><span>{module.course_name}</span><small>{titleCase(status)}</small></div>;
            })}</div>
          </div>
        ))}
      </section>
      <section className="milestone-card"><Sparkles size={20} /><div><strong>Next milestone</strong><p>{profile.current.length || profile.planned.length ? `Complete your ${profile.current.length + profile.planned.length} current or planned modules, then review fourth-year options with the advisor.` : "Add current or planned modules to see your next milestone."}</p></div></section>
    </div>
  );
}

function AchievementsPage({ profile, modules, ready, evidenceViewed }) {
  const yearThree = modules.filter(module => module.year_of_study === 3);
  const achievements = [
    [CircleUserRound, "Profile complete", "Save your curriculum profile", ready],
    [MessageSquareText, "First recommendation", "Get a recommendation from the advisor", localStorage.getItem("curricupath-first-recommendation") === "true"],
    [Check, "Three down", "Complete at least three modules", profile.completed.length >= 3],
    [Trophy, "Building momentum", "Complete at least ten modules", profile.completed.length >= 10],
    [GraduationCap, "Fourth-year ready", "Complete every third-year curriculum module", yearThree.length > 0 && yearThree.every(module => profile.completed.includes(module.course_code))],
    [BookOpen, "Source auditor", "Open Evidence & Sources", evidenceViewed],
  ];
  const unlocked = achievements.filter(item => item[3]).length;
  return (
    <div className="page-content achievements-page">
      <p className="achievement-intro">Achievements track engagement with this prototype. They do not affect eligibility, ranking, or official academic standing.</p>
      <div className="achievement-summary"><div><span>Journey momentum</span><h2>{unlocked} of {achievements.length} milestones unlocked</h2></div><div className="progress-track"><span style={{ width: `${(unlocked / achievements.length) * 100}%` }} /></div></div>
      <div className="achievement-grid">{achievements.map(([Icon, title, description, isUnlocked]) => <article className={`achievement-card ${isUnlocked ? "unlocked" : "locked"}`} key={title}><span className="achievement-icon"><Icon /></span><StatusPill tone={isUnlocked ? "gold" : "outline"}>{isUnlocked ? "Unlocked" : "Locked"}</StatusPill><h3>{title}</h3><p>{description}</p></article>)}</div>
    </div>
  );
}

function EvidencePage({ evidence, loading }) {
  if (loading) return <div className="page-content"><div className="empty-panel">Loading the audit trail...</div></div>;
  if (!evidence) return <div className="page-content"><div className="empty-panel">Evidence data is currently unavailable.</div></div>;
  const verifiedReferences = evidence.external_references.filter(item => item.status === "verified").length;
  const metrics = [
    [evidence.summary.cbo_covered_modules, "modules with course information"],
    [evidence.summary.missing_cbos, "CBOs still needed"],
    [verifiedReferences, "verified external prerequisites"],
    [evidence.summary.rules, "auditable rules"],
  ];
  return (
    <div className="page-content evidence-page">
      <p className="evidence-intro">Curriculum rules and recommendation evidence remain inspectable. Incomplete records are identified rather than silently treated as verified.</p>
      <div className="evidence-metrics">{metrics.map(([value, label]) => <div key={label}><strong>{value}</strong><span>{label}</span></div>)}</div>
      <section className="evidence-table-card">
        <div className="card-heading"><span>Source register</span><h2>Verified and reviewed evidence</h2></div>
        <div className="evidence-table" role="table">
          <div className="evidence-row evidence-head" role="row"><span>Source document</span><span>Locator</span><span>Reviewed</span><span>Status</span></div>
          {evidence.sources.map(source => <div className="evidence-row" role="row" key={source.source_id}><div><strong>{source.title}</strong><small>{source.authority || source.publisher}</small></div><span>{source.locator || "Provider page"}</span><span>{source.review_date || "Not recorded"}</span><span><StatusPill tone={source.verification_status === "verified" ? "green" : "gold"}>{titleCase(source.verification_status)}</StatusPill></span></div>)}
        </div>
      </section>
      <div className="evidence-columns">
        <section className="evidence-list-card"><div className="card-heading"><span>Prerequisite audit</span><h2>External references</h2></div>{evidence.external_references.map(record => <div className="audit-row" key={`${record.reference}-${record.rule_id}`}><strong>{record.reference}</strong><small>{record.rule_id}</small><p>{record.interpretation}</p></div>)}</section>
        <section className="evidence-list-card"><div className="card-heading"><span>Coverage gaps</span><h2>Missing CBOs</h2></div>{evidence.missing_cbos.map(record => <div className="audit-row" key={record.course_code}><strong>{record.course_code} | {record.course_name}</strong><small>{titleCase(record.status)}</small><p>{record.notes}</p></div>)}</section>
      </div>
    </div>
  );
}

function DetailModal({ detail, onClose }) {
  if (!detail) return null;
  const item = detail.data;
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={event => event.target === event.currentTarget && onClose()}>
      <section className="detail-modal" role="dialog" aria-modal="true" aria-label={item.title || item.course_name}>
        <button className="modal-close" onClick={onClose} aria-label="Close"><X /></button>
        {detail.type === "module" ? <ModuleDetail item={item} /> : <CourseDetail item={item} />}
      </section>
    </div>
  );
}

function Fact({ label, children }) {
  return <div className="fact"><dt>{label}</dt><dd>{children || "Not stated"}</dd></div>;
}

function ModuleDetail({ item }) {
  const info = item.course_information;
  return (
    <>
      <StatusPill>{item.course_code}</StatusPill><h2>{item.course_name}</h2><p className="modal-lead">{item.nqf_credits} NQF credits | Level {item.nqf_level}</p>
      <div className="detail-section"><h3>Programme membership</h3>{item.memberships.map(row => <p key={`${row.programme_code}-${row.year_of_study}`}>{row.programme_code}, Year {row.year_of_study}: {titleCase(row.requirement_type)}</p>)}</div>
      <div className="detail-section"><h3>Requirements</h3>{item.rules.length ? item.rules.map(rule => <div className="rule-summary" key={rule.rule_id}><b>{titleCase(rule.rule_type)}</b><p>{rule.plain_language}</p><small>{rule.source_id}{rule.handbook_page ? `, handbook page ${rule.handbook_page}` : ""}</small></div>) : <p>No direct prerequisite, corequisite, or exclusion rule is recorded.</p>}</div>
      <div className="detail-section"><h3>Course information</h3>{!info.cbo_available ? <p>{info.missing_reason}</p> : <dl><Fact label="Academic staff">{info.lecturer}</Fact><Fact label="Coordinator">{info.course_coordinator}</Fact><Fact label="Evidence year">{info.academic_year}</Fact><Fact label="Total notional hours">{info.hours.notional_hours_total} hours</Fact><Fact label="Weekly guidance">{info.hours.weekly_workload_guidance}</Fact><Fact label="Contact pattern">{info.hours.contact_pattern}</Fact><Fact label="Scope">{info.scope}</Fact><Fact label="Prescribed material">{info.prescribed_materials}</Fact><Fact label="Additional material">{info.additional_materials}</Fact></dl>}</div>
    </>
  );
}

function CourseDetail({ item }) {
  return (
    <>
      <StatusPill tone="gold">{item.provider}</StatusPill><h2>{item.title}</h2><p className="modal-lead">{item.description}</p><Stars rating={item.rating_mean} scale={item.rating_scale} />
      <div className="detail-section"><h3>Course details</h3><p>{Number(item.rating_count).toLocaleString()} public ratings | {titleCase(item.level)} | {titleCase(item.workload)} workload | {titleCase(item.format)}</p></div>
      <div className="detail-section"><h3>Outcomes</h3><ul>{item.outcomes.map(outcome => <li key={outcome}>{outcome}</li>)}</ul></div>
      <div className="detail-section"><h3>Evidence</h3><p>{item.source.title} | {titleCase(item.source.verification_status)} | reviewed {item.audit.audit_date}</p><a className="primary-link" href={item.provider_url} target="_blank" rel="noreferrer">Open provider page <ExternalLink size={15} /></a></div>
    </>
  );
}

export function App() {
  const requested = window.location.hash.slice(1);
  const [profile, setProfile] = usePersistentState("curricupath-profile", {
    stage: "year_4_semester_1",
    programme: localStorage.getItem("curricupath-programme") || "",
    stream: "general",
    completed: readJson("curricupath-completed", []),
    current: [], planned: [], historyConfirmed: false,
    interests: [], careers: [], workload: "", format: "",
  });
  const [savedProgramme, setSavedProgramme] = usePersistentString("curricupath-curriculum-ready");
  const ready = Boolean(profile.programme && savedProgramme === profile.programme);
  const validPage = requested in PAGE_META ? requested : "profile";
  const [page, setPage] = useState(validPage === "advisor" && !ready ? "profile" : validPage);
  const [collapsed, setCollapsed] = usePersistentState("curricupath-sidebar-collapsed", false);
  const [theme, setTheme] = usePersistentString("curricupath-theme", "dark");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [rankingMode, setRankingMode] = usePersistentString("curricupath-ranking-mode", "prototype");
  const [system, setSystem] = usePersistentString("curricupath-system", "curricupath");
  const [sessionId, setSessionId] = useState(() => sessionStorage.getItem("curricupath-session"));
  const [messages, setMessages] = useState(INITIAL_MESSAGES);
  const [summary, setSummary] = useState(null);
  const [modules, setModules] = useState([]);
  const [modulesLoading, setModulesLoading] = useState(false);
  const [courses, setCourses] = useState([]);
  const [coursesLoading, setCoursesLoading] = useState(false);
  const [careers, setCareers] = useState([]);
  const [careersLoading, setCareersLoading] = useState(false);
  const [evidence, setEvidence] = useState(null);
  const [evidenceLoading, setEvidenceLoading] = useState(false);
  const [evidenceViewed, setEvidenceViewed] = useState(() => localStorage.getItem("curricupath-evidence-viewed") === "true");
  const [detail, setDetail] = useState(null);

  useEffect(() => {
    getJson("/catalogue/summary").then(data => {
      setSummary(data);
      const modes = data.available_public_course_ranking_modes || ["deterministic"];
      if (!modes.includes(rankingMode)) setRankingMode("deterministic");
    }).catch(() => setSummary(null));
  }, []);

  useEffect(() => {
    localStorage.setItem("curricupath-programme", profile.programme);
    localStorage.setItem("curricupath-completed", JSON.stringify(profile.completed));
    if (!profile.programme) {
      setModules([]);
      return;
    }
    setModulesLoading(true);
    getJson(`/programmes/${profile.programme}/modules`)
      .then(setModules)
      .finally(() => setModulesLoading(false));
  }, [profile.programme]);

  useEffect(() => {
    if (page === "library" && !courses.length && !coursesLoading) {
      setCoursesLoading(true);
      getJson("/courses?limit=100").then(setCourses).finally(() => setCoursesLoading(false));
    }
    if (page === "careers" && !careers.length && !careersLoading) {
      setCareersLoading(true);
      getJson("/career-paths").then(setCareers).finally(() => setCareersLoading(false));
    }
    if (page === "evidence" && !evidence && !evidenceLoading) {
      setEvidenceViewed(true);
      localStorage.setItem("curricupath-evidence-viewed", "true");
      setEvidenceLoading(true);
      getJson("/evidence").then(setEvidence).finally(() => setEvidenceLoading(false));
    }
  }, [page]);

  const navigate = destination => {
    const target = destination === "advisor" && !ready ? "profile" : destination;
    setPage(target);
    window.location.hash = target;
    setMobileOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const saveProfile = () => {
    setSavedProgramme(profile.programme);
    navigate("advisor");
  };

  const resetSession = async () => {
    if (sessionId) await fetch(`/advisor/sessions/${sessionId}`, { method: "DELETE" });
    sessionStorage.removeItem("curricupath-session");
    setSessionId(null);
    setMessages(INITIAL_MESSAGES);
  };

  const openModule = async code => setDetail({ type: "module", data: await getJson(`/modules/${code}`) });
  const openCourse = async id => setDetail({ type: "course", data: await getJson(`/courses/${id}`) });

  return (
    <div className={`app-shell ${collapsed ? "sidebar-collapsed" : ""}`} data-theme={theme === "light" ? "light" : "dark"}>
      <Sidebar page={page} collapsed={collapsed} mobileOpen={mobileOpen} ready={ready} summary={summary} onNavigate={navigate} onToggle={() => setCollapsed(value => !value)} onClose={() => setMobileOpen(false)} />
      <main className="main-content">
        <PageHeader page={page} onMenu={() => setMobileOpen(true)} onReset={resetSession} theme={theme} onThemeChange={setTheme} />
        {page === "profile" && <ProfilePage profile={profile} setProfile={setProfile} modules={modules} loading={modulesLoading} onSave={saveProfile} />}
        {page === "advisor" && ready && <AdvisorPage profile={profile} rankingMode={rankingMode} setRankingMode={setRankingMode} system={system} setSystem={setSystem} handbookRagDemoEnabled={Boolean(summary?.handbook_rag_demo_enabled)} sessionId={sessionId} setSessionId={setSessionId} messages={messages} setMessages={setMessages} onEditProfile={() => navigate("profile")} onOpenModule={openModule} />}
        {page === "library" && <LibraryPage courses={courses} loading={coursesLoading} onOpen={openCourse} />}
        {page === "careers" && <CareersPage careers={careers} loading={careersLoading} onOpenCourse={openCourse} />}
        {page === "journey" && <JourneyPage modules={modules} profile={profile} />}
        {page === "achievements" && <AchievementsPage profile={profile} modules={modules} ready={ready} evidenceViewed={evidenceViewed} />}
        {page === "evidence" && <EvidencePage evidence={evidence} loading={evidenceLoading} />}
        <footer>CurricuPath prototype | Session data stays on this device | Source-based curriculum decisions</footer>
      </main>
      <DetailModal detail={detail} onClose={() => setDetail(null)} />
    </div>
  );
}
