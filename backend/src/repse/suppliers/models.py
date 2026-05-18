"""Supplier entity."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from repse.db.base import Base, TimestampMixin
from repse.db.tenant_filter import TenantOwned


class SupplierStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Supplier(Base, TimestampMixin, TenantOwned):
    __tablename__ = "suppliers"
    __table_args__ = (
        UniqueConstraint("organization_id", "rfc", name="uq_suppliers_org_rfc"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    supplier_type_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("supplier_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rfc: Mapped[str] = mapped_column(String(13), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(255))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[SupplierStatus] = mapped_column(
        Enum(SupplierStatus, native_enum=False, length=16),
        nullable=False,
        default=SupplierStatus.ACTIVE,
        server_default=SupplierStatus.ACTIVE.value,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    deleted_at: Mapped[datetime | None]
