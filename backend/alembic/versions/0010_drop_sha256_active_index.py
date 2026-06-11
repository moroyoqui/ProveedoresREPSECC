"""Drop org-wide SHA-256 active unique index

Revision ID: 0010_drop_sha256_active_index
Revises: 0009_fix_document_sha256_unique
Create Date: 2026-06-09 00:00:00.000000

The uq_documents_org_sha256_active index was org-wide: it blocked the same PDF
from being uploaded for different suppliers, types, or periods — which is valid
for compliance docs (e.g., the same payment receipt for May and June).

The Python dedup check in service.py already scopes duplicate detection to
(organization_id, supplier_id, document_type_id, coverage_period_start, sha256,
deleted_at IS NULL), which is the correct business-rule scope.  The DB-level
index is removed; the Python check is the single source of truth.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0010_drop_sha256_active_index"
down_revision: str | None = "0009_fix_document_sha256_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP INDEX uq_documents_org_sha256_active ON documents")


def downgrade() -> None:
    op.execute(
        "CREATE UNIQUE INDEX uq_documents_org_sha256_active "
        "ON documents(organization_id, (IF(deleted_at IS NULL, file_sha256, NULL)))"
    )
