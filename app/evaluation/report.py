"""Write scored evaluation results as JSON, CSV and report-ready markdown tables."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from app.evaluation.figures import ARM_NAMES, ARM_ORDER, DRAFT_NOTE
from app.evaluation.scoring import LABELS

FAILURE_CATEGORIES = (
    "source", "label", "rule_encoding", "parser", "condition_evaluation",
    "clarification", "baseline_retrieval", "generation", "explanation",
)
NOT_COMPUTED = (
    "Material-reason completeness: needs reviewer-approved reasons matched to each answer.",
    "Reviewer agreement (pre-adjudication): needs the independent reviewers' raw labels.",
    "Grounding and claim-support metrics (Experiment B): scored by a separate procedure.",
    "Ambiguity ablation (Experiment C): scored by a separate procedure.",
)


def _arms(summary: Mapping[str, Any]) -> list[str]:
    return [arm for arm in ARM_ORDER if arm in summary["arms"]]


def _f(value: float | None, digits: int = 3) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def _ci(interval: Sequence[float]) -> str:
    return f"{interval[0]:.2f} to {interval[1]:.2f}"


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["empty"])
        writer.writeheader()
        writer.writerows(rows)


def arm_rows(summary: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for arm in _arms(summary):
        data = summary["arms"][arm]
        row: dict[str, Any] = {
            "arm": arm,
            "n_cases": data["n_cases"],
            "missing_cases": len(data["missing_cases"]),
            "provider_failures": len(data["provider_failure_cases"]),
            "macro_f1": data["macro_f1"],
            "macro_f1_ci95_low": data["macro_f1_ci95"][0],
            "macro_f1_ci95_high": data["macro_f1_ci95"][1],
            "balanced_accuracy": data["balanced_accuracy"],
            "balanced_accuracy_ci95_low": data["balanced_accuracy_ci95"][0],
            "balanced_accuracy_ci95_high": data["balanced_accuracy_ci95"][1],
            "accuracy": data["accuracy"],
        }
        for label in LABELS:
            for metric in ("precision", "recall", "f1", "support"):
                row[f"{label}_{metric}"] = data["per_class"][label][metric]
        for name, rate in data["safety"].items():
            row[name] = rate["rate"]
        row["latency_median_ms"] = data["latency"].get("median_ms")
        row["latency_p95_ms"] = data["latency"].get("p95_ms")
        row["three_run_agreement"] = data["stability"]["exact_agreement_rate"]
        row["decision_change_rate"] = data["stability"]["decision_change_rate"]
        row["majority_vote_macro_f1"] = data.get("majority_vote_sensitivity", {}).get("macro_f1")
        rows.append(row)
    return rows


def case_rows(cases: Sequence[Mapping[str, str]], summary: Mapping[str, Any]) -> list[dict[str, Any]]:
    arms = _arms(summary)
    rows = []
    for case in cases:
        row: dict[str, Any] = {
            "case_id": case["case_id"],
            "author_source": case["author_source"],
            "scenario_type": case["scenario_type"],
            "reference_label": case["reference_label"],
        }
        for arm in arms:
            decision = summary["decisions_by_case"][arm][case["case_id"]]
            row[f"{arm}_decision"] = decision
            row[f"{arm}_correct"] = decision == case["reference_label"]
        row["failure_category"] = ""
        rows.append(row)
    return rows


def markdown(summary: Mapping[str, Any], provenance: Mapping[str, Any], *, draft: bool) -> str:
    arms = _arms(summary)
    lines = ["# Evaluation results tables", ""]
    if draft:
        lines += [f"> **{DRAFT_NOTE}.** Do not cite these numbers as results.", ""]
    lines += [
        f"Reference: {provenance['reference_source']}. Cases scored: {summary['n_cases']}. "
        f"Primary run: {summary['primary_run']}. Intervals: case-level bootstrap, "
        f"{summary['bootstrap']['resamples']} resamples, seed {summary['bootstrap']['seed']}.",
        "",
        "## Table 1. Agreement with reference labels",
        "",
        "| System | Macro-F1 (95% CI) | Balanced accuracy (95% CI) | Accuracy | Invalid outputs |",
        "| --- | --- | --- | --- | --- |",
    ]
    for arm in arms:
        d = summary["arms"][arm]
        lines.append(
            f"| {ARM_NAMES[arm]} | {d['macro_f1']:.2f} ({_ci(d['macro_f1_ci95'])}) | "
            f"{d['balanced_accuracy']:.2f} ({_ci(d['balanced_accuracy_ci95'])}) | "
            f"{d['accuracy']:.2f} | {d['safety']['invalid_output_rate']['numerator']} |"
        )
    provider = {a: len(summary["arms"][a]["provider_failure_cases"]) for a in arms
                if summary["arms"][a]["provider_failure_cases"]}
    if provider:
        lines += ["", "> **Warning: provider failures.** These runs were refused by the hosted service "
                  f"(quota or outage), not answered wrongly: {provider}. They are scored as errors "
                  "above. Re-run those systems before interpreting them."]
    lines += ["", "## Table 2. Error types", "",
              "| System | Unsafe false positive | Overly conservative | Correct escalation | "
              "Unsafe overconfidence | Unnecessary escalation |",
              "| --- | --- | --- | --- | --- | --- |"]
    keys = ("unsafe_false_positive_rate", "overly_conservative_false_negative_rate",
            "correct_escalation_rate", "unsafe_overconfidence_rate_on_manual_review",
            "unnecessary_escalation_rate")
    for arm in arms:
        cells = []
        for key in keys:
            rate = summary["arms"][arm]["safety"][key]
            cells.append("n/a" if rate["rate"] is None
                         else f"{rate['rate'] * 100:.0f}% ({rate['numerator']}/{rate['denominator']})")
        lines.append(f"| {ARM_NAMES[arm]} | " + " | ".join(cells) + " |")
    if summary["paired_differences"]:
        lines += ["", "## Table 3. Paired differences (case-level bootstrap)", "",
                  "| Comparison | Metric | Difference | 95% CI | Reading |", "| --- | --- | --- | --- | --- |"]
        for r in summary["paired_differences"]:
            lines.append(
                f"| {ARM_NAMES[r['first_arm']]} minus {ARM_NAMES[r['second_arm']]} | {r['metric']} | "
                f"{r['difference']:+.2f} | {r['ci95_low']:+.2f} to {r['ci95_high']:+.2f} | {r['verdict']} |"
            )
    lines += ["", "## Table 4. Latency and repeatability", "",
              "| System | Median ms | 95th percentile ms | Same decision in 3 runs | Decision-change rate |",
              "| --- | --- | --- | --- | --- |"]
    for arm in arms:
        d = summary["arms"][arm]
        lines.append(
            f"| {ARM_NAMES[arm]} | {_f(d['latency'].get('median_ms'), 0)} | "
            f"{_f(d['latency'].get('p95_ms'), 0)} | {_f(d['stability']['exact_agreement_rate'], 2)} | "
            f"{_f(d['stability']['decision_change_rate'], 2)} |"
        )
    incomplete = {a: len(summary["arms"][a]["missing_cases"]) for a in arms if summary["arms"][a]["missing_cases"]}
    lines += ["", "## Limits of these tables", "",
              "- Prototype study: with about 15 cases per class, intervals are wide. Report "
              "`inconclusive` rather than reading small differences as real.",
              "- Every disagreement still needs a `failure_category` in `case_decisions.csv` "
              f"({', '.join(FAILURE_CATEGORIES)}).",
              *(f"- Not computed here: {item}" for item in NOT_COMPUTED)]
    if provenance["rejected_cases"]:
        lines.append(f"- Excluded as rejected by reviewers: {', '.join(provenance['rejected_cases'])}.")
    if incomplete:
        lines.append(f"- Missing outputs scored as errors: {incomplete}.")
    return "\n".join(lines) + "\n"


def sensitivity_markdown(
    results: Mapping[str, tuple[Mapping[str, Any], Mapping[str, Any]]],
    agreement: Mapping[str, Any],
    disagreements: Sequence[tuple[str, str, str]],
) -> str:
    first, second = list(results)
    arms = _arms(results[first][0])
    lines = [
        "# Label-set sensitivity",
        "",
        f"> **{DRAFT_NOTE}.** Both label sets are developer-side; neither is independent evidence.",
        "",
        "This shows how far each result depends on which reading of the rules is used as the "
        "answer key. The main difference is whether a corequisite that is only *planned* counts "
        "as satisfied (Rule 1.9 of the Senate Rules).",
        "",
        "## Label sets",
        "",
        *(f"- **{name}**: {results[name][1]['reference_source']}" for name in results),
        "",
        f"Agreement between the two sets: {agreement['raw_agreement'] * 100:.0f}% of "
        f"{agreement['n_cases']} cases, Cohen's kappa {_f(agreement['cohens_kappa'], 2)}. "
        f"They differ on {len(disagreements)} cases.",
        "",
        f"| {first} \\ {second} | " + " | ".join(LABELS) + " |",
        "| --- | --- | --- | --- |",
        *(f"| {label} | " + " | ".join(str(v) for v in row) + " |"
          for label, row in zip(LABELS, agreement["counts"])),
        "",
        "## Macro-F1 by label set",
        "",
        f"| System | {first} | {second} | Change |",
        "| --- | --- | --- | --- |",
    ]
    for arm in arms:
        a, b = (results[name][0]["arms"][arm] for name in (first, second))
        lines.append(f"| {ARM_NAMES[arm]} | {a['macro_f1']:.2f} ({_ci(a['macro_f1_ci95'])}) | "
                     f"{b['macro_f1']:.2f} ({_ci(b['macro_f1_ci95'])}) | {b['macro_f1'] - a['macro_f1']:+.2f} |")
    verdicts = {name: {(p["first_arm"], p["second_arm"]): p for p in results[name][0]["paired_differences"]
                       if p["metric"] == "macro_f1"} for name in results}
    lines += ["", "## Does the comparison verdict change?", ""]
    if verdicts[first]:
        lines += [f"| Comparison (macro-F1) | {first} | {second} |", "| --- | --- | --- |"]
        for pair in verdicts[first]:
            cells = [f"{verdicts[name][pair]['difference']:+.2f}: {verdicts[name][pair]['verdict'].split(' (')[0]}"
                     for name in results]
            lines.append(f"| {ARM_NAMES[pair[0]]} minus {ARM_NAMES[pair[1]]} | " + " | ".join(cells) + " |")
    else:
        lines.append("Not available: this needs CurricuPath and at least one other system scored.")
    lines += ["", "## Cases where the label sets differ", "",
              f"| Case | {first} | {second} |", "| --- | --- | --- |",
              *(f"| {case} | {a} | {b} |" for case, a, b in disagreements)]
    return "\n".join(lines) + "\n"


def write_sensitivity(
    results: Mapping[str, tuple[Mapping[str, Any], Mapping[str, Any]]],
    agreement: Mapping[str, Any],
    disagreements: Sequence[tuple[str, str, str]],
    output_dir: Path,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = [
        {"label_set": name, "arm": arm, "macro_f1": d["macro_f1"],
         "macro_f1_ci95_low": d["macro_f1_ci95"][0], "macro_f1_ci95_high": d["macro_f1_ci95"][1],
         "balanced_accuracy": d["balanced_accuracy"], "accuracy": d["accuracy"],
         "unsafe_false_positive_rate": d["safety"]["unsafe_false_positive_rate"]["rate"],
         "correct_escalation_rate": d["safety"]["correct_escalation_rate"]["rate"]}
        for name, (summary, _) in results.items()
        for arm in _arms(summary)
        for d in [summary["arms"][arm]]
    ]
    csv_path = output_dir / "label_set_sensitivity.csv"
    md_path = output_dir / "label_set_sensitivity.md"
    _write_csv(csv_path, rows)
    md_path.write_text(sensitivity_markdown(results, agreement, disagreements), encoding="utf-8")
    return [csv_path, md_path]


def write_outputs(
    summary: Mapping[str, Any],
    provenance: Mapping[str, Any],
    cases: Sequence[Mapping[str, str]],
    output_dir: Path,
    *,
    draft: bool,
    inputs: Mapping[str, Any],
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    slim = {k: v for k, v in summary.items() if k != "decisions_by_case"}
    payload = {"provenance": provenance, "inputs": inputs, "draft": draft, **slim}
    paths = {
        "metrics_summary.json": lambda p: p.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"),
        "arm_metrics.csv": lambda p: _write_csv(p, arm_rows(summary)),
        "paired_differences.csv": lambda p: _write_csv(p, summary["paired_differences"]),
        "stratified_accuracy.csv": lambda p: _write_csv(p, summary["stratified_accuracy"]),
        "case_decisions.csv": lambda p: _write_csv(p, case_rows(cases, summary)),
        "report_tables.md": lambda p: p.write_text(
            markdown(summary, provenance, draft=draft), encoding="utf-8"),
    }
    written = []
    for name, write in paths.items():
        path = output_dir / name
        write(path)
        written.append(path)
    return written
