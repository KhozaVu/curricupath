# Eligibility audit ? 20 October 2026

Applied to the running Downloads copy of Cirricupath.

## Confirmed defects and fixes

- Mathematics II (MATH2014A): missing Faculty prerequisite. Requires (MATH1048A OR MATH1042A) AND (MATH1049A OR MATH1043A), both passed. Faculty handbook printed page 84 (PDF page 86).
- Data Structures and Algorithms (COMS2004A): missing the same mathematics prerequisites and Software Development I (ELEN2020A) corequisite. Printed page 78 (PDF page 80).
- Physics II (PHYS2007A): missing both first-year mathematics and PHYS1032A/PHYS1033A prerequisites. Printed page 95 (PDF page 97).
- Engineering Physics IB (PHYS1033A): missing Mathematics IA (old or current code) and Physics IA prerequisites, and MATH1049A corequisite. Printed page 95 (PDF page 97).
- Added seven external-code audit records for older mathematics alternatives; student facts are not rewritten.
- Optional School-grid overrides were applied after source verification, so their own evidence was not verified. Overrides now precede source verification. Registered the supplied workbook and included its source in repository eligibility contexts. Unverified/missing grid evidence requires manual review.

## Verification

2,281 tests passed; seven PostgreSQL integration tests skipped because no imported PostgreSQL catalogue was available. The checks cover every recorded Faculty and School-grid prerequisite/corequisite expression using an independent three-valued reference evaluator: all passed; each prerequisite changed individually to failed/not completed, current, planned or unknown; uniform states; and one-pass-only cases. Service regressions cover both programmes and all four combinations of old/current mathematics alternatives. Existing tests cover programme scope, nested AND/OR, programme-year requirements, contradictions, invalid/unverified evidence, exclusions, academic discretion, repeat clashes, bulk lists and advisor routing.

Prerequisites accept completed credit only. Corequisites accept completed/current/planned as a planning check; a planned course still has to be registered. Unknown facts prompt clarification. Explicit failures cannot be treated as passes.

## Boundaries found by the audit

This is module prerequisite/corequisite eligibility, not a complete registration clearance. Recorded general progression rules (Faculty printed page 56) and renewal rules involving marks, aggregates, credit caps and Senate permission are not fully evaluated. Do not infer admission to a year from an eligible module. Special curricula, transfer recognition and discretionary concessions require School review. No blanket requirement to pass every first-year module was added to individual cross-curricular checks.

The experimental School-grid requirement override remains off in the live configuration. It contains strict legacy-code requirements and differences from the Faculty tables, including explicitly empty requirements; enabling it changes the authority used. The live correction uses the Faculty's explicit mathematics alternatives and works with the grid disabled. Timetable clash checks remain enabled.

Historical evaluation metrics have not been recomputed by this audit. Passing regression cases is not a new product accuracy percentage, nor an independent academic validation of every source transcription.
