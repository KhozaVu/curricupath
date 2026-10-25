"""School registration-reference prerequisite integration tests."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from app.backend import CurricuPathService
from app.data.repository import CsvCatalogueRepository


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CASE_PATH = (
    PROJECT_ROOT
    / "experiments"
    / "evaluation"
    / "test_set_v1"
    / "curricupath_test_set_v1.csv"
)


def _service(*, grid_enabled: bool) -> CurricuPathService:
    repository = CsvCatalogueRepository(PROJECT_ROOT / "data" / "processed")
    return CurricuPathService(
        repository,
        str(PROJECT_ROOT),
        school_grid_requirements_enabled=grid_enabled,
    )


def _case(case_id: str) -> dict[str, object]:
    with CASE_PATH.open(newline="", encoding="utf-8-sig") as case_file:
        row = next(row for row in csv.DictReader(case_file) if row["case_id"] == case_id)
    return {
        "target": row["target_course_code"],
        "profile": json.loads(row["student_profile_json"]),
    }


def _evaluate(service: CurricuPathService, case_id: str) -> dict[str, object]:
    case = _case(case_id)
    profile = case["profile"]
    assert isinstance(profile, dict)
    return service.eligibility(
        str(case["target"]),
        str(profile["programme_code"]),
        set(profile["completed_modules"]),
        set(profile["current_modules"]),
        set(profile["planned_modules"]),
        repeating_modules=set(profile["repeating_modules"]),
    )


@pytest.mark.parametrize(
    ("case_id", "missing_codes"),
    [
        ("TS095", {"MATH1043A", "PHYS1032A", "PHYS1033A"}),
        ("TS104", {"MATH1042A"}),
        ("TS121", {"MATH1042A", "PHYS1032A"}),
    ],
)
def test_school_grid_gate_rejects_exact_unsafe_test_profiles(
    case_id: str, missing_codes: set[str]
) -> None:
    result = _evaluate(_service(grid_enabled=True), case_id)

    assert result["decision"] == "ineligible"
    assert all(any(code in reason for reason in result["reasons"]) for code in missing_codes)
    assert all("EIE_REG_GRID_2026, sheet 'EE YOS 2'" in reason for reason in result["reasons"])
    if case_id == "TS104":
        assert result["reasons"] == [
            "PRE_ELEN2003: MATH1042A is required before ELEN2003A and is not listed as "
            "completed (EIE_REG_GRID_2026, sheet 'EE YOS 2'; EBE_2026 p.80)."
        ]


def test_school_grid_gate_accepts_profile_that_satisfies_phys2007_requirements() -> None:
    result = _service(grid_enabled=True).eligibility(
        "PHYS2007A",
        "EFA03",
        {"MATH1042A", "MATH1043A", "PHYS1032A", "PHYS1033A"},
        set(),
        set(),
    )

    assert result["decision"] == "eligible"


@pytest.mark.parametrize("case_id, expected", [("TS095", "ineligible"), ("TS104", "eligible"), ("TS121", "ineligible")])
def test_faculty_rules_apply_even_without_grid(case_id: str, expected: str) -> None:
    # Physics II now has its Faculty prerequisites even when the grid is disabled.
    result = _evaluate(_service(grid_enabled=False), case_id)
    assert result["decision"] == expected


def test_math1048_completion_is_not_rewritten_as_math1042_student_fact() -> None:
    result = _service(grid_enabled=True).eligibility(
        "ELEN2003A",
        "EFA04",
        {"ELEN2017A", "MATH1043A", "MATH1048A", "PHYS1032A", "PHYS1033A"},
        set(),
        {"MATH1042A", "MATH1049A"},
    )

    assert result["decision"] == "ineligible"
    assert "MATH1042A is required" in result["reasons"][0]


def test_explicitly_empty_grid_requirement_replaces_handbook_requirement() -> None:
    # TS010 is eligible under the School grid because ELEN3017A has no grid prerequisite;
    # the handbook's all-third-year rule made the previous engine reject it.
    assert _evaluate(_service(grid_enabled=False), "TS010")["decision"] == "ineligible"
    assert _evaluate(_service(grid_enabled=True), "TS010")["decision"] == "eligible"
