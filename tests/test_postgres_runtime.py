"""Integration checks for PostgreSQL sessions and recommendation audit logs."""

from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.backend import CurricuPathService
from app.config import PROJECT_ROOT, get_settings
from app.data.database import create_database_engine
from app.data.postgres_repository import PostgresCatalogueRepository
from app.data.schema import advisor_sessions, candidate_logs, recommendation_runs
from app.data.sessions import ConversationContext, PostgresSessionStore
from app.main import create_app


@pytest.fixture(scope="module")
def engine():
    database_engine = create_database_engine(get_settings().database_url)
    if not PostgresCatalogueRepository(database_engine).is_healthy():
        pytest.skip("The imported PostgreSQL catalogue is not available.")
    return database_engine


def test_postgres_session_survives_store_recreation(engine) -> None:
    first_store = PostgresSessionStore(engine)
    session_id, _ = first_store.load(None)
    expected = ConversationContext(
        pending_intent="eligibility",
        module_code="ELEN4001A",
        programme_code="EFA04",
    )
    first_store.save(session_id, expected)

    _, restored = PostgresSessionStore(engine).load(session_id)

    assert restored == expected
    first_store.clear(session_id)


def test_advisor_logs_structured_course_candidates_without_prompt_text(engine) -> None:
    repository = PostgresCatalogueRepository(engine)
    service = CurricuPathService(repository, str(PROJECT_ROOT))
    client = TestClient(create_app(service))

    response = client.post(
        "/advisor",
        json={"message": "Find an electric circuits course"},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["run_id"]
    run_id = UUID(result["run_id"])
    with engine.connect() as connection:
        run = connection.execute(
            select(recommendation_runs).where(
                recommendation_runs.c.run_id == run_id
            )
        ).mappings().one()
        candidate_count = connection.scalar(
            select(func.count())
            .select_from(candidate_logs)
            .where(candidate_logs.c.run_id == run_id)
        )
        selected_count = connection.scalar(
            select(func.count())
            .select_from(candidate_logs)
            .where(
                candidate_logs.c.run_id == run_id,
                candidate_logs.c.selected.is_(True),
            )
        )
    assert run["contains_participant_text"] is False
    assert len(run["dataset_version"]) == 64
    assert candidate_count == 24
    assert 1 <= selected_count <= 5

    with engine.begin() as connection:
        connection.execute(
            delete(recommendation_runs).where(
                recommendation_runs.c.run_id == run_id
            )
        )
        connection.execute(
            delete(advisor_sessions).where(
                advisor_sessions.c.session_id == UUID(result["session_id"])
            )
        )
