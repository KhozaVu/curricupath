from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import simpleSplit
import json

P = Path(__file__).resolve().parent
W, H = landscape(A4)
c = canvas.Canvas(str(P/'Appendix_D_Integration_and_Verification.pdf'), pagesize=(W,H))
c.setTitle('Appendix D - CurricuPath Integration and Verification')
c.setAuthor('Gift Vundla (2550723)')
style=ParagraphStyle('body',fontName='Times-Roman',fontSize=10,leading=13)

def paragraph(text,x,y,width):
    p=Paragraph(text,style);_,h=p.wrap(width,1000);p.drawOn(c,x,y-h);return y-h-10

def header(subtitle,page):
    c.setFillColor(colors.black);c.setFont('Times-Bold',13)
    c.drawString(32,H-29,'APPENDIX D - ENGINE INTEGRATION AND VERIFICATION')
    c.setFont('Times-Roman',10);c.drawString(32,H-45,'Gift Vundla (2550723) | '+subtitle)
    c.setFont('Times-Roman',9);c.drawString(32,18,'CurricuPath | Implementation sequence and focused verification')
    c.drawRightString(W-32,18,f'D-{page}')

nodes=['Student','React UI','FastAPI','Session store','Advisor engine','Catalogue repository']
xs=[75+i*(W-150)/5 for i in range(6)]
first=[(0,1,'Ask about MATH1049A',False),(1,2,'POST /advisor + profile',False),
 (2,3,'Load context',False),(3,2,'Existing or empty context',True),
 (2,4,'Advise with request + context',False),(4,5,'Read rules + source status',False),
 (5,4,'PRE_MATH1049 + source',True),(4,2,'MATH1048A fact unknown',True),
 (2,3,'Save pending prerequisite',False),(2,1,'Return focused question',True),
 (1,0,'Ask: MATH1048A completed?',True)]
second=[(0,1,'Declare Completed',False),(1,2,'POST /advisor + session ID',False),
 (2,3,'Restore pending context',False),(3,2,'Target + prerequisite',True),
 (2,4,'Apply reply; re-evaluate target',False),(4,5,'Read applicable rules',False),
 (5,4,'Source-linked requirements',True),(4,2,'Decision + checks + source trace',True),
 (2,3,'Save updated context',False),(2,1,'Structured response',True),
 (1,0,'Display decision + evidence',True)]

def sequence(messages,start,page,subtitle):
    header(subtitle,page)
    paragraph('Synthetic EFA03 example: MATH1049A requires completed MATH1048A. Solid arrows are requests or updates; dashed arrows are returned information. Time proceeds downwards.',32,H-60,W-64)
    top=H-111;bottom=76
    for x,label in zip(xs,nodes):
        c.setStrokeColor(colors.HexColor('#334155'));c.setFillColor(colors.HexColor('#eef2f6'))
        c.roundRect(x-57,top,114,28,3,stroke=1,fill=1)
        c.setFillColor(colors.black);c.setFont('Helvetica-Bold',8.5);c.drawCentredString(x,top+10,label)
        c.setDash(2,3);c.setStrokeColor(colors.HexColor('#a3a3a3'));c.line(x,top,x,bottom);c.setDash()
    for i,(src,dst,label,dashed) in enumerate(messages):
        y=top-22-i*31;left,right=xs[src],xs[dst]
        c.setStrokeColor(colors.HexColor('#334155'));c.setFillColor(colors.HexColor('#334155'));c.setLineWidth(.85)
        if dashed:c.setDash(4,3)
        c.line(left,y,right,y);c.setDash()
        sign=1 if right>left else -1
        path=c.beginPath();path.moveTo(right,y);path.lineTo(right-sign*6,y+3);path.lineTo(right-sign*6,y-3);path.close();c.drawPath(path,stroke=0,fill=1)
        lines=simpleSplit(f'{start+i}. {label}','Helvetica',8.5,min(abs(right-left)-16,240))
        center=(left+right)/2;lineheight=9.5;height=len(lines)*lineheight+4
        width=max(c.stringWidth(t,'Helvetica',8.5) for t in lines)+8
        c.setFillColor(colors.white);c.rect(center-width/2,y-height/2,width,height,stroke=0,fill=1)
        c.setFillColor(colors.black);c.setFont('Helvetica',8.5)
        for j,t in enumerate(lines):c.drawCentredString(center,y+(len(lines)-1)*lineheight/2-j*lineheight-3,t)
    text=('Figure D1a. Initial request and missing-fact question. The repository is an interface: PostgreSQL or the catalogue-backed implementation can supply the records. This drawing does not imply that the live database was available during verification.' if page==1 else 'Figure D1b. Reply handling and re-evaluation of the original target. A declared unmet prerequisite instead produces a blocking decision; disputed institutional evidence requires review. Optional interpretation/reviewer calls and logging are omitted to keep the eligibility sequence readable.')
    paragraph(text,32,64,W-64);c.showPage()

sequence(first,1,1,'D1a Initial request and clarification')
sequence(second,12,2,'D1b Clarification reply and decision')
header('D2 Focused verification and reproduction',3)
y=paragraph('Purpose. This appendix explains the integration boundary and records a fresh implementation check. The sequence follows POST /advisor, session load/save, AdvisorEngine.advise and catalogue retrieval in the retained source. It is a design-level trace, not a timing or database-availability measurement. The editable Figma diagram and Mermaid source accompany the print layout.',32,H-65,W-64)
v=json.loads((P/'verification_scope.json').read_text())
rows=[['Selected test module','Passed','Skipped','What the checks address'],
 ['Eligibility','21','0','Programme gates; known/unknown facts; nested requirements'],
 ['Clarification regressions','20','0','Ambiguous names, candidate replies and clarification modes'],
 ['Response invariants','6','0','Constructed decision/text contradictions and unsupported identifiers'],
 ['PostgreSQL schema/import mapping','7','0','Schema and import contracts without a live database'],
 ['PostgreSQL repository','1','7','Fallback construction passed; live catalogue comparisons skipped'],
 ['Total','55','7','No failures; two environment/dependency warnings']]
t=Table(rows,colWidths=[165,48,48,W-325]);t.setStyle(TableStyle([('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTNAME',(0,1),(-1,-1),'Helvetica'),('FONTSIZE',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),8),('LINEBELOW',(0,0),(-1,0),.8,colors.black),('LINEBELOW',(0,-1),(-1,-1),.8,colors.black),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eef2f6'))]));_,h=t.wrap(W-64,1000);t.drawOn(c,32,y-h);y-=h+18
y=paragraph('<b>Run and limit.</b> On 23 October 2026, 62 collected checks produced 55 passes, seven skips and no failures. All seven skips reported that the imported PostgreSQL catalogue was unavailable. The six selected files included test_clarification.py, which contributed no collected tests. The run did not call hosted models or re-estimate the historical benchmark scores.',32,y,W-64)
y=paragraph('<b>Reproduction.</b> Run pytest on test_eligibility.py, test_clarification.py, test_clarification_fixes.py, test_response_invariants.py, test_postgres_schema.py and test_postgres_repository.py under tests/, using -q -ra and --junitxml. The full command, JUnit XML and grouped counts are included with the editable appendix.',32,y,W-64)
y=paragraph('<b>Interpretation.</b> Passing deliberately invalid response fixtures verifies those guards; it does not establish that every complete conversation produces a consistent explanation. The outdated Mathematics II summary in the main paper remains a separate diagnostic finding. Skipped database comparisons provide no evidence of successful live-database integration.',32,y,W-64)
paragraph('<b>Documentary context.</b> Appendix E preserves the merged 27-page cohort minutes. CurricuPath entries occur on merged pages 3, 6, 10-11, 15-16, 17, 23 and 26. The 2 October section follows 9 October in the merged source; its original order is retained. These team-level minutes support project progression, not individual code authorship or independent validation of a result.',32,y,W-64)
c.save()
print('Created three-page Appendix D.')
