"""Tests for the clearly-labelled live Handbook-RAG comparison adapter."""

from __future__ import annotations

from types import SimpleNamespace

from app.advisor.baseline_demo import HandbookRagDemo


class _FailingRunner:
    def run_case(self, *_args, **_kwargs):
        return SimpleNamespace(
            status="malformed_or_failed",
            parsed_output=None,
            error="ServerError: 503 UNAVAILABLE: high demand",
        )


def test_handbook_rag_demo_explains_temporary_provider_failure() -> None:
    demo = object.__new__(HandbookRagDemo)
    demo._runner = _FailingRunner()

    result = demo.answer("Can I take ELEN4006A?", "EFA04", set(), set(), set())

    assert result["system"] == "handbook_rag"
    assert result["status"] == "temporarily_unavailable"
    assert result["decision"] is None
    assert "hosted model service is busy" in result["answer"]
    assert "Select CurricuPath" in result["answer"]
