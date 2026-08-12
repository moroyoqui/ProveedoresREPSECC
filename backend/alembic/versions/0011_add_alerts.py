"""Add compliance alerts tables (spec 002)

Revision ID: 0011_add_alerts
Revises: 0010_drop_sha256_active_index
Create Date: 2026-06-14 00:00:00.000000

Creates four additive TenantOwned tables: alert_config, supplier_alert_recipients,
alert_silences, notifications. Daily idempotency is enforced by the unique
(organization_id, dedup_key) on notifications.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0011_add_alerts"
down_revision: str | None = "0010_drop_sha256_active_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(text("""
        CREATE TABLE alert_config (
            id                      BIGINT NOT NULL AUTO_INCREMENT,
            organization_id         BIGINT NOT NULL,
            expiring_lead_time_days SMALLINT NOT NULL DEFAULT 15,
            default_recipient_emails JSON NOT NULL,
            daily_run_at            TIME NOT NULL DEFAULT '08:00:00',
            enabled                 TINYINT(1) NOT NULL DEFAULT 1,
            last_run_at             DATETIME(6) NULL,
            last_run_status         VARCHAR(16) NULL,
            last_run_summary        JSON NULL,
            created_at              DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            updated_at              DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            PRIMARY KEY (id),
            CONSTRAINT uq_alert_config_organization_id UNIQUE (organization_id),
            CONSTRAINT fk_alert_config_organization_id_organizations
                FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci
    """))

    op.execute(text("""
        CREATE TABLE supplier_alert_recipients (
            id               BIGINT NOT NULL AUTO_INCREMENT,
            organization_id  BIGINT NOT NULL,
            supplier_id      BIGINT NOT NULL,
            recipient_emails JSON NOT NULL,
            created_by       BIGINT NULL,
            created_at       DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            updated_at       DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            PRIMARY KEY (id),
            CONSTRAINT uq_supplier_alert_recipients_supplier UNIQUE (supplier_id),
            INDEX ix_supplier_alert_recipients_organization_id (organization_id),
            CONSTRAINT fk_supplier_alert_recipients_organization_id_organizations
                FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
            CONSTRAINT fk_supplier_alert_recipients_supplier_id_suppliers
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE,
            CONSTRAINT fk_supplier_alert_recipients_created_by_users
                FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci
    """))

    op.execute(text("""
        CREATE TABLE alert_silences (
            id              BIGINT NOT NULL AUTO_INCREMENT,
            organization_id BIGINT NOT NULL,
            document_id     BIGINT NOT NULL,
            silenced_by     BIGINT NOT NULL,
            reason          VARCHAR(500) NOT NULL,
            started_at      DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            ended_at        DATETIME(6) NULL,
            ended_by        BIGINT NULL,
            ended_reason    VARCHAR(20) NULL,
            created_at      DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            updated_at      DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            PRIMARY KEY (id),
            INDEX ix_alert_silences_organization_id (organization_id),
            INDEX ix_alert_silences_active (organization_id, document_id, ended_at),
            CONSTRAINT fk_alert_silences_organization_id_organizations
                FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
            CONSTRAINT fk_alert_silences_document_id_documents
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
            CONSTRAINT fk_alert_silences_silenced_by_users
                FOREIGN KEY (silenced_by) REFERENCES users(id) ON DELETE RESTRICT,
            CONSTRAINT fk_alert_silences_ended_by_users
                FOREIGN KEY (ended_by) REFERENCES users(id) ON DELETE SET NULL
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci
    """))

    op.execute(text("""
        CREATE TABLE notifications (
            id                BIGINT NOT NULL AUTO_INCREMENT,
            organization_id   BIGINT NOT NULL,
            supplier_id       BIGINT NOT NULL,
            recipient_user_id BIGINT NULL,
            recipient_email   VARCHAR(255) NULL,
            channel           VARCHAR(16) NOT NULL,
            alert_type        VARCHAR(16) NOT NULL,
            payload_json      JSON NOT NULL,
            run_date          DATE NOT NULL,
            dedup_key         VARCHAR(255) NOT NULL,
            status            VARCHAR(16) NOT NULL DEFAULT 'pending',
            attempts          SMALLINT NOT NULL DEFAULT 0,
            last_attempted_at DATETIME(6) NULL,
            sent_at           DATETIME(6) NULL,
            error_message     TEXT NULL,
            read_at           DATETIME(6) NULL,
            created_at        DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            updated_at        DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            PRIMARY KEY (id),
            CONSTRAINT uq_notifications_dedup UNIQUE (organization_id, dedup_key),
            INDEX ix_notifications_organization_id (organization_id),
            INDEX ix_notifications_org_status (organization_id, status, created_at),
            INDEX ix_notifications_org_user_unread (organization_id, recipient_user_id, read_at),
            CONSTRAINT fk_notifications_organization_id_organizations
                FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
            CONSTRAINT fk_notifications_supplier_id_suppliers
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE,
            CONSTRAINT fk_notifications_recipient_user_id_users
                FOREIGN KEY (recipient_user_id) REFERENCES users(id) ON DELETE CASCADE
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci
    """))


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("alert_silences")
    op.drop_table("supplier_alert_recipients")
    op.drop_table("alert_config")
