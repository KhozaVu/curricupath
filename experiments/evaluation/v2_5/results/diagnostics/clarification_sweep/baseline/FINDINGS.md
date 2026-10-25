# Why clarification is not working: ambiguity sweep (diagnostic)

**Status:** developer diagnostic, not the frozen evaluation. Prompts, targets and the cooperative
reply were written by the developers to exercise the mechanism. Frozen case files were not read
or changed. Deterministic intent extraction only (no Gemini). Script: `scripts/diagnose_clarification.py`.

**Design:** 10 real modules x 5 ambiguity levels x 4 phrasings = 200 prompts. Level 0 is the exact code,
1 the full name, 2 the name without its series marker (e.g. "Signals and Systems"), 3 a single topic
word ("signals"), 4 no topic ("that module"). Each prompt ran once as a single turn and once with one
reply giving the module's full name if the system asked a question.

## Result

| Ambiguity level | Single turn | With one reply | System asked | Recovered when it asked |
| --- | --- | --- | --- | --- |
| 0 code | 100% | 100% | 0 | - |
| 1 full name | 62% | 62% | 0 | - |
| 2 name without series | 2% | 22% | 8 | 8/8 |
| 3 topic word | 0% | 25% | 10 | 10/10 |
| 4 no topic | 0% | 62% | 40 | 25/40 |

**Clarification works when it is reached.** At levels 2 and 3 every prompt where it asked was
resolved by the reply (18/18). Accuracy rises from about 0% to 22 to 62% wherever it engages. The
low overall curve comes from the system rarely reaching clarification, not from clarification failing.
So the current 13-case frozen set is not "questions that don't need clarification". Most of them are
refused before clarification can run.

## Root causes (in the order a request meets them)

1. **The scope gate refuses module names before module resolution runs** (`app/advisor/scope.py`).
   When the deterministic extractor returns `unknown` and the text has none of 17 generic words
   (module, course, credit...), the request is refused as out of scope. This refused 63 of 200
   prompts, including 15 full module names, all in the three phrasings other than "Who teaches X?".
   The resolver itself correctly finds "signals" -> ELEN2005A, ELEN3012A, ELEN3013A.
2. **Family names that are also public-course keywords are routed to course search.** "Software
   Development" and "Control" were answered as public-course searches (13 prompts answered wrongly).
3. **Resolver stop words are incomplete** (`app/advisor/module_resolution.py`). "Who teaches
   signals?" is cleaned to "who teache signal", so no candidate scores above threshold. The system
   asks the generic "Which module code or full module name?" instead of offering the three
   candidates. The candidate-offering question fired 0 times in 200 prompts.
4. **The scope gate's own clarification keeps no state** (`app/main.py`, ambiguous branch). "Tell me
   about that module" gets "Are you asking about module information, eligibility...?" but no
   pending intent is saved, so the reply is judged from scratch. Replies naming series modules
   ("Electronics II", "Signals and Systems IIA") are refused (15/40 at level 4). "Control I" only
   succeeds because "control" is a public-course keyword.
5. **Wording sensitivity.** Only "Who teaches X?" reaches the module path at levels 1 to 3. The
   same request phrased as "Tell me about X", "What is X about?" or a bare name is refused.

## Caveats

- The level-4 reply names a module, but the question asked was "which feature?". A literal reply
  ("module information") would need a second turn. This affects the level-4 figure only.
- Prompts share targets, so the Wilson intervals are optimistic. Ten modules is a small family set.
- These are developer-written prompts. They diagnose mechanisms; they are not evidence of accuracy
  and must not be substituted for the reviewer's frozen ambiguity cases.

## Proposed fixes (not applied)

In order of expected effect: let requests through the scope gate when module-name resolution finds
candidates; add interrogative and verb stop words ("who", "teaches", "what", "is", "about") to the
resolver; make the scope-gate clarification save a pending intent; check module-name matches before
public-course keywords. Each fix should come with a regression test. Improvements should then be
confirmed on the reviewer's frozen cases, not only on this sweep, to avoid tuning to the diagnostic.

## After the fixes (applied 2026-09-28)

Changes, each pinned by a regression test in `tests/test_clarification_fixes.py`:

1. **Stop words** (`app/advisor/module_resolution.py`): question words and teaching verbs ("who",
   "what", "which", "teaches", "covers", "lecturer"...) are stripped before module lookup.
2. **Promotion of shared names** (`app/advisor/engine.py`, `_prefer_exact_module_name`): a partial
   title shared by several modules becomes a module lookup, so the engine asks "Which module do
   you mean: A or B?" with candidates. Applies only to unknown or course-search requests that are
   short (at most three content words) or use a module-information phrase; public-course cues
   ("find", "online", "learn"...) and programme questions are left alone.
3. **Scope gate order** (`app/main.py`, `app/advisor/scope.py`): the same module-name decision runs
   before the scope check, after prohibited requests are refused, so curriculum titles are no longer
   refused as out of scope.
4. **Stateless scope question:** no separate change was needed. With fix 3, a module-name reply is
   interpretable on its own; a regression test confirms "Electronics II" is answered after the
   "which feature?" question.

Two regressions surfaced while applying them and were fixed in the code, not the tests: a
programme question ("What is the Electrical Engineering degree?") was being turned into a module
lookup, and module lookup was being run on prohibited requests.

### Result (with one reply naming the module)

| Level | Development before | Development after | Held-out before | Held-out after |
| --- | --- | --- | --- | --- |
| 0 code | 100% | 100% | 100% | 100% |
| 1 full name | 62% | 100% | 17% | 100% |
| 2 name without series | 22% | 100% | 17% | 54% |
| 3 topic word | 25% | 100% | 4% | 50% |
| 4 no topic | 62% | 100% | 17% | 100% |

The development set was studied while the fixes were written, so its 100% is expected and is not
evidence of generalisation. The **held-out set** (6 unseen module families, 4 unseen phrasings,
run against the pre-fix commit in a temporary worktree for the "before" column) is the honest
measure: large gains, but not complete. All 23 remaining held-out failures are refusals of two
phrasings, "Can you give me info on X" and "I need details on X", which have more than three
content words and no recognised module-information phrase. The promotion rule partly overfitted to
the development phrasings. This is reported, not patched: fixing it now would use up the held-out
set, and a new unseen set would be needed to confirm any further change. Code replies and name
replies gave identical results.

### Checks on the frozen data

- Eligibility pilot: 0 of 60 CurricuPath decisions changed.
- Frozen ambiguity cases (draft run): intent recognised 13/13 (was 3/13), clarification asked 11/13
  (was 2/13), refused as out of scope 0/13 (was 8/13). The two arms remain identical because the
  reviewer's scripted replies are still pending, so the frozen set cannot yet show an accuracy gain.

Figures: `baseline/clarification_curve.png`, `after_fixes/clarification_curve.png`,
`heldout_after/clarification_curve.png`, and `before_after_curve.png`.
