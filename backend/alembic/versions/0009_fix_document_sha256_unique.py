"""Replace hard SHA-256 unique constraint with partial unique index

Revision ID: 0009_fix_document_sha256_unique
Revises: 0008_add_repse_folio
Create Date: 2026-06-09 00:00:00.000000

The old constraint uq_documents_org_sha256 (organization_id, file_sha256) blocked
re-upload of a file whose previous version was soft-deleted (deleted_at IS NOT NULL).
This is replaced with a functional partial unique index that only enforces uniqueness
for active (non-deleted) documents, using MySQL 8 functional key parts:

    IF(deleted_at IS NULL, file_sha256, NULL)

NULLs are not considered equal by MySQL unique indexes, so soft-deleted rows never
trigger a uniqueness violation.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0009_fix_document_sha256_unique"
down_revision: str | None = "0008_add_repse_folio"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("uq_documents_org_sha256", "documents", type_="unique")
    op.execute(
        "CREATE UNIQUE INDEX uq_documents_org_sha256_active "
        "ON documents(organization_id, (IF(deleted_at IS NULL, file_sha256, NULL)))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX uq_documents_org_sha256_active ON documents")
    op.create_unique_constraint(
        "uq_documents_org_sha256",
        "documents",
        ["organization_id", "file_sha256"],
    )
