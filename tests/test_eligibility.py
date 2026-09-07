"""Tests for deterministic curriculum eligibility gates."""

from __future__ import annotations

import csv
from pathlib import Path

from app.advisor.eligibility import StudentProfile, check_eligibility


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
) -> StudentProfile:
    return StudentProfile(
        programme_code=programme_code,
        completed_modules=frozenset(completed or set()),
        current_modules=frozenset(current or set()),
        planned_modules=frozenset(planned or set()),
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
    assert result.reasons == ("Corequisite rule CORE_ELEN3000 is not satisfied.",)


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
    assert result.reasons == ("Source MISSING_SOURCE is not registered.",)
