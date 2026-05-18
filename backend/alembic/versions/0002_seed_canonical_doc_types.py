"""Seed canonical DocumentType catalog

Revision ID: 0002_seed_canonical_doc_types
Revises: 0001_baseline
Create Date: 2026-05-17 14:35:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from repse.catalog.canonical import CANONICAL_DOCUMENT_TYPES

revision: str = "0002_seed_canonical_doc_types"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    rows = [
        {
            "slug": ct.slug,
            "name": ct.name,
            "description": ct.description,
            "periodicity": ct.periodicity,
            "origin": "canonical",
            "organization_id": None,
            "status": "active",
        }
        for ct in CANONICAL_DOCUMENT_TYPES
    ]
    table = sa.table(
        "document_types",
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("periodicity", sa.String),
        sa.column("origin", sa.String),
        sa.column("organization_id", sa.BigInteger),
        sa.column("status", sa.String),
    )
    op.bulk_insert(table, rows)


def downgrade() -> None:
    op.execute("DELETE FROM document_types WHERE origin = 'canonical'")
