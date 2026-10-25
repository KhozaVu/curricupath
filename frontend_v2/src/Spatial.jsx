/* Compact module inspector. Recorded rules stay visible; supplementary facts are disclosed on demand. */
import React, { useRef } from "react";
import { AsyncPanel } from "./views/shared";
import { useDialogFocus, useOverlayClose } from "./interaction";

/* ------------------------------------------------------------- inspector */

function requirementState(module, programme) {
  const rules = (module?.rules || []).filter(
    (r) => !/^EFA\d+$/.test(r.scope || "") || r.scope === programme,
  );
  const pre = rules.filter((r) => r.rule_type === "prerequisite");
  const co = rules.filter((r) => r.rule_type === "corequisite");
  return { pre, co };
}

export function ModuleInspector({
  module,
  requestedCode,
  loading,
  error,
  onRetry,
  profile,
  onClose,
  onViewEvidence,
  onPlan,
  onMore,
  onAsk,
  inert,
  modal = false,
}) {
  const panelRef = useRef(null);
  const { closing, close } = useOverlayClose(onClose, panelRef);
  useDialogFocus(panelRef, close, { modal, enabled: !inert });

  const { pre, co } = requirementState(module, profile?.programme);
  const code = module?.course_code;
  const completed = profile?.completed.includes(code);
  const current = profile?.current.includes(code);
  const planned = profile?.planned.includes(code);

  return (
    <>
    {modal && <div className="inspector-scrim" aria-hidden="true" />}
    <aside
      ref={panelRef}
      className={`inspector glass-control ${closing ? "is-closing" : ""}`}
      inert={inert}
      role="dialog"
      aria-modal={modal}
      aria-label={module ? `${module.course_code} details` : "Module details"}
    >
      <button
        className="inspector-close"
        onClick={close}
        aria-label="Close module details"
      >
        ×
      </button>

      <header className="inspector-head">
        <span className="code">{module?.course_code || requestedCode || "Module"}</span>
        <h3>
          {module?.course_name || (loading ? "Opening module…" : "Details unavailable")}
        </h3>
      </header>

      <div className="inspector-body">
        {(loading || error) && <AsyncPanel loading={loading} title={error ? "Module details are unavailable" : "Reading the catalogue…"} error={error} onRetry={onRetry} />}

        {!loading && module && (
          <>
            <div className="plan-status">
              {completed
                ? "Completed"
                : current
                  ? "Currently taking"
                  : planned
                    ? "In your plan"
                    : "Not in your plan"}
            </div>
            <p>
              {module.course_information?.scope?.split(";")[0] ||
                "Explore this module’s recorded requirements before deciding where it fits."}
            </p>
            <div className="inspector-row">
              <dt>Must come first</dt>
              {pre.length === 0 && <dd>No prerequisite is recorded.</dd>}
              {pre.map((r) => (
                <dd key={r.rule_id}>{r.plain_language}</dd>
              ))}
            </div>

            {co.length > 0 && (
              <div className="inspector-row">
                <dt>Alongside</dt>
                {co.map((r) => (
                  <dd key={r.rule_id}>{r.plain_language}</dd>
                ))}
              </div>
            )}

            <div className="inspector-row">
              <dt>Evidence</dt>
              {pre.length + co.length === 0 && (
                <dd>No rule recorded for this module.</dd>
              )}
              {[...pre, ...co].map((r) => (
                <dd key={`src-${r.rule_id}`}>
                  {r.rule_id} · {r.source_id}
                  {r.handbook_page ? `, handbook page ${r.handbook_page}` : ""}
                </dd>
              ))}
            </div>

            <button
              className="primary-button"
              disabled={completed || current}
              onClick={() => onPlan(code)}
            >
              {completed
                ? "Already completed"
                : current
                  ? "Currently taking"
                  : planned
                    ? "Remove from plan"
                    : "Add to plan"}
            </button>
            <p className="sm">
              Planning does not confirm registration eligibility. Ask Advisor
              for a checked decision.
            </p>
            <button className="secondary-button inspector-ask" onClick={onAsk}>Ask Advisor about this module <span aria-hidden="true">↗</span></button>
            <details>
              <summary>More details</summary>
              {module.memberships?.map((m) => (
                <p key={`${m.programme_code}-${m.year_of_study}`}>
                  {m.programme_code} · Year {m.year_of_study} ·{" "}
                  {m.requirement_type?.replaceAll("_", " ")}
                </p>
              ))}
              {module.nqf_credits && (
                <p>
                  {module.nqf_credits} NQF credits · Level{" "}
                  {module.nqf_level || "—"}
                </p>
              )}
              <button className="secondary-button" onClick={onMore}>
                Course information
              </button>
            </details>
            <button className="secondary-button" onClick={onViewEvidence}>
              Why this? · Sources
            </button>
          </>
        )}

        {!loading && !module && !error && (
          <p className="sm">That module could not be opened.</p>
        )}
      </div>
    </aside>
    </>
  );
}
