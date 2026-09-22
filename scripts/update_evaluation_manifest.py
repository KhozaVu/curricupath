"""Refresh the non-secret reproducibility manifest for evaluation v2.5."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EVALUATION = PROJECT_ROOT / "experiments" / "evaluation" / "v2_5"
PROCESSED = PROJECT_ROOT / "data" / "processed"

from app.config import get_settings
from app.data.database import create_database_engine, database_status


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(args: list[str]) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()


def _versions() -> dict[str, str]:
    packages = (
        "fastapi",
        "google-genai",
        "huggingface-hub",
        "numpy",
        "pgvector",
        "psycopg",
        "pydantic",
        "pypdf",
        "sqlalchemy",
    )
    values: dict[str, str] = {}
    for package in packages:
        try:
            values[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            values[package] = "not_installed"
    return values


def main() -> None:
    settings = get_settings()
    manifest_path = EVALUATION / "manifest.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else {"protocol_version": "2.5"}
    )
    processed_paths = sorted(PROCESSED.glob("*.csv"))
    evaluation_paths = sorted(
        path
        for path in EVALUATION.iterdir()
        if path.is_file() and path.name != "manifest.json"
    )
    try:
        database = database_status(create_database_engine(settings.database_url))
    except Exception as exc:
        database = {"connected": False, "error": f"{type(exc).__name__}: {exc}"}
    retrieval = json.loads(
        (EVALUATION / "rag_retrieval_config.json").read_text(encoding="utf-8")
    )
    personnel = json.loads(
        (EVALUATION / "personnel.json").read_text(encoding="utf-8")
    )
    dirty = _git(["status", "--porcelain"])
    manifest.update(
        {
            "refreshed_at": datetime.now(timezone.utc).isoformat(),
            "status": (
                "blocked_pending_human_approval_and_clean_commit"
                if personnel.get("status") != "complete" or dirty
                else "candidate_for_readiness_check"
            ),
            "git": {
                "head": _git(["rev-parse", "HEAD"]),
                "branch": _git(["branch", "--show-current"]),
                "working_tree_clean": not bool(dirty),
            },
            "environment": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "packages": _versions(),
            },
            "models": {
                "gemini": settings.gemini_model,
                "embedding_provider": settings.embedding_provider,
                "embedding_model": settings.embedding_model,
                "embedding_dimension": settings.embedding_dimension,
                "temperature": 0,
                "llm_runs_per_case": 3,
                "primary_run": 1,
            },
            "retrieval": retrieval,
            "database": database,
            "processed_file_sha256": {
                path.name: _sha256(path) for path in processed_paths
            },
            "evaluation_file_sha256": {
                path.name: _sha256(path) for path in evaluation_paths
            },
        }
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Manifest status: {manifest['status']}")
    print(f"Git clean: {manifest['git']['working_tree_clean']}")
    print(f"Database connected: {database.get('connected', False)}")


if __name__ == "__main__":
    main()
