"""Deterministic resolution of user-facing module names to curriculum codes."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re
from typing import Iterable

from app.advisor.normalisation import normalise_text


_ROMAN_SUFFIXES = {
    "i": "1",
    "ii": "2",
    "iii": "3",
    "iv": "4",
    "ia": "1 a",
    "ib": "1 b",
    "iia": "2 a",
    "iib": "2 b",
}
_NUMBER_WORDS = {
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
}
_QUERY_STOP_WORDS = {
    "a",
    "about",
    "am",
    "can",
    "check",
    "course",
    "eligible",
    "eligibility",
    "for",
    "in",
    "is",
    "me",
    "module",
    "please",
    "part",
    "take",
    "tell",
    "the",
    # Question words and teaching verbs carry no module-name content.
    "who",
    "what",
    "which",
    "does",
    "do",
    "teaches",
    "teach",
    "teaching",
    "covers",
    "cover",
    "covered",
    "lecturer",
}


@dataclass(frozen=True)
class ModuleNameMatch:
    """One catalogue module that plausibly matches user wording."""

    course_code: str
    course_name: str
    score: float


def match_module_names(
    query: str,
    modules: Iterable[dict[str, object]],
) -> tuple[ModuleNameMatch, ...]:
    """Return one confident match or tied alternatives without guessing."""

    full_query = _normalise_name(query)
    query_name = _normalise_name(query, remove_query_noise=True)
    if not query_name:
        return ()

    unique_modules = {
        str(module["course_code"]): str(module["course_name"])
        for module in modules
    }
    candidate_names = {
        course_code: _normalise_name(course_name)
        for course_code, course_name in unique_modules.items()
    }
    exact_embedded = [
        ModuleNameMatch(course_code, unique_modules[course_code], 1.0)
        for course_code, candidate_name in candidate_names.items()
        if _contains_name(full_query, candidate_name)
    ]
    if exact_embedded:
        longest = max(
            len(candidate_names[match.course_code].split())
            for match in exact_embedded
        )
        return tuple(
            sorted(
                (
                    match
                    for match in exact_embedded
                    if len(candidate_names[match.course_code].split()) == longest
                ),
                key=lambda item: item.course_code,
            )
        )

    scored: list[ModuleNameMatch] = []
    for course_code, course_name in unique_modules.items():
        candidate_name = candidate_names[course_code]
        score = _name_score(query_name, candidate_name)
        if score >= 0.65:
            scored.append(ModuleNameMatch(course_code, course_name, round(score, 4)))

    if not scored:
        return ()
    scored.sort(key=lambda item: (-item.score, item.course_code))
    if scored[0].score == 1.0:
        return tuple(item for item in scored if item.score == 1.0)

    best_score = scored[0].score
    return tuple(item for item in scored if best_score - item.score <= 0.04)


def _contains_name(query: str, candidate: str) -> bool:
    return bool(
        candidate
        and re.search(
            rf"(?<![a-z0-9]){re.escape(candidate)}(?![a-z0-9])",
            query,
        )
    )


def _normalise_name(value: str, *, remove_query_noise: bool = False) -> str:
    words = normalise_text(value).split()
    normalized: list[str] = []
    for index, word in enumerate(words):
        if remove_query_noise and re.fullmatch(r"efa\d{2}", word):
            continue
        if (
            remove_query_noise
            and word in _QUERY_STOP_WORDS
            and not (word == "a" and index == len(words) - 1)
        ):
            continue
        if (
            remove_query_noise
            and word == "i"
            and (index == 0 or words[index - 1] in {"can", "could", "may", "would"})
        ):
            continue
        replacement = _NUMBER_WORDS.get(word, _ROMAN_SUFFIXES.get(word, word))
        if replacement == "math":
            replacement = "mathematics"
        numeric_branch = _numeric_branch(replacement)
        if numeric_branch is not None:
            normalized.extend(numeric_branch)
        else:
            normalized.extend(_stem_plural(part) for part in replacement.split())
    return " ".join(normalized)


def _stem_plural(word: str) -> str:
    if len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _name_score(query: str, candidate: str) -> float:
    if query == candidate:
        return 1.0

    query_level, query_branch = _series_suffix(query)
    candidate_level, candidate_branch = _series_suffix(candidate)
    if query_level and candidate_level and query_level != candidate_level:
        return 0.0
    if query_branch and not candidate_branch:
        return 0.0
    if query_branch and candidate_branch and query_branch != candidate_branch:
        return 0.0

    query_tokens = set(query.split())
    candidate_tokens = set(candidate.split())
    if query_tokens and query_tokens <= candidate_tokens:
        return 0.9 + 0.08 * len(query_tokens) / len(candidate_tokens)
    if candidate_tokens and candidate_tokens <= query_tokens:
        return 0.88

    overlap = len(query_tokens & candidate_tokens) / max(
        len(query_tokens), len(candidate_tokens), 1
    )
    sequence = SequenceMatcher(None, query, candidate).ratio()
    if overlap < 0.34:
        return 0.0
    return 0.55 * overlap + 0.45 * sequence


def _numeric_branch(word: str) -> tuple[str, str] | None:
    if len(word) == 2 and word[0] in "1234" and word[1] in "ab":
        return word[0], word[1]
    return None


def _series_suffix(name: str) -> tuple[str | None, str | None]:
    words = name.split()
    if not words:
        return None, None
    if len(words) >= 2 and words[-2] in {"1", "2", "3", "4"} and words[-1] in {"a", "b"}:
        return words[-2], words[-1]
    if words[-1] in {"1", "2", "3", "4"}:
        return words[-1], None
    if words[-1] in {"a", "b"}:
        return None, words[-1]
    return None, None
