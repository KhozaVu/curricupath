"""Relational schema for the PostgreSQL CurricuPath catalogue."""

from __future__ import annotations

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID


NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
metadata = MetaData(naming_convention=NAMING_CONVENTION)


sources = Table(
    "sources",
    metadata,
    Column("source_id", Text, primary_key=True),
    Column("title", Text, nullable=False),
    Column("publisher", Text, nullable=False),
    Column("edition_year", Integer, nullable=False),
    Column("document_type", Text, nullable=False),
    Column("local_path", Text),
    Column("url", Text),
    Column("access_date", Date),
    Column("authority_level", Text, nullable=False),
    Column("handbook_page_offset", Integer),
    Column("notes", Text),
    Column("verification_status", Text, nullable=False),
    Column("authority", Text, nullable=False),
    Column("locator", Text, nullable=False),
    Column("review_date", Date, nullable=False),
    Column("verification_notes", Text, nullable=False),
    CheckConstraint(
        "verification_status IN ('verified', 'incomplete', 'disputed', 'superseded')",
        name="source_verification_status",
    ),
)

programme_profiles = Table(
    "programme_profiles",
    metadata,
    Column("programme_code", Text, primary_key=True),
    Column("programme_name", Text, nullable=False),
    Column("qualification", Text, nullable=False),
    Column("duration_years", Integer, nullable=False),
    Column("study_mode", Text, nullable=False),
    Column("focus", Text, nullable=False),
    Column("overview", Text, nullable=False),
    Column("career_opportunities", Text, nullable=False),
    Column("source_id", ForeignKey("sources.source_id"), nullable=False),
    Column("access_date", Date, nullable=False),
    Column("evidence_notes", Text, nullable=False),
    CheckConstraint("duration_years > 0", name="programme_positive_duration"),
)

modules = Table(
    "modules",
    metadata,
    Column("course_code", Text, primary_key=True),
    Column("course_name", Text, nullable=False),
    Column("nqf_credits", Integer, nullable=False),
    Column("nqf_level", Text, nullable=False),
    CheckConstraint("nqf_credits >= 0", name="module_nonnegative_credits"),
)

curriculum_memberships = Table(
    "curriculum_memberships",
    metadata,
    Column("programme_code", Text, primary_key=True),
    Column("course_code", ForeignKey("modules.course_code"), primary_key=True),
    Column("year_of_study", Integer, primary_key=True),
    Column("programme_name", Text, nullable=False),
    Column("requirement_type", Text, nullable=False),
    Column("selection_group", Text),
    Column("selection_count", Integer),
    Column("source_id", ForeignKey("sources.source_id"), nullable=False),
    Column("handbook_page", Integer, nullable=False),
    CheckConstraint("year_of_study BETWEEN 1 AND 4", name="membership_year"),
    CheckConstraint(
        "requirement_type IN ('compulsory', 'elective_pool', 'required_non_credit')",
        name="membership_requirement_type",
    ),
)

rules = Table(
    "rules",
    metadata,
    Column("rule_id", Text, primary_key=True),
    Column("scope", Text, nullable=False),
    Column("rule_type", Text, nullable=False),
    Column("target_course_code", Text),
    Column("condition_json", JSONB, nullable=False),
    Column("source_id", ForeignKey("sources.source_id"), nullable=False),
    Column("handbook_page", Integer, nullable=False),
    Column("notes", Text),
)

external_references = Table(
    "external_references",
    metadata,
    Column("reference", Text, primary_key=True),
    Column("rule_id", ForeignKey("rules.rule_id"), primary_key=True),
    Column("status", Text, nullable=False),
    Column("verified_source_id", ForeignKey("sources.source_id"), nullable=False),
    Column("interpretation", Text, nullable=False),
    Column("action", Text, nullable=False),
)

module_offerings = Table(
    "module_offerings",
    metadata,
    Column("offering_id", BigInteger, primary_key=True, autoincrement=True),
    Column("module_code", ForeignKey("modules.course_code")),
    Column("reported_course_code", Text, nullable=False),
    Column("academic_year", Integer, nullable=False),
    Column("credits", Integer),
    Column("notional_hours_total", Integer),
    Column("weekly_workload_guidance", Text, nullable=False),
    Column("contact_pattern", Text, nullable=False),
    Column("academic_staff", Text, nullable=False),
    Column("course_coordinator", Text, nullable=False),
    Column("scope", Text, nullable=False),
    Column("prescribed_materials", Text, nullable=False),
    Column("additional_materials", Text, nullable=False),
    Column("source_id", ForeignKey("sources.source_id"), nullable=False),
    Column("curriculum_status", Text, nullable=False),
    Column("verification_status", Text, nullable=False),
    Column("evidence_notes", Text, nullable=False),
    UniqueConstraint("reported_course_code", "academic_year"),
    CheckConstraint(
        "curriculum_status IN ('current', 'not_in_current_curriculum')",
        name="offering_curriculum_status",
    ),
)

missing_cbos = Table(
    "missing_cbos",
    metadata,
    Column("course_code", ForeignKey("modules.course_code"), primary_key=True),
    Column("course_name", Text, nullable=False),
    Column("credits", Integer, nullable=False),
    Column("status", Text, nullable=False),
    Column("candidate_filename", Text),
    Column("notes", Text, nullable=False),
    CheckConstraint(
        "status IN ('missing', 'candidate_found_not_imported')",
        name="missing_cbo_status",
    ),
)

public_courses = Table(
    "public_courses",
    metadata,
    Column("course_id", Text, primary_key=True),
    Column("title", Text, nullable=False),
    Column("provider", Text, nullable=False),
    Column("category", Text, nullable=False),
    Column("description", Text, nullable=False),
    Column("outcomes", Text, nullable=False),
    Column("topic_tags", Text, nullable=False),
    Column("interest_tags", Text, nullable=False),
    Column("career_tags", Text, nullable=False),
    Column("workload", Text, nullable=False),
    Column("format", Text, nullable=False),
    Column("level", Text, nullable=False),
    Column("provider_url", Text, nullable=False),
    Column("rating_mean", Float, nullable=False),
    Column("rating_count", Integer, nullable=False),
    Column("rating_scale", Integer, nullable=False),
    Column("source_id", ForeignKey("sources.source_id"), nullable=False),
    Column("access_date", Date, nullable=False),
    CheckConstraint("rating_scale > 0", name="course_positive_rating_scale"),
    CheckConstraint(
        "rating_mean >= 0 AND rating_mean <= rating_scale",
        name="course_rating_range",
    ),
)

course_audits = Table(
    "course_audits",
    metadata,
    Column("course_id", ForeignKey("public_courses.course_id"), primary_key=True),
    Column("source_id", ForeignKey("sources.source_id"), nullable=False),
    Column("availability_status", Text, nullable=False),
    Column("verification_status", Text, nullable=False),
    Column("recommendation_status", Text, nullable=False),
    Column("audited_title", Text, nullable=False),
    Column("audited_provider", Text, nullable=False),
    Column("audit_date", Date, nullable=False),
    Column("notes", Text, nullable=False),
)

aliases = Table(
    "aliases",
    metadata,
    Column("alias", Text, primary_key=True),
    Column("canonical_tag", Text, nullable=False),
    Column("tag_type", Text, nullable=False),
    CheckConstraint("tag_type IN ('interest', 'career')", name="alias_tag_type"),
)

document_chunks = Table(
    "document_chunks",
    metadata,
    Column("chunk_id", BigInteger, primary_key=True, autoincrement=True),
    Column("item_type", Text, nullable=False),
    Column("item_id", Text, nullable=False),
    Column("chunk_kind", Text, nullable=False),
    Column("content", Text, nullable=False),
    Column("content_hash", Text, nullable=False),
    Column("source_id", ForeignKey("sources.source_id"), nullable=False),
    Column("embedding_provider", Text),
    Column("embedding_model", Text),
    Column("embedding_dimension", Integer),
    Column("embedding", VECTOR(384)),
    Column("embedded_at", DateTime(timezone=True)),
    UniqueConstraint("item_type", "item_id", "chunk_kind", "content_hash"),
    CheckConstraint(
        "embedding_dimension IS NULL OR embedding_dimension = 384",
        name="chunk_embedding_dimension",
    ),
)

Index(
    "ix_document_chunks_embedding_hnsw",
    document_chunks.c.embedding,
    postgresql_using="hnsw",
    postgresql_ops={"embedding": "vector_cosine_ops"},
)

advisor_sessions = Table(
    "advisor_sessions",
    metadata,
    Column("session_id", UUID(as_uuid=True), primary_key=True),
    Column("profile_state", JSONB, nullable=False, server_default="{}"),
    Column("profile_version", Integer, nullable=False, server_default="1"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("expires_at", DateTime(timezone=True), nullable=False),
)

recommendation_runs = Table(
    "recommendation_runs",
    metadata,
    Column("run_id", UUID(as_uuid=True), primary_key=True),
    Column(
        "session_id",
        ForeignKey("advisor_sessions.session_id", ondelete="SET NULL"),
    ),
    Column("profile_version", Integer, nullable=False),
    Column("dataset_version", Text, nullable=False),
    Column("intent", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("contains_participant_text", Boolean, nullable=False, server_default="false"),
)

candidate_logs = Table(
    "candidate_logs",
    metadata,
    Column("candidate_log_id", BigInteger, primary_key=True, autoincrement=True),
    Column("run_id", ForeignKey("recommendation_runs.run_id", ondelete="CASCADE"), nullable=False),
    Column("item_type", Text, nullable=False),
    Column("item_id", Text, nullable=False),
    Column("eligible", Boolean),
    Column("gate_outcomes", JSONB, nullable=False, server_default="{}"),
    Column("score_components", JSONB, nullable=False, server_default="{}"),
    Column("final_score", Float),
    Column("selected", Boolean, nullable=False, server_default="false"),
)
