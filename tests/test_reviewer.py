"""Tests for bounded independent response review."""

from app.advisor.reviewer import ReviewCoordinator, ReviewResult


class FakeReviewer:
    model_name = "test-reviewer"

    def __init__(self, reviews):
        self.reviews = iter(reviews)

    def review(self, _message, _result):
        value = next(self.reviews)
        if isinstance(value, Exception):
            raise value
        return value


def _review(verdict, reason_codes=None):
    return ReviewResult(
        verdict=verdict,
        scope_consistent=True,
        query_answered=True,
        intent_consistent=True,
        facts_supported=True,
        decision_consistent=True,
        clarification_appropriate=True,
        reason_codes=reason_codes or [],
    )


def _result():
    return {
        "intent": "module_information",
        "status": "ok",
        "module": {"course_code": "ELEN2017A"},
        "answer": "ELEN2017A is Electric Circuits.",
        "conversation_context": {},
    }


def test_disabled_reviewer_preserves_result_and_records_local_checks() -> None:
    result = ReviewCoordinator().process("Tell me about ELEN2017A", _result())

    assert result["status"] == "ok"
    assert result["review"]["status"] == "not_run"
    assert result["review"]["invariants_passed"] is True


def test_approved_response_keeps_the_decision() -> None:
    coordinator = ReviewCoordinator(FakeReviewer([_review("approve")]))

    result = coordinator.process("Tell me about ELEN2017A", _result())

    assert result["module"]["course_code"] == "ELEN2017A"
    assert result["review"]["verdict"] == "approve"


def test_reviewer_failure_uses_deterministic_response() -> None:
    coordinator = ReviewCoordinator(FakeReviewer([RuntimeError("offline")]))

    result = coordinator.process("Tell me about ELEN2017A", _result())

    assert result["status"] == "ok"
    assert result["review"]["reason_codes"] == ["REVIEWER_UNAVAILABLE"]


def test_unrepairable_revision_returns_safe_response() -> None:
    coordinator = ReviewCoordinator(
        FakeReviewer([_review("revise", ["RESPONSE_DOES_NOT_ADDRESS_QUERY"])])
    )

    result = coordinator.process("Tell me about ELEN2017A", _result())

    assert result["status"] == "review_rejected"
    assert "could not verify" in result["answer"]


def test_one_supported_repair_must_pass_second_review() -> None:
    coordinator = ReviewCoordinator(
        FakeReviewer(
            [
                _review("revise", ["MISSING_SOURCE_QUALIFIER"]),
                _review("approve"),
            ]
        )
    )

    result = coordinator.process("Tell me about ELEN2017A", _result())

    assert result["status"] == "ok"
    assert "verified CurricuPath catalogue" in result["answer"]
    assert result["review"]["repair_count"] == 1
