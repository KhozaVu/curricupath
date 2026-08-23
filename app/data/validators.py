"""Validation for the source-cited curriculum CSV datasets."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path


COURSE_CODE_PATTERN = re.compile(r"^[A-Z]{4}\d{4}A?$")
REQUIRED_DATASETS = ("sources.csv", "modules.csv", "rules.csv")


@dataclass(frozen=True)
class ValidationIssue:
    """A single validation result with a stable machine-readable code."""

    severity: str
    code: str
    message: str


@dataclass(frozen=True)
class ValidationReport:
    """The complete result of auditing a processed curriculum dataset."""

    issues: tuple[ValidationIssue, ...]

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def raise_for_errors(self) -> None:
        if self.errors:
            details = "\n".join(
                f"[{issue.code}] {issue.message}" for issue in self.errors
            )
            raise ValueError(f"Curriculum data validation failed:\n{details}")


def validate_processed_data(data_directory: Path | str) -> ValidationReport:
    """Audit the CSV data required before curriculum eligibility is evaluated."""

    processed_directory = Path(data_directory)
    datasets = {
        filename: _load_csv(processed_directory / filename)
        for filename in REQUIRED_DATASETS
    }
    issues: list[ValidationIssue] = []

    sources = datasets["sources.csv"]
    modules = datasets["modules.csv"]
    rules = datasets["rules.csv"]
    source_ids = {row["source_id"] for row in sources}
    module_codes = {row["course_code"] for row in modules}

    for source in sources:
        source_path = processed_directory.parent.parent / source["local_path"]
        if not source_path.exists():
            issues.append(
                ValidationIssue(
                    "warning",
                    "SOURCE_FILE_MISSING",
                    f"{source['source_id']} is not available at {source_path}.",
                )
            )

    module_keys: set[tuple[str, str, str]] = set()
    selection_groups: set[str] = set()
    for module in modules:
        key = (
            module["programme_code"],
            module["course_code"],
            module["year_of_study"],
        )
        if key in module_keys:
            issues.append(
                ValidationIssue(
                    "error",
                    "DUPLICATE_MODULE_MEMBERSHIP",
                    "Duplicate programme/course/year membership: "
                    f"{'/'.join(key)}.",
                )
            )
        module_keys.add(key)
        if module["source_id"] not in source_ids:
            issues.append(_unknown_source_issue("module", module["course_code"], module["source_id"]))
        if module["selection_group"]:
            selection_groups.add(module["selection_group"])

    selection_rules: set[str] = set()
    for rule in rules:
        if rule["source_id"] not in source_ids:
            issues.append(_unknown_source_issue("rule", rule["rule_id"], rule["source_id"]))

        condition = _parse_condition(rule, issues)
        if condition is None:
            continue

        if rule["rule_type"] in {"prerequisite", "corequisite"}:
            target = rule["target_course_code"]
            if target not in module_codes:
                issues.append(
                    ValidationIssue(
                        "error",
                        "UNKNOWN_RULE_TARGET",
                        f"{rule['rule_id']} targets {target}, which is not in modules.csv.",
                    )
                )

            for course_code in _referenced_course_codes(condition):
                if course_code not in module_codes:
                    issues.append(
                        ValidationIssue(
                            "warning",
                            "EXTERNAL_COURSE_REFERENCE",
                            f"{rule['rule_id']} references {course_code}, outside the "
                            "current EFA03/EFA04 module memberships.",
                        )
                    )

        if rule["rule_type"] == "selection_count":
            group = condition.get("selection_group")
            if isinstance(group, str):
                selection_rules.add(group)

    for group in sorted(selection_groups - selection_rules):
        issues.append(
            ValidationIssue(
                "error",
                "MISSING_SELECTION_RULE",
                f"Selection group {group} has no selection_count rule.",
            )
        )

    return ValidationReport(tuple(issues))


def _load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Required curriculum dataset is missing: {path}")

    with path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def _parse_condition(
    rule: dict[str, str], issues: list[ValidationIssue]
) -> dict[str, object] | None:
    try:
        condition = json.loads(rule["condition_json"])
    except json.JSONDecodeError as error:
        issues.append(
            ValidationIssue(
                "error",
                "INVALID_CONDITION_JSON",
                f"{rule['rule_id']} has invalid condition_json: {error.msg}.",
            )
        )
        return None

    if not isinstance(condition, dict):
        issues.append(
            ValidationIssue(
                "error",
                "INVALID_CONDITION_SHAPE",
                f"{rule['rule_id']} condition_json must decode to an object.",
            )
        )
        return None
    return condition


def _referenced_course_codes(value: object) -> set[str]:
    if isinstance(value, str):
        return {value} if COURSE_CODE_PATTERN.fullmatch(value) else set()
    if isinstance(value, list):
        return set().union(*(_referenced_course_codes(item) for item in value))
    if isinstance(value, dict):
        return set().union(*(_referenced_course_codes(item) for item in value.values()))
    return set()


def _unknown_source_issue(
    record_type: str, record_id: str, source_id: str
) -> ValidationIssue:
    return ValidationIssue(
        "error",
        "UNKNOWN_SOURCE",
        f"{record_type} {record_id} references missing source_id {source_id}.",
    )
