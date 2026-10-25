"""Verify merged appearance, navigation, fixed assets and current ZIP contents."""
from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile, ZIP_DEFLATED
import json, logging, re
import pymupdf
from pypdf import PdfReader
from assemble_submission import PARTS

logging.getLogger('pypdf').setLevel(logging.ERROR)
P=Path(__file__).resolve().parent

def digest(path): return sha256(path.read_bytes()).hexdigest()

def link_signature(link, offset=0):
    base=[link['kind'], tuple(round(x,3) for x in link['from'])]
    if link['kind']==pymupdf.LINK_URI:
        base += [link.get('uri')]
    elif link['kind']==pymupdf.LINK_GOTO:
        base += [link.get('page',-1)+offset,tuple(round(x,3) for x in link.get('to',(0,0)))]
    else:
        base += [link.get('uri'),link.get('name'),link.get('file')]
    return repr(base)

def verify():
    combined=pymupdf.open(P/'CurricuPath_Gift_Vundla_Report.pdf')
    checks=[]; links=[]; offset=0
    for title,name,expected in PARTS:
        component=pymupdf.open(P/name)
        assert len(component)==expected
        for i,page in enumerate(component):
            merged=combined[offset+i]
            original_pixels=page.get_pixmap(matrix=pymupdf.Matrix(.85,.85),alpha=False)
            merged_pixels=merged.get_pixmap(matrix=pymupdf.Matrix(.85,.85),alpha=False)
            equal=(original_pixels.width,original_pixels.height,original_pixels.samples)==(merged_pixels.width,merged_pixels.height,merged_pixels.samples)
            assert equal,(name,i)
            original_links=sorted(link_signature(link,offset) for link in page.get_links())
            merged_links=sorted(link_signature(link) for link in merged.get_links())
            assert original_links==merged_links,(name,i,'link mismatch')
            checks.append({'combined_page':offset+i+1,'component_page':i+1,'component':name,'render_identical':True})
            links.append(len(original_links))
        offset+=len(component)
        component.close()
    assert offset==len(combined)==52
    combined.close()
    result={'date':'2026-10-25','pages':52,'all_pages_render_identical':True,
        'link_integrity_checked':True,'link_errors':[],'links_checked':sum(links),'checks':checks}
    (P/'final_merge_check.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')

    support=json.loads((P/'strength_preservation_audit.json').read_text())
    assert all(digest(P/name)==value for name,value in support['baseline_sha256'].items())
    current=(P/'CurricuPath_Gift_Vundla_Report.tex').read_text(encoding='utf8')
    for env, expected in support['source_block_sha256'].items():
        actual=[sha256(block.encode()).hexdigest() for block in re.findall(rf'\\begin\{{{env}\}}.*?\\end\{{{env}\}}',current,re.S)]
        assert actual==expected, env
    for heading, record in support['unchanged_section_sha256'].items():
        section=current[current.index(r'\section{'+heading+'}'):current.index(r'\section{'+record['end']+'}')]
        for control in [r'\begin{samepage}',r'\end{samepage}',r'\newpage']:
            section=section.replace(control,'')
        assert sha256(' '.join(section.split()).encode()).hexdigest()==record['normalised_sha256'], heading
    support['combined_pages']=52
    support['combined_render_and_link_checks']='All 52 pages match their current components; all links preserve destinations'
    (P/'strength_preservation_audit.json').write_text(json.dumps(support,indent=2)+'\n',encoding='utf8')

    metadata=json.loads((P/'verification.json').read_text())
    metadata.update({'revision':'Abstract, introduction, conclusion and results writing',
        'revision_date':'2026-10-25','main_paper_sha256':digest(P/'CurricuPath_Gift_Vundla_Main_Paper.pdf'),
        'combined_report_sha256':digest(P/'CurricuPath_Gift_Vundla_Report.pdf'),
        'visual_review':'All six revised paper pages rendered and visually inspected; unchanged appendices retain prior visual review. All 52 merged page renders and link destinations match components.',
        'support_review':'READING_PRIORITY_WRITING_REVIEW.md',
        'preservation_audit':'strength_preservation_audit.json',
        'results_discussion_conclusion_verbatim':False,
        'authorised_prose_changes':['Abstract','Introduction','Results','Conclusion'],
        'discussion_prose_unchanged':True,
        'shared_evidence_and_display_blocks_unchanged':True,
        'conclusion_starts_on_page':6})
    metadata['named_destination_count']=len(PdfReader(P/'CurricuPath_Gift_Vundla_Report.pdf').named_destinations)
    (P/'verification.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf8')
    package_results=[]
    for filename in ['CurricuPath_Gift_Vundla_Editable_Source.zip','CurricuPath_Gift_Vundla_Appendices.zip']:
        path=P.parent/filename
        with ZipFile(path) as z: names=z.namelist()
        if 'Editable' in filename:
            names+=['STRENGTH_AND_INSTRUCTION_REVIEW.md','strength_preservation_audit.json','READING_PRIORITY_WRITING_REVIEW.md']
        temporary=path.with_suffix('.updated.zip')
        with ZipFile(temporary,'w',ZIP_DEFLATED) as z:
            for name in dict.fromkeys(names): z.write(P/name,name)
        with ZipFile(temporary) as z:
            assert z.testzip() is None
            for name in z.namelist(): assert z.read(name)==(P/name).read_bytes(),name
            count=len(z.namelist())
        temporary.replace(path)
        package_results.append({'name':filename,'files':count,'all_entries_match_current_files':True})
    summary={'pages':52,'render_checks':len(checks),'links_checked':sum(links),
             'protected_assets_unchanged':len(support['baseline_sha256']),'packages':package_results}
    print(json.dumps(summary,indent=2))

if __name__=='__main__': verify()
