import { RequirementTree } from "./RequirementTree";
import { EvidencePanel } from "./EvidencePanel";
import React, { useEffect, useRef, useState } from "react";
import {
  ArrowUpRight,
  Search,
  Check,
  CircleUserRound,
  Sun,
  Moon,
  X,
  BookOpen,
  Compass,
  ChevronRight,
  GraduationCap,
  SlidersHorizontal,
  PanelLeftClose,
  PanelLeftOpen,
  CircleHelp,
} from "lucide-react";
import { searchEntries } from "../experienceModel.mjs";
import { AsyncPanel, CopyButton } from "./shared";
import { answerText } from "../workspaceModel.mjs";
import { LiquidMark } from "../Atmosphere";
import { useDialogFocus, useOverlayClose } from "../interaction";
const programmeName = (code) =>
  ({ EFA03: "Electrical Engineering", EFA04: "Information Engineering" })[
    code
  ] || "Your degree, your direction";
export function NavigationRail({
  pages,
  page,
  onNavigate,
  onProfile,
  profile,
  ready,
  busy,
  inert,
  reducedMotion,
  collapsed,
  onToggle,
}) {
  return (
    <aside className="navigation-rail glass-control" inert={inert}>
      <button
        className="rail-brand"
        onClick={() => onNavigate("home")}
        aria-label="CurricuPath home"
      >
        <LiquidMark
          reducedMotion={reducedMotion}
          size={35}
          state={busy ? "thinking" : "idle"}
        />
        <span>
          CurricuPath<small>A clearer way forward</small>
        </span>
      </button>
      <div className="rail-section-label">YOUR SPACE</div>
      <nav
        id="navigation-items"
        aria-label="Main navigation"
        style={{
          "--active-index": Math.max(
            0,
            pages.findIndex(([id]) => id === page),
          ),
        }}
      >
        {pages.map(([id, Icon, label]) => (
          <a
            href={`#${id}`}
            key={id}
            className={`rail-item ${page === id ? "active" : ""}`}
            aria-label={label}
            aria-current={page === id ? "page" : undefined}
            onClick={event=>{if(event.ctrlKey || event.metaKey || event.shiftKey || event.altKey)return;event.preventDefault();onNavigate(id);}}
          >
            <Icon size={20} aria-hidden="true" />
            <span className="rail-label">{label}</span>
            <span className="rail-tooltip" aria-hidden="true">{label}</span>
            {page === id && <i />}
          </a>
        ))}
      </nav>
      <div className="rail-bottom">
      <button className="rail-toggle" aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} title={collapsed ? "Expand sidebar" : "Collapse sidebar"} aria-expanded={!collapsed} aria-controls="navigation-items" onClick={onToggle}>
        {collapsed ? <PanelLeftOpen size={20} /> : <PanelLeftClose size={20} />}
      </button>
        <button className="rail-profile" onClick={onProfile} aria-label={ready ? `${profile.programme} student · Your degree profile` : "Set up your degree profile"}>
          <span className="profile-avatar">
            <GraduationCap size={20} />
          </span>
          <span>
            {ready ? profile.programme + " student" : "Make it yours"}
            <small>
              {ready ? "Your degree profile" : "Set up your profile"}
            </small>
          </span>
          <ChevronRight size={15} />
          <span className="rail-tooltip" aria-hidden="true">Degree profile</span>
        </button>
      </div>
    </aside>
  );
}
export function TopBar({
  page,
  theme,
  onTheme,
  onSearch,
  onProfile,
  onDisplay,
  onHelp,
  profile,
}) {
  return (
    <header className="top-bar">
      <div className="breadcrumb">
        Your space <span>/</span>
        <strong>{page[0].toUpperCase() + page.slice(1)}</strong>
        {profile?.programme && <small className="breadcrumb-context">{profile.programme} · {programmeName(profile.programme)}</small>}
      </div>
      <div className="top-actions">
        <button
          className="global-search-trigger"
          aria-label="Search your space"
          onClick={onSearch}
        >
          <Search size={16} />
          <span>Search your space</span><kbd>⌘ / Ctrl K</kbd>
        </button>
        <button
          className="icon-button"
          onClick={onTheme}
          aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
        >
          {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
        </button>
        <button
          className="icon-button"
          aria-label="Appearance and accessibility"
          onClick={onDisplay}
        >
          <SlidersHorizontal size={18} />
        </button>
        <button className="icon-button help-trigger" aria-label="How CurricuPath works" onClick={onHelp}><CircleHelp size={19} aria-hidden="true" /></button>
        <button
          className="icon-button top-profile"
          onClick={onProfile}
          aria-label="Open degree profile"
        >
          <CircleUserRound size={22} />
        </button>
      </div>
    </header>
  );
}
export function Drawer({ title, children, onClose, wide = false, backLabel }) {
  const ref = useRef(null);
  const { closing, close } = useOverlayClose(onClose, ref);
  useDialogFocus(ref, close);
  return (
    <div
      className={`drawer-backdrop ${closing ? "is-closing" : ""}`}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) close();
      }}
    >
      <section
        ref={ref}
        className={`drawer ${wide ? "drawer-wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <header className="drawer-header">
          <div>
            <span className="eyebrow">CURRICUPATH</span>
            <h2>{title}</h2>
          </div>
          <button
            className="icon-button"
            aria-label={backLabel || "Close drawer"} title={backLabel || "Close drawer"}
            onClick={close}
          >
            {backLabel ? <ChevronRight className="overlay-return-icon" size={22} aria-hidden="true" /> : <X size={22} aria-hidden="true" />}
          </button>
        </header>
        <div className="drawer-content">{children}</div>
      </section>
    </div>
  );
}
export function GlobalSearch({ modules, onClose, onModule, onAction, loading = {}, errors = {}, onRetry }) {
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef(null);
  const entries = searchEntries(query, modules, []);
  const current = Math.min(active, Math.max(0, entries.length - 1));
  useEffect(() => {
    const frame = requestAnimationFrame(() => inputRef.current?.focus());
    return () => cancelAnimationFrame(frame);
  }, []);
  useEffect(() => { document.getElementById(`space-search-${current}`)?.scrollIntoView({block:"nearest"}); }, [current]);
  const choose = entry => {
    if (!entry) return;
    if (entry.type === "module") onModule(entry.id);
    else onAction(entry.id);
  };
  return <Drawer title="Search your space" onClose={onClose}>
    <label className="explore-search command-input">
      <Search size={20} aria-hidden="true" />
      <input ref={inputRef} aria-label="Global search" role="combobox" aria-autocomplete="list" aria-expanded={entries.length > 0} aria-controls="space-search-list" aria-activedescendant={entries.length ? `space-search-${current}` : undefined}
        name="global-search" autoComplete="off" spellCheck={false} placeholder="Try ELEN 4025, a topic, or motion…" value={query}
        onChange={e=>{setQuery(e.target.value);setActive(0);}}
        onKeyDown={e=>{if (['ArrowDown','ArrowUp'].includes(e.key)) {e.preventDefault();setActive((current + (e.key==='ArrowDown'?1:-1) + entries.length) % (entries.length || 1));} if(e.key==='Enter'){e.preventDefault();choose(entries[current]);}}} />
      {query && <button className="icon-button" aria-label="Clear global search" onClick={()=>{setQuery('');setActive(0);inputRef.current?.focus();}}><X size={17} aria-hidden="true" /></button>}
    </label>
    <p className="command-hint"><kbd>↑</kbd><kbd>↓</kbd> choose · <kbd>Enter</kbd> open · <kbd>Esc</kbd> close</p>
    <span className="visually-hidden" role="status">{entries.length} results</span>
    <div className="search-results command-results" id="space-search-list" role="listbox" aria-label="Search results">
      {entries.map((entry,index)=> {
        const Icon = entry.type === 'module' ? BookOpen : entry.type === 'course' ? Compass : ArrowUpRight;
        const previous = entries[index-1];
        return <React.Fragment key={`${entry.type}-${entry.id}`}>
          {previous?.type !== entry.type && <div className="command-group" role="presentation">{entry.type === 'action' ? 'Your space · actions' : entry.type === 'module' ? 'Wits curriculum modules' : 'Wits modules'}</div>}
          <div id={`space-search-${index}`} role="option" aria-selected={current===index} className={`command-option ${current===index?'is-selected':''}`}>
            <button tabIndex={-1} onClick={()=>choose(entry)} onMouseEnter={()=>setActive(index)}><Icon size={18} aria-hidden="true"/><span><strong>{entry.title}</strong><small>{entry.detail}</small></span><span className="command-kind">{entry.type}</span></button>
          </div>
        </React.Fragment>;
      })}
    </div>
    {!entries.length && <section className="empty-panel"><h3>No matches yet.</h3><p>Try fewer words, a module code, or a module name.</p><button className="secondary-button" onClick={()=>{setQuery('');setActive(0);inputRef.current?.focus();}}>Show space actions</button></section>}
    {["modules"].map(key=>(loading[key] || errors[key]) && <AsyncPanel key={key} loading={loading[key]} title={`${'Curriculum'} search ${errors[key] ? 'is unavailable' : 'is loading…'}`} error={errors[key]} onRetry={()=>onRetry(key)} />)}
  </Drawer>;
}
export function SourceTrail({ data, onRegister }) {
  const rules = data?.rules || [];
  return (
    <div className="source-trail">
      <span className="eyebrow">THE REASON BEHIND THE RESULT</span>
      <EvidencePanel data={data || {}} />
      <CopyButton
        label="Copy source trail"
        text={answerText({ text: data?.source_id || "", data })}
      />
      <h3>{data?.course_code || data?.title || "Recommendation evidence"}</h3>
      {data?.matched_tags?.length > 0 && (
        <p>
          Matches your stated interests:{" "}
          {data.matched_tags.map((t) => t.replaceAll("_", " ")).join(", ")}.
        </p>
      )}
      {data?.score != null && (
        <section className="rule-summary">
          <b>Ranking signals</b>
          <p>
            Score {Number(data.score).toFixed(2)} ·{" "}
            {data.ranking_mode || "recorded ranking"}. This compares
            recommendation relevance; eligibility is checked separately against
            curriculum rules.
          </p>
          {Object.entries(data.score_components || {})
            .filter(
              ([key, value]) =>
                typeof value === "number" && !["raw_score"].includes(key),
            )
            .map(([key, value]) => (
              <p key={key}>
                {key.replaceAll("_", " ")}: {value.toFixed(2)}
              </p>
            ))}
        </section>
      )}
      {rules.map((r) => (
        <section className="rule-summary" key={r.rule_id}>
          <RequirementTree rule={r}/>
        </section>
      ))}
      {data?.rule_trace?.map((r, i) => (
        <p key={i}>
          {r.gate?.replaceAll("_", " ")} · {r.decision}
          {r.rule_ids?.length > 0 && ` · ${r.rule_ids.join(", ")}`}
        </p>
      ))}
      <button className="secondary-button" onClick={onRegister}>
        Open full evidence register <ArrowUpRight size={16} />
      </button>
    </div>
  );
}
