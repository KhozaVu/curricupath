# Evaluation Data Dictionary

## Shared Conventions

- Identifiers are stable within evaluation version `curricupath-eval-2026-09-15-v1`.
- Multiple module codes or source IDs are separated by semicolons.
- Boolean CSV values use lowercase `true` and `false`.
- Empty means not applicable or deliberately unspecified, not false.
- `draft_internal` means prepared from the frozen catalogue but not independently
  approved.
- `pending_academic_review` applies to anchor expectations awaiting an appropriate
  academic reviewer.
- `approved` may be assigned only after the named review has occurred.
- `rejected_with_reason` requires a note and a new version before final measurement.

## `rule_cases.csv`

| Field | Meaning |
| --- | --- |
| `case_id` | Stable case identifier |
| `category` | Gate or structural-rule condition exercised |
| `operation` | `eligibility` for executable module eligibility or `rule_condition` for aggregate structural review |
| `programme_code` | Declared EFA03/EFA04 programme, if applicable |
| `target` | Candidate module, year target, branch target, or selection group |
| `completed_modules` | Modules declared completed before registration |
| `current_modules` | Modules currently being taken |
| `planned_modules` | Modules proposed concurrently |
| `expected_outcome` | Human-readable expected class |
| `expected_eligible` | Structured eligibility result for `eligibility` rows |
| `expected_needs_clarification` | Whether missing user state should trigger clarification |
| `expected_failed_gate` | First expected failed gate in the fixed gate order |
| `expected_rule_id` | Rule principally exercised by the case |
| `source_basis` | Source identifier supporting the expected rule |
| `anchor_case` | Whether the case belongs to the independent 15-case anchor set |
| `review_status` | Current independent-review state |
| `academic_reviewer` | Reviewer name or approved study code; blank until reviewed |
| `notes` | Construction details, assumptions, or required interpretation checks |

The `rule_condition` rows cover programme selection, progression, and elective
counts that are not yet exposed as standalone eligibility calls. They must not be
counted in executable engine accuracy until a corresponding evaluator exists.

## `intent_cases.csv`

| Field | Meaning |
| --- | --- |
| `prompt_id` | Stable prompt identifier |
| `category` | Wording or interaction class |
| `prompt` | Frozen synthetic user text |
| `expected_intent` | Expected intent from the current controlled intent vocabulary |
| `expected_module_code` | Explicit code expected from extraction; suffix completion may occur later in resolution |
| `expected_programme_code` | Explicit programme expected from the prompt |
| `expected_year_of_study` | Explicit or conventionally stated year |
| `expected_requirement_type` | `compulsory`, `elective_pool`, or blank |
| `expected_interests` | Canonical controlled interest tags |
| `expected_career_preferences` | Canonical controlled career tags |
| `expected_workload_preference` | `light`, `moderate`, `heavy`, or blank |
| `expected_difficulty_preference` | `beginner`, `intermediate`, or blank |
| `expected_format_preference` | Expected delivery format, if explicit |
| `clarification_expected` | Whether end-to-end advisor handling should ask a focused question |
| `context_required` | Whether the row must be run with predefined pending session context |
| `review_status` | Current review state |
| `notes` | Resolution boundary or interpretation notes |

Intent extraction and end-to-end clarification are scored separately. A prompt may
have a correct standalone intent but still require module-name resolution.

## `grounding_cases.csv`

| Field | Meaning |
| --- | --- |
| `case_id` | Stable grounding-case identifier |
| `category` | Scope, staff, materials, missing evidence, or public rating |
| `question` | Frozen synthetic question |
| `item_id` | Module code or public-course ID |
| `expected_response_class` | `supported_answer` or a qualified missing-evidence response |
| `expected_facts_json` | Atomic source-supported facts expected in the response |
| `allowed_source_ids` | Sources permitted to support material claims |
| `prohibited_claims` | Facts that must not be invented or presented as current |
| `evidence_state` | `verified`, `verified_snapshot`, `partial`, or `missing` |
| `review_status` | Current review state |
| `reviewer` | Reviewer name or approved study code |
| `notes` | Evidence limitations and interpretation details |

Public ratings are historical snapshots at their recorded access dates. They must
not be described as current without a new source audit.
