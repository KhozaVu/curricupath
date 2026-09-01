"""Tests for controlled advisor intent normalisation."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.advisor.normalisation import (
    Alias,
    canonical_tags,
    extract_aliases,
    extract_preferences,
    load_aliases,
    normalise_text,
)


ALIASES_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "aliases.csv"


def test_normalise_text_cleans_case_punctuation_and_hyphens() -> None:
    assert normalise_text("AI, cyber-security!") == "ai cyber security"


def test_ml_alias() -> None:
    aliases = load_aliases(ALIASES_PATH)

    assert canonical_tags("ML", aliases)["interest"] == ("machine_learning",)


def test_aliases_map_user_wording_to_canonical_tags() -> None:
    aliases = load_aliases(ALIASES_PATH)

    tags = canonical_tags(
        "I enjoy machine learning, networks, and cyber security.",
        aliases,
    )

    assert tags["interest"] == (
        "machine_learning",
        "networking",
        "cybersecurity",
    )
    assert tags["career"] == ()


def test_case_insensitive_alias_matching() -> None:
    aliases = load_aliases(ALIASES_PATH)

    assert canonical_tags("I LIKE TELECOMS", aliases)["interest"] == (
        "communications",
    )


def test_punctuation_is_ignored_during_matching() -> None:
    aliases = load_aliases(ALIASES_PATH)

    assert canonical_tags("AI, cyber-security!", aliases)["interest"] == (
        "artificial_intelligence",
        "cybersecurity",
    )


def test_preference_extraction_separates_interests_and_career_preferences() -> None:
    aliases = load_aliases(ALIASES_PATH)

    preferences = extract_preferences(
        "I want a data science career using AI and programming.",
        aliases,
    )

    assert preferences.interests == ("artificial_intelligence", "software")
    assert preferences.career_preferences == ("data_science",)
    assert preferences.workload_preference is None
    assert preferences.format_preference is None


def test_duplicate_tags_are_removed() -> None:
    aliases = load_aliases(ALIASES_PATH)

    assert canonical_tags("ML and machine learning", aliases)["interest"] == (
        "machine_learning",
    )


def test_aliases_do_not_match_inside_larger_words() -> None:
    aliases = load_aliases(ALIASES_PATH)

    tags = canonical_tags("I said something about painting.", aliases)

    assert tags == {"interest": (), "career": ()}


def test_unknown_text_returns_empty_preferences() -> None:
    aliases = load_aliases(ALIASES_PATH)

    preferences = extract_preferences("I enjoy painting and hiking.", aliases)

    assert preferences.interests == ()
    assert preferences.career_preferences == ()


def test_longest_alias_wins() -> None:
    aliases = (
        Alias("machine", "machines", "interest"),
        Alias("machine learning", "machine_learning", "interest"),
    )

    tags = canonical_tags("I like machine learning.", aliases)

    assert tags["interest"] == ("machine_learning",)


def test_extract_aliases_maps_ml_telecoms_and_data_science() -> None:
    aliases = load_aliases(ALIASES_PATH)

    result = extract_aliases(
        "I like ML, telecoms and data science.",
        aliases,
    )

    assert result == {
        "interests": ["communications", "machine_learning"],
        "career_preferences": ["data_science"],
    }


def test_invalid_alias_type_is_rejected(tmp_path: Path) -> None:
    aliases_path = tmp_path / "aliases.csv"
    aliases_path.write_text(
        "alias,canonical_tag,tag_type\nml,machine_learning,invalid\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid alias row"):
        load_aliases(aliases_path)


def test_duplicate_alias_phrase_is_rejected(tmp_path: Path) -> None:
    aliases_path = tmp_path / "aliases.csv"
    aliases_path.write_text(
        "alias,canonical_tag,tag_type\nML,machine_learning,interest\n"
        "ml,machine_learning,interest\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate alias phrase"):
        load_aliases(aliases_path)


def test_missing_csv_columns_are_rejected(tmp_path: Path) -> None:
    aliases_path = tmp_path / "aliases.csv"
    aliases_path.write_text("alias,tag_type\nml,interest\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing required columns: canonical_tag"):
        load_aliases(aliases_path)


def test_empty_aliases_csv_is_rejected(tmp_path: Path) -> None:
    aliases_path = tmp_path / "aliases.csv"
    aliases_path.write_text(
        "alias,canonical_tag,tag_type\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="contains no alias records"):
        load_aliases(aliases_path)
