"""Tests for intent scoring and the benchmark comparison output."""

from __future__ import annotations

import pytest

from app.evaluation import benchmark_figures as bench
from app.evaluation.intent_scoring import score_intent, wilson_interval


def _record(case_id, category, expected, predicted, exp_module="", pred_module=None):
    return {"case_id": case_id, "category": category, "expected_intent": expected,
            "predicted_intent": predicted, "expected_module_code": exp_module,
            "predicted_module_code": pred_module, "expected_programme_code": "",
            "predicted_programme_code": None, "expected_year_of_study": "",
            "predicted_year_of_study": None, "latency_ms": 1.0}


def test_wilson_interval_matches_hand_calculation() -> None:
    low, high = wilson_interval(85, 100)

    assert low == pytest.approx(0.7671, abs=1e-3)
    assert high == pytest.approx(0.9069, abs=1e-3)
    assert wilson_interval(0, 0) == [0.0, 0.0]
    assert wilson_interval(10, 10)[1] == 1.0


def test_score_intent_scores_entities_only_where_expected() -> None:
    records = [
        _record("A", "eligibility", "eligibility", "eligibility", "ELEN2017A", "ELEN2017A"),
        _record("B", "eligibility", "eligibility", "unknown", "ELEN2003A", None),
        _record("C", "greeting", "greeting", "greeting"),
    ]

    result = score_intent(records)

    assert result["intent_accuracy"]["correct"] == 2 and result["intent_accuracy"]["n"] == 3
    assert result["by_category"]["eligibility"]["rate"] == 0.5
    assert result["module_code_accuracy"] == {**result["module_code_accuracy"], "correct": 1, "n": 2}
    assert result["programme_code_accuracy"]["n"] == 0
    assert [m["case_id"] for m in result["misses"]] == ["B"]


def _published():
    return [
        {"benchmark_id": "B6", "system": "S", "metric": "average_query_time", "value": "2.07",
         "unit": "seconds", "pages": "2-5", "data_note": "one institution",
         "our_counterpart": "response_time"},
        {"benchmark_id": "B6", "system": "S", "metric": "query_success", "value": "0.93",
         "unit": "proportion", "pages": "2-5", "data_note": "curated set",
         "our_counterpart": "intent_accuracy"},
        {"benchmark_id": "B5", "system": "R", "metric": "faithfulness", "value": "0.927",
         "unit": "proportion", "pages": "4-7", "data_note": "18 questions", "our_counterpart": "none_yet"},
    ]


def _summary():
    arm = {"macro_f1": 0.9, "macro_f1_ci95": [0.8, 0.95], "latency": {"median_ms": 6, "p95_ms": 10}}
    llm = {"macro_f1": 0.7, "macro_f1_ci95": [0.6, 0.8], "latency": {"median_ms": 1606, "p95_ms": 1900}}
    return {"arms": {"curricupath": arm, "handbook_rag": llm}}


_INTENT = {"intent_accuracy": {"correct": 85, "n": 100, "rate": 0.85, "ci95": [0.77, 0.91]},
           "by_category": {"eligibility": {"correct": 20, "n": 20, "rate": 1.0, "ci95": [0.84, 1.0]},
                           "ambiguous_module_name": {"correct": 0, "n": 10, "rate": 0.0, "ci95": [0.0, 0.28]}}}


def test_comparison_rows_state_why_each_published_figure_is_not_comparable() -> None:
    rows = bench.comparison_rows(_summary(), None, _INTENT, _published())
    by_dimension = {r[0]: r for r in rows}

    assert "no model call" in by_dimension["Response time"][1]
    assert "1.6 s" in by_dimension["Response time"][1]
    assert "B6: average query time 2.07" in by_dimension["Response time"][2]
    assert "so only the model-backed baselines" in by_dimension["Response time"][3]
    assert "not accuracy" in by_dimension["Decision quality"][3]


def test_intent_is_reported_with_the_weak_category_not_a_filtered_total() -> None:
    row = {r[0]: r for r in bench.comparison_rows(_summary(), None, _INTENT, _published())}["Intent understanding"]

    assert "85/100" in row[1]
    assert "0/10 on ambiguous module names" in row[1]
    assert "excluding" not in row[1]


def test_comparison_markdown_lists_unmeasured_benchmarks_and_the_caveat() -> None:
    text = bench.comparison_markdown(_summary(), None, _INTENT, _published(), "Configured for a pilot.")

    assert "not directly comparable" in text
    assert "Published figures with no measurement here yet" in text
    assert "| B5 R | faithfulness | 0.927 | 18 questions |" in text
    assert "Configured for a pilot." in text


def test_intent_category_figure_renders(tmp_path) -> None:
    pytest.importorskip("matplotlib")
    path = tmp_path / "categories.png"

    bench.render_intent_categories(_INTENT, path)

    assert path.stat().st_size > 5_000
