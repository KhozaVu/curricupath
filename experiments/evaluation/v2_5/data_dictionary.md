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

## Ambiguity cases (Experiment C)

`ambiguity_cases.csv` holds one row per query. Reviewer-authored fields start as
`pending_independent_review` and are filled only by the independent reviewer, before any system
run and without seeing system output. Developers must not fill them.

| Field | Meaning |
| --- | --- |
| `case_id` | Stable identifier |
| `query` | The exact first message sent to the advisor |
| `student_profile_json` | Programme and module facts supplied with the query (`{}` when none) |
| `intended_interpretation` | Developer-drafted intent the query is meant to express. Used for interpretation scoring only |
| `ambiguity_type` | Scenario category, kept so paraphrases are not counted as independent evidence |
| `required_clarification` | `true` if a careful advisor should ask before answering, otherwise `false` (reviewer) |
| `fixed_simulated_reply` | Exact reply sent once if the system asks a question. Required when `required_clarification` is `true` (reviewer) |
| `neutral_fallback_reply` | Reply sent once if the system asks a further question. Pre-declared and identical for every case |
| `accepted_final_outcomes_json` | JSON list of acceptable final outcomes (reviewer); format below |
| `approval_state` | `pending_academic_review`, `approved`, or `rejected_with_reason` |

Conversation protocol: the query is sent once; if the system asks for clarification the fixed reply
is sent once; if it then asks something further the neutral reply is sent once; any further question
leaves the case unresolved. No reply is improvised. The no-clarification arm sends the query only.

### Accepted outcomes

A JSON list; the final response is correct if it matches **any** item. An item is an object whose
keys must **all** match:

| Key | Matches | Example |
| --- | --- | --- |
| `intent` | The advisor's interpretation of the request. One of: module_information, eligibility, curriculum_list, programme_information, programme_comparison, credit_information, profile_courses, public_course_search, career_path, greeting, help, unknown | `"module_information"` |
| `module_code` | The module the final answer is about | `"ELEN3012A"` |
| `status` | The advisor's response status. Optional | `"out_of_scope"` |

Unless an item names `status`, the system must actually have answered: a response that is still
asking a question, or that refused the request, is never counted as correct. Name
`status: "out_of_scope"` only where a refusal is the right outcome. Unknown keys are rejected.
Example: `[{"intent": "module_information", "module_code": "ELEN3012A"}, {"intent": "module_information", "module_code": "ELEN3013A"}]`.

Metrics that need reviewer fields (appropriate, unnecessary and silent-guess rates, accepted
outcomes, second-attempt success) are reported as not scorable until those fields exist.
