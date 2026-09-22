"""Tests for the boundary between Gemini extraction and trusted app state."""

from types import SimpleNamespace

from app.advisor.intent import (
    DeterministicIntentExtractor,
    GeminiIntentExtractor,
    ParsedAdvisorRequest,
)
from app.advisor.normalisation import Alias


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

    assert result.intent == "curriculum_list"
    assert result.year_of_study == 4
    assert result.requirement_type == "elective_pool"


def test_interest_elective_question_is_not_single_module_eligibility() -> None:
    aliases = (Alias("machine learning", "machine_learning", "interest"),)

    result = DeterministicIntentExtractor(aliases).extract(
        "What electives can I take if I'm interested in machine learning?"
    )

    assert result.intent == "curriculum_list"
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

    assert result.intent == "public_course_search"


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
                intent="public_course_search",
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
