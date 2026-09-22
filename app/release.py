"""Deterministic release inputs for CurricuPath freeze verification."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.advisor.reviewer import REVIEW_REASON_CODES, REVIEW_RUBRIC_VERSION
from app.advisor.scope import SCOPE_POLICY_VERSION
from app.config import Settings


CONTROL_FILES = (
    "app/advisor/eligibility.py",
    "app/advisor/engine.py",
    "app/advisor/intent.py",
    "app/advisor/reviewer.py",
    "app/advisor/response_invariants.py",
    "app/advisor/response_repair.py",
    "app/advisor/scope.py",
    "app/data/sessions.py",
    "app/ui/advisor_page.html",
    "frontend/src/App.jsx",
    "frontend/src/main.jsx",
    "frontend/src/styles.css",
    "frontend/vite.config.js",
)
PROMPT_FILES = (
    "experiments/evaluation/v2_5/grounding_prompt.md",
    "experiments/evaluation/v2_5/rag_prompt.md",
    "experiments/evaluation/v2_5/structured_rules_prompt.md",
)


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest for one release input."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_release_inputs(
    project_root: Path,
    settings: Settings,
    *,
    database_fingerprint: str | None,
) -> dict[str, Any]:
    """Build the non-secret payload whose hash identifies a release."""

    processed_files = sorted((project_root / "data" / "processed").glob("*.csv"))
    catalogue_files = {
        path.name: sha256_file(path)
        for path in processed_files
    }
    control_files = _hash_relative_files(project_root, CONTROL_FILES)
    prompt_files = _hash_relative_files(project_root, PROMPT_FILES)
    policy = {
        "scope_policy_version": SCOPE_POLICY_VERSION,
        "review_rubric_version": REVIEW_RUBRIC_VERSION,
        "review_reason_codes": sorted(REVIEW_REASON_CODES),
    }
    policy["fingerprint"] = canonical_fingerprint(policy)

    payload: dict[str, Any] = {
        "catalogue": {
            "processed_file_sha256": catalogue_files,
            "file_fingerprint": canonical_fingerprint(catalogue_files),
            "database_fingerprint": database_fingerprint,
        },
        "controls": {
            "file_sha256": control_files,
            "fingerprint": canonical_fingerprint(control_files),
        },
        "prompts": {
            "file_sha256": prompt_files,
            "fingerprint": canonical_fingerprint(prompt_files),
        },
        "policy": policy,
        "models": {
            "gemini_model": settings.gemini_model,
            "reasoning_reviewer_model": settings.reasoning_reviewer_model,
            "embedding_provider": settings.embedding_provider,
            "embedding_model": settings.embedding_model,
            "embedding_dimension": settings.embedding_dimension,
            "reviewer_temperature": 0,
        },
        "runtime": {
            "catalogue_backend": settings.catalogue_backend,
            "catalogue_csv_fallback": settings.catalogue_csv_fallback,
            "semantic_search_enabled": settings.semantic_search_enabled,
            "public_course_ranker_enabled": settings.public_course_ranker_enabled,
            "allow_experimental_ranker": settings.allow_experimental_ranker,
            "reasoning_reviewer_enabled": settings.reasoning_reviewer_enabled,
            "reasoning_reviewer_timeout_ms": settings.reasoning_reviewer_timeout_ms,
            "handbook_rag_demo_enabled": settings.handbook_rag_demo_enabled,
        },
    }
    payload["release_fingerprint"] = canonical_fingerprint(payload)
    return payload


def changed_release_sections(
    frozen: dict[str, Any], current: dict[str, Any]
) -> list[str]:
    """Return top-level release sections that differ from the frozen input."""

    changed = sorted(
        key
        for key in set(frozen) | set(current)
        if key != "release_fingerprint"
        if frozen.get(key) != current.get(key)
    )
    if not changed and frozen.get("release_fingerprint") != current.get(
        "release_fingerprint"
    ):
        return ["release_fingerprint"]
    return changed


def canonical_fingerprint(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _hash_relative_files(
    project_root: Path, relative_paths: tuple[str, ...]
) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for relative_path in relative_paths:
        path = project_root / relative_path
        if not path.is_file():
            raise FileNotFoundError(f"Release input is missing: {relative_path}")
        hashes[relative_path] = sha256_file(path)
    return hashes
