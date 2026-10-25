# Investigation plan: managing uncertainty in academic eligibility advice

Status: PROPOSED (2026-10-03). Tags: FACT = measured in this repo; ESTIMATE; ASSUMPTION; PROPOSED.
Nothing here is approved by an academic reviewer. Reference labels are the School registration
reference, adopted; there is no named independent reviewer.

## 1. Question

**Main question.** How effectively does CurricuPath separate eligibility cases that can be decided
from cases that need missing student information or manual academic review, compared with a
rules-only system and LLM-only baselines?

**Supporting questions**
1. Eligibility decisions: agreement with the School registration reference on eligible, ineligible
   and manual-review cases.
2. Evidence sufficiency and abstention: when evidence is insufficient, does the system avoid
   unsupported "eligible" answers and route the case correctly?
3. Clarification: when a material student fact is missing, does asking improve the final decision
   compared with not asking or guessing?
4. Language robustness: does performance change across course-code, module-name and informal wording?

**Claim we can defend (PROPOSED).** CurricuPath treats uncertainty explicitly (answerable / missing
student fact / needs institutional review), and its safe-failure behaviour comes from its rules.
**Claims we cannot make:** that it beats rules-only (it ties; it adds language handling and
clarification on top of the same rules); that results are independently validated; that LLM-only
approaches cannot do this (baselines ran on one low-cost model).

## 2. Two kinds of insufficient evidence (keep them separate)
- **Source insufficient:** the handbook is silent or conflicting, or the case needs discretion
  (grid-only requirements, source conflicts, manual review). FACT: test set v1 already labels this
  per case (`answerable_from_handbook`: 86 true / 53 false of 139; 20 manual-review).
- **Student fact missing:** the answer depends on a status the student has not given. Covered by the
  clarification set v2.

## 3. Work packages

| # | Package | Answers | Needs new runs? | Cost / effort | Status |
|---|---|---|---|---|---|
| A | Evidence-sufficiency split of existing results | Q2 | No (recount) | Hours | Prototype done (table above) |
| B | Abstention metrics (precision, recall of "defer": manual-review + needs-clarification), defined as in the papers you cite | Q2 | No (recount) | Hours | To do |
| C | Wording-level breakdown | Q4 | No (recount; already logged) | Hours | Data exists; needs a table and figure |
| D | Clarification set v3 + re-run | Q3 | Yes, free (no LLM) | 1 day | v2 done; fix clash-partner flaw, decide on a 2nd scripted reply |
| E | Baselines get the grid rules, re-run on the 40 cases | Q1, Q2 fairness | Yes, LLM (about $2-3 on the lite model; ESTIMATE) | Half a day + quota | To do; needed for like-for-like |
| F | Independent spot-check of ~20 reference outcomes by an academic who did not supply the reference | validity | No | Depends on a person | Ask now |
| G | Limitations, future work (usability study, inaccurate student data, stronger-model baselines) | all | No | Writing | Draft |

### A. Evidence-sufficiency split
Report, per system: accuracy and unsafe-eligible rate on source-sufficient vs source-insufficient
cases (and on the 20 manual-review cases alone). Small counts: say so with intervals. **Honest note:**
for rules-only and CurricuPath, manual-review detection depends on a declared reason being present
in the profile or message; it is rule-triggered, not discovered. State this.

### B. Abstention metrics
Define "should defer" = reference is manual_review_required (and, for the clarification set,
"needs a question"). Defer-precision and defer-recall per system; over-referral (deferring when
a decision was possible) and under-referral (deciding when deferral was right). Use the exact
definitions from the abstention paper you cite, and say which.

### C. Wording levels
Table and MATLAB figure of Macro-F1 and unsafe rate by low / medium / high. **Caveat to print:**
medium has 3 and high 4 sentence templates, and CurricuPath's medium/high scores were measured
after the parser fix (development-informed); pre-fix scores are kept. If time allows, add new
unseen phrasings (a small v2 wording set) for a clean test.

### D. Clarification v3
Fix the set so listed clash partners are known (or script the second reply), then re-run the
four conditions. Keep v2 results as the first, disclosed version. Fix the weak ablation: the
no-clarification arm cannot read facts given as text in the first message; either report it as
such or add a structured-input arm that is not the oracle (e.g. "fact withheld, must guess" is
already `assume_absent`). Report counts, not Macro-F1 (two label classes).

### E. Fair baselines
Baselines currently lack the grid requirements that the engine now loads (not like-for-like).
Provide the same rules to the structured-rules baseline; the RAG baseline stays handbook-only by
design (that is what it is). Re-run on the frozen 40 cases at three wordings. Name the model.

### F. Independent check
Ask one lecturer (not the School Admin Manager) to review ~20 cases from the frozen set, chosen
before they see any system output, stratified by label and scenario type. Record reviewer id and
decision in the reviewer fields only if they supply them. Report agreement with the reference.
**Never fill reviewer fields ourselves.**

## 4. Order of work and rough timing (12 days to Open Day, 14 Oct; ASSUMPTION)
1. Day 1: A, B, C recounts and figures (no runs). Send the request for F.
2. Day 1-2: D (v3 set, free re-run).
3. Day 2-4: E (baselines with grid rules), subject to Gemini quota (free tier is thin; ESTIMATE).
4. Day 4-6: write results; if F returns, add the agreement figure.
5. Spare days: unseen-wording set; stronger-model baseline if budget allows.

## 5. Risks
- Circular reference: labels and engine share the registration grid. Mitigation: F, plus stating it.
- Small subset (40 cases, 6 manual-review): wide intervals; report them, avoid small-gap claims.
- Baselines on one low-cost model: findings describe that model only.
- Free-tier quota: batches may stall; the paid option is about $6-15 (ESTIMATE).
- Post-hoc fixes (parser, grid): every post-fix number is development-informed; keep pre-fix numbers.

## 6. Deliverables
Tables: by system, by sufficiency, by wording, abstention, clarification outcomes. Figures (MATLAB):
Macro-F1 by wording, unsafe rate by wording, confusion matrices, sufficiency split, clarification
outcomes. A limitations section (inaccurate student data, no usability study, ethics for any human
study) and a future-work section.
