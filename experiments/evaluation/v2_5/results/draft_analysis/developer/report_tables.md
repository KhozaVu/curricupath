# Evaluation results tables

> **DRAFT: developer-side labels, not independent evidence.** Do not cite these numbers as results.

Reference: developer_expected_label (NOT independent evidence). Cases scored: 60. Primary run: 1. Intervals: case-level bootstrap, 10000 resamples, seed 20260918.

## Table 1. Agreement with reference labels

| System | Macro-F1 (95% CI) | Balanced accuracy (95% CI) | Accuracy | Invalid outputs |
| --- | --- | --- | --- | --- |
| CurricuPath | 0.89 (0.81 to 0.95) | 0.83 (0.76 to 0.91) | 0.83 | 10 |
| Handbook RAG | 0.71 (0.60 to 0.81) | 0.72 (0.62 to 0.81) | 0.72 | 0 |
| Structured-rules LLM | 0.80 (0.69 to 0.89) | 0.80 (0.70 to 0.89) | 0.80 | 0 |
| Rules only | 1.00 (1.00 to 1.00) | 1.00 (1.00 to 1.00) | 1.00 | 0 |
| CurricuPath (no clarification) | 0.89 (0.81 to 0.95) | 0.83 (0.76 to 0.91) | 0.83 | 10 |

## Table 2. Error types

| System | Unsafe false positive | Overly conservative | Correct escalation | Unsafe overconfidence | Unnecessary escalation |
| --- | --- | --- | --- | --- | --- |
| CurricuPath | 0% (0/40) | 0% (0/20) | 100% (20/20) | 0% (0/20) | 0% (0/40) |
| Handbook RAG | 28% (11/40) | 30% (6/20) | 100% (20/20) | 0% (0/20) | 0% (0/40) |
| Structured-rules LLM | 12% (5/40) | 30% (6/20) | 100% (20/20) | 0% (0/20) | 2% (1/40) |
| Rules only | 0% (0/40) | 0% (0/20) | 100% (20/20) | 0% (0/20) | 0% (0/40) |
| CurricuPath (no clarification) | 0% (0/40) | 0% (0/20) | 100% (20/20) | 0% (0/20) | 0% (0/40) |

## Table 3. Paired differences (case-level bootstrap)

| Comparison | Metric | Difference | 95% CI | Reading |
| --- | --- | --- | --- | --- |
| CurricuPath minus Handbook RAG | macro_f1 | +0.18 | +0.03 to +0.32 | first arm higher (interval excludes 0) |
| CurricuPath minus Handbook RAG | balanced_accuracy | +0.12 | -0.03 to +0.26 | inconclusive (interval includes 0) |
| CurricuPath minus Structured-rules LLM | macro_f1 | +0.09 | -0.04 to +0.22 | inconclusive (interval includes 0) |
| CurricuPath minus Structured-rules LLM | balanced_accuracy | +0.03 | -0.10 to +0.16 | inconclusive (interval includes 0) |
| CurricuPath minus Rules only | macro_f1 | -0.11 | -0.19 to -0.05 | first arm lower (interval excludes 0) |
| CurricuPath minus Rules only | balanced_accuracy | -0.17 | -0.24 to -0.09 | first arm lower (interval excludes 0) |
| CurricuPath minus CurricuPath (no clarification) | macro_f1 | +0.00 | +0.00 to +0.00 | identical (no difference in any resample) |
| CurricuPath minus CurricuPath (no clarification) | balanced_accuracy | +0.00 | +0.00 to +0.00 | identical (no difference in any resample) |

## Table 4. Latency and repeatability

| System | Median ms | 95th percentile ms | Same decision in 3 runs | Decision-change rate |
| --- | --- | --- | --- | --- |
| CurricuPath | 5 | 13 | n/a | n/a |
| Handbook RAG | 1606 | 1932 | n/a | n/a |
| Structured-rules LLM | 1822 | 2204 | n/a | n/a |
| Rules only | 1 | 1 | n/a | n/a |
| CurricuPath (no clarification) | 5 | 6 | n/a | n/a |

## Limits of these tables

- Prototype study: with about 15 cases per class, intervals are wide. Report `inconclusive` rather than reading small differences as real.
- Every disagreement still needs a `failure_category` in `case_decisions.csv` (source, label, rule_encoding, parser, condition_evaluation, clarification, baseline_retrieval, generation, explanation).
- Not computed here: Material-reason completeness: needs reviewer-approved reasons matched to each answer.
- Not computed here: Reviewer agreement (pre-adjudication): needs the independent reviewers' raw labels.
- Not computed here: Grounding and claim-support metrics (Experiment B): scored by a separate procedure.
- Not computed here: Ambiguity ablation (Experiment C): scored by a separate procedure.
