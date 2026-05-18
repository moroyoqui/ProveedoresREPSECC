"""Organization (Tenant) entity."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import BigInteger, Date, Enum, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from repse.db.base import Base, TimestampMixin


class OrgStatus(StrEnum):
    ACTIVE = "active"
    GRACE = "grace"
    DELETED = "deleted"


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"
    __table_args__ = (UniqueConstraint("rfc", name="uq_organizations_rfc"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rfc: Mapped[str] = mapped_column(String(13), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    expiring_soon_threshold_days: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=15, server_default="15"
    )
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="America/Mexico_City", server_default="America/Mexico_City"
    )
    status: Mapped[OrgStatus] = mapped_column(
        Enum(OrgStatus, native_enum=False, length=16, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=OrgStatus.ACTIVE,
        server_default=OrgStatus.ACTIVE.value,
    )
    grace_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    deleted_at: Mapped[datetime | None]
