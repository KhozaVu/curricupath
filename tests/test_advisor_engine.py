"""End-to-end tests for the deterministic CSV-backed advisor engine."""

from __future__ import annotations

from pathlib import Path

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


def test_advisor_ranks_verified_electric_circuit_courses() -> None:
    result = _engine().advise("I want an electric circuits course")

    assert result["status"] == "ok"
    assert result["recommendations"]
    assert all(
        "electric_circuits" in course["interest_tags"]
        for course in result["recommendations"]
    )
    assert all(course["score"] > 0 for course in result["recommendations"])


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


def test_advisor_can_add_semantic_matching_without_replacing_fixed_scoring() -> None:
    result = _engine(FakeSemanticMatcher()).advise(
        "I want an electric circuits course"
    )

    assert result["matching_mode"] == "hybrid_semantic"
    assert all(
        course["score_components"]["semantic"] == 0.8
        for course in result["recommendations"]
    )


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
    assert len(result["recommendations"]) == 3
    assert result["recommendations"][0]["course_code"] == "ELEN4025A"
    assert {
        item["course_code"] for item in result["recommendations"][1:]
    } == {"ELEN4010A", "ELEN4020A"}
    assert result["recommendations"][0]["matched_tags"] == ["machine_learning"]
    assert result["recommendations"][0]["eligibility"]["assessed"] is False


def test_natural_elective_interest_question_uses_profile_programme() -> None:
    result = _engine().advise(
        "What electives can I take if I'm interested in machine learning?",
        programme_code="EFA04",
        context=ConversationContext(pending_intent="eligibility"),
    )

    assert result["intent"] == "curriculum_list"
    assert result["status"] == "ok"
    assert result["programme_code"] == "EFA04"
    assert result["year_of_study"] == 4
    assert result["recommendations"][0]["course_code"] == "ELEN4025A"


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
    assert result["recommendations"][0]["course_code"] == "ELEN4023A"
    assert all(
        item["programme_code"] == "EFA03"
        and item["year_of_study"] == 4
        and item["requirement_type"] == "elective_pool"
        for item in result["recommendations"]
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
    assert result["recommendation_kind"] == "interest_suggestions"
    assert len(result["recommendations"]) == 3
    assert result["recommendations"][0]["course_code"] == "ELEN4025A"
    assert all(
        item["eligibility"]["assessed"] is True
        and item["eligibility"]["eligible"] is False
        for item in result["recommendations"]
    )
    assert "none currently pass all declared eligibility rules" in result["answer"]


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


def test_one_clarification_limit_stops_when_another_fact_is_unknown() -> None:
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

    assert first["clarification_question"] == "Have you completed ELEN3000A?"
    assert second["status"] == "clarification_unresolved"
    assert second["clarification_exhausted"] is True
    assert second["clarification_question"] is None
    assert "clarification limit" in second["answer"]


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

    assert result["intent"] == "public_course_search"
    assert result["recommendations"]


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
