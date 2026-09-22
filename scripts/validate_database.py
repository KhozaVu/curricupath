"""Run the curriculum dataset audit from the command line."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DATA = PROJECT_ROOT / "data" / "processed"

sys.path.insert(0, str(PROJECT_ROOT))

from app.data.validators import (
    ValidationReport,
    validate_course_data,
    validate_processed_data,
)


def main() -> None:
    """Print a concise audit report and fail with a non-zero exit on errors."""

    print("Curriculum and public-course datasets")
    print("------------------------------------")
    print(f"Sources: {_record_count('sources.csv'):>2}")
    print(f"Modules: {_record_count('modules.csv'):>2}")
    print(f"Rules:   {_record_count('rules.csv'):>2}")
    print(f"Courses: {_record_count('courses.csv'):>2}")
    print(f"CBO rows:{_record_count('cbo_courses.csv'):>3}")
    print(f"Missing CBOs: {_record_count('missing_cbos.csv'):>2}")
    print(f"Programme profiles: {_record_count('programme_profiles.csv'):>2}\n")

    curriculum_report = validate_processed_data(PROCESSED_DATA)
    course_report = validate_course_data(PROCESSED_DATA)
    reports = (curriculum_report, course_report)
    _print_check("Module codes valid", reports, {"INVALID_MODULE_CODE"})
    _print_check("Source references valid", reports, {"UNKNOWN_SOURCE", "SOURCE_FILE_MISSING", "MISSING_SOURCE_REFERENCE"})
    _print_check("Rule JSON valid", reports, {"INVALID_CONDITION_JSON", "INVALID_CONDITION_SHAPE"})
    _print_check("Prerequisite references valid", reports, {"UNKNOWN_RULE_TARGET"})
    _print_check("Corequisite references valid", reports, {"UNKNOWN_RULE_TARGET"})
    _print_check("Selection groups valid", reports, {"MISSING_SELECTION_RULE"})
    _print_check("Course ratings valid", reports, {"INVALID_COURSE_RATING"})
    _print_check("CBO source and credit data valid", reports, {"UNKNOWN_CBO_MODULE", "INVALID_CBO_SOURCE", "CBO_CREDIT_MISMATCH", "INVALID_NOTIONAL_HOURS"})
    _print_check("Missing CBO register complete", reports, {"UNTRACKED_MISSING_CBO", "STALE_MISSING_CBO", "CBO_COVERAGE_CONFLICT"})
    _print_check("Programme profiles source-verified", reports, {"UNKNOWN_PROGRAMME_PROFILE", "INVALID_PROGRAMME_PROFILE_SOURCE", "UNKNOWN_SOURCE"})
    _print_check("No critical duplicates", reports, {"DUPLICATE_MODULE_MEMBERSHIP", "DUPLICATE_SOURCE_ID", "DUPLICATE_COURSE_ID"})

    issues = tuple(issue for report in reports for issue in report.issues)
    errors = tuple(issue for issue in issues if issue.severity == "error")
    warnings = tuple(issue for issue in issues if issue.severity == "warning")
    print(f"\nErrors:   {len(errors)}")
    print(f"Warnings: {len(warnings)}")
    for warning in warnings:
        print(f"! [{warning.code}] {warning.message}")

    if errors:
        details = "\n".join(f"[{issue.code}] {issue.message}" for issue in errors)
        raise ValueError(f"Dataset validation failed:\n{details}")
    print("\nVALIDATION PASSED")


def _record_count(filename: str) -> int:
    with (PROCESSED_DATA / filename).open(newline="", encoding="utf-8") as csv_file:
        return sum(1 for _ in csv.DictReader(csv_file))


def _print_check(
    label: str, reports: tuple[ValidationReport, ...], codes: set[str]
) -> None:
    failed = [
        issue
        for report in reports
        for issue in report.errors
        if issue.code in codes
    ]
    marker = "x" if failed else "OK"
    print(f"{marker} {label}")


if __name__ == "__main__":
    main()
