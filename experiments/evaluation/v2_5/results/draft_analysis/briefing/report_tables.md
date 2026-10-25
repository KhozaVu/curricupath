# Evaluation results tables

> **DRAFT: developer-side labels, not independent evidence.** Do not cite these numbers as results.

Reference: briefing_draft: developer-side Senate Rules briefing labels, unattributed (NOT independent evidence). Cases scored: 60. Primary run: 1. Intervals: case-level bootstrap, 10000 resamples, seed 20260918.

## Table 1. Agreement with reference labels

| System | Macro-F1 (95% CI) | Balanced accuracy (95% CI) | Accuracy | Invalid outputs |
| --- | --- | --- | --- | --- |
| CurricuPath | 0.65 (0.51 to 0.76) | 0.70 (0.61 to 0.79) | 0.62 | 10 |
| Handbook RAG | 0.51 (0.39 to 0.62) | 0.54 (0.38 to 0.70) | 0.55 | 0 |
| Structured-rules LLM | 0.66 (0.52 to 0.78) | 0.77 (0.68 to 0.85) | 0.68 | 0 |
| Rules only | 0.76 (0.65 to 0.86) | 0.87 (0.81 to 0.92) | 0.78 | 0 |
| CurricuPath (no clarification) | 0.65 (0.51 to 0.76) | 0.70 (0.61 to 0.79) | 0.62 | 10 |

## Table 2. Error types

| System | Unsafe false positive | Overly conservative | Correct escalation | Unsafe overconfidence | Unnecessary escalation |
| --- | --- | --- | --- | --- | --- |
| CurricuPath | 25% (13/53) | 0% (0/7) | 61% (20/33) | 39% (13/33) | 0% (0/27) |
| Handbook RAG | 40% (21/53) | 43% (3/7) | 61% (20/33) | 39% (13/33) | 0% (0/27) |
| Structured-rules LLM | 23% (12/53) | 0% (0/7) | 61% (20/33) | 39% (13/33) | 4% (1/27) |
| Rules only | 25% (13/53) | 0% (0/7) | 61% (20/33) | 39% (13/33) | 0% (0/27) |
| CurricuPath (no clarification) | 25% (13/53) | 0% (0/7) | 61% (20/33) | 39% (13/33) | 0% (0/27) |

## Table 3. Paired differences (case-level bootstrap)

| Comparison | Metric | Difference | 95% CI | Reading |
| --- | --- | --- | --- | --- |
| CurricuPath minus Handbook RAG | macro_f1 | +0.14 | -0.01 to +0.28 | inconclusive (interval includes 0) |
| CurricuPath minus Handbook RAG | balanced_accuracy | +0.16 | -0.02 to +0.35 | inconclusive (interval includes 0) |
| CurricuPath minus Structured-rules LLM | macro_f1 | -0.01 | -0.13 to +0.09 | inconclusive (interval includes 0) |
| CurricuPath minus Structured-rules LLM | balanced_accuracy | -0.07 | -0.18 to +0.04 | inconclusive (interval includes 0) |
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
