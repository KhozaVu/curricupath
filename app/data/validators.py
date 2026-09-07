"""Validation for the source-cited curriculum CSV datasets."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


COURSE_CODE_PATTERN = re.compile(r"^[A-Z]{4}\d{4}A?$")
PROGRAMME_CODE_PATTERN = re.compile(r"^EFA\d{2}$")
REQUIRED_DATASETS = (
    "sources.csv",
    "modules.csv",
    "rules.csv",
    "external_references.csv",
)
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
SOURCE_REQUIRED_FIELDS = (
    "source_id",
    "title",
    "publisher",
    "edition_year",
    "document_type",
    "authority_level",
    "verification_status",
    "authority",
    "locator",
    "review_date",
    "verification_notes",
)
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
EXTERNAL_REFERENCE_REQUIRED_FIELDS = (
    "reference",
    "rule_id",
    "status",
    "verified_source_id",
    "interpretation",
    "action",
)
COURSE_REQUIRED_FIELDS = (
    "course_id",
    "title",
    "provider",
    "category",
    "description",
    "outcomes",
    "topic_tags",
    "interest_tags",
    "career_tags",
    "workload",
    "format",
    "level",
    "provider_url",
    "rating_mean",
    "rating_count",
    "rating_scale",
    "source_id",
    "access_date",
)
COURSE_AUDIT_REQUIRED_FIELDS = (
    "course_id",
    "source_id",
    "availability_status",
    "verification_status",
    "recommendation_status",
    "audited_title",
    "audited_provider",
    "audit_date",
    "notes",
)
ALIAS_REQUIRED_FIELDS = ("alias", "canonical_tag", "tag_type")
COURSE_EXPRESSION_KEYS = {"all_of", "any_of", "all_courses_in_programme_year"}
COURSE_CATEGORIES = {
    "programming_data_ai",
    "electronics_control",
    "communications",
    "career_skills",
}
COURSE_WORKLOADS = {"light", "moderate", "heavy"}
COURSE_LEVELS = {"beginner", "intermediate"}
VALID_VERIFICATION_STATES = {
    "verified",
    "incomplete",
    "disputed",
    "superseded",
}
COURSE_AVAILABILITY_STATES = {"available", "unavailable", "unknown"}
COURSE_RECOMMENDATION_STATES = {"recommendable", "excluded"}


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
    external_references = datasets["external_references.csv"]

    _validate_headers("sources.csv", sources, SOURCE_REQUIRED_FIELDS, issues)
    _validate_headers("modules.csv", modules, MODULE_REQUIRED_FIELDS, issues)
    _validate_headers("rules.csv", rules, RULE_REQUIRED_FIELDS, issues)
    _validate_headers(
        "external_references.csv",
        external_references,
        EXTERNAL_REFERENCE_REQUIRED_FIELDS,
        issues,
    )
    _validate_sources(sources, processed_directory, issues)

    source_ids = {row.get("source_id", "") for row in sources}
    module_codes = {row.get("course_code", "") for row in modules}
    programme_codes = _programme_codes(rules, issues)

    module_keys: set[tuple[str, str, str]] = set()
    selection_groups: set[str] = set()
    for module in modules:
        course_code = module.get("course_code", "<unknown>")
        _validate_required_fields("module", course_code, module, MODULE_REQUIRED_FIELDS, issues)
        _validate_module(module, programme_codes, issues)
        key = (
            module.get("programme_code", ""),
            course_code,
            module.get("year_of_study", ""),
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
        if module.get("source_id", "") not in source_ids:
            issues.append(_unknown_source_issue("module", course_code, module.get("source_id", "")))
        if module.get("selection_group", ""):
            selection_groups.add(module["selection_group"])

    selection_rules: set[str] = set()
    rule_ids: set[str] = set()
    for rule in rules:
        rule_id = rule.get("rule_id", "<unknown>")
        rule_type = rule.get("rule_type", "")
        _validate_required_fields("rule", rule_id, rule, RULE_REQUIRED_FIELDS, issues)
        if rule_id in rule_ids:
            issues.append(
                ValidationIssue(
                    "error",
                    "DUPLICATE_RULE_ID",
                    f"Duplicate rule_id {rule_id}.",
                )
            )
        rule_ids.add(rule_id)

        if rule_type not in RULE_TYPES:
            issues.append(
                ValidationIssue(
                    "error",
                    "INVALID_RULE_TYPE",
                    f"Rule {rule_id} has invalid rule_type {rule_type}.",
                )
            )
        if rule.get("source_id", "") not in source_ids:
            issues.append(_unknown_source_issue("rule", rule_id, rule.get("source_id", "")))
        _validate_handbook_page("rule", rule_id, rule, issues)

        condition = _parse_condition(rule, issues)
        if condition is None:
            continue
        _validate_rule_condition(rule, condition, issues)

        if rule_type in {"prerequisite", "corequisite"}:
            target = rule.get("target_course_code", "")
            if target not in module_codes:
                issues.append(
                    ValidationIssue(
                        "error",
                        "UNKNOWN_RULE_TARGET",
                        f"{rule_id} targets {target}, which is not in modules.csv.",
                    )
                )

        if rule_type == "selection_count":
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

    _validate_external_references(
        external_references,
        rules,
        source_ids,
        module_codes,
        sources,
        issues,
    )

    return ValidationReport(tuple(issues))


def validate_course_data(data_directory: Path | str) -> ValidationReport:
    """Audit public course records and their source-backed ratings."""

    processed_directory = Path(data_directory)
    sources = _load_csv(processed_directory / "sources.csv")
    courses = _load_csv(processed_directory / "courses.csv")
    course_audit = _load_csv(processed_directory / "course_audit.csv")
    aliases = _load_csv(processed_directory / "aliases.csv")
    issues: list[ValidationIssue] = []

    _validate_headers("sources.csv", sources, SOURCE_REQUIRED_FIELDS, issues)
    _validate_headers("courses.csv", courses, COURSE_REQUIRED_FIELDS, issues)
    _validate_headers(
        "course_audit.csv", course_audit, COURSE_AUDIT_REQUIRED_FIELDS, issues
    )
    _validate_headers("aliases.csv", aliases, ALIAS_REQUIRED_FIELDS, issues)
    _validate_sources(sources, processed_directory, issues)

    sources_by_id = {source.get("source_id", ""): source for source in sources}
    canonical_tags = {alias.get("canonical_tag", "") for alias in aliases}
    course_ids: set[str] = set()
    for course in courses:
        course_id = course.get("course_id", "<unknown>")
        _validate_required_fields("course", course_id, course, COURSE_REQUIRED_FIELDS, issues)
        if course_id in course_ids:
            issues.append(
                ValidationIssue("error", "DUPLICATE_COURSE_ID", f"Duplicate course_id {course_id}.")
            )
        course_ids.add(course_id)
        _validate_course(course, sources_by_id, canonical_tags, issues)

    _validate_course_audit(course_audit, courses, sources_by_id, issues)

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

        local_path = source.get("local_path", "").strip()
        url = source.get("url", "").strip()
        if not local_path and not _is_valid_url(url):
            issues.append(
                ValidationIssue(
                    "error",
                    "MISSING_SOURCE_REFERENCE",
                    f"Source {source_id} must have a local_path or a valid url.",
                )
            )

        verification_status = source.get("verification_status", "")
        if verification_status not in VALID_VERIFICATION_STATES:
            issues.append(
                ValidationIssue(
                    "error",
                    "INVALID_VERIFICATION_STATUS",
                    f"Source {source_id} has invalid verification_status "
                    f"{verification_status!r}.",
                )
            )

        if not _is_valid_date(source.get("review_date", "")):
            issues.append(
                ValidationIssue(
                    "error",
                    "INVALID_SOURCE_REVIEW_DATE",
                    f"Source {source_id} has invalid review_date "
                    f"{source.get('review_date', '')!r}.",
                )
            )
        if local_path:
            source_path = processed_directory.parent.parent / local_path
            if not source_path.exists():
                issues.append(
                    ValidationIssue(
                        "error",
                        "SOURCE_FILE_MISSING",
                        f"{source_id} is not available at {source_path}.",
                    )
                )
        if url and not _is_valid_url(url):
            issues.append(
                ValidationIssue("error", "INVALID_SOURCE_URL", f"Source {source_id} has invalid url {url!r}.")
            )
        access_date = source.get("access_date", "").strip()
        if url and not _is_valid_date(access_date):
            issues.append(
                ValidationIssue("error", "INVALID_SOURCE_ACCESS_DATE", f"Source {source_id} has invalid access_date {access_date!r}.")
            )


def _validate_course(
    course: dict[str, str],
    sources_by_id: dict[str, dict[str, str]],
    canonical_tags: set[str],
    issues: list[ValidationIssue],
) -> None:
    course_id = course.get("course_id", "<unknown>")
    if course.get("category", "") not in COURSE_CATEGORIES:
        issues.append(ValidationIssue("error", "INVALID_COURSE_CATEGORY", f"Course {course_id} has invalid category {course.get('category', '')!r}."))
    if course.get("workload", "") not in COURSE_WORKLOADS:
        issues.append(ValidationIssue("error", "INVALID_COURSE_WORKLOAD", f"Course {course_id} has invalid workload {course.get('workload', '')!r}."))
    if course.get("format", "") != "online":
        issues.append(ValidationIssue("error", "INVALID_COURSE_FORMAT", f"Course {course_id} must use the online format."))
    if course.get("level", "") not in COURSE_LEVELS:
        issues.append(ValidationIssue("error", "INVALID_COURSE_LEVEL", f"Course {course_id} has invalid level {course.get('level', '')!r}."))
    if not _is_valid_url(course.get("provider_url", "")):
        issues.append(ValidationIssue("error", "INVALID_PROVIDER_URL", f"Course {course_id} has an invalid provider_url."))
    if not _is_valid_date(course.get("access_date", "")):
        issues.append(ValidationIssue("error", "INVALID_COURSE_ACCESS_DATE", f"Course {course_id} has invalid access_date {course.get('access_date', '')!r}."))

    try:
        rating_mean = float(course.get("rating_mean", ""))
        rating_count = int(course.get("rating_count", ""))
        rating_scale = int(course.get("rating_scale", ""))
    except ValueError:
        rating_mean, rating_count, rating_scale = -1.0, -1, -1
    if rating_scale != 5 or not 0 <= rating_mean <= rating_scale or rating_count < 1:
        issues.append(ValidationIssue("error", "INVALID_COURSE_RATING", f"Course {course_id} must have a 1-5 verified rating and positive review count."))

    source_id = course.get("source_id", "")
    source = sources_by_id.get(source_id)
    if source is None:
        issues.append(_unknown_source_issue("course", course_id, source_id))
    elif source.get("document_type") != "public_course_provider":
        issues.append(ValidationIssue("error", "INVALID_COURSE_SOURCE", f"Course {course_id} must reference a public_course_provider source."))
    for field in ("interest_tags", "career_tags"):
        for tag in _split_tags(course.get(field, "")):
            if tag not in canonical_tags:
                issues.append(
                    ValidationIssue(
                        "error",
                        "UNKNOWN_CONTROLLED_TAG",
                        f"Course {course_id} has {field} tag {tag!r}, which is not "
                        "defined in aliases.csv.",
                    )
                )


def _validate_external_references(
    external_references: list[dict[str, str]],
    rules: list[dict[str, str]],
    source_ids: set[str],
    module_codes: set[str],
    sources: list[dict[str, str]],
    issues: list[ValidationIssue],
) -> None:
    """Require a verified audit record for each prerequisite outside modules.csv."""

    rule_conditions: dict[str, object] = {}
    for rule in rules:
        try:
            rule_conditions[rule.get("rule_id", "")] = json.loads(
                rule.get("condition_json", "")
            )
        except json.JSONDecodeError:
            continue

    required = {
        (rule_id, course_code)
        for rule_id, condition in rule_conditions.items()
        for course_code in _referenced_course_codes(condition)
        if course_code not in module_codes
    }
    audited: set[tuple[str, str]] = set()
    sources_by_id = {source.get("source_id", ""): source for source in sources}
    for record in external_references:
        reference = record.get("reference", "")
        rule_id = record.get("rule_id", "")
        _validate_required_fields(
            "external reference",
            f"{rule_id}/{reference}",
            record,
            EXTERNAL_REFERENCE_REQUIRED_FIELDS,
            issues,
        )
        key = (rule_id, reference)
        if key in audited:
            issues.append(
                ValidationIssue(
                    "error",
                    "DUPLICATE_EXTERNAL_REFERENCE_AUDIT",
                    f"Duplicate external reference audit for {rule_id}/{reference}.",
                )
            )
        audited.add(key)
        if key not in required:
            issues.append(
                ValidationIssue(
                    "error",
                    "INVALID_EXTERNAL_REFERENCE_AUDIT",
                    f"External reference audit {rule_id}/{reference} does not match a "
                    "reference outside modules.csv.",
                )
            )
        if record.get("status") != "verified":
            issues.append(
                ValidationIssue(
                    "error",
                    "UNRESOLVED_EXTERNAL_REFERENCE",
                    f"External reference {rule_id}/{reference} is "
                    f"{record.get('status', '<missing>')}.",
                )
            )
        source_id = record.get("verified_source_id", "")
        source = sources_by_id.get(source_id)
        if source_id not in source_ids:
            issues.append(_unknown_source_issue("external reference", rule_id, source_id))
        elif source is not None and source.get("verification_status") != "verified":
            issues.append(
                ValidationIssue(
                    "error",
                    "UNVERIFIED_EXTERNAL_REFERENCE_SOURCE",
                    f"External reference {rule_id}/{reference} uses unverified "
                    f"source {source_id}.",
                )
            )

    for rule_id, reference in sorted(required - audited):
        issues.append(
            ValidationIssue(
                "error",
                "MISSING_EXTERNAL_REFERENCE_AUDIT",
                f"Rule {rule_id} references external module {reference} without "
                "a verified audit record.",
            )
        )


def _validate_course_audit(
    course_audit: list[dict[str, str]],
    courses: list[dict[str, str]],
    sources_by_id: dict[str, dict[str, str]],
    issues: list[ValidationIssue],
) -> None:
    """Keep course availability and source verification records aligned."""

    courses_by_id = {course.get("course_id", ""): course for course in courses}
    audited_course_ids: set[str] = set()
    for record in course_audit:
        course_id = record.get("course_id", "")
        _validate_required_fields(
            "course audit", course_id, record, COURSE_AUDIT_REQUIRED_FIELDS, issues
        )
        if course_id in audited_course_ids:
            issues.append(
                ValidationIssue(
                    "error",
                    "DUPLICATE_COURSE_AUDIT",
                    f"Duplicate course audit for {course_id}.",
                )
            )
        audited_course_ids.add(course_id)
        course = courses_by_id.get(course_id)
        if course is None:
            issues.append(
                ValidationIssue(
                    "error",
                    "UNKNOWN_AUDITED_COURSE",
                    f"Course audit references unknown course {course_id}.",
                )
            )
            continue
        if record.get("source_id") != course.get("source_id"):
            issues.append(
                ValidationIssue(
                    "error",
                    "COURSE_AUDIT_SOURCE_MISMATCH",
                    f"Course audit {course_id} does not match the course source_id.",
                )
            )
        if record.get("availability_status") not in COURSE_AVAILABILITY_STATES:
            issues.append(
                ValidationIssue(
                    "error",
                    "INVALID_COURSE_AVAILABILITY",
                    f"Course audit {course_id} has invalid availability_status "
                    f"{record.get('availability_status', '')!r}.",
                )
            )
        if record.get("verification_status") not in VALID_VERIFICATION_STATES:
            issues.append(
                ValidationIssue(
                    "error",
                    "INVALID_COURSE_AUDIT_STATUS",
                    f"Course audit {course_id} has invalid verification_status "
                    f"{record.get('verification_status', '')!r}.",
                )
            )
        if record.get("recommendation_status") not in COURSE_RECOMMENDATION_STATES:
            issues.append(
                ValidationIssue(
                    "error",
                    "INVALID_COURSE_RECOMMENDATION_STATUS",
                    f"Course audit {course_id} has invalid recommendation_status "
                    f"{record.get('recommendation_status', '')!r}.",
                )
            )
        if not _is_valid_date(record.get("audit_date", "")):
            issues.append(
                ValidationIssue(
                    "error",
                    "INVALID_COURSE_AUDIT_DATE",
                    f"Course audit {course_id} has invalid audit_date "
                    f"{record.get('audit_date', '')!r}.",
                )
            )

        source = sources_by_id.get(record.get("source_id", ""))
        if source is not None and (
            record.get("verification_status")
            != source.get("verification_status")
        ):
            issues.append(
                ValidationIssue(
                    "error",
                    "COURSE_AUDIT_STATUS_MISMATCH",
                    f"Course audit {course_id} does not match its source "
                    "verification_status.",
                )
            )
        if record.get("verification_status") == "superseded" and record.get(
            "availability_status"
        ) != "unavailable":
            issues.append(
                ValidationIssue(
                    "error",
                    "SUPERSEDED_COURSE_AVAILABLE",
                    f"Superseded course {course_id} cannot be marked available.",
                )
            )
        if record.get("recommendation_status") == "recommendable" and (
            record.get("verification_status") != "verified"
            or record.get("availability_status") != "available"
            or source is None
            or source.get("verification_status") != "verified"
        ):
            issues.append(
                ValidationIssue(
                    "error",
                    "UNSUPPORTED_RECOMMENDABLE_COURSE",
                    f"Course {course_id} is recommendable without a verified, "
                    "available provider record.",
                )
            )

    for course_id in sorted(set(courses_by_id) - audited_course_ids):
        issues.append(
            ValidationIssue(
                "error",
                "MISSING_COURSE_AUDIT",
                f"Course {course_id} has no audit record.",
            )
        )


def _is_valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _split_tags(value: str) -> tuple[str, ...]:
    return tuple(tag.strip() for tag in value.split(";") if tag.strip())


def _is_valid_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


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
    course_code = module.get("course_code", "")
    if not COURSE_CODE_PATTERN.fullmatch(course_code):
        issues.append(
            ValidationIssue(
                "error",
                "INVALID_MODULE_CODE",
                f"Module code {course_code!r} is invalid.",
            )
        )

    programme_code = module.get("programme_code", "")
    if programme_code not in programme_codes:
        issues.append(
            ValidationIssue(
                "error",
                "INVALID_PROGRAMME_CODE",
                f"Module {course_code} has unknown programme_code {programme_code}.",
            )
        )

    try:
        year = int(module.get("year_of_study", ""))
    except ValueError:
        year = 0
    if year not in {1, 2, 3, 4}:
        issues.append(
            ValidationIssue(
                "error",
                "INVALID_YEAR_OF_STUDY",
                f"Module {course_code} has invalid year_of_study "
                f"{module.get('year_of_study', '')!r}.",
            )
        )

    requirement_type = module.get("requirement_type", "")
    if requirement_type not in MODULE_REQUIREMENT_TYPES:
        issues.append(
            ValidationIssue(
                "error",
                "INVALID_REQUIREMENT_TYPE",
                f"Module {course_code} has invalid requirement_type "
                f"{requirement_type!r}.",
            )
        )

    try:
        credits = int(module.get("nqf_credits", ""))
    except ValueError:
        credits = -1
    if credits < 0:
        issues.append(
            ValidationIssue(
                "error",
                "INVALID_NQF_CREDITS",
                f"Module {course_code} has invalid NQF credits "
                f"{module.get('nqf_credits', '')!r}.",
            )
        )

    nqf_level = module.get("nqf_level", "")
    if requirement_type == "required_non_credit":
        valid_level = nqf_level == "N/A"
    else:
        try:
            valid_level = int(nqf_level) > 0
        except ValueError:
            valid_level = False
    if not valid_level:
        issues.append(
            ValidationIssue(
                "error",
                "INVALID_NQF_LEVEL",
                f"Module {course_code} has invalid NQF level {nqf_level!r}.",
            )
        )

    _validate_handbook_page("module", course_code, module, issues)


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


def _validate_headers(
    dataset_name: str,
    rows: list[dict[str, str]],
    required_fields: tuple[str, ...],
    issues: list[ValidationIssue],
) -> None:
    if not rows:
        issues.append(
            ValidationIssue(
                "error",
                "EMPTY_DATASET",
                f"{dataset_name} contains no records.",
            )
        )
        return

    headers = set(rows[0])
    for field in required_fields:
        if field not in headers:
            issues.append(
                ValidationIssue(
                    "error",
                    "MISSING_COLUMN",
                    f"{dataset_name} is missing required column {field}.",
                )
            )


def _validate_handbook_page(
    record_type: str,
    record_id: str,
    record: dict[str, str],
    issues: list[ValidationIssue],
) -> None:
    try:
        page = int(record.get("handbook_page", ""))
    except ValueError:
        page = 0
    if page <= 0:
        issues.append(
            ValidationIssue(
                "error",
                "INVALID_HANDBOOK_PAGE",
                f"{record_type.capitalize()} {record_id} has invalid handbook_page "
                f"{record.get('handbook_page', '')!r}.",
            )
        )


def _parse_condition(
    rule: dict[str, str], issues: list[ValidationIssue]
) -> dict[str, object] | None:
    try:
        condition = json.loads(rule.get("condition_json", ""))
    except json.JSONDecodeError as error:
        issues.append(
            ValidationIssue(
                "error",
                "INVALID_CONDITION_JSON",
                f"{rule.get('rule_id', '<unknown>')} has invalid condition_json: "
                f"{error.msg}.",
            )
        )
        return None

    if not isinstance(condition, dict):
        issues.append(
            ValidationIssue(
                "error",
                "INVALID_CONDITION_SHAPE",
                f"{rule.get('rule_id', '<unknown>')} condition_json must decode to "
                "an object.",
            )
        )
        return None
    return condition


def _validate_rule_condition(
    rule: dict[str, str],
    condition: dict[str, object],
    issues: list[ValidationIssue],
) -> None:
    rule_id = rule.get("rule_id", "<unknown>")
    rule_type = rule.get("rule_type", "")
    if rule_type in {"prerequisite", "corequisite"}:
        if not COURSE_EXPRESSION_KEYS.intersection(condition):
            _invalid_condition_issue(
                rule_id,
                "must contain a course expression such as all_of or any_of",
                issues,
            )
    elif rule_type == "selection_count":
        group = condition.get("selection_group")
        count = condition.get("select_exactly")
        if not isinstance(group, str) or not group:
            _invalid_condition_issue(rule_id, "must contain selection_group", issues)
        if not isinstance(count, int) or count < 1:
            _invalid_condition_issue(rule_id, "must contain a positive select_exactly", issues)
    elif rule_type == "programme_selection":
        options = condition.get("options")
        year = condition.get("at_start_of_year")
        count = condition.get("select_exactly")
        if not isinstance(options, list) or not options:
            _invalid_condition_issue(rule_id, "must contain non-empty options", issues)
        if not isinstance(year, int) or year not in {1, 2, 3, 4}:
            _invalid_condition_issue(rule_id, "must contain a valid at_start_of_year", issues)
        if not isinstance(count, int) or count < 1:
            _invalid_condition_issue(rule_id, "must contain a positive select_exactly", issues)


def _invalid_condition_issue(
    rule_id: str, requirement: str, issues: list[ValidationIssue]
) -> None:
    issues.append(
        ValidationIssue(
            "error",
            "INVALID_RULE_CONDITION",
            f"Rule {rule_id} {requirement}.",
        )
    )


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
