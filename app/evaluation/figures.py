"""Report figures for scored v2.5 evaluation results.

Colour follows the arm, never its rank. The five-slot palette (blue, orange, aqua,
yellow, magenta) passes the adjacent-pair colour-vision checks; three slots sit below
3:1 contrast on the light surface, so every mark carries a visible value label and the
same numbers are written to CSV/markdown tables.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any, Mapping

ARM_ORDER = (
    "curricupath",
    "handbook_rag",
    "structured_rules_llm",
    "rules_only",
    "curricupath_no_clarification",
)
ARM_COLOURS = {
    "curricupath": "#2a78d6",
    "handbook_rag": "#eb6834",
    "structured_rules_llm": "#1baf7a",
    "rules_only": "#eda100",
    "curricupath_no_clarification": "#e87ba4",
}
ARM_NAMES = {
    "curricupath": "CurricuPath",
    "handbook_rag": "Handbook RAG",
    "structured_rules_llm": "Structured-rules LLM",
    "rules_only": "Rules only",
    "curricupath_no_clarification": "CurricuPath (no clarification)",
}
SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e2e1dc"
SAFETY_TITLES = {
    "unsafe_false_positive_rate": "Unsafe false positive\n(said eligible, was not)",
    "overly_conservative_false_negative_rate": "Overly conservative\n(eligible case refused)",
    "correct_escalation_rate": "Correct escalation\n(manual review caught)",
    "unsafe_overconfidence_rate_on_manual_review": "Unsafe overconfidence\n(decided a manual-review case)",
    "unnecessary_escalation_rate": "Unnecessary escalation\n(decidable case escalated)",
    "invalid_output_rate": "Invalid output\n(no valid decision)",
}
DRAFT_NOTE = "DRAFT: developer-side labels, not independent evidence"


def _pyplot():
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise RuntimeError(
            "matplotlib is required to render figures (pip install matplotlib). "
            "Tables are written without it."
        ) from error
    return plt


def _arms(summary: Mapping[str, Any]) -> list[str]:
    return [arm for arm in ARM_ORDER if arm in summary["arms"]]


def _style(ax, *, grid_axis: str = "y") -> None:
    ax.set_facecolor(SURFACE)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=8)


def _wrap(name: str, width: int = 12) -> str:
    return textwrap.fill(name, width, break_long_words=False)


def _finish(fig, path: Path, title: str, *, draft: bool, subtitle: str = "", bottom: float = 0.03) -> None:
    fig.patch.set_facecolor(SURFACE)
    fig.tight_layout(rect=(0, bottom, 1, 0.86))
    fig.text(0.01, 0.985, title, ha="left", va="top", fontsize=12, fontweight="bold", color=INK)
    if subtitle:
        fig.text(0.01, 0.925, subtitle, ha="left", va="top", fontsize=8.5, color=INK_2)
    if draft:
        fig.text(0.99, 0.01, DRAFT_NOTE, ha="right", fontsize=7.5, color=INK_2, style="italic")
    fig.savefig(path, dpi=200, facecolor=SURFACE, bbox_inches="tight")


def _pct(rate: float | None) -> str:
    return "n/a" if rate is None else f"{rate * 100:.0f}%"


def _legend(fig, arms: list[str]) -> None:
    from matplotlib.patches import Patch

    fig.legend(
        handles=[Patch(facecolor=ARM_COLOURS[a], label=ARM_NAMES[a]) for a in arms],
        loc="lower center", ncol=len(arms), frameon=False, fontsize=8,
        labelcolor=INK_2, bbox_to_anchor=(0.5, -0.06),
    )


def primary_metrics(summary, path: Path, *, draft: bool) -> None:
    plt = _pyplot()
    arms = _arms(summary)
    fig, axes = plt.subplots(1, 2, figsize=(9, 4), sharey=True)
    for ax, key, title in zip(axes, ("macro_f1", "balanced_accuracy"),
                              ("Three-class macro-F1", "Balanced accuracy")):
        _style(ax)
        for x, arm in enumerate(arms):
            data = summary["arms"][arm]
            low, high = data[f"{key}_ci95"]
            ax.bar(x, data[key], 0.6, color=ARM_COLOURS[arm], edgecolor=SURFACE, linewidth=1.5)
            ax.errorbar(x, data[key], yerr=[[max(0, data[key] - low)], [max(0, high - data[key])]],
                        color=INK_2, capsize=3, linewidth=1)
            ax.text(x, min(1.0, high) + 0.02, f"{data[key]:.2f}", ha="center", fontsize=8, color=INK)
        ax.set_xticks(range(len(arms)), [_wrap(ARM_NAMES[a]) for a in arms], fontsize=7)
        ax.set_ylim(0, 1.12)
        ax.set_title(title, fontsize=9, color=INK, loc="left")
    axes[0].set_ylabel("Score (0 to 1)", fontsize=8, color=INK_2)
    n = summary["n_cases"]
    _finish(fig, path, "Agreement with reference labels, by system", draft=draft,
            subtitle=f"{n} cases, primary run {summary['primary_run']}. Bars show the score; "
                     f"whiskers show the case-level bootstrap 95% interval.")
    plt.close(fig)


def confusion_matrices(summary, path: Path, *, draft: bool) -> None:
    import numpy as np
    from matplotlib.colors import LinearSegmentedColormap

    plt = _pyplot()
    arms = _arms(summary)
    cmap = LinearSegmentedColormap.from_list("blue", [SURFACE, "#2a78d6"])
    columns = min(3, len(arms))
    rows = -(-len(arms) // columns)
    fig, axes = plt.subplots(rows, columns, figsize=(3.4 * columns, 3.7 * rows), squeeze=False)
    for spare in axes.flat[len(arms):]:
        spare.axis("off")
    short = ["Elig.", "Inelig.", "Manual", "Invalid"]
    for ax, arm in zip(axes.flat, arms):
        counts = np.array(summary["arms"][arm]["confusion_matrix"]["counts"])
        ax.imshow(counts, cmap=cmap, vmin=0, vmax=max(1, counts.max()))
        for (r, c), value in np.ndenumerate(counts):
            dark = value > counts.max() * 0.55
            ax.text(c, r, int(value), ha="center", va="center", fontsize=9,
                    color="#ffffff" if dark else INK)
        ax.set_xticks(range(4), short, fontsize=7, color=INK_2)
        ax.set_yticks(range(3), short[:3], fontsize=7, color=INK_2)
        ax.set_title(_wrap(ARM_NAMES[arm], 18), fontsize=8.5, color=INK, loc="left")
        ax.set_xlabel("Predicted", fontsize=7.5, color=INK_2)
        for side in ax.spines.values():
            side.set_color(GRID)
    for row in axes:
        row[0].set_ylabel("Reference", fontsize=7.5, color=INK_2)
    _finish(fig, path, "Confusion matrices", draft=draft,
            subtitle="Rows are the reference label; columns are what the system returned. "
                     "Numbers are case counts.")
    plt.close(fig)


def safety_rates(summary, path: Path, *, draft: bool) -> None:
    plt = _pyplot()
    arms = _arms(summary)
    fig, axes = plt.subplots(2, 3, figsize=(10, 6.2))
    for index, (ax, (key, title)) in enumerate(zip(axes.flat, SAFETY_TITLES.items())):
        _style(ax, grid_axis="x")
        for y, arm in enumerate(arms):
            rate = summary["arms"][arm]["safety"][key]
            if rate["rate"] is not None:
                ax.barh(y, rate["rate"], 0.6, color=ARM_COLOURS[arm], edgecolor=SURFACE, linewidth=1.5)
            ax.text((rate["rate"] or 0) + 0.02, y,
                    f"{_pct(rate['rate'])} ({rate['numerator']}/{rate['denominator']})",
                    va="center", fontsize=7, color=INK)
        ax.set_xlim(0, 1.45)
        ax.set_xticks([0, 0.5, 1], ["0%", "50%", "100%"])
        ax.set_yticks(range(len(arms)))
        ax.set_yticklabels(
            [_wrap(ARM_NAMES[a], 16) for a in arms] if index % 3 == 0 else [""] * len(arms),
            fontsize=7,
        )
        if index % 3:
            ax.tick_params(axis="y", length=0)
        ax.invert_yaxis()
        ax.set_title(title, fontsize=8.5, color=INK, loc="left")
    _finish(fig, path, "Error types by system", draft=draft,
            subtitle="Each panel is one rate. The label shows the rate and its numerator/denominator.")
    plt.close(fig)


def latency(summary, path: Path, *, draft: bool) -> None:
    plt = _pyplot()
    arms = [a for a in _arms(summary) if summary["arms"][a]["latency"].get("n")]
    fig, ax = plt.subplots(figsize=(8, 3.4))
    _style(ax, grid_axis="x")
    for y, arm in enumerate(arms):
        stats = summary["arms"][arm]["latency"]
        median, p95 = max(stats["median_ms"], 1), max(stats["p95_ms"], 1)
        ax.plot([median, p95], [y, y], color=ARM_COLOURS[arm], linewidth=2)
        ax.plot(median, y, "o", color=ARM_COLOURS[arm], markersize=9, markeredgecolor=SURFACE,
                markeredgewidth=1.5)
        text = ("under 1 ms" if stats["p95_ms"] < 1 else
                f"median {stats['median_ms']:.0f} ms, p95 {stats['p95_ms']:.0f} ms")
        ax.text(p95 * 1.25, y, text, va="center", fontsize=7.5, color=INK)
    ax.set_xscale("log")
    ax.set_xlim(0.7, 1e5)
    ax.set_yticks(range(len(arms)), [ARM_NAMES[a] for a in arms], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Latency per case (milliseconds, log scale)", fontsize=8, color=INK_2)
    _finish(fig, path, "Response latency", draft=draft,
            subtitle="Dot is the median; the line runs to the 95th percentile. Log scale because the "
                     "systems differ by orders of magnitude; times under 1 ms are drawn at 1 ms.")
    plt.close(fig)


def stability(summary, path: Path, *, draft: bool) -> None:
    plt = _pyplot()
    arms = [a for a in _arms(summary) if summary["arms"][a]["stability"]["n_complete_cases"]]
    if not arms:
        return
    fig, ax = plt.subplots(figsize=(7, 3.4))
    _style(ax)
    for x, arm in enumerate(arms):
        data = summary["arms"][arm]["stability"]
        ax.bar(x, data["exact_agreement_rate"], 0.6, color=ARM_COLOURS[arm],
               edgecolor=SURFACE, linewidth=1.5)
        ax.text(x, data["exact_agreement_rate"] + 0.03,
                f"{_pct(data['exact_agreement_rate'])} (n={data['n_complete_cases']})",
                ha="center", fontsize=8, color=INK)
    ax.set_xticks(range(len(arms)), [_wrap(ARM_NAMES[a], 14) for a in arms], fontsize=8)
    ax.set_ylim(0, 1.15)
    ax.set_yticks([0, 0.5, 1], ["0%", "50%", "100%"])
    ax.set_ylabel("Cases with the same decision in all 3 runs", fontsize=8, color=INK_2)
    _finish(fig, path, "Three-run decision stability", draft=draft,
            subtitle="Repeated runs are not independent cases; this measures repeatability only.")
    plt.close(fig)


def paired_differences(summary, path: Path, *, draft: bool) -> None:
    plt = _pyplot()
    rows = [r for r in summary["paired_differences"] if r["metric"] == "macro_f1"]
    if not rows:
        return
    fig, ax = plt.subplots(figsize=(8, max(3.2, 0.9 + 0.75 * len(rows))))
    _style(ax, grid_axis="x")
    ax.axvline(0, color=INK_2, linewidth=1)
    for y, row in enumerate(rows):
        colour = ARM_COLOURS[row["second_arm"]]
        ax.plot([row["ci95_low"], row["ci95_high"]], [y, y], color=colour, linewidth=2)
        ax.plot(row["difference"], y, "o", color=colour, markersize=9, markeredgecolor=SURFACE,
                markeredgewidth=1.5)
        reading = row["verdict"].split(" (")[0].replace("first arm", ARM_NAMES[row["first_arm"]])
        ax.text(1.03, y, reading, transform=ax.get_yaxis_transform(),
                va="center", fontsize=7.5, color=INK)
    ax.set_yticks(range(len(rows)), [f"vs {ARM_NAMES[r['second_arm']]}" for r in rows], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(-1, 1)
    ax.set_xlabel(f"{ARM_NAMES[rows[0]['first_arm']]} minus comparison, macro-F1", fontsize=8, color=INK_2)
    _finish(fig, path, "Paired macro-F1 difference", draft=draft,
            subtitle="Dot is the difference; the line is the case-level bootstrap 95% interval. "
                     "An interval that includes 0 is reported as inconclusive.")
    plt.close(fig)


def stratified(summary, path: Path, *, draft: bool) -> None:
    plt = _pyplot()
    arms = _arms(summary)
    rows = summary["stratified_accuracy"]
    groups = list(dict.fromkeys((r["stratum"], r["value"], r["n"]) for r in rows))
    fig, ax = plt.subplots(figsize=(9, 0.9 + 0.55 * len(groups)))
    _style(ax, grid_axis="x")
    lane = 0.13
    for y, (stratum, value, n) in enumerate(groups):
        for position, arm in enumerate(arms):
            hit = next(r for r in rows if (r["stratum"], r["value"], r["arm"]) == (stratum, value, arm))
            # Each system gets its own lane so identical scores never hide one another.
            ax.plot(hit["accuracy"], y + (position - (len(arms) - 1) / 2) * lane, "o",
                    color=ARM_COLOURS[arm], markersize=6, markeredgecolor=SURFACE, markeredgewidth=1)
    ax.set_yticks(range(len(groups)), [f"{s}: {v} (n={n})" for s, v, n in groups], fontsize=7)
    ax.invert_yaxis()
    ax.set_xlim(-0.03, 1.03)
    ax.set_xticks([0, 0.5, 1], ["0%", "50%", "100%"])
    ax.set_xlabel("Exact-match accuracy within the subset", fontsize=8, color=INK_2)
    _legend(fig, arms)
    _finish(fig, path, "Accuracy by case subset", draft=draft,
            subtitle="Subsets are small; read these as failure patterns, not precise rates.")
    plt.close(fig)


def label_set_sensitivity(results: Mapping[str, Mapping[str, Any]], path: Path, *, draft: bool) -> None:
    """Macro-F1 per system under two answer keys; a long line means a fragile result."""

    plt = _pyplot()
    first, second = list(results)
    arms = _arms(results[first])
    fig, ax = plt.subplots(figsize=(8, max(3.2, 1.2 + 0.7 * len(arms))))
    _style(ax, grid_axis="x")
    for y, arm in enumerate(arms):
        a = results[first]["arms"][arm]["macro_f1"]
        b = results[second]["arms"][arm]["macro_f1"]
        colour = ARM_COLOURS[arm]
        ax.plot([a, b], [y, y], color=colour, linewidth=2, zorder=1)
        ax.plot(a, y, "o", color=colour, markersize=9, markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=2)
        ax.plot(b, y, "D", color=colour, markersize=8, markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=2)
        left, right = (a, b) if a <= b else (b, a)
        ax.text(left - 0.025, y, f"{left:.2f}", ha="right", va="center", fontsize=8, color=INK)
        ax.text(right + 0.025, y, f"{right:.2f}", ha="left", va="center", fontsize=8, color=INK)
    ax.set_yticks(range(len(arms)), [ARM_NAMES[a] for a in arms], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Three-class macro-F1", fontsize=8, color=INK_2)
    _finish(fig, path, "How much the score depends on the answer key", draft=draft,
            subtitle=f"Circle = {first} labels, diamond = {second} labels. Both are developer-side; "
                     f"a long line means the result is fragile.")
    plt.close(fig)


FIGURES = {
    "fig1_primary_metrics.png": primary_metrics,
    "fig2_confusion_matrices.png": confusion_matrices,
    "fig3_error_types.png": safety_rates,
    "fig4_latency.png": latency,
    "fig5_stability.png": stability,
    "fig6_paired_differences.png": paired_differences,
    "fig7_accuracy_by_subset.png": stratified,
}


def render_all(summary: Mapping[str, Any], output_dir: Path, *, draft: bool) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, draw in FIGURES.items():
        path = output_dir / name
        draw(summary, path, draft=draft)
        if path.exists():
            written.append(path)
    return written
