"""End-to-end tests for the deterministic CSV-backed advisor engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.advisor.engine import AdvisorEngine
from app.advisor.elective_careers import ELECTIVE_CAREER_DIRECTIONS
from app.advisor.intent import DeterministicIntentExtractor
from app.backend import CurricuPathService
from app.data.repository import CsvCatalogueRepository
from app.data.sessions import ConversationContext


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DATA = PROJECT_ROOT / "data" / "processed"


def _engine(semantic_matcher=None) -> AdvisorEngine:
    repository = CsvCatalogueRepository(PROCESSED_DATA)
    service = CurricuPathService(repository, str(PROJECT_ROOT))
    extractor = DeterministicIntentExtractor(repository.data.aliases)
    return AdvisorEngine(service, extractor, semantic_matcher)


class FakeSemanticMatcher:
    def course_scores(self, query, course_ids):
        return {course_id: 0.8 for course_id in course_ids}

    def module_scores(self, query, module_codes):
        return {module_code: 0.8 for module_code in module_codes}


def test_csv_repository_exposes_programmes_and_cbo_metadata() -> None:
    repository = CsvCatalogueRepository(PROCESSED_DATA)

    assert {row["programme_code"] for row in repository.list_programmes()} == {
        "EFA03",
        "EFA04",
    }
    module = repository.get_module("ELEN4001A")
    assert module is not None
    assert module["course_information"]["cbo_available"] is True
    assert module["course_information"]["lecturer"] == "Professor Alan Robert Clark"
    assert module["course_information"]["hours"]["notional_hours_total"] == 150
    assert "Antenna fundamentals" in module["course_information"]["scope"]


def test_new_control_two_cbo_exposes_verified_course_information() -> None:
    module = CsvCatalogueRepository(PROCESSED_DATA).get_module("ELEN4016A")

    assert module is not None
    assert module["course_information"]["cbo_available"] is True
    assert module["course_information"]["hours"]["notional_hours_total"] == 150
    assert module["course_information"]["academic_year"] == 2024
    assert module["course_information"]["lecturer"] == "Dr Nyandoro O. T."
    assert "Advanced Control Engineering" in module["course_information"]["prescribed_materials"]


def test_new_first_year_cbos_expose_verified_course_information() -> None:
    repository = CsvCatalogueRepository(PROCESSED_DATA)

    math = repository.get_module("MATH1049A")
    design = repository.get_module("FEBE1004A")
    physics = repository.get_module("PHYS1034A")

    assert math is not None and math["course_information"]["cbo_available"] is True
    assert math["course_information"]["course_coordinator"] == "Dr A Davison"
    assert "Thomas' Calculus" in math["course_information"]["prescribed_materials"]
    assert design is not None
    assert design["course_information"]["hours"]["weekly_workload_guidance"].startswith(
        "About 10 hours per week"
    )
    assert physics is not None
    assert "Mechanics Statics component" in physics["course_information"]["evidence_notes"]


def test_new_math_and_physics_cbos_expose_verified_course_information() -> None:
    repository = CsvCatalogueRepository(PROCESSED_DATA)

    mathematics = repository.get_module("MATH2014A")
    physics = repository.get_module("PHYS2007A")

    assert mathematics is not None
    assert mathematics["course_information"]["cbo_available"] is True
    assert mathematics["course_information"]["course_coordinator"] == "Dr Jabulani Phakathi"
    assert mathematics["course_information"]["hours"]["notional_hours_total"] == 330
    assert "Laplace Fourier" in mathematics["course_information"]["scope"]
    assert physics is not None
    assert physics["course_information"]["cbo_available"] is True
    assert physics["course_information"]["lecturer"] == "Prof Phil Ferrer; Dr Hilary Masenda"
    assert "semiconductors" in physics["course_information"]["scope"]


def test_math1049_cbo_prerequisite_is_enforced() -> None:
    without_math1048 = _engine().advise("Can I take MATH1049A in EFA04?")
    with_math1048 = _engine().advise(
        "Can I take MATH1049A in EFA04?",
        completed_modules={"MATH1048A"},
    )

    assert without_math1048["status"] == "not_eligible"
    assert without_math1048["decision"] == "ineligible"
    assert "MATH1048A (Engineering Mathematics IA)" in without_math1048["answer"]
    assert with_math1048["status"] == "ok"
    assert with_math1048["decision"] == "eligible"
    assert with_math1048["eligible"] is True


def test_completed_module_is_reported_as_completed_not_eligible() -> None:
    result = _engine().advise(
        "Can I take elen2017?",
        programme_code="EFA04",
        completed_modules={"ELEN2017A"},
    )

    assert result["status"] == "completed"
    assert result["completed"] is True
    assert result["available_to_take"] is False
    assert result["answer"] == (
        "ELEN2017A is marked as completed in your profile. "
        "It will not be recommended as a module for you to take again."
    )
    assert result["_candidate_log"][0]["selected"] is False


def test_accepted_candidate_cbos_expose_source_supported_metadata() -> None:
    repository = CsvCatalogueRepository(PROCESSED_DATA)

    signals = repository.get_module("ELEN3013A")
    numerical = repository.get_module("APPM3021A")
    management = repository.get_module("MECN4020A")
    algorithms = repository.get_module("COMS2004A")
    control_one = repository.get_module("ELEN3016A")

    assert signals is not None
    assert signals["course_information"]["course_coordinator"] == "Prof O. O. Oyerinde"
    assert "Discrete-time signals" in signals["course_information"]["scope"]
    assert numerical is not None
    assert numerical["course_information"]["academic_year"] == 2025
    assert "does not state credits" in numerical["course_information"]["evidence_notes"]
    assert management is not None
    assert management["course_information"]["hours"]["notional_hours_total"] == 120
    assert "119 hours" in management["course_information"]["evidence_notes"]
    assert algorithms is not None
    assert algorithms["course_information"]["course_coordinator"] == "Prof Ritesh Ajoodha"
    assert "Data Structures and Algorithms in C++" in algorithms["course_information"]["prescribed_materials"]
    assert control_one is not None
    assert control_one["course_information"]["course_coordinator"] == "Prof M. A. van Wyk"
    assert "Physical-system modelling" in control_one["course_information"]["scope"]


def test_advisor_rejects_ee_only_module_for_ie_profile() -> None:
    result = _engine().advise("Can I take ELEN4001A in EFA04?")

    assert result["intent"] == "eligibility"
    assert result["status"] == "not_eligible"
    assert result["reasons"] == ["ELEN4001A is not part of programme EFA04."]


def test_advisor_escalates_transfer_credit_to_manual_review() -> None:
    result = _engine().advise(
        "My transfer credits may count for ELEN4025A. Can I take it?",
        programme_code="EFA04",
    )

    assert result["status"] == "manual_review_required"
    assert result["decision"] == "manual_review_required"
    assert result["manual_review_required"] is True
    assert "Transfer-credit recognition" in result["answer"]


def test_module_code_without_suffix_resolves_to_handbook_code() -> None:
    result = _engine().advise("Tell me about ELEN2017")

    assert result["status"] == "ok"
    assert result["module"]["course_code"] == "ELEN2017A"
    assert result["module"]["course_name"] == "Electric Circuits"


def test_lowercase_module_code_resolves_to_handbook_code() -> None:
    result = _engine().advise("tell me about elen2017")

    assert result["status"] == "ok"
    assert result["module"]["course_code"] == "ELEN2017A"


def test_programme_name_lists_information_engineering_curriculum() -> None:
    result = _engine().advise(
        "Tell me about Information Engineering courses",
        programme_code="EFA03",
    )

    assert result["intent"] == "curriculum_list"
    assert result["programme_code"] == "EFA04"
    assert result["modules"]
    assert all(module["programme_code"] == "EFA04" for module in result["modules"])
    assert "Information Engineering (EFA04)" in result["answer"]


def test_module_code_and_name_are_interchangeable_for_information_lookup() -> None:
    by_code = _engine().advise("Tell me about ELEN2017A", programme_code="EFA04")
    by_name = _engine().advise(
        "Tell me about the Electric Circuits course",
        programme_code="EFA04",
    )

    assert by_code["module"]["course_code"] == "ELEN2017A"
    assert by_name["module"]["course_code"] == "ELEN2017A"
    assert by_name["answer"] == by_code["answer"]


def test_module_credit_and_year_questions_use_catalogue_membership() -> None:
    result = _engine().advise(
        "How many credits is Electric Circuits and what year is it taken?",
        programme_code="EFA04",
    )

    assert result["module"]["course_code"] == "ELEN2017A"
    assert "12 NQF credits" in result["answer"]
    assert "EFA04 Year 2 compulsory" in result["answer"]


def test_degree_credit_question_counts_elective_selection_rules_once() -> None:
    result = _engine().advise("How many credits does Electrical Engineering have?")

    assert result["intent"] == "credit_information"
    assert result["credit_summary"]["total_nqf_credits"] == 592
    assert [year["total_credits"] for year in result["credit_summary"]["years"]] == [
        144,
        154,
        153,
        141,
    ]


def test_information_engineering_degree_and_careers_are_source_backed() -> None:
    result = _engine().advise(
        "What career opportunities are there for Information Engineering?"
    )

    assert result["intent"] == "programme_information"
    assert result["programme_code"] == "EFA04"
    assert result["programme_profile"]["qualification"] == "BSc (Eng)"
    assert "Software Engineer" in result["programme_profile"]["career_opportunities"]
    assert "Network Engineer" in result["answer"]
    assert result["programme_profile"]["source"]["verification_status"] == "verified"


def test_electrical_engineering_degree_and_careers_are_source_backed() -> None:
    result = _engine().advise("What is the Electrical Engineering degree?")

    assert result["intent"] == "programme_information"
    assert result["programme_code"] == "EFA03"
    assert "generation and use of electrical energy" in result["answer"]
    assert "Power Engineer" in result["programme_profile"]["career_opportunities"]


def test_programme_comparison_bypasses_public_course_ranking() -> None:
    result = _engine().advise(
        "I'm in 2nd year and I like optical wireless communication. Should I choose "
        "Electrical Engineering or Information Engineering?",
        ranking_mode="prototype",
    )

    assert result["intent"] == "programme_comparison"
    assert result["status"] == "ok"
    assert result["recommendation"] == {
        "programme_code": "EFA03",
        "programme_name": "Electrical Engineering",
    }
    assert result["programme_comparison"]["matched_interests"] == [
        "communications"
    ]
    assert "course load" not in result["answer"]
    assert "optical-wireless specialisation" in result["answer"]


def test_advisor_asks_programme_for_wits_interest_suggestions() -> None:
    result = _engine().advise("I want an electric circuits course")
    assert result["intent"] == "module_recommendations"
    assert result["status"] == "clarification_required"
    assert "EFA03 or EFA04" in result["answer"]


def test_machine_learning_career_question_returns_career_directions_not_course_list() -> None:
    result = _engine().advise(
        "If I am taking the machine learning course, what future careers should I expect?"
    )

    assert result["intent"] == "career_path"
    assert result["status"] == "ok"
    assert "career_options" in result
    assert "recommendations" not in result
    assert {option["career_tag"] for option in result["career_options"]} >= {
        "data_science",
        "ml_engineering",
    }
    assert "not employment guarantees" in result["answer"]
    assert "machine_learning" not in result["answer"]


def test_power_systems_career_question_uses_the_fourth_year_elective() -> None:
    result = _engine().advise(
        "If I am taking the power systems course, what future careers should I expect?"
    )

    assert result["intent"] == "career_path"
    assert result["status"] == "ok"
    assert result["career_subject"] == {
        "course_code": "ELEN4018A",
        "course_name": "Power Systems",
    }
    assert "recommendations" not in result
    assert {option["career_tag"] for option in result["career_options"]} == {
        "power_systems_engineering",
        "grid_planning",
    }


def test_career_question_accepts_a_fourth_year_elective_code() -> None:
    result = _engine().advise("What careers can ELEN4024A lead to?")

    assert result["intent"] == "career_path"
    assert result["career_subject"]["course_name"] == "Secure Computing"
    assert {option["career_tag"] for option in result["career_options"]} == {
        "cybersecurity_engineering",
        "secure_software_engineering",
    }


def test_every_fourth_year_elective_has_controlled_career_directions() -> None:
    repository = CsvCatalogueRepository(PROCESSED_DATA)
    elective_codes = {
        module["course_code"]
        for programme in repository.list_programmes()
        for module in repository.list_modules(programme["programme_code"], 4)
        if module["requirement_type"] == "elective_pool"
    }

    assert set(ELECTIVE_CAREER_DIRECTIONS) == elective_codes
    for course_code in sorted(elective_codes):
        result = _engine().advise(
            f"What future careers can taking {course_code} lead to?"
        )
        assert result["status"] == "ok"
        assert result["career_subject"]["course_code"] == course_code
        assert result["career_options"]
        assert "recommendations" not in result


def test_wits_suggestions_do_not_query_public_semantic_candidates() -> None:
    class NoPublicMatcher:
        def course_scores(self,*args):
            raise AssertionError("Retired public matcher queried")
    result = _engine(NoPublicMatcher()).advise("Recommend EFA04 electives for machine learning",module_history_confirmed=False)
    assert result["unresolved_modules"]
    assert all("course_id" not in row for row in result["unresolved_modules"])


def test_advisor_requests_programme_for_eligibility() -> None:
    result = _engine().advise("Can I take ELEN4001A?")

    assert result["status"] == "clarification_required"
    assert "EFA03 or EFA04" in result["clarification_question"]


def test_advisor_lists_a_programme_year() -> None:
    result = _engine().advise("Show the EFA04 year 4 electives")

    assert result["status"] == "ok"
    assert result["modules"]
    assert all(module["programme_code"] == "EFA04" for module in result["modules"])
    assert all(module["year_of_study"] == 4 for module in result["modules"])
    assert all(
        module["requirement_type"] == "elective_pool"
        for module in result["modules"]
    )


def test_explicit_programme_and_ordinal_year_override_ui_selection() -> None:
    result = _engine().advise(
        "show 4th year electives for EFA04",
        programme_code="EFA03",
    )

    assert result["status"] == "ok"
    assert result["programme_code"] == "EFA04"
    assert result["year_of_study"] == 4
    assert result["requirement_type"] == "elective_pool"
    assert len(result["modules"]) == 7
    assert {module["course_code"] for module in result["modules"]} == {
        "ELEN4010A",
        "ELEN4016A",
        "ELEN4017A",
        "ELEN4020A",
        "ELEN4022A",
        "ELEN4024A",
        "ELEN4025A",
    }


def test_word_year_and_compulsory_filter_are_understood() -> None:
    result = _engine().advise("show fourth year compulsory modules for efa04")

    assert result["year_of_study"] == 4
    assert len(result["modules"]) == 5
    assert all(
        module["requirement_type"] == "compulsory"
        for module in result["modules"]
    )


def test_curriculum_filters_survive_programme_clarification() -> None:
    engine = _engine()
    first = engine.advise("show 4th year electives")
    context = ConversationContext.from_dict(first["conversation_context"])

    second = engine.advise("EFA04", context=context)

    assert first["status"] == "clarification_required"
    assert second["status"] == "ok"
    assert len(second["modules"]) == 7
    assert all(
        module["year_of_study"] == 4
        and module["requirement_type"] == "elective_pool"
        for module in second["modules"]
    )


def test_efa04_machine_learning_interest_ranks_matching_elective_first() -> None:
    result = _engine().advise(
        "Recommend EFA04 fourth year electives for machine learning"
    )

    assert result["status"] == "ok"
    assert len(result["unresolved_modules"]) == 3
    assert result["unresolved_modules"][0]["course_code"] == "ELEN4025A"
    assert {
        item["course_code"] for item in result["unresolved_modules"][1:]
    } == {"ELEN4010A", "ELEN4020A"}
    assert result["unresolved_modules"][0]["matched_tags"] == ["machine_learning"]
    assert result["unresolved_modules"][0]["eligibility"]["assessed"] is True


def test_natural_elective_interest_question_uses_profile_programme() -> None:
    result = _engine().advise(
        "What electives can I take if I'm interested in machine learning?",
        programme_code="EFA04",
        context=ConversationContext(pending_intent="eligibility"),
    )

    assert result["intent"] == "eligible_modules"
    assert result["status"] == "ok"
    assert result["programme_code"] == "EFA04"
    assert result["year_of_study"] == 4
    assert result["unresolved_modules"][0]["course_code"] == "ELEN4025A"


def test_profile_course_summary_groups_completed_and_current_modules() -> None:
    result = _engine().advise(
        "Tell me about my courses",
        programme_code="EFA04",
        completed_modules={"ELEN2017A"},
        current_modules={"ELEN2020A"},
        context=ConversationContext(pending_intent="eligibility"),
    )

    assert result["intent"] == "profile_courses"
    assert result["status"] == "ok"
    assert [item["course_code"] for item in result["profile_courses"]["completed"]] == ["ELEN2017A"]
    assert [item["course_code"] for item in result["profile_courses"]["current"]] == ["ELEN2020A"]
    assert result["profile_courses"]["completed"][0]["profile_status"] == "completed"
    assert result["profile_courses"]["current"][0]["profile_status"] == "current"
    assert "You have completed ELEN2017A (Electric Circuits)." in result["answer"]
    assert "currently taking ELEN2020A" in result["answer"]


def test_efa03_interest_recommendation_defaults_to_fourth_year() -> None:
    result = _engine().advise("Suggest EFA03 electives for renewable energy")

    assert result["status"] == "ok"
    assert result["year_of_study"] == 4
    assert result["unresolved_modules"][0]["course_code"] == "ELEN4023A"
    assert all(
        item["programme_code"] == "EFA03"
        and item["year_of_study"] == 4
        and item["requirement_type"] == "elective_pool"
        for item in result["unresolved_modules"]
    )


def test_declared_history_applies_eligibility_before_elective_selection() -> None:
    result = _engine().advise(
        "Recommend EFA04 year 4 electives for machine learning",
        completed_modules={"ELEN3009A", "APPM3021A"},
    )

    assert result["status"] == "ok"
    assert result["recommendations"][0]["course_code"] == "ELEN4025A"
    assert result["recommendations"][0]["eligibility"]["eligible"] is True


def test_interest_matches_remain_visible_when_history_blocks_all() -> None:
    result = _engine().advise(
        "Recommend EFA04 year 4 electives for machine learning",
        completed_modules={"MATH1048A"},
    )

    assert result["status"] == "ok"
    assert result["recommendation_kind"] == "eligible_wits_modules"
    assert len(result["unresolved_modules"]) == 3
    assert result["unresolved_modules"][0]["course_code"] == "ELEN4025A"
    assert all(
        item["eligibility"]["assessed"] is True
        and item["eligibility"]["eligible"] is False
        for item in result["unresolved_modules"]
    )
    assert "need missing module facts" in result["answer"]


def test_module_eligibility_without_code_asks_for_the_code() -> None:
    result = _engine().advise("module eligibility")

    assert result["intent"] == "eligibility"
    assert result["clarification_question"] == (
        "Which module code or full module name should I check?"
    )


def test_module_phrase_starts_module_information_clarification() -> None:
    result = _engine().advise("a module")

    assert result["intent"] == "module_information"
    assert result["clarification_question"] == (
        "Which module code or full module name should I look up?"
    )


def test_module_information_names_staff_and_content_from_verified_cbo() -> None:
    result = _engine().advise("Who teaches Control I and what content is covered?")

    assert result["status"] == "ok"
    assert result["module"]["course_code"] == "ELEN3016A"
    assert "Academic staff/lecturer(s): Prof M. A. van Wyk; Dr M. Ngwako." in result["answer"]
    assert "Course coordinator: Prof M. A. van Wyk." in result["answer"]
    assert "Content covered: Physical-system modelling" in result["answer"]
    assert "Source: verified 2026 CBO." in result["answer"]


def test_module_information_uses_partial_math3025_evidence_without_overclaiming() -> None:
    result = _engine().advise("Tell me about MATH3025A")

    assert result["status"] == "ok"
    information = result["module"]["course_information"]
    assert information["cbo_available"] is True
    assert information["verification_status"] == "incomplete"
    assert information["course_coordinator"] == "Prof. A. Kara"
    assert information["lecturer"] == "Prof. Y. Hardy; Dr. C. Izuchukwu"
    assert "Detailed topic coverage is not stated" in result["answer"]
    assert "a complete CBO is still required" in result["answer"]


def test_latest_added_cbos_expose_verified_staff_and_scope() -> None:
    repository = CsvCatalogueRepository(PROCESSED_DATA)

    expected = {
        "ELEN3007A": ("Prof Anton van Wyk", "Probability foundations"),
        "ELEN3009A": ("Dr S. P. Levitt", "Modern C++"),
        "ELEN3018A": ("Dr S. Achari; Dr M. R. Dangor", "Macroeconomics"),
        "ELEN3024A": ("Prof Mitchell A. Cox", "Analogue AM FM and PM modulation"),
        "ELEN4002A": ("Shamin Achari; Yuval Genga", "Electrical Engineering investigation"),
        "ELEN4012A": ("Shamin Achari; Yuval Genga", "Information Engineering investigation"),
    }
    for course_code, (staff, scope_fragment) in expected.items():
        module = repository.get_module(course_code)
        assert module is not None
        information = module["course_information"]
        assert information["cbo_available"] is True
        assert information["lecturer"] == staff
        assert scope_fragment in information["scope"]

    control = repository.get_module("ELEN3016A")
    assert control is not None
    assert control["course_information"]["academic_year"] == 2026
    assert control["course_information"]["source_id"] == "CBO_ELEN3016_2026"


def test_pending_eligibility_resolves_electronics_one_by_name() -> None:
    context = ConversationContext(pending_intent="eligibility")

    result = _engine().advise(
        "electronics 1",
        programme_code="EFA04",
        context=context,
    )

    assert result["course_code"] == "ELEN2016A"
    assert "no curriculum module record" not in " ".join(result["reasons"])
    assert "MATH1048A (Engineering Mathematics IA)" in result["answer"]
    assert "MATH1049A (Engineering Mathematics IB)" in result["answer"]
    assert "ELEN2017A (Electric Circuits)" in result["answer"]
    assert "Corequisites:" in result["answer"]
    assert "These must be completed before registration." in result["answer"]
    assert "planned concurrently" in result["answer"]


def test_eligibility_marks_declared_prerequisites_and_corequisites_satisfied() -> None:
    result = _engine().advise(
        "Can I take Electronics I in EFA04?",
        completed_modules={
            "MATH1048A",
            "MATH1049A",
            "PHYS1032A",
            "PHYS1033A",
        },
        planned_modules={"ELEN2017A"},
    )

    assert result["eligible"] is True
    assert result["requirements"]["prerequisites"][0]["satisfied"] is True
    assert result["requirements"]["corequisites"][0]["satisfied"] is True
    assert "Prerequisites:" in result["answer"]
    assert "Corequisites:" in result["answer"]


def test_eligibility_asks_the_selected_rule_fact_as_plain_language() -> None:
    result = _engine().advise(
        "Can I take MATH1049A in EFA04?",
        module_history_confirmed=False,
    )

    assert result["status"] == "clarification_required"
    assert result["decision"] == "needs_clarification"
    assert result["clarification_question"] == "Have you completed MATH1048A?"
    assert result["clarification_options"] == ["Completed", "Not completed"]
    assert "Have you completed MATH1048A?" in result["answer"]


def test_conversation_context_round_trips_pending_module_fact() -> None:
    context = ConversationContext(
        pending_intent="eligibility",
        module_code="MATH1049A",
        programme_code="EFA04",
        pending_fact_course_code="MATH1048A",
        pending_fact_gate="prerequisite",
        clarification_attempted=False,
    )

    assert ConversationContext.from_dict(context.as_dict()) == context


def test_completed_clarification_is_reused_for_original_decision() -> None:
    engine = _engine()
    first = engine.advise(
        "Can I take MATH1049A in EFA04?",
        module_history_confirmed=False,
    )
    second = engine.advise(
        "Completed",
        context=ConversationContext.from_dict(first["conversation_context"]),
        module_history_confirmed=False,
    )

    assert first["clarification_question"] == "Have you completed MATH1048A?"
    assert second["decision"] == "eligible"
    assert second["status"] == "ok"
    assert second["clarification_applied"] == {
        "course_code": "MATH1048A",
        "state": "completed",
        "gate": "prerequisite",
    }
    assert second["conversation_context"] == ConversationContext().as_dict()


def test_not_completed_clarification_produces_ineligible_decision() -> None:
    engine = _engine()
    first = engine.advise(
        "Can I take MATH1049A in EFA04?",
        module_history_confirmed=False,
    )
    second = engine.advise(
        "Not completed",
        context=ConversationContext.from_dict(first["conversation_context"]),
        module_history_confirmed=False,
    )

    assert second["decision"] == "ineligible"
    assert second["status"] == "not_eligible"
    assert second["clarification_applied"]["state"] == "not_completed"


def test_planned_corequisite_clarification_satisfies_corequisite() -> None:
    engine = _engine()
    first = engine.advise(
        "Can I take ELEN3000A in EFA03?",
        completed_modules={"MATH2014A"},
        module_history_confirmed=False,
    )
    second = engine.advise(
        "Planned concurrently",
        completed_modules={"MATH2014A"},
        context=ConversationContext.from_dict(first["conversation_context"]),
        module_history_confirmed=False,
    )

    assert first["clarification_question"] == (
        "What is your status for MATH3025A: completed, currently taking it, "
        "planning to take it concurrently, or not completed?"
    )
    assert second["decision"] == "eligible"
    assert second["clarification_applied"]["state"] == "planned"


def test_unrecognised_clarification_stops_without_guessing() -> None:
    engine = _engine()
    first = engine.advise(
        "Can I take MATH1049A in EFA04?",
        module_history_confirmed=False,
    )
    second = engine.advise(
        "I am not sure",
        context=ConversationContext.from_dict(first["conversation_context"]),
        module_history_confirmed=False,
    )

    assert second["status"] == "clarification_unresolved"
    assert second["decision"] == "needs_clarification"
    assert second["clarification_exhausted"] is True
    assert second["conversation_context"] == ConversationContext().as_dict()


def test_a_reply_that_resolves_one_fact_keeps_asking_about_the_rest() -> None:
    engine = _engine()
    first = engine.advise(
        "Can I take ELEN4001A in EFA03?",
        module_history_confirmed=False,
    )
    second = engine.advise(
        "ELEN3000A completed",
        context=ConversationContext.from_dict(first["conversation_context"]),
        module_history_confirmed=False,
    )

    assert first["clarification_question"].startswith(
        "Which of these have you completed: ELEN3000A, MATH3025A?"
    )
    assert second["status"] == "clarification_required"
    assert second["clarification_exhausted"] is False
    assert second["clarification_question"] == "Have you completed MATH3025A?"
    assert second["clarification_applied"]["course_code"] == "ELEN3000A"


def test_a_bare_status_is_not_guessed_when_several_modules_are_pending() -> None:
    engine = _engine()
    first = engine.advise(
        "Can I take ELEN4001A in EFA03?",
        module_history_confirmed=False,
    )
    second = engine.advise(
        "Completed",
        context=ConversationContext.from_dict(first["conversation_context"]),
        module_history_confirmed=False,
    )

    assert second["status"] == "clarification_unresolved"
    assert second["clarification_exhausted"] is True


def _multi_fact_first_turn(engine):
    return engine.advise(
        "Can I take ELEN3013A in EFA04?",
        module_history_confirmed=False,
    )


def test_every_unknown_prerequisite_is_asked_about_in_one_question() -> None:
    first = _multi_fact_first_turn(_engine())

    assert first["status"] == "clarification_required"
    assert first["clarification_question"].startswith(
        "Which of these have you completed: ELEN2020A, ELEN2005A, MATH2014A?"
    )
    assert first["clarification_options"] == ["All completed", "None completed"]
    assert first["conversation_context"]["pending_fact_course_codes"] == [
        "ELEN2020A",
        "ELEN2005A",
        "MATH2014A",
    ]


def test_one_reply_can_give_a_status_for_each_module_and_keeps_the_original_target() -> None:
    engine = _engine()
    first = _multi_fact_first_turn(engine)
    second = engine.advise(
        "ELEN2020A completed, ELEN2005A completed, MATH2014A not completed",
        context=ConversationContext.from_dict(first["conversation_context"]),
        module_history_confirmed=False,
    )

    assert second["course_code"] == "ELEN3013A"
    assert second["decision"] == "ineligible"
    assert {
        (fact["course_code"], fact["state"])
        for fact in second["clarification_applied_all"]
    } == {
        ("ELEN2020A", "completed"),
        ("ELEN2005A", "completed"),
        ("MATH2014A", "not_completed"),
    }


def test_partial_replies_keep_earlier_answers_and_ask_only_about_what_is_left() -> None:
    engine = _engine()
    first = _multi_fact_first_turn(engine)
    second = engine.advise(
        "ELEN2020A completed",
        context=ConversationContext.from_dict(first["conversation_context"]),
        module_history_confirmed=False,
    )
    third = engine.advise(
        "ELEN2005A completed and MATH2014A completed",
        context=ConversationContext.from_dict(second["conversation_context"]),
        module_history_confirmed=False,
    )

    assert second["clarification_question"].startswith(
        "Which of these have you completed: ELEN2005A, MATH2014A?"
    )
    assert second["clarification_exhausted"] is False
    assert third["clarification_question"].startswith("What is your status for ELEN3012A")
    assert ("ELEN2020A", "completed") in ConversationContext.from_dict(
        third["conversation_context"]
    ).answered_facts


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        (
            "ELEN2020A and ELEN2005A are completed the rest are not",
            {"ELEN2020A": "completed", "ELEN2005A": "completed", "MATH2014A": "not_completed"},
        ),
        (
            "I have completed ELEN2020A and ELEN2005A but not MATH2014A",
            {"ELEN2020A": "completed", "ELEN2005A": "completed", "MATH2014A": "not_completed"},
        ),
        (
            "the rest are not, ELEN2005A completed",
            {"ELEN2005A": "completed", "ELEN2020A": "not_completed", "MATH2014A": "not_completed"},
        ),
        (
            "completed: ELEN2020A, MATH2014A. not completed: ELEN2005A",
            {"ELEN2020A": "completed", "MATH2014A": "completed", "ELEN2005A": "not_completed"},
        ),
        ("ELEN2020A yes, ELEN2005A no", {"ELEN2020A": "completed", "ELEN2005A": "not_completed"}),
        ("not sure", {}),
        ("ELEN2020A planned", {}),
    ],
)
def test_prerequisite_replies_are_read_in_natural_groupings(reply, expected) -> None:
    from app.advisor.engine import _parse_module_fact_replies

    codes = ("ELEN2020A", "ELEN2005A", "MATH2014A")

    assert _parse_module_fact_replies(reply, codes, "prerequisite") == expected


def test_grouped_reply_resolves_the_check_end_to_end() -> None:
    engine = _engine()
    first = _multi_fact_first_turn(engine)
    second = engine.advise(
        "ELEN2020A and ELEN2005A are completed the rest are not",
        context=ConversationContext.from_dict(first["conversation_context"]),
        module_history_confirmed=False,
    )

    assert second["course_code"] == "ELEN3013A"
    assert second["decision"] == "ineligible"
    assert len(second["clarification_applied_all"]) == 3


def test_all_completed_button_answers_every_pending_module() -> None:
    engine = _engine()
    first = _multi_fact_first_turn(engine)
    second = engine.advise(
        "All completed",
        context=ConversationContext.from_dict(first["conversation_context"]),
        module_history_confirmed=False,
    )
    third = engine.advise(
        "Planned concurrently",
        context=ConversationContext.from_dict(second["conversation_context"]),
        module_history_confirmed=False,
    )

    assert len(second["clarification_applied_all"]) == 3
    assert third["decision"] == "eligible"
    assert third["conversation_context"] == ConversationContext().as_dict()


def test_a_reply_with_no_recognised_status_still_ends_the_check() -> None:
    engine = _engine()
    first = _multi_fact_first_turn(engine)
    second = engine.advise(
        "not sure",
        context=ConversationContext.from_dict(first["conversation_context"]),
        module_history_confirmed=False,
    )

    assert second["status"] == "clarification_unresolved"
    assert second["clarification_exhausted"] is True


def test_measurement_systems_accepts_completed_third_year_curriculum() -> None:
    repository = CsvCatalogueRepository(PROCESSED_DATA)
    completed = {
        module["course_code"]
        for module in repository.list_modules("EFA04", 3)
    }
    service = CurricuPathService(repository, str(PROJECT_ROOT))

    result = service.eligibility(
        "ELEN4006A",
        "EFA04",
        completed,
        set(),
        set(),
    )

    assert result["eligible"] is True
    assert result["requirements"]["prerequisites"] == [
        {
            "rule_id": "PRE_ELEN4006_EFA04",
            "description": "all EFA04 Year 3 modules",
            "satisfied": True,
            "source_id": "EBE_2026",
        }
    ]


def test_pending_eligibility_clarifies_ambiguous_electronics_name() -> None:
    context = ConversationContext(pending_intent="eligibility")

    result = _engine().advise("electronics", context=context)

    assert result["status"] == "clarification_required"
    assert {item["course_code"] for item in result["module_matches"]} == {
        "ELEN2016A",
        "ELEN3002A",
    }


def test_pending_eligibility_clarifies_missing_a_b_branch() -> None:
    context = ConversationContext(pending_intent="eligibility")

    result = _engine().advise("signals and systems 2", context=context)

    assert result["status"] == "clarification_required"
    assert {item["course_code"] for item in result["module_matches"]} == {
        "ELEN3012A",
        "ELEN3013A",
    }


def test_pending_eligibility_resolves_numeric_a_b_branch() -> None:
    context = ConversationContext(pending_intent="eligibility")

    result = _engine().advise(
        "signals and systems 2 b",
        programme_code="EFA04",
        context=context,
    )

    assert result["course_code"] == "ELEN3013A"


def test_pending_eligibility_prioritises_module_series_over_public_course_alias() -> None:
    context = ConversationContext(pending_intent="eligibility")

    result = _engine().advise("software development", context=context)

    assert result["intent"] == "eligibility"
    assert {item["course_code"] for item in result["module_matches"]} == {
        "ELEN2020A",
        "ELEN3009A",
        "ELEN4010A",
    }


def test_pending_module_information_resolves_interest_named_module() -> None:
    context = ConversationContext(pending_intent="module_information")

    result = _engine().advise("renewable energy", context=context)

    assert result["status"] == "ok"
    assert result["module"]["course_code"] == "ELEN4023A"


def test_bare_exact_course_name_opens_curriculum_module_information() -> None:
    result = _engine().advise("Control I")

    assert result["intent"] == "module_information"
    assert result["status"] == "ok"
    assert result["module"]["course_code"] == "ELEN3016A"


def test_embedded_complete_course_name_resolves_longest_title() -> None:
    result = _engine().advise("Tell me about Electrical Engineering Design II")

    assert result["status"] == "ok"
    assert result["module"]["course_code"] == "ELEN4000A"


def test_public_course_wording_is_not_reclassified_as_module_information() -> None:
    result = _engine().advise("I want an electric circuits course")

    assert result["intent"] == "module_recommendations"
    assert result["status"] == "clarification_required"
    assert "recommendations" not in result


def test_pending_eligibility_uses_follow_up_module_and_programme() -> None:
    engine = _engine()
    first = engine.advise("module eligibility")
    context = ConversationContext(
        pending_intent=first["conversation_context"]["pending_intent"]
    )

    second = engine.advise("ELEN4001A", context=context)
    second_context = ConversationContext(
        pending_intent=second["conversation_context"]["pending_intent"],
        module_code=second["conversation_context"]["module_code"],
    )
    third = engine.advise("EFA04", context=second_context)

    assert second["clarification_question"] == "Which programme are you in: EFA03 or EFA04?"
    assert third["status"] == "not_eligible"
    assert third["reasons"] == ["ELEN4001A is not part of programme EFA04."]


def test_pending_eligibility_resolves_code_without_suffix() -> None:
    context = ConversationContext(pending_intent="eligibility")

    result = _engine().advise("ELEN2017", programme_code="EFA04", context=context)

    assert result["course_code"] == "ELEN2017A"
    assert "no curriculum module record" not in " ".join(result["reasons"])


def test_lowercase_module_and_programme_codes_are_normalised() -> None:
    context = ConversationContext(pending_intent="eligibility")

    result = _engine().advise("elen2017 in efa04", context=context)

    assert result["course_code"] == "ELEN2017A"
    assert result["programme_code"] == "EFA04"
    assert "no curriculum module record" not in " ".join(result["reasons"])


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        ("I have completed MATH1048A", {"MATH1048A": "completed"}),
        ("MATH1048A not done", {"MATH1048A": "not_completed"}),
        ("Completed", {"MATH1048A": "completed"}),
        ("I am not sure", {}),
    ],
)
def test_a_single_pending_module_accepts_a_sentence_that_names_it(reply, expected) -> None:
    from app.advisor.engine import _parse_module_fact_replies

    assert _parse_module_fact_replies(reply, ("MATH1048A",), "prerequisite") == expected


def test_single_question_end_to_end_with_a_named_reply() -> None:
    engine = _engine()
    first = engine.advise("Can I take MATH1049A in EFA04?", module_history_confirmed=False)
    second = engine.advise(
        "I have completed MATH1048A",
        context=ConversationContext.from_dict(first["conversation_context"]),
        module_history_confirmed=False,
    )

    assert first["status"] == "clarification_required"
    assert second["decision"] == "eligible"


class _MisreadingExtractor(DeterministicIntentExtractor):
    """Mimics a language model that guesses an unrelated intent for a bare quick-reply word."""

    def extract(self, text):
        parsed = super().extract(text)
        if text.strip().lower() in {"completed", "all completed", "planned concurrently"}:
            return parsed.model_copy(update={"intent": "profile_courses"})
        return parsed


def test_quick_reply_is_the_answer_even_when_a_model_guesses_another_intent() -> None:
    repository = CsvCatalogueRepository(PROCESSED_DATA)
    service = CurricuPathService(repository, str(PROJECT_ROOT))
    engine = AdvisorEngine(service, _MisreadingExtractor(repository.data.aliases))

    first = engine.advise("Can I take MATH1049A in EFA04?", module_history_confirmed=False)
    second = engine.advise(
        "Completed",
        context=ConversationContext.from_dict(first["conversation_context"]),
        module_history_confirmed=False,
    )

    assert first["status"] == "clarification_required"
    assert second["decision"] == "eligible"
    assert second["clarification_applied"]["state"] == "completed"


def test_a_real_question_with_the_word_completed_is_not_taken_as_the_answer() -> None:
    engine = _engine()
    first = engine.advise("Can I take MATH1049A in EFA04?", module_history_confirmed=False)
    second = engine.advise(
        "Which modules have I completed?",
        context=ConversationContext.from_dict(first["conversation_context"]),
        module_history_confirmed=False,
    )

    assert second.get("clarification_applied") in (None, {})


def test_a_declared_failed_module_settles_the_answer_without_asking_about_others() -> None:
    result = _engine().advise(
        "can I take ELEN4012 having failed ELEN3009?",
        programme_code="EFA04",
        module_history_confirmed=False,
    )

    assert result["decision"] == "ineligible"
    assert result["status"] == "not_eligible"
    assert "ELEN3009A" in result["answer"]
    assert result.get("clarification_question") in (None, "")


@pytest.mark.parametrize(
    ("message", "course", "decision", "told_me"),
    [
        ("can I take ELEN4012 having failed Software Development II?", "ELEN4012A", "ineligible", "ELEN3009A"),
        ("I failed Software Development II. Can I take Control II?", "ELEN4016A", None, None),
        ("Software Development II (failed), can I take ELEN4012A?", "ELEN4012A", "ineligible", "ELEN3009A"),
        ("Can I take Control II? I haven't passed Control I and Software Development II", "ELEN4016A", "ineligible", "ELEN3016A"),
    ],
)
def test_module_titles_given_a_status_are_facts_and_not_the_target(message, course, decision, told_me) -> None:
    result = _engine().advise(message, programme_code="EFA04", module_history_confirmed=False)

    assert result["course_code"] == course
    if decision:
        assert result["decision"] == decision
    if told_me:
        assert told_me in result["answer"]


def test_a_title_that_is_not_exact_is_never_guessed() -> None:
    from app.advisor.declared_names import rewrite_declared_names

    modules = [{"course_code": "ELEN3009A", "course_name": "Software Development II"},
               {"course_code": "ELEN2020A", "course_name": "Software Development I"}]

    assert rewrite_declared_names("I failed Software Development, can I take X?", modules) == \
        "I failed Software Development, can I take X?"
    assert rewrite_declared_names("I failed Software Development II and Software Development I.", modules) == \
        "I failed ELEN3009A and ELEN2020A."


def test_career_questions_keep_their_module_titles() -> None:
    result = _engine().advise(
        "If I am taking the power systems course, what future careers should I expect?"
    )

    assert result["intent"] == "career_path"
    assert result["career_subject"]["course_code"] == "ELEN4018A"


def _elective_codes(result):
    return {module["course_code"] for key in ["modules","unresolved_modules","other_modules"] for module in result.get(key, [])}


def test_elective_lists_differ_by_programme_from_the_profile_or_the_question() -> None:
    engine = _engine()
    ee = engine.advise("what electives can I take in fourth year", programme_code="EFA03")
    ie = engine.advise("what electives can I take in fourth year", programme_code="EFA04")
    ee_by_question = engine.advise("what electives can EE students take in fourth year")
    ie_by_question = engine.advise("what electives can information engineering students take in fourth year")

    assert _elective_codes(ee) and _elective_codes(ie) and _elective_codes(ee) != _elective_codes(ie)
    assert _elective_codes(ee_by_question) == _elective_codes(ee)
    assert _elective_codes(ie_by_question) == _elective_codes(ie)


def test_a_programme_named_in_the_question_wins_over_the_profile_and_says_so() -> None:
    result = _engine().advise(
        "what electives can I take as an information engineering student in fourth year",
        programme_code="EFA03",
    )

    assert "Information Engineering (EFA04)" in result["answer"]
    assert "not your profile's Electrical Engineering (EFA03)" in result["answer"]
    assert result["eligibility_summary"]["checked"] == 7


def test_missing_programme_is_asked_with_buttons_and_every_reply_form_is_understood() -> None:
    engine = _engine()
    first = engine.advise("what electives can I take in fourth year")

    assert first["status"] == "clarification_required"
    assert first["clarification_options"] == ["Electrical Engineering (EFA03)", "Information Engineering (EFA04)"]
    for reply, programme in [
        ("Electrical Engineering (EFA03)", "EFA03"), ("Information Engineering (EFA04)", "EFA04"),
        ("EFA03", "EFA03"), ("EE", "EFA03"), ("IE", "EFA04"), ("electrical", "EFA03"),
    ]:
        second = engine.advise(reply, context=ConversationContext.from_dict(first["conversation_context"]))
        assert second["status"] == "ok" and second["programme_code"] == programme, reply


def test_an_interest_request_is_not_mistaken_for_a_programme_statement() -> None:
    result = _engine().advise(
        "I like electrical engineering, recommend electives about power", programme_code="EFA03"
    )

    assert "interest-matching electives" in result["answer"]


class _GuessesModuleLookup(DeterministicIntentExtractor):
    """Mimics a model that labels a bare programme reply as a module lookup."""

    def extract(self, text):
        parsed = super().extract(text)
        if text.strip().upper() in {"EFA03", "EFA04"}:
            return parsed.model_copy(update={"intent": "module_information"})
        return parsed


def test_a_programme_reply_answers_the_question_even_when_a_model_guesses_a_module_lookup() -> None:
    repository = CsvCatalogueRepository(PROCESSED_DATA)
    engine = AdvisorEngine(
        CurricuPathService(repository, str(PROJECT_ROOT)),
        _GuessesModuleLookup(repository.data.aliases),
    )
    first = engine.advise("what electives can I take in fourth year")
    second = engine.advise(
        "Electrical Engineering (EFA03)",
        context=ConversationContext.from_dict(first["conversation_context"]),
    )

    assert second["status"] == "ok"
    assert second["programme_code"] == "EFA03"
    assert second["eligibility_summary"]["checked"] == 6


class _GuessesLookupForEverything:
    """A model that labels every short reply a module lookup, wrapping the offline parser."""

    def __init__(self, aliases) -> None:
        self._fallback = DeterministicIntentExtractor(aliases)

    def extract(self, text):
        parsed = self._fallback.extract(text)
        if len(text.split()) <= 3:
            return parsed.model_copy(update={"intent": "module_information"})
        return parsed


def _guarded_engine():
    repository = CsvCatalogueRepository(PROCESSED_DATA)
    return AdvisorEngine(
        CurricuPathService(repository, str(PROJECT_ROOT)),
        _GuessesLookupForEverything(repository.data.aliases),
    )


@pytest.mark.parametrize(
    ("first_message", "reply", "check"),
    [
        ("Can I take MATH1049A in EFA04?", "Completed", lambda r: r["decision"] == "eligible"),
        ("Can I take MATH1049A in EFA04?", "Not completed", lambda r: r["decision"] == "ineligible"),
        ("what electives can I take in fourth year", "EFA03", lambda r: r["programme_code"] == "EFA03" and r["status"] == "ok"),
        ("what electives can I take in fourth year", "IE", lambda r: r["programme_code"] == "EFA04" and r["status"] == "ok"),
    ],
)
def test_general_guard_keeps_answers_to_open_questions_whatever_a_model_guesses(first_message, reply, check) -> None:
    engine = _guarded_engine()
    first = engine.advise(first_message, module_history_confirmed=False)
    second = engine.advise(
        reply, context=ConversationContext.from_dict(first["conversation_context"]),
        module_history_confirmed=False,
    )

    assert first["status"] == "clarification_required"
    assert check(second)


def test_general_guard_does_not_swallow_a_new_request_made_while_a_question_is_open() -> None:
    engine = _engine()
    first = engine.advise("Can I take MATH1049A in EFA04?", module_history_confirmed=False)
    second = engine.advise(
        "Show the EFA04 year 4 electives",
        context=ConversationContext.from_dict(first["conversation_context"]),
        programme_code="EFA04",
    )

    assert second["intent"] == "curriculum_list"
    assert second["answer"].startswith("Found")


def test_general_guard_keeps_a_corequisite_status_reply_whatever_a_model_guesses() -> None:
    engine = _guarded_engine()
    kwargs = {"completed_modules": {"MATH2014A"}, "module_history_confirmed": False}
    first = engine.advise("Can I take ELEN3000A in EFA03?", **kwargs)
    second = engine.advise(
        "Planned concurrently",
        context=ConversationContext.from_dict(first["conversation_context"]),
        **kwargs,
    )

    assert first["status"] == "clarification_required"
    assert second["decision"] == "eligible"
    assert second["clarification_applied"]["state"] == "planned"


@pytest.mark.parametrize(
    "message",
    [
        "i would like to know which 4th year electives to pick for a Aeronautic Electrical?",
        "which electives should I pick to become a marine engineer?",
    ],
)
def test_an_unknown_career_is_named_and_not_answered_with_electives(message) -> None:
    result = _engine().advise(message, programme_code="EFA04")

    assert result["intent"] == "career_path"
    assert "don't have verified information" in result["answer"]
    assert "Electrical Engineering (EFA03):" in result["answer"]
    assert "Information Engineering (EFA04):" in result["answer"]
    assert not result.get("modules")


def test_a_known_career_still_gets_elective_matches() -> None:
    result = _engine().advise(
        "which 4th year electives should I pick for a career in software engineering?",
        programme_code="EFA04",
    )

    assert "career_unknown" not in result
    assert "ELEN4010A" in result["answer"]


@pytest.mark.parametrize(
    ("message", "programme", "expected"),
    [
        ("which electives to pick for a power engineer?", "EFA03", {"ELEN4003A", "ELEN4018A", "ELEN4023A"}),
        ("which 4th year electives should I pick to become a network engineer?", "EFA04", {"ELEN4017A"}),
        ("which electives should I pick to become a computer engineer?", "EFA03", set()),
    ],
)
def test_wits_careers_return_their_linked_electives_marked_as_proposed(message, programme, expected) -> None:
    result = _engine().advise(message, programme_code=programme)

    if result["intent"] == "module_recommendations":
        rows=result.get("recommendations",[])+result["unresolved_modules"]+result["interest_matches"]
        assert expected <= {m["course_code"] for m in rows}
        assert all(m["reasons"] and m["matched_tags"] for m in rows)
        assert all(m["eligibility"]["assessed"] for m in rows)
        return
    assert {m["course_code"] for m in result["modules"]} == expected
    assert "not been confirmed by the School" in result["answer"]
    assert result["career_subject"]["links_status"] == "developer_proposed"


def test_every_wits_career_has_a_link_row_for_its_programme() -> None:
    import csv as _csv

    links = {(r["programme_code"], r["wits_career"]) for r in _csv.DictReader(
        (PROCESSED_DATA / "wits_career_elective_links.csv").open(encoding="utf-8"))}
    profiles = _csv.DictReader((PROCESSED_DATA / "programme_profiles.csv").open(encoding="utf-8"))
    for profile in profiles:
        for career in profile["career_opportunities"].split(";"):
            assert (profile["programme_code"], career) in links
