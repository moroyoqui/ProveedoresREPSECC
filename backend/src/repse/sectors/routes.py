"""Sector catalog endpoints (contracts/catalog-sectors-giros.md)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from repse.auth.dependencies import CurrentUser, current_user, require_role
from repse.db.session import get_db
from repse.sectors import service
from repse.sectors.schemas import SectorIn, SectorOut
from repse.users.models import Role

router = APIRouter()


@router.get("", response_model=list[SectorOut])
def list_sectors(
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[SectorOut]:
    sectors = service.list_all(db)
    return [SectorOut(id=s.id, name=s.name) for s in sectors]


@router.post("", response_model=SectorOut, status_code=201)
def create_sector(
    body: SectorIn,
    user: CurrentUser = Depends(require_role(Role.ADMIN.value)),
    db: Session = Depends(get_db),
) -> SectorOut:
    sector = service.create(db, organization_id=user.organization_id, actor_user_id=user.user_id, body=body)
    return SectorOut(id=sector.id, name=sector.name)


@router.patch("/{sector_id}", response_model=SectorOut)
def update_sector(
    sector_id: int,
    body: SectorIn,
    user: CurrentUser = Depends(require_role(Role.ADMIN.value)),
    db: Session = Depends(get_db),
) -> SectorOut:
    sector = service.update(
        db, sector_id=sector_id, organization_id=user.organization_id, actor_user_id=user.user_id, body=body
    )
    return SectorOut(id=sector.id, name=sector.name)


@router.delete("/{sector_id}", status_code=204)
def delete_sector(
    sector_id: int,
    user: CurrentUser = Depends(require_role(Role.ADMIN.value)),
    db: Session = Depends(get_db),
) -> Response:
    service.delete(db, sector_id=sector_id, organization_id=user.organization_id, actor_user_id=user.user_id)
    return Response(status_code=204)
