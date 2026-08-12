"""Organization routes (contracts/organizations.md)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from repse.auth.dependencies import CurrentUser, current_user, require_role
from repse.common.cache import bump_tenant_version
from repse.db.session import get_db
from repse.errors import NotFound
from repse.organizations.models import Organization
from repse.organizations.schemas import OrganizationOut, OrganizationPatch
from repse.users.models import Role

router = APIRouter()


@router.get("", response_model=OrganizationOut)
def get_organization(
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> Organization:
    org = db.get(Organization, user.organization_id)
    if org is None:
        raise NotFound("Organization not found")
    return org


@router.patch("", response_model=OrganizationOut)
def update_organization(
    body: OrganizationPatch,
    user: CurrentUser = Depends(require_role(Role.ADMIN.value)),
    db: Session = Depends(get_db),
) -> Organization:
    org = db.get(Organization, user.organization_id)
    if org is None:
        raise NotFound("Organization not found")
    if body.legal_name is not None:
        org.legal_name = body.legal_name
    if body.contact_email is not None:
        org.contact_email = body.contact_email
    if body.expiring_soon_threshold_days is not None:
        org.expiring_soon_threshold_days = body.expiring_soon_threshold_days
    if body.timezone is not None:
        org.timezone = body.timezone
    db.commit()
    bump_tenant_version(user.organization_id)  # FR-021a: invalida cache del tablero
    db.refresh(org)
    return org
