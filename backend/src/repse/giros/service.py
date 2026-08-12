"""Giro catalog service — CRUD with dependency guards."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from repse.audit.service import AuditEvent, write_event
from repse.errors import Conflict, NotFound
from repse.giros.models import Giro
from repse.giros.schemas import GiroIn, GiroPatch
from repse.sectors.models import Sector

_GIRO_CREATED = "giro.created"
_GIRO_UPDATED = "giro.updated"
_GIRO_DELETED = "giro.deleted"


def list_all(db: Session, *, sector_id: int | None = None) -> list[tuple[Giro, str]]:
    """Returns list of (Giro, sector_name) tuples, ordered by sector name then giro name."""
    stmt = (
        select(Giro, Sector.name.label("sector_name"))
        .join(Sector, Sector.id == Giro.sector_id)
        .order_by(Sector.name, Giro.name)
    )
    if sector_id is not None:
        stmt = stmt.where(Giro.sector_id == sector_id)
    return list(db.execute(stmt).all())


def create(db: Session, *, organization_id: int, actor_user_id: int, body: GiroIn) -> tuple[Giro, str]:
    sector = db.get(Sector, body.sector_id)
    if sector is None:
        raise NotFound("Sector not found")
    _assert_name_available(db, sector_id=body.sector_id, name=body.name, exclude_id=None)
    giro = Giro(sector_id=body.sector_id, name=body.name.strip())
    db.add(giro)
    db.flush()
    write_event(
        db,
        AuditEvent(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=_GIRO_CREATED,
            entity_type="giro",
            entity_id=giro.id,
            metadata={"name": giro.name, "sector_id": giro.sector_id},
        ),
    )
    db.commit()
    db.refresh(giro)
    db.refresh(sector)
    return giro, sector.name


def update(
    db: Session, *, giro_id: int, organization_id: int, actor_user_id: int, body: GiroPatch
) -> tuple[Giro, str]:
    giro = _get_or_404(db, giro_id)
    target_sector_id = body.sector_id if body.sector_id is not None else giro.sector_id

    if body.sector_id is not None and body.sector_id != giro.sector_id:
        sector = db.get(Sector, body.sector_id)
        if sector is None:
            raise NotFound("Sector not found")

    target_name = body.name.strip() if body.name is not None else giro.name
    _assert_name_available(db, sector_id=target_sector_id, name=target_name, exclude_id=giro_id)

    before = {"name": giro.name, "sector_id": giro.sector_id}
    if body.sector_id is not None:
        giro.sector_id = body.sector_id
    if body.name is not None:
        giro.name = body.name.strip()

    write_event(
        db,
        AuditEvent(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=_GIRO_UPDATED,
            entity_type="giro",
            entity_id=giro.id,
            metadata={"before": before, "after": {"name": giro.name, "sector_id": giro.sector_id}},
        ),
    )
    db.commit()
    db.refresh(giro)
    sector = db.get(Sector, giro.sector_id)
    return giro, sector.name  # type: ignore[union-attr]


def delete(db: Session, *, giro_id: int, organization_id: int, actor_user_id: int) -> None:
    giro = _get_or_404(db, giro_id)
    _assert_no_supplier_deps(db, giro_id)
    write_event(
        db,
        AuditEvent(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=_GIRO_DELETED,
            entity_type="giro",
            entity_id=giro_id,
            metadata={"name": giro.name, "sector_id": giro.sector_id},
        ),
    )
    db.delete(giro)
    db.commit()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_or_404(db: Session, giro_id: int) -> Giro:
    giro = db.get(Giro, giro_id)
    if giro is None:
        raise NotFound("Giro not found")
    return giro


def _assert_name_available(
    db: Session, *, sector_id: int, name: str, exclude_id: int | None
) -> None:
    stmt = select(Giro).where(
        Giro.sector_id == sector_id,
        func.lower(Giro.name) == func.lower(name.strip()),
    )
    if exclude_id is not None:
        stmt = stmt.where(Giro.id != exclude_id)
    existing = db.execute(stmt).scalar_one_or_none()
    if existing is not None:
        raise Conflict(
            "Ya existe un giro con ese nombre en este sector.",
            details={"code": "giro_name_taken"},
        )


def _assert_no_supplier_deps(db: Session, giro_id: int) -> None:
    from repse.suppliers.models import Supplier  # local import to avoid circular
    count = db.execute(
        select(func.count()).select_from(Supplier).where(Supplier.giro_id == giro_id)
    ).scalar_one()
    if count > 0:
        raise Conflict(
            f"No se puede eliminar: el giro está asignado a {count} proveedor(es).",
            details={"code": "giro_in_use", "supplier_count": count},
        )
