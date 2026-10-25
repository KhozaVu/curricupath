# Clarification test set v2 (draft labels)

**Purpose.** Test whether asking a question helps. Each "ask" case is a student whose status for
one or more modules is unknown (module history unconfirmed), so a correct system must ask before
it can decide. One scripted reply then supplies the fact, and the FINAL decision is scored.

**Cases (72, frozen by SHA-256 in `freeze.json`).** 33 ask cases (12 single prerequisite, 6
multi-prerequisite with a grouped reply, 9 corequisite, 6 timetable clash), 33 matched controls
(same student, fact already known: no question needed, same label), 6 irrelevant-unknown controls.
Reply wording varies: button text, plain sentence, module-named sentence, "A is completed, the
rest are not".

**Conditions (same cases, no language model).**
- `clarify`: CurricuPath asks, receives the scripted reply, final decision scored.
- `no_clarification`: may not ask; receives the fact as text up front (v2.5 protocol). The engine
  does not read facts from the first message, so this arm cannot use it. It is a weak ablation.
- `assume_absent`: legacy behaviour, unlisted modules count as not completed (a guess).
- `oracle`: facts given as structured data. A ceiling, not a competitor.

**Metrics.** Correct final decision, unresolved, wrong decision, unsafe (answered eligible when
the reference is ineligible), questions asked, and unnecessary questions on controls. Paired
counts per ask case. Labels have two classes only (eligible, ineligible), so Macro-F1 is not the
headline here; counts are.

**Label status.** Developer-proposed, the logical consequence of the stated fact and the cited
rule; the engine was used only to keep cases whose decision flips cleanly. Pending academic
review. Not independent evidence.

**Reproduce.** `py scripts/build_clarification_set_v2.py` (refuses to overwrite),
`py scripts/run_clarification_set_v2.py`, `py scripts/score_clarification_set_v2.py`.
