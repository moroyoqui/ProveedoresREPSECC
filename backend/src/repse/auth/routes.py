"""Auth routes: login local (email + contraseña), logout, /me.

Las altas de organización y de usuarios son siempre explícitas: por el script
``scripts/create_admin.py`` para el primer tenant y por el CRUD de usuarios
después. No hay auto-provisión al iniciar sesión.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from repse.auth.dependencies import CurrentUser, current_user
from repse.auth.passwords import verify_password
from repse.auth.session import COOKIE_NAME, SessionManager, SessionPayload, fresh_expiry
from repse.config import Settings, get_settings
from repse.db.session import get_db
from repse.db.tenant_filter import with_admin_scope
from repse.errors import Conflict, NotFound, ValidationFailure
from repse.organizations.models import Organization
from repse.organizations.schemas import OrganizationOut
from repse.users.models import Role, User, UserStatus

router = APIRouter()


def _session_mgr(settings: Settings = Depends(get_settings)) -> SessionManager:
    return SessionManager(settings)


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    # Puerta de entrada (spec 013, FR-013): "backoffice" (default) o "portal".
    audience: Literal["backoffice", "portal"] = "backoffice"


@router.post("/login")
def login_local(
    body: LoginIn,
    response: Response,
    sessions: SessionManager = Depends(_session_mgr),
    db: Session = Depends(get_db),
) -> dict:
    """Email + password login against the local users table (FR-002 spec 001).

    Multi-tenant lookup:
    the (organization_id, email) combo is unique, but a given email may exist
    only in ONE organization per current model — fail closed if multiple
    matches.
    """
    email = body.email.lower().strip()
    with with_admin_scope():
        candidates = db.execute(
            select(User).where(User.email == email, User.status == UserStatus.ACTIVE)
        ).scalars().all()
    if len(candidates) == 0:
        raise ValidationFailure(
            "Invalid email or password", details={"code": "invalid_credentials"}
        )
    if len(candidates) > 1:
        # Should not happen with current schema (a user belongs to one org) but
        # be defensive: refuse to guess.
        raise Conflict(
            "Email is registered in more than one tenant; contact your admin.",
            details={"code": "ambiguous_user"},
        )
    user = candidates[0]
    if not verify_password(body.password, user.password_hash):
        raise ValidationFailure(
            "Invalid email or password", details={"code": "invalid_credentials"}
        )

    # Gating por audiencia (spec 013, FR-013): la respuesta del mismatch debe
    # ser idéntica a la de credenciales inválidas para no revelar su validez.
    is_supplier = user.role == Role.SUPPLIER
    if (body.audience == "portal") != is_supplier:
        raise ValidationFailure(
            "Invalid email or password", details={"code": "invalid_credentials"}
        )

    with with_admin_scope():
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()

    payload = SessionPayload(
        user_id=user.id,
        organization_id=user.organization_id,
        role=user.role.value,
        expires_at=fresh_expiry(),
        supplier_id=user.supplier_id,
    )
    sessions.issue(response, payload)
    return {"status": "ok", "user_id": user.id, "organization_id": user.organization_id}


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    sessions: SessionManager = Depends(_session_mgr),
):
    # Returning a fresh Response would discard the cookie headers set on the
    # injected `response`; build the final response and attach deletion to it.
    final = Response(status_code=204)
    sessions.revoke(final)
    final.delete_cookie(COOKIE_NAME, path="/")
    return final


@router.get("/me")
def me(user: CurrentUser = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    org = db.get(Organization, user.organization_id)
    if org is None:
        raise NotFound("Organization not found")
    return {
        "id": user.user_id,
        "email": _user_email(db, user.user_id),
        "display_name": _user_display(db, user.user_id),
        "role": user.role,
        "supplier_id": user.supplier_id,
        "organization": OrganizationOut.model_validate(org).model_dump(),
    }


def _user_email(db: Session, user_id: int) -> str:
    row = db.get(User, user_id)
    return row.email if row else ""


def _user_display(db: Session, user_id: int) -> str:
    row = db.get(User, user_id)
    return row.display_name if row else ""

