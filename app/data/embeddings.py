"""Hosted embedding generation and pgvector similarity search."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol, Sequence

import numpy as np
from huggingface_hub import InferenceClient
from sqlalchemy import Engine, or_, select, update

from app.data.schema import document_chunks


BGE_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


class SemanticSearchError(RuntimeError):
    """Raised when hosted embedding or pgvector search cannot be completed."""


class EmbeddingProvider(Protocol):
    """Minimal interface required by catalogue embedding and search."""

    provider_name: str
    model_name: str
    dimension: int

    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_queries(self, texts: Sequence[str]) -> list[list[float]]: ...


@dataclass(frozen=True)
class EmbeddingReport:
    """Summary of one resumable catalogue embedding run."""

    selected: int
    embedded: int
    batches: int


class HuggingFaceHostedEmbeddings:
    """Generate BGE vectors through Hugging Face hosted inference only."""

    provider_name = "huggingface"

    def __init__(
        self,
        token: str,
        model_name: str,
        dimension: int,
        *,
        timeout: float = 60,
        client: Any | None = None,
    ) -> None:
        if not token:
            raise ValueError("A Hugging Face token is required for hosted embeddings.")
        if dimension <= 0:
            raise ValueError("Embedding dimension must be positive.")
        self.model_name = model_name
        self.dimension = dimension
        self._client = client or InferenceClient(
            provider="hf-inference",
            token=token,
            timeout=timeout,
        )

    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]:
        return self._embed(texts)

    def embed_queries(self, texts: Sequence[str]) -> list[list[float]]:
        instructed = [f"{BGE_QUERY_INSTRUCTION}{text.strip()}" for text in texts]
        return self._embed(instructed)

    def _embed(self, texts: Sequence[str]) -> list[list[float]]:
        values = [text.strip() for text in texts]
        if not values or any(not text for text in values):
            raise ValueError("Embedding input must contain non-empty text.")
        try:
            response = self._client.feature_extraction(
                values,
                model=self.model_name,
                normalize=True,
            )
        except Exception as error:
            raise SemanticSearchError(
                f"Hugging Face embedding request failed: {error}"
            ) from error
        return _validated_vectors(response, len(values), self.dimension)


def embed_catalogue(
    engine: Engine,
    provider: EmbeddingProvider,
    *,
    batch_size: int = 8,
    force: bool = False,
) -> EmbeddingReport:
    """Embed pending chunks in resumable batches without holding network transactions."""

    if batch_size <= 0:
        raise ValueError("batch_size must be positive.")

    statement = select(document_chunks.c.chunk_id, document_chunks.c.content)
    if not force:
        statement = statement.where(
            or_(
                document_chunks.c.embedding.is_(None),
                document_chunks.c.embedding_provider.is_distinct_from(
                    provider.provider_name
                ),
                document_chunks.c.embedding_model.is_distinct_from(
                    provider.model_name
                ),
                document_chunks.c.embedding_dimension.is_distinct_from(
                    provider.dimension
                ),
            )
        )
    statement = statement.order_by(document_chunks.c.chunk_id)
    with engine.connect() as connection:
        pending = list(connection.execute(statement).mappings())

    embedded = 0
    batches = 0
    for offset in range(0, len(pending), batch_size):
        batch = pending[offset : offset + batch_size]
        vectors = provider.embed_passages([row["content"] for row in batch])
        embedded_at = datetime.now(timezone.utc)
        with engine.begin() as connection:
            for row, vector in zip(batch, vectors, strict=True):
                connection.execute(
                    update(document_chunks)
                    .where(document_chunks.c.chunk_id == row["chunk_id"])
                    .values(
                        embedding_provider=provider.provider_name,
                        embedding_model=provider.model_name,
                        embedding_dimension=provider.dimension,
                        embedding=vector,
                        embedded_at=embedded_at,
                    )
                )
        embedded += len(batch)
        batches += 1

    return EmbeddingReport(
        selected=len(pending),
        embedded=embedded,
        batches=batches,
    )


class PostgresSemanticSearch:
    """Embed a query remotely and rank stored chunks with pgvector cosine distance."""

    def __init__(self, engine: Engine, provider: EmbeddingProvider) -> None:
        self.engine = engine
        self.provider = provider

    def search(
        self,
        query: str,
        *,
        item_type: str | None = None,
        item_ids: Sequence[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        if not query.strip():
            raise ValueError("Semantic search query cannot be empty.")
        if limit <= 0:
            raise ValueError("Semantic search limit must be positive.")

        query_vector = self.provider.embed_queries([query])[0]
        distance = document_chunks.c.embedding.cosine_distance(query_vector)
        statement = (
            select(
                document_chunks.c.item_type,
                document_chunks.c.item_id,
                document_chunks.c.chunk_kind,
                document_chunks.c.content,
                document_chunks.c.source_id,
                distance.label("distance"),
            )
            .where(
                document_chunks.c.embedding.is_not(None),
                document_chunks.c.embedding_provider
                == self.provider.provider_name,
                document_chunks.c.embedding_model == self.provider.model_name,
                document_chunks.c.embedding_dimension == self.provider.dimension,
            )
            .order_by(distance)
            .limit(limit)
        )
        if item_type:
            statement = statement.where(document_chunks.c.item_type == item_type)
        if item_ids is not None:
            if not item_ids:
                return []
            statement = statement.where(document_chunks.c.item_id.in_(item_ids))

        try:
            with self.engine.connect() as connection:
                rows = connection.execute(statement).mappings().all()
        except Exception as error:
            raise SemanticSearchError(f"pgvector search failed: {error}") from error

        return [
            {
                "item_type": row["item_type"],
                "item_id": row["item_id"],
                "chunk_kind": row["chunk_kind"],
                "content": row["content"],
                "source_id": row["source_id"],
                "similarity": round(1.0 - float(row["distance"]), 6),
            }
            for row in rows
        ]

    def course_scores(
        self, query: str, course_ids: Sequence[str]
    ) -> dict[str, float]:
        results = self.search(
            query,
            item_type="public_course",
            item_ids=course_ids,
            limit=len(course_ids),
        )
        return {row["item_id"]: row["similarity"] for row in results}

    def module_scores(
        self, query: str, module_codes: Sequence[str]
    ) -> dict[str, float]:
        """Return semantic relevance for a programme-filtered module set."""

        results = self.search(
            query,
            item_type="module",
            item_ids=module_codes,
            limit=len(module_codes),
        )
        return {row["item_id"]: row["similarity"] for row in results}


def _validated_vectors(
    response: Any,
    expected_count: int,
    expected_dimension: int,
) -> list[list[float]]:
    array = np.asarray(response, dtype=np.float32)
    if expected_count == 1 and array.ndim == 1:
        array = array.reshape(1, -1)
    if array.shape != (expected_count, expected_dimension):
        raise SemanticSearchError(
            "Embedding response has shape "
            f"{array.shape}; expected ({expected_count}, {expected_dimension})."
        )
    if not np.isfinite(array).all():
        raise SemanticSearchError("Embedding response contains non-finite values.")
    return array.tolist()
