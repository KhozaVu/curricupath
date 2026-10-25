# School-Grid-Aware LLM Rerun

Run date: 2026-10-02  
Reference: School of EIE registration reference, adopted from the School's workbooks; no named independent academic reviewer.

## Protocol

This is a separate, development-informed rerun of the two LLM arms on the frozen 40-case
stratified subset (`subset_40.json`), at low, medium, and high wording levels, one run per case.
Both LLMs received the same target-specific prerequisite/corequisite passage from
`data/rules/grid_rules.json` where a matching programme/target row existed, in addition to the
same frozen handbook retrieval chunks as the original runs. Matching grid rows existed for 24 of
40 cases. The other cases had no matching grid requirement row and retained the handbook evidence.
The structured-rules arm also received the complete grid requirement table and the existing
structured rules and source evidence states.

The run used the historical model `gemini-3.5-flash-lite`, `top_k=20`, the same v2.5 prompt files,
and an identical retrieved-handbook-chunk cache. No new hosted embedding requests were made.
Configuration files and raw evidence are stored alongside each arm/level JSONL. Existing raw
results and frozen inputs were not changed.

## Results

Macro-F1 with case-level 95% bootstrap confidence intervals, balanced accuracy (BA), and unsafe
false positives are shown below. Each complete row has 40 cases; the unsafe denominator is the
26 cases labelled ineligible or manual-review-required.

| Arm | Wording | n | Macro-F1 (95% CI) | BA | Unsafe |
|---|---:|---:|---:|---:|---:|
| Rules only | Low | 40 | 1.0000 (1.0000–1.0000) | 1.0000 | 0/26 |
| Rules only | Medium | 40 | 1.0000 (1.0000–1.0000) | 1.0000 | 0/26 |
| Rules only | High | 40 | 1.0000 (1.0000–1.0000) | 1.0000 | 0/26 |
| CurricuPath | Low | 40 | 0.9825 (0.9524–1.0000) | 0.9667 | 0/26 |
| CurricuPath | Medium | 40 | 0.9730 (0.9369–1.0000) | 0.9500 | 0/26 |
| CurricuPath | High | 40 | 0.9730 (0.9369–1.0000) | 0.9500 | 0/26 |
| CurricuPath, no clarification | Low | 40 | 0.9825 (0.9524–1.0000) | 0.9667 | 0/26 |
| CurricuPath, no clarification | Medium | 40 | 0.9730 (0.9369–1.0000) | 0.9500 | 0/26 |
| CurricuPath, no clarification | High | 40 | 0.9730 (0.9369–1.0000) | 0.9500 | 0/26 |
| Grid-augmented Handbook RAG | Low | 40 | 0.6134 (0.4238–0.7621) | 0.6198 | 9/26 |
| Grid-augmented Handbook RAG | Medium | 40 | 0.5491 (0.3830–0.6941) | 0.6183 | 2/26 |
| Grid-augmented Handbook RAG | High | 40 | 0.5046 (0.3356–0.6521) | 0.5484 | 3/26 |
| Structured-rules LLM, grid-aware | Low | 13 | 0.4222 (0.2137–0.5880) | 0.4381 | 2/8 |
| Structured-rules LLM, grid-aware | Medium | 0 | Not scored | Not scored | Not scored |
| Structured-rules LLM, grid-aware | High | 0 | Not scored | Not scored | Not scored |

The structured-rules arm is incomplete and its 13-case low-level result is descriptive only; do
not compare it as if it were a 40-case result. Gemini returned HTTP 429 quota refusals after
the original 7 cases and again after 6 more cases were completed on 3 October 2026. The medium
and high arms were refused before producing an observation.

## Historical RAG Comparison

On the same frozen cases, the original Handbook-RAG (without grid evidence) had Macro-F1 of
0.3254, 0.3233, and 0.1865 at low, medium, and high wording levels. With grid evidence, these
scores were 0.6134, 0.5491, and 0.5046. Predictions changed for 18, 13, and 15 cases respectively;
the number matching the School reference changed from 15 to 24, 13 to 22, and 8 to 21. There
were respectively 4, 1, and 0 changes from a correct to an incorrect label.

This is **not** an independent accuracy improvement: the added grid facts come from the same
School registration material used to construct the reference labels, and the cases were already
inspected. Treat the result as evidence that supplying grid requirements changes the RAG arm's
decisions and improves agreement on this development-informed subset, not as independent
validation or proof of superiority. The original no-grid results remain the historical baseline.

## Interpretation and Limitations

- Rules-only's perfect agreement is circular in part: its requirements encode the School
  registration reference. It demonstrates faithful encoding of that reference, not independent
  correctness or academic validation.
- The grid-aware RAG comparison repairs the known information-parity gap for the 24 cases with a
  matching grid row. The structured-rules rerun is incomplete because of provider quota limits.
- CurricuPath and rules-only have zero unsafe false positives on this 40-case subset; this does
  not establish safety beyond the adopted reference or this inspected subset.
- Five cases changed from ineligible to eligible after the grid override: `TS010`, `TS015`,
  `TS046`, `TS065`, and `TS067`. All concern `ELEN3017A` (EFA03 for TS010/TS015/TS067;
  EFA04 for TS046/TS065). The corresponding grid rows list no prerequisite/corequisite entries.
  Ask the School to confirm that an empty row means no such registration requirement before
  treating this relaxation as institutionally settled.
- CurricuPath and its no-clarification arm remain identical here. The subset does not demonstrate
  a benefit from clarification.
- The School reference is a single operational source, with no independent academic reviewer,
  second reviewer, or adjudication. Report “agreement with the School registration reference,”
  never “validated accuracy.”
- These outcomes are development-informed. Any confirmatory performance claim needs a new,
  unseen case set and an independent reference process.

## Cost and Artifacts

The dedicated ledger records USD 0.842469 across 139 attempted Gemini calls (120 completed RAG,
13 completed structured-rules, and 6 quota-refused calls conservatively charged at the per-call
ceiling). The USD 3.00 cap was not reached. The ledger is a conservative estimate, not a billing
statement.

- `raw/`: new grid-aware LLM observations plus copies of the existing post-grid deterministic
  observations for paired scoring.
- `raw/*.config.json`: arm/level configuration, prompt/rule/cache hashes, model and retrieval
  settings.
- `spend_ledger.json`: isolated estimated spend ledger.
- `scored/`: generated metrics, confusion table, and summary JSON for all available observations.
- Scoring command: `py scripts/score_test_set_v1.py --raw-dir experiments/evaluation/test_set_v1/results_school_grid_llm/raw --results-dir experiments/evaluation/test_set_v1/results_school_grid_llm/scored`
