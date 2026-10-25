"""Deterministic eligibility gates for curriculum recommendations."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType
from typing import Callable, Iterable, Literal, Mapping


EligibilityDecision = Literal[
    "eligible",
    "ineligible",
    "needs_clarification",
    "manual_review_required",
]
ModuleFactState = Literal[
    "completed",
    "current",
    "planned",
    "not_completed",
    "unknown",
]
RequirementStatus = Literal["satisfied", "unsatisfied", "unknown", "invalid"]
VALID_MODULE_FACT_STATES = frozenset(
    {"completed", "current", "planned", "not_completed", "unknown"}
)


@dataclass(frozen=True)
class EligibilityTrace:
    """One gate outcome in the deterministic eligibility decision."""

    gate: str
    decision: EligibilityDecision
    reasons: tuple[str, ...] = ()
    rule_ids: tuple[str, ...] = ()
    # Modules behind the outcome: unmet or unknown prerequisites/corequisites, or clash partners.
    blocking_modules: tuple[str, ...] = ()


@dataclass(frozen=True)
class RequirementEvaluation:
    """Three-valued result for one recursive curriculum condition."""

    status: RequirementStatus
    unresolved_predicates: tuple[str, ...] = ()
    unsatisfied_predicates: tuple[str, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class StudentProfile:
    """The student state needed by the initial eligibility gates."""

    programme_code: str
    completed_modules: frozenset[str]
    current_modules: frozenset[str]
    planned_modules: frozenset[str]
    repeating_modules: frozenset[str] = frozenset()
    # Modules the student confirmed they are not repeating, taking or planning (clash check only).
    clash_cleared_modules: frozenset[str] = frozenset()
    manual_review_reasons: tuple[str, ...] = ()
    module_states: Mapping[str, ModuleFactState] | None = None
    module_history_confirmed: bool | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "completed_modules",
            frozenset(code.upper() for code in self.completed_modules),
        )
        object.__setattr__(
            self,
            "current_modules",
            frozenset(code.upper() for code in self.current_modules),
        )
        object.__setattr__(
            self,
            "planned_modules",
            frozenset(code.upper() for code in self.planned_modules),
        )
        object.__setattr__(
            self,
            "repeating_modules",
            frozenset(normalise_rule_course_code(code) for code in self.repeating_modules),
        )
        object.__setattr__(
            self,
            "clash_cleared_modules",
            frozenset(
                normalise_rule_course_code(code) for code in self.clash_cleared_modules
            ),
        )
        normalized_states = {
            code.upper(): state for code, state in (self.module_states or {}).items()
        }
        object.__setattr__(self, "module_states", MappingProxyType(normalized_states))

        declared_sets = {
            "completed": self.completed_modules,
            "current": self.current_modules,
            "planned": self.planned_modules,
        }
        seen: dict[str, str] = {}
        for state, course_codes in declared_sets.items():
            for course_code in course_codes:
                code = course_code.upper()
                previous = seen.get(code)
                if previous and previous != state:
                    raise ValueError(
                        f"Module {code} cannot be both {previous} and {state}."
                    )
                seen[code] = state

        for course_code, state in normalized_states.items():
            code = course_code.upper()
            if state not in VALID_MODULE_FACT_STATES:
                raise ValueError(f"Module {code} has invalid profile state {state!r}.")
            previous = seen.get(code)
            if previous and previous != state:
                raise ValueError(
                    f"Module {code} cannot be both {previous} and {state}."
                )

    def module_state(
        self,
        course_code: str,
        *,
        legacy_absence_is_unknown: bool = False,
    ) -> ModuleFactState:
        """Return an explicit fact state while supporting legacy set-only profiles."""

        code = course_code.upper()
        explicit = (self.module_states or {}).get(code)
        if explicit is not None:
            return explicit
        if code in self.completed_modules:
            return "completed"
        if code in self.current_modules:
            return "current"
        if code in self.planned_modules:
            return "planned"
        if self.module_history_confirmed is True:
            return "not_completed"
        if self.module_history_confirmed is False:
            return "unknown"
        return "unknown" if legacy_absence_is_unknown else "not_completed"


@dataclass(frozen=True)
class EligibilityResult:
    """A deterministic gate result with auditable explanations."""

    decision: EligibilityDecision
    reasons: tuple[str, ...]
    rule_trace: tuple[EligibilityTrace, ...] = ()
    unresolved_predicates: tuple[str, ...] = ()
    evidence_issues: tuple[str, ...] = ()
    clarification: dict[str, object] | None = None
    manual_review_package: dict[str, object] | None = None

    @property
    def eligible(self) -> bool:
        return self.decision == "eligible"

    @property
    def needs_clarification(self) -> bool:
        return self.decision == "needs_clarification"

    @property
    def manual_review_required(self) -> bool:
        return self.decision == "manual_review_required"


ProgrammeYearCourses = Mapping[tuple[str, int], frozenset[str]]
ClashRule = Mapping[str, str]
GridRequirementRule = Mapping[str, str]

LEGACY_RULE_CODES = {
    "ELEN2004": "ELEN2020",
    "ELEN2001": "ELEN2016",
    "ELEN2006": "ELEN2021",
    "MATH1048": "MATH1042",
    "MATH1049": "MATH1043",
}
IGNORED_RULE_CODES = frozenset({"MATH1014"})


def normalise_rule_course_code(course_code: str) -> str:
    """Normalize a current or legacy curriculum code for rule matching."""

    code = course_code.strip().upper().replace(" ", "")
    if not code:
        return ""
    suffix = code[-1] if code and code[-1].isalpha() else "A"
    base = code[:-1] if code and code[-1].isalpha() else code
    if base in IGNORED_RULE_CODES:
        return ""
    return f"{LEGACY_RULE_CODES.get(base, base)}{suffix}"


def load_clash_rules(path: Path | str) -> tuple[dict[str, str], ...]:
    """Load generated timetable-clash rules without mutating the source rows."""

    with Path(path).open(newline="", encoding="utf-8") as csv_file:
        rows = tuple(dict(row) for row in csv.DictReader(csv_file))
    required = {
        "rule_id",
        "scope",
        "rule_type",
        "repeating_course",
        "target_course_code",
        "clash_type",
        "source_ids",
        "sheet",
    }
    if not rows:
        raise ValueError("Timetable-clash rule file contains no records.")
    missing = required - set(rows[0])
    if missing:
        raise ValueError(
            "Timetable-clash rule file is missing columns: "
            + ", ".join(sorted(missing))
        )
    return rows


def load_grid_requirement_rules(path: Path | str) -> tuple[dict[str, str], ...]:
    """Load programme-scoped prerequisite/corequisite rules from the School grid."""

    grid_path = Path(path)
    if not grid_path.exists():
        raise FileNotFoundError(f"School registration requirements are missing: {grid_path}")
    with grid_path.open(encoding="utf-8") as grid_file:
        payload = json.load(grid_file)
    tables = payload.get("requirements_from_cross_curricular_tables")
    if not isinstance(tables, dict):
        raise ValueError("grid_rules.json has no requirement table.")

    scopes = {
        "EE YOS 2": "ALL_EFA03_EFA04",
        "EE YOS 3": "EFA03",
        "IE YOS 3": "EFA04",
    }
    loaded: list[dict[str, str]] = []
    for key, requirements in sorted(tables.items()):
        sheet, separator, raw_target = key.partition("|")
        if not separator or sheet not in scopes or not isinstance(requirements, dict):
            raise ValueError(f"Invalid School registration requirement entry: {key!r}.")
        target = normalise_rule_course_code(raw_target)
        if not target:
            raise ValueError(f"Invalid School registration target: {raw_target!r}.")
        for rule_type, field, prefix in (
            ("prerequisite", "prereq", "GRID_PRE"),
            ("corequisite", "coreq", "GRID_CORE"),
        ):
            raw_codes = requirements.get(field, [])
            if not isinstance(raw_codes, list):
                raise ValueError(f"{key} has an invalid {field} list.")
            codes = tuple(
                dict.fromkeys(
                    code
                    for item in raw_codes
                    if (code := normalise_rule_course_code(str(item)))
                )
            )
            loaded.append(
                {
                    "rule_id": f"{prefix}_{target}",
                    "scope": scopes[sheet],
                    "rule_type": rule_type,
                    "target_course_code": target,
                    "condition_json": (
                        json.dumps({"all_of": list(codes)}, separators=(",", ":"))
                        if codes
                        else ""
                    ),
                    "has_requirement": "true" if codes else "false",
                    "source_id": "EIE_REG_GRID_2026",
                    "source_sheet": sheet,
                    "handbook_page": "",
                    "notes": "School registration reference requirement.",
                }
            )
    return tuple(loaded)


def apply_grid_requirement_overrides(
    rules: Iterable[dict[str, str]],
    grid_rules: Iterable[GridRequirementRule],
    course_code: str,
    programme_code: str,
) -> list[dict[str, str]]:
    """Replace handbook requirements with the programme's School-grid requirements."""

    target = course_code.upper()
    base_rules = [dict(rule) for rule in rules]
    selected = [
        dict(rule)
        for rule in grid_rules
        if rule.get("target_course_code") == target
        and rule.get("rule_type") in {"prerequisite", "corequisite"}
        and _scope_applies(rule.get("scope", ""), programme_code)
    ]
    if not selected:
        return base_rules

    for replacement in selected:
        rule_type = replacement["rule_type"]
        replaced = [
            rule
            for rule in base_rules
            if rule.get("target_course_code") == target
            and rule.get("rule_type") == rule_type
            and _scope_applies(rule.get("scope", ""), programme_code)
        ]
        if replaced:
            # Preserve the established rule identity/page while changing only its authority's
            # requirement expression. Grid-only requirements keep their GRID_* identity.
            replacement["rule_id"] = replaced[0].get("rule_id", replacement["rule_id"])
            replacement["handbook_page"] = replaced[0].get("handbook_page", "")
        base_rules = [rule for rule in base_rules if rule not in replaced]
        if replacement.get("has_requirement") == "true":
            base_rules.append(replacement)
    return base_rules


def requirement_satisfied(
    condition: object,
    available_modules: set[str],
    programme_year_courses: ProgrammeYearCourses | None = None,
) -> bool:
    """Evaluate the recursive requirement structures stored in rules.csv."""

    if isinstance(condition, str):
        return condition in available_modules
    if isinstance(condition, list):
        return all(
            requirement_satisfied(item, available_modules, programme_year_courses)
            for item in condition
        )
    if isinstance(condition, dict):
        if "all_of" in condition:
            return all(
                requirement_satisfied(item, available_modules, programme_year_courses)
                for item in condition["all_of"]
            )
        if "any_of" in condition:
            return any(
                requirement_satisfied(item, available_modules, programme_year_courses)
                for item in condition["any_of"]
            )
        programme_year = condition.get("all_courses_in_programme_year")
        if isinstance(programme_year, dict) and programme_year_courses is not None:
            programme = str(programme_year.get("programme", "")).upper()
            try:
                year = int(programme_year.get("year", 0))
            except (TypeError, ValueError):
                return False
            required = programme_year_courses.get((programme, year), frozenset())
            return bool(required) and required.issubset(available_modules)
    return False


def evaluate_requirement(
    condition: object,
    fact_state: Callable[[str], ModuleFactState],
    accepted_states: frozenset[ModuleFactState],
    programme_year_courses: ProgrammeYearCourses | None = None,
) -> RequirementEvaluation:
    """Evaluate nested requirements without collapsing unknown facts to false."""

    if isinstance(condition, str):
        course_code = condition.upper()
        state = fact_state(course_code)
        if state in accepted_states:
            return RequirementEvaluation("satisfied")
        if state == "unknown":
            return RequirementEvaluation(
                "unknown", unresolved_predicates=(course_code,)
            )
        return RequirementEvaluation(
            "unsatisfied", unsatisfied_predicates=(course_code,)
        )

    if isinstance(condition, list):
        return _evaluate_all(
            condition, fact_state, accepted_states, programme_year_courses
        )

    if not isinstance(condition, dict):
        return RequirementEvaluation(
            "invalid", error="Requirement condition has an unsupported value."
        )

    operators = [
        key
        for key in ("all_of", "any_of", "all_courses_in_programme_year")
        if key in condition
    ]
    if len(operators) != 1:
        return RequirementEvaluation(
            "invalid",
            error="Requirement condition must contain exactly one supported operator.",
        )

    operator = operators[0]
    if operator in {"all_of", "any_of"}:
        children = condition[operator]
        if not isinstance(children, list) or not children:
            return RequirementEvaluation(
                "invalid", error=f"Requirement operator {operator} needs a non-empty list."
            )
        evaluator = _evaluate_all if operator == "all_of" else _evaluate_any
        return evaluator(
            children, fact_state, accepted_states, programme_year_courses
        )

    programme_year = condition[operator]
    if not isinstance(programme_year, dict) or programme_year_courses is None:
        return RequirementEvaluation(
            "invalid", error="Programme-year requirement cannot be resolved."
        )
    programme = str(programme_year.get("programme", "")).upper()
    try:
        year = int(programme_year.get("year", 0))
    except (TypeError, ValueError):
        year = 0
    required = sorted(programme_year_courses.get((programme, year), frozenset()))
    if not programme or not year or not required:
        return RequirementEvaluation(
            "invalid",
            error=f"Programme-year requirement {programme or '<missing>'}/{year} is empty.",
        )
    return _evaluate_all(
        required, fact_state, accepted_states, programme_year_courses
    )


def _evaluate_all(
    children: Iterable[object],
    fact_state: Callable[[str], ModuleFactState],
    accepted_states: frozenset[ModuleFactState],
    programme_year_courses: ProgrammeYearCourses | None,
) -> RequirementEvaluation:
    evaluations = tuple(
        evaluate_requirement(
            child, fact_state, accepted_states, programme_year_courses
        )
        for child in children
    )
    invalid = next((item for item in evaluations if item.status == "invalid"), None)
    if invalid is not None:
        return invalid
    unsatisfied = tuple(
        dict.fromkeys(
            code
            for item in evaluations
            if item.status == "unsatisfied"
            for code in item.unsatisfied_predicates
        )
    )
    if unsatisfied:
        return RequirementEvaluation(
            "unsatisfied", unsatisfied_predicates=unsatisfied
        )
    unresolved = tuple(
        dict.fromkeys(
            code
            for item in evaluations
            if item.status == "unknown"
            for code in item.unresolved_predicates
        )
    )
    if unresolved:
        return RequirementEvaluation("unknown", unresolved_predicates=unresolved)
    return RequirementEvaluation("satisfied")


def _evaluate_any(
    children: Iterable[object],
    fact_state: Callable[[str], ModuleFactState],
    accepted_states: frozenset[ModuleFactState],
    programme_year_courses: ProgrammeYearCourses | None,
) -> RequirementEvaluation:
    evaluations = tuple(
        evaluate_requirement(
            child, fact_state, accepted_states, programme_year_courses
        )
        for child in children
    )
    if any(item.status == "satisfied" for item in evaluations):
        return RequirementEvaluation("satisfied")
    invalid = next((item for item in evaluations if item.status == "invalid"), None)
    if invalid is not None:
        return invalid
    unknown = [item for item in evaluations if item.status == "unknown"]
    if unknown:
        # One successful alternative is sufficient. Ask about the branch requiring
        # the fewest missing atomic facts, preserving source order for ties.
        smallest = min(unknown, key=lambda item: len(item.unresolved_predicates))
        return RequirementEvaluation(
            "unknown", unresolved_predicates=smallest.unresolved_predicates
        )
    unsatisfied = tuple(
        dict.fromkeys(
            code
            for item in evaluations
            for code in item.unsatisfied_predicates
        )
    )
    return RequirementEvaluation(
        "unsatisfied", unsatisfied_predicates=unsatisfied
    )


def programme_year_course_map(
    modules: Iterable[Mapping[str, object]],
) -> dict[tuple[str, int], frozenset[str]]:
    """Index curriculum module codes by programme and year for grouped rules."""

    grouped: dict[tuple[str, int], set[str]] = {}
    for module in modules:
        programme = str(module.get("programme_code", "")).upper()
        course_code = str(module.get("course_code", "")).upper()
        try:
            year = int(module.get("year_of_study", 0))
        except (TypeError, ValueError):
            continue
        if programme and course_code and year:
            grouped.setdefault((programme, year), set()).add(course_code)
    return {key: frozenset(codes) for key, codes in grouped.items()}


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
        reasons = (f"{course_code} has no curriculum module record.",)
        return _gate_result(
            "source",
            "manual_review_required",
            reasons,
            evidence_issues=reasons,
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
        if source.get("verification_status") != "verified":
            failures.append(f"Source {source_id} is not verified.")
            continue

        local_path = source.get("local_path", "").strip()
        source_url = source.get("url", "").strip()
        if local_path:
            source_path = Path(local_path)
            if not source_path.is_absolute():
                source_path = root / source_path
            if not source_path.exists():
                failures.append(f"Source {source_id} is not available at {source_path}.")
        elif not source_url:
            failures.append(f"Source {source_id} has no available file or URL.")

    if failures:
        reasons = tuple(failures)
        return _gate_result(
            "source",
            "manual_review_required",
            reasons,
            evidence_issues=reasons,
        )
    return _gate_result("source", "eligible")


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
        return _gate_result("programme", "eligible")
    return _gate_result(
        "programme",
        "ineligible",
        (f"{course_code} is not part of programme {profile.programme_code}.",),
    )


def check_prerequisites(
    course_code: str,
    profile: StudentProfile,
    rules: Iterable[dict[str, str]],
    programme_year_courses: ProgrammeYearCourses | None = None,
) -> EligibilityResult:
    """Require prerequisites to be completed before registration."""

    return _check_requirement_rules(
        course_code,
        profile,
        rules,
        "prerequisite",
        frozenset({"completed"}),
        legacy_absence_is_unknown=False,
        programme_year_courses=programme_year_courses,
    )


def check_corequisites(
    course_code: str,
    profile: StudentProfile,
    rules: Iterable[dict[str, str]],
    programme_year_courses: ProgrammeYearCourses | None = None,
) -> EligibilityResult:
    """Allow completed, current, and planned modules to satisfy corequisites."""

    return _check_requirement_rules(
        course_code,
        profile,
        rules,
        "corequisite",
        frozenset({"completed", "current", "planned"}),
        legacy_absence_is_unknown=True,
        programme_year_courses=programme_year_courses,
    )


def check_exclusions(
    course_code: str,
    profile: StudentProfile,
    rules: Iterable[dict[str, str]],
    programme_year_courses: ProgrammeYearCourses | None = None,
) -> EligibilityResult:
    """Reject a candidate when a course-targeted exclusion condition is present."""

    unknown_rules: list[tuple[dict[str, str], RequirementEvaluation]] = []
    for rule in _rules_for_course(rules, course_code, "exclusion", profile):
        condition, error = _condition_for_rule(rule)
        if error:
            return _gate_result(
                "exclusion",
                "manual_review_required",
                (error,),
                rule_ids=(rule.get("rule_id", "<unknown>"),),
                evidence_issues=(error,),
            )
        evaluation = _evaluate_for_profile(
            condition,
            profile,
            frozenset({"completed", "current", "planned"}),
            programme_year_courses,
            legacy_absence_is_unknown=False,
        )
        if evaluation.status == "invalid":
            reason = (
                f"Rule {rule.get('rule_id', '<unknown>')} has invalid condition data: "
                f"{evaluation.error}"
            )
            return _gate_result(
                "exclusion",
                "manual_review_required",
                (reason,),
                rule_ids=(rule.get("rule_id", "<unknown>"),),
                evidence_issues=(reason,),
            )
        if evaluation.status == "satisfied":
            return _gate_result(
                "exclusion",
                "ineligible",
                (f"Excluded by rule {rule['rule_id']}.",),
                rule_ids=(rule["rule_id"],),
            )
        if evaluation.status == "unknown":
            unknown_rules.append((rule, evaluation))
    if unknown_rules:
        rule, evaluation = min(
            unknown_rules,
            key=lambda item: len(item[1].unresolved_predicates),
        )
        return _gate_result(
            "exclusion",
            "needs_clarification",
            (f"Exclusion rule {rule['rule_id']} depends on an undeclared module fact.",),
            rule_ids=tuple(item[0]["rule_id"] for item in unknown_rules),
            unresolved_predicates=evaluation.unresolved_predicates,
        )
    return _gate_result("exclusion", "eligible")


def check_timetable_clashes(
    course_code: str,
    profile: StudentProfile,
    clash_rules: Iterable[ClashRule],
) -> EligibilityResult:
    """Reject a target that shares a timetable slot with a module the student will attend.

    A listed pair clashes when the student is repeating the pair's first module (the School
    tables are written for repeating students), or is currently taking or planning either module
    of the pair while asking about the other (two modules in one slot clash both ways). When the
    student's module history is explicitly unconfirmed and a partner's status is unknown, the
    gate asks rather than assuming the student is free.
    """

    target = normalise_rule_course_code(course_code)
    repeating = {code for code in profile.repeating_modules if code}
    concurrent = {
        normalise_rule_course_code(code)
        for code in (*profile.current_modules, *profile.planned_modules)
    } | {
        normalise_rule_course_code(code)
        for code, state in (profile.module_states or {}).items()
        if state in {"current", "planned"}
    }
    known = (
        {normalise_rule_course_code(code) for code in profile.completed_modules}
        | {
            normalise_rule_course_code(code)
            for code, state in (profile.module_states or {}).items()
            if state != "unknown"
        }
        | repeating
        | concurrent
        | set(profile.clash_cleared_modules)
    )
    clashes: list[tuple[ClashRule, str, str]] = []
    unknown_partners: dict[str, None] = {}
    for rule in sorted(clash_rules, key=lambda item: item.get("rule_id", "")):
        if rule.get("rule_type") != "timetable_clash" or not _scope_applies(
            rule.get("scope", ""), profile.programme_code
        ):
            continue
        first = normalise_rule_course_code(rule.get("repeating_course", ""))
        second = normalise_rule_course_code(rule.get("target_course_code", ""))
        if target not in {first, second}:
            continue
        partner = second if target == first else first
        if target == second and first in repeating:
            clashes.append((rule, first, "repeating"))
        elif partner in concurrent:
            clashes.append((rule, partner, "concurrent"))
        elif (
            target == second
            and profile.module_history_confirmed is False
            and partner not in known
        ):
            # Ask only about the pair's listed (usually lower-year) module; a reverse-direction
            # partner blocks only when the student has declared it current or planned.
            unknown_partners.setdefault(partner)
    if clashes:
        return _gate_result(
            "timetable_clash",
            "ineligible",
            tuple(
                _timetable_clash_reason(rule, target, partner, kind)
                for rule, partner, kind in clashes
            ),
            rule_ids=tuple(rule.get("rule_id", "<unknown>") for rule, _, _ in clashes),
            blocking_modules=tuple(dict.fromkeys(partner for _, partner, _ in clashes)),
        )
    if unknown_partners:
        return _gate_result(
            "timetable_clash",
            "needs_clarification",
            (f"{target} shares a timetable slot with modules whose status is unknown.",),
            unresolved_predicates=tuple(unknown_partners),
            blocking_modules=tuple(unknown_partners),
        )
    return _gate_result("timetable_clash", "eligible")


def _timetable_clash_reason(
    rule: ClashRule,
    target: str | None = None,
    partner: str | None = None,
    kind: str = "repeating",
) -> str:
    clash_type = rule.get("clash_type", "UNSPECIFIED").upper()
    description = {
        "LEC": "lecture timetable clash",
        "LAB": "laboratory timetable clash",
        "TUT": "tutorial timetable clash",
        "UNSPECIFIED": "timetable clash",
    }.get(clash_type, "timetable clash")
    partner = partner or normalise_rule_course_code(rule.get("repeating_course", ""))
    target = target or normalise_rule_course_code(rule.get("target_course_code", ""))
    held = (
        "which the student is repeating"
        if kind == "repeating"
        else "which the student is taking or planning in the same period"
    )
    locations: dict[str, list[str]] = {}
    for value in rule.get("sheet", "").split(";"):
        source, separator, sheet = value.partition(":")
        if separator:
            locations.setdefault(source, []).append(sheet)
    citations = []
    source_ids = list(filter(None, rule.get("source_ids", "").split(";")))
    for source_id in source_ids:
        sheets = locations.get(source_id, [])
        show_sheet = source_id == "EIE_PLANNER_2026" or len(source_ids) == 1
        location = f", sheet '{sheets[0]}'" if sheets and show_sheet else ""
        citations.append(f"{source_id}{location}")
    citation = "; ".join(citations) or "School registration reference"
    return (
        f"{rule.get('rule_id', '<unknown>')}: {target} has a {description} with "
        f"{partner}, {held}, so it cannot be taken "
        f"({citation})."
    )


def check_eligibility(
    course_code: str,
    profile: StudentProfile,
    modules: Iterable[dict[str, str]],
    rules: Iterable[dict[str, str]],
    sources: Iterable[dict[str, str]],
    source_root: Path | str | None = None,
    *,
    clash_rules: Iterable[ClashRule] = (),
    enable_timetable_clashes: bool = False,
    grid_requirement_rules: Iterable[GridRequirementRule] = (),
    enable_school_grid_requirements: bool = False,
) -> EligibilityResult:
    """Run deterministic eligibility gates with optional School-reference controls."""

    if profile.manual_review_reasons:
        return _gate_result(
            "discretion",
            "manual_review_required",
            tuple(profile.manual_review_reasons),
        )

    module_rows = list(modules)
    rule_rows = list(rules)
    source_rows = list(sources)
    if enable_school_grid_requirements:
        rule_rows = apply_grid_requirement_overrides(
            rule_rows,
            grid_requirement_rules,
            course_code,
            profile.programme_code,
        )
    programme_year_courses = programme_year_course_map(module_rows)
    initial_gates = (
        lambda: check_source(
            course_code,
            profile,
            module_rows,
            rule_rows,
            source_rows,
            source_root,
        ),
        lambda: check_programme(course_code, profile, module_rows),
    )
    trace: tuple[EligibilityTrace, ...] = ()
    for gate in initial_gates:
        result = gate()
        trace += result.rule_trace
        if not result.eligible:
            return replace(result, rule_trace=trace)

    constraint_gates = (
        lambda: check_prerequisites(
            course_code, profile, rule_rows, programme_year_courses
        ),
        lambda: check_corequisites(
            course_code, profile, rule_rows, programme_year_courses
        ),
        lambda: check_exclusions(
            course_code, profile, rule_rows, programme_year_courses
        ),
    )
    if not enable_timetable_clashes:
        for gate in constraint_gates:
            result = gate()
            trace += result.rule_trace
            if not result.eligible:
                return replace(result, rule_trace=trace)
        return EligibilityResult("eligible", (), rule_trace=trace)

    results = []
    for gate in (
        constraint_gates[0],
        constraint_gates[1],
        lambda: check_timetable_clashes(course_code, profile, clash_rules),
        constraint_gates[2],
    ):
        result = gate()
        results.append(result)
        trace += result.rule_trace

    hard_failures = [result for result in results if result.decision == "ineligible"]
    if hard_failures:
        return EligibilityResult(
            "ineligible",
            tuple(reason for result in hard_failures for reason in result.reasons),
            rule_trace=trace,
        )
    manual = [result for result in results if result.manual_review_required]
    if manual:
        evidence_issues = tuple(
            issue for result in manual for issue in result.evidence_issues
        )
        return EligibilityResult(
            "manual_review_required",
            tuple(reason for result in manual for reason in result.reasons),
            rule_trace=trace,
            evidence_issues=evidence_issues,
            manual_review_package={
                "reason": manual[0].reasons[0],
                "affected_rules": [
                    rule_id
                    for result in manual
                    for item in result.rule_trace
                    for rule_id in item.rule_ids
                ],
                "evidence_issues": list(evidence_issues),
            },
        )
    unresolved = [result for result in results if result.needs_clarification]
    if unresolved:
        return replace(unresolved[0], rule_trace=trace)
    return EligibilityResult("eligible", (), rule_trace=trace)


def _check_requirement_rules(
    course_code: str,
    profile: StudentProfile,
    rules: Iterable[dict[str, str]],
    rule_type: str,
    accepted_states: frozenset[ModuleFactState],
    legacy_absence_is_unknown: bool,
    programme_year_courses: ProgrammeYearCourses | None = None,
) -> EligibilityResult:
    matching_rules = _rules_for_course(rules, course_code, rule_type, profile)
    evaluations: list[tuple[dict[str, str], RequirementEvaluation]] = []
    for rule in matching_rules:
        condition, error = _condition_for_rule(rule)
        if error:
            evaluations.append(
                (rule, RequirementEvaluation("invalid", error=error))
            )
            continue
        evaluations.append(
            (
                rule,
                _evaluate_for_profile(
                    condition,
                    profile,
                    accepted_states,
                    programme_year_courses,
                    legacy_absence_is_unknown=legacy_absence_is_unknown,
                ),
            )
        )

    invalid = [(rule, result) for rule, result in evaluations if result.status == "invalid"]
    if invalid:
        reasons = tuple(
            result.error
            or f"Rule {rule.get('rule_id', '<unknown>')} has invalid condition data."
            for rule, result in invalid
        )
        return _gate_result(
            rule_type,
            "manual_review_required",
            reasons,
            rule_ids=tuple(rule.get("rule_id", "<unknown>") for rule, _ in invalid),
            evidence_issues=reasons,
        )

    unsatisfied = [
        (rule, result)
        for rule, result in evaluations
        if result.status == "unsatisfied"
    ]
    if unsatisfied:
        return _gate_result(
            rule_type,
            "ineligible",
            tuple(
                reason
                for rule, result in unsatisfied
                for reason in _requirement_failure_reasons(
                    rule, result.unsatisfied_predicates, course_code, rule_type
                )
            ),
            rule_ids=tuple(rule["rule_id"] for rule, _ in unsatisfied),
            blocking_modules=tuple(
                dict.fromkeys(
                    code
                    for _, result in unsatisfied
                    for code in result.unsatisfied_predicates
                )
            ),
        )

    unknown = [
        (rule, result)
        for rule, result in evaluations
        if result.status == "unknown"
    ]
    if unknown:
        unresolved = tuple(
            dict.fromkeys(
                code
                for _, result in unknown
                for code in result.unresolved_predicates
            )
        )
        return _gate_result(
            rule_type,
            "needs_clarification",
            tuple(
                f"{rule_type.capitalize()} rule {rule['rule_id']} is not satisfied."
                for rule, _ in unknown
            ),
            rule_ids=tuple(rule["rule_id"] for rule, _ in unknown),
            unresolved_predicates=unresolved,
            blocking_modules=unresolved,
        )
    return _gate_result(
        rule_type,
        "eligible",
        rule_ids=tuple(
            rule.get("rule_id", "<unknown>")
            for rule in matching_rules
        ),
    )


def _requirement_failure_reasons(
    rule: Mapping[str, str],
    missing_codes: tuple[str, ...],
    target_course_code: str,
    rule_type: str,
) -> tuple[str, ...]:
    """Explain School-grid failures atomically with their institutional citations."""

    if rule.get("source_id") != "EIE_REG_GRID_2026":
        return (f"{rule_type.capitalize()} rule {rule['rule_id']} is not satisfied.",)
    sheet = rule.get("source_sheet", "")
    citation = "EIE_REG_GRID_2026"
    if sheet:
        citation += f", sheet '{sheet}'"
    page = rule.get("handbook_page", "")
    if page:
        citation += f"; EBE_2026 p.{page}"
    if rule_type == "prerequisite":
        return tuple(
            f"{rule['rule_id']}: {code} is required before {target_course_code} and is not "
            f"listed as completed ({citation})."
            for code in missing_codes
        )
    return tuple(
        f"{rule['rule_id']}: {code} must be taken with {target_course_code} and is not "
        f"completed, current or planned ({citation})."
        for code in missing_codes
    )


def _evaluate_for_profile(
    condition: object,
    profile: StudentProfile,
    accepted_states: frozenset[ModuleFactState],
    programme_year_courses: ProgrammeYearCourses | None,
    *,
    legacy_absence_is_unknown: bool,
) -> RequirementEvaluation:
    return evaluate_requirement(
        condition,
        lambda code: profile.module_state(
            code, legacy_absence_is_unknown=legacy_absence_is_unknown
        ),
        accepted_states,
        programme_year_courses,
    )


def _gate_result(
    gate: str,
    decision: EligibilityDecision,
    reasons: tuple[str, ...] = (),
    *,
    rule_ids: tuple[str, ...] = (),
    unresolved_predicates: tuple[str, ...] = (),
    evidence_issues: tuple[str, ...] = (),
    blocking_modules: tuple[str, ...] = (),
) -> EligibilityResult:
    """Build one internally consistent gate result."""

    clarification = None
    if decision == "needs_clarification":
        target = unresolved_predicates[0] if unresolved_predicates else None
        clarification = {
            "reason": reasons[0] if reasons else "A required student fact is missing.",
            "unresolved_predicates": list(unresolved_predicates),
            "target_predicate": target,
            "target_predicates": list(unresolved_predicates),
            "gate": gate,
            "question": _clarification_question(gate, target, unresolved_predicates),
            "options": (
                list(_clarification_options(gate, len(unresolved_predicates) > 1))
                if target
                else []
            ),
        }

    manual_review_package = None
    if decision == "manual_review_required":
        manual_review_package = {
            "reason": reasons[0] if reasons else "Academic review is required.",
            "affected_rules": list(rule_ids),
            "evidence_issues": list(evidence_issues),
        }

    return EligibilityResult(
        decision=decision,
        reasons=reasons,
        rule_trace=(
            EligibilityTrace(
                gate=gate,
                decision=decision,
                reasons=reasons,
                rule_ids=rule_ids,
                blocking_modules=blocking_modules,
            ),
        ),
        unresolved_predicates=unresolved_predicates,
        evidence_issues=evidence_issues,
        clarification=clarification,
        manual_review_package=manual_review_package,
    )


def _clarification_question(
    gate: str,
    course_code: str | None,
    all_codes: tuple[str, ...] = (),
) -> str:
    if course_code is None:
        return "Could you provide the missing module information?"
    if gate == "timetable_clash":
        if len(all_codes) > 1:
            listed = ", ".join(all_codes)
            return (
                f"{listed} share a timetable slot with this module. Are you repeating, "
                "currently taking or planning to take any of them? For example "
                f"'{all_codes[0]} repeating, the rest none'."
            )
        return (
            f"{course_code} shares a timetable slot with this module. Are you repeating it, "
            "currently taking it, planning to take it, or none of these?"
        )
    if len(all_codes) > 1:
        listed = ", ".join(all_codes)
        first, second = all_codes[0], all_codes[1]
        if gate == "prerequisite":
            return (
                f"Which of these have you completed: {listed}? Reply with a status for "
                f"each, for example '{first} completed, {second} not completed'."
            )
        return (
            f"What is your status for each of these: {listed}? Use completed, current, "
            f"planned concurrently or not completed, for example "
            f"'{first} completed, {second} planned'."
        )
    if gate == "prerequisite":
        return f"Have you completed {course_code}?"
    if gate == "corequisite":
        return (
            f"What is your status for {course_code}: completed, currently taking it, "
            "planning to take it concurrently, or not completed?"
        )
    if gate == "exclusion":
        return (
            f"Have you completed, are you currently taking, or are you planning "
            f"{course_code}?"
        )
    return f"What is your current status for {course_code}?"


def _clarification_options(gate: str, several: bool = False) -> tuple[str, ...]:
    if gate == "timetable_clash":
        return ("None of these",) if several else (
            "Repeating", "Current", "Planned", "None of these"
        )
    if several:
        return ("All completed", "None completed") if gate == "prerequisite" else ()
    if gate == "prerequisite":
        return ("Completed", "Not completed")
    if gate == "corequisite":
        return ("Completed", "Current", "Planned concurrently", "Not completed")
    if gate == "exclusion":
        return ("Completed", "Current", "Planned", "None of these")
    return ()


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
