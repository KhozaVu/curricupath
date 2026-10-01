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
