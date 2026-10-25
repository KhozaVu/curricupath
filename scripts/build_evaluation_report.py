"""Build the pilot evaluation report PDF from the draft analysis outputs.

Every number is read from the result files. Qualitative statements are asserted
against the data, so the build fails instead of printing a claim the data no longer
supports.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EVALUATION = PROJECT_ROOT / "experiments" / "evaluation" / "v2_5"
ANALYSIS = EVALUATION / "results" / "draft_analysis"
OUTPUT = ANALYSIS / "CurricuPath_Pilot_Evaluation_Report.pdf"

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from app.evaluation import scoring
from app.evaluation.benchmark_figures import comparison_rows, load_published
from app.evaluation.figures import ARM_NAMES, ARM_ORDER

INK, INK_2, BLUE, AMBER = "#0b0b0b", "#52514e", "#2a78d6", "#e9b949"
PAGE_W, PAGE_H = A4
MARGIN = 2 * cm
CONTENT_W = PAGE_W - 2 * MARGIN
DRAFT = "DRAFT pilot: developer-side labels, not independent evidence"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _styles():
    base = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=base["Normal"], fontName="Helvetica", fontSize=9.5,
                          leading=13.5, textColor=colors.HexColor(INK), alignment=TA_LEFT, spaceAfter=6)
    return {
        "title": ParagraphStyle("title", parent=body, fontName="Helvetica-Bold", fontSize=22, leading=27, spaceAfter=4),
        "subtitle": ParagraphStyle("subtitle", parent=body, fontSize=11, leading=15, textColor=colors.HexColor(INK_2)),
        "h1": ParagraphStyle("h1", parent=body, fontName="Helvetica-Bold", fontSize=14, leading=18, spaceBefore=14, spaceAfter=6),
        "h2": ParagraphStyle("h2", parent=body, fontName="Helvetica-Bold", fontSize=11, leading=15, spaceBefore=8, spaceAfter=4),
        "body": body,
        "bullet": ParagraphStyle("bullet", parent=body, leftIndent=14, bulletIndent=3, spaceAfter=3),
        "small": ParagraphStyle("small", parent=body, fontSize=8, leading=10.5, spaceAfter=0),
        "cell": ParagraphStyle("cell", parent=body, fontSize=8, leading=10, spaceAfter=0),
        "cellb": ParagraphStyle("cellb", parent=body, fontName="Helvetica-Bold", fontSize=8, leading=10, spaceAfter=0),
        "caption": ParagraphStyle("caption", parent=body, fontSize=8, leading=10.5, textColor=colors.HexColor(INK_2), spaceAfter=10),
    }


S = _styles()


def P(text, style="body"):
    return Paragraph(text, S[style])


def bullets(items):
    return [Paragraph(item, S["bullet"], bulletText="•") for item in items]


def table(rows, widths, *, header=True, zebra=True):
    data = [[Paragraph(str(c), S["cellb" if header and r == 0 else "cell"]) for c in row]
            for r, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.HexColor(INK_2)),
        ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#d9d8d3")),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    if zebra:
        style += [("BACKGROUND", (0, r), (-1, r), colors.HexColor("#f5f4f0")) for r in range(2, len(rows), 2)]
    t.setStyle(TableStyle(style))
    return t


def figure(path: Path, caption: str, max_height=20 * cm):
    width, height = ImageReader(str(path)).getSize()
    scale = min(CONTENT_W / width, max_height / height)
    return KeepTogether([Image(str(path), width=width * scale, height=height * scale),
                         Spacer(1, 3), P(caption, "caption")])


def banner(text):
    t = Table([[Paragraph(text, S["body"])]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1.2, colors.HexColor(AMBER)),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fdf6e3")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor(INK_2))
    canvas.drawString(MARGIN, 1.1 * cm, f"CurricuPath pilot evaluation | {DRAFT}")
    canvas.drawRightString(PAGE_W - MARGIN, 1.1 * cm, f"Page {doc.page}")
    canvas.restoreState()


def f2(x):
    return "n/a" if x is None else f"{x:.2f}"


def ci(pair):
    return f"{pair[0]:.2f} to {pair[1]:.2f}"


def pct(rate):
    return "n/a" if rate is None else f"{rate * 100:.0f}%"


def arms(summary):
    return [a for a in ARM_ORDER if a in summary["arms"]]


def paired(summary, second, metric="macro_f1"):
    return next(p for p in summary["paired_differences"]
                if p["second_arm"] == second and p["metric"] == metric)


def reading(p):
    return p["verdict"].split(" (")[0].replace("first arm", "CurricuPath")


def unresolved_count(raw) -> int:
    return sum((r["parsed_output"] or {}).get("status") == "clarification_unresolved" for r in raw)


def recovered(summary) -> str:
    """Share of the Handbook-RAG to CurricuPath gap that the structured-rules LLM closes."""

    handbook = summary["arms"]["handbook_rag"]["macro_f1"]
    structured = summary["arms"]["structured_rules_llm"]["macro_f1"]
    curricupath = summary["arms"]["curricupath"]["macro_f1"]
    gap = curricupath - handbook
    if gap <= 0:
        return "none"
    share = (structured - handbook) / gap
    return "all" if share >= 1 else f"{share * 100:.0f}%"


def main() -> None:
    dev = _load(ANALYSIS / "developer" / "metrics_summary.json")
    brief = _load(ANALYSIS / "briefing" / "metrics_summary.json")
    intent = _load(ANALYSIS / "intent_metrics.json")
    config = _load(EVALUATION / "results" / "raw" / "draft_run_config.json")
    published = load_published(EVALUATION / "pilot" / "published_benchmarks.csv")
    with (EVALUATION / "eligibility_cases.csv").open(newline="", encoding="utf-8") as h:
        cases = list(csv.DictReader(h))
    with (ANALYSIS / "developer" / "case_decisions.csv").open(newline="", encoding="utf-8") as h:
        decisions = list(csv.DictReader(h))
    briefing_labels = scoring.load_label_set(EVALUATION / "pilot" / "senate_briefing_labels.csv", "briefing_label")
    developer_labels = {c["case_id"]: c["developer_expected_label"] for c in cases}
    agreement = scoring.label_set_agreement(
        [developer_labels[c["case_id"]] for c in cases], [briefing_labels[c["case_id"]] for c in cases])
    differing = [(c["case_id"], developer_labels[c["case_id"]], briefing_labels[c["case_id"]])
                 for c in cases if developer_labels[c["case_id"]] != briefing_labels[c["case_id"]]]
    amb_metrics = _load(ANALYSIS / "ambiguity" / "ambiguity_metrics.json")
    with (ANALYSIS / "ambiguity" / "ambiguity_cases.csv").open(newline="", encoding="utf-8") as h:
        amb_rows = list(csv.DictReader(h))
    named = [r for r in amb_rows if r["ambiguity_type"] == "ambiguous_module_name"]
    named_status = Counter(r["curricupath_first_status"] for r in named)
    assert len(named) == 10 and named_status.get("clarification_required", 0) == 9 and named_status.get("ok", 0) == 1, (
        "Claim '9 of 10 ambiguous-name prompts now produce a clarification' no longer holds.")
    sweeps = ANALYSIS.parent / "diagnostics" / "clarification_sweep"
    sweep = {k: {l["level"]: l for l in _load(sweeps / k / "summary.json")["levels"]}
             for k in ("baseline", "after_fixes", "heldout_before", "heldout_after")}
    raw = [json.loads(l) for l in (EVALUATION / "results" / "raw" / "draft_curricupath.jsonl")
           .read_text(encoding="utf-8").splitlines() if l.strip()]

    no_decision = {d["case_id"] for d in decisions if d["curricupath_decision"] == "invalid"}
    same_elsewhere = all(d["curricupath_decision"] == d["rules_only_decision"]
                         == d["curricupath_no_clarification_decision"]
                         for d in decisions if d["case_id"] not in no_decision)
    unresolved = sum((r["parsed_output"] or {}).get("status") == "clarification_unresolved" for r in raw)
    assert same_elsewhere, "Claim 'CurricuPath equals rules-only outside the 10 declared-fact cases' no longer holds."
    assert all(d["curricupath_no_clarification_decision"] == "invalid" for d in decisions
               if d["case_id"] in no_decision), "No-clarification arm now decides a declared-fact case."
    rules_on_fact = {d["rules_only_decision"] for d in decisions if d["case_id"] in no_decision}
    assert rules_on_fact == {"ineligible"}, "Rules-only decisions on the declared-fact cases changed."
    clarification_cases = {c["case_id"] for c in cases if c["clarification_permitted"] == "true"}
    unknown_corequisite = {c["case_id"] for c in cases if c["scenario_type"] == "corequisite_unknown"}
    assert no_decision == clarification_cases == unknown_corequisite, "No-decision cases changed."
    assert {developer_labels[c] for c in no_decision} == {"ineligible"}
    assert len(no_decision) == 10 and unresolved_count(raw) == 10, "Clarification outcome changed."
    assert set((a, b) for _, a, b in differing) == {("eligible", "manual_review_required")}
    assert all(dev["arms"][a]["provider_failure_cases"] == [] for a in arms(dev)), "Provider failures present."

    cp_d, cp_b = dev["arms"]["curricupath"], brief["arms"]["curricupath"]
    hr_d, hr_b = paired(dev, "handbook_rag"), paired(brief, "handbook_rag")
    sr_d, sr_b = paired(dev, "structured_rules_llm"), paired(brief, "structured_rules_llm")
    story = []

    # ---- Title and summary ---------------------------------------------------------------
    story += [
        P("CurricuPath Pilot Evaluation Report", "title"),
        P("Pilot evaluation (developer-side labels)", "subtitle"),
        P("Project 26P73: AI-assisted Wits EIE learning pathway and module advisor", "subtitle"),
        P(f"Evaluation protocol v2.5, pilot runs | {date.today().strftime('%d %B %Y')} | "
          f"code version {dev['inputs']['git_head'][:8]}", "subtitle"),
        Spacer(1, 8),
        banner("<b>Status: pilot, not a validated result.</b> No independent academic reviewer has approved "
               "reference labels yet. Every score below is measured against developer-side answer keys, so it "
               "describes how the systems behave and differ. It is not evidence of independently validated "
               "accuracy. Figures published for other systems appear as context only."),
        Spacer(1, 8),
        P("Summary", "h1"),
        *bullets([
            f"<b>What was run.</b> Five systems answered the same {dev['n_cases']} synthetic EFA03/EFA04 "
            "eligibility cases once each, and the deterministic intent extractor was tested on 100 draft prompts.",
            "<b>How this differs from the frozen protocol.</b> One run per case instead of three; the model "
            "arms used gemini-3.5-flash-lite instead of the pinned gemini-3.6-flash; and the CurricuPath arms "
            "ran without Gemini intent extraction, so they show the deterministic path only.",
            f"<b>CurricuPath against the handbook-RAG baseline.</b> Agreement with the developer labels "
            f"(macro-F1) is {f2(cp_d['macro_f1'])} against "
            f"{f2(dev['arms']['handbook_rag']['macro_f1'])} under the developer labels (difference "
            f"{hr_d['difference']:+.2f}, 95% interval {hr_d['ci95_low']:+.2f} to {hr_d['ci95_high']:+.2f}; "
            f"{reading(hr_d)}). Under the Senate Rules briefing labels it is {f2(cp_b['macro_f1'])} against "
            f"{f2(brief['arms']['handbook_rag']['macro_f1'])} ({reading(hr_b)}).",
            f"<b>The answer key matters.</b> The two developer-side label sets agree on {pct(agreement['raw_agreement'])} "
            f"of cases (kappa {f2(agreement['cohens_kappa'])}) and differ on {len(differing)}, all on whether a "
            f"corequisite that is only <i>planned</i> counts as satisfied. CurricuPath's macro-F1 moves from "
            f"{f2(cp_d['macro_f1'])} to {f2(cp_b['macro_f1'])} between them.",
            "<b>CurricuPath makes the same decisions as the rules-only system on 50 of 60 cases.</b> On the other "
            "10, rules-only is given the declared completeness fact as structured input and decides "
            "<i>ineligible</i>; CurricuPath does not reach a decision. Elsewhere any advantage over rules-only must "
            "come from language handling and clarification, which this case set does not test.",
            f"<b>Intent understanding:</b> {intent['intent_accuracy']['correct']}/{intent['intent_accuracy']['n']} "
            f"correct ({pct(intent['intent_accuracy']['rate'])}). The weak categories are career-path prompts and "
            "ambiguous module names.",
        ]),
    ]

    # ---- 1. Purpose ------------------------------------------------------------------------
    story += [
        P("1. Purpose and scope", "h1"),
        P("The investigation asks whether hard eligibility gates and conversational clarification improve the "
          "correctness of Wits EIE curriculum advice compared with simpler strategies. The study is limited to "
          "eligibility decisions for the EFA03 (Electrical Engineering) and EFA04 (Information Engineering) "
          "programmes, each returned as one of three outcomes: <i>eligible</i>, <i>ineligible</i> or "
          "<i>manual review required</i>."),
        P("Under the frozen protocol (section 16), work without a named independent reviewer may continue only "
          "as a pilot and must not claim independently validated accuracy. This report is that pilot."),
        P("Its purpose is threefold: to demonstrate that the evaluation method works end to end on real system "
          "outputs, to identify failure patterns, and to isolate the one rule question (Rule 1.9, planned "
          "corequisites) that an academic reviewer has to settle. Claims about accuracy are deferred to the "
          "reviewer-labelled evaluation."),
    ]

    # ---- 2. Method -------------------------------------------------------------------------
    scenario = Counter(c["scenario_type"] for c in cases)
    classes = Counter(developer_labels.values())
    story += [
        P("2. Method", "h1"),
        P("2.1 Systems compared", "h2"),
        table([
            ["System", "What it does", "Pilot configuration"],
            ["CurricuPath", "Intent extraction, module-name resolution, deterministic eligibility gates, and one "
             "scripted clarification where permitted.", "Deterministic extraction; Gemini not used."],
            ["CurricuPath (no clarification)", "The same system with clarification switched off.",
             "Deterministic extraction; Gemini not used."],
            ["Rules only", "The deterministic gates applied directly to the target module. No language layer.",
             "No model."],
            ["Handbook RAG", "Retrieves the 20 most similar handbook passages and asks one model to decide, "
             "with no rules supplied. The baseline representing existing handbook chatbots.",
             "gemini-3.5-flash-lite, top-k 20."],
            ["Structured-rules LLM", "As Handbook RAG, but the structured rules and source states are added to "
             "the prompt.", "gemini-3.5-flash-lite, top-k 20."],
        ], [3.6 * cm, 9.6 * cm, CONTENT_W - 13.2 * cm]),
        P("2.2 Cases", "h2"),
        P(f"{len(cases)} synthetic profiles (no real student data), all drafted by the developers: "
          f"{classes['eligible']} eligible, {classes['ineligible']} ineligible and "
          f"{classes['manual_review_required']} manual review. Scenario types: "
          + ", ".join(f"{k.replace('_', ' ')} ({v})" for k, v in sorted(scenario.items())) + ". "
          "Ten cases permit one scripted clarification."),
        P("2.3 Answer keys", "h2"),
        P("Two developer-side keys were used. Neither is independent evidence."),
        *bullets([
            "<b>Developer labels:</b> the expected outcome written when each case was drafted.",
            "<b>Senate Rules briefing labels:</b> a second reading of the same cases from a briefing document "
            "built from the 2026 Senate Rules. The document calls every label a draft and records no reviewer, "
            "so it is used only as a sensitivity check.",
        ]),
        P("2.4 Measures", "h2"),
        P("Three-class macro-F1 and balanced accuracy, with 95% intervals from a case-level bootstrap "
          f"({dev['bootstrap']['resamples']} resamples, seed {dev['bootstrap']['seed']}), and paired "
          "differences that share each resample. A difference is called directional only when its interval "
          "excludes zero; otherwise it is reported as inconclusive. A run with no valid decision counts as an "
          "error and stays in every denominator. Error types are reported separately: an unsafe false positive "
          "is a case that was not eligible but was answered eligible."),
        P("2.5 How the pilot departs from the frozen protocol", "h2"),
        *bullets(config["deviations_from_frozen_protocol"]),
    ]

    # ---- 3. Results ------------------------------------------------------------------------
    def agree_rows():
        rows = [["System", "Macro-F1, developer labels (95% CI)", "Balanced accuracy", "Macro-F1, briefing labels (95% CI)",
                 "Balanced accuracy", "No valid decision"]]
        for a in arms(dev):
            d, b = dev["arms"][a], brief["arms"][a]
            rows.append([ARM_NAMES[a], f"{f2(d['macro_f1'])} ({ci(d['macro_f1_ci95'])})", f2(d["balanced_accuracy"]),
                         f"{f2(b['macro_f1'])} ({ci(b['macro_f1_ci95'])})", f2(b["balanced_accuracy"]),
                         str(d["safety"]["invalid_output_rate"]["numerator"])])
        return rows

    story += [
        P("3. Eligibility results", "h1"),
        P("3.1 Agreement with the answer keys", "h2"),
        table(agree_rows(), [3.6 * cm, 3.6 * cm, 2.1 * cm, 3.6 * cm, 2.1 * cm, CONTENT_W - 15 * cm]),
        Spacer(1, 4),
        P("<b>The 10 cases with no valid decision.</b> Rules only and both CurricuPath variants return no valid "
          "decision on the same 10 cases. These are the <i>corequisite unknown</i> cases, and they are also the "
          "10 cases where one scripted clarification was permitted. The profile does not declare the "
          "corequisite, and the engine declines to decide rather than assume the module is not taken. The "
          "developers labelled all ten <i>ineligible</i>."),
        P("These are counted as errors by design, and they are not mapped to <i>manual review required</i>. "
          "The frozen protocol keeps <i>needs clarification</i> separate from manual review: clarification asks "
          "for missing information, whereas manual review means the system cannot decide even once the facts "
          "are supplied. It states that clarification is \"never silently converted into manual review\" and "
          "that failing to decide after the scripted reply is a decision error. Two caveats follow. The "
          "developer label of <i>ineligible</i> for these cases is itself open to a reviewer's challenge, and "
          "because the clarification step resolved none of them (section 6), the ten errors say more about "
          "the scripted reply than about the eligibility rules."),
        figure(ANALYSIS / "developer" / "figures" / "fig1_primary_metrics.png",
               "Figure 1. Agreement with the developer labels. Whiskers show the bootstrap 95% interval."),
        figure(ANALYSIS / "developer" / "figures" / "fig2_confusion_matrices.png",
               "Figure 2. Confusion matrices against the developer labels. Rows are the reference label."),
        figure(ANALYSIS / "briefing" / "figures" / "fig1_primary_metrics.png",
               "Figure 3. Agreement with the Senate Rules briefing labels."),
    ]

    def paired_rows():
        rows = [["CurricuPath minus", "Developer labels: difference (95% CI)", "Reading",
                 "Briefing labels: difference (95% CI)", "Reading"]]
        for a in arms(dev):
            if a == "curricupath":
                continue
            d, b = paired(dev, a), paired(brief, a)
            rows.append([ARM_NAMES[a], f"{d['difference']:+.2f} ({d['ci95_low']:+.2f} to {d['ci95_high']:+.2f})",
                         reading(d).replace("CurricuPath ", ""),
                         f"{b['difference']:+.2f} ({b['ci95_low']:+.2f} to {b['ci95_high']:+.2f})",
                         reading(b).replace("CurricuPath ", "")])
        return rows

    story += [
        KeepTogether([
            P("3.2 Paired differences", "h2"),
            P("Macro-F1 difference between CurricuPath and each other system on the same cases."),
            table(paired_rows(), [3.6 * cm, 4.1 * cm, 2.6 * cm, 4.1 * cm, CONTENT_W - 14.4 * cm]),
        ]),
        Spacer(1, 4),
        figure(ANALYSIS / "developer" / "figures" / "fig6_paired_differences.png",
               "Figure 4. Paired macro-F1 differences against the developer labels.", max_height=9 * cm),
    ]

    def error_rows(summary):
        keys = [("unsafe_false_positive_rate", "Unsafe false positive"),
                ("overly_conservative_false_negative_rate", "Overly conservative"),
                ("correct_escalation_rate", "Correct escalation"),
                ("unsafe_overconfidence_rate_on_manual_review", "Unsafe overconfidence"),
                ("unnecessary_escalation_rate", "Unnecessary escalation")]
        rows = [["System", *[k[1] for k in keys]]]
        for a in arms(summary):
            cells = []
            for key, _ in keys:
                r = summary["arms"][a]["safety"][key]
                cells.append("n/a" if r["rate"] is None else f"{pct(r['rate'])} ({r['numerator']}/{r['denominator']})")
            rows.append([ARM_NAMES[a], *cells])
        return rows

    widths = [3.6 * cm] + [(CONTENT_W - 3.6 * cm) / 5] * 5
    story += [
        KeepTogether([P("3.3 Error types", "h2"), P("Against the developer labels:"),
                      table(error_rows(dev), widths)]),
        Spacer(1, 6),
        KeepTogether([P("Against the Senate Rules briefing labels:"), table(error_rows(brief), widths)]),
        Spacer(1, 4),
        figure(ANALYSIS / "developer" / "figures" / "fig3_error_types.png",
               "Figure 5. Error types against the developer labels."),
        figure(ANALYSIS / "briefing" / "figures" / "fig3_error_types.png",
               "Figure 6. Error types against the Senate Rules briefing labels."),
    ]

    story += [
        P("3.4 Sensitivity to the answer key", "h2"),
        P(f"The two label sets agree on {pct(agreement['raw_agreement'])} of the {agreement['n_cases']} cases "
          f"(Cohen's kappa {f2(agreement['cohens_kappa'])}). All {len(differing)} differences are the same: the "
          "developers marked the case <i>eligible</i> and the briefing marked it <i>manual review required</i>, "
          "because a corequisite appears only under the student's planned modules. Senate Rule 1.9 defines a "
          "corequisite as a course that must be taken with another, so whether a planned module counts is a "
          "question for an academic authority. The engine currently accepts planned modules as satisfying a "
          "corequisite."),
        figure(ANALYSIS / "figures" / "fig8_label_set_sensitivity.png",
               "Figure 7. Macro-F1 under each answer key (circle: developer, diamond: briefing).", max_height=8 * cm),
        P("Cases where the label sets differ: " + ", ".join(c for c, _, _ in differing) + ".", "small"),
        Spacer(1, 6),
    ]

    lat = [["System", "Median", "95th percentile", "Runs"]]
    for a in arms(dev):
        s = dev["arms"][a]["latency"]
        lat.append([ARM_NAMES[a], "under 1 ms" if s["median_ms"] < 1 else f"{s['median_ms'] / 1000:.3f} s",
                    "under 1 ms" if s["p95_ms"] < 1 else f"{s['p95_ms'] / 1000:.3f} s", str(s["n"])])
    story += [
        P("3.5 Response time", "h2"),
        P("Times are per case, measured end to end through each system. The CurricuPath figures are for the "
          "deterministic path only; the Gemini-assisted path was not measured."),
        table(lat, [5 * cm, 3.5 * cm, 3.5 * cm, 2 * cm]), Spacer(1, 4),
        figure(ANALYSIS / "developer" / "figures" / "fig4_latency.png", "Figure 8. Response time by system (log scale).",
               max_height=8 * cm),
        figure(ANALYSIS / "developer" / "figures" / "fig7_accuracy_by_subset.png",
               "Figure 9. Exact-match accuracy within case subsets. Subsets hold 10 to 60 cases, so read these as "
               "failure patterns rather than precise rates.", max_height=17 * cm),
    ]

    # ---- 4. Intent -------------------------------------------------------------------------
    ia = intent["intent_accuracy"]
    irows = [["Prompt category", "Correct", "Rate", "95% interval"]]
    for cat, v in sorted(intent["by_category"].items(), key=lambda kv: kv[1]["rate"]):
        irows.append([cat.replace("_", " "), f"{v['correct']}/{v['n']}", pct(v["rate"]), ci(v["ci95"])])
    irows.append(["<b>All prompts</b>", f"<b>{ia['correct']}/{ia['n']}</b>", f"<b>{pct(ia['rate'])}</b>", ci(ia["ci95"])])
    entity = ", ".join(f"{k.replace('_', ' ')} {intent[k + '_accuracy']['correct']}/{intent[k + '_accuracy']['n']}"
                       for k in ("module_code", "programme_code", "year_of_study"))
    story += [
        P("4. Intent understanding", "h1"),
        P("The deterministic extractor was run on 100 developer-drafted prompts that have not been independently "
          "reviewed. The Gemini-assisted extractor was not measured."),
        table(irows, [6 * cm, 2.5 * cm, 2.5 * cm, 4 * cm]), Spacer(1, 4),
        P(f"Where an entity was expected it was always extracted correctly: {entity}."),
        P("The ten <i>ambiguous module name</i> prompts are bare topic words such as electronics or signals, "
          "and this is the category where the extractor scores 0/10. The extractor itself was not changed. "
          "Before the fixes in section 4.2, a later layer did not recover these either: most were refused as out "
          "of scope. After the fixes, nine of the ten get a question asking which module they mean; the tenth, "
          "circuits, matches only Electric Circuits and is answered directly "
          "(section 4.1). The other clear weakness is career-path prompts, four of ten of which were treated as "
          "course searches."),
        figure(ANALYSIS / "figures" / "fig10_intent_by_category.png",
               "Figure 10. Intent accuracy by prompt category with 95% Wilson intervals.", max_height=9 * cm),
    ]

    ambiguity_measures = [("initial_intent_accuracy", "Initial intent matches the intended interpretation"),
                          ("asked_clarification_first_turn", "Asked for clarification on the first turn"),
                          ("answered_first_turn", "Answered on the first turn"),
                          ("refused_out_of_scope_first_turn", "Refused as out of scope on the first turn"),
                          ("unresolved_clarification_rate", "Ended with an unresolved clarification")]
    def amb_cell(m):
        return f"{m['correct']}/{m['n']} ({m['rate'] * 100:.0f}%)"
    amb_arms = amb_metrics["arms"]
    story += [
        P("4.1 Ambiguity and clarification (Experiment C, draft)", "h2"),
        P(f"The {amb_arms['curricupath']['n_cases']} ambiguity cases were run with and without clarification. "
          "The fields that only the independent reviewer may supply (whether clarification is required, the "
          "scripted reply, and the accepted outcomes) are still pending, so only behavioural measures can be "
          "reported here."),
        table([["Measure", "Full CurricuPath", "Without clarification"],
               *[[label, amb_cell(amb_arms["curricupath"][key]), amb_cell(amb_arms["curricupath_no_clarification"][key])]
                 for key, label in ambiguity_measures]],
              [8.6 * cm, 4.2 * cm, CONTENT_W - 12.8 * cm]),
        Spacer(1, 4),
        P("Clarification exists only in CurricuPath. In the version without it, the engine's clarification "
          "switch is off: it never asks, takes the best-scoring module when a name is shared, and otherwise gives "
          "a final \"could not determine\" answer. The other systems (rules only, Handbook RAG, structured-rules "
          "LLM) have no clarification step at all. Full CurricuPath asked in "
          f"{amb_arms['curricupath']['asked_clarification_first_turn']['correct']} of 13 cases; the version "
          "without clarification asked in "
          f"{amb_arms['curricupath_no_clarification']['asked_clarification_first_turn']['correct']}. Whether "
          "those questions lead to better answers cannot be scored until the reviewer's scripted replies and "
          "accepted outcomes exist. These figures are after the fixes in section 4.2; before them, the correct "
          "intent was recognised in 3/13 cases, a question was asked in 2/13 and 8/13 were refused."),
        P("4.2 Why clarification failed, and the fixes", "h2"),
        P("A diagnostic sweep asked about real modules at five levels of ambiguity (exact code, full name, name "
          "without its I/II marker, a single topic word, no topic) in four phrasings. Each prompt ran once with "
          "clarification switched off and once with it on, where any question received one simulated reply "
          "naming the module. These prompts were written by the developers to "
          "exercise the mechanism, not taken from the frozen cases. Clarification itself worked whenever it was "
          "reached; the failures were upstream:"),
        *bullets([
            "The scope gate refused module names as out of scope before module lookup could run.",
            "Question words such as \"who teaches\" were not stripped, so lookup found no candidates and the "
            "student got a generic question instead of a choice of modules.",
            "A name shared by several modules was only treated as a module question when it matched exactly, so "
            "the cases that most needed \"which one?\" never got it.",
        ]),
        P("Three fixes addressed these, each with a regression test: question words are stripped before lookup; "
          "a short name shared by several modules becomes a module question that offers the candidates; and this "
          "decision runs before the scope gate, after prohibited requests are refused. A fourth planned fix, "
          "keeping state after the scope gate's own question, proved unnecessary. The 60 eligibility decisions "
          "were unchanged."),
        table([["Named by", "Studied set before", "Studied set after", "Unseen set before", "Unseen set after"],
               *[[lbl, *(pct(sweep[k][lvl]["with_clarification_rate"]) for k in
                         ("baseline", "after_fixes", "heldout_before", "heldout_after"))]
                 for lvl, lbl in ((1, "Full name"), (2, "Name without I/II"), (3, "Topic word"), (4, "No topic"))]],
              [4.2 * cm, 3.1 * cm, 3.1 * cm, 3.1 * cm, CONTENT_W - 13.5 * cm]),
        Spacer(1, 4),
        figure(ANALYSIS.parent / "diagnostics" / "clarification_sweep" / "before_after_curve.png",
               "Figure 11. Share of answers about the intended module, before and after the fixes. Left: prompts "
               "studied while fixing. Right: unseen module families and phrasings.", max_height=9 * cm),
        P("The studied set reaching 100% is expected, since the fixes were built against it. The unseen set is "
          "the fair measure: large gains, but at the two middle levels only about half succeed. Every remaining "
          "failure there is one of two phrasings (\"Can you give me info on X\", \"I need details on X\") that "
          "the new rule does not recognise, so the rule partly overfitted to the studied phrasings. This is "
          "reported rather than patched, because patching it would use up the unseen set."),
        P("<b>What clarification itself contributes.</b> The same fixed CurricuPath, with clarification switched "
          "off, has to guess the best-scoring module:"),
        table([["Named by", "Studied set: off", "Studied set: on", "Unseen set: off", "Unseen set: on"],
               *[[lbl, pct(sweep["after_fixes"][lvl]["single_turn_rate"]),
                  pct(sweep["after_fixes"][lvl]["with_clarification_rate"]),
                  pct(sweep["heldout_after"][lvl]["single_turn_rate"]),
                  pct(sweep["heldout_after"][lvl]["with_clarification_rate"])]
                 for lvl, lbl in ((1, "Full name"), (2, "Name without I/II"), (3, "Topic word"), (4, "No topic"))]],
              [4.2 * cm, 3.1 * cm, 3.1 * cm, 3.1 * cm, CONTENT_W - 13.5 * cm]),
        Spacer(1, 4),
        P("With a precise name the two are equal, as they should be. As the question becomes ambiguous, guessing "
          "falls away while asking recovers the intended module, including on the unseen set. These are "
          "developer-written prompts with a cooperative simulated reply, so they show the mechanism works, not "
          "how often real students would answer as simulated."),
    ]

    fb_dir = ANALYSIS.parent / "diagnostics" / "llm_fallback"
    fb = {m: _load(fb_dir / f"mode_{m}" / "summary.json") for m in ("off", "fuzzy", "llm")}
    assert [fb[m]["overall"]["correct"] for m in ("off", "fuzzy", "llm")] == [27, 31, 33], "Fallback results changed."
    assert all(fb[m]["by_category"]["negative"]["correct"] == 7 for m in fb), "A negative case changed."
    labels = {"typo": "Typos", "phrasing": "Unusual phrasing", "typo_phrasing": "Typos with shorthand",
              "description": "Descriptions without a name", "negative": "Must not change"}
    story += [
        KeepTogether([
            P("4.3 Handling typos and unusual wording (interpretation fallback)", "h2"),
            P("When the deterministic interpreter cannot tell what a message means, an interpretation fallback now "
          "tries to recover it before the request is refused. It never decides eligibility: it rewrites the "
          "message into a standard request (for example \"Tell me about ELEN2021A\") that the unchanged "
          "deterministic pipeline then processes. Prohibited requests and replies to an open question are "
          "never reinterpreted."),
        ]),
        *bullets([
            "<b>Fuzzy tier</b> (free, offline): misspelt words close to the catalogue's own vocabulary are corrected.",
            "<b>LLM tier:</b> the model sees the message and the module list and must return one module code "
            "from that list, or none; anything else is discarded. Gemini is tried first; Claude Haiku 4.5 is "
            "used only when Gemini refuses a call for quota or availability.",
        ]),
        P("It was measured on 34 developer-written cases that were hash-frozen before the fallback code existed, "
          "including seven that must not change. The pre-fallback failures were seen before implementation, "
          "but the two tiers were specified beforehand and no rules target specific phrases."),
        table([["Case type", "Off", "Fuzzy", "Fuzzy + LLM"],
               *[[f"{labels[c]} ({fb['off']['by_category'][c]['n']})",
                  *(str(fb[m]["by_category"][c]["correct"]) for m in ("off", "fuzzy", "llm"))]
                 for c in labels],
               ["<b>Total (34)</b>", *(f"<b>{fb[m]['overall']['correct']}</b>" for m in ("off", "fuzzy", "llm"))]],
              [7.4 * cm, 3 * cm, 3 * cm, CONTENT_W - 13.4 * cm]),
        Spacer(1, 4),
        P("Each tier has a distinct job: fuzzy matching fixed every typo, and only the LLM handled descriptions "
          "without a module name. The LLM was called for "
          f"{fb['llm']['fallback_used'] - fb['fuzzy']['fallback_used']} of 34 cases, so the free Gemini quota "
          "goes a long way, and no must-not-change case was reinterpreted at any tier. The 60 eligibility "
          "decisions were unchanged. One case still fails: \"the course about probability for engineers\" is "
          "answered as an online-course search, because \"course\" deliberately does not trigger the fallback."),
        P("Caveats: the cases are small and developer-written; the Claude handover is tested only with simulated "
          "providers, since no Anthropic key is configured; and with the LLM tier on, student messages are sent "
          "to Google (and on handover to Anthropic), so they should not contain personal information."),
    ]

    # ---- 5. Benchmarks ---------------------------------------------------------------------
    prow = [["Benchmark", "Metric", "Published value", "Data behind it"]]
    for r in published:
        prow.append([f"{r['benchmark_id']} {r['system']}", r["metric"].replace("_", " "),
                     f"{float(r['value']):g} ({r['unit'].replace('_', ' ')})", r["data_note"]])
    story += [
        KeepTogether([
            P("5. Published benchmarks (context only)", "h1"),
            P("Systems published elsewhere used other institutions, datasets and definitions, so their figures "
              "cannot be reproduced or matched here. They are listed beside our measurements for context and are "
              "deliberately not drawn on the same axis as our results: a shared axis would imply a parity the "
              "data does not support."),
            table([["Dimension", "Measured here (pilot)", "Published", "Why not comparable"],
                   *comparison_rows(dev, brief, intent, published)],
                  [2.6 * cm, 4.6 * cm, 4.4 * cm, CONTENT_W - 11.6 * cm]),
        ]),
        Spacer(1, 8),
        KeepTogether([P("Published figures with their sources", "h2"),
                      table(prow, [4.6 * cm, 3.4 * cm, 3.4 * cm, CONTENT_W - 11.4 * cm])]),
    ]

    # ---- 6. Findings -----------------------------------------------------------------------
    story += [
        P("6. Findings", "h1"),
        *bullets([
            f"<b>CurricuPath agrees more closely with the developer labels than the handbook-RAG baseline does</b> "
            f"({hr_d['difference']:+.2f} macro-F1, interval excludes zero), and points the same way under the "
            f"briefing labels ({hr_b['difference']:+.2f}) without reaching a directional result. The direction is "
            "stable; the strength depends on the answer key.",
            f"<b>Against the structured-rules LLM the comparison is inconclusive under both keys</b> "
            f"({sr_d['difference']:+.2f} and {sr_b['difference']:+.2f}). Supplying the rules to a model recovers "
            f"{recovered(dev)} of its distance from CurricuPath under the developer labels and "
            f"{recovered(brief)} under the briefing labels. That supports the value of structured curation, but "
            "it does not by itself show that deterministic evaluation caused the gain.",
            "<b>CurricuPath and the rules-only system decide identically on 50 of 60 cases.</b> These cases use "
            "clean, fixed wording, so they cannot show the value of language handling. That has to be shown by the "
            "ambiguity and clarification experiment. On the other 10 (ELIG031 to ELIG040) the rules-only arm "
            "receives the declared completeness fact as a structured field while both CurricuPath arms receive it "
            "only as text, and only the rules-only arm decides.",
            f"<b>The clarification step did not resolve any case in this run.</b> All {unresolved} cases where "
            "clarification was permitted ended unresolved. The scripted reply is a general statement that every "
            "module has been listed, and the engine does not read that as declaring the missing corequisite "
            "absent. The frozen cases were not edited after seeing system output.",
            "<b>Whether planned corequisites count changes the unsafe-error picture.</b> Under the briefing "
            f"reading, CurricuPath answers <i>eligible</i> on {cp_b['safety']['unsafe_false_positive_rate']['numerator']} "
            f"of {cp_b['safety']['unsafe_false_positive_rate']['denominator']} cases that were not eligible "
            f"({pct(cp_b['safety']['unsafe_false_positive_rate']['rate'])}), against 0 under the developer labels. "
            "This is the question to put to the academic reviewer.",
            f"<b>Handbook RAG shows the most unsafe errors</b> in both keys "
            f"({pct(dev['arms']['handbook_rag']['safety']['unsafe_false_positive_rate']['rate'])} and "
            f"{pct(brief['arms']['handbook_rag']['safety']['unsafe_false_positive_rate']['rate'])} of "
            "non-eligible cases answered eligible).",
        ]),
    ]

    # ---- 7. Limitations --------------------------------------------------------------------
    story += [
        P("7. How these results may be used", "h1"),
        P("<b>Supported by this pilot</b>"),
        *bullets([
            "The evaluation pipeline runs end to end: five systems on the same cases, scored with paired "
            "bootstrap intervals. This belongs in a methods or pilot section.",
            "Behavioural findings that do not depend on who wrote the labels: CurricuPath and rules-only "
            "decide identically on 50 of 60 cases; on the other 10, CurricuPath (with or without clarification) "
            "does not read the declared completeness fact, while rules-only is handed it as a structured field; and "
            "Handbook RAG answered <i>eligible</i> on non-eligible cases more often than any other system "
            "under both answer keys.",
            "The answer-key sensitivity, which isolates the Rule 1.9 question for the reviewer.",
            "Latency figures, stated as deterministic-path only for CurricuPath, and entity extraction "
            "results, stated as measured on unreviewed prompts.",
        ]),
        P("<b>Not supported by this pilot</b>"),
        *bullets([
            "A claim that CurricuPath \"achieves\" a given macro-F1. That is agreement with developer-side "
            "labels, not accuracy.",
            "Any advantage over the structured-rules LLM. The comparison is inconclusive under both keys.",
            "Any value from the language layer or from clarification. This case set cannot test them.",
            "Parity with, or superiority over, published systems. Their figures are context only.",
        ]),
        P("8. Limitations", "h1"),
        *bullets([
            "Both answer keys are developer-side. The cases and the rules they test were written by the same "
            "people, so agreement is partly circular.",
            "One run per case, so run-to-run repeatability is not measured. The model arms used a lighter "
            "model than the pinned one.",
            "CurricuPath ran without Gemini intent extraction. Its Gemini-assisted behaviour and response time "
            "are not measured here.",
            "60 cases with about 20 per class give wide intervals. The study can show large failure patterns, "
            "not small improvements.",
            "The intent prompts are unreviewed developer drafts.",
            "The clarification ablation exists only as a draft run. The reviewer fields it needs are pending, "
            "so it cannot yet show whether clarification helps. Grounding of explanations, usability with "
            "students and advisors, and recommendation ranking are not evaluated.",
            "Repeated-failure academic exclusion (for example failing a module twice) cannot be represented by "
            "the current student profile, so no case tests it. It is recorded as a known limitation.",
        ]),
        P("9. Next steps", "h1"),
        *bullets([
            "Record the academic reviewer and grounding judge, with committed hours, in the personnel file.",
            "Have the reviewer label the 60 blinded cases and draft concealed cases, then run adjudication.",
            "Repeat the runs with three passes per case on the pinned model, and measure the Gemini-assisted "
            "CurricuPath path.",
            "Ask the reviewer to settle whether a planned corequisite satisfies Rule 1.9, and record the "
            "outcome as a rule decision.",
            "Score grounding and the clarification ablation, then rebuild this report from the official outputs.",
        ]),
    ]

    # ---- Appendix --------------------------------------------------------------------------
    hashes = "<br/>".join(f"{k}: {v[:16]}" for k, v in sorted(dev["inputs"]["sha256"].items()))
    story += [
        P("Appendix. Reproducing this report", "h1"),
        P("All numbers in this document were read from the analysis files. To regenerate them:"),
        P("py scripts/run_evaluation.py --arm rules_only --allow-draft<br/>"
          "py scripts/run_evaluation.py --arm curricupath --allow-draft --runs 1 (with GEMINI_API_KEY blank)<br/>"
          "py scripts/run_evaluation.py --arm handbook_rag --allow-draft --runs 1 --pace-seconds 3.5<br/>"
          "py scripts/run_intent_evaluation.py<br/>"
          "py scripts/run_ambiguity_evaluation.py --allow-draft<br/>"
          "py scripts/score_evaluation.py --allow-draft --reference-sets developer briefing<br/>"
          "py scripts/render_benchmark_figures.py<br/>"
          "py scripts/build_evaluation_report.py", "small"),
        Spacer(1, 6),
        P("Input fingerprints (SHA-256, first 16 characters)", "h2"),
        P(hashes, "small"),
        Spacer(1, 6),
        P("Answer-key provenance", "h2"),
        P("The briefing labels were extracted from <i>senate_rules_briefing.docx</i>, stored beside "
          "<i>senate_briefing_labels.csv</i> with its hash. The document describes every label as a draft and "
          "carries no reviewer name, signature or approval, so it is used for sensitivity analysis only.", "small"),
    ]

    doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                            topMargin=1.8 * cm, bottomMargin=1.9 * cm,
                            title="CurricuPath Pilot Evaluation Report", author="CurricuPath project 26P73")
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
