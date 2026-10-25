import { ScenarioStudio } from "./ScenarioStudio";
import { ChapterKicker } from "./AtlasArtwork";
import React, { lazy, Suspense, useEffect, useState } from "react";
import { Search, Route, ChevronRight, RotateCcw, Focus } from "lucide-react";

import {
  selectedCodes,
  dependencyClosure,
  graphForView,
  moduleConnections,
} from "../planModel.mjs";
import { getJson, AsyncPanel, downloadText, CopyButton } from "./shared";
import { moduleState, planText } from "../workspaceModel.mjs";
import { GraphicsBoundary } from "../GraphicsBoundary";
const CurriculumMap = lazy(() =>
  import("../CurriculumMap").then((m) => ({ default: m.CurriculumMap })),
);
const programmeName = (code) =>
  ({ EFA03: "Electrical Engineering", EFA04: "Information Engineering" })[
    code
  ] || "Your degree, your direction";
export function PlanPage({
  capabilities,
  profile,
  modules,
  loading,
  error,
  onRetry,
  tab,
  setTab,
  options,
  onOptions,
  selected,
  highlight,
  onOpenModule,
  onProfile,
  onSources,
  listOptions,
  onListOptions,
  reducedMotion,graphicsUnavailable,
}) {
  const mode =
    options.mode || (selectedCodes(profile).size ? "study" : "dependencies");
  const [graph, setGraph] = useState(null);
  const [graphError, setGraphError] = useState("");
  const [retry, setRetry] = useState(0);
  const [resetKey, setResetKey] = useState(0);
  const [showLabels, setShowLabels] = useState(false);
  const [spatial,setSpatial]=useState(false);
  const connections = moduleConnections(graph, selected);
  useEffect(() => {
    let alive = true;
    setGraph(null);
    setGraphError("");
    if (profile.programme)
      getJson(`/programmes/${profile.programme}/graph`)
        .then((data) => {
          if (alive) setGraph(data);
        })
        .catch(() => {
          if (alive)
            setGraphError(
              "The curriculum map could not be loaded. Your module list is still available.",
            );
        });
    return () => {
      alive = false;
    };
  }, [profile.programme, retry]);
  const seeds = selected ? [selected] : highlight;
  const focused = options.focus && Boolean(seeds.length);
  const chain = graph && focused ? dependencyClosure(graph, seeds) : null;
  const displayedGraph =
    graph &&
    graphForView(
      graph,
      profile,
      mode,
      selected,
      highlight,
      options.year,
      focused,
    );
  const query = listOptions.query;
  const allModules = listOptions.all;
  const filtered = modules.filter(
    (m) =>
      (!options.year || Number(m.year_of_study) === options.year) &&
      (!chain || chain.has(m.course_code)) &&
      (listOptions.status === "all" ||
        moduleState(profile, m.course_code) === listOptions.status) &&
      `${m.course_code} ${m.course_name}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  const visible =
    tab === "timeline" && !allModules
      ? filtered.filter((m) =>
          [
            ...profile.completed,
            ...profile.current,
            ...profile.planned,
            ...(profile.repeating || []),
          ].includes(m.course_code),
        )
      : filtered;
  const years = [...new Set(visible.map((m) => m.year_of_study))].sort();
  const status = (code) =>
    profile.completed.includes(code)
      ? "Completed"
      : profile.current.includes(code)
        ? "Current"
        : profile.planned.includes(code)
          ? "Planned"
          : profile.repeating?.includes(code)
            ? "Repeating"
            : profile.historyConfirmed ? "Not completed" : "Unknown";
  return (
    <div className="plan-page page-content atlas-plan">
      <div className="view-heading">
        <div>
          <ChapterKicker index="01">Your curriculum, connected</ChapterKicker>
          <h1>Your degree, in perspective.</h1>
          <p>
            {programmeName(profile.programme)}
            {profile.programme && ` · ${profile.programme}`}
          </p>
        </div>
        <div role="group" className="segmented" aria-label="Plan view">
          {["map", "timeline"].map((t) => (
            <button
              key={t}
              aria-pressed={tab === t}
              className={tab === t ? "active" : ""}
              onClick={() => setTab(t)}
            >
              {t === "map" ? "Map" : "Timeline"}
            </button>
          ))}
        </div>
      </div>
      {profile.programme && <ScenarioStudio profile={profile} modules={modules} onOpenModule={onOpenModule} onSources={onSources} targetCode={selected} />}
      {!profile.programme ? (
        <div className="setup-empty">
          <Route size={36} />
          <h2>A path begins with a programme.</h2>
          <p>
            Choose your degree to see its modules and recorded dependencies.
          </p>
          <button className="primary-button" onClick={onProfile}>
            Set up your degree profile
          </button>
        </div>
      ) : (
        <>
          <details className="plan-check-coverage"><summary>What this plan can check</summary><p>Recorded sources, programme membership, prerequisites, corequisites and exclusions support the academic checks. Terms in your draft remain personal intentions.</p><p>{capabilities?capabilities.timetable_clash_check_enabled?'Recorded timetable-clash rules are enabled. They do not establish complete offering or timetable coverage.':'Timetable-clash checking is not enabled on this server. An academic result does not mean a clash-free timetable.':'Check availability has not been supplied by the server. Do not infer timetable coverage.'}</p>{capabilities?.school_grid_requirements_enabled && <p>Additional recorded school requirements are included. Source evidence remains inspectable.</p>}</details>
          <div role="group"
            className="plan-record-summary"
            aria-label="Your declared module selections"
          >
            {[
              ["completed", "Completed"],
              ["current", "Current"],
              ["planned", "Planned"],
              ["repeating", "Repeating"],
            ].map(([key, label]) => (
              <div key={key}>
                <strong>
                  {loading || error
                    ? "—"
                    : !profile.historyConfirmed && !(profile[key] || []).length ? "Unknown" : modules.filter((module) =>
                        (profile[key] || []).includes(module.course_code),
                      ).length}
                </strong>
                <span>{label}</span>
              </div>
            ))}
            <p>
              Declared module history
              <br />
              Planning does not confirm eligibility
            </p>
          </div>
          <div className="plan-view-controls">
            <label>
              Year of study
              <select
                aria-label="Year of study"
                value={options.year || "all"}
                onChange={(event) =>
                  onOptions({
                    year:
                      event.target.value === "all"
                        ? null
                        : Number(event.target.value),
                    focus: false,
                  })
                }
              >
                <option value="all">All years</option>
                {[
                  ...new Set(
                    modules.map((module) => Number(module.year_of_study)),
                  ),
                ]
                  .sort((a, b) => a - b)
                  .map((year) => (
                    <option key={year} value={year}>
                      Year {year}
                    </option>
                  ))}
              </select>
            </label>
            <button
              className={`secondary-button ${focused ? "is-focused" : ""}`}
              aria-pressed={focused}
              disabled={!graph || !seeds.length}
              onClick={() => onOptions({ focus: !focused, year: null })}
            >
              <Focus size={16} />
              {focused ? "Show surrounding modules" : "Focus on this chain"}
            </button>
            <button
              className="text-button"
              onClick={() => {
                onOptions({ year: null, focus: false });
                setResetKey((key) => key + 1);
              }}
            >
              <RotateCcw size={15} />
              Reset view
            </button>
          </div>
          <p className="plan-view-caption" role="status">
            {focused
              ? `Following ${selected || "the advisor’s modules"} and their recorded requirements.`
              : options.year
                ? `Year ${options.year} modules. The map also keeps their recorded requirements from earlier years.`
                : "Select a module in the map or list to inspect its recorded requirements."}
          </p>
          {tab === "map" && <div className="workspace-toolbar"><span>Accessible module list is always available below.</span><button className="secondary-button" disabled={graphicsUnavailable} aria-pressed={spatial} onClick={()=>setSpatial(!spatial)}>{spatial?"Use the reading view":"Open optional 3D view"}</button></div>}
          {tab === "map" && spatial && !graphicsUnavailable && (
            <section className="plan-map-surface">
              <div className="map-toolbar">
                <div role="group" className="segmented" aria-label="Map mode">
                  <button
                    className={mode === "study" ? "active" : ""}
                    aria-pressed={mode === "study"}
                    onClick={() => onOptions({ mode: "study" })}
                  >
                    Study plan
                  </button>
                  <button
                    className={mode === "dependencies" ? "active" : ""}
                    aria-pressed={mode === "dependencies"}
                    onClick={() => onOptions({ mode: "dependencies" })}
                  >
                    Dependencies
                  </button>
                </div>
                <label className="map-label-control">
                  <input
                    type="checkbox"
                    checked={showLabels}
                    onChange={(event) => setShowLabels(event.target.checked)}
                  />
                  Label every module
                </label>
                <span>
                  {displayedGraph
                    ? `${displayedGraph.nodes.length} modules in view · Drag to orbit`
                    : "Loading recorded dependencies…"}
                </span>
              </div>
              {graphError ? (
                <div className="map-loading" role="alert">
                  <p>{graphError}</p>
                  <button
                    className="secondary-button"
                    onClick={() => setRetry((value) => value + 1)}
                  >
                    Try again
                  </button>
                </div>
              ) : (
                <>
                  <GraphicsBoundary
                    fallback={
                      <div className="map-loading">
                        <h2>The map is unavailable.</h2>
                        <p>
                          Your modules and recorded rules are still available in
                          the list below. Reload the page to try the 3D view
                          again.
                        </p>
                      </div>
                    }
                  >
                    <Suspense
                      fallback={
                        <div className="map-loading" role="status">
                          Opening your curriculum map…
                        </div>
                      }
                    >
                      <CurriculumMap
                        programme={profile.programme}
                        profile={profile}
                        selected={selected}
                        highlight={highlight}
                        onOpenModule={onOpenModule}
                        mode={mode}
                        data={graph}
                        year={options.year}
                        focus={focused}
                        resetKey={resetKey}
                        reducedMotion={reducedMotion}
                        showLabels={showLabels}
                      />
                    </Suspense>
                  </GraphicsBoundary>
                </>
              )}
            </section>
          )}
          {tab === "map" && selected && graph && (
            <section
              className="map-selection-card"
              aria-label="Selected module connections"
            >
              <div className="map-selection-heading">
                <div>
                  <span className="eyebrow">Selected connection</span>
                  <h2>{selected}</h2>
                  <p>
                    {graph.nodes.find((node) => node.course_code === selected)
                      ?.course_name || "Recorded curriculum reference"}
                  </p>
                </div>
                <button
                  className="secondary-button"
                  onClick={() => onOpenModule(selected)}
                >
                  Inspect module
                </button>
              </div>
              <p className="helper-text">
                Connections describe recorded rules. Your eligibility is checked
                separately.
              </p>
              {connections.length ? (
                <div className="map-connection-list">
                  {connections.map((edge, index) => (
                    <button
                      key={`${edge.rule_id}-${index}`}
                      onClick={() => onOpenModule(edge.code)}
                    >
                      <span className="eyebrow">
                        {edge.incoming
                          ? "Required by this module"
                          : "Connected next module"}{" "}
                        · {edge.kind}
                      </span>
                      <strong>
                        {edge.code} · {edge.name}
                      </strong>
                      <small>{edge.rule_id}</small>
                    </button>
                  ))}
                </div>
              ) : (
                <p>
                  No direct prerequisite or corequisite connection is recorded
                  in this graph.
                </p>
              )}
            </section>
          )}
          <section className="module-ledger">
            <div className="ledger-heading">
              <div>
                <span className="eyebrow">
                  {tab === "map"
                    ? "EVERY MODULE, WITHIN REACH"
                    : "YOUR STUDY TIMELINE"}
                </span>
                <h2>
                  {tab === "map"
                    ? "Find your next connection."
                    : "One year at a time."}
                </h2>
              </div>
              <label className="inline-search">
                <Search size={17} />
                <input
                  aria-label="Search curriculum modules"
                  placeholder="Find a module…"
                  value={query}
                  onChange={(e) =>
                    onListOptions({ query: e.target.value }, true)
                  }
                />
              </label>
            </div>
            <div className="ledger-tools">
              <label>
                Module status
                <select
                  aria-label="Filter module status"
                  value={listOptions.status}
                  onChange={(e) => onListOptions({ status: e.target.value })}
                >
                  {[
                    "all",
                    "completed",
                    "current",
                    "planned",
                    "repeating",
                    "not_taken",
                  ].map((value) => (
                    <option key={value} value={value}>
                      {value === "all"
                        ? "All statuses"
                        : value.replace("_", " ")}
                    </option>
                  ))}
                </select>
              </label>
              <button
                className="secondary-button"
                onClick={() =>
                  downloadText(
                    `curricupath-${profile.programme}-plan.txt`,
                    planText(profile, modules),
                  )
                }
              >
                Export declared plan
              </button>
              <button
                className="text-button"
                onClick={() =>
                  onListOptions({ query: "", status: "all", all: false })
                }
              >
                Clear list filters
              </button>
              <span role="status">
                {loading ? "Loading your module list…" : `${visible.length} ${visible.length === 1 ? "module" : "modules"} in this list`}
              </span>
            </div>
            <details className="plan-export-preview">
              <summary>Preview or copy your declared plan</summary>
              <CopyButton
                label="Copy declared plan"
                text={planText(profile, modules)}
              />
              <pre>{planText(profile, modules)}</pre>
            </details>
            {tab === "timeline" && (
              <label className="show-all">
                <input
                  type="checkbox"
                  checked={allModules}
                  onChange={(e) => onListOptions({ all: e.target.checked })}
                />
                Show all curriculum modules
              </label>
            )}
            {loading && <p role="status">Loading your curriculum…</p>}
            {error && (
              <AsyncPanel
                title="Your curriculum could not be loaded"
                error={error}
                onRetry={onRetry}
              />
            )}
            {!loading && !error && !visible.length && (
              <p className="empty-panel">
                {tab === "timeline" && !allModules
                  ? "Your timeline is ready for a first step. Add a module to your plan, or show all curriculum modules."
                  : "No modules match your search."}
              </p>
            )}
            {years.map((year) => (
              <div className="ledger-year" key={year}>
                <div className="year-marker">
                  YEAR <strong>{year}</strong>
                </div>
                <div className="ledger-modules">
                  {visible
                    .filter((m) => m.year_of_study === year)
                    .map((m) => (
                      <button
                        key={m.course_code}
                        className={`module-list-row ${selected === m.course_code || highlight.includes(m.course_code) ? "selected" : ""}`}
                        aria-current={
                          selected === m.course_code ? "true" : undefined
                        }
                        onClick={() => onOpenModule(m.course_code)}
                      >
                        <span className="module-code">{m.course_code}</span>
                        <strong>{m.course_name}</strong>
                        <span
                          className={`module-status status-${status(m.course_code).toLowerCase().replace(" ", "-")}`}
                        >
                          {status(m.course_code)}
                        </span>
                        <ChevronRight size={16} />
                      </button>
                    ))}
                </div>
              </div>
            ))}
          </section>
        </>
      )}
    </div>
  );
}
