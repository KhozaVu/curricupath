# CurricuPath Evaluation Plan

> **Superseded for the primary investigation:** Use
> [`revised_evaluation_plan_2026-09-18.md`](revised_evaluation_plan_2026-09-18.md).
> This version is retained for its detailed secondary ranking, questionnaire, and
> methodological-reference material.

**Version:** 1.0  
**Plan date:** 15 September 2026  
**Evaluation milestone:** Demonstration-ready evidence package before the Open Day on 14 October 2026  
**Scope:** EFA03/EFA04 curriculum advice, module information, public-course recommendations, intent handling, clarification, grounding, performance, and usability

## 1. Purpose

This plan defines how CurricuPath will be evaluated as an academic advising and
learning-path prototype. It converts the evaluation commitments in the original
project plan [P1], the revised implementation plan [P2], and the benchmark review
[P3] into executable studies, datasets, metrics, decision rules, and deliverables.

The evaluation must answer six separate questions:

1. Does the deterministic engine apply curriculum rules correctly?
2. Does the language layer identify user intent and request clarification appropriately?
3. Are recommended modules and public courses relevant and correctly ranked?
4. Are material claims supported by approved sources?
5. Is the system responsive and reliable under the intended prototype workload?
6. Can representative users complete advising tasks, and how usable do they find the interface?

No single score will be used as evidence for all six questions. In particular,
participant opinion will not establish academic correctness, automated tests will
not establish usability, and weak labels will not establish ranking superiority.

## 2. Current Evaluation Baseline

At the start of this plan, CurricuPath has:

- a React browser interface served by FastAPI;
- a validated CSV catalogue imported into PostgreSQL with pgvector;
- deterministic source, programme, prerequisite, corequisite, and exclusion gates;
- optional Gemini intent extraction with a deterministic fallback;
- controlled aliases, exact module resolution, and ambiguity clarification;
- deterministic public-course ranking and an optional experimental pairwise ranker;
- source-linked CBO information and explicit missing-evidence records;
- deterministic programme-aware English summaries for module rules while preserving
  raw JSON expressions for audit;
- temporary structured sessions and candidate-level recommendation logs; and
- automated implementation tests.

These are implementation assets, not completed research results. The automated
test count and prototype weak-label scores may be reported as engineering checks,
but they must not be presented as evidence of real-world advising accuracy,
ranking superiority, or usability.

At the evaluation freeze, record the actual catalogue counts, test count, Git
commit, database fingerprint, model configuration, and source manifest. Do not
copy changing counts from this planning document into the final report.

## 3. Evaluation Principles

### 3.1 Separate safety from relevance

Academic eligibility is a hard constraint. A relevant but ineligible module is a
useful future-pathway suggestion only when clearly labelled with its unmet
requirements. It is never a valid current recommendation.

### 3.2 Freeze before measuring

Freeze the catalogue, source states, scenarios, expected decisions, prompts,
candidate pools, ranking configuration, and analysis script before final runs.
Defect fixes after the freeze require a new version and a complete rerun of all
affected experiments.

### 3.3 Keep development and test evidence independent

- Unit-test fixtures are development evidence, not the final evaluation set.
- Prototype criteria labels may exercise the training pipeline but cannot be the
  ground truth used to claim that the learned ranker is better.
- Ranking judges must not see provider ratings, model scores, candidate order, or
  each other's labels.
- An academic reviewer must approve expected curriculum decisions before the
  compared systems are run.

### 3.4 Report uncertainty and failures

Report denominators, confidence intervals where appropriate, missing responses,
abandoned tasks, fallbacks, and failure categories. Do not remove difficult cases
after seeing results.

### 3.5 Minimise participant data

Use synthetic EFA03/EFA04 profiles and predefined tasks. Do not request student
numbers, marks, official transcripts, health information, or other unnecessary
personal data. Do not retain raw participant chat unless the approved study and
consent process explicitly permit it.

## 4. Research Questions and Decision Rules

| ID | Research question | Primary measure | Decision rule |
| --- | --- | --- | --- |
| RQ1 | Does CurricuPath make correct curriculum decisions? | Exact decision accuracy and violation rate | 100% on academically reviewed safety cases; zero ineligible recommendations from gated variants |
| RQ2 | Does it understand and recover from user wording? | Intent accuracy, slot accuracy, clarification appropriateness, second-attempt success | At least 90% appropriate clarification and at least 90% correct refusal/redirection |
| RQ3 | Are its top suggestions relevant and well ordered? | Precision@3 and NDCG@3 | Precision@3 target of at least 0.80; compare variants with paired uncertainty, not threshold alone |
| RQ4 | Are answers grounded in evidence? | Material fact-support rate | 100% support for material curriculum claims and zero invented identifiers |
| RQ5 | Is the prototype operationally usable? | Median/p95 latency, error rate, fallback rate | No unhandled failure in critical tasks; report measured values rather than inventing a latency target after testing |
| RQ6 | Can users complete the intended workflow? | Task success, time, errors, SUS | Report SUS separately from task measures; no claim of usability until participant data exist |

The targets are pre-declared evaluation criteria, not promised outcomes. Any
failure must remain visible in the final results.

## 5. Frozen Evaluation Package

Create `experiments/evaluation/` with the following versioned artefacts:

| Artefact | Required contents |
| --- | --- |
| `manifest.json` | Evaluation version, Git commit, run date, catalogue fingerprint, source-manifest hash, configuration, model names, package versions, and random seeds |
| `rule_cases.csv` | Case ID, synthetic profile, candidate module, expected eligible/unknown state, expected gate, expected reason codes, reviewer, and approval state |
| `intent_cases.csv` | Prompt ID, text, expected intent, programme, year, module, interests, workload, difficulty, and clarification expectation |
| `ranking_cases.csv` | Approved profile IDs, candidate-pool definition, split, and scenario group |
| `grounding_cases.csv` | Question ID, expected facts, allowed source IDs, prohibited claims, and evidence state |
| `performance_cases.csv` | Request ID, execution path, warm-up status, repetition count, and expected response class |
| `usability_tasks.md` | Participant instructions, task success criteria, permitted hints, stopping rule, and observer checklist |
| `questionnaire.md` | Project-specific items, construct mapping, response scale, and SUS instrument administration notes |
| `data_dictionary.md` | Field definitions, missing-value conventions, scales, and derived metric definitions |
| `results/` | Immutable raw run outputs followed by separately generated analysis tables |

The initial data freeze is recorded in
[`experiments/evaluation/manifest.json`](../experiments/evaluation/manifest.json).
Its accepted evidence gaps are part of the evaluation boundary, not validation
errors: answers must expose those unknowns rather than infer missing CBO facts.

The existing `experiments/ranking/profiles.csv`, available judge files, and
`judgements.csv` may be reused for ranking only after profile approval and before
judges see system output. The second judge must use a separately identified file
created through the blinded workflow. Preserve `prototype_judgements.csv`
separately and label all results derived from it as prototype pipeline checks.

## 6. Experimental Blocks

### Experiment A: Data and Rule Correctness

**Goal:** Verify that source-backed curriculum facts and eligibility gates produce
the academically expected decision.

**Sample:** Use 30-50 synthetic student profiles and at least 150 fixed cases. Add
10-15 anchor cases reviewed independently by an academic advisor or suitable EIE
academic. Cases must cover both EFA03 and EFA04 and all of the following:

- correct and wrong programme membership;
- compulsory and elective membership;
- satisfied, missing, alternative, and nested prerequisites;
- completed, current, planned, missing, and ambiguous corequisites;
- exclusions and incompatible combinations;
- progression and selection-count rules;
- incomplete, disputed, superseded, and missing evidence;
- exact codes, lowercase codes, missing final `A`, names, and ambiguous names; and
- boundary cases where the correct answer is unknown or requires referral.

**Procedure:**

1. Generate cases without consulting the system output.
2. Have an academic reviewer approve expected decision, gate, and required modules.
3. Freeze and hash the case file.
4. Run the deterministic service directly, independent of generated prose.
5. Compare structured outputs with expected values.
6. Categorise each mismatch as a data, source, scope, parser, condition-evaluation,
   progression, or explanation error.

**Metrics:**

```text
Exact decision accuracy = correct eligible/ineligible/unknown decisions / all cases
Violation rate = ineligible modules presented as currently recommendable / all presented recommendations
Gate accuracy = correct gate outcomes / cases exercising that gate
Reason completeness = required reason elements present / expected reason elements
```

**Release gate:** Exact accuracy must be 100% on the reviewed safety set and the
violation rate must be zero. A failed safety case blocks the affected release; it
cannot be offset by a higher relevance or usability score.

### Experiment B: Intent, Entity Extraction, and Clarification

**Goal:** Measure whether the advisor routes natural language correctly and asks a
focused question when material information is missing or ambiguous.

**Dataset:** Build a frozen set of at least 100 prompts distributed across module
information, eligibility, curriculum listing, elective recommendation, public-course
search, career direction, clarification answers, feedback, and out-of-scope requests.
Include exact wording and paraphrases, punctuation, lowercase input, missing suffixes,
misspellings, negation, corrections, topic changes, vague language, and malicious
instructions embedded in retrieved text.

**Variants:** Run the same prompts through:

- deterministic intent extraction;
- Gemini intent extraction using the pinned model and prompt; and
- normal runtime with Gemini fallback behaviour enabled.

Use zero-temperature or the lowest deterministic setting available. Record model
identifier, prompt version, timeout, fallback, and error state for every request.

**Metrics:** Intent accuracy; macro-F1 across intent classes; exact and per-field
slot accuracy; clarification appropriateness; boundary-control rate; post-
clarification correctness; second-attempt success; fallback rate; and unhandled
error rate.

A clarification is appropriate only if a required fact is genuinely missing or
multiple valid interpretations remain. Repeating a question already answered,
asking for irrelevant profile details, or silently guessing counts as incorrect.

### Experiment C: Recommendation and Ranking Effectiveness

**Goal:** Compare relevance and order while keeping candidate pools and safety
conditions controlled.

**Core variants from the project plan:**

1. Gates plus fixed rule-only ordering.
2. Ungated preference/content ranking, used offline only to quantify safety loss.
3. Identical ranking with deterministic gates.
4. Identical gated ranking with clarification.

Evaluate the optional pgvector signal and experimental learned ranker as additional
one-change-at-a-time comparisons. Do not change extraction, candidate generation,
gating, and ranking simultaneously and attribute the result to one component.

**Human labels:** Two independent judges assign each profile-course pair an ordinal
grade:

```text
0 = irrelevant or conflicts with the declared preference
1 = weakly relevant
2 = relevant
3 = highly relevant
```

Randomise candidate display order per judge. Hide IDs where practical, provider
ratings, current rank, score components, baseline selections, and the other judge's
grades. Judges complete all assigned rows before disagreements are revealed. Resolve
disagreements through documented adjudication; a difference of two or more points
requires a written note.

**Metrics:**

- Precision@3, using a pre-declared relevance threshold of grade 2 or 3;
- NDCG@3 using the full 0-3 graded relevance scale;
- NDCG@5 where five or more candidates are available;
- top-1 or exact-set correctness for candidate sets smaller than three;
- mean judged relevance;
- eligibility violation rate; and
- quadratic-weighted Cohen's kappa before adjudication.

Compute paired profile-level differences between variants. Report mean values and
95% profile-cluster bootstrap confidence intervals using 10,000 resamples and seed
26073. Keep all paraphrases from one scenario in the same resampling unit and data
split. Do not perform item-level resampling that treats dependent judgements as
independent.

The learned ranker is eligible for a participant-facing comparison only after both
independent judges finish, adjudication is complete, coefficient signs are reviewed,
the held-out comparison is stable, catalogue/model fingerprints match, and all
safety gates pass. Weak-label results remain clearly labelled exploratory.

### Experiment D: Grounding and Explanation Quality

**Goal:** Verify that curriculum and CBO claims are supported, complete, and
appropriately qualified.

Create questions covering prerequisites, corequisites, programme membership,
elective pools, lecturers, workload, scope, materials, public-course ratings, and
known missing CBO information. Include straightforward, multi-fact, incomplete-
source, disputed-source, superseded-source, and no-answer cases.

For each response, record the expected facts, source IDs allowed to support them,
retrieved records/chunks, cited source IDs, final structured answer, and reviewer
judgement. Evaluate facts as atomic claims rather than giving one score to a whole
paragraph.

**Metrics:**

```text
Answer correctness = correct atomic claims / evaluated atomic claims
Fact-support rate = supported material claims / material claims made
Source precision = cited/retrieved sources that support the answer / cited/retrieved sources
Entity recall = expected material entities present / expected material entities
Explanation completeness = expected reason elements present / expected elements
Abstention correctness = correct qualified unknown/abstention decisions / no-answer cases
```

**Release gate:** Material curriculum fact-support must be 100%, and there must be
zero invented module codes, source IDs, lecturer names, prerequisites, or materials.
Incomplete evidence must produce a qualified answer, not a guessed value.

### Experiment E: Performance, Reliability, and Fallbacks

**Goal:** Characterise the operational behaviour of each execution path.

Measure at least these paths separately:

- deterministic exact lookup and eligibility;
- deterministic public-course recommendation;
- PostgreSQL/pgvector semantic retrieval;
- Gemini intent extraction;
- complete recommendation request; and
- degraded operation with Gemini, Hugging Face, or PostgreSQL unavailable.

Use a fixed machine, network description, configuration, and request set. Perform
five warm-up requests that are excluded from analysis, followed by at least 30
measured repetitions per path. Use a monotonic clock around the server operation.
Avoid concurrent load unless a separate load test is explicitly declared.

Report median, p95, minimum, maximum, error rate, timeout rate, fallback rate, and
hosted model calls per request. If API costs are available, report them separately.
Do not compare CurricuPath's local p95 directly with another study's mean without
stating the hardware, network, workload, and statistic differences.

### Experiment F: Task-Based Usability

**Goal:** Determine whether representative users can complete intended tasks and
measure perceived usability separately from objective task performance.

**Participants:** Recruit EIE students from relevant years and, if permitted and
available, at least one academic advisor. Record only broad role/year needed for
analysis. Report the achieved sample honestly; a small convenience sample is a
formative prototype study, not population-level evidence.

**Tasks:** Use 8-10 predefined synthetic tasks covering:

1. Select a programme and mark completed modules.
2. Find compulsory modules for a specified year.
3. Check eligibility for a named module.
4. Interpret a missing prerequisite or corequisite.
5. Resolve an ambiguous module name.
6. Find fourth-year electives matching an interest.
7. Find a verified public course for a career goal and workload preference.
8. Inspect lecturer, scope, workload, and materials evidence.
9. Identify when information is missing and locate the source/evidence view.
10. Reset or correct the profile after an input mistake.

Counterbalance task order where practical. Use the same frozen build and synthetic
profiles for all participants. Define success before the study, including the exact
page/result and whether hints are permitted. Observers record completion, time,
attempts, errors, clarifications, hints, abandonment, and brief non-leading notes.

After the tasks, administer:

- the standard 10-item System Usability Scale (SUS); and
- the CurricuPath-specific questionnaire for perceived relevance, perceived
  correctness, explanation quality, clarification quality, usefulness, and trust.

Keep these scores separate. SUS measures perceived usability. The custom item about
rule consistency measures perceived correctness and must not replace Experiment A.

**SUS scoring:** For odd-numbered items subtract 1 from the response; for even-
numbered items subtract the response from 5; sum the adjusted values and multiply
by 2.5. Report the total from 0-100, its mean, standard deviation, median, range,
sample size, and confidence interval where the sample supports one. Do not describe
SUS as a percentage or invent a pass/fail threshold after seeing the data.

## 7. Content Validation of the Custom Questionnaire

The CurricuPath-specific questionnaire is study-specific and must not be called a
validated usability scale. Before participant administration:

1. Map every item to one intended construct.
2. Ask at least three knowledgeable reviewers to rate each item's relevance on a
   four-point scale: 1 not relevant, 2 somewhat relevant, 3 quite relevant, and
   4 highly relevant.
3. Calculate the Item-level Content Validity Index:

```text
I-CVI = experts rating the item 3 or 4 / total experts
```

4. Calculate S-CVI/Ave as the mean I-CVI across retained items.
5. With three to five reviewers, require unanimous relevance (I-CVI = 1.00) or
   revise/remove the item; target S-CVI/Ave of at least 0.90.
6. Record reviewer comments, revisions, exclusions, and the final item-to-construct
   mapping.
7. Pilot the questionnaire with people who will not be part of the final study to
   check wording, completion time, and technical delivery.

Report each custom domain item descriptively using mean, standard deviation,
median, range, and `N`. Do not create a single total score unless the construct
structure and reliability justify it. If a domain contains enough coherent items,
report internal consistency only as exploratory evidence and avoid strong claims
from a very small sample.

## 8. Statistical Analysis Plan

Analysis decisions must be fixed before final result inspection.

| Data | Planned analysis |
| --- | --- |
| Eligibility decisions | Counts, exact accuracy, Wilson 95% interval where informative, gate-stratified error table, and zero-violation check |
| Intent classes | Confusion matrix, accuracy, macro-F1, per-class precision/recall, and slot accuracy |
| Clarification | Appropriate/total, post-clarification success, second-attempt success, refusal/redirection rate, and failure taxonomy |
| Ranking | Precision@3, NDCG@3/5, paired profile differences, 10,000 profile-cluster bootstrap resamples, and weighted kappa |
| Grounding | Atomic fact counts, support/correctness/entity-recall rates, and evidence-state breakdown |
| Performance | Median, p95, range, error/timeout/fallback rates, and path-specific comparison |
| Usability tasks | Success proportion, median time, attempts, hints, errors, and abandonment by task |
| SUS | Standard score calculation and descriptive statistics; no custom item changes |
| Project questionnaire | Item/domain descriptive statistics, missing responses, CVI evidence, and qualitative themes |

Use paired tests or paired bootstrap comparisons for variants evaluated on the same
profiles. Treat statistical significance as supplementary; practical differences,
confidence intervals, safety violations, and failure types are more important for
this prototype. If many exploratory comparisons are made, label them exploratory
and avoid selective reporting.

## 9. Threats to Validity and Controls

| Threat | Control |
| --- | --- |
| Developers author expected answers after seeing outputs | Academic review and freeze expected outcomes before runs |
| Weak labels reproduce the deterministic rubric | Keep them out of confirmatory evaluation; complete independent judges |
| One judge systematically favours a topic/provider | Blind provider/score information, randomise order, report weighted kappa, adjudicate |
| Paraphrases leak across train and test | Group by underlying profile/scenario and keep groups in one split |
| Small eligible pools distort Precision@3 | Use top-1 or exact-set measures; never pad with ineligible items |
| Source records are stale | Freeze access/review dates and fingerprint the catalogue; report the evaluation date |
| Hosted models change | Pin provider/model/prompt configuration and record fallback status per run |
| Developers facilitate usability sessions | Use a written script, predefined hints, observer checklist, and non-leading wording |
| Convenience sample limits generalisation | Report participant characteristics and frame results as formative |
| Custom questionnaire is treated as validated | Complete CVI review and keep it separate from SUS |
| Perceived correctness replaces actual correctness | Report Experiments A and F as different constructs |
| Raw logs expose participant text | Use scenario IDs and aggregate observations unless consent explicitly covers raw text |
| Fixes are made during final evaluation | Version the fix, document it, and rerun the affected frozen block |

## 10. Ethics, Consent, and Data Handling

Before recruiting participants, confirm that the study activities, cloud processing,
questionnaire, screenshots/recordings, compensation, and retention are covered by
the applicable ethics and institutional approval. Obtain informed consent and make
participation voluntary.

Participant-facing evaluation should use the deterministic ranker by default. Do
not enable a non-deployable experimental ranker without explicitly labelling the
condition and obtaining approval for that comparison.

Store participant IDs as random study codes. Keep the consent key separately from
results. Define who can access the data, where it is stored, when it will be deleted,
and how withdrawal will be handled. Export only anonymised, minimum-necessary data
for analysis. Do not send private student records to Gemini or Hugging Face.

## 11. Execution Schedule to Open Day

| Date | Work | Exit artefact |
| --- | --- | --- |
| 15-18 Sep | Freeze constructs, metrics, case schemas, judge rubric, task definitions, and ownership | Approved evaluation protocol and data dictionary |
| 19-23 Sep | Build and academically review rule, intent, grounding, and anchor cases; complete questionnaire CVI review | Frozen case files and final questionnaire |
| 24-28 Sep | Complete independent ranking labels and adjudication; feature freeze the application | Human ground truth, kappa, release candidate, catalogue fingerprint |
| 29 Sep-3 Oct | Run rule, intent, ranking, grounding, and performance blocks | Immutable raw results and failure register |
| 4-7 Oct | Run permitted pilot/usability sessions and calculate SUS/task measures | Anonymised usability dataset and observations |
| 8-10 Oct | Analyse, bootstrap, prepare tables/figures, rerun only versioned fixes | Reproducible analysis outputs and limitations |
| 11 Oct | Freeze demonstration build and evidence package | Demo-ready release |
| 12-13 Oct | Rehearsal, backup checks, offline fallback, and presentation review | Recovery checklist and final presentation |
| 14 Oct | Open Day demonstration | Frozen system and defensible claims only |

If participant or academic-review approval is delayed, complete Experiments A-E
with reviewed synthetic cases and report Experiment F as not yet conducted. Do not
replace missing participants with developer ratings or LLM-generated responses.

## 12. Ownership and Review

Assign named owners before execution. At minimum, keep these roles distinct where
the two-person team permits:

| Role | Responsibility |
| --- | --- |
| Evaluation lead | Freeze protocol, track deviations, assemble evidence package |
| Data/rule reviewer | Approve catalogue snapshot and expected academic decisions |
| Judge 1 and Judge 2 | Independently score relevance without seeing system rankings |
| Session facilitator | Use the fixed usability script and record task observations |
| Analyst | Run versioned metric scripts and preserve raw outputs |
| Supervisor/academic reviewer | Review academic correctness, questionnaire content, and responsible claims |

Where one person holds multiple roles, disclose the overlap as a limitation. Neither
developer should adjudicate a curriculum rule solely from the system they wrote.

## 13. Required Outputs

The evaluation is complete only when the repository or approved research store
contains:

- frozen case files, hashes, catalogue fingerprint, and environment manifest;
- academic approval of anchor decisions and custom-questionnaire content;
- raw structured outputs for every evaluated case;
- independent ranking judgements, pre-adjudication weighted kappa, and adjudication log;
- Precision@3, NDCG@3/5, paired differences, and bootstrap intervals;
- rule accuracy, violation rate, intent/slot metrics, clarification metrics, and failure taxonomies;
- grounding and source-support results with unsupported-claim examples retained;
- path-specific latency, error, timeout, and fallback statistics;
- task success, task time, error observations, SUS, custom-item results, and achieved sample description;
- a deviation log documenting every change after freeze;
- reproducible commands and package/model versions; and
- a claim table distinguishing demonstrated results, prototype observations, limitations, and future work.

## 14. Reporting Rules

The final report may claim only results directly supported by completed blocks. Use
language such as "on the frozen reviewed test set" and state the denominator. Keep
these categories explicit:

- **Verified engineering result:** automated data/test or reproducibility evidence.
- **Objective evaluation result:** frozen expected decisions, grounding judgements,
  or measured latency.
- **Human evaluation result:** independent relevance labels or participant measures.
- **Exploratory result:** weak labels, small subgroup observations, or unplanned analysis.
- **Not evaluated:** planned work for which evidence was not collected.

Do not claim that CurricuPath replaces academic advising, verifies official records,
predicts academic success, or is more accurate/usable than a benchmark unless the
study design and comparable metric support that statement.

## 15. Methodological Basis

This plan uses multiple evaluation facets because recommender accuracy, rule safety,
grounding, usability, and performance are different properties [M6]. Precision@3 is
used for top-list relevance and NDCG@3 for graded ordering [M3]. Two independent
ordinal judges and weighted Cohen's kappa support relevance-label reliability [M4].
The custom questionnaire receives expert content validation through CVI [M5], while
SUS provides a standardised perceived-usability measure [M1, M2]. The task-based
study design is also informed by the academic-advising chatbot evaluation in [B4].

## References

[P1] Gift Vundla and Vukosi Khoza, *AI-Assisted Wits EIE Learning Pathway and
Module Advisor: Project Plan (26P73)*, supplied ELEN4002A/ELEN4012A LaTeX project
plan, 2026.

[P2] Gift Vundla and Vukosi Khoza, [CurricuPath Revised Implementation Plan](revised_implementation_plan_2026-09-08.md),
8 September 2026.

[P3] Gift Vundla and Vukosi Khoza, [CurricuPath Investigation Benchmark Evaluation](investigation_benchmark_evaluation.md),
2026.

[M1] J. R. Lewis, "The System Usability Scale: Past, Present, and Future,"
*International Journal of Human-Computer Interaction*, vol. 34, pp. 577-590, 2018.

[M2] S. C. Peres, T. Pham, and R. Phillips, "Validation of the System Usability
Scale (SUS)," *Proceedings of the Human Factors and Ergonomics Society Annual
Meeting*, vol. 57, pp. 192-196, 2013.

[M3] D. Valcarce, A. Bellogin, J. Parapar, and P. Castells, "Assessing ranking
metrics in top-N recommendation," *Information Retrieval Journal*, vol. 23,
pp. 411-448, 2020.

[M4] M. Warrens, R. Bosker, and H. Kiers, "A Comparison of Reliability
Coefficients for Ordinal Rating Scales," *Journal of Classification*, vol. 38,
pp. 519-543, 2021.

[M5] M. S. B. Yusoff, "ABC of Content Validation and Content Validity Index
Calculation," *Education in Medicine Journal*, 2019.

[M6] E. Zangerle and C. Bauer, "Evaluating Recommender Systems: Survey and
Framework," *ACM Computing Surveys*, vol. 55, pp. 1-38, 2022.

[B4] M. A. Kuhail, H. Al Katheeri, J. Negreiros, A. Seffah, and O. Alfandi,
"Engaging Students With a Chatbot-Based Academic Advising System,"
*International Journal of Human-Computer Interaction*, vol. 39, no. 10,
pp. 2115-2141, 2023. DOI: 10.1080/10447318.2022.2074645.

Before final submission, verify each methodological reference against the original
publication and complete any missing DOI, issue, or page metadata required by the
chosen citation style.
