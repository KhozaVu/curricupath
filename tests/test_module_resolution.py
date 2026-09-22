"""Tests for deterministic module-name resolution."""

from pathlib import Path

from app.advisor.module_resolution import match_module_names
from app.data.repository import CsvCatalogueRepository


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = CsvCatalogueRepository(PROJECT_ROOT / "data" / "processed")
ALL_MODULES = [
    module
    for programme in REPOSITORY.list_programmes()
    for module in REPOSITORY.list_modules(programme["programme_code"])
]


def test_numeric_suffix_resolves_roman_module_name() -> None:
    matches = match_module_names("electronics 1", ALL_MODULES)

    assert [match.course_code for match in matches] == ["ELEN2016A"]


def test_roman_suffix_resolves_without_treating_i_as_pronoun() -> None:
    matches = match_module_names("electronics i", ALL_MODULES)

    assert [match.course_code for match in matches] == ["ELEN2016A"]


def test_broad_name_returns_ambiguous_matches() -> None:
    matches = match_module_names("electronics", ALL_MODULES)

    assert {match.course_code for match in matches} == {"ELEN2016A", "ELEN3002A"}


def test_missing_a_b_suffix_returns_only_matching_level_branches() -> None:
    matches = match_module_names("signals and systems 2", ALL_MODULES)

    assert {match.course_code for match in matches} == {"ELEN3012A", "ELEN3013A"}


def test_separated_a_b_suffix_resolves_one_branch() -> None:
    matches = match_module_names("signals and systems 2 a", ALL_MODULES)

    assert [match.course_code for match in matches] == ["ELEN3012A"]


def test_word_number_and_branch_resolve_one_module() -> None:
    matches = match_module_names("engineering mathematics one b", ALL_MODULES)

    assert [match.course_code for match in matches] == ["MATH1049A"]


def test_missing_branch_clarifies_engineering_mathematics() -> None:
    matches = match_module_names("engineering math 1", ALL_MODULES)

    assert {match.course_code for match in matches} == {"MATH1048A", "MATH1049A"}


def test_branch_without_number_excludes_unbranched_module() -> None:
    matches = match_module_names("signals and systems a", ALL_MODULES)

    assert [match.course_code for match in matches] == ["ELEN3012A"]


def test_numbered_module_families_return_appropriate_ambiguities() -> None:
    expected = {
        "software development": {"ELEN2020A", "ELEN3009A", "ELEN4010A"},
        "control": {"ELEN3016A", "ELEN4016A"},
        "engineering analysis and design 1": {"FEBE1002A", "FEBE1004A"},
        "engineering physics 1": {"PHYS1032A", "PHYS1033A"},
    }

    for query, expected_codes in expected.items():
        assert {
            match.course_code for match in match_module_names(query, ALL_MODULES)
        } == expected_codes


def test_eligibility_language_is_ignored_during_name_matching() -> None:
    matches = match_module_names("Can I take electric circuits?", ALL_MODULES)

    assert [match.course_code for match in matches] == ["ELEN2017A"]


def test_every_complete_catalogue_name_resolves_to_its_code() -> None:
    unique_modules = {
        module["course_code"]: module["course_name"] for module in ALL_MODULES
    }

    for course_code, course_name in unique_modules.items():
        matches = match_module_names(course_name.lower(), ALL_MODULES)
        assert matches[0].course_code == course_code


def test_every_complete_name_resolves_inside_course_information_questions() -> None:
    unique_modules = {
        module["course_code"]: module["course_name"] for module in ALL_MODULES
    }
    wrappers = (
        "who teaches {name}",
        "course info for {name}",
        "what content is covered in {name}",
        "tell me about the {name} course",
    )

    for course_code, course_name in unique_modules.items():
        for wrapper in wrappers:
            matches = match_module_names(
                wrapper.format(name=course_name.lower()),
                ALL_MODULES,
            )
            assert [match.course_code for match in matches] == [course_code]


def test_longest_complete_title_wins_over_embedded_shorter_title() -> None:
    matches = match_module_names(
        "who teaches Electrical Engineering Design II?",
        ALL_MODULES,
    )

    assert [match.course_code for match in matches] == ["ELEN4000A"]


def test_function_words_inside_official_title_are_preserved() -> None:
    matches = match_module_names(
        "what content is covered in Selected Topics in Sociology?",
        ALL_MODULES,
    )

    assert [match.course_code for match in matches] == ["ELEN4019A"]
