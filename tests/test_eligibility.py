"""Tests for deterministic curriculum eligibility gates."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from app.advisor.eligibility import (
    StudentProfile,
    check_eligibility,
    evaluate_requirement,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DATA = PROJECT_ROOT / "data" / "processed"


def _load_csv(filename: str) -> list[dict[str, str]]:
    with (PROCESSED_DATA / filename).open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


MODULES = _load_csv("modules.csv")
RULES = _load_csv("rules.csv")
SOURCES = _load_csv("sources.csv")


def _profile(
    programme_code: str,
    completed: set[str] | None = None,
    current: set[str] | None = None,
    planned: set[str] | None = None,
    module_states: dict[str, str] | None = None,
    module_history_confirmed: bool | None = None,
) -> StudentProfile:
    return StudentProfile(
        programme_code=programme_code,
        completed_modules=frozenset(completed or set()),
        current_modules=frozenset(current or set()),
        planned_modules=frozenset(planned or set()),
        module_states=module_states,
        module_history_confirmed=module_history_confirmed,
    )


def _check(course_code: str, profile: StudentProfile):
    return check_eligibility(
        course_code,
        profile,
        MODULES,
        RULES,
        SOURCES,
        source_root=PROJECT_ROOT,
    )


def test_ie_student_cannot_take_ee_only_elective() -> None:
    result = _check("ELEN4001A", _profile("EFA04"))

    assert result.eligible is False
    assert result.reasons == ("ELEN4001A is not part of programme EFA04.",)


def test_missing_prerequisite_blocks_module() -> None:
    result = _check("ELEN4001A", _profile("EFA03"))

    assert result.eligible is False
    assert result.reasons == ("Prerequisite rule PRE_ELEN4001 is not satisfied.",)


def test_unconfirmed_history_routes_unknown_prerequisite_to_clarification() -> None:
    result = _check(
        "MATH1049A",
        _profile("EFA04", module_history_confirmed=False),
    )

    assert result.decision == "needs_clarification"
    assert result.unresolved_predicates == ("MATH1048A",)


def test_confirmed_history_treats_absent_prerequisite_as_not_completed() -> None:
    result = _check(
        "MATH1049A",
        _profile("EFA04", module_history_confirmed=True),
    )

    assert result.decision == "ineligible"
    assert result.unresolved_predicates == ()


def test_explicit_not_completed_fact_is_definitive() -> None:
    result = _check(
        "MATH1049A",
        _profile(
            "EFA04",
            module_states={"math1048a": "not_completed"},
            module_history_confirmed=False,
        ),
    )

    assert result.decision == "ineligible"


def test_profile_rejects_conflicting_module_states() -> None:
    with pytest.raises(ValueError, match="cannot be both completed and current"):
        _profile(
            "EFA04",
            completed={"ELEN2017A"},
            module_states={"ELEN2017A": "current"},
        )


def test_recursive_all_of_is_definitively_false_when_one_fact_is_false() -> None:
    states = {"ELEN3000A": "not_completed", "MATH3025A": "unknown"}

    result = evaluate_requirement(
        {"all_of": ["ELEN3000A", "MATH3025A"]},
        lambda code: states[code],
        frozenset({"completed"}),
    )

    assert result.status == "unsatisfied"
    assert result.unsatisfied_predicates == ("ELEN3000A",)
    assert result.unresolved_predicates == ()


def test_recursive_any_of_is_true_when_one_known_alternative_passes() -> None:
    states = {"ELEN3000A": "completed", "MATH3025A": "unknown"}

    result = evaluate_requirement(
        {"any_of": ["ELEN3000A", "MATH3025A"]},
        lambda code: states[code],
        frozenset({"completed"}),
    )

    assert result.status == "satisfied"
    assert result.unresolved_predicates == ()


def test_recursive_any_of_selects_smallest_unknown_branch() -> None:
    result = evaluate_requirement(
        {
            "any_of": [
                {"all_of": ["ELEN3000A", "MATH3025A"]},
                "APPM3021A",
            ]
        },
        lambda _code: "unknown",
        frozenset({"completed"}),
    )

    assert result.status == "unknown"
    assert result.unresolved_predicates == ("APPM3021A",)


def test_recursive_evaluator_rejects_unsupported_condition_shape() -> None:
    result = evaluate_requirement(
        {"some_of": ["ELEN3000A"]},
        lambda _code: "unknown",
        frozenset({"completed"}),
    )

    assert result.status == "invalid"
    assert result.error is not None


def test_clarification_payload_targets_first_material_unknown_fact() -> None:
    result = _check(
        "MATH1049A",
        _profile("EFA04", module_history_confirmed=False),
    )

    assert result.clarification == {
        "reason": "Prerequisite rule PRE_MATH1049 is not satisfied.",
        "unresolved_predicates": ["MATH1048A"],
        "target_predicate": "MATH1048A",
        "question": "Have you completed MATH1048A?",
        "options": ["Completed", "Not completed"],
    }


def test_valid_programme_and_prerequisites_allow_module() -> None:
    result = _check(
        "ELEN4001A",
        _profile("EFA03", completed={"ELEN3000A", "MATH3025A"}),
    )

    assert result == check_eligibility(
        "ELEN4001A",
        _profile("EFA03", completed={"ELEN3000A", "MATH3025A"}),
        MODULES,
        RULES,
        SOURCES,
        source_root=PROJECT_ROOT,
    )
    assert result.eligible is True


def test_all_programme_year_courses_satisfy_measurement_prerequisite() -> None:
    for programme_code in ("EFA03", "EFA04"):
        completed = {
            row["course_code"]
            for row in MODULES
            if row["programme_code"] == programme_code
            and row["year_of_study"] == "3"
        }

        result = _check("ELEN4006A", _profile(programme_code, completed=completed))

        assert result.eligible is True


def test_missing_programme_year_course_blocks_measurement_prerequisite() -> None:
    completed = {
        row["course_code"]
        for row in MODULES
        if row["programme_code"] == "EFA04" and row["year_of_study"] == "3"
    }
    completed.remove("ELEN3024A")

    result = _check("ELEN4006A", _profile("EFA04", completed=completed))

    assert result.eligible is False
    assert result.reasons == (
        "Prerequisite rule PRE_ELEN4006_EFA04 is not satisfied.",
    )


def test_planned_corequisite_allows_module() -> None:
    result = _check(
        "ELEN3000A",
        _profile("EFA03", completed={"MATH2014A"}, planned={"MATH3025A"}),
    )

    assert result.eligible is True


def test_missing_corequisite_needs_clarification() -> None:
    result = _check("ELEN3000A", _profile("EFA03", completed={"MATH2014A"}))

    assert result.eligible is False
    assert result.needs_clarification is True
    assert result.decision == "needs_clarification"
    assert result.manual_review_required is False
    assert result.reasons == ("Corequisite rule CORE_ELEN3000 is not satisfied.",)
    assert result.rule_trace[-1].gate == "corequisite"
    assert result.clarification is not None


def test_excluded_combination_is_rejected() -> None:
    exclusion_rule = {
        "rule_id": "EXCLUSION_TEST",
        "scope": "EFA03",
        "rule_type": "exclusion",
        "target_course_code": "ELEN4001A",
        "condition_json": '{"all_of": ["ELEN3000A"]}',
        "source_id": "EBE_2026",
    }
    result = check_eligibility(
        "ELEN4001A",
        _profile("EFA03", completed={"ELEN3000A", "MATH3025A"}),
        MODULES,
        [*RULES, exclusion_rule],
        SOURCES,
        source_root=PROJECT_ROOT,
    )

    assert result.eligible is False
    assert result.reasons == ("Excluded by rule EXCLUSION_TEST.",)


def test_missing_source_rejects_candidate() -> None:
    modules = [
        {
            **row,
            "source_id": "MISSING_SOURCE",
        }
        if row["course_code"] == "ELEN4001A"
        else row
        for row in MODULES
    ]
    result = check_eligibility(
        "ELEN4001A",
        _profile("EFA03", completed={"ELEN3000A", "MATH3025A"}),
        modules,
        RULES,
        SOURCES,
        source_root=PROJECT_ROOT,
    )

    assert result.eligible is False
    assert result.decision == "manual_review_required"
    assert result.manual_review_required is True
    assert result.reasons == ("Source MISSING_SOURCE is not registered.",)


def test_unverified_source_rejects_candidate() -> None:
    sources = [
        {**source, "verification_status": "incomplete"}
        if source["source_id"] == "EBE_2026"
        else source
        for source in SOURCES
    ]
    result = check_eligibility(
        "ELEN4001A",
        _profile("EFA03", completed={"ELEN3000A", "MATH3025A"}),
        MODULES,
        RULES,
        sources,
        source_root=PROJECT_ROOT,
    )

    assert result.eligible is False
    assert result.decision == "manual_review_required"
    assert result.manual_review_required is True
    assert result.reasons == ("Source EBE_2026 is not verified.",)


def test_deterministic_outcomes_expose_explicit_decisions() -> None:
    eligible = _check(
        "ELEN4001A",
        _profile("EFA03", completed={"ELEN3000A", "MATH3025A"}),
    )
    ineligible = _check("ELEN4001A", _profile("EFA04"))

    assert eligible.decision == "eligible"
    assert ineligible.decision == "ineligible"
    assert eligible.needs_clarification is False
    assert ineligible.manual_review_required is False


def test_declared_academic_discretion_requires_manual_review() -> None:
    profile = StudentProfile(
        programme_code="EFA04",
        completed_modules=frozenset(),
        current_modules=frozenset(),
        planned_modules=frozenset(),
        manual_review_reasons=(
            "Transfer-credit recognition requires academic review.",
        ),
    )

    result = _check("ELEN4025A", profile)

    assert result.decision == "manual_review_required"
    assert result.manual_review_required is True
    assert result.reasons == profile.manual_review_reasons
