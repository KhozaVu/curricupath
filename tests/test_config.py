"""Tests for environment-driven application settings."""

from pathlib import Path

from app.config import get_settings


def test_current_gemini_model_is_the_default(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_MODEL", raising=False)

    assert get_settings().gemini_model == "gemini-3.6-flash"


def test_learned_ranker_is_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("PUBLIC_COURSE_RANKER_ENABLED", raising=False)
    monkeypatch.delenv("PUBLIC_COURSE_RANKER_MODEL", raising=False)
    monkeypatch.delenv("ALLOW_EXPERIMENTAL_RANKER", raising=False)

    settings = get_settings()

    assert not hasattr(settings, "public_course_ranker_enabled")



def test_reasoning_reviewer_is_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("REASONING_REVIEWER_ENABLED", raising=False)
    monkeypatch.delenv("REASONING_REVIEWER_TIMEOUT_MS", raising=False)

    settings = get_settings()

    assert settings.reasoning_reviewer_enabled is False
    assert settings.reasoning_reviewer_timeout_ms == 10000


def test_handbook_rag_demo_is_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("HANDBOOK_RAG_DEMO_ENABLED", raising=False)

    assert get_settings().handbook_rag_demo_enabled is False


def test_handbook_rag_demo_can_be_enabled(monkeypatch) -> None:
    monkeypatch.setenv("HANDBOOK_RAG_DEMO_ENABLED", "true")

    assert get_settings().handbook_rag_demo_enabled is True


def test_handbook_rag_demo_uses_its_own_supported_model(monkeypatch) -> None:
    monkeypatch.delenv("HANDBOOK_RAG_DEMO_MODEL", raising=False)

    assert get_settings().handbook_rag_demo_model == "gemini-3.5-flash-lite"
