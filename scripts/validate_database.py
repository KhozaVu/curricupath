"""Run the curriculum dataset audit from the command line."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DATA = PROJECT_ROOT / "data" / "processed"

sys.path.insert(0, str(PROJECT_ROOT))

from app.data.validators import ValidationReport, validate_processed_data


def main() -> None:
    """Print a concise audit report and fail with a non-zero exit on errors."""

    print("Curriculum datasets")
    print("-------------------")
    print(f"Sources: {_record_count('sources.csv'):>2}")
    print(f"Modules: {_record_count('modules.csv'):>2}")
    print(f"Rules:   {_record_count('rules.csv'):>2}\n")

    report = validate_processed_data(PROCESSED_DATA)
    _print_check("Module codes valid", report, {"INVALID_MODULE_CODE"})
    _print_check("Source references valid", report, {"UNKNOWN_SOURCE", "SOURCE_FILE_MISSING"})
    _print_check("Rule JSON valid", report, {"INVALID_CONDITION_JSON", "INVALID_CONDITION_SHAPE"})
    _print_check("Prerequisite references valid", report, {"UNKNOWN_RULE_TARGET"})
    _print_check("Corequisite references valid", report, {"UNKNOWN_RULE_TARGET"})
    _print_check("Selection groups valid", report, {"MISSING_SELECTION_RULE"})
    _print_check("No critical duplicates", report, {"DUPLICATE_MODULE_MEMBERSHIP", "DUPLICATE_SOURCE_ID"})

    print(f"\nErrors:   {len(report.errors)}")
    print(f"Warnings: {len(report.warnings)}")
    for warning in report.warnings:
        print(f"! [{warning.code}] {warning.message}")

    report.raise_for_errors()
    print("\nVALIDATION PASSED")


def _record_count(filename: str) -> int:
    with (PROCESSED_DATA / filename).open(newline="", encoding="utf-8") as csv_file:
        return sum(1 for _ in csv.DictReader(csv_file))


def _print_check(label: str, report: ValidationReport, codes: set[str]) -> None:
    failed = [issue for issue in report.errors if issue.code in codes]
    marker = "x" if failed else "OK"
    print(f"{marker} {label}")


if __name__ == "__main__":
    main()
