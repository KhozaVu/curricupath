"""Frozen Gemini and pgvector runners for the v2.5 evaluation protocol."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Protocol

from app.data.embeddings import PostgresSemanticSearch
from app.evaluation.models import EvaluationArm, EvaluationDecision


class DecisionClient(Protocol):
    """Generate one schema-constrained decision without hidden retries."""

    model_name: str

    def decide(self, system_instruction: str, payload: dict[str, Any]) -> tuple[str, Any]: ...


@dataclass(frozen=True)
class EvaluationRun:
    """One immutable case/arm/run observation."""

    case_id: str
    arm: EvaluationArm
    run_number: int
    model: str
    status: str
    parsed_output: dict[str, Any] | None
    raw_output: str
    retrieved_chunks: tuple[dict[str, Any], ...]
    latency_ms: int
    error: str | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class GeminiDecisionClient:
    """Call Gemini once and preserve raw output for malformed-output scoring."""

    def __init__(self, api_key: str, model: str, timeout_ms: int = 60_000) -> None:
        from google import genai
        from google.genai import types

        if not api_key:
            raise ValueError("GEMINI_API_KEY is required for evaluation generation.")
        self.model_name = model
        self._types = types
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=timeout_ms,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )

    def decide(
        self,
        system_instruction: str,
        payload: dict[str, Any],
    ) -> tuple[str, Any]:
        response = self._client.models.generate_content(
            model=self.model_name,
            contents=json.dumps(payload, sort_keys=True, default=str),
            config=self._types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=EvaluationDecision,
                temperature=0,
            ),
        )
        return response.text or "", response.parsed


class EvaluationRunner:
    """Run either LLM arm with identical retrieval and output handling."""

    def __init__(
        self,
        search: PostgresSemanticSearch,
        client: DecisionClient,
        prompt_directory: Path,
        rules: list[dict[str, str]],
        source_states: list[dict[str, str]],
        top_k: int,
        retrieval_item_type: str = "evaluation_handbook",
    ) -> None:
        if top_k <= 0:
            raise ValueError("top_k must be positive.")
        self.search = search
        self.client = client
        self.rules = rules
        self.source_states = source_states
        self.top_k = top_k
        self.retrieval_item_type = retrieval_item_type
        self.prompts = {
            "handbook_rag": (prompt_directory / "rag_prompt.md").read_text(
                encoding="utf-8"
            ),
            "structured_rules_llm": (
                prompt_directory / "structured_rules_prompt.md"
            ).read_text(encoding="utf-8"),
        }

    def run_case(
        self,
        case: dict[str, Any],
        arm: EvaluationArm,
        run_number: int,
    ) -> EvaluationRun:
        query = str(
            case.get("consolidated_noninteractive_input")
            or case.get("question")
            or ""
        ).strip()
        if not query:
            raise ValueError(f"Case {case.get('case_id', '<unknown>')} has no query.")
        retrieved = self.search.search(
            query,
            item_type=self.retrieval_item_type,
            limit=self.top_k,
        )
        payload: dict[str, Any] = {
            "case_id": case["case_id"],
            "question": query,
            "student_profile": case.get("student_profile", {}),
            "retrieved_evidence": retrieved,
        }
        if arm == "structured_rules_llm":
            payload["structured_rules"] = self.rules
            payload["source_evidence_states"] = self.source_states

        started = perf_counter()
        raw = ""
        try:
            raw, parsed = self.client.decide(self.prompts[arm], payload)
            decision = (
                parsed
                if isinstance(parsed, EvaluationDecision)
                else EvaluationDecision.model_validate(parsed)
            )
            status = "valid"
            output = decision.model_dump()
            error = None
        except Exception as exc:
            status = "malformed_or_failed"
            output = None
            error = f"{type(exc).__name__}: {exc}"
        return EvaluationRun(
            case_id=str(case["case_id"]),
            arm=arm,
            run_number=run_number,
            model=self.client.model_name,
            status=status,
            parsed_output=output,
            raw_output=raw,
            retrieved_chunks=tuple(retrieved),
            latency_ms=max(0, round((perf_counter() - started) * 1000)),
            error=error,
        )
