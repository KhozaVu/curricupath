"""Typed loading for the validated processed CSV datasets."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from app.advisor.normalisation import Alias, load_aliases
from app.data.validators import validate_course_data, validate_processed_data


@dataclass(frozen=True)
class CurriculumData:
    """Immutable snapshot consumed by deterministic advisor operations."""

    sources: tuple[dict[str, str], ...]
    modules: tuple[dict[str, str], ...]
    rules: tuple[dict[str, str], ...]
    courses: tuple[dict[str, str], ...]
    course_audits: tuple[dict[str, str], ...]
    external_references: tuple[dict[str, str], ...]
    cbo_courses: tuple[dict[str, str], ...]
    missing_cbos: tuple[dict[str, str], ...]
    programme_profiles: tuple[dict[str, str], ...]
    aliases: tuple[Alias, ...]


def load_curriculum_data(data_directory: Path | str) -> CurriculumData:
    """Validate and load a consistent in-memory catalogue snapshot."""

    directory = Path(data_directory)
    validate_processed_data(directory).raise_for_errors()
    validate_course_data(directory).raise_for_errors()
    return CurriculumData(
        sources=tuple(_read_csv(directory / "sources.csv")),
        modules=tuple(_read_csv(directory / "modules.csv")),
        rules=tuple(_read_csv(directory / "rules.csv")),
        courses=tuple(_read_csv(directory / "courses.csv")),
        course_audits=tuple(_read_csv(directory / "course_audit.csv")),
        external_references=tuple(_read_csv(directory / "external_references.csv")),
        cbo_courses=tuple(_read_csv(directory / "cbo_courses.csv")),
        missing_cbos=tuple(_read_csv(directory / "missing_cbos.csv")),
        programme_profiles=tuple(_read_csv(directory / "programme_profiles.csv")),
        aliases=load_aliases(directory / "aliases.csv"),
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))
