# CurricuPath

CurricuPath is a deterministic curriculum and public-course advisor backed by
PostgreSQL and pgvector. Reviewed CSV files remain the authoritative import
sources. Gemini may extract structured intent from a user's wording, but
programme membership, prerequisites, corequisites, exclusions, source
verification remain deterministic application logic. Public-course ranking uses the
auditable criteria baseline unless a separately evaluated pairwise model artifact is
explicitly enabled.

For a clean setup on a partner's computer, including Docker, secrets, pgvector,
and troubleshooting, follow [the partner setup guide](docs/partner_setup.md).
The frozen investigation methodology and release evidence are defined in the
[revised evaluation plan](docs/revised_evaluation_plan_2026-09-18.md). The older
evaluation document is retained only for secondary methodological material.
The proposed context-constrained scope gate and independent response reviewer are
described in the
[reviewer implementation plan](docs/context_constrained_reviewer_plan_2026-09-17.md).

## Run locally

The compiled React interface is included in the repository, so Node.js is not
required just to run CurricuPath. Install the Python dependencies and start the
existing API as usual:

```powershell
py -m pip install -r requirements.txt
docker compose up -d database
py scripts/build_database.py
py scripts/embed_catalogue.py
py -m app.main
```

Open `http://127.0.0.1:8000/` for the complete browser interface. It includes the advisor, curriculum journey, public-course library, career paths, and evidence audit. The header includes a saved Light/Dark display selector. API documentation remains available at `http://127.0.0.1:8000/docs`.

## Share a temporary UI preview

`127.0.0.1` is private to the computer running CurricuPath, so it cannot be
opened by a collaborator on another device. For a short review session, run a
Cloudflare quick tunnel in a second PowerShell window after the API is running:

```powershell
cloudflared tunnel --url http://127.0.0.1:8000 --no-autoupdate
```

Cloudflare prints a unique `https://...trycloudflare.com` address. Share that
address only with the intended reviewer. It is a temporary, unauthenticated
prototype preview: it stops when the command window closes and is not a
production deployment. Do not expose secrets, participant data, or privileged
administrative endpoints through it. Install the official `cloudflared` command
first; it is optional and is not required for ordinary local development.

The browser interface is implemented in React under `frontend/`. After changing
the interface, rebuild the FastAPI-served bundle with Node.js 20 or newer:

```powershell
npm install
npm run build:ui
```

The build writes `app/ui/assets/app.js` and `app/ui/assets/app.css`. Commit those
compiled files with the React source so a partner can run the prototype without
installing frontend tooling.

If `GEMINI_API_KEY` is not set or Gemini is temporarily unavailable, the advisor uses its deterministic alias and identifier extractor. After a failed Gemini request, a short circuit-breaker cooldown keeps clarification replies responsive.

Every advisor request also passes through a versioned deterministic scope policy.
Supported requests continue to the existing engine, ambiguous requests receive a
focused clarification, and out-of-scope requests are stopped before retrieval or
ranking. Local response invariants run on every supported answer. An independent
Gemini response reviewer is available but disabled by default:

```dotenv
REASONING_REVIEWER_ENABLED=false
REASONING_REVIEWER_MODEL=gemini-3.6-flash
REASONING_REVIEWER_TIMEOUT_MS=5000
```

The reviewer can approve, reject, or request one controlled presentation repair. It
cannot modify eligibility, candidate ordering, scores, source IDs, or other protected
decision fields. If it is unavailable, the validated deterministic answer remains
usable and is labelled with `review.status=not_run` in response metadata.

## Live handbook-RAG baseline demo (optional)

For an on-site comparison demo (for example, at Open Day), the advisor page can offer
a "System" toggle that switches a question between CurricuPath and the same naive
handbook-RAG baseline used as the comparator in the frozen v2.5 evaluation. This is a
live, ad-hoc convenience feature, entirely separate from the official evaluation runs
in `experiments/evaluation/v2_5/results/raw/`; it writes no session state and no
recommendation-audit rows. It is disabled by default:

```dotenv
HANDBOOK_RAG_DEMO_ENABLED=false
```

Enabling it requires `GEMINI_API_KEY` and `HF_TOKEN`, and it calls both hosted
services on every baseline question, so treat it as a cost-incurring, demo-only
feature. It also requires the evaluation corpus to already be embedded in the
configured PostgreSQL database (`py scripts/prepare_evaluation_corpus.py` then
`py scripts/embed_catalogue.py`); without it, baseline retrieval returns nothing and
temporary hosted-model failures return a clear baseline-unavailable message and
direct users to the deterministic CurricuPath advisor.
The toggle is hidden entirely when the flag is off, so this has no effect on the
default CurricuPath experience.

## Main endpoints

- `POST /advisor` accepts free text plus optional declared programme and module history.
- `POST /eligibility` runs the fixed source, programme, prerequisite, corequisite, and exclusion gates.
- `GET /programmes/{programme_code}/modules` lists curriculum membership.
- `GET /modules/{course_code}` returns curriculum and verified CBO facts, including staff, workload, scope, materials, and deterministic plain-English rule summaries.
- `GET /cbos/missing` returns the explicit list of curriculum modules whose CBOs are still needed.
- `GET /courses` returns only verified, available, recommendable public courses.
- `POST /search/semantic` embeds a query through hosted Hugging Face inference and searches pgvector.

The advisor also answers source-backed catalogue questions such as:

- `How many credits is ELEN2017A?`
- `What year is Electric Circuits taken?`
- `How many credits does Electrical Engineering have?`

Module credit and year answers come directly from the relevant curriculum-membership
record. Programme totals count each elective pool using its recorded selection count,
not every option in that pool. These totals are catalogue calculations, so official
Wits programme-credit requirements remain the registration authority.

Run the quality checks with:

```powershell
py -m pytest -q
py scripts/validate_database.py
```

## Stabilise and freeze a release

Phase 5 has one command for the engineering release gate:

```powershell
py scripts/freeze_release.py
```

It validates the data, runs the complete test suite with the experimental
Handbook-RAG toggle isolated, runs explicit PostgreSQL smoke tests, builds the
production React interface, and writes a non-secret candidate manifest to
`experiments/release/open_day_rc1_manifest.json`. The manifest fingerprints the
catalogue, imported database, deterministic controls, prompts, policy/rubric,
reason codes, model identifiers, package versions, Compose definition, and Git
state. It never stores API keys.

Commit the candidate and all release inputs, then verify the clean snapshot
without rewriting the manifest:

```powershell
py scripts/freeze_release.py --verify
```

Verification is blocked when files drift, a check fails, PostgreSQL is
unavailable, or the Git working tree is dirty. This proves engineering
reproducibility; official accuracy or comparative claims still require the
independent evaluation gate below. The demonstration route and fallback procedure
are in [`docs/open_day_demo_checklist.md`](docs/open_day_demo_checklist.md).

## Prepare the frozen evaluation

The v2.5 harness keeps draft preparation separate from official outputs:

```powershell
py scripts/prepare_evaluation_v2_5.py
py scripts/prepare_evaluation_corpus.py
py scripts/embed_catalogue.py
py scripts/select_evaluation_top_k.py
py scripts/update_evaluation_manifest.py
py scripts/check_evaluation_readiness.py
```

The readiness command intentionally fails until named independent reviewers, committed
hours, approved labels, and a clean Git snapshot are recorded. Do not bypass it for an
official run. Development dry runs require the explicit `--allow-draft` flag and write
separate draft outputs. Full commands and frozen artefacts are documented in
[`experiments/evaluation/v2_5/README.md`](experiments/evaluation/v2_5/README.md).

## PostgreSQL catalogue

The CSV files remain the reviewed source datasets. PostgreSQL is the primary
runtime retrieval database for relational queries, expiring advisor sessions,
structured recommendation logs, and pgvector matching. Set
`CATALOGUE_BACKEND=csv` to force CSV-only operation. With
`CATALOGUE_CSV_FALLBACK=true`, the application uses validated CSV data when
PostgreSQL is unavailable at startup.

Start Docker Desktop, then build the database from the existing CSV files:

```powershell
docker compose up -d database
py scripts/build_database.py
py scripts/embed_catalogue.py
docker compose ps
```

The build command applies Alembic migrations, validates every processed dataset,
and replaces the imported catalogue in one transaction. It preserves expiring
advisor sessions but clears recommendation runs because those runs refer to the
previous catalogue snapshot. The migration installs PostgreSQL's `vector`
extension and creates 384-dimensional embedding columns for the hosted
`BAAI/bge-small-en-v1.5` model. `build_database.py` never calls Hugging Face;
`embed_catalogue.py` is the explicit hosted-inference step. It is resumable and
only embeds missing, changed, or differently configured chunks. Unchanged vectors
are preserved by content hash when the CSV catalogue is rebuilt.

The running API uses semantic similarity as an optional course-matching signal
when `SEMANTIC_SEARCH_ENABLED=true`. If Hugging Face or PostgreSQL is unavailable,
the advisor falls back to controlled aliases and deterministic text/tag scoring.
Eligibility, prerequisites, corequisites, exclusions, and source verification
never depend on embeddings. Semantic queries are sent to Hugging Face, so do not
include private or identifying student information in free-text search prompts.

Advisor sessions store only structured clarification state and expire after one
hour. Recommendation audit rows store candidate IDs, gate outcomes, score
components, selections, and a dataset fingerprint. Raw participant messages are
not written to PostgreSQL.

## Optional learned public-course ranker

The trained-ranker pathway is implemented, but the repository does not fabricate
labels or a model. The production default remains the deterministic ranker. See
`experiments/ranking/README.md` for the independent two-judge labelling process.

The repository includes 50 balanced draft profiles. Review them and collect blinded
labels at `http://127.0.0.1:8010/` after starting:

```powershell
py scripts/ranking_label_app.py
```

After at least 50 profiles and all profile-course judgements are complete, run:

```powershell
py scripts/train_public_course_ranker.py
```

The experiment uses an L2-regularised pairwise logistic model, profile-level
30/10/10 train/validation/test splits, weighted forward and reverse pairs, and only
the frozen interest, career, lexical, semantic, workload, and missing-preference
features. It excludes provider ratings, review counts, IDs, existing selections,
eligibility outcomes, and source states.

An artifact is marked deployable only after it beats the deterministic baseline on
held-out NDCG@3, passes profile-bootstrap stability checks, has zero safety
violations, and receives explicit human coefficient review. To load an approved
artifact, set:

```dotenv
PUBLIC_COURSE_RANKER_ENABLED=true
PUBLIC_COURSE_RANKER_MODEL=experiments/models/public_course_pairwise_logistic_v1.json
```

Catalogue, embedding-model, feature-order, and checksum mismatches automatically
return the application to deterministic ranking. Keep
`ALLOW_EXPERIMENTAL_RANKER=false` outside a controlled experiment.

Configuration is read from `.env`; use `.env.example` as the non-secret template.
Stop the service without deleting its data volume with:

```powershell
docker compose down
```

The data audit validates `cbo_courses.csv` against curriculum credits and source records,
and requires every curriculum module without a current CBO to appear in
`missing_cbos.csv`. One NQF credit represents 10 total notional learning hours;
weekly workload is only shown when a CBO states it explicitly.
