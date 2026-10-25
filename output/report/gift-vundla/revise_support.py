"""Strengthen explanations while retaining the frozen reporting assets."""
from pathlib import Path
import hashlib, json, re, shutil

P = Path(__file__).resolve().parent
stage = P / 'revision12'
stage.mkdir(exist_ok=False)
source = P / 'CurricuPath_Gift_Vundla_Report.tex'
before = source.read_text(encoding='utf-8')
protected = ['shared_tables.tex', 'shared_references.tex', 'shared_results.json',
    'matched_subset_audit.json', 'shared_evidence.pdf', 'shared_clarification.pdf',
    'Reflection_on_Group_Work.tex', 'Reflection_on_Group_Work.pdf',
    'Appendix_B_Original_Unmarked_Project_Plan.pdf',
    'Appendix_C_Application_Use_Cases.pdf', 'Appendix_D_Integration_and_Verification.pdf',
    'Appendix_E_Merged_Meeting_Minutes.pdf', 'witseiepaper.cls', 'KJN.sty', 'preamble.tex',
    'verification_run_2026-10-23.xml', 'verification_scope.json',
    'worked_dialogue_diagnostic.json', 'failure_analysis.json', 'report_evidence.json']
snapshot = {name: hashlib.sha256((P/name).read_bytes()).hexdigest() for name in protected}
(stage/'before.tex').write_text(before, encoding='utf-8')
(stage/'protected_assets_before.json').write_text(json.dumps(snapshot, indent=2), encoding='utf-8')
s = before

def replace(old, new):
    global s
    assert s.count(old) == 1, old[:100]
    s = s.replace(old, new)

replace(r'''Peer-advising, chatbot, AI-agent and human-in-the-loop systems offer different ways to make academic advice accessible \cite{empowered,khalil,tamas,nile,jiang}. Prerequisite-based, personalised and conversational recommendation address which learning opportunities may suit a student \cite{chawana,islam,ibrahim}. These approaches motivate support for course selection, but relevance and eligibility require different evidence. A module can match a student's interests while violating a programme restriction or prerequisite. Results from another advising setting therefore cannot verify the applicable Wits conditions.''',
r'''Peer-advising, chatbot, AI-agent and human-in-the-loop systems address access to academic advice \cite{empowered,khalil,tamas,nile,jiang}. Kuhail et al.'s MyAdvisor used real advising scenarios and usability principles; students found it helpful and easy to learn \cite{khalil}. This supports evaluating the interaction, but usability alone cannot establish eligibility correctness. AdvisingWise retrieved institutional information, asked about academic backgrounds and required human-advisor validation before delivering responses \cite{jiang}. Its oversight mechanism differs from CurricuPath's automatic decisions on verified conditions and review of cases lacking adequate evidence.

Chanaa and El Faddouli extracted concept prerequisites from linked data and matched them to course metadata \cite{chawana}; personalised and conversational recommenders also address course suitability \cite{islam,ibrahim}. Their prerequisite-aware ranking achieved NDCG@10 of approximately 0.86, supporting relevance within that experiment. A learned dependency between concepts, however, is different from a compulsory Wits registration condition. CurricuPath therefore kept similarity-based discovery separate from source-linked eligibility checks. Ranking quality could not substitute for measuring correct, unsafe and unresolved decisions.''')

replace(r'''Qulac studies clarifying questions for information retrieval \cite{qulac}. In eligibility advising, a reply may instead decide whether a compulsory requirement is satisfied. Abstention research considers when a model should withhold an answer \cite{abstention}; CurricuPath represented the underlying reason explicitly. Missing student facts prompted clarification, while insufficient or disputed institutional evidence required academic review. These distinctions led to a rule-based decision layer, a separate interpretation layer and controlled tests of evidence completeness and missing-fact handling.''',
r'''Aliannejadi et al. introduced Qulac to evaluate clarification through question selection and subsequent document retrieval \cite{qulac}. This supports testing whether an interaction improves an outcome, rather than counting questions alone. CurricuPath's outcome was a registration decision: a reply could settle a compulsory prerequisite. Abstention research examines withholding unsupported answers \cite{abstention}. Here, the cause determined the next action: missing student facts prompted clarification; insufficient or disputed institutional evidence required academic review. The experiments therefore separated missing-fact handling from evidence completeness.''')

replace(r'''FastAPI accepted typed advising requests \cite{fastapi}, while React maintained the interface state \cite{react}. PostgreSQL held the catalogue and its relationships. SQLAlchemy represented those relationships and checks; Alembic managed schema changes \cite{alembic}. Sources could be verified, incomplete, disputed or superseded, so merely attaching a source identifier did not make a rule usable.''',
r'''The backend needed a consistent representation of a target, programme and module states. FastAPI accepted typed requests \cite{fastapi}; React maintained interface state \cite{react}. These fields connected the conversation to the evaluator instead of asking it to infer facts from answer prose. PostgreSQL held related catalogue records, SQLAlchemy represented their relationships, and Alembic managed schema changes \cite{alembic}. Separating source identity from verification status allowed a stored rule to remain inspectable without making disputed evidence usable.''')

replace(r'''Catalogue replacement used a transaction \cite{sqlalchemy}: related records changed together, avoiding a partially imported catalogue. Existing vectors were reused only when item identity, chunk kind and content hash matched. BGE embeddings and pgvector supplied 384-dimensional similarity search \cite{pgvector,bge}. This helped discover related descriptions; similarity was not evidence that a prerequisite had been passed.''',
r'''Catalogue replacement used a transaction \cite{sqlalchemy} so module, rule and source changes formed one update rather than exposing a partial import. Vectors were reused only when item identity, chunk kind and content hash matched, preventing reuse for changed text. BGE embeddings and pgvector supplied 384-dimensional similarity search \cite{pgvector,bge}. This supported discovery of related descriptions; recorded student facts and curriculum conditions still determined eligibility.''')

replace(r'''Controlled aliases and optional Gemini API interpretation produced a target, programme and declared statuses in structured fields \cite{gemini,structured}. An uncertain target had to be resolved before evaluation. The session stored the original target, pending requirement and known facts. Consequently, a short reply such as ``I have completed MATH1049A'' could update the pending prerequisite instead of being treated as a new request. An unrecognised reply left the fact unknown.''',
r'''Controlled aliases and optional Gemini API interpretation produced a target, programme and declared statuses in structured fields \cite{gemini,structured}. Structured output constrained the format, not the truth of the interpretation. An uncertain target required resolution before evaluation. The session retained the target, pending requirement and known facts, allowing ``I have completed MATH1049A'' to update the original request. An unrecognised reply left the fact unknown, making reply interpretation a separately testable boundary.''')

replace(r'''Responses retained the target, outcome, rule checks and source identifiers for inspection. An unresolved target indicated that module identification had not succeeded. A resolved target with a pending prerequisite instead showed that evaluation still needed a student fact. This made the failure audit depend on recorded intermediate states, rather than on how convincing the final answer sounded.''',
r'''Responses retained the target, outcome, rule checks and source identifiers. An unresolved target indicated identification failure; a resolved target with a pending prerequisite located the failure later in the request path. These records supported the failure audit. Documentation established the tools' capabilities; local tests and recorded traces supported implementation claims. The investigation did not compare framework performance or embedding alternatives.''')

replace(r'''Reference decisions were adopted from School registration workbooks supplied on 30 September 2026. No named independent adjudicator was recorded. The same School material informed both references and encoded rules. Agreement therefore tested consistency with that evidence, rather than independently establishing its academic correctness. Evidence sufficiency was a case annotation, not a guarantee that any retrieved page was adequate.''',
r'''Reference decisions were adopted from School registration workbooks supplied on 30 September 2026. Each case recorded the target, profile, expected label and evidence rationale. For example, TS022 concerned ELEN3000A in EFA03. Its record cited the EE Year 3 grid and Faculty rules \cite[p.81]{wits}: MATH3025A was a corequisite, absent from completed, current and planned study. The student confirmed the current/planned lists were complete, supporting an ineligible reference. Without that confirmation, omission would remain unknown and require clarification. Section \ref{sec:failures} examines why the conversational path did not accept this confirmation.

No named independent adjudicator was recorded. The same School material informed references and rules, so agreement tested consistency with that evidence, not independent academic correctness. Evidence sufficiency was a case annotation, not a guarantee that any retrieved page was adequate.''')

replace(r'''\subsection{Why conversational requests remained unresolved}
The full-set''', r'''\subsection{Why conversational requests remained unresolved}
\label{sec:failures}
The full-set''')

# Results, discussion, conclusion, displayed assets and bibliography remain verbatim,
# apart from the internal cross-reference label added above.
for env in ['table', 'figure', 'equation', 'thebibliography']:
    pattern = rf'\\begin\{{{env}\}}.*?\\end\{{{env}\}}'
    assert re.findall(pattern, before, re.S) == re.findall(pattern, s, re.S), env
old_results = before[before.index(r'\section{RESULTS}'):]
new_results = s[s.index(r'\section{RESULTS}'):].replace('\\label{sec:failures}\n', '')
assert old_results == new_results
for name in ['preamble.tex', 'witseiepaper.cls', 'KJN.sty', 'shared_evidence.pdf', 'shared_clarification.pdf']:
    shutil.copy2(P/name, stage/name)
(stage/source.name).write_text(s, encoding='utf-8')
print(json.dumps({'stage': str(stage), 'word_change_approx':len(s.split())-len(before.split()),
    'protected_assets': len(snapshot), 'result_and_discussion_prose': 'unchanged'}, indent=2))
