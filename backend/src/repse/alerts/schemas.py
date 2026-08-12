"""Pydantic schemas for the alerts API (contracts/ spec 002)."""

from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# --- Alert configuration (contracts/alert-config.md) ---------------------------


class AlertConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    expiring_lead_time_days: int
    default_recipient_emails: list[EmailStr]
    daily_run_at: time
    timezone: str
    enabled: bool
    last_run_at: datetime | None = None
    last_run_status: str | None = None


class AlertConfigUpdate(BaseModel):
    expiring_lead_time_days: int | None = Field(default=None, ge=1, le=90)
    default_recipient_emails: list[EmailStr] | None = Field(default=None, min_length=1)
    daily_run_at: time | None = None
    enabled: bool | None = None


class SupplierRecipientsOut(BaseModel):
    supplier_id: int
    recipient_emails: list[EmailStr]
    inherited_from_default: bool


class SupplierRecipientsIn(BaseModel):
    recipient_emails: list[EmailStr] = Field(..., min_length=1)


# --- Silences (contracts/alert-silences.md) ------------------------------------


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str


class AlertSilenceCreate(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500)


class AlertSilenceEnd(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class AlertSilenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    reason: str
    started_at: datetime
    ended_at: datetime | None = None
    ended_reason: str | None = None
    silenced_by: UserBrief


# --- In-app notifications (contracts/notifications.md) -------------------------


class NotificationSupplier(BaseModel):
    id: int
    legal_name: str


class NotificationDocument(BaseModel):
    id: int
    document_type_name: str
    period_label: str | None = None
    due_date: date | None = None
    days_until_due: int | None = None
    detail_url: str


class NotificationOut(BaseModel):
    id: int
    type: str
    status: str
    supplier: NotificationSupplier
    documents: list[NotificationDocument]
    created_at: datetime
    read_at: datetime | None = None


class NotificationListOut(BaseModel):
    items: list[NotificationOut]
    unread_count_total: int
    next_cursor: str | None = None
    has_more: bool


class UnreadCountOut(BaseModel):
    unread_count: int
    checked_at: datetime


class TriggerNowOut(BaseModel):
    job_id: str
    scheduled_at: datetime
    status: str
