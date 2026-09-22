# Evaluation v2.5 Data Dictionary

## Eligibility cases

`eligibility_cases.csv` contains one row per frozen synthetic case.

| Field | Meaning |
| --- | --- |
| `case_id` | Stable identifier |
| `author_source` | `developer_drafted` or `reviewer_drafted` |
| `question` | Initial user wording |
| `target_course_code` | Candidate module used by the rules-only arm |
| `student_profile_json` | Programme and completed/current/planned module facts |
| `scenario_type` | Pre-declared scenario category |
| `reference_label` | `eligible`, `ineligible`, `manual_review_required`, or blank pending review |
| `expected_material_reasons_json` | Independently approved material reasons |
| `clarification_permitted` | Whether CurricuPath may ask one clarification |
| `scripted_reply` | Exact reply supplied after that clarification |
| `consolidated_noninteractive_input` | Initial question plus the same scripted fact for non-interactive arms |
| `reviewer_ids` | Semicolon-separated study identifiers |
| `approval_state` | `pending_academic_review`, `approved`, or `rejected_with_reason` |

## Retrieval development cases

These cases select `top_k` and must never appear in the evaluation set.
`gold_chunk_ids` uses semicolon-separated `evaluation_handbook` item IDs.

## Missing values

Blank means not yet supplied or not applicable. It never means false. JSON values must
parse successfully. Official runs require all blocking review and configuration fields.
