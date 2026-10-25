"""Regression tests for the clarification fixes found by the ambiguity sweep.

Each test states a defect observed in scripts/diagnose_clarification.py and pins the fix.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.advisor.module_resolution import _normalise_name, match_module_names
from app.config import get_settings
from app.data.repository import CsvCatalogueRepository


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


def _ask(client, message, session_id=None):
    return client.post("/advisor", json={"message": message, "programme_code": "EFA03",
                                          "session_id": session_id}).json()


def _modules():
    return CsvCatalogueRepository(get_settings().processed_data_directory).list_modules("EFA03")


# Fix 1: question words were not stripped, so "Who teaches signals?" matched nothing.
def test_question_words_are_stripped_before_module_lookup() -> None:
    assert _normalise_name("Who teaches signals?", remove_query_noise=True) == "signal"
    codes = {m.course_code for m in match_module_names("Who teaches signals?", _modules())}
    assert codes == {"ELEN2005A", "ELEN3012A", "ELEN3013A"}


# Fix 2: a name shared by several modules is a module lookup that offers the candidates.
@pytest.mark.parametrize("message", ["signals", "Tell me about signals", "What is Signals and Systems about?",
                                     "Who teaches signals?"])
def test_a_shared_module_name_asks_which_module_and_offers_candidates(client, message) -> None:
    response = _ask(client, message)

    assert response["status"] == "clarification_required"
    assert {m["course_code"] for m in response["module_matches"]} == {"ELEN2005A", "ELEN3012A", "ELEN3013A"}


def test_choosing_an_offered_candidate_answers_about_that_module(client) -> None:
    first = _ask(client, "Tell me about signals")
    final = _ask(client, "Signals and Systems IIA", first["session_id"])

    assert final["status"] == "ok" and final["module"]["course_code"] == "ELEN3012A"


# Fix 3: an exact full module name used to be refused as out of scope.
@pytest.mark.parametrize("message", ["Signals and Systems IIA", "Tell me about Electronics II",
                                     "What is Engineering Mathematics IB about?"])
def test_an_exact_module_name_is_answered_not_refused(client, message) -> None:
    response = _ask(client, message)

    assert response["status"] == "ok"
    assert response["intent"] == "module_information"


# Former cause 4: after the scope gate's "which feature?" question, a module-name reply was refused.
def test_a_module_name_reply_after_the_scope_question_is_answered(client) -> None:
    first = _ask(client, "Tell me about that module")
    final = _ask(client, "Electronics II", first["session_id"])

    assert first["status"] == "clarification_required"
    assert final["status"] == "ok" and final["module"]["course_code"] == "ELEN3002A"


# Guards found while applying the fixes.
def test_course_requests_use_wits_recommendations(client) -> None:
    for message in ("Find an online software course", "I want to learn software development online"):
        result = _ask(client, message)
        assert result["intent"] == "module_recommendations"
        assert not result.get("courses")
        assert "public_course_search" not in str(result)


def test_programme_questions_stay_programme_questions(client) -> None:
    assert _ask(client, "What is the Electrical Engineering degree?")["intent"] == "programme_information"


def test_prohibited_requests_stay_refused_even_when_they_name_a_module(client) -> None:
    response = _ask(client, "Predict my final marks in Control I")

    assert response["status"] == "out_of_scope"


def _ask_off(client, message):
    return client.post("/advisor", json={"message": message, "programme_code": "EFA03",
                                          "allow_clarification": False}).json()


# The no-clarification ablation must never ask a question; clarification is CurricuPath-only.
@pytest.mark.parametrize("message", ["signals", "Tell me about that module", "Who teaches signals?",
                                     "Tell me about a course"])
def test_with_clarification_disabled_the_advisor_never_asks(client, message) -> None:
    assert _ask_off(client, message)["status"] not in {"clarification_required", "needs_clarification"}


def test_with_clarification_disabled_a_shared_name_takes_the_best_candidate(client) -> None:
    response = _ask_off(client, "signals")

    assert response["status"] == "ok"
    assert response["module"]["course_code"] in {"ELEN2005A", "ELEN3012A", "ELEN3013A"}


def test_with_clarification_disabled_an_undeterminable_request_is_a_final_answer(client) -> None:
    response = _ask_off(client, "Tell me about that module")

    assert response["status"] == "unresolved_without_clarification"


def test_clarification_is_on_by_default(client) -> None:
    assert _ask(client, "signals")["status"] == "clarification_required"
