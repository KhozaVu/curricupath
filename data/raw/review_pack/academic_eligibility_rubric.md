# Academic Eligibility Labelling Rubric

## Decision Order

For each case, apply the following checks in order:

1. Confirm that the target module belongs to the declared programme.
2. Check that all prerequisites are completed.
3. Check that corequisites are completed, current, or planned concurrently where
   the rule allows it.
4. Check whether a recorded exclusion prevents the candidate module.
5. Check that material source evidence is verified and sufficient.
6. Identify whether the outcome needs academic discretion instead of a deterministic
   decision.

## Reference Labels

| Label | Use when |
| --- | --- |
| `eligible` | The module is in the programme, all material rules are satisfied, and verified evidence supports a decision. |
| `ineligible` | A verified programme, prerequisite, corequisite, or exclusion rule definitively prevents the module. |
| `manual_review_required` | The evidence is incomplete, disputed, superseded, invalid, conflicting, or the decision requires academic discretion. |

Do not use `manual_review_required` merely because a rule is difficult. Use it only
when the approved evidence cannot settle the case safely.

## Clarification-Permitted Cases

Some cases have `clarification_permitted = true`. For these cases, use the fact in
`scripted_reply` when determining the final reference label. The reply supplies a
neutral missing student fact; it does not indicate the intended outcome.

The reference label is still only one of the three labels above. Do not enter
`needs_clarification` in `reference_label`.

## Completing A Case

In `eligibility_cases_blinded.csv`, complete only these fields:

| Field | Required format |
| --- | --- |
| `reference_label` | `eligible`, `ineligible`, or `manual_review_required` |
| `expected_material_reasons_json` | A valid JSON array of short, source-backed reasons |
| `reviewer_ids` | Your assigned reviewer ID, for example `AR01` |
| `approval_state` | `approved` once you are satisfied with the label |

Example for a failed prerequisite:

```json
["PRE_MATH1049: MATH1048A is required before MATH1049A and is not listed as completed (EBE_2026)."]
```

Example for an eligible case:

```json
["Programme membership and all recorded prerequisite/corequisite conditions are satisfied (EBE_2026)."]
```

Example requiring academic review:

```json
["The recorded source evidence is insufficient to resolve this case; academic review is required."]
```

## Disagreement and Corrections

If two reviewers disagree, do not overwrite either record. Retain both reviewer IDs
and send the case ID, labels, reasons, and source references for adjudication. The
adjudicated decision must be recorded separately by the evaluation lead.

If the target module, profile JSON, or rule evidence is unusable, set
`approval_state` to `rejected_with_reason` and describe the issue in the JSON reason
field. Do not invent missing curriculum facts.
