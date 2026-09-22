# CurricuPath Academic Eligibility Review Pack

## Purpose

This pack supports independent academic labelling of synthetic EFA03/EFA04
eligibility cases. It establishes the reference outcome against which
CurricuPath will later be evaluated.

This is **not** a review of whether the chatbot response sounds helpful. Please
decide the academically correct outcome from the supplied curriculum evidence.
No CurricuPath output, developer expected label, ranking score, or model result is
included in this pack.

## Contents

| File | Use |
| --- | --- |
| `eligibility_cases_blinded.csv` | The 60 cases to label. |
| `academic_eligibility_rubric.md` | The label definitions and review procedure. |
| `curriculum_modules.csv` | Programme membership, year, credits and requirement type. |
| `curriculum_rules.csv` | Source-cited prerequisite, corequisite and exclusion conditions. |
| `source_register.csv` | Source verification status and location information. |
| `external_prerequisite_audit.csv` | Verified external prerequisite references used by rules. |
| `EBE_eBook_2026.pdf` | The official 2026 EBE handbook used for curriculum memberships and rules. |
| `ambiguity_cases_blinded.csv` | The 13 clarification and wording cases, without intended outcomes. |
| `case_coverage_matrix.md` | Every decision behaviour the approved review set must cover. |
| `uncovered_rule_targets.csv` | Material rule targets needing reviewer-drafted concealed cases. |
| `reviewer_concealed_case_template.csv` | 30 blank authoring rows: satisfied and failure/review paths for each uncovered target. |

The primary institutional source is `EBE_eBook_2026.pdf`. Its page mapping and
source status are recorded under `EBE_2026` in `source_register.csv`.

## Independence Rules

1. Do not open the production app or ask the developers for CurricuPath's result
   before you complete a case label.
2. Do not view the source `eligibility_cases.csv` while labelling; it contains a
   developer expectation that is deliberately excluded here.
3. Base each label on the listed student facts, the curriculum rules, and the
   verified source evidence only.
4. Record uncertainty honestly. If the institutional evidence is incomplete,
   conflicting, invalid, or the outcome requires academic discretion, use
   `manual_review_required`.
5. The cases are synthetic. Do not add real student numbers, marks, names, or
   transcripts to the sheet.

## What To Return

Return the completed `eligibility_cases_blinded.csv` without adding a developer
label column. Also return `ambiguity_cases_blinded.csv` if you review the
clarification cases. A developer will merge only the reviewer-labelled fields into
the frozen evaluation files and retain the original blinded copies.

If you need to reject a poorly formed case instead of labelling it, set
`approval_state` to `rejected_with_reason` and explain why in
`expected_material_reasons_json`.

## Concealed Case Drafting

Where `reviewer_concealed_case_template.csv` contains a row, draft the question and
synthetic profile yourself from the supplied rule and handbook evidence. Do not ask
developers to suggest completed modules, a label, or an expected explanation. Keep
both the satisfied-path and failure/review-path rows only when they are meaningful
for that rule. Return the completed template as a separate file.

## Time and Questions

Record your confirmed hours and independent-review role only after agreeing to
participate, following [evaluation_reviewer_request.md](../../../../docs/evaluation_reviewer_request.md).
Questions about a rule's source are welcome; developers should provide the source
location, not an answer or a preferred label.
