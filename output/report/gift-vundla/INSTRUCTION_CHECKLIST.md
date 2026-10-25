# Instruction-by-instruction report audit

Updated 25 October 2026. Scope: Gift Vundla's current technical paper, combined appendices and reusable team reporting assets. This checklist applies the latest explicit instructions where earlier feedback conflicts.

## Identity and format

| Instruction | Current implementation |
|---|---|
| Exact final title | AI-Assisted E-Learning Recommendation Platform. |
| Latest request: remove the subtitle | Subtitle removed on 24 October 2026; the main project title is retained. |
| Gift's report; student number next to name | Gift Vundla (2550723), with one author in the technical paper. |
| Use the supplied template | Retained Wits class and KJN style; their original hashes are checked. |
| Four to six pages including references | Main paper is six pages. Body font and line spacing are unchanged. |
| Appendices inside the report | One 52-page PDF contains the paper followed by Appendices A-E, with six bookmarks. |
| Paper must stand on its own | Methods, key counts, results, failure analysis and limitations are explained in the six-page paper. Work allocation is confined to Appendix A. |
| Clear layout and navigation | All final main pages, Appendix A and revised Appendix C were rendered and inspected; Appendix D was inspected in the preceding revision. Merge renders and links are checked against components. |

## Writing, argument and individual contribution

| Instruction | Current implementation |
|---|---|
| Keep the strength of the writing | Specific findings, mechanism-based analysis and material limitations retained. |
| Use the supplied academic-writing guide | Introduction develops context, relevant work, application gap, research question, success conditions and P1-P3. Conclusion connects findings with implications and future evaluation. |
| Introductory sentences before subsections | Sections 2-6 open with short substantive paragraphs. Generic empty signposting was replaced. |
| Remove filler, dense terminology and weakening phrasing | Dense history-confirmation wording was simplified; repetitive qualifications reduced; genuine evidence limits retained. |
| Correct the I/you attribution | Gift is the addressee (you); Vukosi is the speaker (I) in the supplied split. All ten rows use that allocation. |
| Preserve each student's individual task | Main emphasis is Gift's eligibility integration, backend/database contracts, verification and reproducibility; Appendix A credits Vukosi's evidence, interpretation, interface/retrieval and case preparation. |
| Explain failures rather than only headline accuracy | Section 5.3 accounts for 8/12/11 unresolved outputs and distinguishes history-status from target-resolution failures. |
| Support backend/testing claims | Section 3.3 describes transaction, repository and conversation-state boundaries; Section 5.5 and Appendix D record the actual focused test run. |
| Use relevant equations | Equation 1 determines nested-condition behaviour; Equation 2 defines the reported Macro-F1 aggregation. |
| Avoid presenting an application defect as repaired | The outdated Mathematics II explanation is disclosed as a diagnostic; its repair is future implementation work. This report edit does not claim an application-code repair. |
| Reflect, discuss scope changes, paraphrase the shared team account | Appendix A acknowledges the supplied account and uses fresh prose for team reflection, plan changes, actual work and overall reflection. |

## Shared results, plots, tables and references

| Instruction | Current implementation |
|---|---|
| Use only the supplied shared plots/tables in the main paper | Exactly two shared plots and two results tables. Earlier independent diagrams/tables are excluded from the current manuscript and package. |
| Preserve shared observations | Evidence-stratum and clarification counts remain unchanged. No historical model calls were rerun. |
| Compare like with like and remove unresolved notes | Classification uses the same frozen 40 cases per wording for every arm; the obsolete dagger and reconciliation note are gone. |
| Correct reporting scope consistently | Table 2, shared JSON and matched audit agree: mean Macro-F1 0.976/0.976/1.000/0.333/0.278; unsafe totals 0/78, 13/78 and 30/78 as appropriate. |
| Keep evidence-stage differences visible | Original LLM and updated deterministic evidence conditions are identified; matching populations is not presented as matching evidence. |
| Report uncertainty accurately | The 33/33 result is qualified as selected scripted cases and its 95% Wilson interval is stated. Zero observed unsafe decisions is not a deployment guarantee. |
| Keep the same reference works | The same 22-source set is retained; corrected author/publication metadata does not add or substitute works. |
| Start citation numbering at 1 | First citation is Wits [1]; all 22 entries are cited. |
| Cite relevant claims and use specific links | Faculty-rule citation placement was tightened; academic titles link to article/DOI records, and software references target relevant documentation sections or model cards. |
| Both reports should share results/tables/references | Exact current reusable assets are packaged for both authors. The partner's final manuscript has not been supplied, so its final adoption cannot be certified. |

## Appendices and documentary evidence

| Instruction | Current implementation |
|---|---|
| Appendix A at most two pages | Two pages. |
| All work-distribution rows and change column | All ten supplied work areas, both named members and Change from project plan column checked. |
| Explain departure from original plan | Broad recommendation scope to eligibility/clarification/evidence; Streamlit/SQLite to FastAPI/React/PostgreSQL/pgvector described in Appendix A. |
| Appendix B original unmarked plan | Eleven-page supplied unmarked file retained byte-for-byte; exact submitted-file identity still needs confirmation. |
| Specific application screenshots | Appendix C shows unknown prerequisite, completed reply and unmet prerequisite; real captures with synthetic facts and reproduction notes. |
| Generate an explanatory software diagram using tools | Existing editable FigJam sequence retained, with corrected context-return label and refreshed SVG/PDF; larger print panels appear in Appendix D. |
| Include merged minutes from to use | Appendix E preserves all 27 pages unchanged, including the supplied date order. |
| Each appendix self-standing | Each has its own title/context or retains the original document; application and verification appendices state their scope and evidence limits. |
| Keep editable/reproducible files consistent | Source ZIP, shared assets, merge script, instruction audit, JUnit XML, counts and hashes updated together. |

## Conflicts resolved using the latest instructions

- The final requested title overrides earlier variants. The 24 October instruction removes the subtitle; the individual contribution remains evident in the technical content.
- The corrected Gift=you contribution split overrides the earlier mistaken Gift=I interpretation.
- Your request to retain the two shared plots overrides older reviewer advice to replace Figure 1. The integration sequence is supplied in Appendix D, as later requested.
- Your request for short section introductions overrides older advice to delete every lead-in. Current lead-ins convey content rather than merely announce subsections.
- Your requirement to retain the same 22 reference works overrides suggestions to add additional literature. Existing related-work comparisons and targeted links were strengthened within that source set.
- The later like-for-like audit correction supersedes screenshot aggregations 0.973 and 0.280. The corrected reusable table is supplied for both authors; observations were not changed.
- The paper stays six pages; the later instruction to include appendices is met by appending them after those six pages in the same PDF.

## Outstanding evidence and external confirmations

1. Confirm that the supplied `project_plan (1).pdf` is the exact original Ulwazi submission. The retained unmarked file differs slightly from the marked copy, so exact identity is not inferred.
2. The partner must use the current shared tables, plots and bibliography. Matching the partner's final manuscript cannot be checked until that manuscript is available.
3. Seven live PostgreSQL comparisons remain skipped because the imported catalogue was unavailable. The recorded focused result is 55 passed, seven skipped and no failures.

Independent academic adjudication, new frozen-case evaluation and participant usability are future research work, not missing edits or results that can be invented. No official rubric grade or graduate-attribute acceptance is asserted.

## Latest writing revision

The author confirmed Gurahoo's report as the comparator. The subtitle is removed. The paper now explains the request path, meaning of truth values, use of stored conversation state, role of each baseline and significance of unresolved outputs more directly. Figures no longer float ahead of their source placement; reference columns are balanced without changing body font or line spacing. The main paper remains six pages.

## Dedicated Literature Review requirement

Applied: Section 2 is LITERATURE REVIEW, with a short opening and critical discussion of the same cited advising, recommendation, evidence-sufficiency, clarification and abstention research. The introduction retains the problem, research question and predictions. Main sections now run from 1 to 7. The paper remains six pages, with unchanged results and reference works.

## Stronger substantiation and preservation review - 25 October 2026

The literature now explains representative studies and connects their evidence to this investigation. Design choices are tied to integration requirements and verification boundaries. Existing case TS022 demonstrates how its profile, source rationale and completeness confirmation support its reference decision. Results, discussion, conclusion, both tables, both plots, both equations, the 22-work bibliography and all appendix PDFs are preserved. The paper remains six pages without typography changes.

`STRENGTH_AND_INSTRUCTION_REVIEW.md` records the manual argument and instruction review. `strength_preservation_audit.json` records source-block comparisons and baseline hashes. Existing evidence limitations remain explicit; no experiment or hosted model call was added.

## Sections read first - 25 October 2026

Revised the abstract, introduction, conclusion and results against the newly supplied academic-writing notes. The introduction follows context, investigation gap, purpose and predictions; the abstract reports the qualified main findings; results paragraphs lead with outcomes; the conclusion answers the question and develops engineering implications. The conclusion begins at the top of page 6. Literature, design, method and discussion prose is retained.

All shared tables, plots, equations, reference entries, counts, evidence records and appendix PDFs are preserved. The paper remains six pages and the combined report 52, without typography compression. `READING_PRIORITY_WRITING_REVIEW.md` explains the review; `strength_preservation_audit.json` now checks fixed blocks and unchanged sections rather than requiring the newly authorised prose to remain verbatim.
