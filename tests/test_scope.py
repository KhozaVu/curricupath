"""Tests for the deterministic CurricuPath scope boundary."""

from app.advisor.intent import DeterministicIntentExtractor
from app.advisor.scope import classify_scope


def _scope(text: str, *, active_context: bool = False):
    parsed = DeterministicIntentExtractor(()).extract(text)
    return classify_scope(text, parsed, has_active_context=active_context)


def test_known_advisor_intent_is_supported() -> None:
    decision = _scope("Can I take ELEN4001A in EFA03?")

    assert decision.status == "supported"
    assert decision.intent == "eligibility"


def test_unknown_curriculum_wording_requests_clarification() -> None:
    decision = _scope("I need some module guidance")

    assert decision.status == "ambiguous"
    assert decision.clarification_question is not None


def test_mark_prediction_is_out_of_scope_even_with_engineering_wording() -> None:
    decision = _scope("Predict my final engineering marks")

    assert decision.status == "out_of_scope"
    assert decision.reason_codes == ["UNSUPPORTED_USER_REQUEST"]


def test_active_clarification_context_accepts_short_follow_up() -> None:
    decision = _scope("Heavy workload", active_context=True)

    assert decision.status == "supported"
    assert decision.reason_codes == ["SUPPORTED_CLARIFICATION_CONTEXT"]
