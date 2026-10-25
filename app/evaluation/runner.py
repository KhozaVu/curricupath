"""Frozen Gemini and pgvector runners for the v2.5 evaluation protocol."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Protocol

from app.data.embeddings import PostgresSemanticSearch
from app.advisor.eligibility import normalise_rule_course_code
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
        self.last_usage = None  # token counts of the most recent call, for spend tracking
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
        self.last_usage = getattr(response, "usage_metadata", None)
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
        grid_requirement_rules: list[dict[str, str]] | None = None,
        retrieval_cache: dict[str, list[dict[str, Any]]] | None = None,
    ) -> None:
        if top_k <= 0:
            raise ValueError("top_k must be positive.")
        self.search = search
        self.client = client
        self.rules = rules
        self.source_states = source_states
        self.grid_requirement_rules = grid_requirement_rules or []
        self.retrieval_cache = retrieval_cache or {}
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
        cache_key = f"{case.get('phrasing_level', '')}:{case['case_id']}"
        if cache_key in self.retrieval_cache:
            retrieved = [dict(item) for item in self.retrieval_cache[cache_key]]
        elif self.retrieval_cache:
            raise ValueError(f"Frozen retrieval cache is missing case {cache_key}.")
        else:
            retrieved = self.search.search(
                query,
                item_type=self.retrieval_item_type,
                limit=self.top_k,
            )
        grid_evidence = self._school_grid_evidence(case)
        if grid_evidence is not None:
            # Both LLM arms receive the same target-specific School facts. The structured arm
            # additionally receives the complete rule table below, isolating rule access.
            retrieved = [*retrieved, grid_evidence]
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

    def _school_grid_evidence(self, case: dict[str, Any]) -> dict[str, Any] | None:
        profile = case.get("student_profile", {})
        programme = str(profile.get("programme_code", "")).upper()
        target = normalise_rule_course_code(str(case.get("target_course_code", "")))
        if not programme or not target:
            return None

        selected = [
            rule
            for rule in self.grid_requirement_rules
            if normalise_rule_course_code(rule.get("target_course_code", "")) == target
            and rule.get("rule_type") in {"prerequisite", "corequisite"}
            and rule.get("scope") in {programme, "ALL_EFA03_EFA04"}
        ]
        if not selected:
            return None

        def codes_for(rule_type: str) -> list[str]:
            result: list[str] = []
            for rule in selected:
                if rule.get("rule_type") != rule_type or rule.get("has_requirement") != "true":
                    continue
                try:
                    condition = json.loads(rule.get("condition_json", "{}"))
                except json.JSONDecodeError:
                    continue
                for code in condition.get("all_of", []):
                    if code not in result:
                        result.append(code)
            return result

        prereqs = codes_for("prerequisite")
        coreqs = codes_for("corequisite")
        sheets = sorted({rule.get("source_sheet", "") for rule in selected if rule.get("source_sheet")})
        locator = ", ".join(sheets)
        content = (
            "School of EIE registration-grid requirements. "
            f"Source: EIE_REG_GRID_2026; sheet: {locator}; programme: {programme}; "
            f"target module: {target}. "
            f"Prerequisites listed by the grid: {', '.join(prereqs) if prereqs else 'none listed'}. "
            f"Corequisites listed by the grid: {', '.join(coreqs) if coreqs else 'none listed'}. "
            "These statements describe the registration-grid record only; 'none listed' does not "
            "assert that no requirement exists in other institutional sources."
        )
        return {
            "source_id": "EIE_REG_GRID_2026",
            "source_locator": f"sheet: {locator}",
            "item_type": "school_registration_grid_requirement",
            "item_id": f"{programme}:{target}",
            "content": content,
            "similarity": None,
        }
