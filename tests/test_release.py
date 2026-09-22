"""Tests for release fingerprint and drift detection."""

from __future__ import annotations

import json
from dataclasses import replace

from app.config import PROJECT_ROOT, get_settings
from app.release import build_release_inputs, changed_release_sections


def test_release_inputs_are_stable_and_exclude_secrets() -> None:
    settings = replace(
        get_settings(),
        gemini_api_key="gemini-secret-marker",
        hf_token="huggingface-secret-marker",
    )

    first = build_release_inputs(
        PROJECT_ROOT, settings, database_fingerprint="database-fingerprint"
    )
    second = build_release_inputs(
        PROJECT_ROOT, settings, database_fingerprint="database-fingerprint"
    )
    encoded = json.dumps(first)

    assert first == second
    assert len(first["release_fingerprint"]) == 64
    assert "gemini-secret-marker" not in encoded
    assert "huggingface-secret-marker" not in encoded


def test_release_drift_names_changed_section() -> None:
    settings = get_settings()
    frozen = build_release_inputs(
        PROJECT_ROOT, settings, database_fingerprint="first"
    )
    current = build_release_inputs(
        PROJECT_ROOT, settings, database_fingerprint="second"
    )

    assert changed_release_sections(frozen, current) == ["catalogue"]
