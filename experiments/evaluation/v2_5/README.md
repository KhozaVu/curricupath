# CurricuPath Evaluation v2.5

This directory implements the frozen protocol in
`docs/revised_evaluation_plan_2026-09-18.md`.

Official generation is intentionally blocked until:

1. `personnel.json` contains named reviewers, judges, owners, and committed hours;
2. independent labels are approved in `eligibility_cases.csv`;
3. `rag_retrieval_config.json` contains a selected `top_k` from the separate
   development set;
4. `manifest.json` records a clean Git commit and final file hashes; and
5. the raw evaluation corpus has been extracted, embedded, and checked.

Use `docs/evaluation_reviewer_request.md` to secure and record the required independent
reviewers, grounding judge, and committed hours without inventing assignments.

Preparation commands:

```powershell
py scripts/prepare_evaluation_v2_5.py
py scripts/prepare_evaluation_corpus.py
py scripts/embed_catalogue.py
py scripts/select_evaluation_top_k.py
py scripts/check_evaluation_readiness.py
```

Only after readiness passes:

```powershell
py scripts/run_evaluation.py --arm handbook_rag
py scripts/run_evaluation.py --arm structured_rules_llm
py scripts/run_evaluation.py --arm rules_only
py scripts/run_evaluation.py --arm curricupath
py scripts/run_evaluation.py --arm curricupath_no_clarification
py scripts/run_grounding_evaluation.py --arm handbook_rag
py scripts/run_grounding_evaluation.py --arm structured_rules_llm
py scripts/run_grounding_evaluation.py --arm curricupath
```

The runner writes three immutable observations per case. Pre-registered run 1 is the
primary result; runs 2 and 3 measure stability.

## Pilot mode (no independent reviewer)

Until a named academic reviewer approves labels, the study is a **pilot** (plan section 16):
it may describe how the systems behave, but must not claim independently validated
accuracy. Draft runs write `draft_*.jsonl` and are stamped DRAFT throughout.

```powershell
py scripts/run_evaluation.py --arm rules_only --allow-draft
py scripts/run_evaluation.py --arm curricupath --allow-draft --runs 1
py scripts/run_evaluation.py --arm handbook_rag --allow-draft --runs 1
py scripts/score_evaluation.py --allow-draft --reference-sets developer briefing
```

- `--runs 1` makes one pass per case (about 60 model calls per arm) instead of three.
  Repeatability figures then show as not available. Official runs always use three.
- `--reference-sets developer briefing` scores against both developer-side answer keys.
  `pilot/senate_briefing_labels.csv` was extracted from `pilot/senate_rules_briefing.docx`
  (hash in the `.provenance.json`). That document calls every label a draft and carries no
  reviewer name, so it is a sensitivity check, never a substitute for `reference_label`.
- Results land in `results/draft_analysis/`, with `label_set_sensitivity.md` showing which
  conclusions change with the answer key. The main difference is whether a corequisite that
  is only *planned* counts as satisfied (Senate Rule 1.9).

### Benchmark comparison (pilot)

```powershell
# CurricuPath arms without Gemini, so only one extraction path is measured
$env:GEMINI_API_KEY = ""; py scripts/run_evaluation.py --arm curricupath --allow-draft --runs 1
# Model arms, paced under a per-minute quota (15 requests per minute on the free tier)
$env:GEMINI_MODEL = "gemini-3.5-flash-lite"
py scripts/run_evaluation.py --arm handbook_rag --allow-draft --runs 1 --pace-seconds 3.5
py scripts/run_intent_evaluation.py
py scripts/score_evaluation.py --allow-draft --reference-sets developer briefing
py scripts/render_benchmark_figures.py
```

- Record how each run was configured in `results/raw/draft_run_config.json`; the report states
  those deviations from the frozen protocol in its summary.
- `pilot/published_benchmarks.csv` holds the published figures with page references. They use
  other institutions and datasets, so they appear only in a context table with a "why not
  comparable" column, and are never plotted on the same axis as our results.
- `py scripts/build_evaluation_report.py` builds the PDF from the analysis files. It asserts the
  qualitative claims it makes, so it fails rather than print a statement the data no longer supports.
- A run refused by the hosted service (quota or outage) is reported as a provider failure with
  a warning, not silently counted as a wrong answer.

### Experiment C (ambiguity and clarification)

```powershell
py scripts/run_ambiguity_evaluation.py --allow-draft    # pilot: reviewer fields still pending
```

Runs the 13 ambiguity cases with and without clarification under the frozen scripted-reply protocol
(`app/evaluation/ambiguity_runner.py`) and scores them (`ambiguity_scoring.py`). Metrics that need the
reviewer's fields report "not scorable" instead of guessing, and where a question is asked but the
fixed reply is pending, no reply is sent. Official mode refuses to run until the readiness gate passes
and every case carries the reviewer's `required_clarification`, `fixed_simulated_reply` and accepted
outcomes (format: `data_dictionary.md`). `--extraction deterministic` (default) blanks the Gemini key
so only one extraction path is measured.
