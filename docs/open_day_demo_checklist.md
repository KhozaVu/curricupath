# CurricuPath Open Day Demonstration Checklist

**Target date:** 14 October 2026  
**Release candidate:** `open-day-rc1-2026-09-22`

## Before the Demonstration

1. Start Docker Desktop and confirm the `curricupath-database-1` container is
   healthy.
2. From the repository root, run `docker compose up -d database`.
3. Run `py scripts/build_database.py` only when the processed CSV files have
   changed since the last successful import.
4. Run `py scripts/freeze_release.py --verify`. Do not demonstrate an unverified
   build as the frozen release.
5. Start the application with `py -m uvicorn app.main:app --host 127.0.0.1 --port
   8000`.
6. Open `http://127.0.0.1:8000/` and complete Profile setup before opening the
   advisor.
7. Keep `REASONING_REVIEWER_ENABLED=false` for the dependable deterministic demo.
   Enable it only for a separately labelled reviewer demonstration.

## Demonstration Route

### 1. Supported Eligibility Decision

Select a complete profile, then ask:

> Can I take ELEN4006A in EFA04, and what prerequisites and corequisites do I
> need?

Show the deterministic decision, prerequisite explanation, source evidence, and
response-check status.

### 2. Targeted Clarification

Use an incomplete profile and ask:

> Can I take MATH1049A in EFA04?

Answer `Completed` when CurricuPath asks about `MATH1048A`. Show that the original
decision is rerun once using that exact fact.

### 3. Institutional Evidence Problem

Use a prepared case whose material evidence is incomplete, disputed, superseded,
or discretionary. Show `manual_review_required` and explain that CurricuPath does
not convert an evidence problem into a student clarification question.

### 4. Out-of-Scope Boundary

Ask:

> Predict my final engineering marks.

Show the fixed safe boundary response and confirm that no curriculum decision or
recommendation is produced.

### 5. Catalogue and Career Features

Show one fourth-year elective recommendation, one module-information response
using verified CBO content, and one supported career-path response. Describe
career links as related pathways, not employment guarantees.

## Failure Recovery

- If Gemini is unavailable, keep the reviewer disabled and continue with the
  deterministic engine. Core eligibility must remain usable.
- If hosted embeddings are unavailable, use deterministic keyword matching and
  ranking. Do not claim semantic-search performance.
- If PostgreSQL is unavailable, restart the Docker service. Use CSV fallback only
  if `CATALOGUE_CSV_FALLBACK=true`, and label that fallback clearly.
- If the UI is unreachable, check `http://127.0.0.1:8000/health`, the Uvicorn
  terminal, and whether another process is already using port 8000.
- Never expose `.env`, API keys, tokens, raw participant prompts, or unrestricted
  database access during the demonstration.

## Claims Boundary

The release checks demonstrate engineering consistency and reproducibility. They
do not establish academic accuracy or superiority over benchmark systems. Those
claims require the independently labelled and approved evaluation described in
`docs/revised_evaluation_plan_2026-09-18.md`.
