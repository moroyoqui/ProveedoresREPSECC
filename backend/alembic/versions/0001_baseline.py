"""Baseline schema

Revision ID: 0001_baseline
Revises:
Create Date: 2026-05-17 14:30:00.000000

Creates every table required by spec 001:
  organizations, users, supplier_types, supplier_type_document_requirements,
  document_types, tenant_document_type_settings, suppliers, documents,
  audit_log.

Schema details are kept in sync with `repse.*.models`; SQLAlchemy generates the
DDL via Base.metadata.create_all on the bind, but we go explicit here so the
migration is reviewable.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# Use MySQL DATETIME(6) so columns accept CURRENT_TIMESTAMP(6) as default.
DT6 = mysql.DATETIME(fsp=6)

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("legal_name", sa.String(length=255), nullable=False),
        sa.Column("rfc", sa.String(length=13), nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=False),
        sa.Column("expiring_soon_threshold_days", sa.SmallInteger(), nullable=False, server_default="15"),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="America/Mexico_City"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("grace_until", sa.Date()),
        sa.Column("created_at", DT6, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        sa.Column("updated_at", DT6, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        sa.Column("deleted_at", DT6),
        sa.UniqueConstraint("rfc", name="uq_organizations_rfc"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("oidc_subject", sa.String(length=255)),
        sa.Column("oidc_provider", sa.String(length=16)),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("last_login_at", DT6),
        sa.Column("created_at", DT6, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        sa.Column("updated_at", DT6, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_users_organization_id_organizations", ondelete="RESTRICT"),
        sa.UniqueConstraint("organization_id", "email", name="uq_users_email"),
        sa.UniqueConstraint("oidc_provider", "oidc_subject", name="uq_users_oidc"),
    )
    op.create_index("ix_users_organization_id", "users", ["organization_id"])

    op.create_table(
        "document_types",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("periodicity", sa.String(length=16), nullable=False),
        sa.Column("origin", sa.String(length=16), nullable=False, server_default="canonical"),
        sa.Column("organization_id", sa.BigInteger()),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("created_at", DT6, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        sa.Column("updated_at", DT6, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_document_types_organization_id_organizations", ondelete="CASCADE"),
        sa.UniqueConstraint("slug", name="uq_document_types_slug"),
        sa.UniqueConstraint("organization_id", "name", name="uq_document_types_org_name"),
    )
    op.create_index("ix_document_types_organization_id", "document_types", ["organization_id"])

    op.create_table(
        "tenant_document_type_settings",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("document_type_id", sa.BigInteger(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("last_changed_by", sa.BigInteger()),
        sa.Column("last_changed_at", DT6),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_tdts_organization_id_organizations", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_type_id"], ["document_types.id"], name="fk_tdts_document_type_id_document_types", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["last_changed_by"], ["users.id"], name="fk_tdts_last_changed_by_users", ondelete="SET NULL"),
        sa.UniqueConstraint("organization_id", "document_type_id", name="uq_tdts_org_type"),
    )
    op.create_index("ix_tdts_organization_id", "tenant_document_type_settings", ["organization_id"])

    op.create_table(
        "supplier_types",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("origin", sa.String(length=16), nullable=False, server_default="custom"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("created_at", DT6, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        sa.Column("updated_at", DT6, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_supplier_types_organization_id_organizations", ondelete="RESTRICT"),
        sa.UniqueConstraint("organization_id", "name", name="uq_supplier_types_org_name"),
    )
    op.create_index("ix_supplier_types_organization_id", "supplier_types", ["organization_id"])

    op.create_table(
        "supplier_type_document_requirements",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("supplier_type_id", sa.BigInteger(), nullable=False),
        sa.Column("document_type_id", sa.BigInteger(), nullable=False),
        sa.Column("periodicity_override", sa.String(length=16)),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("created_by", sa.BigInteger()),
        sa.Column("created_at", DT6, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        sa.Column("updated_at", DT6, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_stdr_organization_id_organizations", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supplier_type_id"], ["supplier_types.id"], name="fk_stdr_supplier_type_id_supplier_types", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_type_id"], ["document_types.id"], name="fk_stdr_document_type_id_document_types", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_stdr_created_by_users", ondelete="SET NULL"),
        sa.UniqueConstraint("supplier_type_id", "document_type_id", name="uq_supplier_type_doc_req"),
    )
    op.create_index("ix_stdr_organization_id", "supplier_type_document_requirements", ["organization_id"])
    op.create_index("ix_stdr_supplier_type_id", "supplier_type_document_requirements", ["supplier_type_id"])
    op.create_index("ix_stdr_document_type_id", "supplier_type_document_requirements", ["document_type_id"])

    op.create_table(
        "suppliers",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("supplier_type_id", sa.BigInteger(), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=False),
        sa.Column("rfc", sa.String(length=13), nullable=False),
        sa.Column("contact_name", sa.String(length=255)),
        sa.Column("contact_email", sa.String(length=255)),
        sa.Column("contact_phone", sa.String(length=32)),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", DT6, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        sa.Column("updated_at", DT6, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        sa.Column("deleted_at", DT6),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_suppliers_organization_id_organizations", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supplier_type_id"], ["supplier_types.id"], name="fk_suppliers_supplier_type_id_supplier_types", ondelete="RESTRICT"),
        sa.UniqueConstraint("organization_id", "rfc", name="uq_suppliers_org_rfc"),
    )
    op.create_index("ix_suppliers_organization_id", "suppliers", ["organization_id"])
    op.create_index("ix_suppliers_supplier_type_id", "suppliers", ["supplier_type_id"])
    op.create_index("ix_suppliers_status", "suppliers", ["status"])

    op.create_table(
        "documents",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("supplier_id", sa.BigInteger(), nullable=False),
        sa.Column("document_type_id", sa.BigInteger(), nullable=False),
        sa.Column("coverage_period_start", sa.Date()),
        sa.Column("coverage_period_end", sa.Date()),
        sa.Column("due_date_calculated", sa.Date()),
        sa.Column("due_date_effective", sa.Date()),
        sa.Column("due_date_override_reason", sa.String(length=255)),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("verified_by", sa.BigInteger()),
        sa.Column("verified_at", DT6),
        sa.Column("verified_note", sa.String(length=500)),
        sa.Column("version", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("is_latest", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("last_updated_by", sa.BigInteger()),
        sa.Column("last_updated_at", DT6),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("file_name_original", sa.String(length=255), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("file_mime_type", sa.String(length=127), nullable=False),
        sa.Column("file_sha256", sa.CHAR(length=64), nullable=False),
        sa.Column("ocr_status", sa.String(length=16), nullable=False, server_default="not_run"),
        sa.Column("ocr_extracted_rfc", sa.String(length=13)),
        sa.Column("ocr_extracted_issued_at", sa.Date()),
        sa.Column("ocr_extracted_valid_until", sa.Date()),
        sa.Column("ocr_raw_text", sa.Text()),
        sa.Column("uploaded_by", sa.BigInteger(), nullable=False),
        sa.Column("created_at", DT6, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        sa.Column("updated_at", DT6, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        sa.Column("deleted_at", DT6),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_documents_organization_id_organizations", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], name="fk_documents_supplier_id_suppliers", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_type_id"], ["document_types.id"], name="fk_documents_document_type_id_document_types", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["verified_by"], ["users.id"], name="fk_documents_verified_by_users", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["last_updated_by"], ["users.id"], name="fk_documents_last_updated_by_users", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], name="fk_documents_uploaded_by_users", ondelete="RESTRICT"),
        sa.UniqueConstraint("organization_id", "file_sha256", name="uq_documents_org_sha256"),
    )
    op.create_index("ix_documents_organization_id", "documents", ["organization_id"])
    op.create_index(
        "ix_documents_org_supplier_type_period",
        "documents",
        ["organization_id", "supplier_id", "document_type_id", "coverage_period_start"],
    )
    op.create_index("ix_documents_org_due", "documents", ["organization_id", "due_date_effective"])
    op.create_index("ix_documents_org_status", "documents", ["organization_id", "status"])
    op.create_index("ix_documents_org_last_updated", "documents", ["organization_id", "last_updated_at"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("actor_user_id", sa.BigInteger()),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.BigInteger()),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", DT6, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_audit_log_organization_id_organizations", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], name="fk_audit_log_actor_user_id_users", ondelete="SET NULL"),
    )
    op.create_index("ix_audit_log_organization_id", "audit_log", ["organization_id"])
    op.create_index("ix_audit_org_created", "audit_log", ["organization_id", "created_at"])
    op.create_index("ix_audit_entity", "audit_log", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("documents")
    op.drop_table("suppliers")
    op.drop_table("supplier_type_document_requirements")
    op.drop_table("supplier_types")
    op.drop_table("tenant_document_type_settings")
    op.drop_table("document_types")
    op.drop_table("users")
    op.drop_table("organizations")
