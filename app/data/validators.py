"""Validation for the source-cited curriculum CSV datasets."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path


COURSE_CODE_PATTERN = re.compile(r"^[A-Z]{4}\d{4}A?$")
PROGRAMME_CODE_PATTERN = re.compile(r"^EFA\d{2}$")
REQUIRED_DATASETS = ("sources.csv", "modules.csv", "rules.csv")
MODULE_REQUIREMENT_TYPES = {"compulsory", "elective_pool", "required_non_credit"}
RULE_TYPES = {
    "corequisite",
    "definition",
    "exclusion",
    "prerequisite",
    "programme_definition",
    "programme_selection",
    "progression",
    "selection_count",
}
SOURCE_REQUIRED_FIELDS = ("source_id", "title", "edition_year", "document_type", "local_path")
MODULE_REQUIRED_FIELDS = (
    "programme_code",
    "programme_name",
    "year_of_study",
    "course_code",
    "course_name",
    "nqf_credits",
    "nqf_level",
    "requirement_type",
    "source_id",
    "handbook_page",
)
RULE_REQUIRED_FIELDS = ("rule_id", "scope", "rule_type", "condition_json", "source_id", "handbook_page")


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
    _validate_sources(sources, processed_directory, issues)

    source_ids = {row["source_id"] for row in sources}
    module_codes = {row["course_code"] for row in modules}
    programme_codes = _programme_codes(rules, issues)

    module_keys: set[tuple[str, str, str]] = set()
    selection_groups: set[str] = set()
    for module in modules:
        _validate_required_fields("module", module["course_code"], module, MODULE_REQUIRED_FIELDS, issues)
        _validate_module(module, programme_codes, issues)
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
        _validate_required_fields("rule", rule["rule_id"], rule, RULE_REQUIRED_FIELDS, issues)
        if rule["rule_type"] not in RULE_TYPES:
            issues.append(
                ValidationIssue(
                    "error",
                    "INVALID_RULE_TYPE",
                    f"Rule {rule['rule_id']} has invalid rule_type {rule['rule_type']}.",
                )
            )
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


def _validate_sources(
    sources: list[dict[str, str]],
    processed_directory: Path,
    issues: list[ValidationIssue],
) -> None:
    source_ids: set[str] = set()
    for source in sources:
        source_id = source.get("source_id", "")
        _validate_required_fields("source", source_id, source, SOURCE_REQUIRED_FIELDS, issues)
        if source_id in source_ids:
            issues.append(
                ValidationIssue(
                    "error",
                    "DUPLICATE_SOURCE_ID",
                    f"Duplicate source_id {source_id}.",
                )
            )
        source_ids.add(source_id)

        if not source.get("edition_year", "").isdigit():
            issues.append(
                ValidationIssue(
                    "error",
                    "INVALID_SOURCE_YEAR",
                    f"Source {source_id} must have a numeric edition_year.",
                )
            )

        source_path = processed_directory.parent.parent / source.get("local_path", "")
        if not source_path.exists():
            issues.append(
                ValidationIssue(
                    "error",
                    "SOURCE_FILE_MISSING",
                    f"{source_id} is not available at {source_path}.",
                )
            )


def _programme_codes(
    rules: list[dict[str, str]], issues: list[ValidationIssue]
) -> set[str]:
    programmes: set[str] = set()
    for rule in rules:
        if rule.get("rule_type") != "programme_definition":
            continue
        programme_code = rule.get("scope", "")
        if not PROGRAMME_CODE_PATTERN.fullmatch(programme_code):
            issues.append(
                ValidationIssue(
                    "error",
                    "INVALID_PROGRAMME_DEFINITION",
                    f"Rule {rule.get('rule_id', '')} has invalid programme code "
                    f"{programme_code}.",
                )
            )
            continue
        programmes.add(programme_code)
    return programmes


def _validate_module(
    module: dict[str, str],
    programme_codes: set[str],
    issues: list[ValidationIssue],
) -> None:
    course_code = module["course_code"]
    if not COURSE_CODE_PATTERN.fullmatch(course_code):
        issues.append(
            ValidationIssue(
                "error",
                "INVALID_MODULE_CODE",
                f"Module code {course_code!r} is invalid.",
            )
        )

    programme_code = module["programme_code"]
    if programme_code not in programme_codes:
        issues.append(
            ValidationIssue(
                "error",
                "INVALID_PROGRAMME_CODE",
                f"Module {course_code} has unknown programme_code {programme_code}.",
            )
        )

    try:
        year = int(module["year_of_study"])
    except ValueError:
        year = 0
    if year not in {1, 2, 3, 4}:
        issues.append(
            ValidationIssue(
                "error",
                "INVALID_YEAR_OF_STUDY",
                f"Module {course_code} has invalid year_of_study "
                f"{module['year_of_study']!r}.",
            )
        )

    if module["requirement_type"] not in MODULE_REQUIREMENT_TYPES:
        issues.append(
            ValidationIssue(
                "error",
                "INVALID_REQUIREMENT_TYPE",
                f"Module {course_code} has invalid requirement_type "
                f"{module['requirement_type']!r}.",
            )
        )


def _validate_required_fields(
    record_type: str,
    record_id: str,
    record: dict[str, str],
    required_fields: tuple[str, ...],
    issues: list[ValidationIssue],
) -> None:
    for field in required_fields:
        if not record.get(field, "").strip():
            issues.append(
                ValidationIssue(
                    "error",
                    "MISSING_REQUIRED_FIELD",
                    f"{record_type.capitalize()} {record_id} is missing {field}.",
                )
            )


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
