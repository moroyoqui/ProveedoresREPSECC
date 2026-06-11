"""Giro catalog endpoints (contracts/catalog-sectors-giros.md)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from repse.auth.dependencies import CurrentUser, current_user, require_role
from repse.db.session import get_db
from repse.giros import service
from repse.giros.schemas import GiroIn, GiroOut, GiroPatch
from repse.users.models import Role

router = APIRouter()


@router.get("", response_model=list[GiroOut])
def list_giros(
    sector_id: int | None = Query(None),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[GiroOut]:
    rows = service.list_all(db, sector_id=sector_id)
    return [GiroOut(id=g.id, sector_id=g.sector_id, sector_name=sn, name=g.name) for g, sn in rows]


@router.post("", response_model=GiroOut, status_code=201)
def create_giro(
    body: GiroIn,
    user: CurrentUser = Depends(require_role(Role.ADMIN.value)),
    db: Session = Depends(get_db),
) -> GiroOut:
    giro, sector_name = service.create(
        db, organization_id=user.organization_id, actor_user_id=user.user_id, body=body
    )
    return GiroOut(id=giro.id, sector_id=giro.sector_id, sector_name=sector_name, name=giro.name)


@router.patch("/{giro_id}", response_model=GiroOut)
def update_giro(
    giro_id: int,
    body: GiroPatch,
    user: CurrentUser = Depends(require_role(Role.ADMIN.value)),
    db: Session = Depends(get_db),
) -> GiroOut:
    giro, sector_name = service.update(
        db, giro_id=giro_id, organization_id=user.organization_id, actor_user_id=user.user_id, body=body
    )
    return GiroOut(id=giro.id, sector_id=giro.sector_id, sector_name=sector_name, name=giro.name)


@router.delete("/{giro_id}", status_code=204)
def delete_giro(
    giro_id: int,
    user: CurrentUser = Depends(require_role(Role.ADMIN.value)),
    db: Session = Depends(get_db),
) -> Response:
    service.delete(db, giro_id=giro_id, organization_id=user.organization_id, actor_user_id=user.user_id)
    return Response(status_code=204)
