"""Portal submission entity — supplier-initiated document validation requests."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import BigInteger, Date, DateTime, Enum, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from repse.db.base import Base, TimestampMixin
from repse.db.tenant_filter import TenantOwned


class SubmissionStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PreSubmissionStatus(StrEnum):
    MISSING = "missing"
    EXPIRED = "expired"
    PENDING = "pending"


class PortalSubmission(Base, TimestampMixin, TenantOwned):
    __tablename__ = "portal_submissions"
    __table_args__ = (
        Index(
            "idx_portal_submissions_lookup",
            "organization_id",
            "supplier_id",
            "document_type_id",
            "coverage_period_start",
            "status",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    supplier_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False
    )
    document_type_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("document_types.id", ondelete="RESTRICT"), nullable=False
    )
    coverage_period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    submitted_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(
            SubmissionStatus,
            native_enum=False,
            length=20,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=SubmissionStatus.PENDING,
        server_default=SubmissionStatus.PENDING.value,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    pre_submission_status: Mapped[PreSubmissionStatus] = mapped_column(
        Enum(
            PreSubmissionStatus,
            native_enum=False,
            length=20,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
