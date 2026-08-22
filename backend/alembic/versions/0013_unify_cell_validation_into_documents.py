"""Unify cell validation into document verification (spec 017)

Revision ID: 0013_unify_cell_validation
Revises: 0012_seed_alert_config
Create Date: 2026-08-21 00:00:00.000000

Data migration. Hasta ahora convivían dos marcas de revisión que podían
contradecirse: `documents.verified` y la tabla `compliance_cell_validations`.
El documento pasa a ser la única fuente de verdad, así que el contenido
aprovechable de la tabla se traslada al documento vigente de cada celda.

Reglas (ver specs/017-unify-verification/data-model.md):

  * Celda con documento vigente sin verificar → se marca verificado
    conservando `validated_by` y `validated_at` originales.
  * Celda con documento vigente ya verificado → no se pisa: la autoría del
    documento es la buena.
  * Celda SIN documento vigente → se descarta, dejando constancia en el log.
    Validar una celda vacía era posible porque la ruta nunca exigió evidencia;
    a partir de spec 017 se rechaza (FR-005), y esas marcas no tienen dónde
    vivir en el modelo nuevo.

La tabla NO se elimina: queda inerte, sin lectores ni escritores, como red de
seguridad. Su retirada definitiva es una migración posterior.
"""
from __future__ import annotations

import logging
from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0013_unify_cell_validation"
down_revision: str | None = "0012_seed_alert_config"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

logger = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    conn = op.get_bind()

    # Se itera por organización para que el traslado no cruce tenants ni
    # dependa de que los ids de proveedor sean únicos entre organizaciones.
    org_ids = [
        row[0]
        for row in conn.execute(
            text("SELECT DISTINCT organization_id FROM compliance_cell_validations")
        )
    ]

    total_migradas = 0
    total_descartadas = 0

    for org_id in org_ids:
        # 1. Constancia de lo que se va a descartar, ANTES de tocar nada.
        huerfanas = conn.execute(
            text("""
                SELECT v.id, v.supplier_id, v.document_type_id,
                       v.coverage_period_start, v.validated_at
                FROM compliance_cell_validations v
                LEFT JOIN documents d
                       ON d.organization_id = v.organization_id
                      AND d.supplier_id = v.supplier_id
                      AND d.document_type_id = v.document_type_id
                      AND (d.coverage_period_start <=> v.coverage_period_start)
                      AND d.is_latest = 1
                      AND d.deleted_at IS NULL
                WHERE v.organization_id = :org_id
                  AND d.id IS NULL
            """),
            {"org_id": org_id},
        ).fetchall()

        for row in huerfanas:
            logger.warning(
                "spec-017: se descarta la validación %s (org=%s, proveedor=%s, tipo=%s, "
                "período=%s, validada el %s): la celda no tiene documento vigente que "
                "respalde la marca",
                row[0], org_id, row[1], row[2], row[3], row[4],
            )
        total_descartadas += len(huerfanas)

        # 2. Traslado al documento vigente, sin pisar los ya verificados.
        result = conn.execute(
            text("""
                UPDATE documents d
                JOIN compliance_cell_validations v
                     ON d.organization_id = v.organization_id
                    AND d.supplier_id = v.supplier_id
                    AND d.document_type_id = v.document_type_id
                    AND (d.coverage_period_start <=> v.coverage_period_start)
                SET d.verified = 1,
                    d.verified_by = v.validated_by,
                    d.verified_at = v.validated_at
                WHERE v.organization_id = :org_id
                  AND d.is_latest = 1
                  AND d.deleted_at IS NULL
                  AND d.verified = 0
            """),
            {"org_id": org_id},
        )
        total_migradas += result.rowcount or 0

    logger.warning(
        "spec-017: unificación completada — %s validaciones trasladadas al documento, "
        "%s descartadas por no tener documento vigente. La tabla "
        "compliance_cell_validations queda inerte (sin lectores ni escritores).",
        total_migradas, total_descartadas,
    )


def downgrade() -> None:
    """Reconstruye las filas de validación a partir de los documentos verificados.

    No es una inversa exacta: las marcas descartadas en el upgrade (celdas sin
    documento) no se pueden recuperar desde los documentos, y las que ya estaban
    verificadas antes de la migración generarán una fila que no existía. Se deja
    porque devuelve el sistema a un estado funcional, no idéntico.
    """
    op.execute(text("""
        INSERT INTO compliance_cell_validations
            (organization_id, supplier_id, document_type_id, coverage_period_start,
             validated_by, validated_at, created_at, updated_at)
        SELECT d.organization_id, d.supplier_id, d.document_type_id,
               d.coverage_period_start, d.verified_by, d.verified_at,
               NOW(), NOW()
        FROM documents d
        LEFT JOIN compliance_cell_validations v
               ON d.organization_id = v.organization_id
              AND d.supplier_id = v.supplier_id
              AND d.document_type_id = v.document_type_id
              AND (d.coverage_period_start <=> v.coverage_period_start)
        WHERE d.verified = 1
          AND d.deleted_at IS NULL
          AND d.is_latest = 1
          AND d.verified_at IS NOT NULL
          AND v.id IS NULL
    """))
