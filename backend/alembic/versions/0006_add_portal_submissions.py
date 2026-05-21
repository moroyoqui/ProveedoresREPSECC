"""Add portal_submissions table for supplier submission tracking

Revision ID: 0006_add_portal_submissions
Revises: 0005_add_supplier_user_link
Create Date: 2026-05-20 00:00:00.000000

Stores supplier-initiated document submission requests. A row represents
a package of documents for a specific type/period sent to accounting review.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision: str = "0006_add_portal_submissions"
down_revision: str | None = "0005_add_supplier_user_link"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(text("""
        CREATE TABLE portal_submissions (
            id                    BIGINT         NOT NULL AUTO_INCREMENT,
            organization_id       BIGINT         NOT NULL,
            supplier_id           BIGINT         NOT NULL,
            document_type_id      BIGINT         NOT NULL,
            coverage_period_start DATE           NULL,
            submitted_at          DATETIME       NOT NULL,
            submitted_by          BIGINT         NULL,
            status                ENUM('pending','approved','rejected') NOT NULL DEFAULT 'pending',
            rejection_reason      TEXT           NULL,
            pre_submission_status ENUM('missing','expired','pending') NOT NULL,
            created_at            DATETIME       NOT NULL,
            updated_at            DATETIME       NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT fk_ps_org
                FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
            CONSTRAINT fk_ps_sup
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE,
            CONSTRAINT fk_ps_doctype
                FOREIGN KEY (document_type_id) REFERENCES document_types(id) ON DELETE RESTRICT,
            CONSTRAINT fk_ps_user
                FOREIGN KEY (submitted_by) REFERENCES users(id) ON DELETE SET NULL,
            INDEX idx_portal_submissions_lookup
                (organization_id, supplier_id, document_type_id, coverage_period_start, status)
        )
    """))


def downgrade() -> None:
    op.drop_table("portal_submissions")
