"""Add sectors and giros global catalogs; extend suppliers with classification columns

Revision ID: 0007_add_sectors_giros
Revises: 0006_add_portal_submissions
Create Date: 2026-06-08 00:00:00.000000

Creates global reference tables `sectors` and `giros` (no organization_id —
see research.md Decisión 1) and extends `suppliers` with optional nullable
FK columns `sector_id` and `giro_id` for supplier classification.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision: str = "0007_add_sectors_giros"
down_revision: str | None = "0006_add_portal_submissions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(text("""
        CREATE TABLE sectors (
            id    BIGINT NOT NULL AUTO_INCREMENT,
            name  VARCHAR(120) NOT NULL,
            created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            PRIMARY KEY (id),
            CONSTRAINT uq_sectors_name UNIQUE (name)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci
    """))

    op.execute(text("""
        CREATE TABLE giros (
            id        BIGINT NOT NULL AUTO_INCREMENT,
            sector_id BIGINT NOT NULL,
            name      VARCHAR(120) NOT NULL,
            created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            PRIMARY KEY (id),
            CONSTRAINT uq_giros_sector_name UNIQUE (sector_id, name),
            INDEX ix_giros_sector_id (sector_id),
            CONSTRAINT fk_giros_sector_id_sectors
                FOREIGN KEY (sector_id) REFERENCES sectors(id) ON DELETE RESTRICT
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci
    """))

    op.execute(text("""
        ALTER TABLE suppliers
            ADD COLUMN sector_id BIGINT NULL DEFAULT NULL AFTER supplier_type_id,
            ADD COLUMN giro_id   BIGINT NULL DEFAULT NULL AFTER sector_id,
            ADD INDEX  ix_suppliers_sector_id (sector_id),
            ADD INDEX  ix_suppliers_giro_id   (giro_id),
            ADD CONSTRAINT fk_suppliers_sector_id_sectors
                FOREIGN KEY (sector_id) REFERENCES sectors(id) ON DELETE RESTRICT,
            ADD CONSTRAINT fk_suppliers_giro_id_giros
                FOREIGN KEY (giro_id) REFERENCES giros(id) ON DELETE RESTRICT
    """))


def downgrade() -> None:
    op.execute(text("""
        ALTER TABLE suppliers
            DROP FOREIGN KEY fk_suppliers_giro_id_giros,
            DROP FOREIGN KEY fk_suppliers_sector_id_sectors,
            DROP INDEX ix_suppliers_giro_id,
            DROP INDEX ix_suppliers_sector_id,
            DROP COLUMN giro_id,
            DROP COLUMN sector_id
    """))
    op.drop_table("giros")
    op.drop_table("sectors")
