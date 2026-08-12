"""Seed default AlertConfig for pre-existing organizations (spec 002)

Revision ID: 0012_seed_alert_config
Revises: 0011_add_alerts
Create Date: 2026-06-14 00:00:01.000000

Data migration: inserts a default AlertConfig (lead time 15 days, 08:00 local,
enabled, recipients = [organization.contact_email]) for every organization that
does not yet have one. New organizations get theirs at provisioning time
(supplier_types/provisioning.py). The downgrade is a no-op: the alert_config
table is dropped by 0011's downgrade if the schema is rolled back.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0012_seed_alert_config"
down_revision: str | None = "0011_add_alerts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(text("""
        INSERT INTO alert_config
            (organization_id, expiring_lead_time_days, default_recipient_emails,
             daily_run_at, enabled, created_at, updated_at)
        SELECT o.id, 15, JSON_ARRAY(o.contact_email), '08:00:00', 1,
               CURRENT_TIMESTAMP(6), CURRENT_TIMESTAMP(6)
        FROM organizations o
        WHERE NOT EXISTS (
            SELECT 1 FROM alert_config c WHERE c.organization_id = o.id
        )
    """))


def downgrade() -> None:
    # No-op: schema rollback (0011 downgrade) drops alert_config entirely.
    pass
