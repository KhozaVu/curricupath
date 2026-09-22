"""Deterministic consistency checks for advisor response structures."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from pydantic import BaseModel, Field


class InvariantReport(BaseModel):
    passed: bool
    reason_codes: list[str] = Field(default_factory=list)


_PRESENTATION_FIELDS = frozenset(
    {
        "answer",
        "clarification_question",
        "clarification_options",
        "suggestions",
        "review",
        "session_id",
        "run_id",
        "conversation_context",
        "_candidate_log",
    }
)


def decision_payload(result: dict[str, Any]) -> dict[str, Any]:
    """Return the protected structured result, excluding presentation/session data."""

    return {
        key: value
        for key, value in result.items()
        if key not in _PRESENTATION_FIELDS
    }


def decision_fingerprint(result: dict[str, Any]) -> str:
    payload = json.dumps(
        decision_payload(result),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_response(result: dict[str, Any]) -> InvariantReport:
    """Check high-value agreement between structured state and displayed wording."""

    reasons: list[str] = []
    answer = str(result.get("answer", "")).strip()
    status = str(result.get("status", ""))

    if not answer:
        reasons.append("EMPTY_RESPONSE")

    if status == "not_eligible" and re.search(
        r"\bis eligible\b|\bcurrently eligible\b", answer, re.IGNORECASE
    ):
        if not re.search(r"\bnot (?:currently )?eligible\b", answer, re.IGNORECASE):
            reasons.append("DECISION_TEXT_CONTRADICTION")

    if result.get("completed") is True and "completed" not in answer.lower():
        reasons.append("COMPLETED_STATUS_NOT_PRESENTED")

    if status == "clarification_required":
        question = str(result.get("clarification_question", ""))
        if not question or question not in answer or answer.count("?") != 1:
            reasons.append("INVALID_CLARIFICATION_RESPONSE")

    if status == "out_of_scope":
        forbidden = (
            "recommendations",
            "modules",
            "module",
            "programme_profile",
            "programme_comparison",
            "credit_summary",
        )
        if any(result.get(field) for field in forbidden):
            reasons.append("OUT_OF_SCOPE_DATA_LEAK")

    displayed_codes = set(re.findall(r"\b[A-Z]{4}\d{4}A?\b", answer.upper()))
    known_codes = _collect_codes(decision_payload(result))
    if displayed_codes - known_codes:
        reasons.append("UNSUPPORTED_IDENTIFIER_IN_RESPONSE")

    return InvariantReport(passed=not reasons, reason_codes=reasons)


def _collect_codes(value: object) -> set[str]:
    if isinstance(value, str):
        return set(re.findall(r"\b[A-Z]{4}\d{4}A?\b", value.upper()))
    if isinstance(value, dict):
        codes: set[str] = set()
        for item in value.values():
            codes.update(_collect_codes(item))
        return codes
    if isinstance(value, (list, tuple, set)):
        codes = set()
        for item in value:
            codes.update(_collect_codes(item))
        return codes
    return set()
