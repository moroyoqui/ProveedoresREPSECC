"""Add password_hash to users for local auth

Revision ID: 0003_add_user_password
Revises: 0002_seed_canonical_doc_types
Create Date: 2026-05-17 21:00:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_add_user_password"
down_revision: str | None = "0002_seed_canonical_doc_types"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "password_hash")
