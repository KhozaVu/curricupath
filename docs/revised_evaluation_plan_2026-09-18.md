# CurricuPath Revised Evaluation Plan

**Version:** 2.5  
**Original plan date:** 18 September 2026  
**Last revised:** 19 September 2026  
**Protocol status:** Frozen for execution; only named personnel, committed hours, and
logged deviations may be added without a new protocol version.  
**Evaluation milestone:** Defensible prototype evidence package before Open Day on
14 October 2026  
**Open Day scope:** Wits EFA03/EFA04 eligibility fidelity, grounding, and a reduced
clarification ablation

## 1. Purpose

This plan replaces architecture-centred evaluation with an outcome-centred study.
Automated tests, PostgreSQL integrity, deterministic gates, and successful fallback
behaviour remain necessary engineering evidence, but they do not establish that the
encoded academic rules agree with independent academic judgement.

The evaluation therefore treats independently labelled Wits advising cases as the
primary reference and compares CurricuPath with a minimal, reproducible handbook-RAG
assistant using the same approved raw sources. ARGObot is the closest published design
reference for this comparator because it answers university-policy questions from a
student handbook using RAG. Its reported results remain literature context rather than
CurricuPath benchmark scores because the institution, source corpus, questions, labels,
and experimental conditions differ.

## 2. Core Investigation

### 2.1 Primary research question

> On independently labelled Wits EFA03/EFA04 advising cases within the supported
> scope, does CurricuPath achieve higher three-class eligibility agreement and fewer
> unsupported curriculum claims than a fixed LLM-RAG baseline using the same approved
> handbook sources?

### 2.2 Narrow contribution

CurricuPath does not claim that deterministic prerequisite checking, RAG, vector
search, or academic chatbots are individually novel. It investigates whether this
combination improves the fidelity and trustworthiness of Wits-specific advice:

- explicit handbook and CBO provenance;
- verified, incomplete, disputed, and superseded evidence states;
- auditable deterministic rule evaluation;
- constrained LLM interpretation and response review;
- clarification instead of silent guessing; and
- deterministic fallback when hosted services are unavailable.

The contribution is therefore the **integration and evaluation of these controls for a
source-bounded Wits advising task**, not the invention of RAG, rule engines, vector
search, ranking, or LLM chat interfaces.

### 2.3 Difference from existing systems

Existing systems tend to emphasise one of three approaches: free-form LLM advice,
retrieval-grounded answers, or structured degree-planning rules. CurricuPath combines
their useful capabilities while assigning each layer a deliberately limited role.

| Existing approach | Typical strength | Remaining problem | CurricuPath difference |
| --- | --- | --- | --- |
| General LLM chatbot | Flexible natural-language interaction | May rely on general knowledge, invent details, or answer outside the evidence | The LLM may interpret and formulate language, but it does not override verified curriculum data or deterministic eligibility gates |
| Handbook RAG, represented by retrieval-only ARGObot | Grounds answers in university documents | Retrieved text is still interpreted generatively; ambiguous, multi-rule, or missing-evidence cases can receive overconfident answers | Curriculum conditions are encoded and evaluated explicitly, while retrieved evidence and page locators remain visible |
| Agentic RAG, represented by full ARGObot | Can search beyond the corpus and escalate through tools | Web results can be unofficial, and tool routing introduces additional variables | The evaluated CurricuPath scope remains closed to approved Wits sources and uses an explicit manual-review state rather than open-web completion |
| Local syllabus RAG, represented by Syllabot | Privacy-conscious retrieval and course-selection support | Retrieval relevance and fluent generation do not by themselves prove rule correctness | CurricuPath separately evaluates eligibility decisions, retrieval, atomic claim support, and refusal/manual review |
| Conventional rule-based planner | Auditable formal decisions | Often brittle for natural-language queries and ambiguous module names | Controlled NLP, aliases, clarification, and course/career explanations sit around rather than inside the decision rules |
| Course recommender | Ranks options according to interests | A highly ranked option may still be academically invalid | Programme, prerequisite, corequisite, exclusion, and evidence gates run before recommendation ranking |

This creates a **controlled hybrid architecture**:

```text
Natural-language interpretation
        -> source and profile resolution
        -> deterministic academic gates
        -> preference ranking of eligible options only
        -> evidence-constrained response formulation
        -> clarification or manual review when authority is insufficient
```

### 2.4 Improvements to be tested

These are proposed improvements, not established findings. Each one must be supported
by a corresponding result before it is presented as an achievement.

| Proposed improvement | Comparator | Required evidence | Primary measure |
| --- | --- | --- | --- |
| More reliable eligibility decisions | Fixed Wits Handbook-RAG | Independent academic labels on identical Wits cases | Three-class macro-F1, balanced accuracy, unsafe false-positive rate |
| Fewer unsupported curriculum claims | Fixed Wits Handbook-RAG | Blind atomic-claim review against approved pages | Unsupported material-claim rate and citation precision |
| Safer treatment of missing or discretionary evidence | Fixed Wits Handbook-RAG | Cases whose correct result is manual review | Correct-escalation and unsafe-overconfidence rates |
| Better handling of ambiguous student language | CurricuPath without clarification | Frozen ambiguous-name, missing-context, and multi-intent scenarios | Final interpretation accuracy and silent-guess rate |
| Better operational resilience | Hosted-service execution path | Controlled Gemini, embedding, network, and database failures | Correct fallback rate and unhandled-error rate |

The primary contribution is supported only if CurricuPath improves the safety and
fidelity measures without producing an unacceptable increase in unnecessary manual
review or clarification burden. This prevents a trivially
conservative system that refuses every difficult case from being labelled superior.

Auditability is treated as a design property and engineering-verification result, not a
comparative accuracy improvement: CurricuPath should make each material deterministic
decision traceable to a rule, source, and locator, whereas the primary RAG baseline has
no equivalent rule trace by design.

### 2.5 Harm model

CurricuPath cannot approve registration or bypass Wits registration controls. Its
credible harms are incorrect planning, wasted time, inappropriate module expectations,
missed alternatives, and misplaced confidence in unsupported advice. The evaluation
must therefore measure both unsafe permissiveness and unnecessary restriction.

## 3. Decision Labels and Error Taxonomy

Every primary eligibility case must have one independently assigned reference label:

| Label | Meaning |
| --- | --- |
| `eligible` | The supplied evidence and declared profile support taking the module. |
| `ineligible` | A known programme, prerequisite, corequisite, exclusion, or progression condition is not met. |
| `manual_review_required` | The available evidence does not authoritatively determine the outcome, or the case requires academic discretion. |

The third class covers cases such as concessions, credit transfers, repeated modules,
incomplete records, contradictory evidence, and decisions delegated to academic staff.
It is not a generic fallback for parser failures.

| System output | Reference label | Interpretation |
| --- | --- | --- |
| Eligible | Ineligible | Unsafe false positive |
| Ineligible | Eligible | Overly conservative false negative |
| Manual review | Manual review | Correct escalation |
| Eligible or ineligible | Manual review | Unsafe overconfidence |
| Manual review | Eligible or ineligible | Unnecessary escalation |

Before the frozen experiment, CurricuPath must expose these three outcomes explicitly
in its structured API. `needs_clarification` must remain separate: clarification asks
for missing user information, whereas manual review acknowledges that the system
cannot authoritatively decide even after the relevant facts are supplied.

For Experiment A, every case must declare whether one clarification turn is permitted
and, if so, provide the exact scripted reply before any system run. Scoring uses the
decision after that one reply. An unexpected clarification on an unambiguous case, a
second clarification request, or failure to produce a decision after the scripted reply
is a decision error and is also counted as unnecessary clarification. Clarification is
never silently converted into `manual_review_required`.

Information must remain equal across Experiment A arms. For every
clarification-permitted case, CurricuPath receives the initial question followed by the
fixed scripted reply, while each non-interactive arm receives a consolidated question
with exactly the same factual content appended before its first and only decision. The
scripted reply may add only the pre-declared missing fact and may not contain hints about
the expected label or relevant rule. Report all Experiment A metrics separately for
clarification-free and clarification-permitted cases as well as for the combined set.
Experiment C, not Experiment A, measures whether eliciting that fact conversationally is
beneficial.

## 4. Compared Systems

### 4.1 Evaluation systems and ablations

| System | Approved-source retrieval | Gemini | Deterministic eligibility | Clarification | Response review |
| --- | --- | --- | --- | --- | --- |
| Wits Handbook-RAG baseline | Yes | Generates the answer | No | No | No |
| Structured-rules LLM arm, exploratory | Raw sources plus the frozen structured rules and evidence states | Generates the answer | No | No | No |
| CurricuPath rules-only evaluation path | Same catalogue | No generated decision | Yes | No | No |
| CurricuPath without clarification, ablation | Same catalogue | Constrained intent and review | Yes | No | Yes |
| Full CurricuPath | Same catalogue | Constrained intent and review | Yes | Yes | Yes |

The Handbook-RAG comparison is primary. The structured-rules LLM arm is exploratory and
receives a read-only snapshot of `rules.csv` and the same evidence states as CurricuPath;
it isolates the effect of deterministic evaluation from the effect of rule curation. The
rules-only path checks the encoded decision layer, while the no-clarification ablation
isolates the effect of clarification. Full CurricuPath measures the deployed workflow.

The structured-rules LLM arm receives the **entire frozen `rules.csv` dataset and the
entire frozen source evidence-state table in context for every case**, in addition to the
same top-k raw handbook/CBO chunks retrieved for the Handbook-RAG arm. It does not
retrieve or select rule rows per question. It uses the same Gemini model identifier,
temperature, prompt skeleton, response schema, timeout, raw-source retriever, and run
policy as Handbook-RAG; its only prompt difference is a clearly delimited structured-rule
context block and the instruction to use it. Both frozen prompts must be stored and
diffed in the manifest so this intended difference is auditable.

### 4.2 Wits Handbook-RAG baseline specification

This comparator adapts the retrieval-only ARGObot architecture to the Wits scope.
ARGObot's published retrieval path chunked a student handbook, embedded and indexed the
chunks, retrieved the three most relevant chunks, and generated an answer with Gemini.
Its separate agentic path added web search and email-based human escalation. Those agent
features are intentionally excluded here so the experiment compares CurricuPath's rule
and control layers with a conventional fixed-source RAG alternative.

The baseline must be deliberately small and reproducible:

```text
Question + synthetic/self-declared profile
        -> retrieve top-k approved handbook/CBO chunks
        -> fixed Gemini model and prompt
        -> one three-class decision, brief explanation, and source/page citations
```

It must use:

- the same frozen Wits source snapshot available to CurricuPath;
- the same student profile and question for each paired case;
- a fixed Gemini model identifier, temperature, prompt, output schema, and timeout;
- a fixed embedding model, chunking method, similarity measure, and `top_k`;
- no web search and no provider knowledge outside the supplied context;
- mandatory source identifiers and page locators in every material answer; and
- a recorded refusal or error rather than an unlogged retry with changed settings.

Select `top_k` once on a small, separate development set containing single-chunk and
multi-rule questions. The development cases must never enter the evaluation set. Choose
the smallest value that achieves **Gold Chunk Recall@K >= 0.90 on the multi-rule
development subset**, record every tested value and the justification in
`rag_retrieval_config.json`, then freeze it before running any evaluation case. If no
tested value meets 0.90 within the model's context budget, freeze the best feasible value
before evaluation and record the unmet target as a baseline limitation. ARGObot's top-3
setting is a starting candidate, not an assumed optimum for Wits multi-rule questions.

Run each Gemini-dependent arm three times per case at the same frozen settings, including
temperature 0. The first pre-registered run is used for the primary paired metrics; runs
two and three measure decision stability and support a clearly labelled majority-decision
sensitivity analysis. Report exact three-run agreement and the proportion of cases whose
decision changes. The deterministic rules-only path runs once per case, with repeat
execution used only to verify byte-equivalent determinism. Never select the most
favourable of the three LLM runs.

The frozen response schema must contain:

```json
{
  "decision": "eligible | ineligible | manual_review_required",
  "answer": "brief user-facing explanation",
  "citations": [
    {"source_id": "...", "page": "..."}
  ]
}
```

The `answer` field requests a concise justification, not hidden chain-of-thought. A
decision without sufficient retrieved evidence must be `manual_review_required`; the
model may not fill gaps from general knowledge.

Parse outputs exactly once against the frozen schema. Invalid JSON, an absent or invalid
`decision`, or a response that cannot be mapped without interpretation counts as a
decision error and remains in the denominator. A material answer with no valid citation
also counts as a citation failure in Experiment B. Preserve the raw response; do not
repair, re-prompt, or exclude malformed outputs after inspection.

It must exclude:

- deterministic prerequisite, corequisite, exclusion, progression, or programme gates;
- post-generation curriculum-rule filtering;
- candidate eligibility filtering before generation;
- CurricuPath's clarification workflow;
- CurricuPath's response reviewer; and
- manually authored corrections to individual outputs.

The baseline may retrieve only the frozen raw handbook and CBO chunks. It must not
retrieve `rules.csv`, validator output, eligibility results, manually prepared rule
summaries, or text generated from CurricuPath's encoded conditions. This prevents the
deterministic rule implementation from leaking into the comparator. Both systems share
the same authoritative evidence snapshot, but only CurricuPath receives its own
structured rule representation.

This anti-leakage restriction applies to the primary Handbook-RAG baseline only. The
separately labelled structured-rules LLM arm intentionally receives the frozen rules and
evidence states, but never CurricuPath decisions or expected labels.

The baseline is an experimental comparator, not a second production application. It
does not require a new interface, separate database, or complete advising platform.

### 4.3 Published-system roles

| Reference | Role in this investigation | What is adopted | What is not adopted |
| --- | --- | --- | --- |
| ARGObot | Principal published RAG-advising reference and basis for the Wits Handbook-RAG comparator | Verified university sources, handbook retrieval, fixed-generation path, source-aware answers, and RAG quality measures | Its reported scores, web search, Gmail escalation, agent routing, or its institution-specific dataset |
| Syllabot | Secondary design reference for privacy, course-selection retrieval, and boundary testing | Structured syllabus evidence, lexical/semantic/multi-evidence query classes, retrieval precision/recall, refusal tests, and evidence-based claim judgement | A local model as the primary comparator, its automatically generated labels as Wits ground truth, or direct score comparisons |
| NileAdvisor and other recommenders | Broader advising and recommendation context | Relevant task and usability measures | Claims of comparative superiority without evaluation on the same Wits cases |

The 2026 Syllabot preprint is useful engineering evidence, but it is not the principal
published benchmark. Replacing Gemini with its local generation model would confound
the architecture comparison with a model comparison. Published percentages from every
reference must remain attached to their original corpus and limitations.

## 5. Evaluation Principles

1. Independent labels are created before reviewers see either system's output.
2. The same case, profile, source snapshot, and allowed evidence are used for paired
   comparison.
3. Unit tests and developer-authored fixtures are engineering evidence, not primary
   research ground truth.
4. No failed, ambiguous, or inconvenient case is removed after results are inspected.
5. Changes after the freeze require a new version and rerun of every affected block.
6. Academic correctness, grounding, relevance, usability, and performance are reported
   separately.
7. Missing evidence must remain visible; neither system may be rewarded for guessing.
8. Raw participant prompts or personal records are not sent to hosted services without
   explicit ethics approval and informed consent.
9. Retrieval quality, answer correctness, claim support, and refusal behaviour are
   separate outcomes; a semantically relevant answer is not automatically correct.
10. Increasing `top_k` after inspecting failures is prohibited because extra context can
    introduce distracting evidence and weaken abstention.

## 6. Frozen Evaluation Package

Create a versioned directory under `experiments/evaluation/v2_5/` containing:

| Artefact | Required contents |
| --- | --- |
| `manifest.json` | Git commit, catalogue fingerprint, source hash, run dates, package versions, model identifiers, prompts, retrieval configuration, seeds, and enabled fallbacks |
| `eligibility_cases.csv` | Case ID, author source, synthetic profile, programme, module, scenario type, independent three-class label, expected material reasons, clarification permitted, scripted reply, consolidated non-interactive input, reviewer IDs, approval state |
| `ambiguity_cases.csv` | Query, profile, intended interpretation, ambiguity type, required clarification, fixed simulated reply, accepted final outcomes |
| `retrieval_development_cases.csv` | Separate non-evaluation questions, gold chunks, query class, tested `top_k` values, and selection rationale |
| `grounding_cases.csv` | Question, expected atomic claims, allowed sources/pages, prohibited claims, evidence state |
| `rag_prompt.md` | Frozen baseline system instruction, output schema, and citation requirements |
| `structured_rules_prompt.md` | Frozen structured-rules prompt with only the documented context-block difference from `rag_prompt.md` |
| `rag_retrieval_config.json` | Corpus exclusions, chunking, embedding model, index version, similarity method, `top_k`, and deterministic tie-breaking |
| `curricupath_outputs.jsonl` | Immutable structured outputs keyed by case and pre-registered run ID |
| `rag_outputs.jsonl` | Three immutable baseline outputs keyed by case and pre-registered run ID |
| `structured_rules_llm_outputs.jsonl` | Three exploratory outputs per case from the LLM-over-structured-rules arm, keyed by pre-registered run ID |
| `grounding_claim_labels.csv` | Blind atomic-claim support labels and reviewer IDs |
| `usability_protocol.md` | Counterbalanced tasks, scripts, success criteria, permitted hints, and stopping rules |
| `performance_cases.csv` | Fixed requests, path, warm-up state, repetition count, and expected response class |
| `deviations.md` | Every post-freeze change, reason, affected cases, and rerun decision |
| `results/` | Immutable raw outputs followed by reproducibly generated analysis tables |

All identifiers, missing-value conventions, labels, and metric formulas must be defined
in a versioned `data_dictionary.md` before the final run.

## 7. Experiment A: Primary Eligibility Fidelity

### 7.1 Objective

Compare CurricuPath and Wits Handbook-RAG against independent academic judgement on
the same EFA03/EFA04 cases. Analyse the structured-rules LLM arm separately to explore
whether any gain is attributable mainly to rule curation or to deterministic evaluation.

### 7.2 Case set

Target 60-90 synthetic cases, with at least 15 cases in each decision class and
meaningful coverage of both programmes. Include:

- correct and wrong programme membership;
- compulsory and elective modules;
- satisfied and missing prerequisites;
- alternative and nested prerequisite expressions;
- completed, current, planned, and missing corequisites;
- exclusions, progression, and selection-count rules;
- incomplete, disputed, superseded, and contradictory evidence;
- concessions, credit-transfer, repetition, and incomplete-record vignettes;
- lowercase codes, missing suffixes, names, and ambiguous names; and
- cases where the handbook genuinely does not settle the answer.

Cases must be drafted from the frozen source snapshot without consulting system
outputs. They should use synthetic profiles and contain no real student identifiers.
Developers may draft the planned coverage cases, but at least one academic reviewer must
also contribute a concealed subset before seeing Section 7.2's scenario list or any
system output. Record each case as `developer_drafted` or `reviewer_drafted`, preserve
that distinction through adjudication, and report results separately for both subsets.
The concealed reviewer cases test scenarios not bounded by the developers' rule model.

### 7.3 Independent labelling

At least one suitable EIE academic reviewer must approve the reference decision and
material rationale. A second independent knowledgeable reviewer is strongly preferred.
Reviewers receive the case and authoritative evidence, not system outputs. Record
pre-adjudication agreement and preserve disagreements. Resolve disagreements through a
documented adjudication process; do not let either developer silently decide contested
cases from the implementation.

Reviewer-drafted concealed cases should be labelled by a second academic or suitably
qualified independent reviewer who did not draft them. If only one academic is
available, the author-labelled concealed subset must be identified and reported as a
limitation rather than described as independently labelled. When reviewer participation
is secured, confirm and record the hours committed separately for case drafting, case
labelling, and disagreement adjudication; do not assume one agreement covers all three.

### 7.4 Primary metrics

- Three-class macro-F1.
- Balanced accuracy.
- Per-class precision, recall, and F1.
- Confusion matrix.
- Unsafe false-positive rate.
- Overly conservative false-negative rate.
- Correct-escalation rate.
- Unsafe-overconfidence rate on manual-review cases.
- Unnecessary-escalation rate.
- Material-reason completeness.
- Three-run decision agreement for every Gemini-dependent arm.

Report paired CurricuPath-minus-RAG differences with case-level bootstrap 95%
confidence intervals. With a small sample, emphasise effect size and error type rather
than statistical significance. An exact paired test may be reported for a pre-declared
binary safety error outcome, but it does not replace the three-class analysis.

This is a precision-limited prototype study. With only about 15 cases in a class,
class-specific recall intervals can be very wide, and paired macro-F1 intervals may also
span practically important differences. The study is designed to detect large failure
patterns, not establish small improvements. Report `inconclusive` when intervals do not
support a directional claim; do not interpret a non-significant result as equivalence.
Primary metrics use pre-registered run 1. Report the three-run majority sensitivity
analysis and decision-change rate separately, without treating repeated runs as
independent cases.

### 7.5 Interpretation

Zero ineligible recommendations remains a release objective, not the primary research
result. A perfectly enforced but incorrectly encoded rule counts as an evaluation error.
All disagreements must be categorised as source, label, rule encoding, parser,
condition-evaluation, clarification, baseline retrieval, generation, or explanation
failures.

The structured-rules LLM arm is analysed separately. If it approaches CurricuPath's
performance, the evidence supports the value of structured curation but not a strong
claim that deterministic evaluation itself caused the gain. If the rules-only and full
CurricuPath paths outperform it, that more directly supports the deterministic-control
claim. Either outcome must be reported.

## 8. Experiment B: Grounding and Claim Support

### 8.1 Objective

Determine whether CurricuPath makes fewer unsupported material claims than the RAG
baseline.

### 8.2 Protocol

Use questions covering programme membership, prerequisites, corequisites, exclusions,
progression, lecturers, scope, workload, prescribed materials, source status, and known
missing CBOs. Include simple, multi-fact, conflicting-source, and no-answer cases.

Stratify the cases using a retrieval-oriented taxonomy adapted from Syllabot:

- lexical-match cases with explicit module codes or exact handbook wording;
- semantic-paraphrase cases with reduced keyword overlap;
- multi-evidence cases requiring facts from more than one approved chunk; and
- out-of-scope or unsupported cases for which refusal/manual review is correct.

Blind reviewers split each answer into atomic material claims. Each claim receives one
label:

- `supported`: the cited approved evidence entails the claim;
- `unsupported`: the approved evidence does not support the claim; or
- `unverifiable`: the source snapshot is insufficient to decide.

The protocol must define materiality and claim segmentation before outputs are judged.
Reviewers should not be shown the system identity where output formatting can be safely
normalised. On a pre-declared overlapping sample, two reviewers must independently
segment claims before support labelling. Report segmentation agreement using exact or
span-overlap agreement together with the support-label agreement statistic.

Name the grounding judges in `manifest.json` before outputs are generated. At least one
grounding judge must be a non-developer who did not implement CurricuPath's response
templates. If only developers are available, report Experiment B as a blinded-formatting
pilot rather than independent grounding evidence.

### 8.3 Metrics

- Supported material-claim rate.
- Unsupported material-claim rate.
- Unverifiable-claim rate.
- Citation precision.
- Expected-entity recall.
- Explanation completeness.
- Correct abstention/manual-review rate.
- Unsupported-answer rate on out-of-scope cases.
- Gold-chunk Precision@K and Recall@K for the baseline retriever.
- Mean and median material claims per answer.
- Claim-segmentation agreement on the double-reviewed subset.
- Count of invented module codes, rules, lecturers, materials, or source IDs.

Report results by claim type and evidence state. A fluent paragraph with one unsupported
prerequisite is not counted as wholly correct.

## 9. Experiment C: Ambiguity and Clarification

### 9.1 Objective

Measure whether CurricuPath's clarification workflow reaches the intended interpretation
and correct advice more reliably than the same CurricuPath pipeline with clarification
disabled. This ablation isolates the clarification layer rather than awarding an
interactive system an automatic advantage over a non-interactive baseline.

### 9.2 Dataset

Use voluntarily contributed, anonymised query patterns where ethics permits, supplemented
by clearly labelled realistic vignettes. Include:

- partial module names such as `electronics` or `signals`;
- Roman/numeric series and A/B variants;
- missing programme or study year;
- vague elective and career questions;
- workload and difficulty ambiguity;
- multi-intent questions; and
- overly general or overly specific wording.

Do not use real student records. Preserve the underlying scenario ID so paraphrases are
not treated as independent evidence. Every case must contain the exact simulated reply
to the expected clarification. The runner supplies that reply once without human
improvisation. Unexpected questions receive the case's pre-declared neutral fallback
reply or are scored as an unresolved clarification according to the data dictionary.

### 9.3 Metrics

- Initial intent and entity accuracy.
- Appropriate-clarification rate.
- Unnecessary-clarification rate.
- Correct final interpretation.
- Correct final advice after clarification.
- Second-attempt success.
- Mean turns to resolution.
- Silent-guess rate.
- Abandonment and unhandled-error rate.

The primary comparison is full CurricuPath versus CurricuPath with clarification
disabled. For the Handbook-RAG baseline, report only first-turn interpretation,
abstention, and silent-guess rates; do not claim a fair final-resolution comparison and
do not add a custom multi-turn policy after the experiment begins.

## 10. Experiment D: Formative Usability

**Status:** Deferred until after Open Day unless the required ethics/institutional
approval already exists before recruitment. It is not part of the 14 October core
evidence package.

### 10.1 Objective

Compare whether representative users can complete advising tasks more accurately and
efficiently with CurricuPath than with handbook-only lookup.

### 10.2 Design

After approval, use a small counterbalanced within-participant pilot. Each participant
completes equivalent task sets under two conditions:

1. CurricuPath; and
2. the approved handbook/source materials without CurricuPath.

Counterbalance condition and task order to reduce learning effects. Use synthetic
profiles and predefined tasks. If the achieved sample is small, report it as formative
and do not make population-level claims.

### 10.3 Tasks

The comparative task set must contain tasks with a natural equivalent in both
conditions. Cover approximately five to six tasks:

1. Determine whether a student may take a named module.
2. Identify and explain a missing prerequisite or corequisite.
3. Identify fourth-year electives related to a stated interest.
4. Locate lecturer, scope, workload, or material information.
5. Recognise that evidence is missing or academic review is required.
6. Locate the supporting source or handbook page.

Interface-specific tasks such as resolving a chat ambiguity or correcting a profile
selection may be observed in a separate CurricuPath-only usability block. They must not
be included in the paired handbook comparison.

### 10.4 Measures

- Correct task completion against the independent answer key.
- Time on task.
- Attempts, navigation errors, hints, and abandonment.
- Participant confidence after each task.
- System Usability Scale for CurricuPath.
- Separate perceived usefulness, explanation clarity, and trust items.
- Brief non-leading qualitative comments.

Perceived correctness does not replace the independently assessed correctness in
Experiment A.

## 11. Experiment E: Recommendation Relevance

**Status:** Deferred until after Open Day. Eligibility-gate invariants remain engineering
checks, but recommendation-quality claims require independent relevance judgements.

Public-course and elective ranking remain secondary to the primary eligibility study.
If time and independent judges are available, compare only one change at a time:

1. rule-only ordering;
2. deterministic preference/content scoring over the same eligible candidate pool;
3. model-assisted scoring over that same eligible candidate pool; and
4. the selected scoring method with clarification.

Every research arm receives the same pre-gated eligible candidate pool. The ungated
path is tested only as an engineering invariant and is not presented as a research
comparator.

Use two blinded judges, a frozen candidate pool, randomised display order, and a 0-3
relevance scale. Report Precision@3, NDCG@3, mean judged relevance, and
pre-adjudication weighted kappa. Eligibility violations are reported separately as
engineering defects. Weak or developer-generated labels are
pipeline checks, not confirmatory evidence. If independent labels are incomplete by the
deadline, report this block as not evaluated rather than promoting weak-label results.

## 12. Engineering Verification

The following checks support reproducibility and operational readiness but are not
research hypotheses:

- CSV validation and PostgreSQL import consistency;
- PostgreSQL versus CSV deterministic-output parity;
- schema migration and transactional rebuild behaviour;
- pgvector retrieval integrity;
- zero known-ineligible items after recommendation gating, tested as an invariant rather
  than claimed as a research contribution;
- session expiry and privacy-conscious logging;
- Gemini, Hugging Face, PostgreSQL, and network failure fallbacks;
- deterministic repeatability;
- material deterministic decisions traceable to a rule ID, source ID, and locator;
- median, p95, minimum, and maximum response time;
- error, timeout, and fallback rates; and
- Docker/partner setup reproducibility.

Use five unmeasured warm-ups followed by at least 30 measured requests per execution
path. Record the machine, network, model, configuration, hosted calls, and catalogue
fingerprint. Do not compare local p95 latency directly with a published mean from a
different environment.

## 13. Analysis Plan

| Evidence | Planned analysis |
| --- | --- |
| Eligibility | Three-class confusion matrices, macro-F1, balanced accuracy, per-class metrics, paired differences, bootstrap intervals, clarification strata, author-source strata, exploratory structured-rules-LLM results, three-run stability, and error taxonomy |
| Reviewer agreement | Raw agreement and an appropriate chance-corrected statistic before adjudication; preserve disagreement counts |
| Grounding | Claims per answer, claim-segmentation agreement, atomic claim counts, and support rates by claim type, source state, and system |
| Ambiguity | Full-versus-no-clarification ablation, intent/entity accuracy, clarification rates, turns, final correctness, and scenario-clustered results |
| Usability | Correct completion, paired time differences, errors, hints, confidence, SUS, and achieved sample description |
| Ranking | Precision@3, NDCG@3, mean relevance, violation rate, weighted kappa, and profile-cluster bootstrap intervals |
| Engineering | Path-specific latency, error, timeout, fallback, parity, and repeatability results |

Freeze analysis scripts and random seeds before final output inspection. Keep all
paraphrases and repeated observations from one underlying scenario in the same
resampling unit. Report denominators, missing data, failed calls, and fallbacks.

## 14. Threats to Validity and Controls

| Threat | Control |
| --- | --- |
| Developers encode and judge the same rules | Independent academic labels created before system runs |
| Developers anticipate every manual-review scenario | Include concealed reviewer-drafted cases and report developer/reviewer subsets separately |
| Rule curation and deterministic evaluation are confounded | Add an exploratory LLM-over-identical-structured-rules arm and interpret it alongside the rules-only path |
| Handbook ambiguity is forced into a binary answer | Explicit `manual_review_required` class |
| RAG baseline is weakened artificially | Same sources, profile, model family, retrieval snapshot, fixed prompt, and citation requirements; select `top_k` on a separate development set |
| CurricuPath receives more facts through clarification | Append the identical scripted fact to every non-interactive arm and report clarification strata separately |
| LLM randomness changes conclusions | Use pre-registered run 1 for primary metrics and two additional runs only for stability and majority sensitivity analysis |
| RAG baseline receives CurricuPath's encoded answer | Exclude rules, eligibility outputs, validator messages, and derived rule summaries from its index |
| RAG baseline is improved after seeing results | Freeze configuration and record every failure without prompt tuning |
| CurricuPath uses additional evidence unavailable to RAG | Declare the primary source subset and provide the same eligible documents to both systems |
| Output style reveals system identity to grounding judges | Normalise formatting and blind system identity where practical |
| Hosted model changes | Pin the exact model identifier, prompt, run period, and response metadata |
| Extra retrieved context makes unsupported answers more likely | Freeze `top_k`; report retrieval metrics and refusal rate by query class |
| Semantic relevance hides factual errors | Use independent decisions and atomic evidence-support labels rather than relevance alone |
| CurricuPath is guaranteed to win a multi-turn clarification comparison | Compare full CurricuPath with a no-clarification ablation; use RAG only for first-turn and silent-guess measures |
| Human follow-up steers clarification outcomes | Store one fixed simulated reply and a neutral fallback rule for every ambiguity case |
| Malformed model output is silently discarded | Count schema-invalid outputs as decision errors and keep them in all denominators |
| Shorter templated answers gain an artificial grounding advantage | Report material claims per answer, explanation completeness, and segmentation agreement |
| Synthetic cases omit real ambiguity | Add independently drafted academic cases and voluntary anonymised query patterns where permitted |
| Small manual-review class inflates metrics | Require minimum class coverage and report per-class denominators |
| Usability learning effects | Counterbalance conditions and use equivalent task sets |
| Small convenience sample | Frame the study as formative and avoid population-level claims |
| Post-freeze fixes hide failures | Version fixes, preserve original outputs, and rerun all affected cases |
| Raw prompts expose participant information | Use synthetic profiles and retain participant text only with approval and consent |

## 15. Ethics and Data Handling

Confirm applicable ethics and institutional requirements before recruiting students or
staff, collecting voluntary prompts, recording screens, or sending participant text to
Gemini or Hugging Face. Obtain informed consent and make participation voluntary.

Use random study identifiers and keep any consent key separate. Do not collect student
numbers, marks, official transcripts, health information, financial information, or
other unnecessary personal data. Define access, retention, deletion, and withdrawal
procedures before collection. Synthetic evaluation cases may use hosted services when
the approved protocol permits it.

## 16. Schedule to Open Day

| Dates | Work | Exit artefact |
| --- | --- | --- |
| 19-21 Sep | Approve protocol; secure named academic reviewer(s) and a non-developer grounding judge; confirm drafting, labelling, adjudication, and grounding hours | Approved protocol, named commitments, workload record, and data dictionary |
| 22-25 Sep | Implement the three runners and no-clarification ablation; tune retrieval only on the development set | Tested runners and frozen retrieval configuration |
| 22-26 Sep | Developers draft planned cases; academic reviewer independently contributes concealed cases | Versioned unlabeled case pool with author-source fields |
| 27 Sep-1 Oct | Independent academic labelling, disagreement resolution, source freeze, and manifest generation | Frozen labelled cases and catalogue fingerprint |
| 2-5 Oct | Generate frozen eligibility and Experiment B answers for CurricuPath, Handbook-RAG, and the structured-rules LLM arm | Immutable eligibility and grounding outputs |
| 5-7 Oct | Segment, blind, and judge grounding claims | Immutable grounding labels and agreement records |
| 7-8 Oct | Run reduced clarification ablation and essential engineering checks | Ambiguity-ablation and reliability results |
| 9-11 Oct | Run analysis, prepare tables, inspect failures, and document limitations | Reproducible results and claim table |
| 12-13 Oct | Freeze demo, rehearse, and verify offline fallback | Demonstration build and recovery checklist |
| 14 Oct | Open Day | Present only completed, supported findings |

Experiments A and B are the committed Open Day evidence package. Experiment C is reduced
to the full-versus-no-clarification ablation. Experiments D and E are post-Open Day work.
If a named academic reviewer is not secured by 21 September, the work may continue only
as a pilot and must not make independently validated accuracy claims. Never substitute
developer or LLM judgements for the missing academic review. If no non-developer
grounding judge is secured, Experiment B must likewise be labelled a pilot.

## 17. Ownership

Assign named owners before case creation. Keep these roles distinct where possible:

| Role | Responsibility | Assignment requirement |
| --- | --- | --- |
| Evaluation lead | Freeze protocol, track deviations, and assemble the evidence package | Name before case drafting |
| Baseline owner | Implement and freeze the minimal Handbook-RAG runner | Name before implementation |
| CurricuPath run owner | Export structured outputs without changing the case set | Name before source freeze |
| Academic reviewer(s) | Draft concealed cases where agreed; independently label eligibility and material reasons | Name and confirm hours by 21 September; use a second reviewer for reviewer-authored cases where possible |
| Grounding judge(s) | Segment and label atomic claims without seeing system identity where practical | Name by 21 September; include at least one non-developer |
| Usability facilitator | Follow the fixed script and predefined hint policy | Deferred until approval exists |
| Analyst | Run versioned metrics and preserve immutable raw outputs | Name before final runs |
| Supervisor | Approve scope, reviewer independence, and responsible claims | Confirm before protocol freeze |

Record the actual names, affiliations or project roles, conflicts, and committed hours in
`manifest.json`; this plan does not invent assignees who have not yet agreed.

Disclose unavoidable role overlap as a limitation. Neither developer should be the sole
authority for cases testing rules they encoded.

## 18. Reporting and Claims

The final evaluation chapter must answer these questions explicitly:

1. **What is the contribution?** A source-bounded, controlled hybrid advising
   architecture for Wits EFA03/EFA04 that separates natural-language interaction from
   deterministic academic decisions, gates ranking by eligibility, and represents
   uncertainty through clarification and manual review.
2. **What is different?** Unlike a conventional handbook-RAG assistant, CurricuPath
   does not ask an LLM alone to infer whether curriculum conditions are met. Unlike a
   standalone rule engine, it accepts varied student language, resolves ambiguity, and
   explains decisions using cited evidence. Unlike an ungated recommender, it ranks only
   after academic and evidence checks pass.
3. **What does it improve?** Only improvements demonstrated by the frozen experiments
   may be claimed. Candidate improvements are eligibility agreement, claim grounding,
   safe escalation, ambiguity resolution, and resilience. Auditability and recommendation
   gating are engineering-verification properties; usability remains a post-Open Day
   question.

Use a contribution evidence table in the results chapter:

| Contribution claim | Baseline/comparator | Result and interval | Supported? | Limitation |
| --- | --- | --- | --- | --- |
| More reliable eligibility decisions | Wits Handbook-RAG | To be completed after evaluation | Yes / No / Inconclusive | Case coverage and reviewer limits |
| Added value of deterministic evaluation beyond rule curation | Structured-rules LLM arm and rules-only CurricuPath | To be completed after evaluation | Yes / No / Inconclusive | Exploratory arm and model variability |
| Fewer unsupported claims | Wits Handbook-RAG | To be completed after evaluation | Yes / No / Inconclusive | Source and claim-segmentation limits |
| Safer ambiguity handling | CurricuPath without clarification | To be completed after evaluation | Yes / No / Inconclusive | Scenario and scripted-reply limits |

The final report must distinguish:

- **Engineering verification:** tests, validation, decision traceability/auditability,
  recommendation gating, parity, reproducibility, and failure handling.
- **Primary research result:** agreement with independent three-class eligibility labels.
- **Grounding result:** independently judged material-claim support.
- **Human evaluation result:** observed task performance or participant ratings.
- **Exploratory result:** incomplete ranking labels, weak labels, or unplanned analysis.
- **Not evaluated:** any planned block lacking sufficient evidence.

Before evaluation, the project may state:

> CurricuPath builds on rule-based, recommender, and RAG advising systems by combining
> explicit Wits source provenance, auditable rule evaluation, clarification, and
> constrained LLM assistance.

Only if supported by the frozen paired results may it later state:

> On the independently labelled Wits EFA03/EFA04 evaluation set, CurricuPath achieved
> higher three-class eligibility agreement and fewer unsupported material claims than
> the fixed Handbook-RAG baseline.

Always state the sample size, confidence interval, model/source snapshot, and supported
scope. Do not claim official registration approval, transcript verification, academic
success prediction, replacement of advisors, or general superiority over published
systems.

## 19. Completion Criteria

The core evaluation is complete when the repository or approved research store contains:

- a frozen source, model, prompt, retrieval, and environment manifest;
- independently approved three-class eligibility labels;
- immutable outputs from CurricuPath, Handbook-RAG, and the exploratory structured-rules LLM arm;
- three-class metrics and the complete error taxonomy;
- blind atomic grounding labels and unsupported-claim examples;
- reduced full-versus-no-clarification outcomes;
- engineering reliability results;
- a deviation log and reproducible analysis commands; and
- a claim table separating demonstrated findings from limitations.

Usability and ranking are explicitly deferred blocks and are not required for the Open
Day evidence package. They become completed results only after their participant,
approval, or independent-judge requirements are met.

## 20. Methodological Basis

This plan builds on the original CurricuPath project plan, the revised implementation
plan, the benchmark investigation, and the supplied critique. ARGObot is the closest
published RAG-advising reference for the fixed Handbook-RAG comparator. Syllabot is a
secondary reference for local/privacy-conscious deployment, retrieval-oriented query
classes, and refusal evaluation. NileAdvisor remains useful rule-plus-language and
recommendation context. Published results provide context and evaluation ideas, not
directly comparable performance baselines.

The existing detailed methodological references for SUS, ranking metrics, agreement,
content validation, and recommender evaluation remain listed in
`docs/evaluation_plan.md`.

### Selected advising-RAG references

1. Michael Tamascelli, Olivia Bunch, Blake Fowler, Maryam Taeb, and Achraf Cohen,
   "Academic Advising Chatbot Powered with AI Agent," *Proceedings of the 2025 ACM
   Southeast Conference*, 2025, DOI: 10.1145/3696673.3723065.
2. Feng Li and Yoritaka Iwata, "A Locally Deployed RAG-Based Academic Advising System
   for Course Selection," arXiv:2606.02983, 2026.

Before submission, verify final bibliographic formatting against the original
publications and the required university citation style.
