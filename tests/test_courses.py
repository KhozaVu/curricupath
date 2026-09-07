"""Tests for the public course and rating dataset audit."""

from __future__ import annotations

import csv
import shutil
from pathlib import Path

from app.data.validators import validate_course_data


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DATA = PROJECT_ROOT / "data" / "processed"


def test_public_course_data_has_no_errors() -> None:
    report = validate_course_data(PROCESSED_DATA)

    assert report.is_valid


def test_week_two_course_coverage_requirements_are_met() -> None:
    with (PROCESSED_DATA / "courses.csv").open(newline="", encoding="utf-8") as csv_file:
        courses = list(csv.DictReader(csv_file))

    assert len(courses) >= 20
    assert len({course["provider"] for course in courses}) >= 3
    assert {course["category"] for course in courses} == {
        "programming_data_ai",
        "electronics_control",
        "communications",
        "career_skills",
    }
    assert {course["level"] for course in courses} == {"beginner", "intermediate"}


def test_every_course_has_an_audit_record() -> None:
    with (PROCESSED_DATA / "courses.csv").open(newline="", encoding="utf-8") as csv_file:
        course_ids = {row["course_id"] for row in csv.DictReader(csv_file)}
    with (PROCESSED_DATA / "course_audit.csv").open(
        newline="", encoding="utf-8"
    ) as csv_file:
        audited_course_ids = {row["course_id"] for row in csv.DictReader(csv_file)}

    assert audited_course_ids == course_ids


def test_unknown_course_source_is_an_error(tmp_path: Path) -> None:
    data_directory = tmp_path / "processed"
    shutil.copytree(PROCESSED_DATA, data_directory)
    courses_path = data_directory / "courses.csv"
    courses_path.write_text(
        courses_path.read_text(encoding="utf-8").replace("SRC_COUR_001", "SRC_UNKNOWN", 1),
        encoding="utf-8",
    )

    report = validate_course_data(data_directory)

    assert any(issue.code == "UNKNOWN_SOURCE" for issue in report.errors)


def test_invalid_rating_is_an_error(tmp_path: Path) -> None:
    data_directory = tmp_path / "processed"
    shutil.copytree(PROCESSED_DATA, data_directory)
    courses_path = data_directory / "courses.csv"
    courses_path.write_text(
        courses_path.read_text(encoding="utf-8").replace(",4.9,39316,5,", ",6.0,39316,5,", 1),
        encoding="utf-8",
    )

    report = validate_course_data(data_directory)

    assert any(issue.code == "INVALID_COURSE_RATING" for issue in report.errors)


def test_unverified_course_cannot_remain_recommendable(tmp_path: Path) -> None:
    data_directory = tmp_path / "processed"
    shutil.copytree(PROCESSED_DATA, data_directory)
    sources_path = data_directory / "sources.csv"
    sources_path.write_text(
        sources_path.read_text(encoding="utf-8").replace(
            ",verified,Coursera,Machine Learning Specialization; rating section,2026-09-07,",
            ",incomplete,Coursera,Machine Learning Specialization; rating section,2026-09-07,",
            1,
        ),
        encoding="utf-8",
    )

    report = validate_course_data(data_directory)

    assert any(
        issue.code == "UNSUPPORTED_RECOMMENDABLE_COURSE" for issue in report.errors
    )


def test_noncanonical_preference_tag_is_an_error(tmp_path: Path) -> None:
    data_directory = tmp_path / "processed"
    shutil.copytree(PROCESSED_DATA, data_directory)
    courses_path = data_directory / "courses.csv"
    courses_path.write_text(
        courses_path.read_text(encoding="utf-8").replace(
            "machine_learning;artificial_intelligence", "ML;artificial_intelligence", 1
        ),
        encoding="utf-8",
    )

    report = validate_course_data(data_directory)

    assert any(
        issue.code == "UNKNOWN_CONTROLLED_TAG" for issue in report.errors
    )
