"""SupplierType + SupplierTypeDocumentRequirement."""

from __future__ import annotations

from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from repse.db.base import Base, TimestampMixin
from repse.db.tenant_filter import TenantOwned
from repse.document_types.models import Periodicity


class SupplierTypeOrigin(StrEnum):
    SYSTEM = "system"
    CUSTOM = "custom"


class SupplierTypeStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class RequirementStatus(StrEnum):
    ACTIVE = "active"
    RETIRED = "retired"


class SupplierType(Base, TimestampMixin, TenantOwned):
    """Industry / classification of a supplier (FR-005a spec 001)."""

    __tablename__ = "supplier_types"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "name", name="uq_supplier_types_org_name"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    origin: Mapped[SupplierTypeOrigin] = mapped_column(
        Enum(SupplierTypeOrigin, native_enum=False, length=16),
        nullable=False,
        default=SupplierTypeOrigin.CUSTOM,
        server_default=SupplierTypeOrigin.CUSTOM.value,
    )
    status: Mapped[SupplierTypeStatus] = mapped_column(
        Enum(SupplierTypeStatus, native_enum=False, length=16),
        nullable=False,
        default=SupplierTypeStatus.ACTIVE,
        server_default=SupplierTypeStatus.ACTIVE.value,
    )


class SupplierTypeDocumentRequirement(Base, TimestampMixin, TenantOwned):
    """Which document types each supplier type requires (FR-012b spec 001)."""

    __tablename__ = "supplier_type_document_requirements"
    __table_args__ = (
        UniqueConstraint(
            "supplier_type_id",
            "document_type_id",
            name="uq_supplier_type_doc_req",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    supplier_type_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("supplier_types.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_type_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("document_types.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    periodicity_override: Mapped[Periodicity | None] = mapped_column(
        Enum(Periodicity, native_enum=False, length=16), nullable=True
    )
    status: Mapped[RequirementStatus] = mapped_column(
        Enum(RequirementStatus, native_enum=False, length=16),
        nullable=False,
        default=RequirementStatus.ACTIVE,
        server_default=RequirementStatus.ACTIVE.value,
    )
    created_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
