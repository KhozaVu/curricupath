"""Tests for curriculum dataset validation."""

from __future__ import annotations

import shutil
from pathlib import Path

from app.data.validators import validate_processed_data


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DATA = PROJECT_ROOT / "data" / "processed"


def test_initial_curriculum_data_has_no_errors() -> None:
    report = validate_processed_data(PROCESSED_DATA)

    assert report.is_valid
    assert not any(
        issue.code == "MISSING_EXTERNAL_REFERENCE_AUDIT" for issue in report.errors
    )


def test_duplicate_module_membership_is_an_error(tmp_path: Path) -> None:
    data_directory = tmp_path / "processed"
    shutil.copytree(PROCESSED_DATA, data_directory)
    modules_path = data_directory / "modules.csv"
    modules_path.write_text(
        modules_path.read_text(encoding="utf-8")
        + modules_path.read_text(encoding="utf-8").splitlines()[1]
        + "\n",
        encoding="utf-8",
    )

    report = validate_processed_data(data_directory)

    assert any(
        issue.code == "DUPLICATE_MODULE_MEMBERSHIP" for issue in report.errors
    )


def test_invalid_rule_json_is_an_error(tmp_path: Path) -> None:
    data_directory = tmp_path / "processed"
    shutil.copytree(PROCESSED_DATA, data_directory)
    rules_path = data_directory / "rules.csv"
    rules_path.write_text(
        rules_path.read_text(encoding="utf-8").replace(
            '"{""must_be_taken_with_target"":true,""required_for_target_credit"":true}"',
            '"not json"',
            1,
        ),
        encoding="utf-8",
    )

    report = validate_processed_data(data_directory)

    assert any(issue.code == "INVALID_CONDITION_JSON" for issue in report.errors)


def test_invalid_module_code_is_an_error(tmp_path: Path) -> None:
    data_directory = tmp_path / "processed"
    shutil.copytree(PROCESSED_DATA, data_directory)
    modules_path = data_directory / "modules.csv"
    modules_path.write_text(
        modules_path.read_text(encoding="utf-8").replace("CHEM1051A", "INVALID", 1),
        encoding="utf-8",
    )

    report = validate_processed_data(data_directory)

    assert any(issue.code == "INVALID_MODULE_CODE" for issue in report.errors)


def test_missing_module_column_is_a_validation_error(tmp_path: Path) -> None:
    data_directory = tmp_path / "processed"
    shutil.copytree(PROCESSED_DATA, data_directory)
    modules_path = data_directory / "modules.csv"
    modules_path.write_text(
        modules_path.read_text(encoding="utf-8").replace(
            "course_code", "module_code", 1
        ),
        encoding="utf-8",
    )

    report = validate_processed_data(data_directory)

    assert any(issue.code == "MISSING_COLUMN" for issue in report.errors)


def test_duplicate_rule_id_is_an_error(tmp_path: Path) -> None:
    data_directory = tmp_path / "processed"
    shutil.copytree(PROCESSED_DATA, data_directory)
    rules_path = data_directory / "rules.csv"
    content = rules_path.read_text(encoding="utf-8")
    rules_path.write_text(
        content + content.splitlines()[1] + "\n",
        encoding="utf-8",
    )

    report = validate_processed_data(data_directory)

    assert any(issue.code == "DUPLICATE_RULE_ID" for issue in report.errors)


def test_invalid_nqf_credits_is_an_error(tmp_path: Path) -> None:
    data_directory = tmp_path / "processed"
    shutil.copytree(PROCESSED_DATA, data_directory)
    modules_path = data_directory / "modules.csv"
    modules_path.write_text(
        modules_path.read_text(encoding="utf-8").replace(",12,5,", ",not-a-number,5,", 1),
        encoding="utf-8",
    )

    report = validate_processed_data(data_directory)

    assert any(issue.code == "INVALID_NQF_CREDITS" for issue in report.errors)


def test_invalid_source_verification_status_is_an_error(tmp_path: Path) -> None:
    data_directory = tmp_path / "processed"
    shutil.copytree(PROCESSED_DATA, data_directory)
    sources_path = data_directory / "sources.csv"
    sources_path.write_text(
        sources_path.read_text(encoding="utf-8").replace(
            ",verified,", ",unreviewed,", 1
        ),
        encoding="utf-8",
    )

    report = validate_processed_data(data_directory)

    assert any(
        issue.code == "INVALID_VERIFICATION_STATUS" for issue in report.errors
    )


def test_invalid_cbo_notional_hours_is_an_error(tmp_path: Path) -> None:
    data_directory = tmp_path / "processed"
    shutil.copytree(PROCESSED_DATA, data_directory)
    cbo_path = data_directory / "cbo_courses.csv"
    cbo_path.write_text(
        cbo_path.read_text(encoding="utf-8").replace(
            "ELEN2017A,2026,12,120,", "ELEN2017A,2026,12,12,", 1
        ),
        encoding="utf-8",
    )

    report = validate_processed_data(data_directory)

    assert any(issue.code == "INVALID_NOTIONAL_HOURS" for issue in report.errors)


def test_programme_profile_requires_verified_official_source(tmp_path: Path) -> None:
    data_directory = tmp_path / "processed"
    shutil.copytree(PROCESSED_DATA, data_directory)
    sources_path = data_directory / "sources.csv"
    sources_path.write_text(
        sources_path.read_text(encoding="utf-8").replace(
            "WITS_IE_COURSE_FINDER_2026,Wits Information Engineering undergraduate degree page,University of the Witwatersrand,2026,university_programme_page",
            "WITS_IE_COURSE_FINDER_2026,Wits Information Engineering undergraduate degree page,University of the Witwatersrand,2026,unverified_web_page",
            1,
        ),
        encoding="utf-8",
    )

    report = validate_processed_data(data_directory)

    assert any(
        issue.code == "INVALID_PROGRAMME_PROFILE_SOURCE" for issue in report.errors
    )
