"""DocumentType + TenantDocumentTypeSetting."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from repse.db.base import Base, TimestampMixin


class Periodicity(StrEnum):
    MONTHLY = "monthly"
    BIMONTHLY = "bimonthly"
    ANNUAL = "annual"
    NONE = "none"


class DocumentTypeOrigin(StrEnum):
    CANONICAL = "canonical"
    CUSTOM = "custom"


class DocumentTypeStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class DocumentType(Base, TimestampMixin):
    """Canonical + per-tenant custom document types.

    Canonical rows have organization_id=NULL and origin='canonical'; custom rows
    are tenant-owned. Tenant activation/deactivation of canonical types is
    tracked separately in TenantDocumentTypeSetting.
    """

    __tablename__ = "document_types"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_document_types_slug"),
        UniqueConstraint("organization_id", "name", name="uq_document_types_org_name"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    periodicity: Mapped[Periodicity] = mapped_column(
        Enum(Periodicity, native_enum=False, length=16), nullable=False
    )
    origin: Mapped[DocumentTypeOrigin] = mapped_column(
        Enum(DocumentTypeOrigin, native_enum=False, length=16),
        nullable=False,
        default=DocumentTypeOrigin.CANONICAL,
        server_default=DocumentTypeOrigin.CANONICAL.value,
    )
    # NULL for canonical (visible to every tenant), set for custom (per-tenant).
    organization_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    status: Mapped[DocumentTypeStatus] = mapped_column(
        Enum(DocumentTypeStatus, native_enum=False, length=16),
        nullable=False,
        default=DocumentTypeStatus.ACTIVE,
        server_default=DocumentTypeStatus.ACTIVE.value,
    )


class TenantDocumentTypeSetting(Base):
    """Per-tenant activation of canonical DocumentTypes (data-model.md spec 001)."""

    __tablename__ = "tenant_document_type_settings"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "document_type_id", name="uq_tdts_org_type"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_type_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("document_types.id", ondelete="CASCADE"), nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    last_changed_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    last_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
