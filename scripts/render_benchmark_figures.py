"""Render the intent figure and the pilot-versus-published context table (draft outputs only)."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EVALUATION = PROJECT_ROOT / "experiments" / "evaluation" / "v2_5"
ANALYSIS = EVALUATION / "results" / "draft_analysis"

from app.evaluation import benchmark_figures as bench


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _configuration_note() -> str:
    config = _load(EVALUATION / "results" / "raw" / "draft_run_config.json")
    if not config:
        return ""
    return "Pilot configuration: " + " ".join(config["deviations_from_frozen_protocol"])


def main() -> None:
    developer = _load(ANALYSIS / "developer" / "metrics_summary.json") or _load(ANALYSIS / "metrics_summary.json")
    briefing = _load(ANALYSIS / "briefing" / "metrics_summary.json")
    intent = _load(ANALYSIS / "intent_metrics.json")
    if developer is None or intent is None:
        raise SystemExit(
            "Run score_evaluation.py --allow-draft and run_intent_evaluation.py first."
        )
    published = bench.load_published(EVALUATION / "pilot" / "published_benchmarks.csv")
    note = _configuration_note()

    figures = ANALYSIS / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    bench.render_intent_categories(intent, figures / "fig10_intent_by_category.png")
    table = ANALYSIS / "benchmark_comparison.md"
    table.write_text(bench.comparison_markdown(developer, briefing, intent, published, note),
                     encoding="utf-8")
    print(f"Wrote {figures / 'fig10_intent_by_category.png'}\nWrote {table}")


if __name__ == "__main__":
    main()
