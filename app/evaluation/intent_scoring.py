"""Score intent-extraction runs against expected intents and entities."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence


def wilson_interval(successes: int, total: int, z: float = 1.96) -> list[float]:
    """95% Wilson score interval for a proportion; sensible for small samples."""

    if total == 0:
        return [0.0, 0.0]
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    half = z * ((p * (1 - p) / total + z * z / (4 * total * total)) ** 0.5) / denominator
    return [max(0.0, centre - half), min(1.0, centre + half)]


def _proportion(successes: int, total: int) -> dict[str, Any]:
    return {
        "correct": successes,
        "n": total,
        "rate": successes / total if total else None,
        "ci95": wilson_interval(successes, total),
    }


def _norm(value: Any) -> str:
    return "" if value in (None, "") else str(value).strip().upper()


def score_intent(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Records carry expected_* and predicted_* fields plus category and latency_ms.

    Entity accuracy is scored only where an entity was expected, so a system is never
    credited for correctly returning nothing.
    """

    by_category: dict[str, list[bool]] = defaultdict(list)
    for record in records:
        by_category[record["category"]].append(
            _norm(record["predicted_intent"]) == _norm(record["expected_intent"])
        )
    result: dict[str, Any] = {
        "n_cases": len(records),
        "intent_accuracy": _proportion(
            sum(sum(flags) for flags in by_category.values()), len(records)
        ),
        "by_category": {
            category: _proportion(sum(flags), len(flags))
            for category, flags in sorted(by_category.items())
        },
    }
    for entity in ("module_code", "programme_code", "year_of_study"):
        expected = [r for r in records if _norm(r[f"expected_{entity}"])]
        hits = sum(_norm(r[f"predicted_{entity}"]) == _norm(r[f"expected_{entity}"]) for r in expected)
        result[f"{entity}_accuracy"] = _proportion(hits, len(expected))
    result["misses"] = [
        {"case_id": r["case_id"], "category": r["category"],
         "expected": r["expected_intent"], "predicted": r["predicted_intent"]}
        for r in records
        if _norm(r["predicted_intent"]) != _norm(r["expected_intent"])
    ]
    latencies = sorted(r["latency_ms"] for r in records if r.get("latency_ms") is not None)
    result["latency_ms"] = (
        {"median": latencies[len(latencies) // 2], "max": latencies[-1]} if latencies else {}
    )
    return result
