+"""Deterministic eligibility gates for curriculum recommendations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class StudentProfile:
    """The student state needed by the initial eligibility gates."""

    programme_code: str
    completed_modules: frozenset[str]
    current_modules: frozenset[str]
    planned_modules: frozenset[str]


@dataclass(frozen=True)
class EligibilityResult:
    """A deterministic gate result with auditable explanations."""

    eligible: bool
    reasons: tuple[str, ...]
    needs_clarification: bool = False


def requirement_satisfied(condition: object, available_modules: set[str]) -> bool:
    """Evaluate the all_of/any_of requirement structure stored in rules.csv."""

    if isinstance(condition, str):
        return condition in available_modules
    if isinstance(condition, list):
        return all(
            requirement_satisfied(item, available_modules) for item in condition
        )
    if isinstance(condition, dict):
        if "all_of" in condition:
            return all(
                requirement_satisfied(item, available_modules)
                for item in condition["all_of"]
            )
        if "any_of" in condition:
            return any(
                requirement_satisfied(item, available_modules)
                for item in condition["any_of"]
            )
    return False


def check_source(
    course_code: str,
    profile: StudentProfile,
    modules: Iterable[dict[str, str]],
    rules: Iterable[dict[str, str]],
    sources: Iterable[dict[str, str]],
    source_root: Path | str | None = None,
) -> EligibilityResult:
    """Require every material module/rule record to reference an available source."""

    module_rows = [row for row in modules if row.get("course_code") == course_code]
    if not module_rows:
        return EligibilityResult(
            False,
            (f"{course_code} has no curriculum module record.",),
        )

    applicable_rules = [
        rule
        for rule in rules
        if rule.get("target_course_code") == course_code
        and rule.get("rule_type") in {"prerequisite", "corequisite", "exclusion"}
        and _scope_applies(rule.get("scope", ""), profile.programme_code)
    ]
    source_ids = {
        row.get("source_id", "") for row in [*module_rows, *applicable_rules]
    }
    source_by_id = {source.get("source_id", ""): source for source in sources}
    root = Path(source_root) if source_root is not None else Path.cwd()

    failures: list[str] = []
    for source_id in sorted(source_ids):
        source = source_by_id.get(source_id)
        if source is None:
            failures.append(f"Source {source_id or '<missing>'} is not registered.")
            continue
        if not source.get("title", "").strip():
            failures.append(f"Source {source_id} has no description.")
            continue
        source_path = Path(source.get("local_path", ""))
        if not source_path.is_absolute():
            source_path = root / source_path
        if not source_path.exists():
            failures.append(f"Source {source_id} is not available at {source_path}.")

    if failures:
        return EligibilityResult(False, tuple(failures))
    return EligibilityResult(True, ())


def check_programme(
    course_code: str,
    profile: StudentProfile,
    modules: Iterable[dict[str, str]],
) -> EligibilityResult:
    """Require a membership record for the student's programme."""

    if any(
        row.get("course_code") == course_code
        and row.get("programme_code") == profile.programme_code
        for row in modules
    ):
        return EligibilityResult(True, ())
    return EligibilityResult(
        False,
        (f"{course_code} is not part of programme {profile.programme_code}.",),
    )


def check_prerequisites(
    course_code: str,
    profile: StudentProfile,
    rules: Iterable[dict[str, str]],
) -> EligibilityResult:
    """Require prerequisites to be completed before registration."""

    return _check_requirement_rules(
        course_code,
        profile,
        rules,
        "prerequisite",
        set(profile.completed_modules),
        needs_clarification=False,
    )


def check_corequisites(
    course_code: str,
    profile: StudentProfile,
    rules: Iterable[dict[str, str]],
) -> EligibilityResult:
    """Allow completed, current, and planned modules to satisfy corequisites."""

    available = (
        set(profile.completed_modules)
        | set(profile.current_modules)
        | set(profile.planned_modules)
    )
    return _check_requirement_rules(
        course_code,
        profile,
        rules,
        "corequisite",
        available,
        needs_clarification=True,
    )


def check_exclusions(
    course_code: str,
    profile: StudentProfile,
    rules: Iterable[dict[str, str]],
) -> EligibilityResult:
    """Reject a candidate when a course-targeted exclusion condition is present."""

    available = (
        set(profile.completed_modules)
        | set(profile.current_modules)
        | set(profile.planned_modules)
    )
    for rule in _rules_for_course(rules, course_code, "exclusion", profile):
        condition, error = _condition_for_rule(rule)
        if error:
            return EligibilityResult(False, (error,))
        if requirement_satisfied(condition, available):
            return EligibilityResult(
                False,
                (f"Excluded by rule {rule['rule_id']}.",),
            )
    return EligibilityResult(True, ())


def check_eligibility(
    course_code: str,
    profile: StudentProfile,
    modules: Iterable[dict[str, str]],
    rules: Iterable[dict[str, str]],
    sources: Iterable[dict[str, str]],
    source_root: Path | str | None = None,
) -> EligibilityResult:
    """Run source, programme, prerequisite, corequisite, and exclusion gates."""

    module_rows = list(modules)
    rule_rows = list(rules)
    source_rows = list(sources)
    result = check_source(
        course_code,
        profile,
        module_rows,
        rule_rows,
        source_rows,
        source_root,
    )
    if not result.eligible:
        return result

    result = check_programme(course_code, profile, module_rows)
    if not result.eligible:
        return result

    result = check_prerequisites(course_code, profile, rule_rows)
    if not result.eligible:
        return result

    result = check_corequisites(course_code, profile, rule_rows)
    if not result.eligible:
        return result

    result = check_exclusions(course_code, profile, rule_rows)
    if not result.eligible:
        return result

    return EligibilityResult(True, ())


def _check_requirement_rules(
    course_code: str,
    profile: StudentProfile,
    rules: Iterable[dict[str, str]],
    rule_type: str,
    available: set[str],
    needs_clarification: bool,
) -> EligibilityResult:
    failures: list[str] = []
    for rule in _rules_for_course(rules, course_code, rule_type, profile):
        condition, error = _condition_for_rule(rule)
        if error:
            failures.append(error)
        elif not requirement_satisfied(condition, available):
            failures.append(f"{rule_type.capitalize()} rule {rule['rule_id']} is not satisfied.")

    if failures:
        return EligibilityResult(False, tuple(failures), needs_clarification)
    return EligibilityResult(True, ())


def _rules_for_course(
    rules: Iterable[dict[str, str]],
    course_code: str,
    rule_type: str,
    profile: StudentProfile,
) -> list[dict[str, str]]:
    return [
        rule
        for rule in rules
        if rule.get("target_course_code") == course_code
        and rule.get("rule_type") == rule_type
        and _scope_applies(rule.get("scope", ""), profile.programme_code)
    ]


def _scope_applies(scope: str, programme_code: str) -> bool:
    return scope in {"ALL", "ALL_EFA03_EFA04"} or programme_code in scope.split("|")


def _condition_for_rule(rule: dict[str, str]) -> tuple[object, str | None]:
    try:
        return json.loads(rule["condition_json"]), None
    except (KeyError, json.JSONDecodeError):
        return None, f"Rule {rule.get('rule_id', '<unknown>')} has invalid condition data."
