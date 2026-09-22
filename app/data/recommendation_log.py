"""Privacy-conscious PostgreSQL audit logging for advisor decisions."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Protocol, Sequence
from uuid import UUID, uuid4

from sqlalchemy import Engine, insert, select
from sqlalchemy.exc import SQLAlchemyError

from app.data.schema import (
    advisor_sessions,
    aliases,
    candidate_logs,
    curriculum_memberships,
    document_chunks,
    programme_profiles,
    public_courses,
    recommendation_runs,
    rules,
    sources,
)


class RecommendationLogger(Protocol):
    def log(
        self,
        session_id: str,
        result: dict[str, Any],
        candidates: Sequence[dict[str, Any]],
    ) -> str | None: ...


class PostgresRecommendationLogger:
    """Store structured decisions without retaining participant prompt text."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def log(
        self,
        session_id: str,
        result: dict[str, Any],
        candidates: Sequence[dict[str, Any]],
    ) -> str | None:
        if not candidates:
            return None
        resolved_session = _uuid_or_none(session_id)
        run_id = uuid4()
        try:
            with self.engine.begin() as connection:
                dataset_version = _catalogue_version(connection)
                profile_version = 1
                if resolved_session is not None:
                    profile_version = connection.scalar(
                        select(advisor_sessions.c.profile_version).where(
                            advisor_sessions.c.session_id == resolved_session
                        )
                    ) or 1
                connection.execute(
                    insert(recommendation_runs),
                    {
                        "run_id": run_id,
                        "session_id": resolved_session,
                        "profile_version": profile_version,
                        "dataset_version": dataset_version,
                        "intent": result.get("intent", "unknown"),
                        "status": result.get("status", "unknown"),
                        "contains_participant_text": False,
                    },
                )
                connection.execute(
                    insert(candidate_logs),
                    [
                        {
                            "run_id": run_id,
                            "item_type": candidate["item_type"],
                            "item_id": candidate["item_id"],
                            "eligible": candidate.get("eligible"),
                            "gate_outcomes": candidate.get("gate_outcomes", {}),
                            "score_components": candidate.get(
                                "score_components", {}
                            ),
                            "final_score": candidate.get("final_score"),
                            "selected": candidate.get("selected", False),
                        }
                        for candidate in candidates
                    ],
                )
        except SQLAlchemyError:
            return None
        return run_id.hex


def catalogue_version(engine: Engine) -> str:
    """Return the same catalogue fingerprint used by recommendation logs."""

    with engine.connect() as connection:
        return _catalogue_version(connection)


def _catalogue_version(connection) -> str:
    """Fingerprint evidence, rules, memberships, ratings, and search content."""

    payload = {
        "sources": [
            tuple(row)
            for row in connection.execute(
                select(
                    sources.c.source_id,
                    sources.c.verification_status,
                    sources.c.review_date,
                ).order_by(sources.c.source_id)
            )
        ],
        "aliases": [
            tuple(row)
            for row in connection.execute(
                select(
                    aliases.c.alias,
                    aliases.c.canonical_tag,
                    aliases.c.tag_type,
                ).order_by(aliases.c.alias)
            )
        ],
        "memberships": [
            tuple(row)
            for row in connection.execute(
                select(
                    curriculum_memberships.c.programme_code,
                    curriculum_memberships.c.course_code,
                    curriculum_memberships.c.year_of_study,
                    curriculum_memberships.c.requirement_type,
                ).order_by(
                    curriculum_memberships.c.programme_code,
                    curriculum_memberships.c.course_code,
                    curriculum_memberships.c.year_of_study,
                )
            )
        ],
        "rules": [
            tuple(row)
            for row in connection.execute(
                select(
                    rules.c.rule_id,
                    rules.c.scope,
                    rules.c.rule_type,
                    rules.c.target_course_code,
                    rules.c.condition_json,
                ).order_by(rules.c.rule_id)
            )
        ],
        "programme_profiles": [
            tuple(row)
            for row in connection.execute(
                select(
                    programme_profiles.c.programme_code,
                    programme_profiles.c.overview,
                    programme_profiles.c.career_opportunities,
                    programme_profiles.c.source_id,
                    programme_profiles.c.access_date,
                ).order_by(programme_profiles.c.programme_code)
            )
        ],
        "course_ratings": [
            tuple(row)
            for row in connection.execute(
                select(
                    public_courses.c.course_id,
                    public_courses.c.rating_mean,
                    public_courses.c.rating_count,
                    public_courses.c.rating_scale,
                ).order_by(public_courses.c.course_id)
            )
        ],
        "search_content": [
            tuple(row)
            for row in connection.execute(
                select(
                    document_chunks.c.item_type,
                    document_chunks.c.item_id,
                    document_chunks.c.content_hash,
                ).order_by(
                    document_chunks.c.item_type,
                    document_chunks.c.item_id,
                    document_chunks.c.content_hash,
                )
            )
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _uuid_or_none(value: str) -> UUID | None:
    try:
        return UUID(value)
    except ValueError:
        return None
