"""PostgreSQL lifecycle and transactional catalogue import helpers."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, delete, func, insert, select, text

from app.data.loaders import CurriculumData
from app.data.schema import (
    aliases,
    candidate_logs,
    course_audits,
    curriculum_memberships,
    document_chunks,
    external_references,
    missing_cbos,
    module_offerings,
    modules,
    programme_profiles,
    public_courses,
    recommendation_runs,
    rules,
    sources,
)


def create_database_engine(database_url: str) -> Engine:
    """Create a checked SQLAlchemy engine for the configured PostgreSQL service."""

    return create_engine(database_url, pool_pre_ping=True)


def upgrade_database(database_url: str, project_root: Path) -> None:
    """Apply all committed Alembic migrations."""

    config = Config(project_root / "alembic.ini")
    config.set_main_option("script_location", str(project_root / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


def database_status(engine: Engine) -> dict[str, Any]:
    """Return basic connectivity, extension, and catalogue state."""

    with engine.connect() as connection:
        version = connection.scalar(text("SELECT extversion FROM pg_extension WHERE extname = 'vector'"))
        table_count = connection.scalar(
            text(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            )
        )
        module_count = connection.scalar(select(func.count()).select_from(modules))
        chunk_count = connection.scalar(select(func.count()).select_from(document_chunks))
        embedded_chunk_count = connection.scalar(
            select(func.count())
            .select_from(document_chunks)
            .where(document_chunks.c.embedding.is_not(None))
        )
    return {
        "connected": True,
        "vector_extension_version": version,
        "table_count": table_count,
        "module_count": module_count,
        "document_chunk_count": chunk_count,
        "embedded_chunk_count": embedded_chunk_count,
    }


def replace_catalogue(engine: Engine, data: CurriculumData) -> dict[str, int]:
    """Replace imported catalogue data atomically while preserving runtime sessions."""

    rows = _catalogue_rows(data)
    with engine.begin() as connection:
        cached_embeddings = {
            (
                row["item_type"],
                row["item_id"],
                row["chunk_kind"],
                row["content_hash"],
            ): row
            for row in connection.execute(
                select(
                    document_chunks.c.item_type,
                    document_chunks.c.item_id,
                    document_chunks.c.chunk_kind,
                    document_chunks.c.content_hash,
                    document_chunks.c.embedding_provider,
                    document_chunks.c.embedding_model,
                    document_chunks.c.embedding_dimension,
                    document_chunks.c.embedding,
                    document_chunks.c.embedded_at,
                ).where(document_chunks.c.embedding.is_not(None))
            ).mappings()
        }
        for table, records in rows:
            if table is document_chunks:
                _restore_cached_embeddings(records, cached_embeddings)
        for table in (
            candidate_logs,
            recommendation_runs,
            document_chunks,
            course_audits,
            public_courses,
            missing_cbos,
            module_offerings,
            external_references,
            rules,
            curriculum_memberships,
            modules,
            aliases,
            programme_profiles,
            sources,
        ):
            connection.execute(delete(table))
        for table, records in rows:
            if records:
                connection.execute(insert(table), records)
    return {table.name: len(records) for table, records in rows}


def _catalogue_rows(
    data: CurriculumData,
) -> list[tuple[Any, list[dict[str, Any]]]]:
    module_rows: dict[str, dict[str, Any]] = {}
    for row in data.modules:
        module_rows.setdefault(
            row["course_code"],
            {
                "course_code": row["course_code"],
                "course_name": row["course_name"],
                "nqf_credits": int(row["nqf_credits"]),
                "nqf_level": row["nqf_level"],
            },
        )

    source_rows = [
        {
            **row,
            "edition_year": int(row["edition_year"]),
            "access_date": _date_or_none(row["access_date"]),
            "handbook_page_offset": _int_or_none(row["handbook_page_offset"]),
            "review_date": date.fromisoformat(row["review_date"]),
            "local_path": _none_if_blank(row["local_path"]),
            "url": _none_if_blank(row["url"]),
            "notes": _none_if_blank(row["notes"]),
        }
        for row in data.sources
    ]
    membership_rows = [
        {
            "programme_code": row["programme_code"],
            "course_code": row["course_code"],
            "year_of_study": int(row["year_of_study"]),
            "programme_name": row["programme_name"],
            "requirement_type": row["requirement_type"],
            "selection_group": _none_if_blank(row["selection_group"]),
            "selection_count": _int_or_none(row["selection_count"]),
            "source_id": row["source_id"],
            "handbook_page": int(row["handbook_page"]),
        }
        for row in data.modules
    ]
    rule_rows = [
        {
            **row,
            "target_course_code": _none_if_blank(row["target_course_code"]),
            "condition_json": json.loads(row["condition_json"]),
            "handbook_page": int(row["handbook_page"]),
            "notes": _none_if_blank(row["notes"]),
        }
        for row in data.rules
    ]
    external_rows = [dict(row) for row in data.external_references]
    offering_rows = [
        {
            **row,
            "module_code": row["course_code"]
            if row["curriculum_status"] == "current"
            else None,
            "reported_course_code": row["course_code"],
            "academic_year": int(row["academic_year"]),
            "credits": _int_or_none(row["credits"]),
            "notional_hours_total": _int_or_none(row["notional_hours_total"]),
        }
        for row in data.cbo_courses
    ]
    for row in offering_rows:
        row.pop("course_code")
    missing_rows = [
        {
            **row,
            "credits": int(row["credits"]),
            "candidate_filename": _none_if_blank(row["candidate_filename"]),
        }
        for row in data.missing_cbos
    ]
    public_course_rows = [
        {
            **row,
            "rating_mean": float(row["rating_mean"]),
            "rating_count": int(row["rating_count"]),
            "rating_scale": int(row["rating_scale"]),
            "access_date": date.fromisoformat(row["access_date"]),
        }
        for row in data.courses
    ]
    audit_rows = [
        {**row, "audit_date": date.fromisoformat(row["audit_date"])}
        for row in data.course_audits
    ]
    alias_rows = [
        {
            "alias": row.phrase,
            "canonical_tag": row.canonical_tag,
            "tag_type": row.tag_type,
        }
        for row in data.aliases
    ]
    programme_profile_rows = [
        {
            **row,
            "duration_years": int(row["duration_years"]),
            "access_date": date.fromisoformat(row["access_date"]),
        }
        for row in data.programme_profiles
    ]
    chunk_rows = _document_chunk_rows(data)
    return [
        (sources, source_rows),
        (programme_profiles, programme_profile_rows),
        (modules, list(module_rows.values())),
        (curriculum_memberships, membership_rows),
        (rules, rule_rows),
        (external_references, external_rows),
        (module_offerings, offering_rows),
        (missing_cbos, missing_rows),
        (public_courses, public_course_rows),
        (course_audits, audit_rows),
        (aliases, alias_rows),
        (document_chunks, chunk_rows),
    ]


def _document_chunk_rows(data: CurriculumData) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for row in data.cbo_courses:
        if row["curriculum_status"] != "current":
            continue
        content = " ".join(
            (
                row["course_code"],
                row["scope"],
                row["prescribed_materials"],
                row["additional_materials"],
            )
        )
        chunks.append(_chunk("module", row["course_code"], content, row["source_id"]))
    for row in data.courses:
        content = " ".join(
            (
                row["title"],
                row["description"],
                row["outcomes"].replace(";", " "),
                row["topic_tags"].replace("_", " ").replace(";", " "),
                row["interest_tags"].replace("_", " ").replace(";", " "),
                row["career_tags"].replace("_", " ").replace(";", " "),
            )
        )
        chunks.append(_chunk("public_course", row["course_id"], content, row["source_id"]))
    return chunks


def _chunk(item_type: str, item_id: str, content: str, source_id: str) -> dict[str, Any]:
    return {
        "item_type": item_type,
        "item_id": item_id,
        "chunk_kind": "search_profile",
        "content": content,
        "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "source_id": source_id,
    }


def _restore_cached_embeddings(
    records: list[dict[str, Any]],
    cached: dict[tuple[str, str, str, str], dict[str, Any]],
) -> None:
    """Reuse vectors only when the searchable content hash is unchanged."""

    for record in records:
        record.update(
            {
                "embedding_provider": None,
                "embedding_model": None,
                "embedding_dimension": None,
                "embedding": None,
                "embedded_at": None,
            }
        )
        key = (
            record["item_type"],
            record["item_id"],
            record["chunk_kind"],
            record["content_hash"],
        )
        existing = cached.get(key)
        if existing is None:
            continue
        record.update(
            {
                "embedding_provider": existing["embedding_provider"],
                "embedding_model": existing["embedding_model"],
                "embedding_dimension": existing["embedding_dimension"],
                "embedding": existing["embedding"],
                "embedded_at": existing["embedded_at"],
            }
        )


def _none_if_blank(value: str) -> str | None:
    return value or None


def _int_or_none(value: str) -> int | None:
    return int(value) if value else None


def _date_or_none(value: str) -> date | None:
    return date.fromisoformat(value) if value else None
