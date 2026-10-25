# Current shared reporting assets - 23 October 2026

The current six-page Gift report uses two shared results tables, two shared plots and the same 22 reference works supplied by the team. Gift's individual emphasis is engine/backend integration, automated verification and reproducible execution. The ten-row work allocation in Appendix A uses Gift as the addressee (you) and Vukosi as the speaker (I).

## Assets to use in both reports

- `shared_tables.tex`: exact current table content from Gift's manuscript.
- `shared_references.tex`: exact current bibliography, with corrected metadata and direct source links.
- `shared_evidence.pdf` and `shared_clarification.pdf`: the two shared plots.
- `shared_results.json` and `matched_subset_audit.json`: counts, matched-subset metrics, stages and raw-output hashes.

The partner's final editable report/PDF has not been supplied for a complete comparison. Providing identical reusable assets makes synchronisation possible; it does not prove the partner has already applied them. Reference numbering follows each paper's first citation; Gift begins with Wits [1].

## Current results scope

All classification arms use the same frozen 40 cases at each of three wordings. Mean Macro-F1 is 0.976 for CurricuPath and no clarification, 1.000 for rules-only, 0.333 for structured-rules LLM and 0.278 for Handbook RAG. Unsafe totals are 0/78 for deterministic arms, 13/78 for structured LLM and 30/78 for RAG. Deterministic rows retain post-grid conditions; LLM rows retain their original evidence condition. Equal case populations do not remove that evidence difference.

The older screenshot values 0.973 and 0.280 are superseded by the reproducible matched-subset recount. These are corrections to reporting scope and aggregation, not newly generated observations. Both partners should use the corrected table assets. No unresolved reconciliation note or dagger remains in the paper.

Evidence-stratum counts remain [18/63,18/57], [24/63,28/57], [63/63,39/57], [55/63,39/57], [63/63,57/57] and [55/63,57/57]. Clarification outcomes remain 0/0/33 without clarification, 13/11/9 with assume-absent, and 33/0/0 after scripted replies (correct/wrong/unresolved).

The separate `report_evidence.json` describes historical full-set and other recorded conditions. Its populations and stages must not be substituted for the matched-subset table. Prior alignment notes are preserved only as revision history.
