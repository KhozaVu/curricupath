"""Structured advisor intent extraction with Gemini and deterministic fallback."""

from __future__ import annotations

import re
import warnings
from contextvars import ContextVar
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
    "eligible_modules",
    "module_recommendations",
    "career_path",
    "unknown",
]
RequirementType = Literal["compulsory", "elective_pool"]

MIN_REQUEST_TIMEOUT_MS = 15_000  # API minimum is 10 s

# Which extractor read the current request: "gemini" or "offline" (parser only). Set per request
# context so concurrent requests do not overwrite each other; shown in the advisor response.
EXTRACTOR_SOURCE: ContextVar[str | None] = ContextVar("extractor_source", default=None)

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


_CODE = r"[A-Za-z]{4}\s?\d{4}[Aa]?"
_CODE_LIST = rf"({_CODE}(?:\s*(?:,|and|&)\s*{_CODE})*)"
_LEAD = r"(?:the\s+)?(?:modules?\s+|courses?\s+)?"
# (status, phrases that precede a module code). Negative forms are matched and masked first so
# "have not completed X" is never also read as "completed X".
_DECLARATION_PATTERNS = (
    ("not_completed", re.compile(
        r"\b(?:failed|fail|flunked|did not pass|didn'?t pass|not passed|have not passed|haven'?t passed|"
        r"have not completed|haven'?t completed|not completed|have not done|haven'?t done|never passed|"
        r"never completed)\s+" + _LEAD + _CODE_LIST, re.IGNORECASE)),
    ("completed", re.compile(
        r"\b(?:completed|passed|finished|have done|already done)\s+" + _LEAD + _CODE_LIST, re.IGNORECASE)),
    ("current", re.compile(
        r"\b(?:currently\s+)?(?:taking|doing|enrolled in|studying)\s+" + _LEAD + _CODE_LIST, re.IGNORECASE)),
    ("planned", re.compile(
        r"\b(?:plan(?:ning)?\s+to\s+(?:take|do)|will\s+(?:take|do)|going\s+to\s+(?:take|do))\s+"
        + _LEAD + _CODE_LIST, re.IGNORECASE)),
)
_NEGATIVE_AFTER = re.compile(
    rf"({_CODE})\s*[\(,:-]?\s*(?:i\s+)?(?:failed|not passed|not completed|not done|was failed)\b",
    re.IGNORECASE,
)


_ASKS_TO_TAKE = re.compile(
    r"\b(?:can|may|could|am|will|would|should)\s+i\s+(?:take|do|register|enrol|enroll|sign up|join|add|be)\b"
    r"|\b(?:eligible|eligibility|qualify|allowed to|permitted to|open to me|able to (?:take|register))\b",
    re.IGNORECASE,
)


def asks_whether_student_can_take(text: str) -> bool:
    """True for questions such as 'Can I take X?' where stated statuses are background facts."""

    return bool(_ASKS_TO_TAKE.search(text))


def _clean_code(raw: str) -> str:
    code = re.sub(r"\s+", "", raw).upper()
    return code if code[-1].isalpha() else code + "A"


def extract_declared_modules(text: str) -> dict[str, list[str]]:
    """Module codes the student states a status for ("failed X", "completed Y", "taking Z")."""

    found: dict[str, dict[str, None]] = {k: {} for k, _ in _DECLARATION_PATTERNS}
    masked = text
    for status, pattern in _DECLARATION_PATTERNS:
        for match in pattern.finditer(masked):
            for raw in re.findall(_CODE, match.group(1)):
                found[status][_clean_code(raw)] = None
        masked = pattern.sub(lambda m: " " * len(m.group(0)), masked)
    for match in _NEGATIVE_AFTER.finditer(text):
        found["not_completed"][_clean_code(match.group(1))] = None
    return {status: list(codes) for status, codes in found.items()}


def extract_not_completed_modules(text: str) -> list[str]:
    """Module codes the student says they failed or have not completed (codes only)."""

    return extract_declared_modules(text)["not_completed"]


class ParsedAdvisorRequest(BaseModel):
    """Facts extracted from one user message; no recommendation decisions."""

    intent: Intent = "unknown"
    module_code: str | None = None
    programme_code: str | None = None
    year_of_study: int | None = Field(default=None, ge=1, le=4)
    requirement_type: RequirementType | None = None
    include_electives: bool = False
    interests: list[str] = Field(default_factory=list)
    career_preferences: list[str] = Field(default_factory=list)
    workload_preference: Literal["light", "moderate", "heavy"] | None = None
    difficulty_preference: Literal["beginner", "intermediate"] | None = None
    format_preference: str | None = None
    completed_modules: list[str] = Field(default_factory=list)
    # Modules the student says they failed or have not passed. Read by the deterministic
    # parser only, never from a language model.
    not_completed_modules: list[str] = Field(default_factory=list)
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
        extra_interests = {
            "software": "software", "intelligent systems": "artificial_intelligence",
            "power systems": "power_systems", "renewable energy": "renewable_energy",
            "robotics": "control", "embedded systems": "electronics_engineering",
        }
        tags = {**tags, "interest": tuple(dict.fromkeys([*tags["interest"], *[
            tag for phrase, tag in extra_interests.items()
            if re.search(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])", normalized)
        ]]))}
        declared = extract_declared_modules(text)
        declared_codes = {code for codes in declared.values() for code in codes}
        code_matches = list(re.finditer(r"\b[A-Z]{4}\d{4}A?\b", text.upper()))
        # The module being asked about is the first one the student did not just state a status
        # for ("I failed X. Can I take Y?" asks about Y).
        module_match = next(
            (m for m in code_matches if _clean_code(m.group(0)) not in declared_codes),
            # Every code was given a status. In a "can I take ...?" question the target is then
            # named instead of coded; otherwise ("if I am taking X, what careers...") keep X.
            None if asks_whether_student_can_take(text) else (code_matches[0] if code_matches else None),
        )
        programme_match = re.search(r"\bEFA\d{2}\b", text.upper())
        # "EE" / "IE" (upper case only, so "i.e." is not read as a programme).
        abbreviation_match = re.search(r"\b(EE|IE)\b", text)
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
        programme_words = {a.canonical_tag for a in self.aliases if a.phrase in PROGRAMME_NAMES}
        other_tags = (set(tags["interest"]) | set(tags["career"])) - programme_words
        programme_name_is_programme = bool(
            programme_name
            and (
                programme_question_language
                or re.search(
                    r"\b(?:course|courses|module|modules|curriculum|programme|degree|branch|"
                    r"students?|stream|option|major|specialisation|specialization)\b",
                    normalized,
                )
                # "as an information engineering student", "I study electrical engineering"
                or re.search(r"\b(?:i am|i m|im|i study|studying|as an?|my)\b", normalized)
                # a bare reply to "Which programme are you in?"
                or normalized in set(PROGRAMME_NAMES) | {"electrical", "information"}
                # "fourth year electrical engineering electives": a list, unless another interest
                # ("electives about power") makes the programme name a preference instead
                or (
                    re.search(r"\b(?:electives?|compulsory)\b", normalized)
                    and not other_tags
                    and not re.search(
                        r"\b(?:i like|i love|i enjoy|interested in|passionate|recommend|suggest|"
                        r"focus(?:ed)? on|into)\b",
                        normalized,
                    )
                )
            )
        )
        programme_code = (
            programme_match.group(0)
            if programme_match
            else {"EE": "EFA03", "IE": "EFA04"}[abbreviation_match.group(1)]
            if abbreviation_match
            else PROGRAMME_NAMES.get(programme_name or "")
            if programme_name_is_programme
            else {"electrical": "EFA03", "information": "EFA04"}.get(normalized)
        )
        if programme_name_is_programme and (
            re.search(
                r"\b(?:students?|stream|option|major|i am|i m|im|i study|studying|as an?)\b", normalized
            )
            # "fourth year electrical engineering elective courses": a list for the programme
            or re.search(r"\b(?:electives?|compulsory|core modules?)\b|\b(?:what|which)\s+modules\b", normalized)
        ):
            # "electrical engineering students ..." names the programme; it is not a career interest.
            tags = {
                kind: tuple(tag for tag in values if tag not in programme_words)
                for kind, values in tags.items()
            }
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
        ) or bool(
            # Registration and permission wording: "am I allowed to register for X",
            # "is X open to me", "can I sign up for / enrol in X", "can I do X this year",
            # "I want to take X, is that ok".
            re.search(
                r"\b(?:allowed|permitted|able) to (?:take|do|register|enrol|enroll|sign up)\b"
                r"|\b(?:can|may|could) i do\b(?! (?:anything|something|about|it|that|this|more|better|well|to)\b)"
                r"|\b(?:can|may|could) i (?:register|enrol|enroll|sign up|join|add)\b"
                r"|\bopen to me\b"
                r"|\b(?:register|registering|enrol|enroll|enrolling|sign up|signing up) (?:for|in|into)\b"
                r"|\bwant to (?:take|do|register|enrol|enroll)\b.*\b(?:ok|okay|fine|allowed|possible)\b",
                normalized,
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
                "tell me about",
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
        elif module_match is None and eligibility_language and re.search(
            r"\b(?:modules|courses|electives|options)\b|\bwhat can i (?:take|do|register)\b", normalized
        ):
            intent = "eligible_modules"
        elif eligibility_language:
            intent = "eligibility"
        elif programme_curriculum_language:
            intent = "curriculum_list"
        elif programme_information_language:
            intent = "programme_information"
        elif module_match is None and module_information_language and not programme_code:
            intent = "module_information"
        elif module_match is None and (tags["interest"] or tags["career"]) and not career_outcome_language and not module_information_language:
            intent = "module_recommendations"
        elif module_match is None and re.search(r"\b(?:recommend|suggest)\b", normalized):
            intent = "module_recommendations"
        elif elective_recommendation_language:
            intent = "curriculum_list"
        elif module_match is None and re.search(
            r"\b(?:electives?|compulsory|core modules?)\b|\b(?:what|which)\s+modules\b", normalized
        ):
            # "what electives can I take?" asks for a list, not about one named module.
            intent = "curriculum_list"
        elif eligibility_language:
            intent = "eligibility"
        elif career_outcome_language:
            intent = "career_path"
        elif module_match or module_information_language:
            intent = "module_information"
        elif normalized in {"module", "a module", "module information", "module info"}:
            intent = "module_information"
        elif programme_curriculum_language or (year_of_study and re.search(r"\b(?:modules?|courses?)\b", normalized)):
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
            intent = "module_recommendations"
        elif normalized in {"hi", "hello", "hey", "good morning", "good afternoon"}:
            intent = "greeting"
        elif "help" in normalized or "what can you do" in normalized:
            intent = "help"

        workload = _extract_workload(normalized)
        difficulty = _extract_difficulty(normalized)
        return ParsedAdvisorRequest(
            intent=intent,
            module_code=module_match.group(0) if module_match else None,
            completed_modules=declared["completed"],
            current_modules=declared["current"],
            planned_modules=declared["planned"],
            not_completed_modules=declared["not_completed"],
            programme_code=programme_code,
            year_of_study=year_of_study,
            requirement_type=None if (year_of_study in {1,2,3} and re.search(r"\band\s+(?:the\s+)?electives?\b", normalized)) else requirement_type,
            include_electives=bool(year_of_study in {1,2,3} and re.search(r"\band\s+(?:the\s+)?electives?\b", normalized)),
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
                # The Gemini API rejects client deadlines under 10 s (HTTP 400), which made every
                # call fail silently into the offline parser when this was 5 s.
                timeout=MIN_REQUEST_TIMEOUT_MS,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        self._model = model
        self._fallback = fallback
        self._allowed_interests = allowed_interests
        self._allowed_careers = allowed_careers
        self._retry_after = 0.0
        self._warned = False

    def extract(self, text: str) -> ParsedAdvisorRequest:
        from google.genai import types

        if monotonic() < self._retry_after:
            EXTRACTOR_SOURCE.set("offline")
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
            EXTRACTOR_SOURCE.set("gemini")
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
                    "not_completed_modules": baseline.not_completed_modules,
                    "programme_code": baseline.programme_code,
                    "year_of_study": baseline.year_of_study,
                    "include_electives": baseline.include_electives,
                    "requirement_type": (
                        baseline.requirement_type
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
                        (set(parsed.completed_modules) & explicit_codes)
                        | set(baseline.completed_modules)
                    ),
                    "current_modules": sorted(
                        (set(parsed.current_modules) & explicit_codes)
                        | set(baseline.current_modules)
                    ),
                    "planned_modules": sorted(
                        set(parsed.planned_modules) & explicit_codes
                    ),
                }
            )
        except Exception as error:
            self._retry_after = monotonic() + 60
            if not getattr(self, "_warned", False):
                self._warned = True
                warnings.warn(
                    f"Gemini intent extraction failed ({type(error).__name__}: "
                    f"{str(error)[:160]}); using the offline parser for the next 60 s.",
                    RuntimeWarning,
                    stacklevel=2,
                )
            EXTRACTOR_SOURCE.set("offline")
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
