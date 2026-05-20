"""Document status recalculator (T092 spec 001).

Materializa ``Document.status`` para todos los documentos ``is_latest=True`` de
una organización, aplicando ``status_calculator.compute_status`` con el
``expiring_soon_threshold_days`` actual de la org.

Idempotente: sólo escribe filas que cambiaron de estado. Invocaciones:

  (a) cron diario (``jobs.run_daily_recalculation``).
  (b) cambio del threshold de la org (FR-013).
  (c) cambio de ``supplier_type_id`` de un proveedor (FR-005a/b/c) — opcional;
      la materialización se puede recomputar de forma lazy también.
  (d) edición de requirements del SupplierType (FR-012b).
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from repse.audit.service import write_system_event
from repse.documents.models import Document
from repse.documents.status import compute_status
from repse.organizations.models import Organization

logger = logging.getLogger(__name__)


def recalc_for_organization(
    db: Session,
    *,
    organization_id: int,
    today: date | None = None,
    audit: bool = False,
) -> int:
    """Recalcula ``status`` para todos los documentos latest del tenant.

    Devuelve la cantidad de filas cuyo ``status`` cambió.

    El filtro multi-tenant se aplica vía ``current_tenant`` del ``do_orm_execute``
    listener; el caller debe haber hecho ``set_current_tenant(org_id)`` o estar
    en ``with_admin_scope()`` (cron). Para evitar contención con el contexto
    actual, leemos la org con ``with_admin_scope`` interno aquí.
    """
    from repse.db.tenant_filter import set_current_tenant, with_admin_scope

    if today is None:
        today = datetime.now(timezone.utc).date()

    with with_admin_scope():
        org = db.get(Organization, organization_id)
    if org is None:
        return 0
    threshold = int(org.expiring_soon_threshold_days)

    set_current_tenant(organization_id)
    docs = (
        db.execute(
            select(Document).where(Document.is_latest.is_(True))
        )
        .scalars()
        .all()
    )

    changed = 0
    for doc in docs:
        new_status = compute_status(
            doc, today=today, expiring_soon_threshold_days=threshold
        )
        if doc.status != new_status:
            doc.status = new_status
            changed += 1

    if changed:
        db.flush()
        if audit:
            write_system_event(
                db,
                organization_id=organization_id,
                action="documents.status_recalculated",
                entity_type="organization",
                entity_id=organization_id,
                metadata={"changed": changed, "today": today.isoformat()},
            )
        db.commit()
        logger.info(
            "documents.status_recalculated",
            extra={"organization_id": organization_id, "changed": changed},
        )

    return changed
