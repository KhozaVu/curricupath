"""Measure the deterministic intent extractor on the draft intent dataset.

The 100-case set is a developer draft that has not been independently reviewed, so
every result is a pilot figure. Uses no hosted model and consumes no quota.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from time import perf_counter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EVALUATION = PROJECT_ROOT / "experiments" / "evaluation"
RAW = EVALUATION / "v2_5" / "results" / "raw"
OUTPUT = EVALUATION / "v2_5" / "results" / "draft_analysis" / "intent_metrics.json"

from app.advisor.intent import DeterministicIntentExtractor
from app.config import get_settings
from app.data.repository import CsvCatalogueRepository
from app.evaluation.intent_scoring import score_intent


def main() -> None:
    settings = get_settings()
    repository = CsvCatalogueRepository(settings.processed_data_directory)
    extractor = DeterministicIntentExtractor(repository.get_aliases())
    with (EVALUATION / "intent_cases.csv").open(newline="", encoding="utf-8") as handle:
        cases = list(csv.DictReader(handle))

    records = []
    for case in cases:
        started = perf_counter()
        parsed = extractor.extract(case["prompt"])
        elapsed_ms = (perf_counter() - started) * 1000
        records.append({
            "case_id": case["prompt_id"],
            "category": case["category"],
            "prompt": case["prompt"],
            "expected_intent": case["expected_intent"],
            "predicted_intent": parsed.intent,
            "expected_module_code": case["expected_module_code"],
            "predicted_module_code": parsed.module_code,
            "expected_programme_code": case["expected_programme_code"],
            "predicted_programme_code": parsed.programme_code,
            "expected_year_of_study": case["expected_year_of_study"],
            "predicted_year_of_study": parsed.year_of_study,
            "latency_ms": round(elapsed_ms, 3),
        })

    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "draft_intent_deterministic.jsonl").write_text(
        "\n".join(json.dumps(r, sort_keys=True) for r in records) + "\n", encoding="utf-8"
    )
    summary = {
        "status": "DRAFT: developer-authored, unreviewed cases; deterministic extractor only",
        "extractor": "DeterministicIntentExtractor (no Gemini)",
        **score_intent(records),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    accuracy = summary["intent_accuracy"]
    print(f"Intent accuracy: {accuracy['correct']}/{accuracy['n']} = {accuracy['rate']:.3f} "
          f"(95% CI {accuracy['ci95'][0]:.2f} to {accuracy['ci95'][1]:.2f})")
    for category, value in summary["by_category"].items():
        print(f"  {category:28s} {value['correct']:3d}/{value['n']:<3d} {value['rate']:.2f}")
    for entity in ("module_code", "programme_code", "year_of_study"):
        v = summary[f"{entity}_accuracy"]
        print(f"{entity} accuracy: {v['correct']}/{v['n']}")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
