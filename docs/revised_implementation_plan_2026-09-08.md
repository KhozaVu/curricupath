# CurricuPath Revised Implementation Plan

Date: 8 September 2026. Status: proposed architecture and delivery plan; no application implementation authorised by this document.

> **Implementation update, 15 September 2026:** This document remains the
> dated planning baseline. The repository has since implemented the React
> browser interface, FastAPI integration, PostgreSQL/pgvector runtime path,
> deterministic eligibility gates, source-backed CBO information, and optional
> hosted intent/embedding adapters. See
> [`project_layers.md`](project_layers.md) for the current implementation and
> [`partner_setup.md`](partner_setup.md) for setup and temporary review links.

## 1. Decision and scope

Build a source-grounded curriculum and public-learning advisor using PostgreSQL with pgvector, run locally through Docker Compose. Retain deterministic eligibility decisions. Use an existing LLM for structured language extraction, optional semantic review, and constrained response wording. Develop a transparent ranking baseline first; train a small ranking model only when suitable labelled data and time are available.

Docker is the deployment mechanism, PostgreSQL is the database, and pgvector is its vector-search extension. These are complementary choices. Use one application and one PostgreSQL service initially, with modules inside the application rather than six independently deployed services.

The essential outputs are:

| Output | Required information and behaviour |
| --- | --- |
| Curriculum requirements | Programme/year membership; prerequisites; co-requisites; compulsory modules; elective pools and selection counts; exclusions; applicable progression rules; source citations |
| Eligibility advice | Eligible, ineligible, or unknown for the declared profile; reasons; missing information; applicable rule versions |
| Career pathways | Curated career-to-skill-to-module/public-course connections; explain relevance and skill gaps; distinguish future pathway steps from immediately eligible options |
| Course information | Scope, learning outcomes, lecturer/instructor, hours and their units, delivery format, materials references, academic year, provenance and explicit missing values |
| Learning options | Ranked eligible curriculum options and relevant public courses, clearly distinguished; public-course completion never implies Wits credit or prerequisite equivalence without an explicit rule |

Retain the original minimum course library, session feedback, journey/progress and achievements in a simple UI. Removing these is a scope amendment because they are core objectives in the original plan, not merely optional decoration.

## 2. Evidence and current implementation

This revision is based on the repository inspected on 8 September and the original project plan, *AI-Assisted E-Learning and Wits EIE Curriculum Recommendation Platform: Project Plan (26P73)*, supplied as `26g06_84657_11357303_Gift Vundla and Vukosi-Project plan comments (1).pdf`. Counts in the following initial-state table are historical; consult `project_layers.md` and the validation script for the live catalogue.

| Existing asset | Reuse and remaining work |
| --- | --- |
| 101 curriculum membership rows, 65 rules | Retain CSV source data and nested JSON expressions; 101 memberships are not necessarily 101 distinct modules |
| 24 public courses, 25 sources, 17 external-reference records | Import transactionally; preserve provenance; recorded verification is an audit assertion, not proof supplied by passing tests |
| Validators and course audit manifest | Extend for database relationships, field provenance, temporal validity, metadata completeness and recommendation eligibility |
| Normalisation and controlled aliases | Reuse as deterministic baseline and fallback; add negation, contradictions and explicit unknowns to the extraction contract |
| Eligibility evaluator | Existing gate skeleton is useful but incomplete; source verification states, unknown versus failed requirements, rule-expression coverage and bundle/progression checks need hardening |
| Database/loaders/build scripts | Currently placeholders; implement PostgreSQL here instead of first implementing SQLite |
| Ranking, clarification and UI | Substantial work remains; placeholder files do not count as completed components |
| Tests | Last recorded execution: 39 passed on 7 September; this planning task did not rerun tests or establish broader correctness |

Before freezing the migrated catalogue, resolve known audit weaknesses: `electric_circuits` versus `electrical_circuits`, uppercase `DC_analysis`/`AC_analysis`, insufficient justification for DC Analysis's recorded intermediate level, and course/source identifiers previously reused for replacements. Check exact provider titles and URLs, and distinguish inferred workload/level from provider statements. Preserve replacement history in an audit migration record rather than rewriting it away. Tests cannot independently establish lecturer details, current availability, source authority or rating accuracy.

## 3. Changes from the original plan

| Original reference | Commitment | Revised treatment |
| --- | --- | --- |
| Section 3, PDF p. 2 | Local deterministic architecture, SQLite, no live LLM service | PostgreSQL/pgvector in Docker; retain local deterministic baseline; introduce LLM adapters and document model deployment/data handling |
| Section 3.1, p. 2 | Versioned data, authority hierarchy, independent tag review | Preserve; add CBO extraction staging, per-field provenance, dated offerings and career mappings |
| Section 3.2 and Appendix E.1, pp. 3 and 10 | Hard source/programme/prerequisite/co-requisite/exclusion gates before ranking | Mandatory for every production recommendation, including reranking and reviewer-approved results |
| Section 3.2 and Appendix E.2, pp. 3 and 10 | Frozen weighted ranking and TF-IDF | Retain as experimental baseline; evaluate embeddings and trained ranking separately |
| Sections 3.3 and Appendix E, pp. 3 and 11 | Focused clarification; rerun gates; bounded unresolved handling | Preserve one focused question and one clarification attempt per request for the baseline; distinguish user uncertainty from source disputes |
| Sections 3.4 and 5.2, pp. 3-4 | Four matched variants | Preserve comparisons; additional LLM/retrieval/ranker experiments must isolate one change at a time |
| Section 4, p. 3, and Appendix D, p. 9 | Eight-week schedule and ownership | Use remaining Weeks 4-8 provisionally; preserve evaluation/report time and existing lead responsibilities |
| Section 5.3, p. 4, Appendix E.3, p. 10 | Session-only profiles, no persistent participant chat logs or passive histories | Temporary state must actually expire; cloud LLM processing and any new data collection require checking compatibility with the approved protocol before participant use |

Record the architecture and research-method changes with the supervisor. The original document reports permission expiry of 15 December 2026; this is not a submission deadline and does not establish that a changed cloud-processing arrangement is covered.

## 4. Improved pipeline

```text
CBOs / handbook / provider pages
  -> extraction staging -> human source audit -> versioned catalogue
                                                    |
User text -> Selection -> confirmed session state    |
                         |                          |
                         v                          v
                     Matching + deterministic eligibility
                         -> Ranking -> Reviewer
                                         |
             +---------------------------+-----------------------+
             |                           |                       |
       missing user fact           source/data dispute         pass
             |                           |                       |
       clarification               staff audit queue      Output formulator
             |                     + safe abstention            |
       update session                                           v
             -> Matching again                       final validation -> UI
```

### Stage 1: Selection and intent extraction

Support explicit intents: module information, requirements, elective selection, career pathway, public-course search, comparison, clarification answer, feedback, and out-of-scope. Information requests should not demand a full student profile: a user can ask who teaches a module without first establishing registration eligibility.

The LLM returns a schema-validated object containing intent, referenced item IDs/codes, programme/year, interests, career goal, workload/format preference, explicit negative preferences, declared module statuses, unresolved fields, and supporting spans from the prompt. Retain the distinction between extracted text, a proposed interpretation, and confirmed profile facts.

Use the alias table and exact code lookup to validate the object. Preserve phrases such as 'not interested in AI' and 'I have not completed X'; keyword filtering must not discard negation or silently delete unknown words. An LLM may propose a code correction but must not silently confirm a different module or infer academic completion from an interest statement. Missing, conflicting and explicitly negative facts have separate states.

On invalid structured output, allow one bounded repair attempt, then use the existing normaliser and a focused clarification/template fallback. Sorting at this stage classifies intent and preferences; it does not make the final course ranking.

### Stage 2: Matching and eligibility

Route exact module-code, lecturer, prerequisites, compulsory-list and elective-pool queries to relational SQL. These require complete authoritative records; semantic top-k search must not truncate required lists or dependency chains.

For career and open-ended course discovery, combine exact tags/keywords, PostgreSQL text search and embedding similarity. Retrieve evidence chunks and join them to stable module/course IDs. Deduplicate multiple chunks belonging to one item before ranking. Record component scores and retrieval reasons; vector proximity is semantic relevance, not eligibility or calibrated confidence.

For this small catalogue, start with exact vector search. pgvector supports exact search by default; approximate indexes are an optimisation only after measured need and filtered-recall tests. Keep one versioned embedding model/dimension and rebuild embeddings when source text or model changes. [pgvector documentation](https://github.com/pgvector/pgvector)

For curriculum recommendations apply source verification, programme/stream, prerequisites, co-requisites and exclusions before suitability scoring. Apply year/progression, elective counts and plan-wide compatibility before emitting a registration-like bundle. A module can be individually eligible while a proposed set violates an exclusion, elective quota or total-load rule. Evaluate nested all/any expressions and all supported aggregate rule types; unsupported material expressions return unknown and block recommendation.

Prerequisites count only confirmed completed modules. Planned co-requisites count only where the rule permits concurrent study, and only when the proposed concurrent selection itself is valid. Unknown completion triggers clarification; confirmed noncompletion gives a reasoned rejection. Cyclic prerequisite data are flagged, while legitimate co-requisite groups are assessed together.

Public courses require verified relevant evidence and availability plus any declared provider entry requirements. Do not accidentally apply Wits programme restrictions to all public courses. Future pathway suggestions may show currently ineligible modules, but must label their dependencies and must not call them eligible now.

Create a matching output log containing run ID, dataset snapshot, candidate IDs, retrieval scores, gate outcomes, cited evidence IDs and exclusion reasons. Retain detailed logs only for synthetic evaluation; participant logs follow the session-retention policy below.

### Stage 3: Ranking

Implement the original baseline exactly: `0.33 interest + 0.28 career + 0.22 TF-IDF + 0.17 workload/format`, with the missing-value and deterministic tie rules in Appendix E.2. Maintain its TF-IDF corpus and vocabulary frozen across matched variants.

Assess an embedding-based content component as a separate variant. Do not quietly replace TF-IDF while claiming an otherwise identical original comparison. Public aggregate ratings are secondary quality evidence, not personalised relevance labels; keep them displayed but outside the initial baseline score. Missing metadata must not become a guessed match. Curated career/skill links need their own evidence and rationale.

An ML ranker is a conditional extension. Start with a small supervised model over query-item features, for example pairwise logistic ranking or a tree-based learning-to-rank model. Train on independently judged synthetic profile/candidate relevance, not invented student histories or provider star ratings used as ground truth for personal fit. Do not train an LLM from scratch.

Before training, create a separate development set with enough varied profile groups and positive/negative pairs to produce stable validation results. Use a learning curve and held-out profile-level results to judge adequacy; the 24 catalogue items alone are not a training dataset. Group paraphrases of one profile in the same split. Freeze test profiles and judgements before training, exclude them from prompt tuning, and report that catalogue-level generalisation is unproven without an item-held-out experiment.

Use the local laptop first. Select only one of Colab, Kaggle or Lightning AI if measured compute needs justify it; record dependency versions, seeds, hardware and exported model checksum. Upload only permitted public/synthetic data. External compute is a training environment, not a dependency of the running chatbot. Retain the baseline if training data, compute or validation gains are insufficient. Any learned ranker receives only eligible candidates and cannot expand that set.

### Stage 4: Reviewer

Build deterministic acceptance checks first: all item IDs exist, all recommended items passed gates, source versions apply, required citations are present, bundle constraints hold, and explanations do not contradict scores or profile facts.

An existing reasoning-capable LLM can then check semantic consistency against a fixed rubric. It returns `pass`, `clarify_user`, `data_review_required`, or `abstain`, with concise reason codes and evidence IDs. It must not rewrite rules, grant eligibility, invent courses, or change rankings silently. Do not use its approval or stated confidence as the evaluation ground truth; generator and reviewer can share errors.

Reviewer timeout, malformed output or disagreement with a hard check produces a deterministic supported response or abstention. Missing nonmaterial lecturer metadata may be shown as unknown; unresolved eligibility evidence blocks an affected recommendation.

### Stage 5: Human involvement

User clarification resolves missing programme, prerequisite status, concurrent plans or preference priority. Ask one focused question at a time, then revalidate the session state and rerun matching and all gates. A clarification answer cannot simply append an item to a previously eligible set.

Staff review resolves conflicting CBO/handbook rules, stale availability and source gaps. Students cannot verify institutional rules by saying a source is correct. Record the dispute and exclude the affected recommendation pending an authorised source correction.

Keep the original single clarification attempt per request for the matched baseline. If an eligibility-critical fact remains unknown, abstain. If only preferences remain unknown, return verified eligible items in fixed order with an uncertainty note. A later deliberate new request may begin a new cycle; avoid an automatic infinite reviewer/clarification loop. Use profile version numbers to discard results from an older in-flight request after a follow-up changes context.

### Stage 6: Output formulation

Construct a trusted response object first: selected IDs and order, eligibility state, applicable rules, concise relevance reasons, field values, missing fields and citations. Render compulsory requirements separately from optional recommendations and future career preparation.

Use an LLM only to verbalise this object; a separate NLP sentence-formulation model is unnecessary. Render factual course cards and citations directly from stored fields wherever possible. Validate the final output against the trusted object, particularly module codes, prerequisite statements, hours and lecturer names. If validation fails, render a deterministic template. Treat retrieved CBO and provider text as evidence, never as executable instructions; use parameterised database access and fixed query tools rather than model-generated arbitrary SQL.

## 5. CBO ingestion and data design

At the initial inspection, CBOs had not yet been supplied as a complete corpus. The live prototype now records 49 CBO offering rows and 14 explicit missing-CBO records, but coverage remains incomplete. Continue to use the handbook for curriculum requirements and official CBOs for module-specific detail, with the original authority hierarchy: current faculty rules, official school guidance, official module outlines, then verified public sources. Do not let a CBO silently overwrite a higher-authority rule; log conflicts by academic year and applicability.

Ingestion steps: register document and checksum; identify module and academic year; extract text/tables and OCR if needed; propose structured facts; attach page/section/excerpt provenance; validate; human-review material rules and metadata; publish in one transaction; generate embeddings only for approved searchable content. Failed extraction stays in staging. Reimports are idempotent and do not create duplicate offerings or rules.

Record the lecturer per offering/year, rather than as a timeless property of the module. Separate contact, laboratory, self-study, weekly and total hours; preserve units and whether the source explicitly states them. Credits are not evidence of actual contact hours. Materials should record title, type, edition and an authorised URL/reference; do not redistribute restricted course packs. Use null plus a missing reason for unverifiable information.

| Logical tables | Main responsibility |
| --- | --- |
| programmes, modules, curriculum_memberships | Separate module identity from programme/year and compulsory/elective membership |
| module_offerings, offering_staff, materials | Academic year, lecturer roles, hours, format, scope and materials |
| rules, rule_applicability, rule_evidence | Stable rule identity, nested condition JSON, effective periods and evidence |
| public_courses, rating_observations, availability_observations | Stable provider course identity and dated measurements; retain previous observations |
| careers, skills, item_skills, career_skills | Curated career pathways, links, relevance rationale and evidence |
| tags, aliases, item_tags | Versioned vocabulary with consistent namespaces; migrations for renamed tags |
| sources, source_versions, field_evidence, audit_issues | Authority, source status, document checksum, field-level provenance and resolution history |
| document_chunks, embeddings | Evidence-linked chunks, item IDs, model/version/dimension and content checksum |
| experiment_runs, candidate_logs | Synthetic reproducibility artefacts and frozen configuration |

Do not reuse a course ID or source ID when replacing it with a different provider course. Mark the previous record superseded and link the replacement. Existing reused IDs require an explicit legacy mapping. A whole document's verified status does not prove that every extracted field is correct.

The application catalogue role should be read-only. A separate import/migration role publishes audited changes. Use foreign keys, membership uniqueness, controlled states, rating constraints, schema migrations and a transactional build that leaves the prior valid catalogue untouched on failure. CSVs remain the initial reproducible import artefacts; PostgreSQL is the runtime catalogue. Pin tested software versions and use a named Docker volume for catalogue persistence, plus a tested backup/restore procedure. [Docker volume documentation](https://docs.docker.com/reference/compose-file/volumes/)

## 6. Temporary chatbot data

The requirement is short-lived session state, not another permanent store. Start with application session memory. If a database interface is necessary, use a separate ephemeral session PostgreSQL service on memory-backed storage, with no durable volume or backup; do not use pooled SQL temporary tables as multi-request session storage. PostgreSQL connection lifetime is not chatbot session lifetime.

Store a random session ID, declared profile, extracted preferences, clarification state, feedback, progress, profile version and expiry. Enforce a proposed 30-minute idle expiry, reset button, query-time expiry checks and cleanup. Do not retain raw messages or profile payloads in application logs, traces, exports, database statement logs or training datasets. Expiry alone on an ordinary durable database is not sufficient because backups and write-ahead logs can retain data.

Persistent output logs contain synthetic experiment data only. Participant evaluation retains only the permitted anonymous aggregate survey results. Configure cloud-model transmission, provider retention and restricted CBO access against the actual approved protocol before participant deployment; use local processing or synthetic-only demonstrations until compatibility is established. This is a design dependency stemming from Section 5.3 of the original plan.

## 7. Delivery schedule and ownership

The confirmed Open Day is 14 October 2026, 36 calendar days from this revision. Plan five working weeks from 8 September, with a demo-ready release by 11 October and 12-13 October reserved for rehearsal and recovery checks. The original plan's Week 4-8 labels are retained to map the remaining work. Formal report submission dates and weekly developer hours remain unconfirmed; Open Day is the delivery milestone, not evidence of a report deadline. Reserve the final two weeks for evaluation and deliverables. Budget each developer's actual available capacity at 80%, leaving 20% for integration and defects.

| Period | Vukosi lead | Gift lead | Joint exit evidence |
| --- | --- | --- | --- |
| Week 4, 8-14 Sep | CBO collection and coverage manifest; pilot extraction of 3-5 varied outlines; career/skill vocabulary; extraction and clarification contracts | PostgreSQL migrations/imports; session boundary; repair source/unknown gates; exact retrieval and baseline ranker | One cited end-to-end request works with deterministic language fallback; CSV/database parity and gate tests |
| Week 5, 15-21 Sep | Remaining in-scope CBO audit; LLM intent adapter; focused clarification; Streamlit details/chat/evidence and minimum journey views | Hybrid matching; deterministic reviewer; feedback/variants; logs; optional LLM reviewer adapter | Integrated prototype; all advertised module facts sourced or explicitly missing; no unsupported recommendations |
| Week 6, 22-28 Sep | Interface/clarification edge cases; independent relevance labelling; approved survey preparation | Regression/failure tests; freeze runs; small ML experiment only if labels and stable baseline exist | Feature freeze; frozen reference cases/configuration; reproducible baseline and four variants |
| Week 7, 29 Sep-5 Oct | Blinded scoring, permitted usability, metadata/grounding analysis | Execute matched comparisons; bootstrap analysis; latency/failure analysis | Evaluation tables, agreement metrics, failure taxonomy; fix critical defects only |
| Week 8, 6-11 Oct | Individual report draft, shared poster/presentation and interface evidence | Individual report draft, reproducibility package and release evidence | Demo release, poster, evidence pack, report drafts and independently reproduced run; align final reports with confirmed submission dates |
| 12-13 Oct | Rehearse explanation, career/CBO examples and clarification flow | Rehearse startup, backup restore and network/model outage fallback | Timed demonstration on the actual laptop; local assets and tested fallback; no new features |
| 14 Oct: Open Day | Present interface, source audit and user interaction | Present engine, evaluation and reproducibility | Demonstrate the frozen release; record only permitted feedback |

In the first two working days, measure CBO review time and count distinct in-scope modules. Prioritise EFA03/EFA04 third- and fourth-year options and their prerequisite dependencies. Publish a module-by-field coverage manifest for all remaining modules, not fabricated filler. If complete CBO coverage cannot fit the available capacity, negotiate a documented metadata pilot scope while preserving handbook-based curriculum coverage; do not claim every module has full information.

The critical path is source access -> audited facts/schema -> working gates -> retrieval/baseline -> UI/clarification -> frozen tests -> evaluation. Decide by 21 September whether a labelled development set and stable baseline justify a small ML experiment. If they do not, freeze the criteria-based ranker for Open Day and document ML training as future work. Stop feature development on 28 September. Model training and a generative reviewer must not block the critical path. A separate large reviewer model, collaborative filtering, distributed deployment and extensive UI polish are stretch work.

If four weeks or fewer remain, omit custom ML training and use a criteria-based reviewer plus templates where needed. If three or fewer remain, restrict LLM use to structured intent extraction, use the deterministic baseline, and prioritise the original evaluation and reports. Any reduction of originally required UI/evaluation scope must be documented with the supervisor rather than silently dropped.

## 8. Evaluation and release gates

Preserve the original 30-50 synthetic profiles, at least 150 fixed cases, and independently sourced 10-15 anchor cases (Section 5.1). These are evaluation cases, separate from ML training/development cases. Include exact code queries, paraphrases, negation, topic changes, unknown versus failed prerequisites, co-requisite bundles, exclusions, progression/selection constraints, missing CBO fields, contradictory sources, unavailable providers, expired sessions and malicious instructions inside retrieved text.

Retain the four original variants: gates plus fixed ordering; ungated personalised ranking; identical ranking with gates; identical gated ranking with clarification. The ungated variant is offline only. Keep model-extracted profiles and candidate pools fixed when testing downstream effects; test extraction separately against frozen labelled intents/slots. Evaluate hybrid retrieval or learned ranking in additional controlled comparisons, not by changing several components of the original variants together.

| Metric | Release/evaluation rule |
| --- | --- |
| Gate correctness | Zero ineligible or materially unsupported recommendations in gated acceptance cases; measure exact decisions, not only generated prose |
| Grounding | 100% source support for material curriculum claims; field-specific checks for lecturer/hours/materials; zero invented identifiers |
| Ranking | Original Precision@3 >= 0.80 and relevance >= 4/5 targets; add NDCG@3 for graded ranking; these are targets, not promised results |
| Small eligible sets | Apply original top-1/exact-set policy; do not pad results with ineligible candidates |
| Retrieval | Measure relevant-item Recall@k and complete retrieval of exact requirement lists separately |
| Clarification/boundary | Preserve original >=90% targets and denominator rules; report invalid/abandoned follow-ups separately |
| Reviewer | False acceptance and false rejection against independent judgements; a reviewer pass is not a correctness label |
| Operational quality | Record measured median/p95 latency, model calls and cost per request on declared hardware; bounded timeouts and usable fallback |
| Data/session integrity | Import rollback, reset/expiry, session isolation, catalogue hashes unchanged after feedback, and no participant payloads in persistent logs |

Use the original blinded independent scoring, weighted kappa for ordinal judgements, binary agreement, and profile-cluster bootstrap (10,000 resamples, seed 26073, 95% intervals). Keep the original +/-20% one-at-a-time sensitivity tests. State uncertainty and investigator bias. Do not call public-course review counts training benchmarks; educational suitability requires the source-grounded profile/item judgements defined for this project.

Release artefacts should include the CBO coverage manifest, source/field audit and replacement history, frozen catalogue/checksums, schema/migrations/import instructions, model/prompt/embedding configurations, experiment results, failure cases, contribution records and reproducible startup instructions. Ship only redistributable documents; restricted sources need access instructions and checksums.

## 9. Immediate planning hand-off

Use 14 October as the confirmed Open Day milestone; confirm report deadlines and team capacity separately. Record approval of the architectural change and its data-handling implications; collect the in-scope CBOs; freeze the shared request/candidate/review/response contracts; agree source authority and unknown-value handling; then implement one complete vertical slice before expanding model sophistication.

The next implementation milestone is a user asking about a circuit-related career: the system extracts a structured request, retrieves curated options, checks source and academic rules, asks a necessary clarification, reruns the gates, and displays a cited response with lecturer/hours/materials where verified. It must also handle the same request with missing CBO evidence and an unavailable LLM without inventing facts.
