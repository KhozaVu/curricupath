"""Tests for the Experiment C runner protocol and scoring, using hand-built fixtures."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from app.evaluation import ambiguity_runner as runner
from app.evaluation import ambiguity_scoring as scoring

ASK = {"status": "clarification_required", "intent": "module_information", "session_id": "s1"}
OK = {"status": "ok", "intent": "module_information", "module": {"course_code": "ELEN3012A"}, "session_id": "s1"}
WRONG = {"status": "ok", "intent": "module_information", "module": {"course_code": "ELEN9999A"}}
OUT = {"status": "out_of_scope", "intent": "unknown"}
ACCEPT = json.dumps([{"intent": "module_information", "module_code": "ELEN3012A"}])


def _case(case_id="A1", **overrides):
    case = {"case_id": case_id, "query": "signals", "intended_interpretation": "module_information",
            "required_clarification": "true", "fixed_simulated_reply": "the analogue one",
            "neutral_fallback_reply": "I do not know", "accepted_final_outcomes_json": ACCEPT,
            "approval_state": "approved"}
    return {**case, **overrides}


def _sender(*responses):
    calls, remaining = [], iter(responses)

    def send(message, session_id):
        calls.append((message, session_id))
        return next(remaining)

    return send, calls


def test_a_clarification_is_answered_once_with_the_fixed_reply() -> None:
    send, calls = _sender(ASK, OK)

    record = runner.run_case(send, _case(), allow_clarification=True)

    assert calls == [("signals", None), ("the analogue one", "s1")]
    assert record["n_turns"] == 2 and record["final"]["status"] == "ok" and record["error"] is None


def test_a_second_question_gets_the_neutral_reply_once_then_stays_unresolved() -> None:
    send, calls = _sender(ASK, ASK, ASK)

    record = runner.run_case(send, _case(), allow_clarification=True)

    assert [m for m, _ in calls] == ["signals", "the analogue one", "I do not know"]
    assert record["n_turns"] == 3 and runner.is_clarification(record["final"])
    assert record["error"] is None


def test_the_ablation_never_replies() -> None:
    send, calls = _sender(ASK)

    record = runner.run_case(send, _case(), allow_clarification=False)

    assert len(calls) == 1 and record["n_turns"] == 1


def test_an_answered_first_turn_gets_no_reply() -> None:
    send, calls = _sender(OK)

    runner.run_case(send, _case(), allow_clarification=True)

    assert len(calls) == 1


def test_a_pending_reply_is_never_improvised() -> None:
    send, calls = _sender(ASK)

    record = runner.run_case(send, _case(fixed_simulated_reply=runner.PENDING), allow_clarification=True)

    assert len(calls) == 1 and record["unscripted"] is True and record["n_turns"] == 1


def test_a_failing_advisor_is_recorded_not_raised() -> None:
    def send(message, session_id):
        raise RuntimeError("boom")

    record = runner.run_case(send, _case(), allow_clarification=True)

    assert record["error"] == "RuntimeError: boom" and record["n_turns"] == 0


def _record(case_id, first, final=None, n_turns=None):
    turns = [{"message": "q", "response": first}]
    if final is not None:
        turns.append({"message": "r", "response": final})
    return {"case_id": case_id, "turns": turns, "final": final or first,
            "n_turns": n_turns or len(turns), "error": None}


def test_metrics_match_a_hand_calculation() -> None:
    cases = [_case("C1"), _case("C2"), _case("C3", required_clarification="false"),
             _case("C4", required_clarification="false")]
    records = [_record("C1", ASK, OK), _record("C2", WRONG), _record("C3", ASK, OK), _record("C4", OK)]

    m = scoring.score_arm(cases, records)

    assert m["appropriate_clarification_rate"]["rate"] == 0.5
    assert m["unnecessary_clarification_rate"]["rate"] == 0.5
    assert m["silent_guess_rate"]["rate"] == 0.5
    assert m["final_outcome_accepted"]["rate"] == 0.75
    assert m["second_attempt_success"]["correct"] == 2 and m["second_attempt_success"]["n"] == 2
    assert m["mean_turns_to_resolution"] == pytest.approx(1.5)
    assert m["unresolved_clarification_rate"]["correct"] == 0


def test_reviewer_dependent_metrics_are_not_scorable_when_fields_are_pending() -> None:
    pending = _case(required_clarification=runner.PENDING, accepted_final_outcomes_json="[]")

    m = scoring.score_arm([pending], [_record("A1", OUT)])

    assert m["initial_intent_accuracy"]["rate"] == 0
    assert m["refused_out_of_scope_first_turn"]["rate"] == 1
    for name in ("appropriate_clarification_rate", "silent_guess_rate", "final_outcome_accepted"):
        assert m[name]["rate"] is None and "reviewer" in m[name]["not_scorable"]


def test_accepted_outcomes_reject_unknown_keys_and_ignore_case() -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        scoring.parse_accepted(_case(accepted_final_outcomes_json='[{"colour": "red"}]'))
    assert scoring.outcome_matches(OK, {"module_code": "elen3012a"})
    assert not scoring.outcome_matches(OK, {"module_code": "ELEN1111A"})


def test_exact_sign_test_matches_hand_values() -> None:
    assert scoring.exact_sign_test(0, 0) == 1.0
    assert scoring.exact_sign_test(5, 0) == pytest.approx(2 / 32)
    assert scoring.exact_sign_test(3, 1) == pytest.approx(10 / 16)


def test_paired_comparison_counts_only_discordant_pairs() -> None:
    cases = [_case("C1"), _case("C2"), _case("C3")]
    full = [_record("C1", ASK, OK), _record("C2", ASK, OK), _record("C3", OK)]
    ablation = [_record("C1", ASK), _record("C2", ASK), _record("C3", OK)]

    result = scoring.paired_comparison(cases, full, ablation)["final_outcome_accepted"]

    assert result["only_with_clarification"] == 2 and result["only_without_clarification"] == 0
    assert result["both_correct"] == 1 and result["exact_sign_test_p"] == pytest.approx(0.5)


def test_official_run_is_gated_on_reviewer_fields() -> None:
    cases_path = Path(__file__).resolve().parents[1] / "experiments" / "evaluation" / "v2_5" / "ambiguity_cases.csv"
    with cases_path.open(newline="", encoding="utf-8") as handle:
        real = list(csv.DictReader(handle))

    problems = runner.case_errors(real)

    assert {p.split(":")[0] for p in problems} == {c["case_id"] for c in real}
    assert runner.case_errors([_case()]) == []
    assert any("fixed simulated reply" in p for p in runner.case_errors([_case(fixed_simulated_reply="")]))


def test_a_response_that_is_still_asking_never_counts_as_correct_advice() -> None:
    assert not scoring.outcome_matches(ASK, {"intent": "module_information"})
    assert not scoring.outcome_matches(OUT, {"intent": "unknown"})
    assert scoring.outcome_matches(OUT, {"intent": "unknown", "status": "out_of_scope"})
    assert scoring.outcome_matches(OK, {"intent": "module_information"})
