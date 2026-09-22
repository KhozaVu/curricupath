# CurricuPath Phase Progress

**Updated:** 22 September 2026  
**Open Day target:** 14 October 2026

## Read This First

CurricuPath has a working prototype: the React interface, FastAPI service,
CSV/PostgreSQL catalogue access, deterministic eligibility gates, public-course
search, source evidence, session state, and optional response review are present.

The percentages below describe delivery of the implementation plans, not proof of
academic accuracy. A feature is only ready to make a research claim after the
independent evaluation work is complete.

| Area | Current progress | What this means |
| --- | ---: | --- |
| Functional prototype | about 90% | The main user journeys work, with deterministic fallbacks and an automated release gate. |
| Context-constrained reviewer addition | about 85% | The code, UI and engineering release controls are present; independent evaluation remains. |
| Eligibility uncertainty extension | 100% | Phases 1-4 are complete, including one-turn clarification reuse and safe termination. |
| Formal evaluation readiness | infrastructure ready; official run not started | Scripts, cases, manifests and gates exist, but named reviewers and approved labels are still required. |

## Track A: Eligibility Uncertainty Extension

This track implements the contribution under investigation: distinguish a student
fact that is missing from institutional evidence that is missing or unsuitable.

| Phase | Status | Progress | Delivered evidence |
| --- | --- | ---: | --- |
| 1. Decision and evidence contract | Complete | 100% | `EligibilityResult` returns `eligible`, `ineligible`, `needs_clarification`, or `manual_review_required`; evidence and rule traces are retained. |
| 2. Explicit student module facts | Complete | 100% | Profiles support `completed`, `current`, `planned`, `not_completed`, and `unknown`; the interface records whether the module history is complete. |
| 3. Recursive requirement evaluation | Complete | 100% | Nested `all_of`, `any_of`, and programme-year conditions use three-valued evaluation; the system short-circuits known branches and produces a focused question for a material unknown. |
| 4. Clarification answer reuse | Complete | 100% | A controlled reply is stored as the requested module fact, the original eligibility decision is rerun once, and unresolved cases stop safely instead of looping or guessing. |

### Phase 3 Behaviour Now Available

For a prerequisite such as `MATH1048A`, an incomplete profile receives:

> Have you completed MATH1048A?

If a known non-completion already makes an `all_of` rule fail, CurricuPath returns
an ineligible decision rather than asking unnecessary questions. If an `any_of`
rule has one confirmed valid route, unknown alternatives do not cause a
clarification. Malformed rule data becomes `manual_review_required`.

The implementation is in [eligibility.py](../app/advisor/eligibility.py), with
advisor presentation in [engine.py](../app/advisor/engine.py).

### Phase 4 Behaviour Now Available

When an eligibility decision needs one student fact, the session retains the
original module, programme, rule gate, and missing module code. The next reply is
accepted only when it maps to a controlled state such as `completed`,
`not_completed`, `current`, or `planned`. Prerequisites accept only completed or
not-completed replies; current and planned states are also available for
corequisites and exclusions.

CurricuPath applies that fact and reruns the deterministic gates once. If the
result is then eligible or ineligible, the session is cleared. If another fact is
still unknown, or the reply cannot be interpreted, the system returns
`clarification_unresolved`, clears the pending context, and directs the student to
update the profile. This one-question cap prevents conversational loops and
unrecorded assumptions.

## Track B: Context-Constrained Reviewer Plan

This follows [context_constrained_reviewer_plan_2026-09-17.md](context_constrained_reviewer_plan_2026-09-17.md).

| Phase | Status | Progress | Remaining work |
| --- | --- | ---: | --- |
| 1. Policy and contracts | Complete | 100% | Maintain the supported, ambiguous and out-of-scope taxonomy as a versioned contract. |
| 2. Deterministic controls | Complete | 100% | Keep scope checks, response invariants, safe out-of-scope responses and deterministic fallback covered by regression tests. |
| 3. Reviewer adapter | Implemented, disabled by default | 100% in code | Enable only for a controlled live smoke test with a valid provider key; do not make it required for the Open Day demo. |
| 4. Evaluation and UI transparency | Partly complete | 35% | The UI shows whether a response was independently reviewed or deterministic-only. Run the matched variants and collect the metrics. |
| 5. Stabilisation and release freeze | Candidate verified | 85% | Automated checks, release fingerprints, drift detection and the demo/fallback runbook are complete. Commit the release inputs, run non-mutating verification, and rehearse before final freeze. |

The reviewer cannot change eligibility, source facts, candidate ordering, or rule
outcomes. It only checks whether the user-facing wording agrees with the protected
deterministic result. The feature flag remains off by default so a model outage
does not block the prototype.

## Evaluation Status

The project has the evaluation structure, but it is not yet an official study.
The following are still human/process requirements:

- Confirm named academic reviewer(s), a non-developer grounding judge, and their
  available hours in `experiments/evaluation/v2_5/personnel.json`.
- Have reviewers independently label and approve the eligibility cases without
  seeing CurricuPath outputs.
- Commit a clean project snapshot before generating the final manifest.
- Run the frozen CurricuPath, Handbook-RAG and structured-rules comparison arms.
- Run the reduced clarification ablation and record its limitations honestly.

Until these are complete, describe evaluation output as a pilot or engineering
verification, not independently validated performance.

## Immediate Next Steps

1. Commit the verified release candidate and all release inputs.
2. Run `py scripts/freeze_release.py --verify` from the clean committed snapshot.
3. Secure the evaluation roles and begin independent case labelling.
4. Run the official evaluation readiness gate on the clean committed snapshot.
5. Rehearse the Open Day demo with PostgreSQL, CSV fallback and reviewer-disabled
   fallback paths.

## Phase 5 Release Candidate

`scripts/freeze_release.py` now runs the data validator, complete automated suite,
explicit PostgreSQL smoke tests, and production React build. It fingerprints the
catalogue, database, deterministic controls, prompts, policy/rubric versions,
reviewer reason codes, model configuration, packages, Compose definition and Git
state without storing API keys.

The first run passed every engineering gate and produced
`experiments/release/open_day_rc1_manifest.json` with release fingerprint
`0592c52510226f6f05e4ea34bf4d161d06c921f7a7ce1abc764d3af437bb2534`.
It remains `candidate_verified` because the working tree is intentionally still
dirty. Final freeze requires committing the candidate and running the non-mutating
`--verify` operation from a clean tree. The Open Day route and outage recovery
steps are recorded in `docs/open_day_demo_checklist.md`.

## Verification Completed for the Latest Eligibility Work

- 93 focused eligibility, advisor, response-invariant, and reviewer tests passed.
- One isolated FastAPI session clarification test passed.
- The complete suite passed with 253 tests when the Handbook-RAG demo was
  explicitly disabled for tests that exercise the unconfigured path.
- Curriculum and public-course validation passed with 0 errors and 0 warnings.
- Python compilation passed for the Phase 4 modules.

The local `.env` currently enables the Handbook-RAG demonstration, so its two
"not configured" tests fail unless `HANDBOOK_RAG_DEMO_ENABLED=false` is set for
the test process. This is a configuration-state distinction, not a Phase 4
failure. The complete release command used here was:

```powershell
$env:HANDBOOK_RAG_DEMO_ENABLED='false'; py -m pytest -q
```
