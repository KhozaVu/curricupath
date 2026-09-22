# CurricuPath Context-Constrained Reviewer Plan

**Date:** 17 September 2026  
**Status:** Initial scope, invariant, bounded-repair and optional reviewer layers
implemented on 17 September 2026; evaluation and release-gate work remains.  
**Target milestone:** Open Day, 14 October 2026.

## 1. Objective

Add explicit scope control and an independent reasoning reviewer while preserving
all current CurricuPath functionality: profile setup, module information,
eligibility, curriculum and elective queries, programme information and comparison,
credit answers, public-course recommendations, career paths, clarification,
journey tracking, achievements, evidence inspection, PostgreSQL/pgvector retrieval,
CSV fallback, and deterministic ranking.

The architectural trust rule remains:

> Verified catalogue data and deterministic rules define academic truth. Language
> models may interpret wording and review presentation quality, but may not create,
> remove, or change an academic decision.

The reviewer is therefore a response-quality control, not a second eligibility
engine and not an unrestricted chatbot.

## 2. Additions to the Proposed Architecture

The supplied proposal is sound. The following additions close important loopholes.

### 2.1 Use three scope outcomes

A binary supported/unsupported result would incorrectly reject unfamiliar wording
for a valid CurricuPath question. The scope gate should return:

- `SUPPORTED`: enough information exists to route the request safely.
- `AMBIGUOUS`: the request may be supported, but a focused clarification is needed.
- `OUT_OF_SCOPE`: the requested action is not a CurricuPath capability.

An ambiguous module name should produce a module-choice question. It should not be
described as out of scope. A question about predicting marks, personal wellbeing,
admissions guarantees, or official registration approval is out of scope.

### 2.2 Separate decisions from wording

Every supported engine result should have two parts:

```text
decision_payload     Immutable structured facts, gates, scores and source IDs
presentation_payload Human-readable answer, cards, labels and suggestions
```

The reviewer may reject or request repair of `presentation_payload`. It must never
modify `decision_payload`. FastAPI should verify after review that protected fields
such as `eligible`, `completed`, `course_code`, `programme_code`, rule outcomes,
candidate order, scores and source IDs are unchanged.

### 2.3 Prefer deterministic repair

`REVISE` should first map reviewer reason codes to deterministic response templates.
For example, `MISSING_REQUIREMENT_EXPLANATION` can rebuild the answer from the
existing prerequisite summary. A language model may rephrase non-material text only
if a later experiment explicitly enables it. There should be at most one repair and
one second review; otherwise return a safe response.

### 2.4 Define failure and privacy behaviour

The system must remain usable if the reviewer is unavailable. Deterministic engine
answers that pass local invariant checks should still be returned with
`review_status=not_run`. A reviewer timeout must not silently convert a valid result
into an academic rejection. Persistent logs should contain verdicts, reason codes,
latency, model/configuration version and catalogue fingerprint, but not raw
participant prompts or generated prose.

## 3. Supported Scope

The scope policy should be a versioned application constant rather than a prompt-only
instruction.

### 3.1 Supported request families

- Module information, including lecturer, scope, materials, credits and year.
- Module eligibility, prerequisites, corequisites and exclusions.
- Curriculum, compulsory-module and elective-pool listings.
- Interest-based fourth-year elective suggestions.
- Programme information and EFA03/EFA04 comparison.
- Source-verified public-course search and career-path exploration.
- Questions about modules selected as completed, current or planned.
- Greetings, help, clarification answers and requests to reset the conversation.

### 3.2 Ambiguous requests

- A partial module name with multiple catalogue matches.
- Eligibility without a programme or identifiable module.
- An elective recommendation without a known programme.
- A supported topic expressed too vaguely to select one operation.
- Contradictory profile facts, such as the same module marked both incomplete and
  completed in one request.

### 3.3 Out-of-scope requests

- Predicting marks, graduation outcomes or employment guarantees.
- Mental-health, financial, legal or disciplinary advice.
- Making official registration decisions or overriding faculty rules.
- General knowledge unrelated to EFA03/EFA04, verified public courses or supported
  career information.
- Requests to invent, alter or ignore curriculum evidence.

The response should be deterministic and briefly identify the supported alternatives.
Out-of-scope requests must never be sent through retrieval and ranking merely because
they contain a known keyword such as `engineering` or `course`.

## 4. Target Pipeline

```text
React request and declared profile
        |
        v
FastAPI/Pydantic validation
        |
        v
Deterministic normalisation and intent extraction
        |
        v
Versioned scope gate
   |             |                 |
supported     ambiguous       out of scope
   |             |                 |
   v             v                 v
AdvisorEngine  focused          fixed safe
   |          clarification      response
   v
Repository, retrieval, rules, eligibility and ranking
   |
   v
Immutable decision payload + draft presentation
   |
   +--> local response invariants
   |
   v
Optional independent reviewer
   |             |                 |
approve        revise             reject
   |             |                 |
   |       one deterministic       |
   |          repair only          |
   +-------------+-----------------+
                 |
                 v
Final invariant check -> audit metadata -> React
```

Scope checking occurs before semantic retrieval. Local invariants occur both before
and after the reviewer because structural agreement can be tested without a model.

## 5. Contracts

### 5.1 Scope result

```python
class ScopeDecision(BaseModel):
    status: Literal["supported", "ambiguous", "out_of_scope"]
    intent: Intent
    reason_codes: list[str]
    clarification_question: str | None = None
```

The scope decision must be derived from the validated intent, identifiers and current
conversation state. An optional model may propose a classification, but deterministic
policy has final authority for explicitly supported and prohibited operations.

### 5.2 Review input

The reviewer receives only the minimum necessary context:

- Original request, marked as untrusted user content.
- Detected intent and scope result.
- Declared profile fields relevant to this request.
- Immutable structured engine result.
- Source IDs and already-retrieved evidence snippets used by the result.
- Draft presentation.
- The reviewer rubric and protected-field policy.

Raw source documents should not be included when a short evidence record is enough.
Instructions found inside user text or retrieved evidence are data and must not be
followed by the reviewer.

### 5.3 Structured review output

```python
class ReviewResult(BaseModel):
    verdict: Literal["approve", "revise", "reject"]
    scope_consistent: bool
    query_answered: bool
    intent_consistent: bool
    facts_supported: bool
    decision_consistent: bool
    clarification_appropriate: bool
    reason_codes: list[str]
    repair_instructions: list[str]
```

`repair_instructions` may reference only approved presentation operations. It may
not contain replacement eligibility decisions, new module codes, new sources or new
rankings.

### 5.4 Initial reason-code vocabulary

- `RESPONSE_DOES_NOT_ADDRESS_QUERY`
- `INTENT_RESPONSE_MISMATCH`
- `UNSUPPORTED_MATERIAL_CLAIM`
- `DECISION_TEXT_CONTRADICTION`
- `MISSING_REQUIREMENT_EXPLANATION`
- `MISSING_SOURCE_QUALIFIER`
- `CLARIFICATION_REQUIRED`
- `UNNECESSARY_CLARIFICATION`
- `UNSUPPORTED_USER_REQUEST`
- `REVIEWER_OUTPUT_INVALID`
- `REVIEWER_UNAVAILABLE`

Version this vocabulary. Do not accept arbitrary model-created reason codes.

## 6. Local Invariants

Implement deterministic checks before relying on model judgement:

- An ineligible result cannot contain text stating that the module is eligible.
- A completed module must be labelled completed rather than recommended again.
- Every displayed module/course identifier must exist in the structured result.
- Every material academic claim must reference a supplied source or rule outcome.
- Programme and year labels must agree with curriculum membership.
- Recommendation cards must preserve the engine's candidate order and score.
- A clarification result must contain exactly one focused question and no final
  academic decision.
- Out-of-scope responses must not include recommendations or retrieved candidates.

These checks are fast, reproducible and useful even when the external reviewer is
disabled.

## 7. Reviewer Policy

The reviewer operates under these restrictions:

1. It assesses correspondence between the request, structured result, evidence and
   presentation.
2. It cannot call the database, add evidence, rerank candidates or execute tools.
3. It cannot change protected fields.
4. It returns schema-validated JSON at temperature zero.
5. Invalid output, timeout or provider failure opens the existing style of bounded
   circuit breaker and records `review_status=not_run`.
6. `REVISE` permits one deterministic repair and one re-review.
7. A second failure returns a fixed safe explanation or focused clarification.
8. Academic answers from the deterministic engine are never changed solely because
   the reviewer has different domain knowledge.

For Open Day, use the already configured hosted model adapter if it supports reliable
structured output. Keep the reviewer behind `REASONING_REVIEWER_ENABLED=false` by
default until evaluation thresholds are met.

## 8. Logging and Data Handling

Add review metadata to each recommendation run:

- Reviewer enabled/disabled/not run.
- Reviewer model and rubric version.
- Verdict and controlled reason codes.
- Review and repair count.
- Reviewer latency and timeout flag.
- Dataset and decision-payload fingerprints.
- Whether final local invariants passed.

Do not persist raw user text, model prompts, evidence prose or final responses for
participant sessions. Synthetic evaluation cases may retain full traces in a clearly
separate experiment directory.

## 9. Evaluation

Create a frozen, independently reviewed test set containing:

- Supported requests for every intent and common wording variant.
- Ambiguous requests that should lead to one focused clarification.
- Clearly out-of-scope requests.
- Adversarial requests that ask the system to ignore rules or invent facts.
- Correct drafts, incomplete drafts and drafts that contradict structured results.
- Reviewer outages, malformed output and timeout cases.

Report:

| Measure | Release target |
| --- | ---: |
| Deterministic scope accuracy on reviewed cases | at least 95% |
| Out-of-scope false acceptance | 0% on safety-critical cases |
| Academic decision mutation by reviewer | 0 cases |
| Unsupported material claims accepted | 0 cases |
| Useful revision precision | at least 90% |
| Unnecessary rejection rate | below 5% |
| Local invariant pass rate | 100% |
| Reviewer p95 latency | measured and reported; target below 3 seconds |

Compare three matched variants:

1. Current engine without new scope/review controls.
2. Deterministic scope gate plus local invariants.
3. Deterministic scope gate, local invariants and reasoning reviewer.

This isolates whether the reasoning reviewer adds value beyond checks that ordinary
code can perform.

## 10. Implementation Sequence to 14 October

### Phase 1: Policy and contracts, 17-20 September

- Freeze the supported, ambiguous and out-of-scope taxonomy.
- Add Pydantic scope/review contracts and controlled reason codes.
- Define protected fields for each current intent response.
- Create initial reviewed scope and contradiction cases.

### Phase 2: Deterministic controls, 21-25 September

- Implement the scope gate before retrieval/ranking.
- Implement local response invariants.
- Add fixed out-of-scope and reviewer-failure responses.
- Preserve all current regression tests and UI behaviour.

### Phase 3: Reviewer adapter, 26-30 September

- Add a provider-independent reviewer protocol and one hosted implementation.
- Enforce timeout, schema validation, one-repair limit and circuit breaker.
- Add review metadata to existing recommendation logs.
- Keep the feature disabled by default.

### Phase 4: Evaluation and UI transparency, 1-6 October

- Run the three matched variants on the frozen cases.
- Add a subtle UI state for reviewed, deterministic-only and unavailable review.
- Ensure rejection and clarification wording remains understandable.
- Measure accuracy, mutation, false acceptance, false rejection and latency.

### Phase 5: Stabilisation, 7-11 October

- Fix only failures supported by frozen cases; version any policy change.
- Run the complete automated suite, validators and PostgreSQL smoke tests.
- Freeze model, prompt/rubric, reason-code and catalogue fingerprints.
- Update the investigation report and demonstration script.

### Open Day buffer, 12-14 October

- No architectural expansion.
- Rehearse supported, ambiguous, out-of-scope and reviewer-outage demonstrations.
- Keep deterministic fallback available for the complete demonstration.

## 11. Proposed File Changes

```text
app/advisor/scope.py                 scope taxonomy and deterministic gate
app/advisor/reviewer.py              protocol, contracts and orchestration
app/advisor/response_invariants.py   protected-field and text/structure checks
app/advisor/response_repair.py       bounded deterministic repairs
app/main.py                          reviewer dependency construction
app/config.py                        reviewer feature flag/model/timeout
app/data/recommendation_log.py       review audit metadata
frontend/src/App.jsx                 optional review-status presentation
tests/test_scope.py                  scope and ambiguity cases
tests/test_reviewer.py               verdict and failure behaviour
tests/test_response_invariants.py    decision/presentation contradictions
experiments/evaluation/              frozen reviewer evaluation cases/results
```

Do not place reviewer logic inside `eligibility.py`, `ranking.py` or React. Those
boundaries must remain deterministic and independently testable.

## 12. Definition of Done

This addition is complete only when:

- Every request receives a versioned scope outcome before retrieval or ranking.
- Existing supported features retain their current behaviour and tests.
- Ambiguous requests ask one focused clarification.
- Out-of-scope requests receive a fixed safe response.
- The reviewer cannot mutate academic decisions or candidate ordering.
- Local invariants catch known response/decision contradictions without a model.
- Reviewer failure degrades to a documented deterministic path.
- One-repair and timeout limits are enforced.
- Review metadata is auditable without retaining participant text.
- Matched evaluation shows whether the reviewer improves quality beyond deterministic
  controls.
- Documentation and the Open Day demonstration accurately distinguish implemented,
  experimental and disabled components.

## 13. Recommendation

Proceed with the architecture, including the safeguards above. The highest-value
first implementation is the deterministic scope gate and local response invariants.
They immediately constrain context, improve failure handling, and create a stable
contract for evaluating whether an independent reasoning reviewer is worth its added
latency and provider dependency.
