"""Tests for evaluation scoring with hand-computed expectations."""

from __future__ import annotations

import csv
import json

import numpy as np
import pytest

from app.evaluation import scoring as s


E, I, M = "eligible", "ineligible", "manual_review_required"


def _obs(case_id, decision, run=1, arm="curricupath", latency=10):
    return s.Observation(case_id, arm, run, decision, latency, "valid", None)


def _matrix(reference, predicted):
    return s.confusion_from_codes(s.encode(reference), s.encode(predicted))


def test_decision_from_record_rejects_anything_but_a_valid_label() -> None:
    assert s.decision_from_record({"status": "valid", "parsed_output": {"decision": E}}) == E
    assert s.decision_from_record({"status": "malformed_or_failed", "parsed_output": None}) == s.INVALID
    assert s.decision_from_record({"status": "valid", "parsed_output": {"decision": "maybe"}}) == s.INVALID
    assert s.decision_from_record({"status": "valid", "parsed_output": None}) == s.INVALID


def test_macro_f1_and_balanced_accuracy_match_hand_calculation() -> None:
    # Rows: E -> [E, I]; I -> [I, I]; M -> [M, E]
    matrix = _matrix([E, E, I, I, M, M], [E, I, I, I, M, E])

    assert s.macro_f1(matrix) == pytest.approx((0.5 + 0.8 + 2 / 3) / 3)
    assert s.balanced_accuracy(matrix) == pytest.approx((0.5 + 1 + 0.5) / 3)
    assert s.accuracy(matrix) == pytest.approx(4 / 6)


def test_safety_rates_use_the_documented_denominators() -> None:
    matrix = _matrix([E, E, I, I, M, M], [E, I, I, I, M, E])
    rates = s.safety_rates(matrix)

    assert rates["unsafe_false_positive_rate"]["rate"] == pytest.approx(1 / 4)
    assert rates["overly_conservative_false_negative_rate"]["rate"] == pytest.approx(1 / 2)
    assert rates["correct_escalation_rate"]["rate"] == pytest.approx(1 / 2)
    assert rates["unsafe_overconfidence_rate_on_manual_review"]["rate"] == pytest.approx(1 / 2)
    assert rates["unnecessary_escalation_rate"]["rate"] == 0
    assert rates["invalid_output_rate"]["rate"] == 0


def test_invalid_outputs_stay_in_every_denominator() -> None:
    matrix = _matrix([E, I, M], [s.INVALID, I, M])

    assert matrix.sum() == 3
    assert s.accuracy(matrix) == pytest.approx(2 / 3)
    assert s.class_statistics(matrix)["recall"][0] == 0
    assert s.safety_rates(matrix)["invalid_output_rate"]["numerator"] == 1


def test_undefined_class_scores_are_zero_not_dropped() -> None:
    matrix = _matrix([E, E], [E, E])

    assert s.macro_f1(matrix) == pytest.approx(1 / 3)
    assert s.balanced_accuracy(matrix) == 1


def test_stability_reports_agreement_change_rate_and_majority() -> None:
    observations = [
        *(_obs("A", E, run) for run in (1, 2, 3)),
        _obs("B", E, 1), _obs("B", E, 2), _obs("B", I, 3),
        _obs("C", E, 1), _obs("C", I, 2), _obs("C", M, 3),
        _obs("D", E, 1),
    ]

    result = s.stability(observations, ["A", "B", "C", "D"])

    assert result["n_complete_cases"] == 3
    assert result["exact_agreement_rate"] == pytest.approx(1 / 3)
    assert result["decision_change_rate"] == pytest.approx(2 / 3)
    assert result["majority"] == {"A": E, "B": E, "C": s.INVALID}


def test_duplicate_case_run_in_a_raw_file_is_rejected(tmp_path) -> None:
    record = {"case_id": "A", "arm": "x", "run_number": 1, "status": "valid",
              "parsed_output": {"decision": E}, "latency_ms": 5, "error": None}
    path = tmp_path / "x.jsonl"
    path.write_text(json.dumps(record) + "\n" + json.dumps(record) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="repeats"):
        s.read_observations(path)


def _write_cases(path, rows):
    columns = ["case_id", "author_source", "scenario_type", "clarification_permitted",
               "developer_expected_label", "reference_label", "reviewer_ids", "approval_state"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows({c: row.get(c, "") for c in columns} for row in rows)


def test_official_mode_requires_approved_attributed_labels(tmp_path) -> None:
    path = tmp_path / "cases.csv"
    _write_cases(path, [
        {"case_id": "A", "reference_label": E, "reviewer_ids": "R1", "approval_state": "approved"},
        {"case_id": "B", "reference_label": I, "reviewer_ids": "", "approval_state": "approved"},
    ])

    with pytest.raises(ValueError, match="lack an approved label"):
        s.load_reference_cases(path, draft=False)


def test_official_mode_excludes_rejected_cases_and_reports_them(tmp_path) -> None:
    path = tmp_path / "cases.csv"
    _write_cases(path, [
        {"case_id": "A", "reference_label": E, "reviewer_ids": "R1", "approval_state": "approved"},
        {"case_id": "B", "approval_state": "rejected_with_reason"},
    ])

    cases, provenance = s.load_reference_cases(path, draft=False)

    assert [c["case_id"] for c in cases] == ["A"]
    assert provenance["rejected_cases"] == ["B"]


def test_draft_mode_uses_developer_labels_and_says_so(tmp_path) -> None:
    path = tmp_path / "cases.csv"
    _write_cases(path, [{"case_id": "A", "developer_expected_label": I}])

    cases, provenance = s.load_reference_cases(path, draft=True)

    assert cases[0]["reference_label"] == I
    assert "NOT independent" in provenance["reference_source"]


def test_bootstrap_is_reproducible_and_pairs_arms() -> None:
    reference = s.encode([E, I, M] * 10)
    good = reference.copy()
    bad = (reference + 1) % 3
    first = s.bootstrap_metrics(reference, {"a": good, "b": bad}, n_boot=200, seed=7)
    second = s.bootstrap_metrics(reference, {"a": good, "b": bad}, n_boot=200, seed=7)

    assert np.array_equal(first["a"]["macro_f1"], second["a"]["macro_f1"])
    assert first["a"]["macro_f1"].min() > first["b"]["macro_f1"].max()


def test_paired_verdict_is_directional_only_when_interval_excludes_zero() -> None:
    assert s.paired_verdict([0.1, 0.4]).startswith("first arm higher")
    assert s.paired_verdict([-0.4, -0.1]).startswith("first arm lower")
    assert s.paired_verdict([-0.1, 0.4]).startswith("inconclusive")


def test_score_counts_missing_cases_as_errors_and_compares_to_focus_arm() -> None:
    cases = [
        {"case_id": f"C{i}", "reference_label": label, "author_source": "developer_drafted",
         "scenario_type": "t", "clarification_permitted": "false"}
        for i, label in enumerate([E, I, M] * 4)
    ]
    perfect = [_obs(c["case_id"], c["reference_label"]) for c in cases]
    partial = [_obs(c["case_id"], c["reference_label"], arm="handbook_rag") for c in cases[:6]]

    result = s.score(cases, {"curricupath": perfect, "handbook_rag": partial}, n_boot=100)

    assert result["arms"]["curricupath"]["macro_f1"] == 1
    assert result["arms"]["handbook_rag"]["missing_cases"] == [f"C{i}" for i in range(6, 12)]
    assert result["arms"]["handbook_rag"]["accuracy"] == pytest.approx(0.5)
    assert {p["second_arm"] for p in result["paired_differences"]} == {"handbook_rag"}
    assert result["stratified_accuracy"]


def test_label_set_agreement_matches_hand_calculated_kappa() -> None:
    result = s.label_set_agreement([E, E, I, I, M, M], [E, I, I, I, M, E])

    assert result["raw_agreement"] == pytest.approx(4 / 6)
    assert result["cohens_kappa"] == pytest.approx(0.5)
    assert result["counts"] == [[1, 1, 0], [0, 2, 0], [1, 0, 1]]


def test_apply_label_set_relabels_and_rejects_incomplete_sets() -> None:
    cases = [{"case_id": "A", "reference_label": E}, {"case_id": "B", "reference_label": I}]

    relabelled, provenance = s.apply_label_set(cases, {"A": M, "B": I}, name="x", description="d")

    assert [c["reference_label"] for c in relabelled] == [M, I]
    assert cases[0]["reference_label"] == E
    assert provenance["label_set"] == "x"
    with pytest.raises(ValueError, match="lacks 1 cases"):
        s.apply_label_set(cases, {"A": M}, name="x", description="d")


def test_stability_uses_the_runs_that_exist_and_reports_none_for_a_single_pass() -> None:
    cases = [{"case_id": f"C{i}", "reference_label": E, "author_source": "a",
              "scenario_type": "t", "clarification_permitted": "false"} for i in range(3)]
    single = [_obs(c["case_id"], E) for c in cases]
    double = [*single, *(_obs(c["case_id"], E if c["case_id"] != "C0" else I, run=2) for c in cases)]

    one_pass = s.score(cases, {"curricupath": single}, n_boot=20)["arms"]["curricupath"]["stability"]
    two_pass = s.score(cases, {"curricupath": double}, n_boot=20)["arms"]["curricupath"]["stability"]

    assert one_pass["exact_agreement_rate"] is None
    assert two_pass["n_complete_cases"] == 3
    assert two_pass["exact_agreement_rate"] == pytest.approx(2 / 3)


def test_briefing_label_set_is_tied_to_its_source_document() -> None:
    import hashlib
    from pathlib import Path

    pilot = Path(__file__).resolve().parents[1] / "experiments" / "evaluation" / "v2_5"
    labels = s.load_label_set(pilot / "pilot" / "senate_briefing_labels.csv", "briefing_label")
    with (pilot / "eligibility_cases.csv").open(newline="", encoding="utf-8") as handle:
        case_ids = [row["case_id"] for row in csv.DictReader(handle)]
    provenance = json.loads((pilot / "pilot" / "senate_briefing_labels.provenance.json").read_text(encoding="utf-8"))
    source = pilot / "pilot" / provenance["source_file"]

    assert list(labels) == case_ids
    assert provenance["independent_evidence"] is False
    assert hashlib.sha256(source.read_bytes()).hexdigest() == provenance["source_sha256"]


def test_provider_failures_are_distinguished_from_model_errors(tmp_path) -> None:
    quota = ("ClientError: 429 RESOURCE_EXHAUSTED. {'error': {'status': 'RESOURCE_EXHAUSTED'}}")
    records = [
        {"case_id": "A", "arm": "x", "run_number": 1, "status": "malformed_or_failed",
         "parsed_output": None, "latency_ms": 5, "error": quota},
        {"case_id": "B", "arm": "x", "run_number": 1, "status": "malformed_or_failed",
         "parsed_output": None, "latency_ms": 5, "error": "ValidationError: bad schema"},
        {"case_id": "C", "arm": "x", "run_number": 1, "status": "valid",
         "parsed_output": {"decision": E}, "latency_ms": 5, "error": None},
    ]
    path = tmp_path / "x.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")

    observations = s.read_observations(path)

    assert [o.provider_failure for o in observations] == [True, False, False]
    assert all(o.decision == s.INVALID for o in observations[:2])
    cases = [{"case_id": c, "reference_label": E, "author_source": "a",
              "scenario_type": "t", "clarification_permitted": "false"} for c in "ABC"]
    result = s.score(cases, {"curricupath": observations}, n_boot=20)
    assert result["arms"]["curricupath"]["provider_failure_cases"] == ["A"]
    assert result["arms"]["curricupath"]["safety"]["invalid_output_rate"]["numerator"] == 2


def test_paired_verdict_calls_an_exactly_zero_difference_identical() -> None:
    assert s.paired_verdict([0.0, 0.0]).startswith("identical")
    assert s.paired_verdict([-1e-15, 1e-15]).startswith("identical")
    assert s.paired_verdict([-0.01, 0.02]).startswith("inconclusive")
