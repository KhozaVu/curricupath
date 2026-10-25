"""Revise the four sections readers commonly skim; preserve frozen evidence."""
from pathlib import Path
from hashlib import sha256
import json, re, shutil

P=Path(__file__).resolve().parent
S=P/'revision13'
S.mkdir(exist_ok=False)
before=(P/'CurricuPath_Gift_Vundla_Report.tex').read_text(encoding='utf8')
(S/'before.tex').write_text(before,encoding='utf8')
protected=json.loads((P/'strength_preservation_audit.json').read_text())['baseline_sha256']
assert all(sha256((P/name).read_bytes()).hexdigest()==value for name,value in protected.items())
(S/'protected_assets_before.json').write_text(json.dumps(protected,indent=2),encoding='utf8')
s=before

def span(a,b,new):
 global s
 assert s.count(a)==s.count(b)==1
 s=s[:s.index(a)]+new+'\n\n'+s[s.index(b):]

def replace(old,new):
 global s
 assert s.count(old)==1,old[:90]
 s=s.replace(old,new)

span(r'\abstract{',r'\keywords',r'''\abstract{Eligibility advice must distinguish unmet requirements from missing student facts and unverified curriculum rules. This investigation evaluated how CurricuPath preserved that distinction when a source-linked rule engine was connected to request interpretation and conversation state. Comparisons used 139 synthetic cases, a common 40-case baseline subset and 33 selected missing-fact cases. Adding School requirements raised code-based agreement from 119/139 (85.6\%) to 131/139 (94.2\%); rules-only reached 139/139 on structured inputs. No unsafe eligible answers occurred among 90 non-eligible references after the update. Clarification resolved 33/33 selected cases after one question and one scripted reply, compared with 13 correct decisions when omissions were treated as negative. Unrecognised history confirmations accounted for the eight remaining code-based failures. A separate diagnostic found an eligible decision with an outdated explanation. These findings identify evidence sufficiency, fact interpretation and explanation consistency as distinct checks on reliable advice. Cases and rules were development-informed, with shared source material and no recorded independent academic adjudication.}''')

span(r'\section{INTRODUCTION}',r'\section{LITERATURE REVIEW}',r'''\section{INTRODUCTION}
A module can match a student's interests without meeting registration requirements. Wits Electrical Engineering (EE, EFA03) and Information Engineering (IE, EFA04) impose programme restrictions, prerequisites and corequisites. Applicable conditions were assembled from Faculty rules \cite{wits}, course outlines and School guidance.

Academic advising systems support access to guidance \cite{empowered,khalil,tamas,nile,jiang}, while course recommenders address suitability \cite{chawana,islam,ibrahim}. The engineering problem examined here was preserving eligibility requirements when incomplete student facts passed through a conversational interface. An omitted result cannot safely mean pass or fail. A missing or disputed institutional rule requires a different response: requesting more student marks cannot establish the rule.

The investigation asked: \emph{How effectively did CurricuPath distinguish decidable eligibility cases from those needing student information or academic review, compared with rules-only and language-model baselines?} The work connected source-linked conditions, declared facts and conversation state, then audited where conversational decisions diverged from structured evaluation.

Three predictions guided the comparisons: complete inputs should preserve evaluator agreement (P1); clarification should outperform treating omissions as negative (P2); and School evidence should chiefly improve handbook-insufficient cases (P3). These predictions were development-informed, not preregistered. Evidence updates and clarification improved agreement, while remaining failures exposed limits in interpreting replies and maintaining consistent explanations. The following sections explain the design, experimental comparisons and implications.''')

replace('The results first show the effect of curriculum evidence, then the unresolved interpretation failures and the benefit and cost of clarification.',
 'Added curriculum evidence improved agreement, and clarification resolved the selected missing-fact cases. The remaining failures identify where conversational inputs diverged from structured evaluation.')

replace(r'''Across all 139 cases, adding School evidence increased agreement on code-based questions from 119/139 (85.6\%) to 131/139 (94.2\%). Unsafe eligible decisions fell from 7/90 to 0/90. Post-update Macro-F1 was 0.9798, 0.9688 and 0.9716 for code, name and informal wording. Rules-only reached 139/139. CurricuPath's remaining errors were unresolved outputs, rather than incorrect valid labels. Withholding an answer avoided unsafe eligibility in these cases, but the unresolved cases still counted as incorrect against their references.''',
r'''School evidence raised code-based agreement from 119/139 (85.6\%) to 131/139 (94.2\%) and reduced unsafe eligible decisions from 7/90 to 0/90. Post-update Macro-F1 was 0.9798, 0.9688 and 0.9716 for code, name and informal wording. Rules-only reached 139/139 on structured inputs. All remaining CurricuPath errors were unresolved outputs: withholding avoided unsafe eligibility, but still failed to provide the reference decision.''')

replace(r'''Table \ref{tab:shared_evidence} pools the three wordings of the frozen 40-case subset: 63 handbook-sufficient and 57 School-evidence-required observations. Starred rows are deterministic updates made after inspecting earlier results. Figure \ref{fig:shared_evidence} displays the same counts.''',
r'''The School update improved the evidence-required group without changing handbook-sufficient outcomes (Table \ref{tab:shared_evidence}; Figure \ref{fig:shared_evidence}). The frozen 40-case subset contributes 63 handbook-sufficient and 57 School-evidence-required observations across three wordings. Starred rows are deterministic updates made after inspecting earlier results.''')

replace(r'''Adding the grid changed the deterministic School-evidence group from 39/57 to 57/57, while its handbook-sufficient group stayed unchanged. The improvement therefore occurred where additional institutional evidence was needed, supporting P3. Original RAG and structured LLM outcomes were lower, but their evidence representation and input scope differed.''',
r'''Both deterministic arms rose from 39/57 to 57/57 in the School-evidence group, supporting P3. Original RAG and structured LLM outcomes were lower, but different evidence representations and input scopes prevented attributing that gap solely to reasoning.''')

replace(r'''Every arm in Table \ref{tab:shared_safety} uses the same 40 cases per wording. Unsafe totals across the 78 non-eligible observations were 0/78 for each deterministic arm, 13/78 for structured LLM and 30/78 for RAG. Matching cases controls the population, while the evidence-stage difference remains. CurricuPath and no clarification gave identical results here; the dedicated missing-fact experiment was needed to examine P2.''',
r'''Across the same 40 cases per wording, unsafe totals were 0/78 for each deterministic arm, 13/78 for structured LLM and 30/78 for RAG (Table \ref{tab:shared_safety}). Matching cases controlled the population, not the evidence supplied. CurricuPath and no clarification were identical here; their missing-fact behaviour required the separate P2 experiment.''')

replace(r'''The full-set outputs contained 8, 12 and 11 unresolved decisions for code, name and informal wording. Eight cases failed at every wording: TS022, TS041, TS077, TS078, TS081, TS089, TS110 and TS134. All had ineligible references. The target was resolved, but clarification ended without an accepted status for MATH3025A, ELEN3012A or APPM3021A. The common scripted reply was ``I have listed every module I am currently taking or planning.'' The response still asked for the specific module's status.''',
r'''History-completeness replies accounted for eight failures at every wording: TS022, TS041, TS077, TS078, TS081, TS089, TS110 and TS134. All had resolved targets and ineligible references. Despite the scripted reply, ``I have listed every module I am currently taking or planning'', clarification ended without an accepted status for MATH3025A, ELEN3012A or APPM3021A. The system continued asking about the module. Total unresolved decisions were 8, 12 and 11 for code, name and informal wording.''')

replace(r'''The two input paths treated that statement differently. Rules-only converted ``every module'' into an explicit history-confirmed flag and treated an omitted corequisite as absent. The conversational path had to interpret the statement; when it failed, the omitted module remained unknown. These responses therefore exposed a failure to pass student information to the evaluator, without demonstrating incorrect combination of the rule conditions.''',
r'''The rules-only adapter converted ``every module'' into a history-confirmed flag and treated omitted corequisites as absent. The conversational path failed to accept that confirmation, leaving them unknown. The difference therefore arose in transferring student information to the evaluator; these outputs did not demonstrate incorrect combination of rule conditions.''')

replace(r'''Name wording added four unresolved targets: TS027, TS057, TS064 and TS069. Informal wording failed on the same targets except TS057. That case concerned Introduction to Machine Learning; its informal question included ELEN4025A and resolved successfully. The stored responses requested a code or full name, but did not establish a finer internal resolver cause. These cases motivate paired code/name regression checks.''',
r'''Module identification added four unresolved targets under name wording: TS027, TS057, TS064 and TS069. Informal wording failed on the same targets except TS057, whose Introduction to Machine Learning question included ELEN4025A and resolved. Responses requested a code or full name; the records did not establish a finer resolver cause. These cases motivate paired code/name checks.''')

replace(r'''Figure \ref{fig:clarification} shows the three shared missing-fact conditions. CurricuPath and the fully informed oracle each reached 33 correct decisions. No clarification left all 33 unresolved. Assume-absent produced 13 correct, 11 wrong and nine unresolved outputs, including three unsafe eligible answers among 16 ineligible references. The 95\% Wilson interval for 33/33 correctness was 89.57--100\%.''',
r'''Clarification reached 33/33 correct decisions, matching the fully informed oracle; assume-absent reached 13/33 (Figure \ref{fig:clarification}). The latter produced 11 wrong and nine unresolved outputs, including three unsafe eligible answers among 16 ineligible references. No clarification left all 33 unresolved. For the selected scripted cases, the 95\% Wilson interval for 33/33 correctness was 89.57--100\%.''')

replace(r'''CurricuPath asked one question in each missing-fact case and none across the 39 known-fact or irrelevant-unknown controls; all controls ended correctly. The added interaction was one system question and one scripted reply, sometimes covering several statuses. Clarification therefore improved the selected cases at a measurable message cost, supporting P2. This count does not measure the time a real student would need, or whether they would abandon the conversation.''',
r'''Each missing-fact case required one question and one scripted reply, sometimes covering several statuses. CurricuPath asked no questions across the 39 known-fact or irrelevant-unknown controls, all of which ended correctly. The improvement supports P2 at this observed message cost; it does not establish student response time or abandonment.''')

replace(r'''The 23 October run produced 55 passes, seven skips and no failures. Checks covered unknown versus absent prerequisites, nested requirements, ambiguous module replies and clarification state. Response guards rejected constructed decision/text contradictions and unsupported module identifiers. Schema checks exercised import mappings without a live database. All seven skips were PostgreSQL repository comparisons because the imported catalogue was unavailable; the passing repository check exercised fallback construction. Live-database equivalence consequently remained untested. These results concern the selected implementation checks, not a new benchmark or every possible conversation.''',
r'''The focused run on 23 October passed 55 checks, skipped seven and recorded no failures. Checks covered unknown versus absent prerequisites, nested requirements, ambiguous module replies and clarification state. Response guards rejected constructed decision/text contradictions and unsupported module identifiers; schema checks exercised import mappings without a live database. The unavailable imported catalogue prevented all seven live PostgreSQL comparisons; the passing repository check exercised fallback construction. These selected checks left live-database equivalence unverified and did not re-estimate benchmark performance or cover every conversation.''')

span(r'\section{CONCLUSION}',r'\begin{thebibliography}',r'''\section{CONCLUSION}
CurricuPath's eligibility reliability depended on both adequate institutional evidence and accurate transfer of student facts. School requirements raised code-based agreement to 131/139 (94.2\%), compared with 139/139 for rules-only on structured inputs. Clarification resolved 33/33 selected missing-fact cases after one question and one scripted reply, compared with 13 correct decisions when omissions were treated as negative.

Unrecognised history confirmations and an outdated explanation exposed failures beyond rule evaluation. Reliable advice therefore requires checking the complete path from the student's statement to the decision and its explanation. The immediate priorities are explicit history-completeness handling and explanations generated from the final evaluated state. These development-informed synthetic results share source material with the rules; independently adjudicated cases and unseen replies are needed before extending the findings to operational registration advice.''')

for env in ['table','figure','equation','thebibliography']:
 pattern=rf'\\begin\{{{env}\}}.*?\\end\{{{env}\}}'
 assert re.findall(pattern,before,re.S)==re.findall(pattern,s,re.S),env
for section,end in [('LITERATURE REVIEW','DESIGN AND IMPLEMENTATION'),('DESIGN AND IMPLEMENTATION','EXPERIMENTAL METHOD'),('EXPERIMENTAL METHOD','RESULTS'),('DISCUSSION','CONCLUSION')]:
 a,b=rf'\section{{{section}}}',rf'\section{{{end}}}'
 assert before[before.index(a):before.index(b)]==s[s.index(a):s.index(b)],section
keys=re.findall(r'\\bibitem\{([^}]+)\}',s)
seen=[]
for group in re.findall(r'\\cite(?:\[[^]]*\])?\{([^}]+)\}',s):
 for key in group.split(','):
  if key not in seen: seen.append(key)
assert seen==keys
for name in ['preamble.tex','witseiepaper.cls','KJN.sty','shared_evidence.pdf','shared_clarification.pdf']:
 shutil.copy2(P/name,S/name)
(S/'CurricuPath_Gift_Vundla_Report.tex').write_text(s,encoding='utf8')
print(json.dumps({'stage':str(S),'net_word_change':len(s.split())-len(before.split()),
 'unchanged_sections':['Literature Review','Design and Implementation','Experimental Method','Discussion'],
 'protected_assets':len(protected)},indent=2))
