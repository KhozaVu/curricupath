"""Before/after curves for the clarification fixes, on the development and held-out prompt sets.

Reads summaries written by scripts/diagnose_clarification.py. Diagnostic only: developer-generated
prompts and simulated replies, not the frozen evaluation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
SWEEPS = PROJECT_ROOT / "experiments" / "evaluation" / "v2_5" / "results" / "diagnostics" / "clarification_sweep"

from app.evaluation.figures import INK, INK_2, SURFACE, _finish, _pyplot, _style

PANELS = [
    ("Development set (prompts studied while fixing)", "baseline", "after_fixes"),
    ("Held-out set (unseen modules and phrasings)", "heldout_before", "heldout_after"),
]
TICKS = ["0\ncode", "1\nfull name", "2\nno series", "3\ntopic word", "4\nno topic"]
BEFORE, AFTER = "#8f8e88", "#2a78d6"


def _load(label):
    return json.loads((SWEEPS / label / "summary.json").read_text(encoding="utf-8"))


def main() -> None:
    plt = _pyplot()
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), sharey=True)
    rows = []
    for ax, (title, before_label, after_label) in zip(axes, PANELS):
        before, after = _load(before_label), _load(after_label)
        _style(ax)
        xs = [s["level"] for s in after["levels"]]
        series = [
            (before, "with_clarification_rate", BEFORE, "o", "-", "Before fixes, with one reply"),
            (after, "single_turn_rate", AFTER, "s", "--", "After fixes, clarification switched off"),
            (after, "with_clarification_rate", AFTER, "o", "-", "After fixes, with one reply"),
        ]
        for data, key, colour, marker, style, label in series:
            ys = [s[key] for s in data["levels"]]
            ax.plot(xs, ys, linestyle=style, marker=marker, color=colour, linewidth=2 if style == "-" else 1.4,
                    markersize=7, markeredgecolor=SURFACE, markeredgewidth=1.2, label=label,
                    alpha=1 if style == "-" else 0.75)
        for s_before, s_after in zip(before["levels"], after["levels"]):
            ax.text(s_after["level"], s_after["with_clarification_rate"] + 0.04,
                    f"{s_after['with_clarification_rate'] * 100:.0f}%", ha="center", fontsize=7.5, color=AFTER)
            ax.text(s_before["level"], s_before["with_clarification_rate"] - 0.075,
                    f"{s_before['with_clarification_rate'] * 100:.0f}%", ha="center", fontsize=7.5, color=INK_2)
            rows.append((title.split(" (")[0], s_after["level"], s_before["with_clarification_rate"],
                         s_after["with_clarification_rate"], s_after["n"]))
        ax.set_xticks(xs, TICKS, fontsize=7.5)
        ax.set_ylim(-0.08, 1.12)
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1], ["0%", "25%", "50%", "75%", "100%"])
        ax.set_xlabel("Ambiguity of the question", fontsize=8, color=INK_2)
        n = after["n_prompts"]
        ax.set_title(f"{title}\n{after['targets']} modules, {n} prompts", fontsize=9.5, color=INK, loc="left",
                     fontweight="bold")
    axes[0].set_ylabel("Final answer is about the intended module", fontsize=8, color=INK_2)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=7.5, loc="lower center", ncol=4,
               bbox_to_anchor=(0.5, -0.06))
    path = SWEEPS / "before_after_curve.png"
    _finish(fig, path, "Clarification before and after the fixes", draft=False,
            subtitle="Solid: with one simulated reply naming the module. Dashed: clarification switched off (best guess, no question). The held-out panel "
                     "shows how far the fixes generalise beyond the prompts they were built on.")
    fig.text(0.99, 0.005, "DIAGNOSTIC: developer-generated prompts and replies; not the frozen evaluation",
             ha="right", fontsize=7.5, color=INK_2, style="italic")
    fig.savefig(path, dpi=200, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    for name, level, b, a, n in rows:
        print(f"{name:12s} level {level}: {b * 100:5.0f}% -> {a * 100:5.0f}%  (n={n})")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
