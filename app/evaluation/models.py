"""Structured contracts shared by the evaluation runners."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


DecisionLabel = Literal["eligible", "ineligible", "manual_review_required"]
EvaluationArm = Literal["handbook_rag", "structured_rules_llm"]


class EvaluationCitation(BaseModel):
    """A source locator supplied for a material evaluation answer."""

    source_id: str = Field(min_length=1)
    page: str = Field(min_length=1)


class EvaluationDecision(BaseModel):
    """The exact three-class output required from both Gemini arms."""

    decision: DecisionLabel
    answer: str = Field(min_length=1)
    citations: list[EvaluationCitation]


class GroundingAnswer(BaseModel):
    """A concise evidence-bounded answer used for atomic-claim review."""

    answer: str = Field(min_length=1)
    citations: list[EvaluationCitation]
    abstained: bool
