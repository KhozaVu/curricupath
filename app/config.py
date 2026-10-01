"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    """Runtime settings for catalogue and hosted model adapters."""

    processed_data_directory: Path
    database_url: str
    catalogue_backend: str
    catalogue_csv_fallback: bool
    timetable_clash_gate_enabled: bool
    gemini_api_key: str | None
    gemini_model: str
    hf_token: str | None
    embedding_provider: str
    embedding_model: str
    embedding_dimension: int
    semantic_search_enabled: bool
    public_course_ranker_enabled: bool
    public_course_ranker_model: Path
    allow_experimental_ranker: bool
    reasoning_reviewer_enabled: bool
    reasoning_reviewer_model: str
    reasoning_reviewer_timeout_ms: int
    handbook_rag_demo_enabled: bool
    handbook_rag_demo_model: str
    interpretation_fallback: str
    interpretation_model: str
    anthropic_api_key: str | None
    claude_fallback_model: str


def get_settings() -> Settings:
    """Build settings without reading or storing secrets in repository files."""

    return Settings(
        processed_data_directory=PROJECT_ROOT / "data" / "processed",
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://curricupath:curricupath_dev@127.0.0.1:5432/curricupath",
        ),
        catalogue_backend=os.getenv("CATALOGUE_BACKEND", "csv").strip().lower(),
        catalogue_csv_fallback=_environment_flag(
            "CATALOGUE_CSV_FALLBACK", default=True
        ),
        timetable_clash_gate_enabled=_environment_flag(
            "TIMETABLE_CLASH_GATE_ENABLED", default=False
        ),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
        hf_token=os.getenv("HF_TOKEN"),
        embedding_provider=os.getenv("EMBEDDING_PROVIDER", "huggingface"),
        embedding_model=os.getenv(
            "EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"
        ),
        embedding_dimension=int(os.getenv("EMBEDDING_DIMENSION", "384")),
        semantic_search_enabled=_environment_flag(
            "SEMANTIC_SEARCH_ENABLED", default=False
        ),
        public_course_ranker_enabled=_environment_flag(
            "PUBLIC_COURSE_RANKER_ENABLED", default=False
        ),
        public_course_ranker_model=_project_path(
            os.getenv(
                "PUBLIC_COURSE_RANKER_MODEL",
                "experiments/models/public_course_pairwise_logistic_v1.json",
            )
        ),
        allow_experimental_ranker=_environment_flag(
            "ALLOW_EXPERIMENTAL_RANKER", default=False
        ),
        reasoning_reviewer_enabled=_environment_flag(
            "REASONING_REVIEWER_ENABLED", default=False
        ),
        reasoning_reviewer_model=os.getenv(
            "REASONING_REVIEWER_MODEL",
            os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
        ),
        reasoning_reviewer_timeout_ms=max(
            10_000, int(os.getenv("REASONING_REVIEWER_TIMEOUT_MS", "10000"))
        ),
        handbook_rag_demo_enabled=_environment_flag(
            "HANDBOOK_RAG_DEMO_ENABLED", default=False
        ),
        # Keep the live comparison demo configurable without altering the
        # frozen model choice recorded for formal evaluation runs.
        handbook_rag_demo_model=os.getenv(
            "HANDBOOK_RAG_DEMO_MODEL", "gemini-3.5-flash-lite"
        ),
        interpretation_fallback=os.getenv("INTERPRETATION_FALLBACK", "fuzzy").strip().lower(),
        interpretation_model=os.getenv("INTERPRETATION_MODEL", "gemini-3.5-flash-lite"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        claude_fallback_model=os.getenv("CLAUDE_FALLBACK_MODEL", "claude-haiku-4-5"),
    )


def _environment_flag(name: str, *, default: bool) -> bool:
    fallback = "true" if default else "false"
    return os.getenv(name, fallback).strip().lower() in {"1", "true", "yes", "on"}


def _project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path
