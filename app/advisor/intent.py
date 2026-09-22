"""Structured advisor intent extraction with Gemini and deterministic fallback."""

from __future__ import annotations

import re
from time import monotonic
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from app.advisor.normalisation import Alias, canonical_tags, normalise_text


Intent = Literal[
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
    "unknown",
]
RequirementType = Literal["compulsory", "elective_pool"]

YEAR_WORDS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
}
PROGRAMME_NAMES = {
    "electrical engineering": "EFA03",
    "information engineering": "EFA04",
}


class ParsedAdvisorRequest(BaseModel):
    """Facts extracted from one user message; no recommendation decisions."""

    intent: Intent = "unknown"
    module_code: str | None = None
    programme_code: str | None = None
    year_of_study: int | None = Field(default=None, ge=1, le=4)
    requirement_type: RequirementType | None = None
    interests: list[str] = Field(default_factory=list)
    career_preferences: list[str] = Field(default_factory=list)
    workload_preference: Literal["light", "moderate", "heavy"] | None = None
    difficulty_preference: Literal["beginner", "intermediate"] | None = None
    format_preference: str | None = None
    completed_modules: list[str] = Field(default_factory=list)
    current_modules: list[str] = Field(default_factory=list)
    planned_modules: list[str] = Field(default_factory=list)


class IntentExtractor(Protocol):
    def extract(self, text: str) -> ParsedAdvisorRequest: ...


class DeterministicIntentExtractor:
    """Extract exact identifiers and controlled aliases without an external model."""

    def __init__(self, aliases: tuple[Alias, ...]) -> None:
        self.aliases = aliases

    def extract(self, text: str) -> ParsedAdvisorRequest:
        normalized = normalise_text(text)
        tags = canonical_tags(text, self.aliases)
        module_match = re.search(r"\b[A-Z]{4}\d{4}A?\b", text.upper())
        programme_match = re.search(r"\bEFA\d{2}\b", text.upper())
        programme_name = next(
            (name for name in PROGRAMME_NAMES if name in normalized),
            None,
        )
        compared_programmes = all(
            name in normalized for name in PROGRAMME_NAMES
        )
        programme_comparison_language = bool(
            compared_programmes
            and re.search(
                r"\b(?:choose|choice|compare|comparison|versus|vs|difference|better)\b",
                normalized,
            )
        )
        programme_question_language = bool(
            any(
                phrase in normalized
                for phrase in (
                    "what is",
                    "tell me about",
                    "how many credits",
                    "how much credit",
                    "career opportunities",
                    "career opportunity",
                    "career options",
                    "job opportunities",
                )
            )
            or re.search(r"\bwhat careers?\b", normalized)
            or re.search(r"\bwhat jobs?\b", normalized)
        )
        programme_name_is_programme = bool(
            programme_name
            and (
                programme_question_language
                or re.search(
                    r"\b(?:course|courses|module|modules|curriculum|programme|degree|branch)\b",
                    normalized,
                )
            )
        )
        programme_code = (
            programme_match.group(0)
            if programme_match
            else PROGRAMME_NAMES.get(programme_name or "")
            if programme_name_is_programme
            else None
        )
        year_of_study = _extract_year(normalized)
        requirement_type = _extract_requirement_type(normalized)
        interest_based_curriculum = bool(
            programme_code
            and not programme_name_is_programme
            and (tags["interest"] or tags["career"])
            and any(
                word in normalized
                for word in ("recommend", "suggest", "option", "course", "elective")
            )
        )
        if interest_based_curriculum:
            year_of_study = year_of_study or 4
            requirement_type = requirement_type or "elective_pool"

        intent: Intent = "unknown"
        eligibility_language = any(
            phrase in normalized
            for phrase in (
                "eligible",
                "eligibility",
                "can i take",
                "may i take",
                "qualify",
                "prerequisite",
                "corequisite",
                "co requisite",
            )
        )
        elective_recommendation_language = bool(
            requirement_type == "elective_pool"
            and module_match is None
            and (tags["interest"] or tags["career"])
        )
        programme_curriculum_language = bool(
            programme_code
            and module_match is None
            and re.search(r"\b(?:course|courses|module|modules|curriculum)\b", normalized)
            and not re.search(r"\b(?:online|public)\b", normalized)
            and not re.search(r"\b(?:recommend|suggest)\b", normalized)
        )
        programme_information_language = bool(
            programme_code
            and module_match is None
            and (
                programme_question_language
                or re.search(r"\b(?:programme|degree|qualification)\b", normalized)
            )
        )
        credit_question_language = bool(
            re.search(r"\b(?:credit|credits|nqf credits?)\b", normalized)
        )
        module_information_language = any(
            phrase in normalized
            for phrase in (
                "course info",
                "course information",
                "course details",
                "module info",
                "module information",
                "module details",
                "who is the lecturer",
                "who teaches",
                "content covered",
                "what content is covered",
                "course content",
                "what is covered",
                "what topics",
                "how many credits",
                "how much credit",
                "what year",
                "which year",
                "in what year",
                "year is",
            )
        )
        profile_course_language = bool(
            module_match is None
            and (
                re.search(r"\bmy (?:selected )?(?:courses|modules)\b", normalized)
                or re.search(
                    r"\b(?:completed|current) (?:courses|modules)\b",
                    normalized,
                )
                or re.search(
                    r"\b(?:courses|modules) i (?:have|ve|am|m) "
                    r"(?:currently )?(?:completed|doing|taking)\b",
                    normalized,
                )
                or re.search(
                    r"\bwhat (?:courses|modules) am i "
                    r"(?:currently )?(?:doing|taking)\b",
                    normalized,
                )
            )
        )
        career_outcome_language = bool(
            "career" in normalized
            and programme_code is None
            and any(
                phrase in normalized
                for phrase in (
                    "future career",
                    "career path",
                    "career paths",
                    "career option",
                    "career options",
                    "what career",
                    "which career",
                    "lead to",
                )
            )
        )
        if programme_comparison_language:
            intent = "programme_comparison"
        elif credit_question_language and module_match is None and (
            programme_code is not None
            or any(word in normalized for word in ("degree", "programme", "whole course"))
        ):
            intent = "credit_information"
        elif profile_course_language:
            intent = "profile_courses"
        elif elective_recommendation_language:
            intent = "curriculum_list"
        elif eligibility_language:
            intent = "eligibility"
        elif career_outcome_language:
            intent = "career_path"
        elif module_match or module_information_language:
            intent = "module_information"
        elif normalized in {"module", "a module", "module information", "module info"}:
            intent = "module_information"
        elif programme_curriculum_language:
            intent = "curriculum_list"
        elif programme_information_language:
            intent = "programme_information"
        elif (
            "compulsory" in normalized
            or "elective" in normalized
            or "curriculum" in normalized
            or interest_based_curriculum
        ):
            intent = "curriculum_list"
        elif "career" in normalized:
            intent = "career_path"
        elif tags["interest"] or tags["career"] or "course" in normalized:
            intent = "public_course_search"
        elif normalized in {"hi", "hello", "hey", "good morning", "good afternoon"}:
            intent = "greeting"
        elif "help" in normalized or "what can you do" in normalized:
            intent = "help"

        workload = _extract_workload(normalized)
        difficulty = _extract_difficulty(normalized)
        return ParsedAdvisorRequest(
            intent=intent,
            module_code=module_match.group(0) if module_match else None,
            programme_code=programme_code,
            year_of_study=year_of_study,
            requirement_type=requirement_type,
            interests=list(tags["interest"]),
            career_preferences=list(tags["career"]),
            workload_preference=workload,
            difficulty_preference=difficulty,
            format_preference="online" if "online" in normalized else None,
        )


class GeminiIntentExtractor:
    """Use Gemini structured output and fall back if the service is unavailable."""

    def __init__(
        self,
        api_key: str,
        model: str,
        fallback: IntentExtractor,
        allowed_interests: frozenset[str],
        allowed_careers: frozenset[str],
    ) -> None:
        from google import genai
        from google.genai import types

        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=5_000,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        self._model = model
        self._fallback = fallback
        self._allowed_interests = allowed_interests
        self._allowed_careers = allowed_careers
        self._retry_after = 0.0

    def extract(self, text: str) -> ParsedAdvisorRequest:
        from google.genai import types

        if monotonic() < self._retry_after:
            return self._fallback.extract(text)

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=text,
                config=types.GenerateContentConfig(
                    system_instruction=(
                        "Extract only facts explicitly stated in this CurricuPath request. "
                        "Do not recommend courses, infer completed modules, or invent codes. "
                        "Use null or an empty list when information is absent."
                    ),
                    response_mime_type="application/json",
                    response_schema=ParsedAdvisorRequest,
                    temperature=0,
                ),
            )
            parsed = response.parsed
            if not isinstance(parsed, ParsedAdvisorRequest):
                parsed = ParsedAdvisorRequest.model_validate(parsed)
            baseline = self._fallback.extract(text)
            explicit_codes = set(re.findall(r"\b[A-Z]{4}\d{4}A?\b", text.upper()))
            fallback_interests = set(baseline.interests)
            fallback_careers = set(baseline.career_preferences)
            return parsed.model_copy(
                update={
                    "intent": (
                        baseline.intent
                        if baseline.intent != "unknown"
                        else parsed.intent
                    ),
                    "module_code": baseline.module_code,
                    "programme_code": baseline.programme_code,
                    "year_of_study": baseline.year_of_study or parsed.year_of_study,
                    "requirement_type": (
                        baseline.requirement_type or parsed.requirement_type
                    ),
                    "interests": sorted(
                        {
                            _normalise_tag(tag)
                            for tag in parsed.interests
                            if _normalise_tag(tag) in self._allowed_interests
                        }
                        | fallback_interests
                    ),
                    "career_preferences": sorted(
                        {
                            _normalise_tag(tag)
                            for tag in parsed.career_preferences
                            if _normalise_tag(tag) in self._allowed_careers
                        }
                        | fallback_careers
                    ),
                    "completed_modules": sorted(
                        set(parsed.completed_modules) & explicit_codes
                    ),
                    "current_modules": sorted(
                        set(parsed.current_modules) & explicit_codes
                    ),
                    "planned_modules": sorted(
                        set(parsed.planned_modules) & explicit_codes
                    ),
                }
            )
        except Exception:
            self._retry_after = monotonic() + 60
            return self._fallback.extract(text)


def build_intent_extractor(
    aliases: tuple[Alias, ...],
    api_key: str | None,
    model: str,
) -> IntentExtractor:
    """Select Gemini when configured while preserving an offline fallback."""

    fallback = DeterministicIntentExtractor(aliases)
    if not api_key:
        return fallback
    return GeminiIntentExtractor(
        api_key,
        model,
        fallback,
        frozenset(
            alias.canonical_tag for alias in aliases if alias.tag_type == "interest"
        ),
        frozenset(
            alias.canonical_tag for alias in aliases if alias.tag_type == "career"
        ),
    )


def _normalise_tag(tag: str) -> str:
    return normalise_text(tag).replace(" ", "_")


def _extract_year(normalized: str) -> int | None:
    numeric_patterns = (
        r"\b(?:year|level)\s*([1-4])\b",
        r"\b([1-4])(?:st|nd|rd|th)\s+(?:year|level)\b",
    )
    for pattern in numeric_patterns:
        match = re.search(pattern, normalized)
        if match:
            return int(match.group(1))

    word_patterns = (
        r"\b(first|second|third|fourth)\s+(?:year|level)\b",
        r"\b(?:year|level)\s+(first|second|third|fourth)\b",
    )
    for pattern in word_patterns:
        match = re.search(pattern, normalized)
        if match:
            return YEAR_WORDS[match.group(1)]
    return None


def _extract_requirement_type(normalized: str) -> RequirementType | None:
    if re.search(r"\b(?:elective|electives|optional)\b", normalized):
        return "elective_pool"
    if re.search(r"\b(?:compulsory|mandatory)\b", normalized):
        return "compulsory"
    return None


def _extract_workload(normalized: str) -> Literal["light", "moderate", "heavy"] | None:
    patterns = {
        "light": ("light", "low workload", "few hours", "less time"),
        "moderate": ("moderate", "medium workload", "average workload"),
        "heavy": ("heavy", "high workload", "intensive", "demanding"),
    }
    return next(
        (value for value, phrases in patterns.items() if any(phrase in normalized for phrase in phrases)),
        None,
    )


def _extract_difficulty(
    normalized: str,
) -> Literal["beginner", "intermediate"] | None:
    if any(
        phrase in normalized
        for phrase in ("beginner", "beginner friendly", "basic", "easy", "introductory")
    ):
        return "beginner"
    if any(
        phrase in normalized
        for phrase in ("intermediate", "advanced", "challenging")
    ):
        return "intermediate"
    return None
