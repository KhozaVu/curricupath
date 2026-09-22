"""Tests for hosted embedding validation without external API calls."""

from __future__ import annotations

import numpy as np
import pytest

from app.data.embeddings import (
    BGE_QUERY_INSTRUCTION,
    HuggingFaceHostedEmbeddings,
    SemanticSearchError,
)


class FakeInferenceClient:
    def __init__(self, response: object) -> None:
        self.response = response
        self.calls: list[tuple[list[str], str, bool]] = []

    def feature_extraction(
        self, texts: list[str], *, model: str, normalize: bool
    ) -> object:
        self.calls.append((texts, model, normalize))
        return self.response


def test_query_uses_bge_retrieval_instruction() -> None:
    client = FakeInferenceClient(np.ones((1, 384), dtype=np.float32))
    provider = HuggingFaceHostedEmbeddings(
        "test-token",
        "BAAI/bge-small-en-v1.5",
        384,
        client=client,
    )

    vectors = provider.embed_queries(["electric circuits"])

    assert len(vectors[0]) == 384
    assert client.calls[0][0] == [
        f"{BGE_QUERY_INSTRUCTION}electric circuits"
    ]
    assert client.calls[0][2] is True


def test_passage_text_is_sent_without_query_instruction() -> None:
    client = FakeInferenceClient(np.ones((2, 384), dtype=np.float32))
    provider = HuggingFaceHostedEmbeddings(
        "test-token",
        "BAAI/bge-small-en-v1.5",
        384,
        client=client,
    )

    provider.embed_passages(["circuit analysis", "software engineering"])

    assert client.calls[0][0] == ["circuit analysis", "software engineering"]


def test_single_vector_response_is_accepted() -> None:
    client = FakeInferenceClient(np.ones(384, dtype=np.float32))
    provider = HuggingFaceHostedEmbeddings(
        "test-token",
        "BAAI/bge-small-en-v1.5",
        384,
        client=client,
    )

    assert len(provider.embed_passages(["one passage"])[0]) == 384


def test_wrong_embedding_shape_is_rejected() -> None:
    client = FakeInferenceClient(np.ones((1, 768), dtype=np.float32))
    provider = HuggingFaceHostedEmbeddings(
        "test-token",
        "BAAI/bge-small-en-v1.5",
        384,
        client=client,
    )

    with pytest.raises(SemanticSearchError, match=r"expected \(1, 384\)"):
        provider.embed_passages(["wrong shape"])


def test_non_finite_embedding_is_rejected() -> None:
    response = np.ones((1, 384), dtype=np.float32)
    response[0, 0] = np.nan
    provider = HuggingFaceHostedEmbeddings(
        "test-token",
        "BAAI/bge-small-en-v1.5",
        384,
        client=FakeInferenceClient(response),
    )

    with pytest.raises(SemanticSearchError, match="non-finite"):
        provider.embed_passages(["invalid vector"])
