# CurricuPath Project Layers

This document describes the system that is implemented in the repository now. It
also identifies planned components that are not yet active, so the prototype is not
confused with the full revised implementation plan in
[`docs/revised_implementation_plan_2026-09-08.md`](revised_implementation_plan_2026-09-08.md).
The context-constrained scope gate, deterministic response invariants and optional
independent reviewer are specified in
[`context_constrained_reviewer_plan_2026-09-17.md`](context_constrained_reviewer_plan_2026-09-17.md).
Their initial implementation is part of the running application; the reviewer is
disabled by default pending matched evaluation.

## 1. System Overview

CurricuPath is a source-grounded curriculum and public-course advisor. It combines
deterministic academic rules with optional hosted language and embedding services.

```text
Browser UI
    |
    v
FastAPI HTTP API
    |
    +--> Intent extraction (Gemini or deterministic fallback)
    |
    v
Advisor orchestration
    |
    +--> Module-name resolution and clarification
    +--> Public-course workload/difficulty clarification
    +--> Deterministic eligibility gates
    +--> Controlled-vocabulary and semantic candidate matching
    +--> Selectable deterministic or prototype public-course ranking
    |
    v
CurricuPath service and repository interface
    |
    +--> PostgreSQL + pgvector (normal runtime)
    +--> Validated CSV snapshot (fallback and tests)
    |
    v
Audited handbook, CBO, public-course, source, and rule data
```

The central trust rule is:

> Gemini interprets what the user asked, and embeddings estimate relevance. Only
> deterministic code and verified catalogue records decide academic eligibility.

## 2. Presentation Layer

**Purpose:** Give users one browser interface for advising, curriculum selection,
public courses, career paths, and evidence inspection.

**How it works:**

- The Advisor page sends natural-language requests and profile data to `/advisor`.
- A top-bar selector switches public-course ordering between the deterministic
  baseline and the prototype pairwise model. It never changes academic eligibility.
- A persistent header selector switches between light and dark presentation modes.
  This changes only colours; it never changes curriculum data or decisions.
- The browser defaults to the prototype when it is available and remembers the
  selection in `localStorage`. Direct API requests default to deterministic ranking
  unless `ranking_mode=prototype` is supplied.
- Missing prototype preferences are collected through clickable light/moderate/heavy
  workload and beginner/intermediate difficulty questions.
- The Curriculum page groups modules by year and lets the user mark completed
  modules. The selection is reused in eligibility checks.
- The Course Library filters verified and currently recommendable public courses.
- Career Paths group public courses by controlled career tags.
- Evidence displays source states, external prerequisite references, missing CBOs,
  and orphan CBO records.
- A detail dialog displays module membership, lecturer, scope, material, and hours
  when a verified CBO provides those facts.
- Module prerequisite, corequisite, and exclusion expressions are translated by the
  backend into programme-aware English. The UI displays the readable sentence and
  handbook page instead of exposing raw `condition_json`; the original JSON remains
  available in the API record for auditing.

**Tools:** React 19, Vite, HTML5, CSS, Lucide icons, and the browser `fetch` API.
The React source is bundled before delivery so the FastAPI application serves a
self-contained interface. `localStorage` retains the selected programme and
completed modules on the device; `sessionStorage` retains the temporary advisor
session ID for the browser tab.

**Key files:**

- `app/ui/advisor_page.html`
- `frontend/src/App.jsx`
- `frontend/src/main.jsx`
- `frontend/src/styles.css`
- `app/ui/assets/app.css`
- `app/ui/assets/app.js`
- `app/ui/advisor_page.py`

**Failure behavior:** API errors are shown in the interface. The UI does not make
eligibility decisions itself. The local interface is normally reached at
`http://127.0.0.1:8000/`; a Cloudflare quick tunnel may expose it temporarily
for private review, but it is not an authenticated or production deployment.

## 3. HTTP API Layer

**Purpose:** Expose a typed boundary between the browser and backend services.

**How it works:** FastAPI validates request bodies with Pydantic models, calls the
application service or advisor engine, and serializes the result as JSON. Uvicorn
runs the application server and FastAPI serves the static frontend assets.

**Implemented endpoints:**

| Method and route | Responsibility |
| --- | --- |
| `GET /` | Serve the browser interface |
| `GET /health` | Check the active catalogue repository |
| `GET /catalogue/summary` | Return catalogue counts and available ranking modes |
| `GET /programmes` | List supported programmes |
| `GET /programmes/{code}/modules` | List curriculum membership, optionally by year |
| `GET /modules/{code}` | Return module, rules, sources, and CBO information |
| `GET /courses` | Filter recommendable public courses |
| `GET /courses/{id}` | Return one public-course record |
| `GET /career-paths` | Group course options by career tag |
| `GET /evidence` | Return evidence and audit summaries |
| `GET /cbos/missing` | Return the explicit missing-CBO register |
| `POST /eligibility` | Run deterministic academic gates |
| `POST /search/semantic` | Run direct hosted-embedding and pgvector search |
| `POST /advisor` | Run advising with a request-scoped public-course ranking mode |
| `DELETE /advisor/sessions/{id}` | Clear temporary conversation context |

**Tools:** FastAPI, Pydantic, Uvicorn, and Starlette static-file serving.

**Key file:** `app/main.py`

## 4. Temporary Session Layer

**Purpose:** Preserve only the structured facts needed to answer a follow-up
clarification.

**How it works:** The server stores a random session ID and a `ConversationContext`
containing fields such as pending intent, module, programme, year, requirement type,
workload, difficulty, format, and controlled preferences. It does not store raw
conversation text. PostgreSQL sessions expire after one hour and expired rows are
removed when a session is loaded. The profile version increases when context
changes.

When PostgreSQL is active, `PostgresSessionStore` is used. The CSV/test path uses a
thread-safe in-memory store whose data disappears when the server restarts.

**Tools:** Python dataclasses, UUIDs, SQLAlchemy transactions, PostgreSQL `JSONB`, and
browser `sessionStorage`.

**Key file:** `app/data/sessions.py`

## 5. Language and Intent Layer

**Purpose:** Convert free text into a constrained `ParsedAdvisorRequest`. This layer
extracts facts; it does not select or approve modules.

**How it works:**

1. Text is lowercased and cleaned deterministically.
2. Whole-phrase aliases map user wording to controlled interest and career tags.
3. Regular expressions extract module codes, programme codes, and year indicators.
4. Explicit wording extracts workload and difficulty preferences. Supported
   synonyms include low workload, intensive, beginner, easy, intermediate, and
   advanced.
5. The deterministic extractor classifies supported intents.
6. If configured, Gemini produces Pydantic-validated structured output at
   temperature zero.
7. Gemini output is restricted to known tags and module codes explicitly present in
   the user text. Deterministic fields take priority.
8. On an API error, timeout, or cooldown, the system automatically uses the
   deterministic extractor for at least the next minute.

**Supported intents:** greeting, help, module information, eligibility, curriculum
list, programme information, programme comparison, credit information, public-course
search, career path, profile courses, and unknown. Credit questions for a named
module return that module's NQF credits and programme/year placement. Programme
credit questions calculate the current catalogue total using elective selection rules.

**Tools:** `google-genai`, Pydantic structured output, regular expressions, and the
controlled `aliases.csv` vocabulary.

**Key files:**

- `app/advisor/intent.py`
- `app/advisor/normalisation.py`
- `data/processed/aliases.csv`

**Failure behavior:** The chatbot remains usable without Gemini, although nuanced
language may require a focused clarification.

## 6. Resolution and Clarification Layer

**Purpose:** Resolve how users refer to modules without guessing between ambiguous
curriculum names.

**How it works:** Exact module codes and full titles are preferred. Codes are
case-insensitive, and a missing terminal `A` is added only when that exact suffixed
module exists. Name matching recognizes common numeric, Roman numeral, and `A`/`B`
series forms. If a phrase such as `electronics` or `signals` matches several modules,
the advisor returns the candidates and asks the user to choose one.

Follow-up answers are merged with the temporary conversation context, then the
request is processed again. Clarification never grants eligibility by itself.

When prototype public-course ranking is selected, the advisor asks one focused
question at a time if workload or difficulty is missing. The original subject and
career tags remain in session context while the user answers. Difficulty is then an
exact candidate filter. Workload is a declared preference used only after candidates
have passed the controlled relevance filter.

**Tools:** Deterministic text normalization, regular expressions, similarity scoring,
and session context.

**Key files:**

- `app/advisor/module_resolution.py`
- `app/advisor/engine.py`
- `app/data/sessions.py`

## 7. Advisor Orchestration Layer

**Purpose:** Route a parsed request through the appropriate trusted operation and
build a structured answer for the UI.

**How it works:** `AdvisorEngine` merges explicit UI profile data with extracted
facts, resolves module names, requests clarification when a material field is
missing, and dispatches to one of four principal flows:

```text
Module information -> exact module lookup -> CBO/source facts -> response

Credit information -> programme memberships -> compulsory credits plus required
                      elective selections -> catalogue total and yearly breakdown

Eligibility -> exact module lookup -> Gates 1-5 -> reasons and requirements

Elective request -> programme/year/elective SQL filter -> relevance ranking
                 -> optional eligibility assessment -> labelled suggestions

Public course request -> recommendable-course filter -> relevance ranking
                      -> top five source-verified options

Prototype public course request -> ask workload if missing
                                -> ask difficulty if missing
                                -> controlled-tag relevance filter
                                -> exact difficulty filter
                                -> semantic/model ranking
                                -> explicit workload adjustment
                                -> source-verified options
```

For elective suggestions, academic relevance and current registration eligibility
are deliberately separate. A strong interest match can be displayed with unmet
requirements rather than disappearing or being presented as eligible.

**Tools:** Python service objects, typed request structures, deterministic scoring,
optional semantic search, and structured JSON responses.

**Key file:** `app/advisor/engine.py`

## 8. Deterministic Eligibility Layer

**Purpose:** Answer whether a curriculum module may be taken, with auditable reasons.

**Gate order:**

1. Source verification
2. Programme or stream membership
3. Prerequisites
4. Corequisites
5. Exclusions

Ranking occurs only after these gates when the operation is making an eligibility-
constrained recommendation.

**Rule semantics:** Prerequisites are satisfied only by completed modules.
Corequisites can be satisfied by completed, current, or concurrently planned modules.
Nested JSON rules support `all_of` and `any_of`, allowing expressions such as
`(A or B) and (C or D) and E`. Exclusions are checked against completed, current, and
planned modules.

Every result contains `eligible`, one or more reason strings when rejected, a
`needs_clarification` flag, and a human-readable prerequisite/corequisite summary.

**Tools:** Python dataclasses, recursive JSON condition evaluation, and exact
relational catalogue lookups. No LLM or embedding model participates in a gate.

**Key files:**

- `app/advisor/eligibility.py`
- `app/backend.py`
- `data/processed/rules.csv`
- `data/processed/external_references.csv`

## 9. Matching and Ranking Layer

**Purpose:** Order eligible or clearly labelled candidates by relevance to explicit
interests, career goals, text, workload, and format.

**Current module matching:** Controlled terms score direct title and scope matches
more strongly than a mention found only in supporting material. An optional semantic
score can supplement this result.

**Deterministic public-course scoring:** The baseline combines normalized components
for:

- Query-to-description token overlap
- Controlled interest-tag overlap
- Controlled career-tag overlap
- Workload and format preference match
- Optional pgvector semantic similarity

The component values and final score are placed in the candidate audit log. Ties are
resolved by stable item identifiers, making the output reproducible for identical
data and inputs.

**Selectable prototype scoring:** The Advisor UI can request the versioned pairwise
logistic artifact instead. The choice is sent with each `/advisor` request, avoiding
unsafe global mode changes when several sessions are active. Module eligibility and
curriculum recommendations continue to use deterministic logic in both modes.

For prototype public-course requests, exact controlled interest/career matches form
the candidate pool before model ranking. The selected difficulty filters that pool.
Because the current weak-label model did not learn a trustworthy workload effect,
its raw utility is min-max normalized across the current candidates and blended with
an explicit workload match: 30% model utility and 70% declared workload fit. This
post-model rule is logged in `score_components`; it is not presented as a learned
coefficient.

**Tools:** Deterministic Python scoring, controlled tags, and optional cosine
similarity from pgvector. The optional experiment uses scikit-learn's
L2-regularised logistic regression over weighted pairwise feature differences.

**Key files:**

- `app/advisor/module_matching.py`
- `app/advisor/engine.py`
- `app/advisor/ranking.py`
- `app/advisor/ranker_training.py`
- `app/advisor/prototype_labels.py`
- `scripts/generate_prototype_labels.py`
- `scripts/train_public_course_ranker.py`

**Current boundary:** `ranking.py` contains the frozen baseline and optional
pairwise-logistic runtime. A complete 1,200-row weak-label dataset and trained
prototype artifact now exist. The artifact records
`label_provenance=prototype_criteria_v1_codex_assisted` and
`deployment_eligible=false`. It can load only when the explicit experimental setting
is enabled and its catalogue fingerprint, embedding model, feature order, and
checksum match the live system. Missing semantic scores cause a whole-request
fallback to deterministic ranking.

The prototype reported test NDCG@3 of 1.0 versus 0.984579 for the deterministic
baseline on its weak labels. This is a pipeline smoke-test result, not valid evidence
of real-world superiority, because the labels were generated from a related
controlled-tag rubric. On the 143 available Vukosi grades, weak labels had 82.5%
exact agreement and 96.5% agreement within one grade. Independent completion and
adjudication remain necessary for a defensible evaluation.

`clarification.py`, `feedback.py`, and `variants.py` remain placeholders; current
clarification behavior is implemented in `engine.py`. The independent reasoning
reviewer is implemented as an optional, disabled-by-default quality-control layer;
it cannot change academic decisions and is not an Open Day dependency.

## 9A. Scope and Independent Review Layer

**Purpose:** Reject unsupported requests before retrieval and detect disagreement
between structured decisions and displayed wording without giving a model authority
over academic truth.

The deterministic scope policy returns `supported`, `ambiguous`, or `out_of_scope`.
Supported requests continue through the existing engine, ambiguous requests receive
one focused question, and out-of-scope requests receive a fixed response without
retrieval or ranking. Active clarification context permits short answers such as
`Heavy workload` while explicit prohibited requests remain out of scope.

Local invariants check decision/wording agreement, completed-module labels,
clarification shape, leaked recommendation data and invented module identifiers.
The optional Gemini reviewer receives a protected decision payload and draft answer,
returns schema-validated reason codes, and can request only one controlled repair.
Timeout or provider failure returns the deterministic response after local checks.
Reviewer metadata is attached to candidate audit records without storing participant
text.

**Key files:**

- `app/advisor/scope.py`
- `app/advisor/response_invariants.py`
- `app/advisor/response_repair.py`
- `app/advisor/reviewer.py`

**Label workflow:** `scripts/ranking_label_app.py` serves a separate local research
interface on port 8010. Its 50 profiles are approved. Judge 1 currently contains 143
of 1,200 grades and Judge 2 contains none. The lab stores judges separately, reveals
disagreements only after both finish, and produces adjudicated `judgements.csv`.
`prototype_judgements.csv` is deliberately separate and never overwrites human
grades. The research interface is separate from the participant-facing advisor.

## 10. Application Service Layer

**Purpose:** Keep HTTP, language parsing, and storage implementations separate.

**How it works:** `CurricuPathService` exposes programme, module, course, evidence,
career, and eligibility operations through a repository protocol. This keeps the
same advisor logic usable with PostgreSQL or a validated CSV snapshot.

The service also normalizes module codes and expands rule conditions into readable
module-code and module-name requirements.

**Tools:** Python protocols and dependency injection.

**Key file:** `app/backend.py`

## 11. Repository Layer

**Purpose:** Turn stored rows into stable application records while hiding whether
the source is PostgreSQL or CSV.

**PostgreSQL repository:** Performs relational filters and joins for module
membership, rules, sources, CBO offerings, public courses, evidence, and catalogue
counts. This is the normal configured runtime backend.

**CSV repository:** Loads the same validated data into memory. It supports tests,
offline fallback, and operation when PostgreSQL is unavailable. If
`CATALOGUE_CSV_FALLBACK=false`, a PostgreSQL startup failure stops the application
instead of silently changing backend.

**Tools:** SQLAlchemy Core and Python CSV-backed collections.

**Key files:**

- `app/data/postgres_repository.py`
- `app/data/repository.py`
- `app/backend.py`

## 12. PostgreSQL and pgvector Layer

**Purpose:** Provide the runtime system of record, relational integrity, temporary
session storage, decision logs, and vector search.

**Main tables:**

| Data group | Tables |
| --- | --- |
| Evidence and curriculum | `sources`, `modules`, `curriculum_memberships`, `rules`, `external_references` |
| CBO information | `module_offerings`, `missing_cbos` |
| Public learning | `public_courses`, `course_audits` |
| Vocabulary and retrieval | `aliases`, `document_chunks` |
| Temporary state and audit | `advisor_sessions`, `recommendation_runs`, `candidate_logs` |

The database schema is versioned with Alembic. PostgreSQL constraints and foreign
keys complement the CSV validator. Catalogue replacement occurs inside one
transaction, so a failed import does not leave a partially updated catalogue.

Docker Compose runs PostgreSQL 16 using the pgvector image and persists data in the
named `curricupath_postgres` volume. The application itself currently runs on the
host, not in a Docker container.

**Tools:** PostgreSQL 16, pgvector 0.8.6, Docker Compose, SQLAlchemy 2, Psycopg 3, and
Alembic.

**Key files:**

- `compose.yaml`
- `app/data/schema.py`
- `app/data/database.py`
- `app/data/postgres_repository.py`
- `migrations/`
- `alembic.ini`

## 13. Semantic Retrieval Layer

**Purpose:** Improve open-ended matching without running a local embedding model.

**How it works:** Approved module and public-course text is converted to search
documents. `scripts/embed_catalogue.py` sends only missing or outdated chunks to the
Hugging Face hosted inference API. Normalized 384-dimensional vectors are stored in
`document_chunks`. At request time, the query is embedded with the BGE retrieval
instruction and PostgreSQL ranks candidate chunks by cosine distance.

The active model is `BAAI/bge-small-en-v1.5`. A content hash and the provider, model,
and dimension allow unchanged vectors to survive catalogue rebuilds. `--force`
rebuilds all vectors when required.

Semantic similarity is used only as a relevance signal. It cannot create a module,
change a rule, establish source authority, or override an eligibility result.

**Tools:** Hugging Face hosted inference, `huggingface_hub`, NumPy, BGE embeddings,
PostgreSQL, and pgvector cosine distance.

**Key files:**

- `app/data/embeddings.py`
- `scripts/embed_catalogue.py`
- `app/data/schema.py`

**Failure behavior:** If hosted embeddings fail, the advisor falls back to controlled
tags and deterministic text scoring. The direct `/search/semantic` endpoint reports
a service-unavailable response when semantic search is not configured.

## 14. Source and Processed Data Layer

**Purpose:** Preserve reviewable, version-controlled input for every catalogue fact.

**Raw evidence:** `data/raw/` contains the handbook and collected CBO PDFs. These are
evidence documents, not executable instructions.

**Processed datasets:**

| File | Responsibility |
| --- | --- |
| `sources.csv` | Source identity, authority, locator, dates, and verification state |
| `modules.csv` | Programme/year membership, credits, level, and compulsory/elective status |
| `rules.csv` | Programme, progression, prerequisite, corequisite, exclusion, and selection rules |
| `external_references.csv` | Audit trail for prerequisite codes outside current memberships |
| `cbo_courses.csv` | Lecturer, scope, prescribed material, hours, offering year, and provenance |
| `missing_cbos.csv` | Explicit record of modules without acceptable CBO coverage |
| `courses.csv` | Verified public-course descriptions, tags, format, workload, and ratings |
| `course_audit.csv` | Availability and rating verification for public courses |
| `aliases.csv` | Controlled user-language to interest/career vocabulary mappings |

The current validated snapshot contains 78 sources (76 verified, one incomplete,
and one superseded), 101 curriculum membership rows, 66 rules, 24 public courses,
49 CBO offering rows, and 14 missing-CBO records.

## 15. Validation and Import Layer

**Purpose:** Fail loudly before inconsistent evidence reaches the running advisor.

**How it works:** The loaders first run curriculum and public-course validators. They
check required fields, identifiers, duplicates, programme/year/status values, JSON
rule structure, source references, prerequisite/corequisite references, selection
groups, ratings, CBO credit/hour consistency, source paths, audit parity, controlled
tags, and missing-CBO coverage. Errors raise `ValueError`; the system never silently
repairs source data.

After validation, `scripts/build_database.py` applies Alembic migrations and replaces
the catalogue transactionally. Search chunks are regenerated, while compatible
embeddings are restored by content hash.

```text
Handbook/CBO/provider evidence
    -> reviewed processed CSVs
    -> strict validators
    -> immutable loader snapshot
    -> Alembic migration
    -> transactional PostgreSQL import
    -> searchable document chunks
    -> hosted embedding generation
```

**Tools:** Python `csv` and `json`, custom validators, dataclasses, Alembic, SQLAlchemy,
and PostgreSQL transactions.

**Key files:**

- `app/data/validators.py`
- `app/data/loaders.py`
- `app/data/database.py`
- `scripts/validate_database.py`
- `scripts/build_database.py`

## 16. Evidence and Output-Audit Layer

**Purpose:** Make recommendations traceable without persisting participant messages.

**How it works:** Candidate logs record the item ID, eligibility state, gate outcomes,
score components, final score, and whether the item was selected. Each run records a
SHA-256 catalogue fingerprint based on source states, memberships, rules, ratings,
and searchable content. The run is linked to a random session and profile version,
but `contains_participant_text` is false.

The browser Evidence page separately exposes source verification states and known
coverage gaps so missing evidence is visible rather than invented.

**Tools:** PostgreSQL `JSONB`, SQLAlchemy, UUIDs, and SHA-256 hashing.

**Key files:**

- `app/data/recommendation_log.py`
- `app/data/schema.py`
- `app/ui/assets/app.js`

## 17. Testing Layer

**Purpose:** Protect deterministic behavior and data integrity while the catalogue
and interface evolve.

Tests cover validation, CSV and PostgreSQL repositories, migrations/imports,
eligibility gates, normalisation, intent extraction, module-name ambiguity,
multi-turn workload/difficulty clarification, selectable ranking modes,
recommendations, CBO handling, sessions, API routes, embeddings, prototype labels,
and candidate logs. The current suite contains 217 collected tests, including checks
for plain-English rule presentation and the frozen draft evaluation datasets.
Hosted services are replaced with test doubles so the suite is reproducible without
using Gemini or Hugging Face credits.

**Tools:** pytest, FastAPI test clients, temporary CSV fixtures, fakes/mocks, and a
Docker PostgreSQL integration path where required.

**Key location:** `tests/`

## 18. Configuration and Runtime Tools

Secrets and machine-specific settings belong in the gitignored `.env` file. The
committed `.env.example` documents the required names.

| Setting | Used by |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy/PostgreSQL connection |
| `CATALOGUE_BACKEND` | Select `postgresql` or `csv` repository |
| `CATALOGUE_CSV_FALLBACK` | Permit validated CSV fallback |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Optional structured intent extraction |
| `HF_TOKEN` | Hosted Hugging Face embeddings |
| `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION` | Vector compatibility |
| `SEMANTIC_SEARCH_ENABLED` | Enable or disable semantic request matching |
| `PUBLIC_COURSE_RANKER_ENABLED` | Make the optional artifact available to the advisor |
| `PUBLIC_COURSE_RANKER_MODEL` | Select the versioned ranker artifact path |
| `ALLOW_EXPERIMENTAL_RANKER` | Permit a non-deployable artifact for prototype testing only |
| `POSTGRES_*` | Docker Compose database configuration |

The principal operational commands are:

```powershell
docker compose up -d database
py scripts/validate_database.py
py scripts/build_database.py
py scripts/embed_catalogue.py
py scripts/generate_prototype_labels.py
py scripts/train_public_course_ranker.py --prototype-labels experiments/ranking/prototype_judgements.csv
py -m app.main
py -m pytest -q
```

## 19. Current Versus Planned Components

| Capability | Current state |
| --- | --- |
| Source-grounded curriculum and public-course data | Implemented |
| CBO lecturer, scope, material, and derived weekly-hours display | Implemented where evidence exists |
| Deterministic programme/prerequisite/corequisite/exclusion gates | Implemented |
| Module-name ambiguity clarification | Implemented |
| Gemini structured intent extraction with fallback | Implemented and optional |
| PostgreSQL catalogue, sessions, and decision logs | Implemented |
| Hosted BGE embeddings and pgvector retrieval | Implemented and optional |
| Criteria-based relevance ranking | Implemented |
| Request-scoped deterministic/prototype ranking switch | Implemented for public courses |
| Workload and difficulty clarification | Implemented for prototype public-course requests |
| Pairwise ML training, evaluation, and guarded artifact loading | Implemented |
| AI-assisted prototype labels and non-deployable trained artifact | Implemented |
| Complete independently judged labels and deployable trained artifact | Not yet available |
| Context scope gate and deterministic response invariants | Implemented |
| Independent reasoning-model reviewer | Implemented, optional and disabled by default pending evaluation |
| Full feedback and experimental-variant framework | Not implemented; placeholders only |
| Complete CBO coverage | Not complete; gaps are explicitly registered |
| Repeated-failure / academic-standing exclusion | Not implemented. The student profile has no attempt-history, grade, or failure field, so a rule such as "failing a module twice results in exclusion" cannot currently be evaluated. One handbook-sourced rule (`EXCLUSION_BSC_ENG`, `EBE_2026` p.59) gestures at this but is structurally unreachable and uses unimplemented condition predicates. Logged as a deviation in `experiments/evaluation/v2_5/deviations.md`; deferred past Open Day. |

This division keeps the current prototype demonstrable and auditable while leaving a
clean path to the reviewer, feedback, evaluation variants, and trained ranker in the
revised plan.
