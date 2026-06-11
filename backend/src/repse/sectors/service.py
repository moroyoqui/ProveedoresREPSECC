"""Sector catalog service — CRUD with dependency guards."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from repse.audit.service import AuditEvent, write_event
from repse.errors import Conflict, NotFound
from repse.sectors.models import Sector
from repse.sectors.schemas import SectorIn

_SECTOR_CREATED = "sector.created"
_SECTOR_UPDATED = "sector.updated"
_SECTOR_DELETED = "sector.deleted"


def list_all(db: Session) -> list[Sector]:
    return list(db.execute(select(Sector).order_by(Sector.name)).scalars().all())


def create(db: Session, *, organization_id: int, actor_user_id: int, body: SectorIn) -> Sector:
    _assert_name_available(db, name=body.name, exclude_id=None)
    sector = Sector(name=body.name.strip())
    db.add(sector)
    db.flush()
    write_event(
        db,
        AuditEvent(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=_SECTOR_CREATED,
            entity_type="sector",
            entity_id=sector.id,
            metadata={"name": sector.name},
        ),
    )
    db.commit()
    db.refresh(sector)
    return sector


def update(
    db: Session, *, sector_id: int, organization_id: int, actor_user_id: int, body: SectorIn
) -> Sector:
    sector = _get_or_404(db, sector_id)
    _assert_name_available(db, name=body.name, exclude_id=sector_id)
    before = sector.name
    sector.name = body.name.strip()
    write_event(
        db,
        AuditEvent(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=_SECTOR_UPDATED,
            entity_type="sector",
            entity_id=sector.id,
            metadata={"before": before, "after": sector.name},
        ),
    )
    db.commit()
    db.refresh(sector)
    return sector


def delete(db: Session, *, sector_id: int, organization_id: int, actor_user_id: int) -> None:
    sector = _get_or_404(db, sector_id)
    _assert_no_giro_deps(db, sector_id)
    _assert_no_supplier_deps(db, sector_id)
    write_event(
        db,
        AuditEvent(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=_SECTOR_DELETED,
            entity_type="sector",
            entity_id=sector_id,
            metadata={"name": sector.name},
        ),
    )
    db.delete(sector)
    db.commit()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_or_404(db: Session, sector_id: int) -> Sector:
    sector = db.get(Sector, sector_id)
    if sector is None:
        raise NotFound("Sector not found")
    return sector


def _assert_name_available(db: Session, *, name: str, exclude_id: int | None) -> None:
    stmt = select(Sector).where(func.lower(Sector.name) == func.lower(name.strip()))
    if exclude_id is not None:
        stmt = stmt.where(Sector.id != exclude_id)
    existing = db.execute(stmt).scalar_one_or_none()
    if existing is not None:
        raise Conflict(
            "Ya existe un sector con ese nombre.",
            details={"code": "sector_name_taken"},
        )


def _assert_no_giro_deps(db: Session, sector_id: int) -> None:
    from repse.giros.models import Giro  # local import to avoid circular
    count = db.execute(
        select(func.count()).select_from(Giro).where(Giro.sector_id == sector_id)
    ).scalar_one()
    if count > 0:
        raise Conflict(
            f"No se puede eliminar: el sector tiene {count} giro(s) asociado(s).",
            details={"code": "sector_has_dependencies", "giro_count": count},
        )


def _assert_no_supplier_deps(db: Session, sector_id: int) -> None:
    from repse.suppliers.models import Supplier  # local import to avoid circular
    count = db.execute(
        select(func.count()).select_from(Supplier).where(Supplier.sector_id == sector_id)
    ).scalar_one()
    if count > 0:
        raise Conflict(
            f"No se puede eliminar: el sector está asignado a {count} proveedor(es).",
            details={"code": "sector_in_use", "supplier_count": count},
        )
