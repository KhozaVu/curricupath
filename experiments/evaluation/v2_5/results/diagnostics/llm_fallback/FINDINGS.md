# Interpretation fallback: fuzzy matching and LLM (diagnostic)

**Status:** developer diagnostic, not the frozen evaluation. The 34 test cases (`fresh_cases.csv`)
were written and hash-frozen (`fresh_cases.freeze.json`) before any fallback code existed. The
baseline run was then viewed before implementation; the two tiers were specified before the cases
were written and no phrase-specific rules were added. Cases must not be edited; add a new file.

## Design

The fallback runs only when the deterministic interpreter fails: intent `unknown`, or the student
wrote "module" but no module was identified. Prohibited requests and replies to an open
clarification are never reinterpreted. It never decides eligibility. It rewrites an unresolved
message into a canonical request ("Tell me about ELEN2021A") that the unchanged deterministic
pipeline then processes, and records what it did in the response (`interpretation_fallback`).

1. **Fuzzy tier** (free, offline): misspelt words close to the catalogue's own vocabulary are corrected.
2. **LLM tier:** the model sees the message and the programme's module list and must return one
   module code from that list, or null. Answers outside the catalogue are discarded. Gemini is
   tried first; Claude Haiku 4.5 is used only if Gemini refuses the call for quota or availability.

Setting `INTERPRETATION_FALLBACK` = `off` | `fuzzy` (default) | `llm`; per-request field
`interpretation_fallback` for the ablation.

## Ablation on the frozen fresh set (one turn per case)

| Category | Off | Fuzzy | Fuzzy + LLM |
| --- | --- | --- | --- |
| Typos (12) | 11 | 12 | 12 |
| Unusual phrasing (8) | 8 | 8 | 8 |
| Typos with shorthand (3) | 0 | 3 | 3 |
| Descriptions without a name (4) | 1 | 1 | 3 |
| Negatives that must not change (7) | 7 | 7 | 7 |
| **Total (34)** | **27** | **31** | **33** |

- "Off" reproduces the pre-fallback system exactly (27/34).
- The fuzzy tier fixed every typo case. The LLM was called only twice in 34 cases, both for
  descriptions ("the module where you learn about motors and transformers" -> ELEN3003A; "which
  module teaches circuit analysis" -> ELEN2017A). Gemini answered both; the Claude handover was not needed.
- No negative case was wrongly reinterpreted at any tier (public-course search, prohibited request,
  unrelated question, career request, eligibility question, greeting, programme question).
- Remaining failure: "the course about probability for engineers" is answered as a public-course
  search. "Course" deliberately does not trigger the fallback because it legitimately refers to
  online courses too.
- The 60 eligibility pilot decisions are unchanged with the fuzzy tier on by default.

## Caveats

- 34 developer-written cases; small categories. This shows the mechanism works and where each tier
  helps, not real-world accuracy.
- The Claude Haiku handover is covered by unit tests with fake providers only. It has not run live:
  no Anthropic API key or SDK is installed on this machine.
- The LLM tier sends the student's message and the module list to Google (and, on handover, to
  Anthropic). Messages should not contain personal information; the privacy section must say so.

## Addendum 2026-09-29: Gemini-first ordering (`mode_llm_gemini_first`)

The LLM tier was changed after the run above: in `llm` mode the model is now asked first, the fuzzy
tier is used only when no model gives a usable answer, and the model may also return a programme
(EFA03/EFA04) as well as a module. Re-run on the same frozen file (hash check passed), Gemini, paced
at 4.5 s per request, one turn per case. The earlier `mode_llm` output is kept unchanged.

| Category | Fuzzy + LLM (fuzzy first) | LLM first |
| --- | --- | --- |
| Typos (12) | 12 | 12 |
| Unusual phrasing (8) | 8 | 8 |
| Typos with shorthand (3) | 3 | 3 |
| Descriptions without a name (4) | 3 | 3 |
| Negatives that must not change (7) | 7 | 7 |
| **Total (34)** | **33** | **33** |

- Identical correctness case by case. The same single failure remains (F25, "the course about
  probability for engineers", answered as a public-course search; "course" does not trigger the
  fallback by design).
- What changed is which tier did the work: four cases the fuzzy tier used to fix (F07, F21, F22,
  F23) are now resolved by Gemini, so model calls rose from 2 to 6 of 34. On this set, putting the
  model first bought no accuracy and cost four extra external calls.
- None of the 34 cases asks about a programme with a typo, so the new programme output is not
  exercised here. It was checked only by unit tests with fake providers and by a handful of
  ad-hoc live queries during development (for example "tell me aboyt Information Enyineering"
  -> EFA04), which are not evidence of accuracy.
- The Claude Haiku handover remains untested live.
