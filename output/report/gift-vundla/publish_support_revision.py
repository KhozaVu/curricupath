"""Promote the inspected revision and record what was preserved."""
from pathlib import Path
from hashlib import sha256
import json, re, shutil
from pypdf import PdfReader

P=Path(__file__).resolve().parent
S=P/'revision12'
archive=P/'archive_before_support_revision_2026-10-25'
archive.mkdir(exist_ok=False)
for name in ['CurricuPath_Gift_Vundla_Report.tex','CurricuPath_Gift_Vundla_Report.pdf',
             'CurricuPath_Gift_Vundla_Main_Paper.pdf','verification.json',
             'instruction_audit.json','final_merge_check.json','README.md',
             'REVISION_NOTES.md','INSTRUCTION_CHECKLIST.md','GA_Comparison_and_Revision_Notes.md']:
    shutil.copy2(P/name,archive/name)

before=(S/'before.tex').read_text(encoding='utf8')
after=(S/'CurricuPath_Gift_Vundla_Report.tex').read_text(encoding='utf8')
protected=json.loads((S/'protected_assets_before.json').read_text())
checks={name:sha256((P/name).read_bytes()).hexdigest()==value for name,value in protected.items()}
assert all(checks.values())
assert before[before.index(r'\section{RESULTS}'):]==after[after.index(r'\section{RESULTS}'):].replace('\\label{sec:failures}\n','')
blocks={}
for env in ['table','figure','equation','thebibliography']:
    pattern=rf'\\begin\{{{env}\}}.*?\\end\{{{env}\}}'
    blocks[env]=re.findall(pattern,before,re.S)==re.findall(pattern,after,re.S)
assert all(blocks.values())
keys=re.findall(r'\\bibitem\{([^}]+)\}',after)
first=[]
for group in re.findall(r'\\cite(?:\[[^]]*\])?\{([^}]+)\}',after):
    for key in group.split(','):
        if key not in first: first.append(key)
assert first==keys
assert len(PdfReader(S/'CurricuPath_Gift_Vundla_Main_Paper.pdf').pages)==6
log=(S/'CurricuPath_Gift_Vundla_Main_Paper.log').read_text(errors='replace')
assert not re.search(r'Overfull|undefined references|undefined citations|Rerun to get',log)
shutil.copy2(S/'CurricuPath_Gift_Vundla_Report.tex',P/'CurricuPath_Gift_Vundla_Report.tex')
shutil.copy2(S/'CurricuPath_Gift_Vundla_Main_Paper.pdf',P/'CurricuPath_Gift_Vundla_Main_Paper.pdf')

audit={'date':'2026-10-25','revision':'Stronger substantiation within the retained reporting constraints',
 'main_pages':6,'protected_asset_hash_checks':checks,'baseline_sha256':protected,
 'unchanged_source_blocks':blocks,'results_discussion_conclusion_verbatim':True,
 'citations_in_first_appearance_order':first==keys,'first_citation':'wits',
 'all_six_final_pages_visually_inspected':True,'latex_overfull_or_undefined':False,
 'new_experiments_or_hosted_calls':False,
 'new_reference_case':'TS022 from the existing frozen case CSV; no new case or reference label',
 'new_literature_details':'Verified against existing primary sources: Kuhail, Jiang, Chanaa, Aliannejadi and Joren',
 'manual_review':'Argument, source-to-claim links, contribution emphasis, relevant equations and retained validity limits reviewed; no official GA acceptance inferred',
 'outstanding':['Exact identity of supplied unmarked plan as original submission',
    'Partner final manuscript uses current shared assets',
    'Seven live-database comparisons unexecuted',
    'Independent academic adjudication and participant evaluation not established']}
(P/'strength_preservation_audit.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf8')

note='''# Strength and instruction review - 25 October 2026

## Changes made

The literature review now explains what MyAdvisor and AdvisingWise did, what their evidence supports, and why usability or advisor oversight differs from automatic eligibility checking. Chanaa and El Faddouli's prerequisite-aware ranking is connected to its relevance metric and distinguished from institutional registration conditions. Qulac motivates evaluating the outcome of a question. The evidence-sufficiency discussion explains why incomplete curriculum coverage should be examined separately from model reasoning.

The design explanation connects typed fields, source verification, atomic imports, vector reuse and retained conversation state to concrete integration needs. Structured output is explicitly distinguished from a correct interpretation. Documentation supports tool capability; recorded traces and local checks support implementation claims. Framework performance and embedding quality were not comparatively evaluated.

Section 4.1 now follows existing case TS022 from its EFA03 profile and cited corequisite to its adopted ineligible reference. It explains why confirmed completeness differs from an omitted status, then points to the recorded conversational failure. The case, source rationale and reference label already existed; this revision did not invent independent checking.

Repeated introductory and implementation wording was tightened to retain six pages without changing typography. No structural suggestions from the earlier read-only comparison were silently applied: the seven-section structure is retained.

## Preservation checks

| Requirement or strength | Result and evidence |
|---|---|
| Exact title, no subtitle; Gift Vundla (2550723) | Retained and checked. |
| Individual contribution and correct attribution | Main emphasis remains engine/backend integration, verification and reproducibility. Appendix A is byte-identical, retaining Gift=you and Vukosi=I, all ten work areas and the change-from-plan column. |
| Shared results and only the agreed main tables/plots | Both table blocks and both figure blocks are identical to the prior manuscript. Both plot PDFs, shared JSON and matched scoring audit pass baseline hash checks. |
| Preserve the strongest numerical and explanatory writing | Results, discussion and conclusion are verbatim, except an invisible cross-reference label. This preserves denominators, uncertainty, failure mechanisms, predictions and practical recommendations. |
| Same 22 references, direct links and numbering from [1] | Bibliography block and reusable reference file are identical. First appearances follow bibliography order; all 22 works remain cited. Added literature details were checked against the existing primary works. No new reference was introduced. |
| Dedicated literature review and section introductions | Literature Review remains Section 2. Major sections retain substantive opening paragraphs. |
| Relevant equations | Both equation blocks are identical. Truth values are applied to eligibility; Macro-F1 is tied to the reported aggregation. |
| Template and readable six-page paper | Original class, style and preamble hashes match. Fonts, line spacing, plot sizes and margins were not compressed. All six rendered pages were visually inspected. |
| Appendices inside the report | Reassembled after the paper: A (2 pages), B (11), C (3), D (3), E (27), for 52 pages total. Appendix PDFs are byte-identical to the prior versions. |
| No fabricated evaluation or deployment claim | The 55-pass/7-skip record, scripted 33/33 result, source coupling, evidence-stage mismatch, unknown grid rows and absence of independent adjudication remain disclosed. No application fix or fresh benchmark was claimed. |
| Clear, supported academic argument | Reviewed for claim, mechanism, supporting source or record, and implication. The main improvements concern GA2/4/5/6a/9 evidence; this is not an official assessment of graduate attributes. |

## Matters that remain unverified

The partner's final manuscript has not been supplied for exact synchronisation. The supplied unmarked plan is preserved, but its identity as the exact original submission remains unconfirmed. Seven live PostgreSQL comparisons remain skipped. Independent academic adjudication and real-participant evaluation require additional research, not editing. These qualifications remain in the reporting records; stronger prose does not establish missing evidence.

## Primary-source checks for the revised literature

- [Kuhail et al.: MyAdvisor scenarios and usability findings](https://www.tandfonline.com/doi/abs/10.1080/10447318.2022.2074645).
- [Jiang et al.: institutional retrieval, background questions and human validation](https://arxiv.org/abs/2511.05706).
- [Chanaa and El Faddouli: concept prerequisites, metadata matching and NDCG@10](https://link.springer.com/article/10.1186/s40561-024-00301-0).
- [Aliannejadi et al.: clarification and document retrieval](https://arxiv.org/abs/1907.06554).
- [Joren et al.: sufficient context and error analysis](https://proceedings.iclr.cc/paper_files/paper/2025/file/33dffa2e3d2ab74a783d1a8c292f66d9-Paper-Conference.pdf).

The automated preservation record is `strength_preservation_audit.json`; the broader document constraints remain in `INSTRUCTION_CHECKLIST.md` and `instruction_audit.json`.
'''
(P/'STRENGTH_AND_INSTRUCTION_REVIEW.md').write_text(note,encoding='utf8')
add='''
## Stronger substantiation and preservation review - 25 October 2026

The literature now explains representative studies and connects their evidence to this investigation. Design choices are tied to integration requirements and verification boundaries. Existing case TS022 demonstrates how its profile, source rationale and completeness confirmation support its reference decision. Results, discussion, conclusion, both tables, both plots, both equations, the 22-work bibliography and all appendix PDFs are preserved. The paper remains six pages without typography changes.

`STRENGTH_AND_INSTRUCTION_REVIEW.md` records the manual argument and instruction review. `strength_preservation_audit.json` records source-block comparisons and baseline hashes. Existing evidence limitations remain explicit; no experiment or hosted model call was added.
'''
for name in ['README.md','REVISION_NOTES.md','INSTRUCTION_CHECKLIST.md','GA_Comparison_and_Revision_Notes.md']:
    with (P/name).open('a',encoding='utf8') as f: f.write(add)
# The audit date should reflect the current execution, not the previous edit.
ap=P/'audit_report_instructions.py'
t=ap.read_text(encoding='utf8').replace('"date": "2026-10-24"','"date": "2026-10-25"')
ap.write_text(t,encoding='utf8')
print(json.dumps({'promoted':True,'protected_assets':len(checks),'source_blocks_preserved':blocks,'main_pages':6}))
