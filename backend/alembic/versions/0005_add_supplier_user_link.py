"""Add supplier_id FK to users for supplier role

Revision ID: 0005_add_supplier_user_link
Revises: 0004_cell_validations
Create Date: 2026-05-19 00:00:00.000000

Links a user with role='supplier' to a specific Supplier row.
The Role column already uses native_enum=False (VARCHAR), so adding
the new 'supplier' enum value requires no DB schema change — only this
nullable FK column is new.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_add_supplier_user_link"
down_revision: str | None = "0004_cell_validations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("supplier_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_users_supplier",
        "users",
        "suppliers",
        ["supplier_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_users_supplier", "users", ["supplier_id"])


def downgrade() -> None:
    op.drop_index("ix_users_supplier", table_name="users")
    op.drop_constraint("fk_users_supplier", "users", type_="foreignkey")
    op.drop_column("users", "supplier_id")
