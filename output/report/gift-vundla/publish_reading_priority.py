"""Publish the inspected writing revision with evidence-preservation checks."""
from pathlib import Path
from hashlib import sha256
import json,re,shutil
from pypdf import PdfReader

P=Path(__file__).resolve().parent
S=P/'revision13'
archive=P/'archive_before_reading_priority_2026-10-25'
archive.mkdir(exist_ok=False)
for name in ['CurricuPath_Gift_Vundla_Report.tex','CurricuPath_Gift_Vundla_Report.pdf',
 'CurricuPath_Gift_Vundla_Main_Paper.pdf','verification.json','instruction_audit.json',
 'final_merge_check.json','README.md','REVISION_NOTES.md','INSTRUCTION_CHECKLIST.md',
 'GA_Comparison_and_Revision_Notes.md','strength_preservation_audit.json',
 'STRENGTH_AND_INSTRUCTION_REVIEW.md','verify_report_delivery.py']:
 shutil.copy2(P/name,archive/name)

before=(S/'before.tex').read_text(encoding='utf8')
after=(S/'CurricuPath_Gift_Vundla_Report.tex').read_text(encoding='utf8')
baseline=json.loads((S/'protected_assets_before.json').read_text())
asset_checks={name:sha256((P/name).read_bytes()).hexdigest()==value for name,value in baseline.items()}
assert all(asset_checks.values())
def digest(s):return sha256(s.encode()).hexdigest()
def normal(s):
 for x in [r'\begin{samepage}',r'\end{samepage}',r'\newpage']:
  s=s.replace(x,'')
 return ' '.join(s.split())
def section(s,a,b):return s[s.index(r'\section{'+a+'}'):s.index(r'\section{'+b+'}')]
unchanged={}
for a,b in [('LITERATURE REVIEW','DESIGN AND IMPLEMENTATION'),
 ('DESIGN AND IMPLEMENTATION','EXPERIMENTAL METHOD'),('EXPERIMENTAL METHOD','RESULTS'),
 ('DISCUSSION','CONCLUSION')]:
 assert normal(section(before,a,b))==normal(section(after,a,b)),a
 unchanged[a]={'end':b,'normalised_sha256':digest(normal(section(after,a,b)))}
blocks={}
for env in ['table','figure','equation','thebibliography']:
 pattern=rf'\\begin\{{{env}\}}.*?\\end\{{{env}\}}'
 original=re.findall(pattern,before,re.S); revised=re.findall(pattern,after,re.S)
 assert original==revised,env
 blocks[env]=[digest(x) for x in original]
original_numbers=set(re.findall(r'\d+(?:\.\d+)?',section(before,'RESULTS','DISCUSSION')))
revised_numbers=set(re.findall(r'\d+(?:\.\d+)?',section(after,'RESULTS','DISCUSSION')))
assert original_numbers==revised_numbers
keys=re.findall(r'\\bibitem\{([^}]+)\}',after)
seen=[]
for group in re.findall(r'\\cite(?:\[[^]]*\])?\{([^}]+)\}',after):
 for key in group.split(','):
  if key not in seen:seen.append(key)
assert seen==keys
assert len(PdfReader(S/'CurricuPath_Gift_Vundla_Main_Paper.pdf').pages)==6
log=(S/'CurricuPath_Gift_Vundla_Main_Paper.log').read_text(errors='replace')
assert not re.search(r'Overfull|undefined references|undefined citations|Rerun to get',log)
shutil.copy2(S/'CurricuPath_Gift_Vundla_Report.tex',P/'CurricuPath_Gift_Vundla_Report.tex')
shutil.copy2(S/'CurricuPath_Gift_Vundla_Main_Paper.pdf',P/'CurricuPath_Gift_Vundla_Main_Paper.pdf')

audit={'date':'2026-10-25','revision':'Abstract, introduction, conclusion and results writing',
 'baseline_sha256':baseline,'protected_asset_hash_checks':asset_checks,
 'source_block_sha256':blocks,'unchanged_section_sha256':unchanged,
 'authorised_prose_changes':['Abstract','Introduction','Results','Conclusion'],
 'layout_changes':['Conclusion starts at the top of page 6','First literature paragraph kept together across columns'],
 'source_blocks_preserved':True,'results_numeric_vocabulary_preserved':True,
 'citations_in_first_appearance_order':True,'first_citation':'wits',
 'main_pages':6,'all_six_final_pages_visually_inspected':True,
 'body_typography_unchanged':True,'latex_overfull_or_undefined':False,
 'manual_review':'Claim scope, denominators, source-to-claim links, failure mechanisms and material limits checked. No independent validation or official GA acceptance inferred.',
 'new_experiments_or_hosted_calls':False,
 'outstanding':['Exact identity of supplied unmarked plan as original submission',
 'Partner final manuscript uses current shared assets','Seven live-database comparisons unexecuted',
 'Independent academic adjudication and participant evaluation not established']}
(P/'strength_preservation_audit.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf8')

note='''# Writing review: sections read first

Revised 25 October 2026 using the newly supplied Academic Writing Notes. This request authorises prose changes to the abstract, introduction, conclusion and results; the earlier claim that their wording was verbatim applied to the preceding revision only.

## Abstract: problem, method, finding, implication

The opening identifies the decision problem: unmet requirements, missing student facts and unverified rules require different responses. The abstract then states the integration and comparisons, gives code-based agreement before and after School evidence, contrasts clarification with assuming omissions are negative, and closes with the failure mechanisms and evidence limits. It preserves the distinction between the 139-case benchmark, common 40-case subset, 33 selected missing-fact cases and separate explanation diagnostic. It does not present 94.2% or 33/33 as general real-student accuracy.

## Introduction: context, niche, investigation

The introduction moves from interest versus registration eligibility to the Wits conditions, then connects the existing advising and recommendation literature to this investigation's integration problem. It distinguishes an omitted result from a missing institutional rule, states the research question and comparison scope, and preserves predictions P1-P3 and their development-informed status. A brief findings preview and roadmap complete the introduction. The gap is local and specific; the text does not claim that all earlier advising systems lack eligibility reasoning.

## Conclusion: answer, evidence, implications

The conclusion states what the investigation established about eligibility reliability, supports it with the qualified code-based and clarification results, and identifies history-completeness handling and final-state explanations as priorities. It ends with the shared-source and synthetic-case limits and the need for independent academic adjudication and unseen-reply tests. It starts cleanly at the top of page 6, keeping its two paragraphs together for readers who skim it first.

## Results: findings before table descriptions

Subsections lead with the observed change, comparison or failure. The School-evidence improvement (39/57 to 57/57) is introduced before the shared table and figure discussion. The interpretation audit still distinguishes the eight unrecognised history confirmations from the additional unresolved targets. Clarification agreement is contrasted with guessing, followed by its message cost, controls and uncertainty interval. The selected implementation checks retain the 55-pass/7-skip record and live-database limitation.

## Preservation and quality review

- Both tables, both figure blocks, both equation blocks and the 22-work bibliography are identical to the previous version.
- All 20 protected asset hashes match: shared counts, plots, scoring audit, diagnostic records, test record, template and appendix components.
- The literature, design, method and discussion prose is unchanged. Two layout controls keep the first literature paragraph together and begin the conclusion on page 6.
- Exact title, Gift Vundla (2550723), corrected individual attribution, all ten Appendix A rows and the change-from-plan column remain intact.
- The paper remains six pages and the combined report 52 pages, with Appendices A-E embedded. Fonts, body line spacing, margins and image sizes were not compressed.
- All six final main pages were rendered and inspected. The assembled report is checked against all component page renders and link destinations.
- Counts, denominators, cases, reference decisions and observations were not changed. This is a writing revision, not a new experiment or application-code repair.

The prior external confirmations and research limitations remain documented: exact original-plan identity, adoption of shared assets by the partner, seven skipped live-database comparisons, independent academic adjudication and participant evaluation. None was supplied by rewriting.

## Writing-guide checks

| Guide principle | Current application |
|---|---|
| Context to gap to purpose | Concrete registration context, supported related-work context, integration problem, research question and predictions. |
| Clarity and simplicity | Findings lead paragraphs; direct verbs replace generic announcements and repeated qualifications. Necessary limits remain explicit. |
| Logical flow | Problem to comparison to observation to implication, with distinct evidence populations. |
| Specific to general conclusion | Qualified results lead to concrete engineering priorities and bounded further evaluation. |
| Substantiation | Numerical findings retain their experimental scope; the reference and figure assets are fixed. |

This review supports technical communication and the existing engineering argument; it does not assign an official grade or certify graduate attributes.
'''
(P/'READING_PRIORITY_WRITING_REVIEW.md').write_text(note,encoding='utf8')
(P/'STRENGTH_AND_INSTRUCTION_REVIEW.md').write_text(note,encoding='utf8')
append='''
## Sections read first - 25 October 2026

Revised the abstract, introduction, conclusion and results against the newly supplied academic-writing notes. The introduction follows context, investigation gap, purpose and predictions; the abstract reports the qualified main findings; results paragraphs lead with outcomes; the conclusion answers the question and develops engineering implications. The conclusion begins at the top of page 6. Literature, design, method and discussion prose is retained.

All shared tables, plots, equations, reference entries, counts, evidence records and appendix PDFs are preserved. The paper remains six pages and the combined report 52, without typography compression. `READING_PRIORITY_WRITING_REVIEW.md` explains the review; `strength_preservation_audit.json` now checks fixed blocks and unchanged sections rather than requiring the newly authorised prose to remain verbatim.
'''
for name in ['README.md','REVISION_NOTES.md','INSTRUCTION_CHECKLIST.md','GA_Comparison_and_Revision_Notes.md']:
 text=(P/name).read_text(encoding='utf8')
 if name in ['README.md','INSTRUCTION_CHECKLIST.md']:
  text=text.replace('Updated 24 October 2026','Updated 25 October 2026',1)
 (P/name).write_text(text+append,encoding='utf8')
print(json.dumps({'promoted':True,'main_pages':6,'protected_assets':len(baseline),
 'four_sections_revised':True,'shared_blocks_preserved':True},indent=2))
