"""Offline tests for the PostgreSQL schema and CSV import mapping."""

from __future__ import annotations

from pathlib import Path

from app.data.database import _catalogue_rows, _restore_cached_embeddings
from app.data.loaders import load_curriculum_data
from app.data.schema import document_chunks, metadata, modules


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DATA = PROJECT_ROOT / "data" / "processed"


def test_postgres_schema_contains_runtime_and_catalogue_tables() -> None:
    assert set(metadata.tables) == {
        "advisor_sessions",
        "aliases",
        "candidate_logs",
        "course_audits",
        "curriculum_memberships",
        "document_chunks",
        "external_references",
        "missing_cbos",
        "module_offerings",
        "modules",
        "programme_profiles",
        "public_courses",
        "recommendation_runs",
        "rules",
        "sources",
    }


def test_embedding_column_matches_hosted_model_dimension() -> None:
    assert str(document_chunks.c.embedding.type) == "VECTOR(384)"
    assert "ix_document_chunks_embedding_hnsw" in {
        index.name for index in document_chunks.indexes
    }


def test_catalogue_import_rows_match_table_columns() -> None:
    data = load_curriculum_data(PROCESSED_DATA)

    for table, records in _catalogue_rows(data):
        supplied_columns = set().union(*(set(record) for record in records))
        assert supplied_columns <= set(table.c.keys())


def test_catalogue_import_preserves_non_numeric_nqf_levels() -> None:
    data = load_curriculum_data(PROCESSED_DATA)
    rows_by_table = dict(_catalogue_rows(data))

    assert modules.c.nqf_level.type.python_type is str
    assert {row["nqf_level"] for row in rows_by_table[modules]} >= {"5", "N/A"}


def test_catalogue_build_prepares_plain_search_chunks_without_embeddings() -> None:
    data = load_curriculum_data(PROCESSED_DATA)
    rows_by_table = dict(_catalogue_rows(data))
    chunks = rows_by_table[document_chunks]

    expected_chunks = sum(
        row["curriculum_status"] == "current" for row in data.cbo_courses
    ) + len(data.courses)
    assert len(chunks) == expected_chunks
    assert all(not chunk["content"].startswith("passage: ") for chunk in chunks)
    assert all("embedding" not in chunk for chunk in chunks)


def test_unchanged_chunk_restores_cached_embedding() -> None:
    record = {
        "item_type": "public_course",
        "item_id": "CRS001",
        "chunk_kind": "search_profile",
        "content_hash": "same-content",
    }
    cached = {
        ("public_course", "CRS001", "search_profile", "same-content"): {
            "embedding_provider": "huggingface",
            "embedding_model": "BAAI/bge-small-en-v1.5",
            "embedding_dimension": 384,
            "embedding": [0.0] * 384,
            "embedded_at": "timestamp",
        }
    }

    _restore_cached_embeddings([record], cached)

    assert record["embedding_model"] == "BAAI/bge-small-en-v1.5"
    assert len(record["embedding"]) == 384


def test_cached_and_new_chunks_have_the_same_insert_shape() -> None:
    records = [
        {
            "item_type": "public_course",
            "item_id": "CRS001",
            "chunk_kind": "search_profile",
            "content_hash": "same-content",
        },
        {
            "item_type": "module",
            "item_id": "FEBE1000A",
            "chunk_kind": "search_profile",
            "content_hash": "new-content",
        },
    ]
    cached = {
        ("public_course", "CRS001", "search_profile", "same-content"): {
            "embedding_provider": "huggingface",
            "embedding_model": "BAAI/bge-small-en-v1.5",
            "embedding_dimension": 384,
            "embedding": [0.0] * 384,
            "embedded_at": "timestamp",
        }
    }

    _restore_cached_embeddings(records, cached)

    embedding_columns = {
        "embedding_provider",
        "embedding_model",
        "embedding_dimension",
        "embedding",
        "embedded_at",
    }
    assert embedding_columns <= set(records[0])
    assert embedding_columns <= set(records[1])
    assert records[1]["embedding"] is None
