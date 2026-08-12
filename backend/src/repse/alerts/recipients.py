"""Recipient resolution (T013).

Email recipients: per-supplier override beats the org default (FR-008).
In-app recipients: active back-office users of the tenant (admin/manager/viewer).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from repse.alerts.models import AlertConfig, SupplierAlertRecipientOverride
from repse.users.models import Role, User, UserStatus

_BACKOFFICE_ROLES = (Role.ADMIN, Role.MANAGER, Role.VIEWER)


def resolve_recipients(
    db: Session, organization_id: int, supplier_id: int, config: AlertConfig
) -> list[str]:
    """Email recipients for a supplier's alerts: override or org default."""
    override = db.execute(
        select(SupplierAlertRecipientOverride).where(
            SupplierAlertRecipientOverride.organization_id == organization_id,
            SupplierAlertRecipientOverride.supplier_id == supplier_id,
        )
    ).scalar_one_or_none()
    if override is not None and override.recipient_emails:
        return list(override.recipient_emails)
    return list(config.default_recipient_emails)


def inapp_recipient_user_ids(db: Session, organization_id: int) -> list[int]:
    """Active back-office users that receive the in-app notification center entries."""
    return list(
        db.execute(
            select(User.id).where(
                User.organization_id == organization_id,
                User.role.in_(_BACKOFFICE_ROLES),
                User.status == UserStatus.ACTIVE,
            )
        ).scalars()
    )
