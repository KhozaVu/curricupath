"""Normalize advisor language into a controlled preference vocabulary."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


VALID_TAG_TYPES = {"career", "interest"}


@dataclass(frozen=True)
class Alias:
    """A user-facing phrase mapped to a controlled canonical tag."""

    phrase: str
    canonical_tag: str
    tag_type: str


@dataclass(frozen=True)
class PreferenceProfile:
    """Preferences extracted from a free-text advisor request."""

    interests: tuple[str, ...]
    career_preferences: tuple[str, ...]
    workload_preference: str | None = None
    format_preference: str | None = None


def load_aliases(path: Path | str) -> tuple[Alias, ...]:
    """Load the controlled alias vocabulary from aliases.csv."""

    with Path(path).open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        headers = set(reader.fieldnames or [])
        required_columns = {"alias", "canonical_tag", "tag_type"}
        missing_columns = required_columns - headers
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"aliases.csv is missing required columns: {missing}.")
        rows = list(reader)

    if not rows:
        raise ValueError("aliases.csv contains no alias records.")

    aliases: list[Alias] = []
    seen_aliases: set[str] = set()
    for row in rows:
        phrase = normalise_text(row["alias"])
        canonical_tag = row["canonical_tag"].strip()
        tag_type = row["tag_type"].strip().lower()
        if not phrase or not canonical_tag or tag_type not in VALID_TAG_TYPES:
            raise ValueError(f"Invalid alias row: {row!r}.")
        if phrase in seen_aliases:
            raise ValueError(f"Duplicate alias phrase: {phrase!r}.")
        seen_aliases.add(phrase)
        aliases.append(Alias(phrase, canonical_tag, tag_type))
    return tuple(aliases)


def normalise_text(raw_text: str) -> str:
    """Lowercase and collapse punctuation/whitespace before alias matching."""

    cleaned = raw_text.lower().replace("-", " ")
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def canonical_tags(raw_text: str, aliases: Iterable[Alias]) -> dict[str, tuple[str, ...]]:
    """Find canonical tags using longest non-overlapping phrase matches."""

    normalized = normalise_text(raw_text)
    matches: list[tuple[int, int, Alias]] = []
    for alias in aliases:
        for match in re.finditer(
            rf"(?<![a-z0-9]){re.escape(alias.phrase)}(?![a-z0-9])",
            normalized,
        ):
            matches.append((match.start(), match.end(), alias))

    matches.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    accepted: list[tuple[int, int, Alias]] = []
    for start, end, alias in matches:
        overlaps = any(
            start < accepted_end and end > accepted_start
            for accepted_start, accepted_end, _ in accepted
        )
        if not overlaps:
            accepted.append((start, end, alias))

    tags_by_type: dict[str, list[str]] = {"interest": [], "career": []}
    for _, _, alias in accepted:
        tags = tags_by_type[alias.tag_type]
        if alias.canonical_tag not in tags:
            tags.append(alias.canonical_tag)

    return {tag_type: tuple(tags) for tag_type, tags in tags_by_type.items()}


def extract_preferences(
    raw_text: str,
    aliases: Iterable[Alias],
) -> PreferenceProfile:
    """Convert a free-text request into the advisor's structured preferences."""

    tags = canonical_tags(raw_text, aliases)
    return PreferenceProfile(
        interests=tags["interest"],
        career_preferences=tags["career"],
    )


def extract_aliases(
    raw_text: str,
    aliases: Iterable[Alias],
) -> dict[str, list[str]]:
    """Return sorted canonical tags for the initial advisor intent interface."""

    tags = canonical_tags(raw_text, aliases)
    return {
        "interests": sorted(tags["interest"]),
        "career_preferences": sorted(tags["career"]),
    }
