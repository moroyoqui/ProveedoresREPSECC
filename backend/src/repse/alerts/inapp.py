"""In-app notification row construction (T014) + the shared dedup key.

In-app entries are considered delivered on creation (status SENT); the email
channel starts PENDING and is sent by the SMTP step.
"""

from __future__ import annotations

from datetime import date

from repse.alerts.models import (
    AlertChannel,
    AlertType,
    Notification,
    NotificationStatus,
)


def make_dedup_key(
    supplier_id: int,
    alert_type: AlertType,
    run_date: date,
    channel: AlertChannel,
    recipient: str | int,
) -> str:
    """Daily-idempotency key: one notification per supplier/type/day/channel/recipient."""
    return f"{supplier_id}:{alert_type.value}:{run_date.isoformat()}:{channel.value}:{recipient}"


def build_inapp_notifications(
    *,
    organization_id: int,
    supplier_id: int,
    alert_type: AlertType,
    run_date: date,
    payload: dict,
    user_ids: list[int],
) -> list[Notification]:
    """One in-app Notification per recipient user."""
    rows: list[Notification] = []
    for uid in user_ids:
        rows.append(
            Notification(
                organization_id=organization_id,
                supplier_id=supplier_id,
                recipient_user_id=uid,
                recipient_email=None,
                channel=AlertChannel.IN_APP,
                alert_type=alert_type,
                payload_json=payload,
                run_date=run_date,
                dedup_key=make_dedup_key(
                    supplier_id, alert_type, run_date, AlertChannel.IN_APP, uid
                ),
                status=NotificationStatus.SENT,
            )
        )
    return rows
