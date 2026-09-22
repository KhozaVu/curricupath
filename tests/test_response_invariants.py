"""Tests for deterministic response consistency checks."""

from app.advisor.response_invariants import decision_fingerprint, validate_response


def test_consistent_eligibility_response_passes() -> None:
    result = {
        "intent": "eligibility",
        "status": "not_eligible",
        "eligible": False,
        "course_code": "ELEN4001A",
        "answer": "ELEN4001A is not currently eligible.",
    }

    assert validate_response(result).passed is True


def test_eligibility_contradiction_is_rejected() -> None:
    result = {
        "intent": "eligibility",
        "status": "not_eligible",
        "eligible": False,
        "course_code": "ELEN4001A",
        "answer": "ELEN4001A is eligible for this profile.",
    }

    report = validate_response(result)

    assert report.passed is False
    assert "DECISION_TEXT_CONTRADICTION" in report.reason_codes


def test_presentation_changes_do_not_change_decision_fingerprint() -> None:
    original = {"status": "ok", "eligible": True, "answer": "First wording"}
    revised = {"status": "ok", "eligible": True, "answer": "Second wording"}

    assert decision_fingerprint(original) == decision_fingerprint(revised)


def test_unknown_identifier_in_answer_is_rejected() -> None:
    report = validate_response(
        {
            "intent": "module_information",
            "status": "ok",
            "module": {"course_code": "ELEN2017A"},
            "answer": "You should take ELEN9999A.",
        }
    )

    assert report.passed is False
    assert "UNSUPPORTED_IDENTIFIER_IN_RESPONSE" in report.reason_codes


def test_clarification_question_may_have_grounded_explanation() -> None:
    report = validate_response(
        {
            "intent": "eligibility",
            "status": "clarification_required",
            "course_code": "MATH1049A",
            "unresolved_predicates": ["MATH1048A"],
            "clarification_question": "Have you completed MATH1048A?",
            "answer": (
                "I need one more fact before deciding. "
                "Have you completed MATH1048A?"
            ),
        }
    )

    assert report.passed is True


def test_clarification_response_must_include_its_question() -> None:
    report = validate_response(
        {
            "intent": "eligibility",
            "status": "clarification_required",
            "course_code": "MATH1049A",
            "unresolved_predicates": ["MATH1048A"],
            "clarification_question": "Have you completed MATH1048A?",
            "answer": "Please provide more information.",
        }
    )

    assert report.passed is False
    assert "INVALID_CLARIFICATION_RESPONSE" in report.reason_codes
