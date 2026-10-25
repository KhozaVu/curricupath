import { safeLocal, safeSession } from "../storageModel.mjs";
import { AcademicContext } from "./AcademicContext";
import { AnswerWorkbench, AnswerLibrary } from "./AnswerWorkbench";
import { contextKey, declarationConflicts } from "../academicWorkspace.mjs";
import { AtlasArtwork, ChapterKicker } from "./AtlasArtwork";
import { answerText } from "../workspaceModel.mjs";
import { recommendationReason } from "../planModel.mjs";
import {
  Bot,
  Check,
  ChevronRight,
  CircleHelp,
  ExternalLink,
  Route,
  Send,
  ShieldAlert,
  ShieldCheck,
  UserRoundSearch,
  XCircle,
} from "lucide-react";
import React from "react";

import { useEffect, useRef, useState } from "react";

import {
  usePersistentState,
  downloadText,
  INITIAL_MESSAGES,
  moduleCodes,
  titleCase,
  getJson,
  StatusPill,
  CopyButton,
} from "./shared";
function ResultModuleCard({ item, onOpen }) {
  const info = item.course_information;
  return (
    <button
      className="chat-result-card"
      onClick={() => onOpen(item.course_code)}
    >
      <span className="result-card-top">
        <StatusPill>{item.course_code}</StatusPill>
        <span className="result-card-status">
          {item.profile_status ? (
            titleCase(item.profile_status)
          ) : (
            <ChevronRight size={16} />
          )}
        </span>
      </span>
      <strong>{item.course_name}</strong>
      <small>
        {item.nqf_credits} credits | NQF level {item.nqf_level}
      </small>
      {info?.cbo_available && (
        <div className="result-facts">
          <span><b>Lecturer</b>{info.lecturer || "Not stated"}</span>
          <span><b>Content</b>{info.scope || "Not stated"}</span>
        </div>
      )}
    </button>
  );
}

function ModuleDetailCard({ item, onOpen }) {
  const info = item.course_information;
  const fact = (label, value) =>
    value ? (
      <div className="fact">
        <dt>{label}</dt>
        <dd>{value}</dd>
      </div>
    ) : null;
  return (
    <section className="module-detail-card">
      <div className="result-card-top">
        <StatusPill>{item.course_code}</StatusPill>
        <small>
          {item.nqf_credits} credits | NQF level {item.nqf_level}
        </small>
      </div>
      <h3>{item.course_name}</h3>
      {item.memberships?.length > 0 && (
        <div className="detail-block">
          <h4>Where it sits in your programme</h4>
          <ul>
            {item.memberships.map((row) => (
              <li key={`${row.programme_code}-${row.year_of_study}`}>
                {row.programme_code}, Year {row.year_of_study}:{" "}
                {titleCase(row.requirement_type)}
                {row.handbook_page ? ` (handbook page ${row.handbook_page})` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="detail-block">
        <h4>Requirements</h4>
        {item.rules?.length ? (
          item.rules.map((rule) => (
            <p key={rule.rule_id} className="rule-line">
              <b>{titleCase(rule.rule_type)}.</b> {rule.plain_language}{" "}
              <small>
                {rule.source_id}
                {rule.handbook_page ? `, handbook page ${rule.handbook_page}` : ""}
              </small>
            </p>
          ))
        ) : (
          <p>No direct prerequisite, corequisite, or exclusion rule is recorded.</p>
        )}
      </div>
      <div className="detail-block">
        <h4>Course information</h4>
        {!info?.cbo_available ? (
          <p>{info?.missing_reason || "No course brief is on record for this module."}</p>
        ) : (
          <dl className="fact-list">
            {fact("Academic staff", info.lecturer)}
            {fact("Coordinator", info.course_coordinator)}
            {fact("Evidence year", info.academic_year)}
            {fact(
              "Notional hours",
              info.hours?.notional_hours_total &&
                `${info.hours.notional_hours_total} hours`,
            )}
            {fact("Weekly guidance", info.hours?.weekly_workload_guidance)}
            {fact("Contact pattern", info.hours?.contact_pattern)}
            {fact("Content", info.scope)}
            {fact("Prescribed material", info.prescribed_materials)}
            {fact("Additional material", info.additional_materials)}
          </dl>
        )}
      </div>
      <button className="text-button" onClick={() => onOpen(item.course_code)}>
        Open full module page <ChevronRight size={14} />
      </button>
    </section>
  );
}

function ProfileCourseGroup({ title, items, onOpenModule }) {
  if (!items?.length) return null;
  return (
    <section className="profile-course-group">
      <h3>
        {title} <span>{items.length}</span>
      </h3>
      {items.map((item) => (
        <ResultModuleCard
          key={item.course_code}
          item={item}
          onOpen={onOpenModule}
        />
      ))}
    </section>
  );
}

function ProgrammeProfileCard({ item }) {
  return (
    <section className="programme-profile-result">
      <div className="result-card-top">
        <StatusPill>{item.programme_code}</StatusPill>
        <small>
          {item.duration_years} years | {titleCase(item.study_mode)}
        </small>
      </div>
      <h3>{item.programme_name}</h3>
      <p>{item.focus}</p>
      <div className="programme-careers">
        <strong>Career opportunities</strong>
        <div className="tag-row">
          {item.career_opportunities.map((career) => (
            <span key={career}>{career}</span>
          ))}
        </div>
      </div>
      {item.source?.url && (
        <a href={item.source.url} target="_blank" rel="noreferrer">
          View official Wits programme page <ExternalLink size={13} />
        </a>
      )}
    </section>
  );
}

function RecommendationCard({
  item,
  isMatch,
  onSelect,
  onOpenModule,
  onOpenCourse,
  onSources,
  onShowInPlan,
  busy,
}) {
  const title = item.title || `${item.course_code} - ${item.course_name}`;
  const unmet = [
    ...(item.eligibility?.requirements?.prerequisites || []),
    ...(item.eligibility?.requirements?.corequisites || []),
  ].filter((requirement) => !requirement.satisfied);
  const metadata = item.provider
    ? `${item.provider} | ${titleCase(item.level)} | ${titleCase(item.workload)} workload`
    : isMatch
      ? "Select this module"
      : `Year ${item.year_of_study} | ${titleCase(item.requirement_type)}`;

  return (
    <article className="chat-result-card">
      <span className="result-card-top">
        <StatusPill tone={item.provider ? "outline" : "blue"}>
          {item.course_code || item.provider}
        </StatusPill>
        {item.score != null && item.matched_tags?.length > 0 && (
          <small>Ranking score {Number(item.score).toFixed(2)}</small>
        )}
      </span>
      <strong>{title}</strong>
      <small>{metadata}</small>
      <span>{recommendationReason(item)}</span>
      {item.score != null && item.matched_tags?.length > 0 && (
        <small>
          Relative ranking, not eligibility confidence. Open “Why this?” for the
          supplied signals.
        </small>
      )}
      <small>
        {item.source_id
          ? "Source recorded"
          : item.eligibility?.assessed
            ? "Checked against recorded rules"
            : "Evidence not supplied"}
      </small>
      {item.matched_tags?.length > 0 && (
        <span className="match-tags">
          Matches: {item.matched_tags.map(titleCase).join(", ")}
        </span>
      )}
      {item.eligibility?.assessed && (
        <span
          className={
            item.eligibility.completed
              ? "eligibility-completed"
              : item.eligibility.eligible
                ? "eligibility-ok"
                : "eligibility-warning"
          }
        >
          {item.eligibility.completed
            ? "Completed"
            : item.eligibility.needs_clarification
              ? "Needs more information"
              : item.eligibility.manual_review_required
                ? "Academic review required"
                : item.eligibility.available_to_take
                  ? "Eligible with your declared history"
                  : "Not currently available"}
        </span>
      )}
      {item.eligibility?.reasons?.length > 0 && <small>{item.eligibility.reasons.slice(0,2).join(" ")}</small>}
      {unmet.length > 0 && (
        <span className="requirements">
          Needs: {unmet.map((item) => item.description).join("; ")}
        </span>
      )}
      <div className="recommendation-actions">
        <button
          className="secondary-button"
          onClick={() =>
            isMatch
              ? onSelect(item.course_code)
              : item.course_code
                ? onOpenModule(item.course_code)
                : onOpenCourse?.(item.course_id)
          }
        >
          {isMatch
            ? "Select module"
            : item.course_code
              ? "View module"
              : "View course"}
          <ChevronRight size={15} />
        </button>
        <button className="text-button" onClick={() => onSources?.(item)}>
          Why this?
        </button>
        {item.course_code && !isMatch && (
          <button
            className="text-button"
            onClick={() => onShowInPlan?.([item.course_code], true)}
          >
            Show in Plan
          </button>
        )}
      </div>
    </article>
  );
}

const GATE_LABELS = {
  source: "Source verified",
  programme: "In your programme",
  prerequisite: "Prerequisites",
  corequisite: "Corequisites",
  exclusion: "Exclusions",
  timetable_clash: "Timetable",
  discretion: "Academic discretion",
};

const BLOCK_PHRASES = {
  prerequisite: ["Prerequisite not met", "Prerequisite status unknown"],
  corequisite: [
    "Corequisite not completed, current or planned",
    "Corequisite status unknown",
  ],
  exclusion: ["Excluded by", "Exclusion status unknown"],
  timetable_clash: ["Timetable clash with", "Possible timetable clash with"],
};

function RequirementModules({ requirements }) {
  const groups = [
    ["Prerequisites (must be completed first)", requirements?.prerequisites],
    ["Corequisites (must be taken with it)", requirements?.corequisites],
  ].filter(([, mods]) => mods?.length);
  if (!groups.length) return null;
  return (
    <div className="requirement-modules">
      {groups.map(([title, rules]) => (
        <div key={title} className="requirement-group">
          <span className="requirement-title">{title}</span>
          <ul className="requirement-list">
            {rules.map((mod) => (
              <li key={mod.code} className={mod.met ? "met" : "unmet"}>
                <span aria-hidden="true">{mod.met ? "✓" : "✗"}</span>
                <code>{mod.code}</code>
                {mod.name && <span>{mod.name}</span>}
                <small>{mod.met ? "done / planned" : "not finished"}</small>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function BlockingModules({ trace, target }) {
  const rows = trace.filter(
    (step) =>
      step.decision !== "eligible" &&
      step.blocking_modules?.length > 0 &&
      !["prerequisite", "corequisite"].includes(step.gate),
  );
  if (!rows.length) return null;
  return (
    <div className="blocking-modules">
      {rows.map((step, index) => {
        const phrases = BLOCK_PHRASES[step.gate] || [
          titleCase(step.gate),
          titleCase(step.gate),
        ];
        const unknown = step.decision === "needs_clarification";
        return (
          <div
            key={`${step.gate}-${index}`}
            className={`blocking-row ${unknown ? "unknown" : "unmet"}`}
          >
            <span className="blocking-label">
              {phrases[unknown ? 1 : 0]}
              {target ? <small> for {target}</small> : null}
            </span>
            <span className="blocking-codes">
              {step.blocking_modules.map((code) => (
                <code key={code}>{code}</code>
              ))}
            </span>
          </div>
        );
      })}
    </div>
  );
}

const DECISIONS = {
  ok: {
    tone: "eligible",
    Icon: ShieldCheck,
    label: "Eligible · recorded requirements met",
    lede: "The evaluated requirements are met for the history you supplied. Inspect the supporting checks and evidence below.",
  },
  completed: {
    tone: "completed",
    Icon: Check,
    label: "Marked complete in your declared history",
    lede: "No eligibility check is needed.",
  },
  not_eligible: {
    tone: "blocked",
    Icon: XCircle,
    label: "Not eligible · a requirement is unmet",
    lede: "The rule that blocks it is named below, with the checks that were run.",
  },
  clarification_required: {
    tone: "asking",
    Icon: CircleHelp,
    label: "Clarification required",
    lede: "A fact is missing that you can supply. Nothing is assumed until you answer.",
  },
  clarification_unresolved: {
    tone: "asking",
    Icon: CircleHelp,
    label: "Clarification still required",
    lede: "Set this module in Profile setup, then ask again.",
  },
  manual_review_required: {
    tone: "human",
    Icon: UserRoundSearch,
    label: "Manual review required",
    lede: "The approved evidence cannot settle this case, so the system will not guess.",
  },
};

/* Academic outcomes must stay visually distinct. See DESIGN.md section 2. */
function DecisionBanner({ data }) {
  const spec = DECISIONS[data.status];
  if (!spec || data.intent !== "eligibility") return null;
  const { Icon } = spec;
  const reasons = (data.reasons || []).filter(Boolean);
  const trace = (data.rule_trace || []).filter((step) => step && step.gate);
  const citations = data.citations || [];

  return (
    <section
      className={`decision-banner tone-${spec.tone}`}
      aria-label="Eligibility decision"
    >
      <div className="decision-head">
        <span className="decision-icon">
          <Icon size={19} aria-hidden="true" />
        </span>
        <div>
          <strong>{spec.label}</strong>
          {data.course_code && (
            <span className="decision-code">{data.course_code}</span>
          )}
          <p>{spec.lede}</p>
        </div>
      </div>

      <RequirementModules
        requirements={
          data.requirement_modules || data.eligibility?.requirement_modules
        }
      />
      <BlockingModules trace={trace} target={data.course_code} />

      {reasons.length > 0 && (
        <ul className="decision-reasons">
          {reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      )}

      {trace.length > 0 && (
        <div className="decision-trace">
          <span className="decision-trace-label">Checks run</span>
          <div className="decision-gates">
            {trace.map((step, index) => (
              <span
                key={`${step.gate}-${index}`}
                className={`gate ${step.decision === "eligible" ? "pass" : "stop"}`}
              >
                {step.decision === "eligible" ? (
                  <Check size={12} aria-hidden="true" />
                ) : (
                  <ShieldAlert size={12} aria-hidden="true" />
                )}
                {GATE_LABELS[step.gate] || titleCase(step.gate)}
                {step.rule_ids?.length > 0 && (
                  <code>{step.rule_ids.join(", ")}</code>
                )}
              </span>
            ))}
          </div>
        </div>
      )}

      {citations.length > 0 && (
        <p className="decision-source">
          Source:{" "}
          {citations
            .map((c) => `${c.source_id}${c.page ? `, page ${c.page}` : ""}`)
            .join(" · ")}
        </p>
      )}

      <p className="decision-foot">
        Decided by curriculum rules, not by the language model.
      </p>
    </section>
  );
}

function ChatMessage({
  message,
  busy,
  onPrompt,
  onOpenModule,
  onOpenCourse,
  onSources,
  onShowInPlan,
  currentContext,
  onEditProfile,
  onSaveAnswer,
}) {
  const data = message.data;
  const records =
    data?.recommendations ||
    data?.modules ||
    data?.module_matches ||
    [];
  const options = data?.clarification_options || [];
  const asking =
    message.role === "assistant" &&
    data &&
    (data.clarification_question || options.length > 0);
  if (asking) {
    const missing = (
      data.unresolved_predicates ||
      data.eligibility?.unresolved_predicates ||
      []
    ).filter(Boolean);
    return (
      <article
        className="message assistant asking"
        data-recorded="true"
        aria-live="polite"
      >
        <span className="avatar">
          <CircleHelp size={17} />
        </span>
        <div className="bubble ask-card">
          <span className="ask-label">CurricuPath needs one answer</span>
          <p className="ask-question">
            {data.clarification_question || message.text}
          </p>
          {data.module_matches?.length > 0 && (
            <div className="ask-options ask-modules">
              {data.module_matches.map((match) => (
                <button
                  key={match.course_code}
                  disabled={busy}
                  onClick={() => onPrompt(match.course_code)}
                >
                  <code>{match.course_code}</code>
                  <span>{match.course_name}</span>
                </button>
              ))}
            </div>
          )}
          {options.length > 0 && (
            <div className="ask-options">
              {options.map((option) => (
                <button
                  key={option}
                  disabled={busy}
                  onClick={() => onPrompt(option)}
                >
                  {option}
                </button>
              ))}
            </div>
          )}
          <small className="ask-hint">
            {options.length > 0 || data.module_matches?.length > 0
              ? "Pick one, or type your own answer below."
              : "Type your answer below."}
          </small>
          {missing.length > 0 && (
            <details className="ask-why">
              <summary>Why am I being asked?</summary>
              <ul>
                {missing.map((item, index) => (
                  <li key={index}>
                    {typeof item === "string" ? item : JSON.stringify(item)}
                  </li>
                ))}
              </ul>
              <button className="text-button" onClick={onEditProfile}>
                Edit my profile instead
              </button>
            </details>
          )}
        </div>
      </article>
    );
  }
  return (
    <article
      className={`message ${message.role}`}
      data-recorded={Boolean(message.data && message.role === "assistant")}
    >
      {message.role === "assistant" && (
        <span className="avatar">
          <Bot size={17} />
        </span>
      )}
      <div className="bubble">
        <strong>
          {message.role === "user"
            ? "You"
            : data?.system === "handbook_rag"
              ? "Handbook RAG (experimental)"
              : "CurricuPath"}
        </strong>
        {data && <DecisionBanner data={data} />}
        {data && <AnswerWorkbench message={message} currentContext={currentContext} onEdit={onEditProfile} onSources={onSources} onShowInPlan={onShowInPlan} onSave={onSaveAnswer} />}
        {data ? <details className="answer-narrative" open={data.intent !== "eligibility"}><summary>Full explanation</summary><p>{message.text}</p></details> : <p>{message.text}</p>}
        {message.role === "assistant" && message.data && (
          <CopyButton text={answerText(message)} />
        )}
        {message.failedPrompt && (
          <button
            className="secondary-button"
            disabled={busy}
            onClick={() => onPrompt(message.failedPrompt,true)}
          >
            Retry question
          </button>
        )}
        {message.suggestions?.length > 0 && (
          <div className="prompt-row">
            {message.suggestions.map((prompt) => (
              <button key={prompt} onClick={() => onPrompt(prompt)}>
                {prompt}
              </button>
            ))}
          </div>
        )}
        {data?.clarification_options?.length > 0 && (
          <div className="prompt-row">
            {data.clarification_options.map((option) => (
              <button key={option} onClick={() => onPrompt(option)}>
                {option}
              </button>
            ))}
          </div>
        )}
        {data?.ranking_mode && (
          <small className="message-note">
            Ranking: {titleCase(data.ranking_mode)}
          </small>
        )}
        {data?.review && (
          <small className="message-note">
            Response check:{" "}
            {data.review.status === "reviewed"
              ? "Independent review passed"
              : data.review.status === "rejected"
                ? "Response blocked by safety checks"
                : data.review.status === "deterministic" ? "Deterministic review recorded" : `Recorded review status: ${data.review.status || "not supplied"}`}
          </small>
        )}
        {data?.preferences_applied && (
          <small className="message-note">
            Preferences: {titleCase(data.preferences_applied.difficulty)}{" "}
            difficulty, {titleCase(data.preferences_applied.workload)} workload
          </small>
        )}
        {data?.system === "handbook_rag" && data.decision && (
          <small className="message-note">
            Baseline decision: {titleCase(data.decision)}
          </small>
        )}
        {data?.citations?.length > 0 && (
          <ul className="citation-list">
            {data.citations.map((citation) => (
              <li key={`${citation.source_id}-${citation.page}`}>
                {citation.source_id} &middot; {citation.page}
              </li>
            ))}
          </ul>
        )}
        {data?.module && (
          <ModuleDetailCard item={data.module} onOpen={onOpenModule} />
        )}
        {data?.programme_profile && (
          <ProgrammeProfileCard item={data.programme_profile} />
        )}
        {data?.credit_summary && (
          <CreditSummary summary={data.credit_summary} />
        )}
        {data?.career_options && (
          <CareerOptions options={data.career_options} />
        )}
        {data?.programme_comparison && (
          <div className="programme-comparison-results">
            {data.programme_comparison.recommended_programme_code && (
              <small className="message-note">
                Closer fit for the stated interest:{" "}
                {data.programme_comparison.recommended_programme_code}
              </small>
            )}
            {data.programme_comparison.profiles.map((profile) => (
              <ProgrammeProfileCard
                key={profile.programme_code}
                item={profile}
              />
            ))}
          </div>
        )}
        {data?.profile_courses && (
          <div className="profile-course-groups">
            <ProfileCourseGroup
              title="Completed modules"
              items={data.profile_courses.completed}
              onOpenModule={onOpenModule}
            />
            <ProfileCourseGroup
              title="Currently taking"
              items={data.profile_courses.current}
              onOpenModule={onOpenModule}
            />
          </div>
        )}
        {records.length > 0 && <h3 className="response-section-title">{data?.recommendations?.length ? "Wits modules matching your interests" : data?.eligibility_summary ? "Eligible Wits modules" : "Recorded module information"}</h3>}
        {records.map((item, index) => (
          <RecommendationCard
            key={item.course_id || `${item.course_code}-${index}`}
            item={item}
            isMatch={Boolean(data?.module_matches)}
            onSelect={onPrompt}
            onOpenModule={onOpenModule}
            onOpenCourse={onOpenCourse}
            onSources={(item) =>
              onSources?.({
                ...item,
                citations: item.citations || data.citations,
                rule_trace: item.rule_trace || data.rule_trace,
              })
            }
            onShowInPlan={onShowInPlan}
          />
        ))}
        {data?.interest_matches?.length > 0 && <section><h3>Interest matches for future planning</h3><p>These match your interests, but do not currently meet all requirements.</p>{data.interest_matches.map(item=><RecommendationCard key={item.course_code} item={item} onOpenModule={onOpenModule} onSources={onSources} onShowInPlan={onShowInPlan}/>)}</section>}
        {data?.unresolved_modules?.length > 0 && <section><h3>Need more information or academic review</h3><p>These modules are not confirmed eligible.</p>{data.unresolved_modules.map(item=><RecommendationCard key={item.course_code} item={item} onOpenModule={onOpenModule} onSources={onSources} onShowInPlan={onShowInPlan}/>)}</section>}
        {data?.other_modules?.length > 0 && <details><summary>Other checked modules ({data.other_modules.length})</summary>{data.other_modules.map(item=><RecommendationCard key={item.course_code} item={item} onOpenModule={onOpenModule} onSources={onSources} onShowInPlan={onShowInPlan}/>)}</details>}
      </div>
    </article>
  );
}

function CreditSummary({ summary }) {
  return (
    <section className="credit-summary">
      <strong>{summary.total_nqf_credits} NQF credits in the catalogue</strong>
      <div>
        {summary.years.map((year) => (
          <span key={year.year_of_study}>
            Year {year.year_of_study}: <b>{year.total_credits}</b> credits
          </span>
        ))}
      </div>
      <small>
        Elective credits use the recorded number of choices required.
      </small>
    </section>
  );
}

function CareerOptions({ options }) {
  return (
    <div className="career-options">
      {options.map((option) => (
        <section className="career-option" key={option.career_tag}>
          <strong>{option.display_name}</strong>
          <p>{option.description}</p>
          {option.supporting_courses.length > 0 && (
            <small>
              Supporting courses: {option.supporting_courses.join(", ")}
            </small>
          )}
        </section>
      ))}
    </div>
  );
}

/* Module codes an advisor response actually refers to. Only codes that came back
   from the API are lit in the world; nothing is inferred from the prose. */
export function namedModules(data) {
  if (!data) return [];
  const codes = new Set();
  const take = (value) => {
    if (typeof value === "string" && /^[A-Z]{4}\d{4}A?$/.test(value))
      codes.add(value);
  };
  take(data.course_code);
  take(data.module?.course_code);
  for (const list of [
    data.recommendations,
    data.modules,
    data.module_matches,
    data.suggestions,
  ]) {
    for (const item of list || []) take(item?.course_code);
  }
  return [...codes];
}

export function AdvisorPage({
  onHighlight,
  onBusy,
  profile,
  rankingMode,
  setRankingMode,
  system,
  setSystem,
  handbookRagDemoEnabled,
  sessionId,
  setSessionId,
  messages,
  setMessages,
  onEditProfile,
  onOpenModule,
  onOpenCourse,
  onSources,
  draft,
  onDraft,
  context,
  processing,
}) {
  const input = draft;
  const setInput = onDraft;
  const sending = processing;
  const [clearing, setClearing] = useState(false);
  const [conversationError, setConversationError] = useState("");
  const inFlight = useRef(false);
  const controller=useRef(null),generation=useRef(0);
  const currentContext=contextKey(profile);
  const [answers,setAnswers]=usePersistentState('curricupath-wits-saved-answers-v2',[]);
  const [saveNotice,setSaveNotice]=useState('');
  const [confirmClear,setConfirmClear]=useState(false);
  const [exporting,setExporting]=useState(false);
  const [trash,setTrash]=useState(null);
  const [answerTrash,setAnswerTrash]=useState(null);
  useEffect(()=>{
    generation.current++;controller.current?.abort();inFlight.current=false;onBusy?.(false);
    setMessages(current=>current.filter(message=>!message.waiting));
    return ()=>{generation.current++;controller.current?.abort();inFlight.current=false;onBusy?.(false);};
  },[currentContext]);
  const saveAnswer=message=>{
    const question=message.question || messages.findLast(m=>m.role==='user')?.text || 'Recorded answer';
    const saved={...message,id:crypto.randomUUID(),question,savedAt:new Date().toISOString()};
    setAnswers(current=>[saved,...(Array.isArray(current)?current:[]).filter(a=>!(a.question===question && a.contextKey===message.contextKey))].slice(0,30));
    setSaveNotice('Answer saved on this device with its original context.');
  };
  const transcript=messages.map(m=>`${m.role==='user'?'You':'CurricuPath'}: ${answerText(m)}${m.profileContext?`\nDeclared context:\n${JSON.stringify(m.profileContext,null,2)}`:''}`).join('\n\n');

  const askAdvisor = async (rawText,retry=false) => {
    const text = String(rawText ?? "").trim();
    if (!text || inFlight.current || sending) return;
    if(declarationConflicts(profile).length){setConversationError("Resolve conflicting module declarations in Profile before requesting new advice.");return;}
    inFlight.current = true;
    const token=++generation.current;
    controller.current=new AbortController();
    const suppliedProfile=structuredClone(profile);
    setConversationError("");
    setInput("");
    setMessages((current) => [
      ...(retry?current.filter(m=>m.failedPrompt!==text):current),
      ...(retry?[]:[{ role: "user", text }]),
      {
        role: "assistant",
        text: "Checking the audited curriculum data…",
        waiting: true,
      },
    ]);
    onBusy?.(true);
    onHighlight?.([]);
    try {
      const data = await getJson("/advisor", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.current.signal,
        body: JSON.stringify({
          message: text,
          session_id: sessionId,
          programme_code: profile.programme || null,
          completed_modules: moduleCodes(profile.completed.join(",")),
          current_modules: moduleCodes(profile.current.join(",")),
          planned_modules: moduleCodes(profile.planned.join(",")),
          repeating_modules: moduleCodes((profile.repeating || []).join(",")),
          module_states: Object.fromEntries([
            ...profile.completed.map((code) => [code, "completed"]),
            ...profile.current.map((code) => [code, "current"]),
            ...profile.planned.map((code) => [code, "planned"]),
          ]),
          module_history_confirmed: Boolean(profile.historyConfirmed),
          manual_review_reasons: profile.reviewNote?.trim()
            ? [profile.reviewNote.trim()]
            : [],
          ranking_mode: "deterministic",
          interests: profile.interests || [],
          year_of_study: Number(profile.stage?.match(/year_(\d)/)?.[1]) || null,
          system,
        }),
      });
      if(token!==generation.current)return;
      if (data.system !== "handbook_rag") {
        setSessionId(data.session_id);
        safeSession.setItem("curricupath-session", data.session_id);
      }
      if (data.recommendations?.length)
        safeLocal.setItem("curricupath-first-recommendation", "true");
      setMessages((current) => [
        ...current.filter((message) => !message.waiting),
        { role: "assistant", text: data.answer, data, contextKey:currentContext, profileContext:suppliedProfile, question:text, createdAt:new Date().toISOString() },
      ]);
      onHighlight?.(namedModules(data));
    } catch (error) {
      if(token!==generation.current || error.name==='AbortError')return;
      setMessages((current) => [
        ...current.filter((message) => !message.waiting),
        {
          role: "assistant",
          text: `I could not complete that request: ${error.message}`,
          failedPrompt: text,
        },
      ]);
      setInput((current) => current || text);
    } finally {
      if(token===generation.current){inFlight.current = false;onBusy?.(false);}
    }
  };

  const clearConversation = async () => {
    if (inFlight.current || sending) return;
    setTrash(messages);
    inFlight.current = true;
    setClearing(true);
    setConversationError("");
    try {
      if (sessionId) {
        try {
          await getJson(`/advisor/sessions/${encodeURIComponent(sessionId)}`, {method: "DELETE"});
        } catch {
          /* the server session may already be gone; start fresh anyway */
        }
      }
      onHighlight?.([]);
      setSessionId(null);
      safeSession.removeItem("curricupath-session");
      setMessages([
        {
          role: "assistant",
          text: "Conversation cleared. What would you like to plan next?",
          suggestions: INITIAL_MESSAGES[0].suggestions,
        },
      ]);
    } catch (error) {
      setConversationError(
        `Could not start a new conversation. ${error.message}`,
      );
    } finally {
      inFlight.current = false;
      setClearing(false);
    }
  };

  const hasConversation = messages.some((message) => message.role === "user");
  return (
    <div
      className={`advisor-page ${hasConversation ? "has-conversation" : "advisor-empty"}`}
    >
      <div className="prototype-notice">
        <ShieldCheck size={16} />
        <span>
          Evidence-led guidance · Prototype, not an official registration
          decision
        </span>
      </div>
      <AcademicContext profile={profile} onEdit={onEditProfile} />
      {trash && !hasConversation && <button className="text-button" onClick={()=>{setMessages(trash);setTrash(null);}}>Undo new conversation</button>}
      {confirmClear && <div className="workspace-warning"><p>Clear this conversation? Saved answers are preserved. You can undo locally until you leave this view.</p><button className="secondary-button" disabled={sending} onClick={()=>{setConfirmClear(false);clearConversation();}}>Confirm clear conversation</button><button className="text-button" onClick={()=>setConfirmClear(false)}>Keep conversation</button></div>}
      {exporting && <section className="workspace-export"><p>This export contains questions and declared personal context. Review it before sharing.</p><pre>{transcript}</pre><button className="secondary-button" onClick={()=>downloadText('curricupath-conversation.txt',transcript)}>Export reviewed conversation</button></section>}
      {answerTrash && <button className="text-button" onClick={()=>{setAnswers(answerTrash);setAnswerTrash(null);}}>Undo saved answer removal</button>}
      <p role="status" className="helper-text">{saveNotice}</p>
      <details className="advanced-controls">
        <summary>Conversation &amp; saved answers</summary>
      <div className="workspace-toolbar advisor-workspace-tools"><button className="text-button" onClick={()=>setExporting(!exporting)} aria-expanded={exporting}>Preview / export conversation</button><button className="text-button" disabled={sending} onClick={()=>setConfirmClear(true)}>Clear conversation</button>{trash && <button className="text-button" onClick={()=>{setMessages(trash);setTrash(null);setConversationError('Conversation restored as a local record. New requests use a fresh server session.');}}>Undo conversation clear</button>}</div>
      <AnswerLibrary answers={Array.isArray(answers)?answers:[]} onRemove={id=>{setAnswerTrash(answers);setAnswers(current=>current.filter(a=>a.id!==id));}} onClear={()=>{setAnswerTrash(answers);setAnswers([]);}} onSources={onSources} profile={profile} />
      </details>
      <details className="advanced-controls">
        <summary>Evaluation / Advanced</summary>
        <div className="advisor-actions">
          {handbookRagDemoEnabled && (
            <label>
              Advisor system
              <select
                value={system}
                onChange={(e) => setSystem(e.target.value)}
              >
                <option value="curricupath">CurricuPath</option>
                <option value="handbook_rag">Handbook RAG (baseline)</option>
              </select>
            </label>
          )}
          <button className="text-button" onClick={onEditProfile}>
            Edit profile
          </button>
          <button
            className="text-button"
            disabled={sending || clearing}
            onClick={clearConversation}
          >
            New conversation
          </button>
        </div>
      </details>
      {system === "handbook_rag" && (
        <div className="prototype-notice baseline-notice">
          Experimental comparison baseline: retrieval and an LLM only, not
          checked against curriculum rules. Not an official CurricuPath
          decision.
        </div>
      )}
      <section className="chat-panel">
        {!hasConversation && (
          <div className="advisor-intro">
            <AtlasArtwork variant="dialogue" className="advisor-illustration" />
            <ChapterKicker index="02">A little clarity goes a long way</ChapterKicker>
            <h1>
              What do you want
              <br />
              to figure out?
            </h1>
            <p>
              Electives, prerequisites, or what comes next.
              <br />
              Start with a question. We’ll find the evidence.
            </p>
          </div>
        )}
        {hasConversation && (
          <div className="conversation-tools">
            <span>
              {messages.filter((m) => m.role === "assistant" && m.data).length}{" "}
              recorded responses
            </span>
            <button
              className="text-button"
              disabled={!messages.some((m) => m.role === "assistant" && m.data)}
              onClick={() =>
                document
                  .querySelectorAll(
                    '.message-log .message[data-recorded="true"]',
                  )
                  ?.item(
                    messages.filter((m) => m.role === "assistant" && m.data)
                      .length - 1,
                  )
                  ?.scrollIntoView({ block: "start" })
              }
            >
              Latest answer
            </button>
          </div>
        )}
        {hasConversation && (
          <div className="message-log" aria-live="polite" aria-busy={sending}>
            {messages
              .filter(
                (message, index) =>
                  index > 0 || message.data || message.role === "user",
              )
              .map((message, index) => (
                <ChatMessage
                  key={`${message.role}-${index}`}
                  message={message}
                  onPrompt={askAdvisor}
                  onOpenModule={onOpenModule}
                  onOpenCourse={onOpenCourse}
                  onSources={onSources}
                  onShowInPlan={onHighlight}
                  busy={sending || clearing}
                  currentContext={currentContext}
                  onEditProfile={onEditProfile}
                  onSaveAnswer={saveAnswer}
                />
              ))}
          </div>
        )}
        <div className="composer-dock">
          {sending && <button className="secondary-button" onClick={()=>{generation.current++;controller.current?.abort();inFlight.current=false;onBusy?.(false);setMessages(current=>current.filter(message=>!message.waiting));setConversationError('Request cancelled. You can revise your question and try again.');}}>Cancel current request</button>}
          {context && input.includes(context.code) && (
            <div className="advisor-module-context">
              <span>
                <small>From your curriculum</small>
                <strong>
                  {context.code} · {context.name}
                </strong>
              </span>
              <button
                className="text-button"
                onClick={() => onOpenModule(context.code)}
              >
                View module
              </button>
            </div>
          )}
          {conversationError && (
            <p className="conversation-error" role="alert">
              {conversationError}
            </p>
          )}
          <form
            className="composer"
            onSubmit={(event) => {
              event.preventDefault();
              askAdvisor(input);
            }}
          >
            <textarea
              aria-label="Your question"
              aria-describedby="composer-hint"
              rows={2}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Ask about your next step…"
              maxLength={2000}
              autoComplete="off"
              onKeyDown={(event) => {
                if (
                  event.key === "Enter" &&
                  !event.shiftKey &&
                  !event.nativeEvent.isComposing
                ) {
                  event.preventDefault();
                  askAdvisor(input);
                }
              }}
            />
            <button
              disabled={sending || clearing || !input.trim()}
              aria-label="Send message"
            >
              <Send size={20} />
            </button>
          </form>
          <small id="composer-hint" className="composer-hint">
            Enter to send · Shift + Enter for a new line
          </small>
        </div>
        {!hasConversation && (
          <div className="quick-context">
            {INITIAL_MESSAGES[0].suggestions.map((prompt) => (
              <button key={prompt} onClick={() => askAdvisor(prompt)}>
                {prompt}
                <ChevronRight size={14} />
              </button>
            ))}
          </div>
        )}
        {hasConversation && (
          <div className="conversation-actions">
            <button
              className="text-button"
              disabled={sending || clearing}
              onClick={clearConversation}
            >
              New conversation
            </button>
            {namedModules(messages.at(-1)?.data).length > 0 && (
              <button
                className="text-button"
                onClick={() =>
                  onHighlight?.(namedModules(messages.at(-1)?.data), true)
                }
              >
                Show in Plan <Route size={16} />
              </button>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
