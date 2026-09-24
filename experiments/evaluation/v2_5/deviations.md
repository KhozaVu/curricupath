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

