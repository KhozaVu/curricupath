# Academic Eligibility Rubric: School Registration Reference v2

This version supplements, and does not overwrite,
`data/raw/review_pack/academic_eligibility_rubric.md`.

## Reference Authority

The primary benchmark is the **School of EIE registration reference (Admin Manager,
2026-09-30)**. It is a single institutional reference used by the School for registration
decisions. It is not independent, multi-reviewer validation. Records adopting this key use
`approval_state = adopted_school_reference`, keep `reviewer_ids` empty, and record the
reference authority above.

## Decision Checks

Evaluate all applicable deterministic constraints and retain every failing reason:

1. Confirm that the target module belongs to the declared programme.
2. Check that every prerequisite is completed.
3. Check that every corequisite is completed, current, or planned concurrently.
4. Check whether the target clashes with a module the student is repeating. A recorded
   timetable clash definitively prevents the target module.
5. Check whether a recorded exclusion prevents the target module.
6. Check that material source evidence is sufficient for the selected reference mode.
7. Return `manual_review_required` when evidence is conflicting, incomplete, discretionary,
   or otherwise cannot safely settle the decision.

The clash check uses the union of the planner's blue cells and the cross-curricular table's
`Time-table Clashes` entries. It applies only to `profile.repeating_modules`; it does not
extend to current or planned modules. A listed clash overrides any statement that the
higher-year course can otherwise be taken.

## Reference Labels

| Label | Use when |
| --- | --- |
| `eligible` | Programme membership and every applicable deterministic condition are satisfied. |
| `ineligible` | A programme, prerequisite, corequisite, timetable-clash, or exclusion rule definitively prevents the module. |
| `manual_review_required` | Institutional evidence or academic discretion cannot safely settle the decision. |

## Material Reason Categories

- `programme_membership`
- `prerequisite`
- `corequisite`
- `timetable_clash`
- `exclusion`
- `evidence_state`
- `academic_discretion`

Clash reasons cite a `CLASH_<REPEATING>_<TARGET>` rule ID, the repeating and target course
codes, source IDs, and the relevant sheet where available.
