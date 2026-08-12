"""Alerts data model (spec 002): config, per-supplier overrides, silences, notifications.

Four additive TenantOwned tables. Nothing in spec 001 changes.
"""

from __future__ import annotations

from datetime import datetime, time
from enum import StrEnum

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from repse.db.base import Base, TimestampMixin
from repse.db.tenant_filter import TenantOwned


def _enum(enum_cls: type[StrEnum], length: int = 16) -> Enum:
    """Match the project convention: non-native string enums by value."""
    return Enum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=lambda e: [m.value for m in e],
    )


class RunStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class AlertChannel(StrEnum):
    EMAIL = "email"
    IN_APP = "in_app"


class AlertType(StrEnum):
    EXPIRING_SOON = "expiring_soon"
    EXPIRED = "expired"


class NotificationStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    READ = "read"


class SilenceEndReason(StrEnum):
    MANUAL = "manual"
    DOCUMENT_RENEWED = "document_renewed"
    TYPE_RETIRED = "type_retired"


class AlertConfig(Base, TimestampMixin, TenantOwned):
    """One row per organization (FR-007). Seeded at org provisioning."""

    __tablename__ = "alert_config"
    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_alert_config_organization_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    expiring_lead_time_days: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=15, server_default="15"
    )
    default_recipient_emails: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    daily_run_at: Mapped[time] = mapped_column(
        Time, nullable=False, default=time(8, 0, 0), server_default=text("'08:00:00'")
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    last_run_status: Mapped[RunStatus | None] = mapped_column(_enum(RunStatus), nullable=True)
    last_run_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class SupplierAlertRecipientOverride(Base, TimestampMixin, TenantOwned):
    """Per-supplier recipient override (FR-008). Supplants the org default."""

    __tablename__ = "supplier_alert_recipients"
    __table_args__ = (
        UniqueConstraint(
            "supplier_id", name="uq_supplier_alert_recipients_supplier"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    supplier_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False
    )
    recipient_emails: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class AlertSilence(Base, TimestampMixin, TenantOwned):
    """Manual per-document silencing (FR-009). Active while ended_at IS NULL."""

    __tablename__ = "alert_silences"
    __table_args__ = (
        Index(
            "ix_alert_silences_active", "organization_id", "document_id", "ended_at"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    silenced_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=text("CURRENT_TIMESTAMP(6)")
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    ended_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    ended_reason: Mapped[SilenceEndReason | None] = mapped_column(
        _enum(SilenceEndReason, length=20), nullable=True
    )


class Notification(Base, TimestampMixin, TenantOwned):
    """One row per channel (FR-004). Daily idempotency via (org, dedup_key)."""

    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("organization_id", "dedup_key", name="uq_notifications_dedup"),
        Index("ix_notifications_org_status", "organization_id", "status", "created_at"),
        Index(
            "ix_notifications_org_user_unread",
            "organization_id",
            "recipient_user_id",
            "read_at",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    supplier_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False
    )
    recipient_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    recipient_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    channel: Mapped[AlertChannel] = mapped_column(_enum(AlertChannel), nullable=False)
    alert_type: Mapped[AlertType] = mapped_column(_enum(AlertType), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    run_date: Mapped[Date] = mapped_column(Date, nullable=False)
    # Application-built idempotency key: f"{supplier_id}:{alert_type}:{run_date}:{channel}:{recipient}".
    dedup_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(
        _enum(NotificationStatus),
        nullable=False,
        default=NotificationStatus.PENDING,
        server_default=NotificationStatus.PENDING.value,
    )
    attempts: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default="0"
    )
    last_attempted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
