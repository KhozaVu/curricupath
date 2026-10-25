"""Deterministic application service for catalogue and eligibility requests."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
import re
from typing import Any, Protocol

from app.advisor.eligibility import (
    ModuleFactState,
    StudentProfile,
    _condition_for_rule,
    _scope_applies,
    apply_grid_requirement_overrides,
    check_eligibility,
    load_clash_rules,
    load_grid_requirement_rules,
    normalise_rule_course_code,
    programme_year_course_map,
    requirement_satisfied,
)
from app.advisor.module_resolution import ModuleNameMatch, match_module_names
from app.advisor.normalisation import Alias


class Repository(Protocol):
    backend_name: str

    def is_healthy(self) -> bool: ...

    def get_aliases(self) -> tuple[Alias, ...]: ...

    def list_programmes(self) -> list[dict[str, Any]]: ...

    def get_programme_profile(self, programme_code: str) -> dict[str, Any] | None: ...

    def list_modules(
        self, programme_code: str, year_of_study: int | None = None
    ) -> list[dict[str, Any]]: ...

    def get_module(self, course_code: str) -> dict[str, Any] | None: ...

    def get_course(self, course_id: str) -> dict[str, Any] | None: ...

    def list_courses(
        self,
        category: str | None = None,
        interest: str | None = None,
        career: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]: ...

    def eligibility_context(
        self, course_code: str
    ) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]: ...

    def catalogue_summary(self) -> dict[str, Any]: ...

    def career_paths(self) -> list[dict[str, Any]]: ...

    def evidence(self) -> dict[str, Any]: ...

    def list_missing_cbos(self) -> list[dict[str, Any]]: ...


class CurricuPathService:
    """Coordinate fixed backend operations without language-model decisions."""

    def __init__(
        self,
        repository: Repository,
        source_root: str,
        *,
        timetable_clash_gate_enabled: bool = False,
        school_grid_requirements_enabled: bool = False,
    ) -> None:
        self.repository = repository
        self.source_root = source_root
        self.timetable_clash_gate_enabled = timetable_clash_gate_enabled
        self.school_grid_requirements_enabled = school_grid_requirements_enabled
        clash_path = Path(source_root) / "data" / "rules" / "grid_clash_rules.csv"
        self.clash_rules = (
            load_clash_rules(clash_path) if timetable_clash_gate_enabled else ()
        )
        grid_path = Path(source_root) / "data" / "rules" / "grid_rules.json"
        self.grid_requirement_rules = (
            load_grid_requirement_rules(grid_path)
            if school_grid_requirements_enabled
            else ()
        )

    def health(self) -> dict[str, str]:
        return {"status": "ok" if self.repository.is_healthy() else "unavailable"}

    def programmes(self) -> list[dict[str, Any]]:
        return self.repository.list_programmes()

    def programme_profile(self, programme_code: str) -> dict[str, Any] | None:
        return self.repository.get_programme_profile(programme_code.upper())

    def modules(
        self, programme_code: str, year_of_study: int | None
    ) -> list[dict[str, Any]]:
        return self.repository.list_modules(programme_code, year_of_study)

    def programme_credit_summary(self, programme_code: str) -> dict[str, Any]:
        """Calculate catalogue credits while respecting elective selection rules."""

        programme = programme_code.upper()
        modules = self.repository.list_modules(programme)
        if not modules:
            return {"programme_code": programme, "programme_name": programme, "total_nqf_credits": 0, "years": []}

        years: list[dict[str, Any]] = []
        for year in sorted({int(module["year_of_study"]) for module in modules}):
            memberships = [module for module in modules if int(module["year_of_study"]) == year]
            compulsory_credits = sum(int(module["nqf_credits"]) for module in memberships if module["requirement_type"] == "compulsory")
            elective_groups: dict[str, list[dict[str, Any]]] = {}
            for module in memberships:
                if module["requirement_type"] == "elective_pool" and module.get("selection_group"):
                    elective_groups.setdefault(module["selection_group"], []).append(module)
            elective_requirements = []
            for group, options in sorted(elective_groups.items()):
                first = options[0]
                credits_each = int(first["nqf_credits"])
                choices_required = int(first.get("selection_count") or 0)
                elective_requirements.append({"selection_group": group, "choices_required": choices_required, "credits_each": credits_each, "required_credits": choices_required * credits_each})
            elective_credits = sum(item["required_credits"] for item in elective_requirements)
            years.append({"year_of_study": year, "compulsory_credits": compulsory_credits, "elective_credits": elective_credits, "total_credits": compulsory_credits + elective_credits, "elective_requirements": elective_requirements})

        return {"programme_code": programme, "programme_name": modules[0]["programme_name"], "total_nqf_credits": sum(year["total_credits"] for year in years), "years": years}

    def module(self, course_code: str) -> dict[str, Any] | None:
        code = self._resolve_module_code(course_code)
        module = self.repository.get_module(code)
        if module is None:
            return None

        result = dict(module)
        result["rules"] = [self._present_rule(rule) for rule in module.get("rules", [])]
        return result

    def module_name_matches(
        self, query: str, programme_code: str | None = None
    ) -> tuple[ModuleNameMatch, ...]:
        """Resolve free-text module names within a programme when one is known."""

        if programme_code:
            modules = self.repository.list_modules(programme_code.upper())
        else:
            modules = [
                module
                for programme in self.repository.list_programmes()
                for module in self.repository.list_modules(
                    programme["programme_code"]
                )
            ]
        return match_module_names(query, modules)

    def course(self, course_id: str) -> dict[str, Any] | None:
        return self.repository.get_course(course_id.upper())

    def summary(self) -> dict[str, Any]:
        retired = {"recommendable_courses", "providers", "categories", "semantic_public_course_search_enabled"}
        summary = {**{k:v for k,v in self.repository.catalogue_summary().items() if k not in retired}, "storage_backend": self.repository.backend_name}
        summary["verified_sources"] = sum(r.get("verification_status")=="verified" for r in self.repository.evidence().get("sources",[]) if r.get("document_type") != "public_course_provider")
        return summary

    def career_paths(self) -> list[dict[str, Any]]:
        return self.repository.career_paths()

    def evidence(self) -> dict[str, Any]:
        result = self.repository.evidence()
        result["summary"] = self.summary()
        result["sources"] = [r for r in result["sources"] if r.get("document_type") != "public_course_provider"]
        result["source_status_counts"] = {state:sum(r.get("verification_status")==state for r in result["sources"]) for state in {r.get("verification_status") for r in result["sources"]}}
        result["summary"]["verified_sources"] = sum(r.get("verification_status")=="verified" for r in result["sources"])
        return result

    def missing_cbos(self) -> list[dict[str, Any]]:
        return self.repository.list_missing_cbos()

    def courses(
        self,
        category: str | None,
        interest: str | None,
        career: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        return self.repository.list_courses(category, interest, career, limit)

    def programme_graph(self, programme_code: str) -> dict[str, Any]:
        """Modules of a programme and the recorded prerequisite/corequisite links between them.

        Built from the same rule rows (and, when enabled, the same School-grid overrides) that the
        eligibility gates use. Nothing is inferred: a module with no recorded rule has no edge, and
        grouped conditions such as "all Year 3 modules" are not expanded into edges.
        """

        programme = programme_code.upper()
        nodes: dict[str, dict[str, Any]] = {}
        for module in self.repository.list_modules(programme):
            code = str(module["course_code"]).upper()
            nodes.setdefault(code, {
                "course_code": code,
                "course_name": module.get("course_name"),
                "year_of_study": module.get("year_of_study"),
                "requirement_type": module.get("requirement_type"),
            })
        edges: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        for target in nodes:
            _, rules, _ = self.repository.eligibility_context(target)
            if self.school_grid_requirements_enabled:
                rules = apply_grid_requirement_overrides(
                    rules, self.grid_requirement_rules, target, programme
                )
            for rule in rules:
                kind = rule.get("rule_type")
                if kind not in {"prerequisite", "corequisite"}:
                    continue
                if not _scope_applies(rule.get("scope", ""), programme):
                    continue
                condition, error = _condition_for_rule(rule)
                if error:
                    continue
                for source in _codes_in_condition(condition):
                    key = (source, target, kind)
                    if source in nodes and source != target and key not in seen:
                        seen.add(key)
                        edges.append({"from": source, "to": target, "kind": kind,
                                      "rule_id": rule.get("rule_id", "")})
        return {"programme_code": programme, "nodes": list(nodes.values()), "edges": edges}

    def eligibility(
        self,
        course_code: str,
        programme_code: str,
        completed_modules: set[str],
        current_modules: set[str],
        planned_modules: set[str],
        manual_review_reasons: tuple[str, ...] = (),
        module_states: dict[str, ModuleFactState] | None = None,
        module_history_confirmed: bool | None = None,
        *,
        repeating_modules: set[str] | None = None,
        clash_cleared_modules: set[str] | None = None,
    ) -> dict[str, Any]:
        code = self._resolve_module_code(course_code)
        profile = StudentProfile(
            programme_code=programme_code.upper(),
            completed_modules=frozenset(value.upper() for value in completed_modules),
            current_modules=frozenset(value.upper() for value in current_modules),
            planned_modules=frozenset(value.upper() for value in planned_modules),
            repeating_modules=frozenset(
                value.upper() for value in (repeating_modules or set())
            ),
            clash_cleared_modules=frozenset(
                value.upper() for value in (clash_cleared_modules or set())
            ),
            manual_review_reasons=manual_review_reasons,
            module_states={
                code.upper(): state for code, state in (module_states or {}).items()
            },
            module_history_confirmed=module_history_confirmed,
        )
        modules, rules, sources = self.repository.eligibility_context(code)
        result = check_eligibility(
            code,
            profile,
            modules,
            rules,
            sources,
            source_root=self.source_root,
            clash_rules=self.clash_rules,
            enable_timetable_clashes=self.timetable_clash_gate_enabled,
            grid_requirement_rules=self.grid_requirement_rules,
            enable_school_grid_requirements=self.school_grid_requirements_enabled,
        )
        completed = code in profile.completed_modules
        effective_rules = (
            apply_grid_requirement_overrides(
                rules,
                self.grid_requirement_rules,
                code,
                profile.programme_code,
            )
            if self.school_grid_requirements_enabled
            else rules
        )
        requirements = self._requirement_summary(profile, effective_rules, modules)
        return {
            "course_code": code,
            "programme_code": profile.programme_code,
            "decision": result.decision,
            "eligible": result.eligible,
            "completed": completed,
            "repeating_modules": sorted(profile.repeating_modules),
            "available_to_take": result.eligible and not completed,
            "reasons": list(result.reasons),
            "needs_clarification": result.needs_clarification,
            "manual_review_required": result.manual_review_required,
            "rule_trace": [asdict(entry) for entry in result.rule_trace],
            "unresolved_predicates": list(result.unresolved_predicates),
            "evidence_issues": list(result.evidence_issues),
            "clarification": result.clarification,
            "manual_review_package": result.manual_review_package,
            "module_states": dict(profile.module_states or {}),
            "module_history_confirmed": profile.module_history_confirmed,
            "requirements": requirements,
            "requirement_modules": self._requirement_modules(
                profile, effective_rules, modules
            ),
            **self._evidence_for_result(code, result, effective_rules, sources),
        }

    def _evidence_for_result(
        self,
        code: str,
        result: Any,
        rules: list[dict[str, str]],
        sources: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Rules and sources behind an eligibility answer, so the UI can cite them."""

        shown = []
        for rule in rules:
            if rule.get("target_course_code") != code or rule.get("rule_type") not in {
                "prerequisite",
                "corequisite",
                "exclusion",
            }:
                continue
            presented = self._present_rule(rule)
            shown.append(
                {
                    "rule_id": str(presented.get("rule_id", "")),
                    "rule_type": str(presented.get("rule_type", "")),
                    "source_id": str(presented.get("source_id", "")),
                    "handbook_page": str(presented.get("handbook_page") or ""),
                    "plain_language": str(presented.get("plain_language", "")),
                }
            )
        used = {rule["source_id"] for rule in shown if rule.get("source_id")}
        clash_ids = {
            rule_id
            for step in result.rule_trace
            if step.gate == "timetable_clash"
            for rule_id in step.rule_ids
        }
        for clash in self.clash_rules:
            if clash.get("rule_id") not in clash_ids:
                continue
            ids = [value for value in clash.get("source_ids", "").split(";") if value]
            used.update(ids)
            shown.append(
                {
                    "rule_id": clash["rule_id"],
                    "rule_type": "timetable_clash",
                    "source_id": ids[0] if ids else "",
                    "plain_language": (
                        f"{clash.get('target_course_code', '')} clashes in the timetable "
                        f"with {clash.get('repeating_course', '')} "
                        f"({clash.get('clash_type', 'timetable')} clash)."
                    ),
                }
            )
        return {
            "rules": shown,
            "sources": [
                {
                    key: str(source.get(key) or "")
                    for key in (
                        "source_id",
                        "title",
                        "publisher",
                        "url",
                        "verification_status",
                        "locator",
                    )
                }
                for source in sources
                if source.get("source_id") in used
            ],
        }

    def _requirement_modules(
        self,
        profile: StudentProfile,
        rules: list[dict[str, str]],
        modules: list[dict[str, str]],
    ) -> dict[str, list[dict[str, Any]]]:
        """Each module named by a prerequisite/corequisite rule, with whether it is met."""

        available_by_type = {
            "prerequisite": set(profile.completed_modules),
            "corequisite": (
                set(profile.completed_modules)
                | set(profile.current_modules)
                | set(profile.planned_modules)
            ),
        }
        programme_year_courses = programme_year_course_map(modules)
        out: dict[str, list[dict[str, Any]]] = {
            "prerequisites": [],
            "corequisites": [],
        }
        for rule_type, key in (
            ("prerequisite", "prerequisites"),
            ("corequisite", "corequisites"),
        ):
            for rule in rules:
                if rule.get("rule_type") != rule_type or not _scope_applies(
                    rule.get("scope", ""), profile.programme_code
                ):
                    continue
                try:
                    condition = json.loads(rule["condition_json"])
                except (KeyError, json.JSONDecodeError):
                    continue
                for code in _condition_codes(condition):
                    if any(item["code"] == code for item in out[key]):
                        continue
                    out[key].append(
                        {
                            "code": code,
                            "name": self._module_name(code),
                            "met": requirement_satisfied(
                                code,
                                available_by_type[rule_type],
                                programme_year_courses,
                            ),
                        }
                    )
        return out

    def _requirement_summary(
        self,
        profile: StudentProfile,
        rules: list[dict[str, str]],
        modules: list[dict[str, str]],
    ) -> dict[str, list[dict[str, Any]]]:
        available_by_type = {
            "prerequisite": set(profile.completed_modules),
            "corequisite": (
                set(profile.completed_modules)
                | set(profile.current_modules)
                | set(profile.planned_modules)
            ),
        }
        summary: dict[str, list[dict[str, Any]]] = {
            "prerequisites": [],
            "corequisites": [],
        }
        programme_year_courses = programme_year_course_map(modules)
        for rule_type, output_key in (
            ("prerequisite", "prerequisites"),
            ("corequisite", "corequisites"),
        ):
            for rule in rules:
                if (
                    rule.get("rule_type") != rule_type
                    or not _scope_applies(rule.get("scope", ""), profile.programme_code)
                ):
                    continue
                try:
                    condition = json.loads(rule["condition_json"])
                except (KeyError, json.JSONDecodeError):
                    continue
                summary[output_key].append(
                    {
                        "rule_id": rule["rule_id"],
                        "description": _describe_requirement(
                            condition, self._module_label
                        ),
                        "satisfied": requirement_satisfied(
                            condition,
                            available_by_type[rule_type],
                            programme_year_courses,
                        ),
                        "source_id": rule["source_id"],
                    }
                )
        return summary

    def _module_name(self, course_code: str) -> str:
        module = self.repository.get_module(course_code)
        return module["course_name"] if module else ""

    def _module_label(self, course_code: str) -> str:
        module = self.repository.get_module(course_code)
        if module is None:
            return course_code
        return f"{course_code} ({module['course_name']})"

    def _present_rule(self, rule: dict[str, Any]) -> dict[str, Any]:
        """Add deterministic plain language without discarding the source rule."""

        presented = dict(rule)
        try:
            condition = json.loads(str(rule["condition_json"]))
            description = _describe_requirement(condition, self._module_label)
        except (KeyError, json.JSONDecodeError, TypeError):
            description = "a curriculum requirement that could not be displayed"
        presented["condition_description"] = description
        presented["plain_language"] = _plain_language_rule(
            str(rule.get("rule_type", "rule")),
            str(rule.get("scope", "")),
            description,
        )
        return presented

    def _resolve_module_code(self, course_code: str) -> str:
        """Resolve the optional handbook suffix without guessing unknown codes."""

        code = course_code.strip().upper()
        if self.repository.get_module(code) is not None:
            return code
        suffixed = f"{code}A"
        if not code.endswith("A") and self.repository.get_module(suffixed) is not None:
            return suffixed
        return code


def _condition_codes(condition: object) -> list[str]:
    """Module codes named anywhere in a rule condition, in source order."""

    if isinstance(condition, str):
        return [condition]
    codes: list[str] = []
    if isinstance(condition, dict):
        for value in condition.values():
            if isinstance(value, list):
                for child in value:
                    codes.extend(_condition_codes(child))
    return list(dict.fromkeys(codes))


def _scope_applies(scope: str, programme_code: str) -> bool:
    return scope in {"ALL", "ALL_EFA03_EFA04"} or programme_code in scope.split("|")


def _describe_requirement(condition: object, module_label) -> str:
    if isinstance(condition, str):
        return module_label(condition)
    if isinstance(condition, list):
        return " and ".join(
            _describe_requirement(item, module_label) for item in condition
        )
    if isinstance(condition, dict):
        if "all_of" in condition:
            parts = []
            for item in condition["all_of"]:
                description = _describe_requirement(item, module_label)
                if isinstance(item, dict) and "any_of" in item:
                    description = f"({description})"
                parts.append(description)
            return " and ".join(parts)
        if "any_of" in condition:
            choices_list = []
            for item in condition["any_of"]:
                description = _describe_requirement(item, module_label)
                if isinstance(item, dict) and "all_of" in item:
                    description = f"({description})"
                choices_list.append(description)
            choices = " or ".join(choices_list)
            return f"either {choices}"
        programme_year = condition.get("all_courses_in_programme_year")
        if isinstance(programme_year, dict):
            return (
                f"all {programme_year.get('programme', 'programme')} Year "
                f"{programme_year.get('year', '?')} modules"
            )
    return "an unrecognized curriculum requirement"


def _plain_language_rule(rule_type: str, scope: str, description: str) -> str:
    scope_text = _plain_language_scope(scope)
    if rule_type == "prerequisite":
        requirement = (
            f"Before registering for this module, you must have completed {description}."
        )
    elif rule_type == "corequisite":
        requirement = (
            "You must have completed, currently be taking, or plan to take "
            f"{description} at the same time."
        )
    elif rule_type == "exclusion":
        requirement = f"You may not take this module when {description} applies."
    else:
        requirement = f"This module is subject to {description}."
    if scope_text:
        requirement = f"{requirement[:1].lower()}{requirement[1:]}"
    return f"{scope_text}{requirement}"


def _plain_language_scope(scope: str) -> str:
    if scope in {"", "ALL", "ALL_EFA03_EFA04"}:
        return ""
    programmes = [part for part in scope.split("|") if part.startswith("EFA")]
    if not programmes:
        return ""
    if len(programmes) == 1:
        label = programmes[0]
    else:
        label = " and ".join(programmes)
    return f"For {label} students, "


def _codes_in_condition(condition: object) -> list[str]:
    """Module codes named anywhere in a nested all_of / any_of condition."""

    found: dict[str, None] = {}

    def walk(node: object) -> None:
        if isinstance(node, str):
            code = normalise_rule_course_code(node)
            if code and re.fullmatch(r"[A-Z]{4}\d{4}[A-Z]", code):
                found[code] = None
        elif isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                walk(value)

    walk(condition)
    return list(found)
