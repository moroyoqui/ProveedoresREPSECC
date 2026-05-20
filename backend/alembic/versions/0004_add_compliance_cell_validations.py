"""Add compliance_cell_validations table

Revision ID: 0004_cell_validations
Revises: 0003_add_user_password
Create Date: 2026-05-19 00:00:00.000000

Stores supervisor-level approvals of a document type for a given supplier and
coverage period. Distinct from documents.verified which tracks per-file
authentication. See data-model.md §ComplianceCellValidation (spec 008 US6).
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

DT6 = mysql.DATETIME(fsp=6)

revision: str = "0004_cell_validations"
down_revision: str | None = "0003_add_user_password"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "compliance_cell_validations",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "supplier_id",
            sa.BigInteger(),
            sa.ForeignKey("suppliers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_type_id",
            sa.BigInteger(),
            sa.ForeignKey("document_types.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("coverage_period_start", sa.Date(), nullable=True),
        sa.Column(
            "validated_by",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("validated_at", DT6, nullable=False),
        sa.Column(
            "created_at",
            DT6,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
        ),
        sa.Column(
            "updated_at",
            DT6,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
        ),
        sa.UniqueConstraint(
            "organization_id",
            "supplier_id",
            "document_type_id",
            "coverage_period_start",
            name="uq_cell_validation",
        ),
    )
    op.create_index(
        "ix_compliance_cell_validations_org_supplier",
        "compliance_cell_validations",
        ["organization_id", "supplier_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_compliance_cell_validations_org_supplier", "compliance_cell_validations")
    op.drop_table("compliance_cell_validations")
