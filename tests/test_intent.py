"""Tests for the boundary between Gemini extraction and trusted app state."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.data.repository import CsvCatalogueRepository
from app.advisor.intent import (
    DeterministicIntentExtractor,
    GeminiIntentExtractor,
    ParsedAdvisorRequest,
)
from app.advisor.normalisation import Alias


PROCESSED_DATA = Path(__file__).resolve().parents[1] / "data" / "processed"


class _Models:
    def __init__(self, parsed: ParsedAdvisorRequest) -> None:
        self._parsed = parsed

    def generate_content(self, **_kwargs) -> SimpleNamespace:
        return SimpleNamespace(parsed=self._parsed)


class _UnavailableModels:
    def __init__(self) -> None:
        self.calls = 0

    def generate_content(self, **_kwargs) -> None:
        self.calls += 1
        raise RuntimeError("provider unavailable")


def test_deterministic_extractor_understands_ordinal_year_and_electives() -> None:
    result = DeterministicIntentExtractor(()).extract(
        "show 4th year electives for efa04"
    )

    assert result.intent == "curriculum_list"
    assert result.programme_code == "EFA04"
    assert result.year_of_study == 4
    assert result.requirement_type == "elective_pool"


def test_deterministic_extractor_understands_spelled_year_and_compulsory() -> None:
    result = DeterministicIntentExtractor(()).extract(
        "show fourth year compulsory modules for EFA04"
    )

    assert result.year_of_study == 4
    assert result.requirement_type == "compulsory"


def test_programme_interest_course_request_means_fourth_year_electives() -> None:
    aliases = (Alias("machine learning", "machine_learning", "interest"),)

    result = DeterministicIntentExtractor(aliases).extract(
        "Suggest EFA04 courses for machine learning"
    )

    assert result.intent == "module_recommendations"
    assert result.year_of_study == 4
    assert result.requirement_type == "elective_pool"


def test_interest_elective_question_is_not_single_module_eligibility() -> None:
    aliases = (Alias("machine learning", "machine_learning", "interest"),)

    result = DeterministicIntentExtractor(aliases).extract(
        "What electives can I take if I'm interested in machine learning?"
    )

    assert result.intent == "eligible_modules"
    assert result.module_code is None
    assert result.requirement_type == "elective_pool"
    assert result.interests == ["machine_learning"]


def test_explicit_module_can_i_take_remains_eligibility() -> None:
    aliases = (Alias("machine learning", "machine_learning", "interest"),)

    result = DeterministicIntentExtractor(aliases).extract(
        "Can I take ELEN4025A for machine learning?"
    )

    assert result.intent == "eligibility"
    assert result.module_code == "ELEN4025A"


def test_my_courses_selects_profile_course_summary() -> None:
    extractor = DeterministicIntentExtractor(())

    assert extractor.extract("Tell me about my courses").intent == "profile_courses"
    assert extractor.extract("What modules am I currently taking?").intent == "profile_courses"


def test_programme_names_select_the_matching_curriculum() -> None:
    extractor = DeterministicIntentExtractor(())

    information = extractor.extract("Tell me about Information Engineering courses")
    electrical = extractor.extract("Show me the Electrical Engineering curriculum")

    assert information.intent == "curriculum_list"
    assert information.programme_code == "EFA04"
    assert electrical.intent == "curriculum_list"
    assert electrical.programme_code == "EFA03"


def test_explicit_public_course_wording_is_not_a_programme_curriculum_request() -> None:
    aliases = (Alias("electrical engineering", "electrical_engineering", "career"),)

    result = DeterministicIntentExtractor(aliases).extract(
        "Find a public course for electrical engineering"
    )

    assert result.intent == "module_recommendations"


def test_degree_and_career_questions_select_programme_information() -> None:
    extractor = DeterministicIntentExtractor(())

    electrical = extractor.extract("What is Electrical Engineering?")
    information = extractor.extract(
        "What are the career opportunities for Information Engineering?"
    )

    assert electrical.intent == "programme_information"
    assert electrical.programme_code == "EFA03"
    assert information.intent == "programme_information"
    assert information.programme_code == "EFA04"


def test_credit_question_for_named_degree_selects_credit_information() -> None:
    result = DeterministicIntentExtractor(()).extract(
        "How many credits does Electrical Engineering have?"
    )

    assert result.intent == "credit_information"
    assert result.programme_code == "EFA03"


def test_credit_and_year_question_for_a_module_select_module_information() -> None:
    extractor = DeterministicIntentExtractor(())

    assert extractor.extract("How many credits is ELEN2017A?").intent == "module_information"
    assert extractor.extract("What year is Electric Circuits taken?").intent == "module_information"


def test_degree_choice_question_selects_programme_comparison() -> None:
    aliases = (
        Alias("optical wireless communication", "communications", "interest"),
    )

    result = DeterministicIntentExtractor(aliases).extract(
        "I'm in 2nd year and I like optical wireless communication. Should I choose "
        "Electrical Engineering or Information Engineering?"
    )

    assert result.intent == "programme_comparison"
    assert result.year_of_study == 2
    assert result.interests == ["communications"]


def test_course_information_language_selects_module_information_intent() -> None:
    extractor = DeterministicIntentExtractor(())

    assert extractor.extract("course info").intent == "module_information"
    assert extractor.extract("Who teaches Control I?").intent == "module_information"
    assert extractor.extract("What content is covered in Electronics II?").intent == "module_information"


def test_course_preference_language_extracts_workload_and_difficulty() -> None:
    extractor = DeterministicIntentExtractor(())

    assert extractor.extract("low workload and easy").workload_preference == "light"
    assert extractor.extract("low workload and easy").difficulty_preference == "beginner"
    assert extractor.extract("intensive and advanced").workload_preference == "heavy"
    assert extractor.extract("intensive and advanced").difficulty_preference == "intermediate"


def test_gemini_output_is_limited_to_explicit_codes_and_controlled_tags() -> None:
    aliases = (
        Alias("electric circuits", "electric_circuits", "interest"),
        Alias("electrical engineering", "electrical_engineering", "career"),
    )
    fallback = DeterministicIntentExtractor(aliases)
    extractor = GeminiIntentExtractor.__new__(GeminiIntentExtractor)
    extractor._client = SimpleNamespace(
        models=_Models(
            ParsedAdvisorRequest(
                intent="module_recommendations",
                module_code="FAKE9999A",
                programme_code="EFA04",
                interests=["electric circuits", "invented_topic"],
                career_preferences=["electrical engineering", "invented_career"],
                completed_modules=["FAKE9999A"],
            )
        )
    )
    extractor._model = "test-model"
    extractor._fallback = fallback
    extractor._allowed_interests = frozenset({"electric_circuits"})
    extractor._allowed_careers = frozenset({"electrical_engineering"})
    extractor._retry_after = 0.0

    result = extractor.extract(
        "I want electric circuits for an electrical engineering career"
    )

    assert result.module_code is None
    assert result.programme_code is None
    assert result.interests == ["electric_circuits"]
    assert result.career_preferences == ["electrical_engineering"]
    assert result.completed_modules == []


def test_gemini_failure_opens_circuit_breaker_and_uses_fallback() -> None:
    fallback = DeterministicIntentExtractor(())
    models = _UnavailableModels()
    extractor = GeminiIntentExtractor.__new__(GeminiIntentExtractor)
    extractor._client = SimpleNamespace(models=models)
    extractor._model = "test-model"
    extractor._fallback = fallback
    extractor._allowed_interests = frozenset()
    extractor._allowed_careers = frozenset()
    extractor._retry_after = 0.0

    first = extractor.extract("module eligibility")
    second = extractor.extract("module eligibility")

    assert first.intent == "eligibility"
    assert second.intent == "eligibility"
    assert models.calls == 1


@pytest.mark.parametrize(
    "message",
    [
        "Am I allowed to register for Control II?",
        "Is Network Fundamentals open to me?",
        "Can I sign up for ELEN4017A?",
        "Can I enrol in Microprocessors next semester?",
        "I study Electrical Engineering. Can I do Control II this year?",
        "I want to take Renewable Energy, is that ok?",
    ],
)
def test_registration_and_permission_wording_is_an_eligibility_question(message) -> None:
    extractor = DeterministicIntentExtractor(CsvCatalogueRepository(PROCESSED_DATA).get_aliases())

    assert extractor.extract(message).intent == "eligibility"


@pytest.mark.parametrize(
    "message",
    ["Can I do anything about my marks?", "Can I do better in Control II?", "Who teaches ELEN4016A?"],
)
def test_permission_regex_does_not_capture_other_questions(message) -> None:
    extractor = DeterministicIntentExtractor(CsvCatalogueRepository(PROCESSED_DATA).get_aliases())

    assert extractor.extract(message).intent != "eligibility"


def test_gemini_intent_extractor_uses_a_deadline_the_api_accepts() -> None:
    from app.advisor.intent import MIN_REQUEST_TIMEOUT_MS

    assert MIN_REQUEST_TIMEOUT_MS >= 10_000  # the API rejects shorter client deadlines


def test_gemini_failure_warns_once_and_falls_back_to_the_offline_parser() -> None:
    import warnings

    class _Boom:
        class models:
            @staticmethod
            def generate_content(**_kwargs):
                raise RuntimeError("deadline too short")

    offline = DeterministicIntentExtractor(())
    extractor = GeminiIntentExtractor.__new__(GeminiIntentExtractor)
    extractor._client = _Boom()
    extractor._model, extractor._fallback = "m", offline
    extractor._allowed_interests = extractor._allowed_careers = frozenset()
    extractor._retry_after, extractor._warned = 0.0, False

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = extractor.extract("Can I take ELEN3013A?")

    assert result.intent == "eligibility"
    assert any("Gemini intent extraction failed" in str(w.message) for w in caught)


def test_extractor_source_is_recorded_for_success_and_for_fallback() -> None:
    from app.advisor.intent import EXTRACTOR_SOURCE

    class _Fails:
        class models:
            @staticmethod
            def generate_content(**_kwargs):
                raise RuntimeError("503 unavailable")

    class _Works:
        class models:
            @staticmethod
            def generate_content(**_kwargs):
                return SimpleNamespace(parsed=ParsedAdvisorRequest(intent="eligibility"))

    def build(client):
        extractor = GeminiIntentExtractor.__new__(GeminiIntentExtractor)
        extractor._client, extractor._model = client, "m"
        extractor._fallback = DeterministicIntentExtractor(())
        extractor._allowed_interests = extractor._allowed_careers = frozenset()
        extractor._retry_after, extractor._warned = 0.0, False
        return extractor

    EXTRACTOR_SOURCE.set(None)
    build(_Works()).extract("Can I take ELEN3013A?")
    assert EXTRACTOR_SOURCE.get() == "gemini"

    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        build(_Fails()).extract("Can I take ELEN3013A?")
    assert EXTRACTOR_SOURCE.get() == "offline"


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("can I take ELEN4012 having failed ELEN3009?", ["ELEN3009A"]),
        ("I failed ELEN3009A and ELEN3012", ["ELEN3009A", "ELEN3012A"]),
        ("ELEN3009 (failed), can I take ELEN4012A?", ["ELEN3009A"]),
        ("not completed ELEN3000A, MATH3025A", ["ELEN3000A", "MATH3025A"]),
        ("I passed ELEN3009A", []),
        ("Can I take ELEN4012A?", []),
    ],
)
def test_failed_or_not_completed_modules_are_read_from_the_message(message, expected) -> None:
    from app.advisor.intent import extract_not_completed_modules

    assert extract_not_completed_modules(message) == expected


@pytest.mark.parametrize(
    ("message", "target", "completed", "current", "planned", "failed"),
    [
        ("I failed ELEN3009A and ELEN3012. Can I take ELEN4011A?", "ELEN4011A", [], [], [], ["ELEN3009A", "ELEN3012A"]),
        ("I have completed ELEN3009A. Can I take ELEN4012A?", "ELEN4012A", ["ELEN3009A"], [], [], []),
        ("Can I take ELEN4012A? I completed ELEN3009A", "ELEN4012A", ["ELEN3009A"], [], [], []),
        ("I am currently taking ELEN3012A, can I take ELEN3013A?", "ELEN3013A", [], ["ELEN3012A"], [], []),
        ("I plan to take ELEN3012A. Can I take ELEN3013A?", "ELEN3013A", [], [], ["ELEN3012A"], []),
        ("I have not completed ELEN3009A, can I take ELEN4012A?", "ELEN4012A", [], [], [], ["ELEN3009A"]),
        ("Can I take ELEN3013A?", "ELEN3013A", [], [], [], []),
    ],
)
def test_declared_statuses_are_read_and_the_target_is_the_module_being_asked_about(
    message, target, completed, current, planned, failed
) -> None:
    extractor = DeterministicIntentExtractor(CsvCatalogueRepository(PROCESSED_DATA).get_aliases())
    parsed = extractor.extract(message)

    assert parsed.module_code == target
    assert (parsed.completed_modules, parsed.current_modules, parsed.planned_modules) == (
        completed, current, planned)
    assert parsed.not_completed_modules == failed


@pytest.mark.parametrize(
    "message",
    [
        "what electives can I take",
        "What electives can I take in fourth year?",
        "which modules can I take",
        "what compulsory modules do I have",
    ],
)
def test_list_questions_with_can_i_take_ask_for_a_list_not_for_one_module(message) -> None:
    extractor = DeterministicIntentExtractor(CsvCatalogueRepository(PROCESSED_DATA).get_aliases())

    assert extractor.extract(message).intent == ("eligible_modules" if "can I take" in message or "can i take" in message else "curriculum_list")


def test_can_i_take_a_named_module_is_still_an_eligibility_question() -> None:
    extractor = DeterministicIntentExtractor(CsvCatalogueRepository(PROCESSED_DATA).get_aliases())

    assert extractor.extract("Can I take ELEN4010A?").intent == "eligibility"
    assert extractor.extract("Can I take the elective ELEN4010A?").intent == "eligibility"


def test_gemini_cannot_invent_a_combined_year_request():
    fallback=DeterministicIntentExtractor((Alias("machine learning","machine_learning","interest"),))
    extractor=GeminiIntentExtractor.__new__(GeminiIntentExtractor)
    extractor._client=SimpleNamespace(models=_Models(ParsedAdvisorRequest(intent="module_recommendations",year_of_study=3,include_electives=True,interests=["machine_learning"])))
    extractor._model="test-model"
    extractor._fallback=fallback
    extractor._allowed_interests=frozenset({"machine_learning"})
    extractor._allowed_careers=frozenset()
    extractor._retry_after=0.0
    result=extractor.extract("Recommend electives for machine learning")
    assert result.include_electives is False
    assert result.year_of_study is None
    assert result.requirement_type=="elective_pool"
