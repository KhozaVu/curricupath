# Label-set sensitivity

> **DRAFT: developer-side labels, not independent evidence.** Both label sets are developer-side; neither is independent evidence.

This shows how far each result depends on which reading of the rules is used as the answer key. The main difference is whether a corequisite that is only *planned* counts as satisfied (Rule 1.9 of the Senate Rules).

## Label sets

- **developer**: developer_expected_label (NOT independent evidence)
- **briefing**: briefing_draft: developer-side Senate Rules briefing labels, unattributed (NOT independent evidence)

Agreement between the two sets: 78% of 60 cases, Cohen's kappa 0.67. They differ on 13 cases.

| developer \ briefing | eligible | ineligible | manual_review_required |
| --- | --- | --- | --- |
| eligible | 7 | 0 | 13 |
| ineligible | 0 | 20 | 0 |
| manual_review_required | 0 | 0 | 20 |

## Macro-F1 by label set

| System | developer | briefing | Change |
| --- | --- | --- | --- |
| CurricuPath | 0.89 (0.81 to 0.95) | 0.65 (0.51 to 0.76) | -0.24 |
| Handbook RAG | 0.71 (0.60 to 0.81) | 0.51 (0.39 to 0.62) | -0.21 |
| Structured-rules LLM | 0.80 (0.69 to 0.89) | 0.66 (0.52 to 0.78) | -0.14 |
| Rules only | 1.00 (1.00 to 1.00) | 0.76 (0.65 to 0.86) | -0.24 |
| CurricuPath (no clarification) | 0.89 (0.81 to 0.95) | 0.65 (0.51 to 0.76) | -0.24 |

## Does the comparison verdict change?

| Comparison (macro-F1) | developer | briefing |
| --- | --- | --- |
| CurricuPath minus Handbook RAG | +0.18: first arm higher | +0.14: inconclusive |
| CurricuPath minus Structured-rules LLM | +0.09: inconclusive | -0.01: inconclusive |
| CurricuPath minus Rules only | -0.11: first arm lower | -0.11: first arm lower |
| CurricuPath minus CurricuPath (no clarification) | +0.00: identical | +0.00: identical |

## Cases where the label sets differ

| Case | developer | briefing |
| --- | --- | --- |
| ELIG001 | eligible | manual_review_required |
| ELIG002 | eligible | manual_review_required |
| ELIG003 | eligible | manual_review_required |
| ELIG005 | eligible | manual_review_required |
| ELIG006 | eligible | manual_review_required |
| ELIG007 | eligible | manual_review_required |
| ELIG010 | eligible | manual_review_required |
| ELIG013 | eligible | manual_review_required |
| ELIG014 | eligible | manual_review_required |
| ELIG015 | eligible | manual_review_required |
| ELIG018 | eligible | manual_review_required |
| ELIG019 | eligible | manual_review_required |
| ELIG020 | eligible | manual_review_required |
