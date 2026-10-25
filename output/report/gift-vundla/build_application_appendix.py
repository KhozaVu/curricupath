from pathlib import Path
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from PIL import Image as PILImage

P = Path(__file__).resolve().parent
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='Paper', fontName='Times-Roman', fontSize=11, leading=14, spaceAfter=9))
styles.add(ParagraphStyle(name='HeadingPaper', fontName='Times-Bold', fontSize=13, leading=16, spaceAfter=12))
styles.add(ParagraphStyle(name='TitlePaper', fontName='Times-Bold', fontSize=14, leading=18, alignment=TA_CENTER, spaceAfter=9))
styles.add(ParagraphStyle(name='CaptionPaper', fontName='Times-Roman', fontSize=10, leading=12, spaceBefore=7, spaceAfter=13))
styles.add(ParagraphStyle(name='SmallPaper', fontName='Times-Roman', fontSize=10, leading=12, spaceAfter=9))
flow = []

def para(text, style='Paper'):
    flow.append(Paragraph(text, styles[style]))

def shot(name, caption):
    path = P / 'application-screenshots' / name
    width, height = PILImage.open(path).size
    flow.append(Image(str(path), width=174*mm, height=174*mm*height/width))
    para(caption, 'CaptionPaper')

para('APPENDIX C', 'TitlePaper')
para('APPLICATION USE-CASE DEMONSTRATIONS', 'TitlePaper')
para('Gift Vundla (2550723) | CurricuPath | Captured 22 October 2026', 'SmallPaper')
para('Purpose and scope', 'HeadingPaper')
para('These screenshots illustrate the connection between a student-facing question, a declared prerequisite fact and the deterministic eligibility response. They were captured from the local CurricuPath application using a synthetic Electrical Engineering profile (EFA03). No actual student transcript was entered.')
para('These are interface demonstrations, not additional experimental cases or official permission to register. They do not establish independent academic correctness or change the main paper results. The local build may differ from the historical benchmark snapshot. The shared results plots and tables remain unchanged.')
para('C1 Missing information produces a focused question', 'HeadingPaper')
para('<b>Input:</b> Can I take MATH1049A in EFA03? No completed-module history was supplied. <b>Observed response:</b> Have you completed MATH1048A?')
shot('C1-missing-fact.jpg', 'Figure C1. The application requests the prerequisite completion fact instead of interpreting undeclared history as a pass or failure. Direct capture from the running interface.')
para('<b>What this demonstrates:</b> the question targets a specific fact needed by the eligibility check. The two answer controls provide a short route to supply it. This illustrates the missing-fact mechanism discussed in the paper.')
flow.append(PageBreak())
para('APPENDIX C - APPLICATION USE-CASE DEMONSTRATIONS', 'TitlePaper')
para('C2 Applying the answer to the original request', 'HeadingPaper')
para('<b>Setup:</b> continue the MATH1049A request from C1. <b>Synthetic reply:</b> select Completed for MATH1048A. <b>Observed response:</b> Eligible - recorded requirements met, with rule PRE_MATH1049 and the displayed checks.')
shot('C2-after-clarification.jpg', 'Figure C2. The decision names the target and displays the prerequisite, source-verification, programme and other checks. Completion is self-declared, not independently verified.')
para('<b>What this demonstrates:</b> the short reply is associated with the pending prerequisite and the original target is evaluated again. The response exposes a rule identifier, linking conversation state with backend evaluation.')
para('<b>Interpretation boundary:</b> the interface groups its positive status badge as done / planned. Here the actual reply was Completed; this capture does not demonstrate acceptance of a planned prerequisite. A successful example also does not establish correct handling of every possible reply.')
para('<b>Source identification:</b> the accompanying response panel names CBO_MATH1049_2026, the MATH1049A Engineering Mathematics IB course outline, and rule PRE_MATH1049. This identification was read from the same response; the source PDF is not reproduced here.')
flow.append(PageBreak())
para('APPENDIX C - APPLICATION USE-CASE DEMONSTRATIONS', 'TitlePaper')
para('C3 An unmet prerequisite produces a blocking reason', 'HeadingPaper')
para('<b>Setup:</b> start a new conversation in the same synthetic EFA03 programme. <b>Input:</b> Can I take MATH1049A in EFA03? I have not completed MATH1048A. <b>Observed response:</b> Not eligible - a requirement is unmet.')
shot('C3-unmet-prerequisite.jpg', 'Figure C3. The response marks MATH1048A as not finished and states that PRE_MATH1049 is not satisfied. The target and programme match C1-C2; the declared prerequisite state differs.')
para('<b>What this demonstrates:</b> the service exposes the curriculum condition blocking a request. Together, C1-C3 distinguish an unknown prerequisite, a declared completed prerequisite and a declared unmet prerequisite. These examples illustrate implementation behaviour, not population-level accuracy.')
para('Capture and reproduction record', 'HeadingPaper')
para('Local route: http://127.0.0.1:8002/v2#advisor. Each new case used New conversation. Captures retain the sidebar and response context; Latest answer brought the decision into view. No response text was replaced or composited. Original JPEGs and capture_manifest.json accompany the editable appendix.', 'SmallPaper')
para('The three captures distinguish missing, completed and unmet prerequisite states. They illustrate the declared-status check; year progression and formal permission to register remain separate academic matters.', 'SmallPaper')

def footer(canvas, doc):
    canvas.setFont('Times-Roman', 9)
    canvas.drawString(18*mm, 12*mm, 'CurricuPath | Synthetic application demonstrations')
    canvas.drawRightString(192*mm, 12*mm, f'C-{doc.page}')

doc = SimpleDocTemplate(str(P/'Appendix_C_Application_Use_Cases.pdf'), pagesize=A4,
    rightMargin=18*mm, leftMargin=18*mm, topMargin=16*mm, bottomMargin=19*mm,
    title='Appendix C - CurricuPath Application Use-Case Demonstrations', author='Gift Vundla (2550723)')
doc.build(flow, onFirstPage=footer, onLaterPages=footer)
print('Created Appendix C.')
