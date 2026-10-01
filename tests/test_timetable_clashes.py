"""Synthetic tests for the School registration-reference timetable-clash gate."""

from __future__ import annotations

import json
from pathlib import Path

from app.advisor.eligibility import StudentProfile, check_eligibility, load_clash_rules


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _profile(*repeating: str) -> StudentProfile:
    return StudentProfile(
        programme_code="EFA03",
        completed_modules=frozenset(),
        current_modules=frozenset(),
        planned_modules=frozenset(),
        repeating_modules=frozenset(repeating),
    )


def _module(course_code: str) -> dict[str, str]:
    return {
        "programme_code": "EFA03",
        "course_code": course_code,
        "year_of_study": "3",
        "source_id": "SRC_TEST",
    }


def _source() -> dict[str, str]:
    return {
        "source_id": "SRC_TEST",
        "title": "Synthetic eligibility source",
        "verification_status": "verified",
        "url": "https://example.test/source",
        "local_path": "",
    }


def _clash(
    repeating: str,
    target: str,
    clash_type: str,
    *,
    source_ids: str = "EIE_PLANNER_2026;EIE_REG_GRID_2026",
    sheet: str = "EIE_PLANNER_2026:EE YOS 2;EIE_REG_GRID_2026:EE YOS 2",
) -> dict[str, str]:
    return {
        "rule_id": f"CLASH_{repeating}_{target}",
        "scope": "EFA03",
        "rule_type": "timetable_clash",
        "repeating_course": repeating,
        "target_course_code": target,
        "clash_type": clash_type,
        "source_ids": source_ids,
        "sheet": sheet,
    }


def _check(
    target: str,
    profile: StudentProfile,
    *,
    clash_rules: tuple[dict[str, str], ...] = (),
    rules: tuple[dict[str, str], ...] = (),
    enabled: bool = True,
):
    return check_eligibility(
        target,
        profile,
        [_module(target)],
        rules,
        [_source()],
        clash_rules=clash_rules,
        enable_timetable_clashes=enabled,
    )


def test_lecture_clash_with_repeated_module_is_ineligible() -> None:
    result = _check(
        "ELEN3000A",
        _profile("ELEN2003A"),
        clash_rules=(_clash("ELEN2003A", "ELEN3000A", "LEC"),),
    )

    assert result.decision == "ineligible"
    assert result.reasons == (
        "CLASH_ELEN2003A_ELEN3000A: ELEN3000A has a lecture timetable clash "
        "with ELEN2003A, which the student is repeating, so it cannot be taken "
        "(EIE_PLANNER_2026, sheet 'EE YOS 2'; EIE_REG_GRID_2026).",
    )


def test_text_only_unspecified_clash_and_missing_suffix_are_supported() -> None:
    result = _check(
        "ELEN3003A",
        _profile("ELEN2017"),
        clash_rules=(
            _clash(
                "ELEN2017A",
                "ELEN3003A",
                "UNSPECIFIED",
                source_ids="EIE_REG_GRID_2026",
                sheet="EIE_REG_GRID_2026:EE YOS 2",
            ),
        ),
    )

    assert result.decision == "ineligible"
    assert "has a timetable clash with ELEN2017A" in result.reasons[0]


def test_non_clashing_repeat_reports_prerequisite_only() -> None:
    prerequisite = {
        "rule_id": "PRE_ELEN3002",
        "scope": "EFA03",
        "rule_type": "prerequisite",
        "target_course_code": "ELEN3002A",
        "condition_json": json.dumps({"all_of": ["ELEN2005A"]}),
        "source_id": "SRC_TEST",
    }
    result = _check(
        "ELEN3002A",
        _profile("ELEN2005A"),
        rules=(prerequisite,),
    )

    assert result.decision == "ineligible"
    assert result.reasons == ("Prerequisite rule PRE_ELEN3002 is not satisfied.",)
    assert all("CLASH_" not in reason for reason in result.reasons)


def test_no_repeating_modules_leaves_clash_gate_silent() -> None:
    result = _check(
        "ELEN3000A",
        _profile(),
        clash_rules=(_clash("ELEN2003A", "ELEN3000A", "LEC"),),
    )

    assert result.decision == "eligible"
    assert result.reasons == ()


def test_feature_flag_off_preserves_previous_eligibility_path() -> None:
    result = _check(
        "ELEN3000A",
        _profile("ELEN2003A"),
        clash_rules=(_clash("ELEN2003A", "ELEN3000A", "LEC"),),
        enabled=False,
    )

    assert result.decision == "eligible"


def test_clash_and_prerequisite_failures_are_both_reported() -> None:
    prerequisite = {
        "rule_id": "PRE_ELEN3000",
        "scope": "EFA03",
        "rule_type": "prerequisite",
        "target_course_code": "ELEN3000A",
        "condition_json": json.dumps({"all_of": ["MATH2014A"]}),
        "source_id": "SRC_TEST",
    }
    result = _check(
        "ELEN3000A",
        _profile("ELEN2003A"),
        clash_rules=(_clash("ELEN2003A", "ELEN3000A", "LEC"),),
        rules=(prerequisite,),
    )

    assert result.decision == "ineligible"
    assert len(result.reasons) == 2
    assert result.reasons[0] == "Prerequisite rule PRE_ELEN3000 is not satisfied."
    assert result.reasons[1].startswith("CLASH_ELEN2003A_ELEN3000A:")


def test_generated_rules_include_known_text_only_pair() -> None:
    rules = load_clash_rules(PROJECT_ROOT / "data" / "rules" / "grid_clash_rules.csv")

    assert len(rules) == 52
    known = next(
        rule
        for rule in rules
        if rule["repeating_course"] == "ELEN2017A"
        and rule["target_course_code"] == "ELEN3003A"
    )
    assert known["agreement"] == "text_only"
    assert known["clash_type"] == "UNSPECIFIED"
