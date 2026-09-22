"""Read-only PostgreSQL repository for the imported CurricuPath catalogue."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.advisor.normalisation import Alias
from app.data.repository import _course_record, _module_membership, _split
from app.data.schema import (
    aliases as aliases_table,
    course_audits,
    curriculum_memberships,
    external_references,
    missing_cbos,
    module_offerings,
    modules,
    programme_profiles,
    public_courses,
    rules,
    sources,
)


class PostgresCatalogueRepository:
    """Serve the catalogue from PostgreSQL while preserving the CSV API contract."""

    backend_name = "postgresql"

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def is_healthy(self) -> bool:
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                return bool(
                    connection.scalar(
                        select(func.count()).select_from(modules)
                    )
                )
        except SQLAlchemyError:
            return False

    def get_aliases(self) -> tuple[Alias, ...]:
        statement = select(
            aliases_table.c.alias,
            aliases_table.c.canonical_tag,
            aliases_table.c.tag_type,
        ).order_by(aliases_table.c.alias)
        with self.engine.connect() as connection:
            rows = connection.execute(statement).mappings()
            return tuple(
                Alias(row["alias"], row["canonical_tag"], row["tag_type"])
                for row in rows
            )

    def list_programmes(self) -> list[dict[str, str]]:
        statement = (
            select(
                curriculum_memberships.c.programme_code,
                curriculum_memberships.c.programme_name,
            )
            .distinct()
            .order_by(curriculum_memberships.c.programme_code)
        )
        with self.engine.connect() as connection:
            return [dict(row) for row in connection.execute(statement).mappings()]

    def get_programme_profile(self, programme_code: str) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                select(programme_profiles).where(
                    programme_profiles.c.programme_code == programme_code
                )
            ).mappings().first()
            if row is None:
                return None
            source = connection.execute(
                select(sources).where(sources.c.source_id == row["source_id"])
            ).mappings().one()
        profile = _normalise_row(row)
        return {
            **profile,
            "study_mode": profile["study_mode"].replace("_", " "),
            "career_opportunities": _split(profile["career_opportunities"]),
            "source": _source_summary(source),
        }

    def list_modules(
        self,
        programme_code: str,
        year_of_study: int | None = None,
    ) -> list[dict[str, Any]]:
        statement = self._membership_statement().where(
            curriculum_memberships.c.programme_code == programme_code
        )
        if year_of_study is not None:
            statement = statement.where(
                curriculum_memberships.c.year_of_study == year_of_study
            )
        statement = statement.order_by(
            curriculum_memberships.c.year_of_study,
            curriculum_memberships.c.course_code,
        )
        with self.engine.connect() as connection:
            return [
                _module_membership(dict(row))
                for row in connection.execute(statement).mappings()
            ]

    def get_module(self, course_code: str) -> dict[str, Any] | None:
        statement = self._membership_statement().where(
            curriculum_memberships.c.course_code == course_code
        )
        with self.engine.connect() as connection:
            memberships = [
                _module_membership(dict(row))
                for row in connection.execute(statement).mappings()
            ]
            if not memberships:
                return None
            rule_rows = [
                _rule_record(row)
                for row in connection.execute(
                    select(rules)
                    .where(rules.c.target_course_code == course_code)
                    .order_by(rules.c.rule_id)
                ).mappings()
            ]
            cbo = connection.execute(
                select(module_offerings)
                .where(
                    module_offerings.c.module_code == course_code,
                    module_offerings.c.curriculum_status == "current",
                )
                .order_by(module_offerings.c.academic_year.desc())
                .limit(1)
            ).mappings().first()
            missing = connection.execute(
                select(missing_cbos).where(missing_cbos.c.course_code == course_code)
            ).mappings().first()
            source_ids = {row["source_id"] for row in memberships}
            source_ids.update(row["source_id"] for row in rule_rows)
            if cbo is not None:
                source_ids.add(cbo["source_id"])
            source_rows = self._sources_by_id(connection, source_ids)

        module = memberships[0]
        return {
            "course_code": course_code,
            "course_name": module["course_name"],
            "nqf_credits": module["nqf_credits"],
            "nqf_level": module["nqf_level"],
            "memberships": memberships,
            "rules": rule_rows,
            "course_information": _course_information(module, cbo, missing),
            "sources": [
                _source_summary(source_rows[source_id])
                for source_id in sorted(source_ids)
            ],
        }

    def list_courses(
        self,
        category: str | None = None,
        interest: str | None = None,
        career: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        statement = (
            select(public_courses)
            .join(course_audits, course_audits.c.course_id == public_courses.c.course_id)
            .join(sources, sources.c.source_id == public_courses.c.source_id)
            .where(
                course_audits.c.availability_status == "available",
                course_audits.c.verification_status == "verified",
                course_audits.c.recommendation_status == "recommendable",
                sources.c.verification_status == "verified",
            )
            .order_by(
                public_courses.c.rating_mean.desc(),
                public_courses.c.rating_count.desc(),
                public_courses.c.course_id,
            )
        )
        if category:
            statement = statement.where(public_courses.c.category == category)
        with self.engine.connect() as connection:
            rows = connection.execute(statement).mappings()
            courses = [_course_record(_normalise_row(row)) for row in rows]
        if interest:
            courses = [course for course in courses if interest in course["interest_tags"]]
        if career:
            courses = [course for course in courses if career in course["career_tags"]]
        return courses[:limit]

    def get_course(self, course_id: str) -> dict[str, Any] | None:
        courses = self.list_courses(limit=1000)
        course = next(
            (row for row in courses if row["course_id"] == course_id),
            None,
        )
        if course is None:
            return None
        with self.engine.connect() as connection:
            source = connection.execute(
                select(sources).where(sources.c.source_id == course["source_id"])
            ).mappings().one()
            audit = connection.execute(
                select(course_audits).where(course_audits.c.course_id == course_id)
            ).mappings().one()
        return {
            **course,
            "source": _source_summary(source),
            "audit": _normalise_row(audit),
            "verification_notes": source["verification_notes"],
        }

    def catalogue_summary(self) -> dict[str, Any]:
        courses = self.list_courses(limit=1000)
        with self.engine.connect() as connection:
            scalar = connection.scalar
            return {
                "programmes": len(self.list_programmes()),
                "module_memberships": scalar(
                    select(func.count()).select_from(curriculum_memberships)
                ),
                "unique_modules": scalar(select(func.count()).select_from(modules)),
                "rules": scalar(select(func.count()).select_from(rules)),
                "recommendable_courses": len(courses),
                "providers": len({course["provider"] for course in courses}),
                "verified_sources": scalar(
                    select(func.count())
                    .select_from(sources)
                    .where(sources.c.verification_status == "verified")
                ),
                "external_references": scalar(
                    select(func.count()).select_from(external_references)
                ),
                "cbo_covered_modules": scalar(
                    select(func.count(func.distinct(module_offerings.c.module_code)))
                    .select_from(module_offerings)
                    .where(
                        module_offerings.c.curriculum_status == "current",
                        module_offerings.c.module_code.is_not(None),
                    )
                ),
                "missing_cbos": scalar(
                    select(func.count()).select_from(missing_cbos)
                ),
                "orphan_cbos": scalar(
                    select(func.count())
                    .select_from(module_offerings)
                    .where(
                        module_offerings.c.curriculum_status
                        == "not_in_current_curriculum"
                    )
                ),
                "categories": sorted({course["category"] for course in courses}),
            }

    def career_paths(self) -> list[dict[str, Any]]:
        paths: dict[str, list[dict[str, Any]]] = {}
        for course in self.list_courses(limit=1000):
            for career in course["career_tags"]:
                paths.setdefault(career, []).append(course)
        return [
            {
                "career_tag": career,
                "display_name": career.replace("_", " ").title(),
                "course_count": len(courses_for_path),
                "courses": courses_for_path,
                "related_interests": sorted(
                    {
                        tag
                        for course in courses_for_path
                        for tag in course["interest_tags"]
                    }
                ),
            }
            for career, courses_for_path in sorted(paths.items())
        ]

    def evidence(self) -> dict[str, Any]:
        with self.engine.connect() as connection:
            source_rows = [
                _source_summary(row)
                | {
                    "document_type": row["document_type"],
                    "authority": row["authority"],
                    "review_date": _iso(row["review_date"]),
                    "verification_notes": row["verification_notes"],
                }
                for row in connection.execute(
                    select(sources).order_by(sources.c.source_id)
                ).mappings()
            ]
            reference_rows = [
                _normalise_row(row)
                for row in connection.execute(
                    select(external_references).order_by(
                        external_references.c.rule_id,
                        external_references.c.reference,
                    )
                ).mappings()
            ]
            missing_rows = [
                _normalise_row(row)
                for row in connection.execute(
                    select(missing_cbos).order_by(missing_cbos.c.course_code)
                ).mappings()
            ]
            orphan_rows = [
                _offering_record(row)
                for row in connection.execute(
                    select(module_offerings)
                    .where(
                        module_offerings.c.curriculum_status
                        == "not_in_current_curriculum"
                    )
                    .order_by(module_offerings.c.reported_course_code)
                ).mappings()
            ]
            rule_counts = _count_query(connection, rules.c.rule_type)
            source_status_counts = _count_query(
                connection, sources.c.verification_status
            )
        return {
            "summary": self.catalogue_summary(),
            "sources": source_rows,
            "external_references": reference_rows,
            "missing_cbos": missing_rows,
            "orphan_cbos": orphan_rows,
            "rule_counts": rule_counts,
            "source_status_counts": source_status_counts,
        }

    def list_missing_cbos(self) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            return [
                _normalise_row(row)
                for row in connection.execute(
                    select(missing_cbos).order_by(missing_cbos.c.course_code)
                ).mappings()
            ]

    def eligibility_context(
        self, course_code: str
    ) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
        # The catalogue is small, and grouped prerequisite expressions require
        # complete programme-year membership context for deterministic evaluation.
        statement = self._membership_statement()
        with self.engine.connect() as connection:
            module_rows = [
                _eligibility_module_record(row)
                for row in connection.execute(statement).mappings()
            ]
            rule_rows = [
                _rule_record(row)
                for row in connection.execute(
                    select(rules)
                    .where(rules.c.target_course_code == course_code)
                    .order_by(rules.c.rule_id)
                ).mappings()
            ]
            source_ids = {
                row["source_id"]
                for row in [*module_rows, *rule_rows]
                if row.get("source_id")
            }
            source_rows = [
                _source_record(row)
                for row in connection.execute(
                    select(sources)
                    .where(sources.c.source_id.in_(source_ids))
                    .order_by(sources.c.source_id)
                ).mappings()
            ] if source_ids else []
        return module_rows, rule_rows, source_rows

    @staticmethod
    def _membership_statement():
        return select(
            curriculum_memberships.c.programme_code,
            curriculum_memberships.c.programme_name,
            curriculum_memberships.c.year_of_study,
            modules.c.course_code,
            modules.c.course_name,
            modules.c.nqf_credits,
            modules.c.nqf_level,
            curriculum_memberships.c.requirement_type,
            curriculum_memberships.c.selection_group,
            curriculum_memberships.c.selection_count,
            curriculum_memberships.c.source_id,
            curriculum_memberships.c.handbook_page,
        ).join(modules, modules.c.course_code == curriculum_memberships.c.course_code)

    @staticmethod
    def _sources_by_id(connection, source_ids: set[str]) -> dict[str, Any]:
        if not source_ids:
            return {}
        rows = connection.execute(
            select(sources).where(sources.c.source_id.in_(source_ids))
        ).mappings()
        return {row["source_id"]: row for row in rows}


def _eligibility_module_record(row: Any) -> dict[str, str]:
    return {
        key: "" if value is None else str(value)
        for key, value in dict(row).items()
    }


def _rule_record(row: Any) -> dict[str, str]:
    result = _normalise_row(row)
    result["condition_json"] = json.dumps(
        row["condition_json"], separators=(",", ":"), sort_keys=True
    )
    return result


def _source_record(row: Any) -> dict[str, str]:
    return {
        key: "" if value is None else _iso(value)
        for key, value in dict(row).items()
    }


def _source_summary(row: Any) -> dict[str, str]:
    return {
        "source_id": row["source_id"],
        "title": row["title"],
        "publisher": row["publisher"],
        "local_path": row["local_path"] or "",
        "url": row["url"] or "",
        "verification_status": row["verification_status"],
        "locator": row["locator"],
    }


def _course_information(module: dict[str, Any], cbo: Any, missing: Any) -> dict[str, Any]:
    if cbo is None:
        return {
            "cbo_available": False,
            "lecturer": None,
            "course_coordinator": None,
            "hours": {
                "credits": module["nqf_credits"],
                "notional_hours_total": module["nqf_credits"] * 10,
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
            "credits": cbo["credits"],
            "notional_hours_total": cbo["notional_hours_total"],
            "weekly_workload_guidance": cbo["weekly_workload_guidance"],
            "contact_pattern": cbo["contact_pattern"],
            "basis": "1 NQF credit represents 10 notional learning hours; explicit weekly guidance is quoted separately from the available course evidence.",
        },
        "scope": cbo["scope"],
        "prescribed_materials": cbo["prescribed_materials"],
        "additional_materials": cbo["additional_materials"],
        "source_id": cbo["source_id"],
        "academic_year": cbo["academic_year"],
        "verification_status": cbo["verification_status"],
        "evidence_notes": cbo["evidence_notes"],
        "missing_reason": None,
    }


def _offering_record(row: Any) -> dict[str, Any]:
    result = _normalise_row(row)
    result.pop("offering_id", None)
    result.pop("module_code", None)
    result["course_code"] = result.pop("reported_course_code")
    return result


def _normalise_row(row: Any) -> dict[str, Any]:
    return {
        key: _iso(value) if isinstance(value, (date, datetime)) else value
        for key, value in dict(row).items()
    }


def _iso(value: Any) -> str:
    return value.isoformat() if isinstance(value, (date, datetime)) else str(value)


def _count_query(connection, column) -> dict[str, int]:
    statement = select(column, func.count()).group_by(column).order_by(column)
    return {
        row[0]: row[1]
        for row in connection.execute(statement)
    }
