"""Versioned deterministic scope policy for CurricuPath requests."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from app.advisor.intent import ParsedAdvisorRequest
from app.advisor.normalisation import normalise_text


SCOPE_POLICY_VERSION = "scope-v1-2026-09-17"
ScopeStatus = Literal["supported", "ambiguous", "out_of_scope"]

SUPPORTED_INTENTS = frozenset(
    {
        "greeting",
        "help",
        "module_information",
        "eligibility",
        "profile_courses",
        "programme_information",
        "programme_comparison",
        "credit_information",
        "curriculum_list",
        "public_course_search",
        "career_path",
    }
)

_OUT_OF_SCOPE_PATTERNS = (
    r"\b(?:predict|estimate|guess)\b.{0,30}\b(?:mark|marks|grade|grades|result|results)\b",
    r"\b(?:drop out|quit engineering|leave university)\b",
    r"\b(?:mental health|depress(?:ed|ion)?|anxiety|suicid(?:e|al))\b",
    r"\b(?:legal advice|disciplinary hearing|appeal my mark)\b",
    r"\b(?:loan|bursary application|financial advice|tuition payment)\b",
    r"\b(?:guarantee|promise)\b.{0,25}\b(?:job|employment|admission|graduate|pass)\b",
    r"\b(?:override|ignore|bypass)\b.{0,30}\b(?:rule|prerequisite|requirement)\b",
)

_SUPPORTED_TOPIC_WORDS = frozenset(
    {
        "module",
        "course",
        "curriculum",
        "programme",
        "degree",
        "elective",
        "compulsory",
        "prerequisite",
        "corequisite",
        "eligibility",
        "eligible",
        "credit",
        "credits",
        "career",
        "lecturer",
        "efa03",
        "efa04",
    }
)


class ScopeDecision(BaseModel):
    """A deterministic boundary decision made before retrieval and ranking."""

    status: ScopeStatus
    intent: str
    reason_codes: list[str] = Field(default_factory=list)
    clarification_question: str | None = None
    policy_version: str = SCOPE_POLICY_VERSION


def classify_scope(
    text: str,
    parsed: ParsedAdvisorRequest,
    *,
    has_active_context: bool = False,
) -> ScopeDecision:
    """Classify a request without using retrieval, ranking, or an external model."""

    normalized = normalise_text(text)
    if any(re.search(pattern, normalized) for pattern in _OUT_OF_SCOPE_PATTERNS):
        return ScopeDecision(
            status="out_of_scope",
            intent=parsed.intent,
            reason_codes=["UNSUPPORTED_USER_REQUEST"],
        )

    if has_active_context:
        return ScopeDecision(
            status="supported",
            intent=parsed.intent,
            reason_codes=["SUPPORTED_CLARIFICATION_CONTEXT"],
        )

    if parsed.intent in SUPPORTED_INTENTS:
        return ScopeDecision(
            status="supported",
            intent=parsed.intent,
            reason_codes=["SUPPORTED_INTENT"],
        )

    words = set(normalized.split())
    if words.intersection(_SUPPORTED_TOPIC_WORDS):
        return ScopeDecision(
            status="ambiguous",
            intent=parsed.intent,
            reason_codes=["SUPPORTED_TOPIC_UNCLEAR_INTENT"],
            clarification_question=(
                "Are you asking about module information, eligibility, curriculum "
                "requirements, a verified public course, or a career path?"
            ),
        )

    return ScopeDecision(
        status="out_of_scope",
        intent=parsed.intent,
        reason_codes=["UNSUPPORTED_USER_REQUEST"],
    )


def out_of_scope_response(
    parsed: ParsedAdvisorRequest, decision: ScopeDecision
) -> dict[str, object]:
    """Return a fixed response without invoking retrieval or recommendation logic."""

    return {
        "intent": parsed.intent,
        "status": "out_of_scope",
        "answer": (
            "That request is outside CurricuPath's supported academic-advising "
            "functions. I can help with module information, curriculum requirements, "
            "eligibility, verified public courses, programme comparisons, credits, "
            "and supported career-path information."
        ),
        "scope": decision.model_dump(),
        "conversation_context": {},
    }
