"""Read-only repository over the validated CSV catalogue."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.advisor.normalisation import Alias
from app.data.loaders import CurriculumData, load_curriculum_data


class CsvCatalogueRepository:
    """Serve a validated in-memory snapshot of the processed CSV files."""

    backend_name = "csv"

    def __init__(self, data_directory: Path | str) -> None:
        self.data: CurriculumData = load_curriculum_data(data_directory)
        self._sources = {row["source_id"]: row for row in self.data.sources}
        self._audits = {row["course_id"]: row for row in self.data.course_audits}
        self._cbos = {
            row["course_code"]: row
            for row in self.data.cbo_courses
            if row["curriculum_status"] == "current"
        }
        self._missing_cbos = {
            row["course_code"]: row for row in self.data.missing_cbos
        }

    def is_healthy(self) -> bool:
        return True

    def get_aliases(self) -> tuple[Alias, ...]:
        return self.data.aliases

    def list_programmes(self) -> list[dict[str, str]]:
        programmes = {
            (row["programme_code"], row["programme_name"])
            for row in self.data.modules
        }
        return [
            {"programme_code": code, "programme_name": name}
            for code, name in sorted(programmes)
        ]

    def get_programme_profile(self, programme_code: str) -> dict[str, Any] | None:
        row = next(
            (
                profile
                for profile in self.data.programme_profiles
                if profile["programme_code"] == programme_code
            ),
            None,
        )
        if row is None:
            return None
        return {
            **row,
            "duration_years": int(row["duration_years"]),
            "study_mode": row["study_mode"].replace("_", " "),
            "career_opportunities": _split(row["career_opportunities"]),
            "source": self._source_summary(row["source_id"]),
        }

    def list_modules(
        self,
        programme_code: str,
        year_of_study: int | None = None,
    ) -> list[dict[str, Any]]:
        rows = [
            _module_membership(row)
            for row in self.data.modules
            if row["programme_code"] == programme_code
            and (year_of_study is None or int(row["year_of_study"]) == year_of_study)
        ]
        return sorted(rows, key=lambda row: (row["year_of_study"], row["course_code"]))

    def get_module(self, course_code: str) -> dict[str, Any] | None:
        memberships = [
            row for row in self.data.modules if row["course_code"] == course_code
        ]
        if not memberships:
            return None
        first = memberships[0]
        source_ids = {row["source_id"] for row in memberships}
        rules = [
            dict(row)
            for row in self.data.rules
            if row["target_course_code"] == course_code
        ]
        source_ids.update(row["source_id"] for row in rules)
        cbo = self._cbos.get(course_code)
        if cbo is not None:
            source_ids.add(cbo["source_id"])
        return {
            "course_code": course_code,
            "course_name": first["course_name"],
            "nqf_credits": int(first["nqf_credits"]),
            "nqf_level": first["nqf_level"],
            "memberships": [_module_membership(row) for row in memberships],
            "rules": rules,
            "course_information": self._course_information(first, cbo),
            "sources": [self._source_summary(source_id) for source_id in sorted(source_ids)],
        }

    def list_courses(
        self,
        category: str | None = None,
        interest: str | None = None,
        career: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        courses: list[dict[str, Any]] = []
        for course in self.data.courses:
            audit = self._audits.get(course["course_id"])
            source = self._sources.get(course["source_id"])
            if not _is_recommendable(audit, source):
                continue
            interests = _split(course["interest_tags"])
            careers = _split(course["career_tags"])
            if category and course["category"] != category:
                continue
            if interest and interest not in interests:
                continue
            if career and career not in careers:
                continue
            courses.append(_course_record(course))
        return sorted(
            courses,
            key=lambda row: (-row["rating_mean"], -row["rating_count"], row["course_id"]),
        )[:limit]

    def get_course(self, course_id: str) -> dict[str, Any] | None:
        for course in self.list_courses(limit=100):
            if course["course_id"] == course_id:
                source = self._sources[course["source_id"]]
                audit = self._audits[course_id]
                return {
                    **course,
                    "source": self._source_summary(course["source_id"]),
                    "audit": dict(audit),
                    "verification_notes": source["verification_notes"],
                }
        return None

    def catalogue_summary(self) -> dict[str, Any]:
        courses = self.list_courses(limit=100)
        verified_sources = sum(
            source["verification_status"] == "verified"
            for source in self.data.sources
        )
        return {
            "programmes": len(self.list_programmes()),
            "module_memberships": len(self.data.modules),
            "unique_modules": len({row["course_code"] for row in self.data.modules}),
            "rules": len(self.data.rules),
            "recommendable_courses": len(courses),
            "providers": len({course["provider"] for course in courses}),
            "verified_sources": verified_sources,
            "external_references": len(self.data.external_references),
            "cbo_covered_modules": len(self._cbos),
            "missing_cbos": len(self.data.missing_cbos),
            "orphan_cbos": sum(
                row["curriculum_status"] == "not_in_current_curriculum"
                for row in self.data.cbo_courses
            ),
            "categories": sorted({course["category"] for course in courses}),
        }

    def career_paths(self) -> list[dict[str, Any]]:
        paths: dict[str, list[dict[str, Any]]] = {}
        for course in self.list_courses(limit=100):
            for career in course["career_tags"]:
                paths.setdefault(career, []).append(course)
        return [
            {
                "career_tag": career,
                "display_name": career.replace("_", " ").title(),
                "course_count": len(courses),
                "courses": courses,
                "related_interests": sorted(
                    {tag for course in courses for tag in course["interest_tags"]}
                ),
            }
            for career, courses in sorted(paths.items())
        ]

    def evidence(self) -> dict[str, Any]:
        return {
            "summary": self.catalogue_summary(),
            "sources": [
                self._source_summary(source["source_id"])
                | {
                    "document_type": source["document_type"],
                    "authority": source["authority"],
                    "review_date": source["review_date"],
                    "verification_notes": source["verification_notes"],
                }
                for source in self.data.sources
            ],
            "external_references": [dict(row) for row in self.data.external_references],
            "missing_cbos": [dict(row) for row in self.data.missing_cbos],
            "orphan_cbos": [
                dict(row)
                for row in self.data.cbo_courses
                if row["curriculum_status"] == "not_in_current_curriculum"
            ],
            "rule_counts": _count_values(self.data.rules, "rule_type"),
            "source_status_counts": _count_values(
                self.data.sources, "verification_status"
            ),
        }

    def list_missing_cbos(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self.data.missing_cbos]

    def _course_information(
        self,
        module: dict[str, str],
        cbo: dict[str, str] | None,
    ) -> dict[str, Any]:
        if cbo is None:
            missing = self._missing_cbos.get(module["course_code"])
            return {
                "cbo_available": False,
                "lecturer": None,
                "course_coordinator": None,
                "hours": {
                    "credits": int(module["nqf_credits"]),
                    "notional_hours_total": int(module["nqf_credits"]) * 10,
                    "weekly_workload_guidance": None,
                    "contact_pattern": None,
                    "basis": "1 NQF credit represents 10 notional learning hours; this is not a weekly-hour value.",
                },
                "scope": None,
                "prescribed_materials": None,
                "additional_materials": None,
                "source_id": None,
                "academic_year": None,
                "missing_reason": missing["notes"] if missing else "No verified CBO record is available.",
                "missing_status": missing["status"] if missing else "untracked",
                "candidate_filename": missing["candidate_filename"] if missing else None,
            }
        return {
            "cbo_available": True,
            "lecturer": cbo["academic_staff"],
            "course_coordinator": cbo["course_coordinator"],
            "hours": {
                "credits": int(cbo["credits"]),
                "notional_hours_total": int(cbo["notional_hours_total"]),
                "weekly_workload_guidance": cbo["weekly_workload_guidance"],
                "contact_pattern": cbo["contact_pattern"],
                "basis": "1 NQF credit represents 10 notional learning hours; explicit weekly guidance is quoted separately from the available course evidence.",
            },
            "scope": cbo["scope"],
            "prescribed_materials": cbo["prescribed_materials"],
            "additional_materials": cbo["additional_materials"],
            "source_id": cbo["source_id"],
            "academic_year": int(cbo["academic_year"]),
            "verification_status": cbo["verification_status"],
            "evidence_notes": cbo["evidence_notes"],
            "missing_reason": None,
        }

    def eligibility_context(
        self, course_code: str
    ) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
        # Grouped prerequisite expressions need programme-year membership context.
        modules = [dict(row) for row in self.data.modules]
        rules = [
            dict(row)
            for row in self.data.rules
            if row["target_course_code"] == course_code
        ]
        source_ids = {
            row["source_id"] for row in [*modules, *rules] if row.get("source_id")
        }
        # Optional School-grid overrides need their source in the same evidence context.
        if "EIE_REG_GRID_2026" in self._sources:
            source_ids.add("EIE_REG_GRID_2026")
        sources = [dict(self._sources[source_id]) for source_id in source_ids]
        return modules, rules, sources

    def _source_summary(self, source_id: str) -> dict[str, str]:
        source = self._sources[source_id]
        return {
            "source_id": source_id,
            "title": source["title"],
            "publisher": source["publisher"],
            "local_path": source["local_path"],
            "url": source["url"],
            "verification_status": source["verification_status"],
            "locator": source["locator"],
        }


def _module_membership(row: dict[str, str]) -> dict[str, Any]:
    return {
        "programme_code": row["programme_code"],
        "programme_name": row["programme_name"],
        "year_of_study": int(row["year_of_study"]),
        "course_code": row["course_code"],
        "course_name": row["course_name"],
        "nqf_credits": int(row["nqf_credits"]),
        "nqf_level": row["nqf_level"],
        "requirement_type": row["requirement_type"],
        "selection_group": row["selection_group"] or None,
        "selection_count": int(row["selection_count"]) if row["selection_count"] else None,
        "source_id": row["source_id"],
        "handbook_page": int(row["handbook_page"]),
    }


def _course_record(row: dict[str, str]) -> dict[str, Any]:
    return {
        **row,
        "outcomes": _split(row["outcomes"]),
        "topic_tags": _split(row["topic_tags"]),
        "interest_tags": _split(row["interest_tags"]),
        "career_tags": _split(row["career_tags"]),
        "rating_mean": float(row["rating_mean"]),
        "rating_count": int(row["rating_count"]),
        "rating_scale": int(row["rating_scale"]),
    }


def _is_recommendable(
    audit: dict[str, str] | None, source: dict[str, str] | None
) -> bool:
    return bool(
        audit
        and source
        and audit["availability_status"] == "available"
        and audit["verification_status"] == "verified"
        and audit["recommendation_status"] == "recommendable"
        and source["verification_status"] == "verified"
    )


def _split(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def _count_values(
    rows: tuple[dict[str, str], ...], field: str
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = row[field]
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))
