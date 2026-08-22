"""Bloqueos de una celda de cumplimiento (proveedor, tipo, período).

Regla compartida por los dos canales que borran documentos: el portal del
proveedor (spec 013) y el back-office (spec 016). Una celda con un envío
pendiente de validación no admite borrado, porque retirar la evidencia
invalidaría una revisión en curso.

Spec 017: la comprobación de "celda ya validada" desapareció de aquí. Al
unificar validado y verificado, esa condición pasó a ser exactamente la misma
que "documento vigente verificado", que la ruta de borrado ya comprueba por su
cuenta. Mantener las dos era comprobar dos veces lo mismo con códigos de error
distintos.

Vive aquí y no en `documents/service.py` a propósito: la convención del
proyecto (ver docstring de `portal/routes_write.py`) es que la lógica de canal
se invoque desde las rutas, no desde el servicio compartido.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from repse.errors import Conflict
from repse.portal.models import PortalSubmission, SubmissionStatus


def check_cell_unlocked(
    db: Session,
    *,
    organization_id: int,
    supplier_id: int,
    document_type_id: int,
    coverage_period_start: date | None,
) -> None:
    """Raise Conflict if the cell has a submission pending validation."""
    pending = db.execute(
        select(PortalSubmission).where(
            PortalSubmission.organization_id == organization_id,
            PortalSubmission.supplier_id == supplier_id,
            PortalSubmission.document_type_id == document_type_id,
            PortalSubmission.coverage_period_start == coverage_period_start,
            PortalSubmission.status == SubmissionStatus.PENDING,
        )
    ).scalar_one_or_none()
    if pending is not None:
        raise Conflict(
            "Delete not allowed: cell already submitted for validation",
            details={"code": "delete_not_allowed"},
        )

