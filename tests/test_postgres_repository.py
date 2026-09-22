"""Integration checks for PostgreSQL catalogue retrieval and CSV fallback."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from app.backend import CurricuPathService
from app.config import PROJECT_ROOT, get_settings
from app.data.database import create_database_engine
from app.data.postgres_repository import PostgresCatalogueRepository
from app.data.repository import CsvCatalogueRepository
from app.main import _build_catalogue_repository


PROCESSED_DATA = Path(__file__).resolve().parents[1] / "data" / "processed"


@pytest.fixture(scope="module")
def repositories():
    settings = get_settings()
    postgres = PostgresCatalogueRepository(
        create_database_engine(settings.database_url)
    )
    if not postgres.is_healthy():
        pytest.skip("The imported PostgreSQL catalogue is not available.")
    return CsvCatalogueRepository(PROCESSED_DATA), postgres


def test_postgres_programmes_aliases_and_counts_match_csv(repositories) -> None:
    csv, postgres = repositories

    assert postgres.list_programmes() == csv.list_programmes()
    assert set(postgres.get_aliases()) == set(csv.get_aliases())
    assert postgres.catalogue_summary() == csv.catalogue_summary()


def test_postgres_programme_profiles_match_csv(repositories) -> None:
    csv, postgres = repositories

    for programme_code in ("EFA03", "EFA04"):
        assert postgres.get_programme_profile(programme_code) == csv.get_programme_profile(
            programme_code
        )


def test_postgres_curriculum_membership_matches_csv(repositories) -> None:
    csv, postgres = repositories

    assert postgres.list_modules("EFA04", 4) == csv.list_modules("EFA04", 4)


def test_postgres_module_and_cbo_information_match_csv(repositories) -> None:
    csv, postgres = repositories

    postgres_module = postgres.get_module("ELEN4001A")
    csv_module = csv.get_module("ELEN4001A")
    assert postgres_module is not None
    assert csv_module is not None
    assert postgres_module["course_name"] == csv_module["course_name"]
    assert postgres_module["memberships"] == csv_module["memberships"]
    assert (
        postgres_module["course_information"]
        == csv_module["course_information"]
    )
    assert postgres_module["sources"] == csv_module["sources"]

    for course_code in ("MATH2014A", "PHYS2007A"):
        assert postgres.get_module(course_code) == csv.get_module(course_code)


def test_postgres_verified_course_catalogue_matches_csv(repositories) -> None:
    csv, postgres = repositories

    csv_courses = csv.list_courses(limit=100)
    postgres_courses = postgres.list_courses(limit=100)
    assert [row["course_id"] for row in postgres_courses] == [
        row["course_id"] for row in csv_courses
    ]
    assert postgres.get_course("CRS001") == csv.get_course("CRS001")


def test_postgres_eligibility_matches_csv(repositories) -> None:
    csv, postgres = repositories
    csv_service = CurricuPathService(csv, str(PROJECT_ROOT))
    postgres_service = CurricuPathService(postgres, str(PROJECT_ROOT))
    profiles = [
        ("ELEN4001A", "EFA04", set(), set(), set()),
        ("ELEN2017A", "EFA04", set(), set(), set()),
        ("ELEN3002A", "EFA03", {"ELEN2005A"}, set(), set()),
    ]

    for arguments in profiles:
        assert postgres_service.eligibility(*arguments) == csv_service.eligibility(
            *arguments
        )


def test_postgres_evidence_has_same_audited_sets(repositories) -> None:
    csv, postgres = repositories
    csv_evidence = csv.evidence()
    postgres_evidence = postgres.evidence()

    assert postgres_evidence["summary"] == csv_evidence["summary"]
    assert {
        row["source_id"] for row in postgres_evidence["sources"]
    } == {row["source_id"] for row in csv_evidence["sources"]}
    assert postgres_evidence["rule_counts"] == csv_evidence["rule_counts"]
    assert (
        postgres_evidence["source_status_counts"]
        == csv_evidence["source_status_counts"]
    )


def test_repository_builder_falls_back_to_csv_when_postgres_is_down() -> None:
    settings = replace(
        get_settings(),
        catalogue_backend="postgresql",
        catalogue_csv_fallback=True,
        database_url=(
            "postgresql+psycopg://curricupath:unused@127.0.0.1:1/"
            "curricupath?connect_timeout=1"
        ),
    )

    repository = _build_catalogue_repository(settings)

    assert isinstance(repository, CsvCatalogueRepository)
