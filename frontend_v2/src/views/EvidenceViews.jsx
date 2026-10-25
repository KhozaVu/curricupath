import {EvidenceSearch} from "./EvidenceSearch";
import {sourceLocation,resolveSourceReference} from "../collectionModel.mjs";
import sourceManifest from "../sourceManifest.json" with {type:"json"};
import { EvidencePanel } from "./EvidencePanel";
import { RequirementTree } from "./RequirementTree";
import { ExternalLink, Search, X, ShieldCheck } from "lucide-react";
import React, { useState } from "react";
import { titleCase, Stars, StatusPill, AsyncPanel, usePersistentState } from "./shared";
export function EvidencePage({ evidence, loading, error, onRetry,onInspect }) {
  const [query, setQuery] = usePersistentState("curricupath-evidence-query-v1","");
  const [view, setView] = usePersistentState("curricupath-evidence-view-v1","sources");
  const [status, setStatus] = usePersistentState("curricupath-evidence-status-v1","all");
  if (error)
    return (
      <AsyncPanel
        title="The evidence register is unavailable"
        error={error}
        onRetry={onRetry}
      />
    );
  if (loading)
    return (
      <div className="page-content">
        <AsyncPanel loading title="Loading the audit trail…" />
      </div>
    );
  if (!evidence)
    return (
      <div className="page-content">
        <div className="empty-panel">
          Evidence data is currently unavailable.
        </div>
      </div>
    );
  const verifiedReferences = evidence.external_references.filter(
    (item) => item.status === "verified",
  ).length;
  const metrics = [
    [evidence.summary.cbo_covered_modules, "modules with course information"],
    [evidence.summary.missing_cbos, "CBOs still needed"],
    [verifiedReferences, "verified external prerequisites"],
    [evidence.summary.rules, "auditable rules"],
  ];
  const sources = evidence.sources.filter(
    (source) =>
      (status === "all" || source.verification_status === status) &&
      [
        source.title,
        source.source_id,
        source.authority,
        source.publisher,
        source.locator,
      ]
        .join(" ")
        .toLowerCase()
        .includes(query.trim().toLowerCase()),
  );
  return (
    <div className="page-content evidence-page">
      <EvidenceSearch onInspect={onInspect} index={evidence.index} sources={evidence.sources}/>
      <p className="evidence-intro">
        Curriculum rules and recommendation evidence remain inspectable.
        Incomplete records are identified rather than silently treated as
        verified.
      </p>
      <div className="evidence-metrics">
        {metrics.map(([value, label]) => (
          <div key={label}>
            <strong>{value}</strong>
            <span>{label}</span>
          </div>
        ))}
      </div>
      <div role="group" className="segmented evidence-tabs" aria-label="Evidence collection">
        {[
          ["sources", "Source register"],
          ["references", "Prerequisite audit"],
          ["gaps", "Coverage gaps"],
        ].map(([key, label]) => (
          <button
            key={key}
            aria-pressed={view === key}
            className={view === key ? "active" : ""}
            onClick={() => {
              setView(key);
              setQuery("");
            }}
          >
            {label}
          </button>
        ))}
      </div>
      {view !== "sources" && (
        <label className="inline-search">
          <Search size={17} />
          <input
            aria-label="Search audit records"
            placeholder="Module, rule ID or recorded status…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
      )}
      {view === "sources" && (
        <section className="evidence-table-card">
          <div className="card-heading">
            <span>Source register</span>
            <h2>Verified and reviewed evidence</h2>
          </div>
          <div className="evidence-filters">
            <label className="inline-search">
              <Search size={17} />
              <input
                aria-label="Search evidence sources"
                placeholder="Document, authority or source ID…"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
              {query && (
                <button
                  className="icon-button"
                  aria-label="Clear evidence search"
                  onClick={() => setQuery("")}
                >
                  <X size={16} />
                </button>
              )}
            </label>
            <label>
              Verification
              <select
                aria-label="Filter source verification"
                value={status}
                onChange={(event) => setStatus(event.target.value)}
              >
                <option value="all">All statuses</option>
                {[
                  ...new Set(
                    evidence.sources.map(
                      (source) => source.verification_status,
                    ),
                  ),
                ].map((value) => (
                  <option key={value} value={value}>
                    {titleCase(value)}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <p className="history-filter-summary" role="status">
            {sources.length} of {evidence.sources.length} source documents
          </p>
          <div className="evidence-table" role="table">
            <div className="evidence-row evidence-head" role="row">
              <span role="columnheader">Source document</span>
              <span role="columnheader">Locator</span>
              <span role="columnheader">Reviewed</span>
              <span role="columnheader">Status</span>
            </div>
            {sources.map((source) => (
              <div className="evidence-row" role="row" key={source.source_id}>
                <div role="cell" data-label="Source document">
                  <strong>{source.title}</strong>
                  <small>{source.authority || source.publisher}</small>
                  <small className="source-identifier">
                    {source.source_id}
                  </small>
                </div>
                <span role="cell" data-label="Locator">
                  {source.locator || "Location not supplied"}{sourceLocation(resolveSourceReference(source,sourceManifest[source.source_id])) && <a className="text-button" href={sourceLocation(resolveSourceReference(source,sourceManifest[source.source_id]))} target="_blank" rel="noreferrer">Open recorded document</a>}
                </span>
                <span role="cell" data-label="Reviewed">
                  {source.review_date || "Not recorded"}
                </span>
                <span role="cell" data-label="Status">
                  <StatusPill
                    tone={
                      source.verification_status === "verified"
                        ? "green"
                        : "gold"
                    }
                  >
                    {titleCase(source.verification_status)}
                  </StatusPill>
                </span>
              </div>
            ))}
          </div>
          {!sources.length && (
            <p className="empty-panel">
              No source documents match. Try another status or search.
            </p>
          )}
        </section>
      )}
      <div className="evidence-columns">
        {view === "references" && (
          <section className="evidence-list-card">
            <div className="card-heading">
              <span>Prerequisite audit</span>
              <h2>External references</h2>
              <p role="status">
                {
                  evidence.external_references.filter((record) =>
                    Object.values(record)
                      .join(" ")
                      .toLowerCase()
                      .includes(query.toLowerCase()),
                  ).length
                }{" "}
                matching records
              </p>
            </div>
            {evidence.external_references
              .filter((record) =>
                Object.values(record)
                  .join(" ")
                  .toLowerCase()
                  .includes(query.toLowerCase()),
              )
              .map((record) => (
                <div
                  className="audit-row"
                  key={`${record.reference}-${record.rule_id}`}
                >
                  <strong>{record.reference}</strong>
                  <small>{record.rule_id}</small>
                  <StatusPill
                    tone={record.status === "verified" ? "green" : "gold"}
                  >
                    {titleCase(record.status)}
                  </StatusPill>
                  <p>{record.interpretation}</p>
                </div>
              ))}
          </section>
        )}
        {view === "gaps" && (
          <section className="evidence-list-card">
            <div className="card-heading">
              <span>Coverage gaps</span>
              <h2>Missing CBOs</h2>
              <p role="status">
                {
                  evidence.missing_cbos.filter((record) =>
                    Object.values(record)
                      .join(" ")
                      .toLowerCase()
                      .includes(query.toLowerCase()),
                  ).length
                }{" "}
                matching records
              </p>
            </div>
            {evidence.missing_cbos
              .filter((record) =>
                Object.values(record)
                  .join(" ")
                  .toLowerCase()
                  .includes(query.toLowerCase()),
              )
              .map((record) => (
                <div className="audit-row" key={record.course_code}>
                  <strong>
                    {record.course_code} | {record.course_name}
                  </strong>
                  <small>{titleCase(record.status)}</small>
                  <p>{record.notes}</p>
                </div>
              ))}
          </section>
        )}
      </div>
    </div>
  );
}
function Fact({ label, children }) {
  return (
    <div className="fact">
      <dt>{label}</dt>
      <dd>{children || "Not stated"}</dd>
    </div>
  );
}
export function ModuleDetail({ item }) {
  const info = item.course_information;
  return (
    <>
      <EvidencePanel data={item} compact />
      <StatusPill>{item.course_code}</StatusPill>
      <h2>{item.course_name}</h2>
      <p className="modal-lead">
        {item.nqf_credits} NQF credits | Level {item.nqf_level}
      </p>
      <div className="detail-section">
        <h3>Programme membership</h3>
        {item.memberships.map((row) => (
          <p key={`${row.programme_code}-${row.year_of_study}`}>
            {row.programme_code}, Year {row.year_of_study}:{" "}
            {titleCase(row.requirement_type)}
          </p>
        ))}
      </div>
      <div className="detail-section">
        <h3>Requirements</h3>
        {item.rules.length ? (
          item.rules.map((rule) => (
            <div className="rule-summary" key={rule.rule_id}>
              <b>{titleCase(rule.rule_type)}</b>
              <RequirementTree rule={rule} />
              <small>
                {rule.source_id}
                {rule.handbook_page
                  ? `, handbook page ${rule.handbook_page}`
                  : ""}
              </small>
            </div>
          ))
        ) : (
          <p>
            No direct prerequisite, corequisite, or exclusion rule is recorded.
          </p>
        )}
      </div>
      <div className="detail-section">
        <h3>Course information</h3>
        {!info.cbo_available ? (
          <p>{info.missing_reason}</p>
        ) : (
          <dl>
            <Fact label="Academic staff">{info.lecturer}</Fact>
            <Fact label="Coordinator">{info.course_coordinator}</Fact>
            <Fact label="Evidence year">{info.academic_year}</Fact>
            <Fact label="Total notional hours">
              {info.hours.notional_hours_total} hours
            </Fact>
            <Fact label="Weekly guidance">
              {info.hours.weekly_workload_guidance}
            </Fact>
            <Fact label="Contact pattern">{info.hours.contact_pattern}</Fact>
            <Fact label="Scope">{info.scope}</Fact>
            <Fact label="Prescribed material">{info.prescribed_materials}</Fact>
            <Fact label="Additional material">{info.additional_materials}</Fact>
          </dl>
        )}
      </div>
    </>
  );
}
