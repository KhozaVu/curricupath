"""Add source-backed programme degree profiles.

Revision ID: 20260915_02
Revises: 20260908_01
Create Date: 2026-09-15
"""

from __future__ import annotations

from alembic import op

from app.data.schema import programme_profiles


revision = "20260915_02"
down_revision = "20260908_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    programme_profiles.create(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    programme_profiles.drop(bind=op.get_bind(), checkfirst=True)
