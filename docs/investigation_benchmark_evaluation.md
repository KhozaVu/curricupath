# CurricuPath Implementation Investigation and Benchmark Evaluation

**Project:** AI-Assisted Wits EIE Learning Pathway and Module Advisor (26P73)  
**Authors:** Gift Vundla and Vukosi Khoza  
**School:** School of Electrical and Information Engineering, University of the Witwatersrand  
**Implementation snapshot:** 15 September 2026  
**Status:** Prototype investigation report, not evidence of official registration approval

## Abstract

This report evaluates the current CurricuPath implementation against the aims and
evaluation criteria in the supplied ELEN4002A/ELEN4012A LaTeX project plan and six
academic-advising benchmark reports. CurricuPath has progressed from the plan's
CSV/SQLite and Streamlit concept to a layered FastAPI, PostgreSQL, pgvector, Gemini,
and browser application. Its central safety decision remains unchanged: source,
programme, prerequisite, corequisite, and exclusion rules are evaluated by
deterministic code before ranking, while language models and embeddings are limited
to interpretation and relevance estimation.

The implementation currently has a validated source trail, deterministic eligibility
gates, controlled intent and module-name resolution, temporary structured sessions,
public-course matching, an experimental learning-to-rank path, decision logs, and a
multi-page browser interface. The automated suite contains 217 collected tests, and the
data audit reports no errors or warnings. Draft evaluation assets now contain 150 rule
cases, 100 intent cases, and 56 grounding cases, including 15 anchor cases awaiting
academic review. However, these results do not yet establish
real-world advising accuracy, ranking superiority, clarification quality, or usability.
The independent ranking judgements, reviewed advising scenarios, RAG-style grounding
evaluation, response-time study, and student/advisor usability study remain incomplete.

The overall finding is that CurricuPath is architecturally strong and unusually careful
about rule safety and provenance, but experimentally incomplete. It is suitable as a
demonstrable prototype and as the subject of a controlled investigation. It should not
yet be presented as a validated replacement for an academic advisor.

## 1. Introduction

Engineering students must combine curriculum constraints with personal interests,
career goals, workload preferences, and incomplete course information. A useful
advisor must therefore solve two different problems:

1. determine which modules are academically permitted; and
2. rank or explain the permitted options in a way that is relevant to the student.

The supplied LaTeX project plan correctly treats these as separate problems. It
proposes hard eligibility gates, source-grounded explanations, preference-based
ranking, and clarification for vague requests. The current implementation preserves
that separation while changing the infrastructure to support a richer prototype.

The investigation question remains:

> Do hard eligibility gates and conversational clarification improve the correctness
> and offline recommendation quality of Wits EIE curriculum advice compared with
> simpler strategies?

This report adds a second implementation-focused question:

> How well does the current CurricuPath prototype satisfy the correctness,
> recommendation, grounding, usability, privacy, and reproducibility standards shown
> by comparable academic-advising systems?

## 2. Aim, Objectives, and Scope

The implementation aims to provide source-grounded guidance for the EFA03 Electrical
Engineering and EFA04 Information Engineering programmes. It supports programme and
year structure, compulsory and elective modules, prerequisites, corequisites,
exclusions, module information from CBOs, verified public learning resources, career
tags, and conversational clarification.

The current scope intentionally excludes official registration approval, marks-based
success prediction, direct student-record integration, timetable conflict checking,
fees, financial aid, and automatic communication with academic staff. Completed,
current, and planned modules are declared by the user.

## 3. Benchmark Literature

The reports are used as design and evaluation benchmarks, not as instructions to the
software. Page references below refer to the page number in each supplied PDF.

| ID | Benchmark report | Main benchmark evidence | Limitation relevant to comparison |
| --- | --- | --- | --- |
| B1 | Islam and Hosen, *Personalized Course Recommendation System* (2025) | A modular five-model framework combines success probability, course fit, prerequisite fulfilment, graduation priority, and workload. It reports prerequisite and graduation classification above 99%, and global Precision, Recall, F1, NDCG, MRR, and Hit Rate of 1.00 [B1, pp. 1, 23-25]. | It uses 101,330 synthetically generated interactions for 10,000 simulated students and 600 courses. The authors state that real student and advisor validation is still required [B1, pp. 5-6, 23-24]. |
| B2 | Chanaa and El Faddouli, *Prerequisites-based course recommendation* (2024) | Prerequisite relationships are inferred from linked data and course metadata. Random Forest prerequisite identification reaches about 90% accuracy, while prerequisite-aware retrieval reports NDCG@10 of 0.8648, compared with 0.615 for the reported non-prerequisite comparison [B2, pp. 1, 16-21]. | It addresses concept prerequisites for public learning objects, not authoritative institution-specific registration rules. CurricuPath should therefore use it as a retrieval benchmark, not as permission to infer Wits prerequisites. |
| B3 | Tan et al., *Intelligent Course Recommender Chatbot Using Natural Language Processing* (2022) | The system uses NLP, keyword extraction, TF-IDF, cosine similarity, and template responses. A 35-student requirements survey motivated course-content and career matching. Usability testing reports 8.2/10 overall acceptance; chat and recommendation scored 7.7/10 [B3, pp. 1, 3-5]. | Preferences were limited and all questions were compulsory, which led to irrelevant answers. The paper recommends more varied and optional questions [B3, p. 5]. |
| B4 | Kuhail et al., *Engaging Students With a Chatbot-Based Academic Advising System* (2023) | MyAdvisor derives 15 advising scenarios from observations and advisor interviews, applies conversational usability heuristics, and evaluates 13 tasks with 17 students and 4 advisors. Student task success was 92%, advisor success 85%, average task time was 1.02 and 1.10 minutes, and SUS was 86.47 and 80.62 respectively [B4, pp. 16-20]. | The study is small and institution-specific. Failures came from missing training phrases, inputs that were too general or too specific, unsatisfactory answers, and software defects [B4, pp. 18-23]. |
| B5 | Tamascelli et al., *Academic Advising Chatbot Powered with AI Agent* (2025) | ARGObot compares a Gemini RAG system with a GPT-4 agent using RAG, web search, and email escalation. On 18 handbook questions, the agent reports answer correctness 0.878, context precision 0.937, faithfulness 0.927, context entity recall 0.272, and answer relevance 0.894 [B5, pp. 4-7]. | The grounding test contains only 18 questions and context entity recall is low for both variants. Student usability testing was not completed [B5, pp. 5-8]. |
| B6 | Alaa et al., *NileAdvisor* (2025) | Gemini converts natural language to Cypher over a Neo4j curriculum graph, while a rule-based transcript engine validates prerequisites. The study reports a 420-query collection, 50 transcripts, 96% precision, 95.6% recall, 95.8% F1, 93% query success, 2.07 s query time, and 100% recommendation success on the 50 transcripts [B6, pp. 2-5]. | The paper describes 420 curated queries but its performance table lists 300 processed queries. Transcript scale is small, the implementation covers one institution and three tracks, and wider curriculum and transcript-format generalisation remain untested [B6, pp. 4, 6]. |

### 3.1 Benchmark criteria derived from the reports

Together, the reports suggest that an academic advisor should be assessed on more
than recommendation accuracy:

- **Rule correctness:** prerequisites and programme constraints must be enforced.
- **Ranking quality:** evaluate order with Precision@k, NDCG@k, MRR, or blinded
  relevance scores.
- **Grounding:** answers should be supported by the retrieved or structured source.
- **Intent robustness:** general, specific, misspelled, and multi-turn requests should
  reach the correct advising operation.
- **Clarification quality:** suggestions should help a user recover from ambiguity.
- **Usability:** measure task success, time, errors, and SUS with students and advisors.
- **Responsiveness:** measure end-to-end response time rather than only model runtime.
- **Human escalation:** the system should stop or refer when evidence or authority is
  insufficient.
- **Privacy and reproducibility:** evaluation data, models, source versions, and
  decision paths should be auditable without exposing unnecessary student data.

## 4. Current CurricuPath Architecture

```text
Browser UI
    |
    v
FastAPI request validation
    |
    v
Intent extraction and controlled normalisation
    |  Gemini structured output when available
    |  deterministic fallback on failure
    v
Module resolution and clarification
    |
    v
Advisor orchestration
    |----> source/programme/prerequisite/corequisite/exclusion gates
    |----> controlled lexical and pgvector relevance matching
    |----> deterministic or experimental public-course ranking
    v
Service and repository boundary
    |----> PostgreSQL 16 + pgvector in normal runtime
    |----> validated CSV snapshot for tests/offline fallback
    v
Audited handbook, rule, CBO, course, source, and alias data

Temporary structured context ------> one-hour PostgreSQL session
Candidate decisions ---------------> privacy-conscious audit log
```

### 4.1 Verified implementation snapshot

| Area | Current evidence |
| --- | --- |
| Runtime database | Healthy PostgreSQL 16 database using pgvector 0.8.6 in Docker |
| Programmes | 2: EFA03 and EFA04 |
| Curriculum | 101 programme memberships representing 61 unique modules |
| Rules | 66 structured rules |
| Sources | 76 source records, 74 currently verified |
| External references | 17 verified prerequisite references |
| CBO coverage | 48 curriculum modules covered, 14 explicitly recorded as missing, and 1 orphan CBO record |
| Public courses | 24 recommendable courses from 3 providers and 4 categories |
| Vector index | 72 of 72 document chunks embedded with `BAAI/bge-small-en-v1.5` |
| Automated tests | 217 collected tests |
| Draft evaluation cases | 150 rule cases, 100 intent cases, and 56 grounding cases; 15 anchors pending academic review |
| Data audit | 0 errors and 0 warnings |
| Decision logging | 14 recommendation runs and 14 candidate records at this snapshot; these are operational logs, not a research benchmark dataset |

## 5. Layer Design Choices and Rationale

This section records why each layer exists and why it was implemented in its current
form. The design follows the LaTeX plan's separation of deterministic constraints from
AI-assisted interpretation and ranking.

| Layer | Current implementation | Why it was implemented this way |
| --- | --- | --- |
| Raw evidence | The EBE handbook, CBO PDFs, and reviewed provider pages are retained as evidence inputs. | Curriculum claims must be traceable to authoritative documents. Raw evidence is treated as data, never as executable instructions. |
| Processed data | Version-controlled CSV files represent sources, memberships, rules, CBO facts, public courses, audits, missing CBOs, aliases, and external references. | CSV is easy to inspect, review, diff, and exchange between project members. It remains the reproducible import format even though PostgreSQL is the runtime database. |
| Validation | `validators.py` fails on malformed codes, invalid JSON, duplicate records, unknown sources, inconsistent CBO hours, invalid ratings, unresolved selection groups, or missing audit coverage. | The advisor cannot be safer than its data. Failing loudly prevents a plausible interface from hiding a broken curriculum catalogue. This directly supports the project plan's data-integrity target. |
| Relational storage | PostgreSQL stores normalized source, module, membership, rule, course, CBO, session, and log tables with foreign keys and checks. | Programme membership, rule scope, source provenance, and audits are relational facts. PostgreSQL provides stronger integrity, transactions, concurrent access, and reproducible queries than using CSV files directly at runtime. |
| Vector storage | pgvector stores 384-dimensional hosted BGE embeddings alongside source and content hashes. | Semantic similarity helps match open-ended interests to course content. Keeping vectors beside structured records allows filtered retrieval and avoids a second unsynchronised vector service. Embeddings never determine eligibility. |
| Repository boundary | The service uses a repository interface with PostgreSQL and CSV implementations. | Tests and offline demonstrations can use the same advisor logic without requiring Docker, while production-like runs use PostgreSQL. Explicit fallback settings prevent an unnoticed backend change. |
| Intent and normalisation | Controlled aliases, regular expressions, and deterministic extraction run alongside optional Gemini structured output. Gemini fields are constrained to known tags and explicit course codes. | LLMs are useful for varied language but should not invent curriculum facts. The controlled vocabulary addresses the wording variation observed in B3 and B4 while preserving reproducibility and a fallback when the hosted model fails. |
| Module resolution | Codes are case-insensitive; a missing final `A` is resolved only when safe; full and partial names support Roman/numeric series; ambiguous names produce choices. | Students should not have to know exact catalogue spelling. Explicit ambiguity questions avoid silently choosing between modules such as Electronics I and Electronics II, addressing the too-general input failures reported in B4. |
| Temporary session | Only structured clarification state is retained for one hour. Raw chat text is not stored by the server. | Multi-turn clarification needs context, but the project does not need persistent participant conversations. This minimizes privacy risk while allowing a follow-up such as a workload answer to reuse the original interest. |
| Eligibility | Five deterministic gates run in a fixed order: source, programme, prerequisite, corequisite, and exclusion. Nested `all_of` and `any_of` conditions are evaluated recursively. | Academic constraints are hard rules, not relevance signals. This is the central safety boundary in the LaTeX plan and aligns with B1, B2, and B6, while avoiding probabilistic approval of registration eligibility. |
| Candidate matching | Exact controlled tags and lexical matches form interpretable candidate signals; optional BGE cosine similarity supplements them. | Controlled tags provide precision and auditability, while embeddings improve recall for natural wording. This combines the metadata matching principle in B2/B3 with an explicit protection against semantic similarity overriding rules. |
| Deterministic ranking | A frozen weighted baseline combines lexical, semantic, interest, career, workload, and format evidence, renormalizing when optional signals are absent. | A transparent baseline is required for ablation and comparison. Stable ID tie-breaking makes identical inputs reproducible and score components can be inspected. |
| Experimental ranking | A checksummed L2 pairwise logistic model can rank public courses when its catalogue fingerprint, feature order, embedding model, and safety settings match. | Pairwise ranking is appropriate for ordered preferences, but artifact checks prevent a stale model from silently scoring a changed catalogue. The prototype remains marked `deployment_eligible=false` until independent judging and safety checks pass. |
| Clarification | The engine asks focused module, programme, workload, or difficulty questions and preserves the pending intent. | B3 shows that forcing every user to answer every preference question can reduce quality. CurricuPath asks only for information material to the current operation and allows deterministic fallback or redirection. |
| Application service | `CurricuPathService` separates domain operations from HTTP, storage, and LLM adapters. | This makes eligibility testable without a web server or model API and keeps the same business rules across the UI, direct API, PostgreSQL, and CSV test paths. |
| API | FastAPI and Pydantic expose typed catalogue, eligibility, semantic search, advisor, evidence, and reset endpoints. | A typed boundary rejects malformed requests early, supports independent frontend/backend testing, and is compatible with future interfaces without duplicating domain logic. |
| Decision log | Recommendation runs record catalogue fingerprint, intent, status, gate outcomes, score components, selected candidates, and profile version without raw prompt text. | This supports debugging and reproducibility while reducing participant-data collection. It is stronger than an opaque final recommendation, but scripted evaluation must separately retain approved scenario IDs and expected outcomes. |
| Browser interface | The blue-and-white React UI guides programme selection, curriculum completion, advisor chat, course browsing, career paths, achievements, and source inspection. Module details show deterministic programme-aware rule sentences and handbook pages instead of raw JSON. | B3 and B4 show that usability and visible suggestions materially affect task success. The UI therefore exposes choices and evidence rather than requiring users to discover exact commands. Achievements are explicitly engagement-only and do not influence eligibility. Plain-English presentation improves comprehension without allowing generated text to alter the underlying rule. |
| Runtime and migration | Docker Compose runs PostgreSQL/pgvector; Alembic creates the schema and vector extension; the FastAPI app currently runs on the host. | Containerising the stateful dependency improves setup consistency while keeping application development simple. Transactional imports prevent a failed rebuild from leaving a partially replaced catalogue. |

## 6. Changes from the Original LaTeX Plan

| Planned design | Current implementation | Investigation consequence |
| --- | --- | --- |
| Streamlit interface | FastAPI-served HTML, CSS, and vanilla JavaScript | Frontend and backend can be tested independently, but a browser usability study is still required. |
| CSV, JSON, or SQLite local store | CSV audit inputs plus PostgreSQL/pgvector runtime | Stronger integrity and vector retrieval, with added Docker and migration complexity. |
| TF-IDF content similarity | Controlled lexical overlap plus hosted BGE embeddings and pgvector | Better semantic recall is possible, but retrieval needs a dedicated grounding evaluation comparable to B5. |
| Fixed hybrid score | Frozen deterministic baseline plus optional pairwise logistic prototype | Enables a real model comparison, but the model cannot be claimed superior until two independent judges complete the relevance dataset. |
| Template clarification | Deterministic session-aware questions in `engine.py` | Functional behaviour exists, although `clarification.py` remains a placeholder and should eventually become the dedicated policy module described in the plan. |
| Four formal advisor variants | Deterministic and prototype modes are exposed; exact rule-only, ungated, hybrid, and hybrid-with-clarification evaluation runs are not yet packaged | The core components exist, but the original ablation experiment is not yet complete. |

## 7. Benchmark Assessment

Status meanings:

- **Strong:** implemented with direct automated or data evidence.
- **Partial:** implemented, but independent or human evaluation is incomplete.
- **Gap:** not yet implemented or not yet measured.

| Benchmark dimension | CurricuPath status | Evidence and interpretation | Required next evidence |
| --- | --- | --- | --- |
| Institution-specific hard constraints | **Strong structurally; Partial empirically** | Source, programme, prerequisite, corequisite, and exclusion gates are deterministic and tested. This is safer for Wits rules than inferring prerequisites from metadata as in B2. | Freeze reviewed EFA03/EFA04 cases and demonstrate 100% exact eligibility with zero gated violations. |
| Data integrity and provenance | **Strong** | The validator reports no errors or warnings; source states, external references, course audits, and missing CBOs are explicit. | Repeat the audit at release and record the catalogue fingerprint and source review dates. |
| Course and career relevance | **Partial** | Twenty-four verified public courses are matched using controlled tags, text, and optional embeddings. | Complete blinded relevance grading and report Precision@3, NDCG@3/5, uncertainty, and failure categories. |
| Learned ranking | **Prototype only** | Weak-label test results are NDCG@3 1.000, NDCG@5 0.991, pairwise accuracy 0.939, and Precision@3 0.900. The deterministic weak-label baseline reports NDCG@3 0.985 and Precision@3 0.900. | Do not claim superiority: the bootstrap lower bound is 0, only 20% of test profiles improve, one learned workload coefficient is negative, and the labels are not independent. Complete both judges and coefficient review. |
| Natural-language intent | **Partial** | Gemini structured extraction is constrained by deterministic facts and has a deterministic fallback. Tests cover known phrasing, casing, shortened codes, and ambiguity. | Build a frozen paraphrase set and report intent accuracy, entity accuracy, boundary-control rate, and fallback rate. B6's 93% query success is a useful external comparison. |
| Clarification and recovery | **Partial** | Focused questions handle ambiguous module names and missing programme, workload, or difficulty. Suggested choices are visible in the UI. | Measure whether a clarification was appropriate and whether the final answer became correct. The project target is at least 90%; B4 also suggests tracking second-attempt success. |
| Source-grounded answers | **Strong structurally; Gap metrically** | Curriculum decisions use verified records and the UI exposes sources. Embedding content is source-linked. | Create question, expected-answer, retrieved-context, and response records; score support/faithfulness and entity coverage. Compare cautiously with B5, not by reusing its 18 questions. |
| Module detail coverage | **Partial** | CBO data can show lecturer, coordinator, scope, materials, contact pattern, notional hours, and provenance for 47 modules. | Obtain or verify the 14 missing CBOs. Do not infer lecturer or prescribed material where the source is absent. |
| Workload reasoning | **Partial** | Public courses use controlled light/moderate/heavy values; CBO modules retain credits, contact patterns, and notional hours. | Distinguish total notional hours (`credits x 10`) from weekly workload. Validate any weekly estimate against the actual teaching calendar and assessment schedule. |
| Conversational usability | **Gap** | The interface has guided setup, suggestions, ambiguity choices, evidence views, reset, responsive navigation, and visible ratings, but no participant study has been run. | Run scenario-based tests with students and at least one advisor; report task success, time, errors, second attempts, and SUS. B4 provides the strongest method benchmark. |
| Response time and reliability | **Gap metrically** | The application is operational with a healthy local PostgreSQL database and hosted-model fallbacks. | Measure median and p95 latency separately for deterministic, Gemini, semantic, and full recommendation paths. Compare with B6's 2.07 s query average only after using equivalent end-to-end timing. |
| Human-in-the-loop escalation | **Partial** | Unresolved evidence can block or redirect, but CurricuPath does not automatically contact an advisor. | Define escalation criteria and display an official contact route. Automatic email is optional and would require consent, authentication, and governance. |
| Privacy | **Strong for the prototype** | Sessions retain structured context for one hour; logs omit raw participant text; no marks, student numbers, or private records are required. | Document consent and retention if a usability study stores recordings, transcripts, or questionnaires. |
| Scalability and portability | **Partial** | PostgreSQL, pgvector, repository abstraction, Docker, and migrations support growth. CSV fallback supports offline use. | Load-test concurrent sessions and extend only after EFA03/EFA04 correctness is frozen. |

## 8. Interpretation Against the Benchmarks

### 8.1 Where CurricuPath compares well

CurricuPath's strongest contribution is its trust boundary. B1 and B6 combine AI
components with prerequisite-aware recommendation, while B2 shows that prerequisite
knowledge improves educational retrieval. CurricuPath applies the same principle more
conservatively for institutional rules: prerequisites are not predicted, inferred from
embeddings, or generated by Gemini. They are imported from reviewed Wits evidence and
evaluated exactly.

The source model is also comparatively strong. Each material curriculum or course
record has an authority, locator, review date, and verification state. Missing CBOs and
external prerequisite references are represented explicitly. This makes a data or
interpretation failure visible instead of allowing the language layer to fill the gap.

The language design responds directly to B3 and B4. Controlled aliases support varied
wording, while module-name resolution asks a choice question for ambiguous series.
Session context permits a short follow-up without requiring a full prompt again.
Clickable suggestions and guided curriculum setup follow B4's finding that suggestions
help users recover from vague input.

Privacy and reproducibility are also deliberate strengths. B1 uses synthetic data to
avoid exposing real student records. CurricuPath goes further for its current scope by
not requiring records or marks at all. Structured, expiring context and logs without raw
prompt text reduce collection risk, while catalogue and model fingerprints preserve the
technical conditions of a recommendation.

### 8.2 Where CurricuPath does not yet meet the benchmark

The largest gap is evaluation, not backend functionality. A passing unit test proves
that code follows its specified examples; it does not prove that the specification covers
real advising language or that the expected answers were independently correct. B4's
scenario-based usability method and B6's query categories show the type of external
coverage still needed.

The ranking model is technically integrated but scientifically immature. Its current
results come from 1,200 weak labels generated by a controlled rubric related to the
features being trained. Judge 1 has completed 143 of 1,200 independent grades, Judge 2
has not started, and there are no adjudicated grades. The artifact is correctly marked
`deployment_eligible=false`. Prototype mode may be used for development comparison,
but it should not be described as a validated improvement or used as the default in a
participant-facing evaluation.

Grounding is present as architecture but has not been quantified. Unlike B5,
CurricuPath has not yet measured answer correctness, context precision, faithfulness,
entity recall, or answer relevance on a frozen set. CurricuPath's structured lookup can
make such an evaluation simpler, but the metric still has to be run.

Finally, no SUS or task-completion study exists. Interface polish, achievements, star
ratings, and responsive navigation are demonstrable features, not evidence of usability.
B4's 17-student/4-advisor study and B3's acceptance study should be treated as method
benchmarks rather than scores that CurricuPath can inherit.

## 9. Evaluation Plan Required to Close the Evidence Gaps

The following staged evaluation preserves the targets in the LaTeX plan and adds the
measurements used by the supplied reports.

### 9.1 Freeze data and expected decisions

1. Export the validated catalogue fingerprint and source review manifest.
2. Ask an academic reviewer to verify the coverage matrix and a 10-15 case anchor set.
3. Build 30-50 scripted EFA03/EFA04 profiles covering eligible, ineligible, ambiguous,
   incomplete-evidence, wrong-programme, prerequisite, corequisite, exclusion,
   compulsory, elective, and unrelated requests.
4. Freeze expected outcomes before running advisor variants.

### 9.2 Evaluate deterministic gates

- Report exact eligibility accuracy by gate and programme.
- Require 100% correctness on reviewed cases and zero ineligible recommendations from
  any gated variant.
- Report every failure as data, source, scope, condition-evaluation, or explanation
  error.

### 9.3 Evaluate intent and clarification

- Add paraphrases, lowercase codes, missing suffixes, partial names, misspellings,
  very general prompts, and over-specific prompts.
- Report intent accuracy, programme/year/module entity accuracy, clarification
  appropriateness, post-clarification correctness, boundary-control rate, and second
  attempt success.
- Retain the project targets of at least 90% appropriate clarification and at least 90%
  correct refusal or redirection.

### 9.4 Evaluate ranking variants

Run the four variants from the LaTeX plan on identical frozen profiles and catalogue
data:

1. rule-only;
2. ungated preference-and-content ranking;
3. gated hybrid ranking; and
4. gated hybrid ranking with clarification.

For cases with at least three acceptable options, report Precision@3 and NDCG@3.
Report exact/top-1 correctness for single-decision cases, mean blinded relevance on the
0-3 or 1-5 scale, eligibility violation rate, bootstrap 95% confidence intervals, and
weighted Cohen's kappa between the two judges. The model can be deployment-eligible
only after independent labels, adjudication, coefficient review, catalogue compatibility,
and all safety checks pass.

### 9.5 Evaluate grounding and explanations

- For each material answer, store the approved question ID, expected facts, source ID,
  retrieved records or chunks, final response, and reviewer decision.
- Require 100% source support for material curriculum claims.
- Report answer correctness, source precision, fact support/faithfulness, entity recall,
  and explanation completeness.
- Test missing, disputed, incomplete, superseded, and contradictory evidence states.

### 9.6 Evaluate usability and performance

- Use 8-13 realistic tasks covering setup, module information, eligibility, electives,
  course search, career paths, evidence, ambiguity, reset, and error recovery.
- Include students and at least one academic advisor if ethics and availability permit.
- Record task success, time on task, number of attempts, observed errors, SUS, and
  qualitative comments.
- Time deterministic, Gemini, embedding, and complete advisor requests separately.
  Report median, p95, error rate, and fallback rate.

## 10. Open Loopholes, Risks, and Controls

| Risk or loophole | Why it matters | Required control |
| --- | --- | --- |
| Experimental ranker is selectable while not deployment-eligible | Users may confuse a pipeline experiment with a validated model. | Keep a visible prototype label, default participant-facing runs to deterministic, and block formal deployment until all artifact checks pass. |
| Human ranking labels are incomplete | Weak-label metrics can reward a model for reproducing its own rubric. | Complete two blinded judges, adjudication, kappa, and bootstrap comparison. |
| Fourteen CBOs are missing | Lecturer, content, material, and workload answers are incomplete for those modules. | Keep missing fields explicit, continue the CBO register, and never infer facts from module names. |
| Credit-based workload can be misread as weekly hours | NQF notional hours cover the full course, not automatically each teaching week. | Show total notional hours separately and compute weekly guidance only from a documented period and assessment/contact schedule. |
| LLM intent output can be wrong | A plausible parse could route a student to the wrong operation. | Preserve deterministic precedence, schema validation, known-tag restrictions, cooldown fallback, and clarification for ambiguity. |
| Semantic similarity can retrieve a related but unsuitable option | Relevance is not permission or source authority. | Filter by recommendable state and programme/rule gates before presenting eligibility; log semantic scores separately. |
| Source and public ratings become stale | Availability, ratings, lecturers, and curricula change. | Enforce access/review dates, verification states, periodic re-audit, and catalogue fingerprints. |
| Self-declared completed modules may be inaccurate | Eligibility is only as correct as the profile supplied. | Clearly label outcomes as based on declared modules and provide an editable confirmation step. Do not claim transcript verification. |
| Raw prompt minimisation reduces failure reconstruction | Privacy-safe logs cannot reproduce every unexpected phrase. | For scripted evaluation, store approved scenario IDs and prompts in the research dataset; retain no participant text unless consent and ethics approval permit it. |
| Clarification policy is embedded in the engine | Growth may make `engine.py` hard to audit and create divergence from the planned architecture. | After the prototype milestone, move the tested policy into `clarification.py` without changing behaviour. |
| Hosted Gemini and Hugging Face services can fail or change | Availability and model revisions affect latency and output. | Pin model/provider metadata, use timeouts and deterministic fallbacks, and record the active adapter in evaluation runs. |
| Automated advisor contact is absent | Some questions require human authority. | Provide a verified contact/referral path first. Add automated email only with authentication, explicit consent, and institutional approval. |

## 11. Ethics and Responsible Claims

CurricuPath should continue to avoid marks, student numbers, financial records, health
information, demographics, and persistent raw chat logs. If a usability study records
screens, speech, prompts, or questionnaires, the team must obtain the required ethics
and institutional permissions, explain retention, and collect informed consent.

The prototype may currently claim that:

- it stores and validates a source-grounded EFA03/EFA04 catalogue;
- it applies deterministic eligibility rules in a documented order;
- it provides auditable candidate scores and source trails;
- it supports hosted intent interpretation and semantic matching with deterministic
  fallbacks; and
- its automated implementation and data tests pass for the cases currently encoded.

The prototype may not yet claim that:

- it is 100% accurate for real Wits advising;
- the learned ranker is better than the deterministic baseline in real use;
- students or advisors find it usable or trustworthy;
- it predicts academic success;
- it verifies a student's official academic record; or
- it replaces registration approval or a human academic advisor.

### 11.1 Phase 5 Stabilisation Evidence

The Open Day release process is now executable rather than an informal checklist.
`scripts/freeze_release.py` validates the processed data, runs the complete Python
suite, executes the PostgreSQL session/logging smoke tests, builds the production
React interface, and records the result in a non-secret release manifest. The
manifest fingerprints:

- every processed CSV catalogue file and the imported PostgreSQL catalogue;
- the deterministic eligibility, orchestration, scope, response-invariant,
  response-repair, reviewer, intent, and session controls;
- the frozen RAG, structured-rules, and grounding prompts;
- the scope policy version, reviewer rubric version, and complete controlled
  reviewer reason-code set; and
- the configured model identifiers, embedding dimensions, feature flags, package
  versions, Compose definition, Git commit, and database health state.

The first candidate run passed data validation, the complete automated suite, the
explicit PostgreSQL smoke tests, and the production frontend build. Its release
fingerprint is
`0592c52510226f6f05e4ea34bf4d161d06c921f7a7ce1abc764d3af437bb2534`.
The artifact is correctly labelled `candidate_verified`, not frozen, because the
working tree is not yet clean. After the candidate and its inputs are committed,
`py scripts/freeze_release.py --verify` performs a non-mutating drift check and
refuses release if a fingerprint changed, a check fails, PostgreSQL is unavailable,
or the tree is dirty.

This is engineering verification only. The manifest separately records that
official comparative claims remain blocked until the required independent academic
review and grounding judgement are complete.

## 12. Conclusion

The current CurricuPath implementation follows the most important principle in the
LaTeX project plan and the benchmark literature: academic constraints and evidence
must be separated from preference ranking and conversational presentation. Its
deterministic rule gates, explicit source states, validated PostgreSQL catalogue,
controlled language layer, semantic retrieval boundary, temporary structured sessions,
and privacy-conscious logs form a credible engineering foundation.

Against the six benchmarks, CurricuPath is strongest in institution-specific rule
safety, provenance, modularity, privacy, and reproducibility. It is partially complete in
intent handling, clarification, module information, content matching, and experimental
ranking. It remains weakest in independent evaluation: there is no completed reviewed
eligibility set, two-judge ranking ground truth, grounding metric study, response-time
study, or participant usability study.

The next investigation milestone should therefore be an evidence package, not another
architectural expansion. Freezing reviewed scenarios, completing independent labels,
running the four planned variants, measuring source support and latency, and conducting
a small task-based usability study would convert the current prototype from a strong
implementation into a defensible academic result.

## References

[P1] Gift Vundla and Vukosi Khoza, *AI-Assisted Wits EIE Learning Pathway and
Module Advisor: Project Plan (26P73)*, supplied ELEN4002A/ELEN4012A LaTeX
project-plan template, 2026.

[P2] Gift Vundla and Vukosi Khoza, [Revised CurricuPath Implementation Plan](revised_implementation_plan_2026-09-08.md),
8 September 2026.

[B1] M. S. Islam and A. S. M. S. Hosen, "Personalized Course Recommendation
System: A Multi-Model Machine Learning Framework for Academic Success,"
*Digital*, vol. 5, art. 17, 2025. DOI: 10.3390/digital5020017. Supplied file:
`digital-05-00017-v2.pdf`.

[B2] A. Chanaa and N. El Faddouli, "Prerequisites-based course recommendation:
recommending learning objects using concept prerequisites and metadata matching,"
*Smart Learning Environments*, vol. 11, art. 16, 2024. DOI:
10.1186/s40561-024-00301-0. Supplied file: `s40561-024-00301-0 (1).pdf`.

[B3] C. W. Tan, M. H. A. Hijazi, S. Alias, A. A. A. Ibrahim, and M. F. I. Othman,
"Intelligent Course Recommender Chatbot Using Natural Language Processing,"
*International Journal on Advanced Science, Engineering and Information Technology*,
vol. 12, no. 5, 2022. Supplied file: `sriatmaja,+Hijazi+14798-AAP.pdf`.

[B4] M. A. Kuhail, H. Al Katheeri, J. Negreiros, A. Seffah, and O. Alfandi,
"Engaging Students With a Chatbot-Based Academic Advising System,"
*International Journal of Human-Computer Interaction*, vol. 39, no. 10,
pp. 2115-2141, 2023. DOI: 10.1080/10447318.2022.2074645. Supplied file:
`Engaging Students With a Chatbot-Based Academic Advising System.pdf`.

[B5] M. Tamascelli, O. Bunch, B. Fowler, M. Taeb, and A. Cohen, "Academic
Advising Chatbot Powered with AI Agent," in *Proceedings of the 2025 ACM Southeast
Conference*, 2025. DOI: 10.1145/3696673.3723065. Supplied file:
`3696673.3723065.pdf`.

[B6] M. Alaa et al., "NileAdvisor: AI-Powered Academic Advising and Recommendation
System," in *Proceedings of the 7th Novel Intelligent and Leading Emerging Sciences
Conference*, 2025. DOI: 10.1109/NILES68063.2025.11232041. Supplied file:
`NileAdvisor_AI-Powered_Academic_Advising_and_Recommendation_System.pdf`.

## Appendix A. Main Implementation Evidence

- Advisor orchestration: [`app/advisor/engine.py`](../app/advisor/engine.py)
- Deterministic eligibility: [`app/advisor/eligibility.py`](../app/advisor/eligibility.py)
- Intent extraction: [`app/advisor/intent.py`](../app/advisor/intent.py)
- Controlled aliases: [`app/advisor/normalisation.py`](../app/advisor/normalisation.py)
- Module resolution: [`app/advisor/module_resolution.py`](../app/advisor/module_resolution.py)
- Ranking: [`app/advisor/ranking.py`](../app/advisor/ranking.py)
- Service boundary: [`app/backend.py`](../app/backend.py)
- API: [`app/main.py`](../app/main.py)
- Data validation: [`app/data/validators.py`](../app/data/validators.py)
- PostgreSQL schema: [`app/data/schema.py`](../app/data/schema.py)
- Semantic retrieval: [`app/data/embeddings.py`](../app/data/embeddings.py)
- Temporary sessions: [`app/data/sessions.py`](../app/data/sessions.py)
- Decision logging: [`app/data/recommendation_log.py`](../app/data/recommendation_log.py)
- Browser interface entry point: [`app/ui/advisor_page.html`](../app/ui/advisor_page.html)
- React interface source: [`frontend/src/App.jsx`](../frontend/src/App.jsx)
- Frozen draft evaluation data: [`experiments/evaluation/`](../experiments/evaluation/)
- Open Day release manifest: [`experiments/release/open_day_rc1_manifest.json`](../experiments/release/open_day_rc1_manifest.json)
- Release freeze tooling: [`scripts/freeze_release.py`](../scripts/freeze_release.py)
- Demonstration checklist: [`docs/open_day_demo_checklist.md`](open_day_demo_checklist.md)
- Layer documentation: [`docs/project_layers.md`](project_layers.md)
- Automated tests: [`tests/`](../tests/)

## Appendix B. Reproduction Commands

```powershell
docker compose up -d database
py scripts/build_database.py
py scripts/embed_catalogue.py
py scripts/validate_database.py
py scripts/freeze_release.py
# After committing the candidate and all release inputs:
py scripts/freeze_release.py --verify
py -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The hosted embedding command requires a configured Hugging Face token. The application
still supports deterministic matching when semantic search is disabled or unavailable.
