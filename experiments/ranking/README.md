# Public-Course Ranking Experiment

This directory holds independently authored profiles and blinded relevance
judgements for the optional public-course learning-to-rank experiment. Do not fill
these files from existing CurricuPath scores, recommendation logs, provider ratings,
or LLM-generated labels.

## Profiles

Complete `profiles.csv` with at least 50 distinct preference profiles:

- At least 30 rows with `split=train`
- At least 10 rows with `split=validation`
- At least 10 rows with `split=test`
- `interests` and `career_preferences` use semicolon-separated canonical tags from
  `data/processed/aliases.csv`
- `workload_preference` is blank, `light`, `moderate`, or `heavy`
- `profile_group_id` identifies one underlying preference scenario; all of its
  paraphrases must remain in the same split
- `profile_author` identifies who defined or reviewed the scenario
- `review_status` must be changed from `draft` to `approved` by a human reviewer
  before either judge starts grading

Freeze the profiles and their split assignments before judging.

The repository includes 50 balanced draft scenarios generated without baseline
scores. A human must review and approve them before judging. Relevance grades remain
human research data; generating grades from the existing ranker would leak the
baseline into the proposed ground truth.

## Judgements

For every profile and every recommendable public course, add one row to
`judgements.csv`. With 50 profiles and the current 24 courses, this is 1,200 rows.

Grades are `0` (irrelevant/conflicting), `1` (weak), `2` (relevant), or `3`
(excellent). Two different judges must grade independently without seeing baseline
or semantic scores. Fill `final_grade` after both grades are complete. A difference
of two or more grades requires an explanation in `adjudication_notes`.

Use the local blinded interface instead of editing both judge files together:

```powershell
py scripts/ranking_label_app.py
```

Open `http://127.0.0.1:8010/`. First review and approve the draft profile set. Each
judge then chooses a different slot and identifier. The page returns grades only
from that judge's file. Once both judges complete 1,200 grades, prepare adjudication
and resolve every disagreement. Agreements merge automatically.

## Train

Ensure PostgreSQL, pgvector, catalogue embeddings, and `HF_TOKEN` are available, then
run:

```powershell
py scripts/train_public_course_ranker.py
```

The script caches semantic features, tunes only `C`, reports weighted Cohen's kappa,
evaluates NDCG@3, Precision@3, NDCG@5, pairwise accuracy, and profile-bootstrap
uncertainty, then writes a checksummed model artifact under `experiments/models/`.

Use `--approve-coefficients` only after a human reviews the learned signs and
contributions. Even with that flag, the artifact is deployment-eligible only when it
beats the deterministic baseline and passes every stability and safety check.

Do not enable `ALLOW_EXPERIMENTAL_RANKER` in a participant-facing run. That switch is
only for inspecting a checksummed but not-yet-approved artifact during development.

## Prototype labels

When time does not permit completion of the two independent judge files, generate a
separate weak-label dataset to exercise the technical pipeline:

```powershell
py scripts/generate_prototype_labels.py
py scripts/train_public_course_ranker.py --prototype-labels experiments/ranking/prototype_judgements.csv
```

`prototype_judgements.csv` is generated from the versioned controlled-tag rubric in
`app/advisor/prototype_labels.py`. It does not modify either human judge file. A model
trained from it records `label_provenance=prototype_criteria_v1_codex_assisted` and is
always marked `deployment_eligible=false`, regardless of its measured metrics.
