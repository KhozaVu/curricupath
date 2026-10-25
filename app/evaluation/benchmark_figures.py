"""Set pilot measurements beside figures published for other systems, as a table.

Published figures are context only. They are deliberately not plotted next to our results:
they come from other institutions, datasets and definitions, so a shared axis would imply a
parity the data cannot support.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Mapping, Sequence

from app.evaluation.figures import (
    ARM_COLOURS, DRAFT_NOTE, INK, INK_2, SURFACE, _finish, _pyplot, _style,
)

CAVEAT = (
    "Published figures use other institutions, datasets and definitions. They are listed for "
    "context and are not directly comparable."
)


def load_published(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _published(rows: Sequence[Mapping[str, str]], counterpart: str) -> list[Mapping[str, str]]:
    return [r for r in rows if r["our_counterpart"] == counterpart]


def _published_text(rows: Sequence[Mapping[str, str]], counterpart: str) -> str:
    return "; ".join(
        f"{r['benchmark_id']}: {r['metric'].replace('_', ' ')} {float(r['value']):g} ({r['data_note']})"
        for r in _published(rows, counterpart)
    )


def _seconds(ms: float) -> str:
    return "under 1 ms" if ms < 1 else (f"{ms:.0f} ms" if ms < 1000 else f"{ms / 1000:.1f} s")


def comparison_rows(
    developer: Mapping[str, Any],
    briefing: Mapping[str, Any] | None,
    intent: Mapping[str, Any],
    published: Sequence[Mapping[str, str]],
) -> list[list[str]]:
    """Dimension, measured here, published, and why the two are not like for like."""

    arms = developer["arms"]
    rows: list[list[str]] = []
    timing = []
    if "curricupath" in arms:
        timing.append(f"CurricuPath median {_seconds(arms['curricupath']['latency']['median_ms'])} "
                      "(deterministic path, no model call)")
    for arm, name in (("handbook_rag", "Handbook RAG"), ("structured_rules_llm", "structured-rules LLM")):
        if arm in arms:
            timing.append(f"{name} median {_seconds(arms[arm]['latency']['median_ms'])} (one model call)")
    rows.append(["Response time", "; ".join(timing), _published_text(published, "response_time"),
                 "The published time includes a language-model pipeline. Our CurricuPath figure contains "
                 "no model call, so only the model-backed baselines are the same kind of measurement."])
    if "curricupath" in arms:
        macro = f"CurricuPath macro-F1 {arms['curricupath']['macro_f1']:.2f} (developer labels)"
        if briefing is not None:
            macro += f", {briefing['arms']['curricupath']['macro_f1']:.2f} (briefing labels)"
        rows.append(["Decision quality", macro, _published_text(published, "eligibility_macro_f1"),
                     "Different task, metric and data. Our answer keys are developer-side, so this measures "
                     "agreement with our labels, not accuracy."])
    overall = intent["intent_accuracy"]
    ambiguous = intent["by_category"].get("ambiguous_module_name")
    detail = f"{overall['correct']}/{overall['n']} prompts correct ({overall['rate'] * 100:.0f}%)"
    if ambiguous:
        detail += f"; {ambiguous['correct']}/{ambiguous['n']} on ambiguous module names (bare topic words)"
    rows.append(["Intent understanding", detail, _published_text(published, "intent_accuracy"),
                 "Different query sets. Ours are unreviewed developer drafts, and the extractor was "
                 "measured without Gemini."])
    return rows


def comparison_markdown(
    developer: Mapping[str, Any],
    briefing: Mapping[str, Any] | None,
    intent: Mapping[str, Any],
    published: Sequence[Mapping[str, str]],
    footnote: str = "",
) -> str:
    lines = [
        "# Pilot measurements and published benchmarks", "",
        f"> **{DRAFT_NOTE}.**", "", CAVEAT, "",
        "| Dimension | Measured here | Published | Why not comparable |", "| --- | --- | --- | --- |",
        *(f"| {a} | {b} | {c} | {d} |" for a, b, c, d in comparison_rows(developer, briefing, intent, published)),
        "", "## Published figures with no measurement here yet", "",
        "| Benchmark | Metric | Value | Data |", "| --- | --- | --- | --- |",
        *(f"| {r['benchmark_id']} {r['system']} | {r['metric'].replace('_', ' ')} | {float(r['value']):g} | "
          f"{r['data_note']} |" for r in _published(published, "none_yet")),
    ]
    if footnote:
        lines += ["", "## How the pilot runs were configured", "", footnote]
    return "\n".join(lines) + "\n"


def render_intent_categories(intent: Mapping[str, Any], path: Path) -> None:
    """Intent accuracy per prompt category with 95% Wilson intervals, weakest first."""

    plt = _pyplot()
    items = sorted(intent["by_category"].items(), key=lambda kv: kv[1]["rate"])
    fig, ax = plt.subplots(figsize=(8.5, 1.6 + 0.5 * len(items)))
    _style(ax, grid_axis="x")
    for y, (category, value) in enumerate(items):
        ax.plot(value["ci95"], [y, y], color=ARM_COLOURS["curricupath"], linewidth=2, alpha=0.55, zorder=1)
        ax.plot(value["rate"], y, "o", color=ARM_COLOURS["curricupath"], markersize=9,
                markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=2)
        ax.text(1.03, y, f"{value['correct']}/{value['n']}", va="center", fontsize=8, color=INK)
    ax.set_yticks(range(len(items)), [c.replace("_", " ") for c, _ in items], fontsize=8)
    ax.set_xlim(-0.02, 1.02)
    ax.set_xlabel("Intent accuracy (dot) with 95% Wilson interval; counts at right", fontsize=8, color=INK_2)
    _finish(fig, path, "Intent accuracy by prompt category", draft=True,
            subtitle="Deterministic extractor on 100 developer-drafted, unreviewed prompts. "
                     "Categories hold 5 to 20 prompts, so intervals are wide.")
    plt.close(fig)
