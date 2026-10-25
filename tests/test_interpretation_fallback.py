"""Tests for the interpretation fallback (fuzzy tier and LLM tier), using fake providers."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.advisor.interpretation_fallback import (
    FuzzyCorrector,
    InterpretationFallback,
    LLMInterpretation,
    canonical_message,
    capped_fallback_mode,
    is_new_programme_question,
    needs_fallback,
)


class FakeProvider:
    def __init__(self, name, answer=None, error=None):
        self.name, self.answer, self.error, self.calls = name, answer, error, 0

    def interpret(self, message, modules):
        self.calls += 1
        if self.error:
            raise self.error
        return self.answer


class FakeService:
    class repository:
        @staticmethod
        def list_programmes():
            return [{"programme_code": "EFA03"}]

        @staticmethod
        def list_modules(code):
            return [{"course_code": "ELEN2021A", "course_name": "Microprocessors"},
                    {"course_code": "ELEN4006A", "course_name": "Measurement Systems"}]


def _resolves(text):
    return "ELEN" in text or "microprocessors" in text.lower() or "measurement" in text.lower()


def test_fuzzy_corrects_near_misses_against_catalogue_vocabulary_only() -> None:
    corrector = FuzzyCorrector(["Microprocessors", "Measurement Systems"])

    text, fixes = corrector.correct("cn u tell me abt microprocesors")

    assert fixes == {"microprocesors": "microprocessors"}
    assert text == "cn u tell me abt microprocessors"
    assert corrector.correct("What is the weather today")[1] == {}


def test_llm_answers_outside_the_catalogue_are_rejected() -> None:
    fallback = InterpretationFallback(FakeService, [FakeProvider("gemini", LLMInterpretation(
        module_code="ELEN9999A", intent="module_information"))])

    assert fallback.recover("the chip programming module", "EFA03", "llm", lambda t: False) is None


def test_quota_failure_hands_over_to_the_next_provider() -> None:
    gemini = FakeProvider("gemini", error=RuntimeError("429 RESOURCE_EXHAUSTED"))
    claude = FakeProvider("claude", LLMInterpretation(module_code="ELEN2021A", intent="module_information"))

    result = InterpretationFallback(FakeService, [gemini, claude]).recover(
        "the chip programming module", "EFA03", "llm", lambda t: False)

    assert result.provider == "claude" and result.message == "Tell me about ELEN2021A"
    assert gemini.calls == 1 and claude.calls == 1


def test_a_non_quota_error_does_not_try_another_provider() -> None:
    gemini = FakeProvider("gemini", error=ValueError("bad schema"))
    claude = FakeProvider("claude", LLMInterpretation(module_code="ELEN2021A", intent="module_information"))

    assert InterpretationFallback(FakeService, [gemini, claude]).recover(
        "x module", "EFA03", "llm", lambda t: False) is None
    assert claude.calls == 0


def test_fuzzy_mode_never_calls_a_model_and_off_does_nothing() -> None:
    provider = FakeProvider("gemini", LLMInterpretation(module_code="ELEN2021A", intent="module_information"))
    fallback = InterpretationFallback(FakeService, [provider])

    assert fallback.recover("the chip module", "EFA03", "fuzzy", _resolves) is None
    assert fallback.recover("microprocesors", "EFA03", "off", _resolves) is None
    assert fallback.recover("microprocesors", "EFA03", "fuzzy", _resolves).tier == "fuzzy"
    assert provider.calls == 0


def test_llm_mode_asks_the_model_before_fuzzy_and_can_name_a_programme() -> None:
    provider = FakeProvider("gemini", LLMInterpretation(programme_code="EFA04", intent="programme_information"))

    result = InterpretationFallback(FakeService, [provider]).recover(
        "tell me aboyt Information Enyineering", "EFA03", "llm", lambda t: True)

    assert result.tier == "llm" and result.message == "What is the EFA04 programme?"
    assert provider.calls == 1


def test_llm_programme_answers_outside_the_catalogue_are_rejected() -> None:
    provider = FakeProvider("gemini", LLMInterpretation(programme_code="EFA99", intent="programme_information"))

    assert InterpretationFallback(FakeService, [provider]).recover(
        "the robots degree", "EFA03", "llm", lambda t: False) is None


def test_llm_mode_uses_fuzzy_when_no_model_answers() -> None:
    gemini = FakeProvider("gemini", error=RuntimeError("429 RESOURCE_EXHAUSTED"))

    result = InterpretationFallback(FakeService, [gemini]).recover(
        "microprocesors", "EFA03", "llm", _resolves)

    assert result.tier == "fuzzy" and gemini.calls == 1


def test_a_request_can_lower_but_never_raise_the_server_mode() -> None:
    assert capped_fallback_mode("llm", "off") == "off"
    assert capped_fallback_mode("llm", "fuzzy") == "fuzzy"
    assert capped_fallback_mode("off", "llm") == "off"
    assert capped_fallback_mode("fuzzy", "llm") == "fuzzy"
    assert capped_fallback_mode(None, "llm") == "llm"
    assert capped_fallback_mode("llm", "bogus") == "off"


def test_needs_fallback_and_canonical_messages() -> None:
    assert needs_fallback("microprocesors", "unknown", None)
    assert needs_fallback("which module teaches circuit analysis", "public_course_search", None)
    assert not needs_fallback("Find an online course", "public_course_search", None)
    assert not needs_fallback("Tell me about ELEN2021A", "module_information", "ELEN2021A")
    assert canonical_message("eligibility", "ELEN2021A") == "Can I take ELEN2021A?"


def test_programme_name_in_a_longer_message_is_sent_to_the_fallback_but_a_bare_name_is_not() -> None:
    assert needs_fallback("Tell me aboyt Information Engineering", "module_information", None)
    assert not needs_fallback("information engineering", "module_information", None)
    assert not needs_fallback("Tell me about Information Engineering Design", "module_information", "ELEN4011A")
    assert not needs_fallback("Information Engineering Design", "module_information", None)
    assert not needs_fallback("What is the EFA04 programme?", "programme_information", None)


@pytest.fixture(scope="module")
def client():
    previous = os.environ.get("GEMINI_API_KEY")
    os.environ["GEMINI_API_KEY"] = ""
    from scripts.run_evaluation import _curricupath_components

    _, app = _curricupath_components()
    with TestClient(app) as test_client:
        yield test_client
    if previous is None:
        os.environ.pop("GEMINI_API_KEY", None)
    else:
        os.environ["GEMINI_API_KEY"] = previous


def _ask(client, message, mode):
    return client.post("/advisor", json={"message": message, "programme_code": "EFA03",
                                          "interpretation_fallback": mode}).json()


def test_fuzzy_tier_end_to_end_records_what_it_changed(client) -> None:
    response = _ask(client, "Microprocesors", "fuzzy")

    assert response["status"] == "ok" and response["module"]["course_code"] == "ELEN2021A"
    assert response["interpretation_fallback"]["corrections"] == {"Microprocesors": "microprocessors"}


def test_fallback_off_leaves_the_old_behaviour(client) -> None:
    response = _ask(client, "Microprocesors", "off")

    assert response["status"] == "out_of_scope" and "interpretation_fallback" not in response


def test_prohibited_requests_are_never_reinterpreted(client) -> None:
    response = _ask(client, "Predict my marks for Contrl I", "fuzzy")

    assert response["status"] == "out_of_scope" and "interpretation_fallback" not in response


def test_a_pending_clarification_is_only_interrupted_by_a_new_programme_question() -> None:
    assert is_new_programme_question("Tell me aboyt Information Engineering", "module_information", None)
    assert not is_new_programme_question("information engineering", "module_information", None)
    assert not is_new_programme_question("the design one", "module_information", None)
    assert not is_new_programme_question("ELEN4011A", "module_information", "ELEN4011A")
