# Required Academic Review Coverage

It is not feasible or useful to enumerate every combination of 101 modules and
five possible fact states. This matrix defines the complete set of **decision
behaviours** that the review set must cover. A case may satisfy more than one row.

The existing blinded eligibility sheet provides 60 balanced cases. The reviewer
should check that each required behaviour below has at least one approved case and
draft a concealed case for any gap. `uncovered_rule_targets.csv` identifies the 15
material rule targets not represented by the current 60-case target list.

| Decision area | Required case | What the reviewer checks |
| --- | --- | --- |
| Programme | Candidate belongs to EFA03 | Membership permits the next gate. |
| Programme | Candidate belongs to EFA04 | Membership permits the next gate. |
| Programme | Candidate belongs only to the other programme | Definitive ineligibility. |
| Prerequisite | Single completed prerequisite | Deterministic eligibility path. |
| Prerequisite | Single missing prerequisite | Deterministic ineligibility path. |
| Prerequisite | `all_of` all completed | Deterministic eligibility path. |
| Prerequisite | `all_of` one confirmed missing and another unknown | Confirmed failure must settle the decision without unnecessary clarification. |
| Prerequisite | `any_of` one completed alternative | A valid branch must satisfy the rule. |
| Prerequisite | `any_of` all alternatives confirmed missing | Deterministic ineligibility path. |
| Prerequisite | Nested `all_of` / `any_of` expression | Correct branch interpretation. |
| Prerequisite | Programme-year requirement fully completed | Deterministic eligibility for fourth-year requirements. |
| Prerequisite | Programme-year requirement with one confirmed missing module | Deterministic ineligibility. |
| Prerequisite | Programme-year requirement with incomplete history | A targeted clarification is appropriate before the final simulated fact. |
| Corequisite | Required module already completed | Rule is satisfied. |
| Corequisite | Required module currently taken | Rule is satisfied where concurrent study is allowed. |
| Corequisite | Required module planned concurrently | Rule is satisfied where concurrent study is allowed. |
| Corequisite | Required module confirmed absent | Deterministic ineligibility. |
| Corequisite | Required module unknown | One focused clarification, followed by the scripted final fact. |
| Corequisite | `any_of` alternatives | At least one valid concurrent route is enough. |
| Exclusion | Exclusion condition present | Deterministic ineligibility. |
| Exclusion | Exclusion condition not present | Candidate may continue to later checks. |
| Exclusion | Exclusion-relevant fact unknown | Clarify only if the unknown can change the outcome. |
| Evidence | Verified module and rule source | The evidence permits a decision. |
| Evidence | Missing, incomplete, disputed, superseded, or invalid material source | `manual_review_required`; no definitive academic decision. |
| Discretion | Transfer credit, exceptional registration, or another declared faculty discretion | `manual_review_required`. |
| Language | Exact module code | Correct target is selected. |
| Language | Module code without suffix or in lower case | Correct known module is selected without guessing. |
| Language | Ambiguous module name or number/letter series | A focused choice question is required. |
| Language | Missing programme for a programme-dependent question | A focused programme question is required. |
| Safety | Out-of-scope request | A fixed supported-scope response; no retrieval or ranking. |

## Case Set Requirements

- Keep at least 15 approved cases for each final label: `eligible`, `ineligible`,
  and `manual_review_required`.
- Retain both EFA03 and EFA04 cases.
- Include cases with each relevant operator: direct module, `all_of`, `any_of`,
  nested combinations, and programme-year membership.
- Keep clarification cases separate from their final three-class label. The reviewer
  records the label after applying the neutral scripted reply.
- Do not replace the blind source sheet with a developer-labelled copy.

## Additional Review Files

- `ambiguity_cases_blinded.csv` contains the 13 wording and clarification cases.
- `uncovered_rule_targets.csv` identifies rule targets for reviewer-drafted
  concealed cases.
- `reviewer_concealed_case_template.csv` provides 30 blank rows covering a
  satisfied path and a failure/review path for each uncovered target.
