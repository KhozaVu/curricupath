# Evaluation Deviations

Add every post-freeze change with its date, reason, affected cases, affected outputs,
and rerun decision. Never overwrite an earlier entry.

## 2026-09-22: Repeated-failure academic exclusion is out of scope for this evaluation

**Reason:** During initial review of the reviewer pack, the named academic reviewer
referred us back to `EBE_eBook_2026.pdf`, noting that failing a module twice results
in exclusion. Investigation confirmed CurricuPath's student-profile schema
(`completed_modules`/`current_modules`/`planned_modules` in `app/main.py`'s
`AdvisorRequest`) has no field for module attempt history, grades, or failure, so
this class of exclusion cannot currently be represented or evaluated. One existing
rule, `EXCLUSION_BSC_ENG` (`data/processed/rules.csv`, source `EBE_2026`, handbook
page 59), gestures at repeated-course/aggregate performance but is structurally
unreachable (`target_course_code` is blank, so `_rules_for_course` in
`app/advisor/eligibility.py` never selects it for any course-specific check) and its
condition keys (`repeated_courses_must_pass`, `minimum_aggregate_percent`) are not
implemented by the condition evaluator, which only recognises `all_of`/`any_of`/
`all_courses_in_programme_year`. The reviewer has not yet supplied the specific rule
number for the "fail twice" clause; it has not been located independently in the
handbook and is not yet cited precisely anywhere in this codebase.

**Affected cases:** None of the 60 eligibility cases test this scenario, because the
case schema (`student_profile_json`) has no field to express a failed or repeated
attempt. No case needs relabelling as a result of this deviation.

**Affected outputs:** None yet generated. This is a known, pre-existing gap in
CurricuPath's rule model, not a change to any frozen case, label, or output.

**Rerun decision:** No rerun required. This capability gap is deferred past Open Day
(14 Oct 2026) by developer/supervisor decision and is recorded here as an explicit
scope limitation rather than being silently absent. It should be disclosed in the
final report's limitations section: CurricuPath cannot currently detect or apply
repeated-failure academic exclusion, and the evaluation's eligibility cases do not
exercise this rule class.


## 2026-09-29: Interpretation fallback made Gemini-first and extended to programmes

**Reason:** A live query ("tell me aboyt Information Enyineering") was answered with a
module clarification instead of the EFA04 programme. The fuzzy tier did not correct
"aboyt", and the LLM tier could only return modules and was never reached because the
fuzzy rewrite already parsed. Rather than keep adding phrase-level patches, the developer
chose to rely on the LLM tier: in `llm` mode the model is asked first, fuzzy is the
fallback when no model answers, and the model may return EFA03/EFA04 with intent
`programme_information` (validated against the catalogue). The local server default was
set to `llm` in `.env`. Separately, a request can now only lower, never raise, the
server's fallback mode (review finding: public callers could otherwise switch Gemini on).

**Affected cases:** None relabelled. Ambiguity case AMB012 ("information engineering",
expected `ambiguous_module_name`) is unaffected because a bare programme name is parsed
deterministically and never reaches the fallback.

**Affected outputs:** `results/diagnostics/llm_fallback/mode_llm` no longer describes the
current code. Re-run as `mode_llm_gemini_first` (33/34, unchanged correctness; see the
FINDINGS addendum). The 60-case eligibility pilot drafts run with the Gemini key blank,
so they do not exercise this tier.

**Rerun decision:** Diagnostic re-run done. Any official run must record the
`INTERPRETATION_FALLBACK` value it used.

## 2026-09-29: Non-interactive CurricuPath arm now receives the consolidated fact

**Reason:** Review finding. `scripts/run_evaluation.py` sent `question` to both CurricuPath
arms, while the frozen protocol (and the RAG runner) gives every non-interactive arm
`consolidated_noninteractive_input`. The no-clarification arm now receives that field.
Also fixed from the same review: `--pace-seconds` rejects negative values before any
output file is created, and `run_fallback_evaluation.py --mode none` now explicitly runs
with the fallback off instead of inheriting the server default.

**Affected cases:** ELIG031-ELIG040, the only cases whose consolidated input differs from
the question (declared fact: "I have listed every module I am currently taking or
planning.").

**Affected outputs:** `results/raw/draft_curricupath.jsonl` and
`draft_curricupath_no_clarification.jsonl` regenerated (draft, 1 run, Gemini key blank,
fuzzy fallback). No decision changed in either arm; the pilot report's figures stand.

**Finding (not fixed):** With the fact supplied up front, all ten cases remain
`unresolved_without_clarification`. The engine accepts this declared fact only as a reply
to its own follow-up question, not inside the first message. This is a real limitation
of the no-clarification arm and must be reported as such. It is deliberately not patched
now, because doing so would mean building against the eligibility test set.

**Rerun decision:** Draft outputs regenerated; no further rerun needed for the pilot.

## 2026-09-29 (later): Fallback also triggers for a programme name read as module names

**Reason:** Live query "Tell me aboyt Information Engineering" still produced a
"which module do you mean" clarification. The parser treated the programme name as a
prefix of two module names, which counts as resolved, so the fallback never ran.
`needs_fallback` now also returns true when the parser lands on `module_information`
with no module chosen, the message ends with a programme name, and there are other
words before it. If the model gives no usable answer, the original clarification is
shown unchanged.

**Affected cases:** None. The only frozen case ending in a programme name is AMB012
("information engineering"), which has no other words and is deliberately excluded.

**Affected outputs:** None. No frozen fallback case matches the new condition.

**Rerun decision:** No rerun needed.

## 2026-09-29 (later still): New programme question interrupts a pending clarification

**Reason:** In the browser UI the session carries over. After the advisor asked "which
module do you mean?", the fallback was skipped for every later message (it only ran with
no clarification pending), so "Tell me aboyt Information Engineering" repeated the same
question. The fallback now also runs while a clarification is pending, but only when the
message ends with a programme name and has other words before it; ordinary replies to the
clarification ("the design one", a module code, the bare programme name) are unaffected.

**Affected cases:** None of the frozen sets. The ambiguity runner scripts replies to
clarifications; none ends in a programme name after other words.

**Affected outputs:** None. **Rerun decision:** No rerun needed.

## 2026-09-29 (evening): Rules-only arm receives the declared fact; analysis regenerated

**Reason:** Review finding. The rules-only runner passed only the structured module lists, so
ELIG031-ELIG040 had no decision while the other non-interactive arms received the scripted
fact ("I have listed every module I am currently taking or planning"). It is now encoded as
`module_history_confirmed=true` for exactly the cases whose consolidated input carries that
fact. Also regenerated, after the earlier no-clarification parity fix, so analysis matches raw
evidence: scoring (`score_evaluation.py --allow-draft --reference-sets developer briefing`),
benchmark figures and the PDF report.

**Affected cases:** ELIG031-ELIG040.

**Affected outputs:** `draft_rules_only.jsonl` (these 10 cases: no decision -> `ineligible`,
matching the developer label), all files under `results/draft_analysis/`. Rules-only macro-F1
under developer labels moves to 1.000 (was 0.889, equal to CurricuPath) and to 0.758 under the
briefing labels. CurricuPath figures are unchanged.

**Finding:** CurricuPath and rules-only now agree on 50 of 60 cases, not 60. On the other 10 the
gap is one of information format: rules-only is handed the fact as a structured field, while
both CurricuPath arms receive it as text, and the engine does not read it (the interactive
arm's clarification also stays unresolved). This is a real limitation and the report says so.
The report text that claimed identical decisions on all 60 was corrected; its assertions were
changed to match the data.

**Rerun decision:** Draft outputs regenerated; no official run affected.

## 2026-09-29 (night): Clarification asks about every unknown module in the gate

**Reason:** Product change requested by the developer. A live check ("Can I take ELEN3013A?")
had three unknown prerequisites; the advisor asked about only the first and then stopped
("clarification limit reached"). Now (1) the clarification question lists every unknown module
in the failing gate and accepts one status per module (or the "All completed" / "None
completed" shortcuts); (2) statuses already given are kept in the session
(`answered_facts`) while the check continues; (3) a reply that supplies at least one new
status keeps the check going, and a reply that supplies none ends it. A bare "Completed" is
not applied when several modules are pending (it is not guessed). The original-target module
is preserved when a reply names the pending modules.

**Supersedes:** the "one clarification only" behaviour recorded in
`test_one_clarification_limit_stops_when_another_fact_is_unknown`, which was rewritten.
The protocol still allows one scripted reply per evaluation case, and the runner sends
exactly one.

**Affected cases:** none. Re-running both draft CurricuPath eligibility arms and both draft
ambiguity arms after the change gave identical decisions and statuses on every case (60 and
13). ELIG031-ELIG040 remain unresolved (their scripted reply is not a module status).

**Affected outputs:** the raw draft files gained fields (`target_predicates`,
`clarification_applied_all`), so they were regenerated, and scoring, figures and the PDF
report were regenerated from them; figures unchanged.

**Rerun decision:** Done for the pilot. Official runs use the code as frozen at that time.

## 2026-10-01: School registration reference adopted and timetable-clash gate specified

**Reason:** Independent academic review was not obtainable. The project team adopted the
2026 registration workbooks supplied by School of EIE Admin Manager M. Ismail by email on
2026-09-30 as the primary answer key and benchmark, named the **School registration
reference**. This is the closest available substitute for academic review, but it is a
single-source institutional reference and is not independent, multi-reviewer validation.
Developer labels and Senate Rules briefing labels remain sensitivity keys.

The source bundle was supplied as
`C:\Users\khoza\Downloads\codex_bundle.zip`. The Downloads original was left untouched;
verified copies were placed under `data/raw`, `data/rules`, `scripts`, and `docs`, and their
SHA-256 values were recorded in `school_reference_input_fingerprints.json`. All 19 payload
files matched the prefixes in the bundle's `README.txt`. The supplied generator reproduced
`eligibility_cases_pilot_proposed.csv` byte-for-byte. Its generated `grid_rules.json` was
semantically identical to the supplied file (84 records and no differing JSON values) but
not byte-identical because of serialization; this was disclosed and the project owner then
directed implementation to continue. The verified supplied JSON was restored and remains
the retained input.

**Pre-scoring rulings:**

1. A corequisite planned concurrently satisfies the corequisite under rubric step 3 and
   the handbook's "must be taken with" definition. A stricter reading must be reported as
   sensitivity analysis.
2. ELIG018 (`ELEN3024A`) follows the registration grid's additional `MATH2014A`
   prerequisite and is therefore ineligible; the handbook-only eligible outcome must be
   reported alongside it.
3. ELIG041-ELIG044 are `manual_review_required` under rubric step 6.
4. A scripted clarification reply is treated as a supplied student fact.
5. A timetable clash is a hard ineligibility reason, equal to a missing prerequisite or
   corequisite. A clash exists when either the colour-coded planner or the cross-curricular
   table records the pair. A clash cannot be cancelled by the "Higher Year Courses that can
   be taken" column.

The clash gate applies only when a target clashes with a module in
`profile.repeating_modules`. It does not infer clashes from current or planned modules, and
it does not infer clashes from Year 1 diagonal/slot headers. Whether those other states
should be checked is an open design question. Failed clarification remains a separate open
design question and is not changed by this amendment.

**Affected cases:** The 20 blinded pilot profiles contain no `repeating_modules`, so their
School-reference labels are unchanged and the clash gate is exercised on 0 of 20 cases.
Synthetic clash fixtures are kept outside the frozen set. Experiment C reviewer fields
remain empty and Experiment C remains blocked.

**Affected outputs:** A versioned eligibility rubric, generated combined clash-rule table,
source-disagreement table, and feature-gated deterministic eligibility implementation are
added. Any engine run using grid-sourced requirements or this clash gate must be reported
separately as: "engine encodes the reference; shows faithful encoding, not independent
agreement".

**Rerun decision:** No benchmark output may be interpreted or regenerated until this
amendment and the fixed headline configuration are committed. Existing pilot outputs remain
historical draft outputs and do not contain clash cases.

## 2026-10-01 (implementation): Generator newline drift corrected

**Reason:** The earlier byte mismatch in `grid_rules.json` was traced to platform newline
translation on Windows. The supplied generator now opens JSON outputs with explicit LF
newlines. It reproduces both `eligibility_cases_pilot_proposed.csv` and `grid_rules.json`
byte-for-byte with their verified bundle copies. No JSON value, case, profile, question, or
label changed.

**Affected cases:** None. The 20 proposed labels remain 5 eligible, 11 ineligible, and 4
manual-review-required; the clash gate is exercised on 0 of 20 cases.

**Rerun decision:** Generator reproducibility gate passed. Synthetic clash tests may proceed;
benchmark systems have not been scored against the School registration reference in this
implementation step.

## 2026-10-01 (later): Clash gate extended to current/planned modules and asked in chat

**Reason:** Developer decision on the open design question in the entry above. The clash gate
previously fired only for `repeating_modules`.

1. A target is now also ineligible when a module of a listed clash pair is declared current or
   planned while the student asks about the other module (either direction: two modules in
   one timetable slot clash both ways). Reason text says "taking or planning in the same
   period" rather than "repeating".
2. When the module history is explicitly unconfirmed (`module_history_confirmed=false`) and
   the listed partner's status is unknown, the gate returns `needs_clarification` and the
   advisor asks "Are you repeating it, currently taking it, planning to take it, or none of
   these?" (batched when several partners are unknown). Reverse-direction partners are never
   asked about; they block only when declared current or planned. Legacy profiles
   (`module_history_confirmed` absent) are not asked, preserving earlier behaviour.
3. A "none of these" answer is recorded as `clash_cleared_modules` for the clash check only. It
   never marks a module "not completed", so it cannot change prerequisite results.
4. Fix: the pending clarification now records the gate that asked (`clarification.gate`)
   instead of the last gate run. With the clash gate on, every gate runs, so the old value could
   be wrong and a prerequisite reply could be read as a corequisite one.

**Interpretation caveat:** the School tables are framed around students repeating a module.
Treating current/planned modules as clashes extends that reading; it should be confirmed with
the academic reviewer before any claim about it.

**Affected cases:** none. The clash gate stays disabled in the evaluation harness. Re-running
both draft CurricuPath arms after the change gave identical decisions and statuses on all 60
cases; the original raw files were restored so recorded hashes still match.

**Tests:** developer-written synthetic fixtures in `tests/test_timetable_clashes.py` (gate level
and conversation level, using real School-reference pairs). They are not evaluation evidence
and are kept outside the frozen sets. `tests/test_backend.py` was updated for the Repeating tab
added in commit 58ba4ca.

**Rerun decision:** no rerun needed.

## 2026-10-01: Test set v1 (School-reference labels) adopted for the benchmark comparison

**What:** `experiments/evaluation/test_set_v1/` holds a 139-case test set supplied by the
developer, frozen by SHA-256 (`freeze.json`), with a plan (`PLAN.md`), a runner
(`scripts/run_test_set_v1.py`), a scorer (`scripts/score_test_set_v1.py`), a retrying driver for
the Gemini arms (`scripts/run_test_set_v1_llm.sh`) and MATLAB figures (`matlab/make_figures.m`).
Labels are the School of EIE registration reference (Admin Manager, 2026-09-30), adopted; no
named independent reviewer. Ambiguity levels are the three stored phrasings per case.
Developer decisions: headline on all 139 cases (held-out and development also reported); one
paced Gemini run per case (not three).

**Code change made before any LLM result existed:** `AdvisorRequest` gained an optional
`manual_review_reasons` list, passed to the eligibility gates alongside the reasons the engine
detects in the message text. The 20 discretion cases carry these reasons in the student profile;
the rules-only arm and the LLM arms already receive the profile, so without this field CurricuPath
alone could not see them (information parity). Found on the 36 development cases.

**Finding, not fixed:** at the medium level CurricuPath reads all three templates ("Is X open to
me given what I have completed?", "Am I allowed to register for X?", "I study P. Can I do X this
year?") as module-information requests, so it gives no eligibility decision (Macro-F1 0.00).
The parser was not changed after seeing these results. Medium and high levels contain only 3
and 4 sentence templates, so each level measures coverage of a few wordings, not ambiguity in
general; this must be stated wherever the per-level results appear.

**Rerun decision:** pending the developer's decision on whether to fix the parser and, if so,
how to report a post-fix run (it would no longer be a clean held-out result on these wordings).

## 2026-10-01 (later): Eligibility-intent wording widened after the test set v1 medium-level result

**Reason:** Developer instruction ("fix it") after test set v1 showed CurricuPath giving no
eligibility decision at the medium level (Macro-F1 0.000) and at half of the high level (0.350):
registration/permission wording ("allowed to register for", "open to me", "sign up for",
"enrol in", "can I do X", "want to take X, is that ok") was parsed as module information or a
course search. `app/advisor/intent.py` now treats these as eligibility questions, with guards so
"can I do anything/better/about..." is not captured. Tests added in `tests/test_intent.py`.

**Disclosure:** this change was made after seeing test set v1 results on these wordings. The
post-fix CurricuPath scores at medium and high (0.896 and 0.900) are therefore
**development-informed**, not clean held-out results. The pre-fix outputs and scores are
preserved in `test_set_v1/results/pre_fix_2026-10-01/` and must be reported alongside. A clean
measurement needs new, unseen phrasings (test set v2).

**Affected outputs:** CurricuPath arms of test set v1 re-run at all levels; rules-only unchanged
(reads no question). LLM baselines not yet run, so unaffected.

## 2026-10-02: Test set v1 baseline runs, subset and model

**What was run:** the two language-model baselines (`handbook_rag`, `structured_rules_llm`) on a
frozen **40-case stratified subset** of test set v1 (`subset_40.json`, drawn from the frozen
60-case `subset_60.json`, fixed seed 20261002, chosen before any baseline result was read:
14 eligible, 20 ineligible, 6 manual-review; 17 scenario types), at all three phrasing levels,
one run per case. CurricuPath, its no-clarification ablation and rules-only ran all 139 cases
and are also scored on the same 40 (`subset40` split) for the paired comparison.

**Developer decisions:** 40 cases instead of 139 to limit cost and quota; one pass instead of
three; model **`gemini-3.5-flash-lite`** instead of the pinned `gemini-3.6-flash`, because the
pinned model's free-tier quota allowed only a handful of calls a day and 503 "high demand"
refusals blocked the rest. A first partial set from the pinned model (9 cases) is archived in
`results/partial_gemini-3.6-flash_free_tier/` and is not used. Billing was unlinked after the
runs started, so the notional spend ledger (about $1.0, `results/spend_ledger.json`) may not
reflect charges.

**Consequences for what can be claimed:**
- The baseline scores describe **this lite model**. A stronger model could score higher, so
  they must not be presented as a ceiling for LLM approaches.
- With 40 cases and 6 in the manual-review class, intervals are wide (about +/-0.10 to 0.15
  Macro-F1). Small gaps between CurricuPath and rules-only are not conclusive.
- CurricuPath's medium and high scores were measured after the parser fix of 2026-10-01 and are
  development-informed. Pre-fix results are in `results/pre_fix_2026-10-01/`.
- Labels are the School registration reference, adopted, without a named independent reviewer.
- Both baselines received the same clash rules and the student's declared review reasons as
  CurricuPath; the structured-rules arm was given the grid clash rules, the RAG arm was not
  (it retrieves handbook text only).

**Provider failures:** none recorded in the scored runs (0 across all 15 arm/level cells).

## 2026-10-02 (later): School-grid requirements enabled for deterministic post-fix runs

**FACT - reason:** Test set v1 exposed School-reference prerequisite/corequisite requirements
that the runtime handbook-rule path did not execute. `PHYS2007A` had no prerequisite row in
`data/processed/rules.csv`; `ELEN2003A` used the handbook's alternative mathematics codes rather
than the registration grid's exact requirement. The deterministic service now has a default-off
`SCHOOL_GRID_REQUIREMENTS_ENABLED` feature gate. When enabled, it loads
`data/rules/grid_rules.json` and replaces the target/programme's handbook prerequisite and
corequisite expressions with the School registration-grid expressions, including explicitly
empty lists. Every failed grid requirement cites `EIE_REG_GRID_2026`, its sheet, and the EBE page
when a corresponding handbook rule exists.

**FACT - TS104 cause:** `LEGACY_RULE_CODES` was not rewriting completed student facts during
prerequisite evaluation. The pre-fix eligible decision came from `PRE_ELEN2003` itself, whose
handbook condition accepts `MATH1048A` as an alternative to `MATH1042A`. The School-grid mode
requires `MATH1042A` specifically, so a planned `MATH1042A` does not satisfy the prerequisite.
The legacy mapping remains intact for interpreting legacy codes in School-reference inputs.

**FACT - unresolved evidence detail:** `scripts/build_review_labels.py` treats completed
`MATH1048A` as satisfying `MATH1042A`, while frozen test case `TS104` and its adopted expected
reason require completed `MATH1042A`. This implementation follows the frozen School-reference
key as directed, without changing either source artifact. Written School confirmation of whether
that equivalence should apply to student completion facts remains desirable.

**FACT - files changed:** `.env.example`, `app/advisor/eligibility.py`, `app/backend.py`,
`app/config.py`, `app/main.py`, `scripts/run_test_set_v1.py`,
`scripts/score_test_set_v1.py`, `tests/test_school_grid_requirements.py`, and this append-only
deviation entry. New outputs are under
`experiments/evaluation/test_set_v1/results_post_grid_final/`; existing raw outputs and frozen
case files were not edited. `results_post_grid/` is a superseded intermediate engineering run
that did not yet treat an explicitly empty grid list as replacing the handbook requirement;
it must not be reported as the final post-fix result.

**FACT - affected cases:** Across the deterministic arms and all three stored phrasing levels,
12 distinct cases changed and every change moved to the adopted reference label: `TS010`,
`TS012`, `TS015`, `TS046`, `TS047`, `TS065`, `TS066`, `TS067`, `TS076`, `TS095`, `TS104`, and
`TS121`. There were 108 arm/level decision changes and zero regressions. `TS095`, `TS104`, and
`TS121` are ineligible at all three levels with cited School-grid reasons.

**FACT - post-fix full-set results:** Rules-only Macro-F1 changed from 0.9310 to 1.0000 at each
of the three levels. CurricuPath changed from 0.9087/0.8965/0.8996 to
0.9800/0.9690/0.9720 at low/medium/high. CurricuPath without clarification has the same values.
The unsafe rate changed from 7/90 to 0/90 for every deterministic arm/level cell.

**FACT - interpretation:** These post-change scores are **DEVELOPMENT-INFORMED** because the fix
was made after inspecting test set v1 outcomes. The School registration reference is encoded by
the grid-enabled engine, so agreement demonstrates faithful encoding, not independent accuracy
or academic validation. The reference remains adopted from a single School source with no named
independent reviewer.

**ASSUMPTION:** The School grid replaces, rather than augments, handbook prerequisite/corequisite
lists whenever the grid contains a target/programme entry; an empty grid list therefore removes
the corresponding handbook constraint.

**PROPOSED - rerun decision:** Preserve pre-fix outputs as the clean historical run and retain
the new post-grid outputs as development-informed engineering verification. Use a newly frozen,
unseen test set for any future comparative accuracy claim.

## 2026-10-02 (later): Grid-evidence parity rerun for the two LLM arms

**DECISION - before rerun:** The post-grid deterministic engine uses School registration-grid
prerequisite/corequisite requirements, whereas the existing Handbook RAG and structured-rules
LLM runs did not receive those requirements. The old LLM outputs remain untouched and are not
pooled with the new outputs. A separate, explicitly grid-aware run will score the same frozen
`subset_40.json` cases at low, medium, and high phrasing levels, with one run per case for each
LLM arm. The other deterministic results will be the already-recorded post-grid runs scored on
the same 40 cases.

**DECISION - equalized facts:** Before generation, both LLM arms will receive an identical,
case-targeted evidence passage from `data/rules/grid_rules.json`, keyed by programme and target
course and citing `EIE_REG_GRID_2026` plus its workbook sheet. The structured-rules arm will
additionally receive the full School-grid prerequisite/corequisite table, alongside the existing
structured rules, clash rules, and evidence-state table. Handbook RAG retains its frozen prompt
and vector-retrieved handbook evidence, with the grid passage added to its evidence list. This is
a grid-augmented RAG baseline, not the original handbook-only baseline. The two LLM arms still
differ in access to the full structured rule table; their per-arm configuration and raw evidence
are retained in a new output directory.

**DECISION - retrieval freeze:** The earlier `handbook_rag` raw observations contain complete
retrieved-chunk records for every case in `subset_40.json` at all three wording levels. The rerun
will reuse those exact handbook chunks and record their SHA-256 hashes, rather than calling the
hosted embedding service again. Only the grid evidence is newly added to each model payload.

**DECISION - spend/output controls:** New outputs and a dedicated spend ledger will be stored
under `experiments/evaluation/test_set_v1/results_school_grid_llm/`; the existing results,
frozen case files, labels, profiles, questions, and prompts are not overwritten. The model-call
budget is capped at USD 3.00 using the runner's conservative per-call ceiling. Any partial run
will be reported as incomplete, not silently combined with prior observations. This is one run
per case, not the three-run protocol used in the separate evaluation plan. Pin the model from the
six historical baseline run configs (`gemini-3.5-flash-lite`) rather than the current `.env`
default, so the comparison does not silently change model. The preflight confirms the frozen
retrieval cache covers all 40 cases at all three levels; matching grid requirement rows exist for
24 of the 40 cases, and the remaining cases retain the same retrieved handbook evidence used by
the deterministic engine when no grid row applies.

**INTERPRETATION:** The rerun addresses the known input-information mismatch; it does not remove
the circularity of comparing rules-only output with labels derived from the registration grid,
does not constitute independent academic validation, and remains development-informed because
the frozen cases and outcomes have already been inspected. Continue to call rules-only agreement
faithful encoding of the School registration reference, not independent accuracy. Preserve and
report the prior no-grid LLM results as historical context only; compare them separately to show
the effect of adding grid evidence, without presenting that change as a clean unseen-test result.

**OPEN / follow-up:** The five post-grid cases that changed from ineligible to eligible require
School spot-checking: `TS010`, `TS015`, `TS046`, `TS065`, and `TS067`, all for `ELEN3017A`
(EFA03 in TS010/TS015/TS067; EFA04 in TS046/TS065). The matching grid rows list no
prerequisite/corequisite entries, so ask the School to confirm that an empty row means no
registration requirement. The eight previously observed malformed CurricuPath answers associated
with single-reply cases remain unresolved; this grid-evidence rerun does not repair or conceal
them. The TS104 disagreement between the generator's MATH1048A equivalence and the frozen key
also remains referred to the School.

**FACT - rerun outcome:** All 120 grid-aware Handbook-RAG observations completed (40 cases at
each of three wording levels). The structured-rules LLM completed only 7/40 low-level cases, then
received Gemini HTTP 429 quota refusals; medium and high produced zero observations. No retry was
made after quota refusal. The provider error prevented completion; it was not caused by the USD
3.00 safety cap.

**FACT - paired subset results:** On `subset40`, grid-aware Handbook RAG Macro-F1 was
0.6134 [0.4238, 0.7621], 0.5491 [0.3830, 0.6941], and 0.5046 [0.3356, 0.6521] at low/medium/high
wording, with unsafe false positives 9/26, 2/26, and 3/26. Compared with historical no-grid RAG,
the number matching the adopted reference changed 15->24, 13->22, and 8->21; correct decisions
changed to incorrect in 4, 1, and 0 cases, respectively. This difference is reference-informed
and development-informed, not an independent accuracy estimate. Structured-rules metrics are
incomplete and must not be treated as comparable 40-case scores.

**FACT - run accounting:** The isolated ledger records USD 0.691717 across 130 attempted Gemini
calls. It includes three quota-refused attempts conservatively charged at the per-call ceiling;
this is a ledger estimate, not a billing statement. The USD 3.00 cap was not reached. Reused
handbook retrieval caches avoided any new hosted embedding requests. New raw observations and
scoring outputs are in `experiments/evaluation/test_set_v1/results_school_grid_llm/`; prior raw
results and frozen inputs remain unchanged. The detailed summary is in that directory's
`README.md`.

## 2026-10-03: Structured-rules grid-aware rerun resumed

**FACT:** The append-only structured-rules rerun resumed with the same frozen cases, retrieval
cache, `gemini-3.5-flash-lite` model, prompts, grid evidence, output directory and USD 3.00
ledger cap. Six additional low-wording cases completed, increasing coverage from 7/40 to 13/40.
Gemini then returned HTTP 429 quota exhaustion. Medium and high again produced no observations;
repeated retries were stopped.

**FACT - provisional result:** On the 13 completed low-wording cases, Macro-F1 is 0.4222
[0.2137, 0.5880], balanced accuracy is 0.4381 and unsafe false positives are 2/8. This is an
incomplete convenience sample determined by provider availability and must not be compared with
the complete 40-case arms or used for a performance claim. The dedicated ledger now records an
estimated USD 0.842469 across 139 attempted calls, including six quota-refused attempts charged
at the conservative ceiling. Completion remains blocked by provider quota, not the spend cap.

## 2026-10-02: Clarification test set v2 created and first results

**What:** `experiments/evaluation/clarification_set_v2/` (72 cases, frozen by hash) tests the
clarification step directly: the system lacks a needed student fact, asks, receives one scripted
reply, and is scored on the final decision. Four deterministic conditions (clarify,
no_clarification, assume_absent, oracle). No language model, no cost. Labels are developer-proposed
and pending academic review.

**Fix before freezing:** a single pending module previously accepted only exact phrases ("Completed");
a sentence naming the module ("I have completed MATH2014A") was recognised as a reply but not
understood. It now falls back to the grouped-status parser (`engine.py`, tests added).

**First results (ask cases, n = 33):** clarify 25 correct, 8 unresolved, 0 wrong, 0 unsafe;
no_clarification 0 correct, 33 unresolved; assume_absent 13 correct, 11 wrong, 3 unsafe;
oracle 33 correct. FACT (counts from the raw outputs).

**Flaw found, not fixed in v2:** all 8 clarify misses, and all 8 unnecessary questions on controls,
have one cause: with module history unconfirmed, the clash gate also asks about every listed
clash partner of the target. After the prerequisite or corequisite reply the engine asks that
second question, which the single scripted reply cannot answer. The construction filter only
checked the FIRST question. Per the freeze rule, v2 is not edited; a v3 should either mark listed
clash partners as known or script a second reply. Whether the advisor should ask about clash
partners at all when the student has said nothing about repeating modules is a product decision
to put to the School.

**Reading the results:** `no_clarification` scores 0 because the engine does not read facts given
as text in the first message, not because asking is the only way to get them. Only the paired
comparison clarify vs assume_absent (12 vs 0) and the oracle gap (8 cases) are informative about
the question step itself.

## 2026-10-03: Evidence-sufficiency, abstention and wording recounts (no new runs)

**What:** `scripts/analyse_uncertainty_v1.py` recounts the existing frozen-subset outputs of test
set v1 (40 cases x 3 wordings) by (a) whether the handbook alone can answer the case
(`answerable_from_handbook`), (b) abstention (defer = manual_review_required), (c) wording level.
Outputs in `test_set_v1/results_uncertainty/`. Deterministic systems are shown before and after
the School-grid rules; "after" is development-informed and partly circular.

**FACT (counts):** with the grid rules not loaded, rules-only and CurricuPath score 39/57 on the
cases the handbook cannot answer, with 9 unsupported "eligible" answers; handbook RAG scores
18/63 on answerable and 18/57 on unanswerable cases (unsafe 11 and 19). The pattern "accurate when
evidence is sufficient, wrong when not" is NOT seen for RAG: it is poor in both groups with the
lite model. For deterministic systems the unsafe answers appear only where the handbook is
insufficient; they do not abstain there because they cannot detect missing evidence, only
declared discretion.

**Caveats:** small counts (6 reference needs-review cases per wording); pooled rows repeat the
same 40 cases across wordings, so only per-level rows carry intervals; baselines ran on one
low-cost model and without the grid rules.

## 2026-10-03: Clarification test set v3 (fixes the v2 clash-partner side effect)

**Why:** in v2, 8 of 33 ask cases ended undecided and 8 controls drew a question, all because,
with module history unconfirmed, the clash gate also asks about every listed clash partner of the
target; one scripted reply cannot answer that second question. v2 is kept unchanged.

**What changed in v3:** same design and counts (72 cases: 33 ask, 33 matched controls, 6
irrelevant-unknown controls; same fact types and reply styles). The target's other clash partners
are declared known (`not_completed`) in the student profile, so the only open question is the one
the case is about. Cases are NOT filtered by what the engine does after the reply. Frozen with a
new hash in `clarification_set_v3/freeze.json`. Runner and scorer take `CLARIFICATION_SET`.

**FACT (n = 33 ask cases):** clarify 33 correct, 0 wrong, 0 unresolved, 0 unsafe, 33 questions;
no_clarification 0 correct, 33 unresolved; assume_absent 13 correct, 11 wrong, 9 unresolved, 3
unsafe; oracle 33 correct. Controls and irrelevant cases: 0 unnecessary questions.

**How to read it:** it shows the question/reply mechanism works when exactly one fact is open and
the scripted reply uses wording the parser handles. It is NOT a measure of how well the advisor
does in free conversation: the set was designed after seeing v2, the reply parser was developed in
the same project, and labels are developer-proposed (pending academic review, no independent
reviewer). The guess comparison (13 vs 33) depends on the label mix; the "no_clarification" zero
reflects that the engine does not read facts given as text, not that asking is the only route.
Still open: whether the advisor should ask about clash partners at all when a student has said
nothing about repeating modules (a School question), and what a student should be asked when
several unrelated facts are unknown (the v2 behaviour).

## 2026-10-03: Grid-aware LLM baselines completed (40 cases x 3 wordings)

**What:** the grid-aware re-run in `test_set_v1/results_school_grid_llm/` is now complete. Handbook
RAG (grid evidence added to its prompt context) was finished by an earlier session; the
structured-rules LLM arm, which had 13 of 40 low-level cases, was completed here with the same
model (`gemini-3.5-flash-lite`), prompts and settings recorded in its config files. One run per
case, free tier, notional ledger about $1.9 (billing was unlinked, so nothing was charged).

**FACT (subset of 40, Macro-F1 low / medium / high; unsafe out of 26):** rules-only 1.000 / 1.000 /
1.000 (0 unsafe); CurricuPath 0.983 / 0.973 / 0.973 (0 unsafe); grid-aware Handbook RAG 0.613 /
0.549 / 0.505 (unsafe 9 / 2 / 3); grid-aware structured-rules LLM 0.561 / 0.368 / 0.379 (unsafe
7 / 2 / 1).

**One invalid run:** TS007 at the high wording was a transport failure ("Server disconnected
without sending a response"), recorded as `malformed_or_failed`. The scorer counts it as an
invalid output (2.5 percent of that cell) and it is not retried or removed. It is not classified
as a provider refusal because only 429/503-type errors are.

**Reading the results:** the grid evidence lifts both LLM baselines but they stay far below the
rule-based systems; these gains are not independent because the grid is also the source of the
reference labels. The baselines are one low-cost model with one run per case. The Handbook-RAG
arm is no longer handbook-only. Comparisons with the earlier handbook-only baseline must say so.

## 2026-10-05: Parser reads module statuses stated in the message; clearer clarification wording

**Reason:** live use showed (a) "can I take ELEN4012 having failed ELEN3009?" was answered with a
request for the status of eleven Year 3 modules, ignoring the stated failure; (b) the parser took
the FIRST module code in a message as the module being asked about, so "I failed ELEN3009A. Can I
take ELEN4011A?" was answered about ELEN3009A; (c) a bare "Completed" reply was read by Gemini as a
question about courses and not accepted as the answer; (d) the clarification question did not say
what was missing, why, or what to reply.

**Changes:** the deterministic parser now reads declared statuses from codes ("failed", "did not
pass", "have not completed", "completed", "passed", "currently taking", "plan to take") and fills
the profile's not-completed, completed, current and planned lists; the module being asked about is
the first code that was not just given a status; a reply that is a valid status for the pending
question is always taken as the answer; clarification replies say which module is missing, its
role, what is already met, and point to Profile setup. Module NAMES are not read as declared
statuses; failing a module twice (exclusion) is still not modelled. Gemini cannot set the
not-completed list.

**Affected evaluation outputs:** none. Re-running CurricuPath on all 139 cases at three wordings
(417 case-wordings) after the change gave identical decisions to the reported run. The test
sets contain no declared-status wording. Reported scores stand.

## 2026-10-05 (later): Module titles given a status are read as facts

**Why:** "can I do ELEN4012 if I failed Software Development II" fell back to asking about eleven
modules because only codes were understood as declared statuses.

**Change:** in "can I take ...?"-type questions only, an exact catalogue title that follows a
status phrase ("failed", "completed", "currently taking", "plan to take", or "(failed)" after it)
is rewritten to its code before the message is read (`app/advisor/declared_names.py`); titles that
are not exact or map to more than one module are left untouched, never guessed. When every code in
such a question has been given a status, the target is taken from the title that was asked about.
Career and information questions keep their titles. The reply names the module ("ELEN3009A
(Software Development II)").

**Affected evaluation outputs:** none. CurricuPath and the no-clarification arm were re-run on all
139 cases at three wordings (834 case-wordings) and gave identical decisions to the reported runs.

## 2026-10-05 (evening): "What electives can I take?" is a list question

**Why:** "what electives can I take" matched "can I take" and was routed as a module-eligibility
question with no module, so the advisor asked for a module code. **Change:** a message that asks
about electives, compulsory modules or "which modules" and names no module is a curriculum-list
question (`app/advisor/intent.py`). **Affected evaluation outputs:** none; CurricuPath was re-run
on all 139 cases at three wordings (417 case-wordings) with identical decisions.

## 2026-10-05 (night): Programme named in a question, and programme-specific list answers

**Why:** EE and IE have different electives, but the programme was only read from the profile or
from "EFA03/EFA04" or "electrical engineering ... course/module" wording. "Electrical engineering
students", "I study ...", "EE", "IE" and one-word replies were ignored, and "electrical
engineering" was also read as a career interest, so such questions got interest-based
recommendations. **Change:** the parser reads the programme from those wordings and abbreviations
(upper-case EE/IE only), a programme named in the question wins over the profile and the reply says
so, the "Which programme are you in?" question offers two buttons, and bare programme replies and
the button text are accepted as the answer. **Affected evaluation outputs:** none; CurricuPath and
its no-clarification arm gave identical decisions on all 139 cases at three wordings.

## 2026-10-06: General guard for answers to open questions; elective lists for a named programme

**Why:** a language model had three times overridden a short reply to an open question (a bare
"Completed", a module-name reply, a programme reply) by assigning it an unrelated intent.
**Change:** while a question is open, a message that the offline parser cannot read as a request of
its own is treated as the answer, whatever intent the model guessed; messages the parser does read
as a request ("Show the EFA04 year 4 electives") are not swallowed. Also: "fourth year electrical
engineering electives / elective courses" is read as a programme elective list and not as an interest
match, while "I like electrical engineering, recommend electives..." stays an interest request.
**Affected evaluation outputs:** none; both CurricuPath arms gave identical decisions on all 139
cases at three wordings (834 case-wordings).

## 2026-10-07: Career questions — unknown careers named; Wits careers linked to electives

**Change:** a career the advisor has no evidence for ("Aeronautic Electrical") is now named in the
reply, with no elective recommendation, and the careers Wits lists for EFA03 and EFA04 are shown
instead. Each Wits-listed career is linked to Year 4 electives through
`data/processed/wits_career_elective_links.csv` (career -> existing elective career tags, with a
rationale per row). **These links are developer-proposed and unconfirmed by the School**; every
reply that uses them says so, and the file is the place for the School to correct them.
**Affected evaluation outputs:** none; CurricuPath gave identical decisions on all 417
case-wordings of test set v1.
