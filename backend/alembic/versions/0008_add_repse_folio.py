"""Add repse_folio column to suppliers

Revision ID: 0008_add_repse_folio
Revises: 0007_add_sectors_giros
Create Date: 2026-06-08 00:00:00.000000

Adds optional text field `repse_folio` (VARCHAR 60) to `suppliers` to store the
STPS REPSE registration folio number. No index needed — not used as a filter.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision: str = "0008_add_repse_folio"
down_revision: str | None = "0007_add_sectors_giros"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(text("""
        ALTER TABLE suppliers
            ADD COLUMN repse_folio VARCHAR(60) NULL DEFAULT NULL AFTER notes
    """))


def downgrade() -> None:
    op.execute(text("""
        ALTER TABLE suppliers DROP COLUMN repse_folio
    """))
