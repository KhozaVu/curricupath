# Comparison with Gurahoo's report and the 24 October revision

The author confirmed Jashna Gurahoo's report as the comparator. The newly attached eleven-page PDF is the marked CurricuPath project plan; it supplies original-scope context and supervisor feedback, not a second completed investigation report.

## What the comparison means

The investigations solve different engineering problems. Gurahoo examines image compression and simulated transmission; CurricuPath examines curriculum eligibility, missing evidence and interpretation of student facts. PSNR, SSIM and channel equations cannot be used to judge eligibility accuracy. The useful comparison is how clearly each report presents its engineering mechanism, investigation design, supporting evidence and limits.

Gurahoo's most useful writing feature is its explanation of successive stages. For example, its codebook discussion connects image complexity to the number of representative colours and then to reconstruction quality. That gives the reader a physical picture before discussing performance. CurricuPath's earlier wording sometimes named frameworks, facts and gates without giving an equally clear account of how one student's reply moved through them. Gurahoo also places its system model in the main paper. CurricuPath retains its integration sequence in Appendix D, consistent with the earlier instruction to keep only the shared result plots in the main paper; Section 3 now supplies a direct verbal workflow. The current paper now has a dedicated Literature Review in Section 2 and concrete improvements in Section 6.3. The review compares prior approaches and connects them to the design and experimental choices.

CurricuPath already made several aspects more explicit: its P1-P3 predictions, known-fact and irrelevant-unknown controls, recorded evidence conditions, complete unresolved-output audit and distinctions between reference agreement and independent correctness. These are strengths to preserve, rather than replacing them with stronger-sounding claims or equations from another domain. They do not establish an official mark or acceptance of a graduate attribute.

## Evidence against the graduate attributes

| GA | Useful comparison with Gurahoo | CurricuPath evidence and revision | Remaining boundary |
|---|---|---|---|
| GA 2: engineering knowledge supported by mathematics | Gurahoo relates quantisation, channel modelling and quality metrics to its communication problem. | Sections 3.1-3.2 connect curriculum alternatives and compulsory conditions to three-valued logic. Section 3.4 follows a Mathematics II reply from unknown to satisfied; Equation 2 defines the classification score. The text now explains the engineering consequence of each expression. | The appropriate mathematics is rule evaluation and classification, not additional channel or compression formulas. Mathematical quantity alone does not establish complexity. |
| GA 4a: design and conduct an investigation | Gurahoo gives a recognisable dataset-to-system-to-output narrative. | Sections 4.1-4.3 explain the 139 cases, common 40-case subset, three matched wordings, evidence conditions and 33 missing-fact cases plus 39 controls. The roles of rules-only, RAG, structured LLM, no clarification, assume-absent and oracle are now described in ordinary language. | Synthetic cases and shared source material limit independent academic validity. |
| GA 4b: experiments and reconciliation with predictions | Gurahoo relates performance curves to SNR, but its main paper does not present an explicit numbered prediction-to-observation comparison. | P1-P3 are stated in the introduction and examined in Section 6.1, including partial support for P1 and the eight history-statement failures. Clarification correctness is accompanied by the added one-question/one-reply cost. | Predictions were development-informed. Scripted-case success does not establish real-student performance. |
| GA 5: appropriate tools and methods | Gurahoo's stage explanations make the purpose of RF and K-Means easy to follow. | Section 3.3 explains what storage, transactions, semantic retrieval, structured interpretation and session state contribute. A favourable similarity score cannot substitute for a passed prerequisite. Tests and audits provide evidence beyond naming the technology stack. | Seven live PostgreSQL comparisons remain skipped; no database-performance comparison is asserted. |
| GA 6a: technical communication | The comparator's input-operation-output paragraphs make several mechanisms concrete. | Removed the subtitle as requested; rewrote the workflow and fact logic; defined the baseline roles; retained substantive section introductions; placed floats after their source positions and balanced the reference columns. The paper remains six pages, with unchanged body font and line spacing. | The explicit request to remove the subtitle supersedes the older subtitle instruction in the writing checklist. |
| GA 9: sourcing, evaluating and using new knowledge | Both reports connect literature and software methods to implementation. | Related-work comparisons motivate evidence sufficiency, clarification and withholding unsupported decisions. Source links, the inspectable rule trace, actual verification record and Appendix A's learning reflection support correct use of the selected methods. | References and tool names alone cannot prove individual learning; attribution remains based on the supplied work split. |
| GA 6b and GA 6c | Both technical papers are only part of the course evidence. | The technical paper can support preparation of the affected-party report and presentation. | Communication with affected parties and oral presentation performance require their separate assessed artefacts; they cannot be certified from this paper. |

## Specific changes to the paper

1. Removed the subtitle while retaining the exact project title and Gift Vundla (2550723).
2. Opened with a concrete advising problem: an omitted result is neither evidence of a pass nor evidence of a failure, and a missing institutional rule requires a different response.
3. Explained the request path before listing the implementation technologies.
4. Explained compulsory versus alternative requirements before the logic equation, and distinguished planned corequisites from completed prerequisites.
5. Explained how conversation state connects a short reply to the original module and how intermediate records support the failure audit.
6. Described why each baseline is included and what information it receives. The reported evidence-stage difference remains explicit.
7. Made the result interpretation more direct: 131/139 is 94.2% on the specified code-based snapshot; unresolved responses remain errors even when they avoid unsafe eligible answers.
8. Linked P1-P3 to the observed mechanisms and gave concrete implementation priorities, including separate completeness flags for completed/current/planned histories.
9. Kept both shared tables, both shared plot assets, all recorded counts, all 22 bibliography works and Appendices A-E. The bibliography includes only a local layout break; reusable reference content is unchanged.
10. Improved use of the six pages through clearer prose and float/reference placement, without adding filler or shrinking the template.

## Reading the project-plan comments in the final scope

The new marked plan raises interaction cost, the candidate-count dependence of Precision@3 and independent review of team-authored labels. The final investigation reports message count for the selected clarification cases. Precision@3 belongs to the earlier ranking proposal and is not a result of the narrowed eligibility investigation; Appendix A explains that scope change. Independent academic adjudication remains absent from the record and is not fabricated as a completed evaluation.

The marked plan has not replaced Appendix B's supplied unmarked plan. Confirming that unmarked file as the exact original submission remains a separate provenance question.

## Sources inspected

- [Gurahoo's supplied report, technical paper pages 1-6](<C:/Users/giftv/Downloads/25R028_Gurahoo, Jashna_(Olutayo Oyerinde) (5).pdf>).
- [Overall assessment form](C:/Users/giftv/Downloads/Investigation_Project_CBO_Updatedv2.pdf).
- [Paper guidelines](<C:/Users/giftv/Downloads/elen4002_4012_paper_guidelines (1).pdf>).
- [New marked project plan](<C:/Users/giftv/Downloads/26g06_84657_11357303_Gift Vundla and Vukosi-Project plan comments (6).pdf>).
- [Supplied academic-writing notes](<C:/Users/giftv/.codex/attachments/0a19f0c1-dcd4-45ec-ae6a-b53f62435a99/Pasted text.txt>).

No external article, benchmark or model run was added to the manuscript as a result of this stylistic comparison. The comparison is a document review, not a re-marking of Gurahoo's project or a reproduction of its experiments.

## Dedicated Literature Review

Section 2 now separates the literature review from the introduction. It covers academic advising and recommendation, evidence sufficiency, clarification and abstention, then relates these approaches to CurricuPath. The following sections have been renumbered. The review retains the same reference works; it does not add model runs, tables or plots.

## Stronger substantiation and preservation review - 25 October 2026

The literature now explains representative studies and connects their evidence to this investigation. Design choices are tied to integration requirements and verification boundaries. Existing case TS022 demonstrates how its profile, source rationale and completeness confirmation support its reference decision. Results, discussion, conclusion, both tables, both plots, both equations, the 22-work bibliography and all appendix PDFs are preserved. The paper remains six pages without typography changes.

`STRENGTH_AND_INSTRUCTION_REVIEW.md` records the manual argument and instruction review. `strength_preservation_audit.json` records source-block comparisons and baseline hashes. Existing evidence limitations remain explicit; no experiment or hosted model call was added.

## Sections read first - 25 October 2026

Revised the abstract, introduction, conclusion and results against the newly supplied academic-writing notes. The introduction follows context, investigation gap, purpose and predictions; the abstract reports the qualified main findings; results paragraphs lead with outcomes; the conclusion answers the question and develops engineering implications. The conclusion begins at the top of page 6. Literature, design, method and discussion prose is retained.

All shared tables, plots, equations, reference entries, counts, evidence records and appendix PDFs are preserved. The paper remains six pages and the combined report 52, without typography compression. `READING_PRIORITY_WRITING_REVIEW.md` explains the review; `strength_preservation_audit.json` now checks fixed blocks and unchanged sections rather than requiring the newly authorised prose to remain verbatim.
