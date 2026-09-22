# CurricuPath Evaluation Datasets

This directory contains the frozen draft evaluation inputs described in
[`docs/evaluation_plan.md`](../../docs/evaluation_plan.md). The datasets are
separate from development fixtures and from the public-course ranker's prototype
weak labels.

## Files

| File | Purpose | Current state |
| --- | --- | --- |
| `manifest.json` | Catalogue fingerprint, environment, hashes, accepted evidence gaps, and change-control record | Data snapshot frozen; Git commit pending |
| `rule_cases.csv` | Eligibility gates and structural curriculum-rule cases | 150 draft cases; 15 anchors pending academic review |
| `intent_cases.csv` | Intent, slot, ambiguity, clarification, and boundary prompts | 100 draft cases pending review |
| `grounding_cases.csv` | Expected source-supported facts and prohibited unsupported claims | 56 draft cases pending review |
| `data_dictionary.md` | Field definitions, scales, and review-state meanings | Version 1 |

The ranking profiles and blinded judge files remain under
`experiments/ranking/`. Do not copy prototype weak labels into the independent
evaluation files.

## Regeneration

Generate the draft CSV files from the frozen processed catalogue:

```powershell
py scripts/generate_evaluation_cases.py
py -m pytest tests/test_evaluation_data.py -q
```

Regeneration overwrites the generated draft CSVs. Do not run it after an academic
reviewer or human judge has edited a frozen evaluation file. Instead, create a new
evaluation version and preserve the reviewed version unchanged.

## Review Workflow

1. Confirm that the catalogue fingerprint in `manifest.json` matches the runtime.
2. Give the 15 `anchor_case=true` rows to an academic reviewer without showing
   CurricuPath's output.
3. Record the reviewer identity or approved study code and change only the reviewed
   rows to `approved` or `rejected_with_reason`.
4. Correct rejected expectations from the handbook/CBO evidence, create a new
   version, and rerun affected cases.
5. Review the remaining rule cases before using aggregate accuracy in the report.
6. Review intent wording and expected slots before running Gemini or fallback
   comparisons.
7. Review each grounding case as an atomic expected-fact record.

The current complete automated suite contains 217 collected tests. Passing
`test_evaluation_data.py` proves file and implementation consistency only.
It does not constitute independent academic approval.
