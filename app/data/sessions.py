"""Short-lived in-memory conversation state for the prototype UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import Lock
from time import monotonic
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import Engine, delete, select
from sqlalchemy.dialects.postgresql import insert

from app.data.schema import advisor_sessions


@dataclass(frozen=True)
class ConversationContext:
    """Facts retained while the advisor is waiting for clarification."""

    pending_intent: str | None = None
    module_code: str | None = None
    programme_code: str | None = None
    year_of_study: int | None = None
    requirement_type: str | None = None
    interests: tuple[str, ...] = ()
    career_preferences: tuple[str, ...] = ()
    workload_preference: str | None = None
    difficulty_preference: str | None = None
    format_preference: str | None = None
    pending_fact_course_code: str | None = None
    pending_fact_gate: str | None = None
    clarification_attempted: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "pending_intent": self.pending_intent,
            "module_code": self.module_code,
            "programme_code": self.programme_code,
            "year_of_study": self.year_of_study,
            "requirement_type": self.requirement_type,
            "interests": list(self.interests),
            "career_preferences": list(self.career_preferences),
            "workload_preference": self.workload_preference,
            "difficulty_preference": self.difficulty_preference,
            "format_preference": self.format_preference,
            "pending_fact_course_code": self.pending_fact_course_code,
            "pending_fact_gate": self.pending_fact_gate,
            "clarification_attempted": self.clarification_attempted,
        }

    @classmethod
    def from_dict(cls, value: object) -> ConversationContext:
        if not isinstance(value, dict):
            return cls()
        return cls(
            pending_intent=value.get("pending_intent"),
            module_code=value.get("module_code"),
            programme_code=value.get("programme_code"),
            year_of_study=value.get("year_of_study"),
            requirement_type=value.get("requirement_type"),
            interests=tuple(value.get("interests", [])),
            career_preferences=tuple(value.get("career_preferences", [])),
            workload_preference=value.get("workload_preference"),
            difficulty_preference=value.get("difficulty_preference"),
            format_preference=value.get("format_preference"),
            pending_fact_course_code=value.get("pending_fact_course_code"),
            pending_fact_gate=value.get("pending_fact_gate"),
            clarification_attempted=bool(value.get("clarification_attempted", False)),
        )


class SessionStore(Protocol):
    def load(self, session_id: str | None) -> tuple[str, ConversationContext]: ...

    def save(self, session_id: str, context: ConversationContext) -> None: ...

    def clear(self, session_id: str) -> None: ...


@dataclass
class _StoredSession:
    context: ConversationContext = field(default_factory=ConversationContext)
    touched_at: float = field(default_factory=monotonic)


class InMemorySessionStore:
    """Thread-safe temporary store; state disappears when the server restarts."""

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._ttl_seconds = ttl_seconds
        self._sessions: dict[str, _StoredSession] = {}
        self._lock = Lock()

    def load(self, session_id: str | None) -> tuple[str, ConversationContext]:
        with self._lock:
            self._discard_expired()
            resolved_id = session_id or uuid4().hex
            session = self._sessions.setdefault(resolved_id, _StoredSession())
            session.touched_at = monotonic()
            return resolved_id, session.context

    def save(self, session_id: str, context: ConversationContext) -> None:
        with self._lock:
            self._sessions[session_id] = _StoredSession(context=context)

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def _discard_expired(self) -> None:
        cutoff = monotonic() - self._ttl_seconds
        expired = [
            session_id
            for session_id, session in self._sessions.items()
            if session.touched_at < cutoff
        ]
        for session_id in expired:
            del self._sessions[session_id]


class PostgresSessionStore:
    """Persist expiring clarification context without storing conversation text."""

    def __init__(self, engine: Engine, ttl_seconds: int = 3600) -> None:
        self.engine = engine
        self._ttl = timedelta(seconds=ttl_seconds)

    def load(self, session_id: str | None) -> tuple[str, ConversationContext]:
        resolved_id = _session_uuid(session_id)
        now = datetime.now(timezone.utc)
        with self.engine.begin() as connection:
            connection.execute(
                delete(advisor_sessions).where(advisor_sessions.c.expires_at <= now)
            )
            state = connection.scalar(
                select(advisor_sessions.c.profile_state).where(
                    advisor_sessions.c.session_id == resolved_id
                )
            )
            if state is None:
                connection.execute(
                    insert(advisor_sessions).values(
                        session_id=resolved_id,
                        profile_state={},
                        expires_at=now + self._ttl,
                    )
                )
                context = ConversationContext()
            else:
                connection.execute(
                    advisor_sessions.update()
                    .where(advisor_sessions.c.session_id == resolved_id)
                    .values(updated_at=now, expires_at=now + self._ttl)
                )
                context = ConversationContext.from_dict(state)
        return resolved_id.hex, context

    def save(self, session_id: str, context: ConversationContext) -> None:
        resolved_id = _session_uuid(session_id)
        now = datetime.now(timezone.utc)
        statement = insert(advisor_sessions).values(
            session_id=resolved_id,
            profile_state=context.as_dict(),
            expires_at=now + self._ttl,
        )
        statement = statement.on_conflict_do_update(
            index_elements=[advisor_sessions.c.session_id],
            set_={
                "profile_state": statement.excluded.profile_state,
                "profile_version": advisor_sessions.c.profile_version + 1,
                "updated_at": now,
                "expires_at": now + self._ttl,
            },
        )
        with self.engine.begin() as connection:
            connection.execute(statement)

    def clear(self, session_id: str) -> None:
        resolved_id = _existing_session_uuid(session_id)
        if resolved_id is None:
            return
        with self.engine.begin() as connection:
            connection.execute(
                delete(advisor_sessions).where(
                    advisor_sessions.c.session_id == resolved_id
                )
            )


def _session_uuid(value: str | None) -> UUID:
    return _existing_session_uuid(value) or uuid4()


def _existing_session_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None
