"""Create the PostgreSQL catalogue and pgvector storage.

Revision ID: 20260908_01
Revises: None
Create Date: 2026-09-08
"""

from __future__ import annotations

from alembic import op

from app.data.schema import metadata


revision = "20260908_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    metadata.drop_all(bind=op.get_bind())
    op.execute("DROP EXTENSION IF EXISTS vector")
