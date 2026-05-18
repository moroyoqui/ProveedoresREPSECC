"""Auth routes: OAuth login, callback, logout, /me.

Provisioning of a tenant happens on the *first* successful callback for an
email domain that does not yet belong to an Organization. For v1 this creates
the Organization + the first admin user automatically; production may want to
require manual approval.
"""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlencode

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware  # noqa: F401  (caller wires it)

from repse.auth.dependencies import CurrentUser, current_user
from repse.auth.oidc import build_oauth
from repse.auth.session import COOKIE_NAME, SessionManager, SessionPayload, fresh_expiry
from repse.config import Settings, get_settings
from repse.db.session import get_db
from repse.db.tenant_filter import with_admin_scope
from repse.errors import Conflict, NotFound, ValidationFailure
from repse.organizations.models import Organization, OrgStatus
from repse.organizations.schemas import OrganizationOut
from repse.supplier_types.provisioning import provision_organization
from repse.users.models import OidcProvider, Role, User, UserStatus

router = APIRouter()


def _oauth(settings: Settings = Depends(get_settings)) -> OAuth:
    return build_oauth(settings)


def _session_mgr(settings: Settings = Depends(get_settings)) -> SessionManager:
    return SessionManager(settings)


@router.get("/login/{provider}")
async def login(
    provider: str,
    request: Request,
    redirect_to: str | None = Query(None),
    oauth: OAuth = Depends(_oauth),
    settings: Settings = Depends(get_settings),
):
    if provider not in {"google", "microsoft"}:
        raise ValidationFailure(f"Unsupported provider '{provider}'")
    client = getattr(oauth, provider, None)
    if client is None:
        raise ValidationFailure(
            f"Provider '{provider}' is not configured (missing OIDC_* env vars)"
        )
    redirect_uri = f"{settings.app_base_url}/api/v1/auth/callback/{provider}"
    if redirect_to:
        request.session["redirect_to"] = redirect_to
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/callback/{provider}")
async def callback(
    provider: str,
    request: Request,
    response: Response,
    oauth: OAuth = Depends(_oauth),
    sessions: SessionManager = Depends(_session_mgr),
    db: Session = Depends(get_db),
):
    if provider not in {"google", "microsoft"}:
        raise ValidationFailure(f"Unsupported provider '{provider}'")
    client = getattr(oauth, provider, None)
    if client is None:
        raise ValidationFailure(f"Provider '{provider}' not configured")
    try:
        token = await client.authorize_access_token(request)
    except OAuthError as exc:
        raise ValidationFailure(f"OAuth error: {exc.error}") from exc

    user_info = token.get("userinfo") or await client.userinfo(token=token)
    email = (user_info.get("email") or "").lower().strip()
    sub = user_info.get("sub") or user_info.get("oid") or ""
    display_name = user_info.get("name") or email
    if not email or not sub:
        raise ValidationFailure("OIDC userinfo missing email or subject")

    # Resolve / create User. With_admin_scope because no tenant context yet.
    with with_admin_scope():
        user = db.execute(
            select(User).where(
                User.oidc_provider == OidcProvider(provider),
                User.oidc_subject == sub,
            )
        ).scalar_one_or_none()

        if user is None:
            # Try matching by email (provisioned beforehand by an admin).
            user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()

        if user is None:
            # First-time visitor: bootstrap an Organization + first admin.
            org = _bootstrap_organization(db, contact_email=email)
            user = User(
                organization_id=org.id,
                email=email,
                oidc_subject=sub,
                oidc_provider=OidcProvider(provider),
                display_name=display_name,
                role=Role.ADMIN,
                status=UserStatus.ACTIVE,
            )
            db.add(user)
            db.flush()
            provision_organization(db, organization_id=org.id)
        else:
            if user.status is UserStatus.DISABLED:
                raise Conflict("User is disabled", details={"code": "user_disabled"})
            # Bind OIDC identifiers on first login through this provider.
            user.oidc_provider = OidcProvider(provider)
            user.oidc_subject = sub
            user.display_name = display_name
            user.last_login_at = datetime.now(timezone.utc)

        db.commit()

        payload = SessionPayload(
            user_id=user.id,
            organization_id=user.organization_id,
            role=user.role.value,
            expires_at=fresh_expiry(),
        )

    redirect_to = request.session.pop("redirect_to", None) or "/"
    redir = RedirectResponse(url=redirect_to, status_code=302)
    sessions.issue(redir, payload)
    return redir


def _bootstrap_organization(db: Session, *, contact_email: str) -> Organization:
    # v1 default: legal_name + RFC are placeholders until the admin updates them.
    org = Organization(
        legal_name=f"Tenant of {contact_email}",
        rfc=f"PROV{datetime.now().strftime('%y%m%d')}AAA",  # placeholder; admin updates it
        contact_email=contact_email,
        status=OrgStatus.ACTIVE,
    )
    db.add(org)
    db.flush()
    return org


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    sessions: SessionManager = Depends(_session_mgr),
):
    sessions.revoke(response)
    response.delete_cookie(COOKIE_NAME, path="/")
    return Response(status_code=204)


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
        "organization": OrganizationOut.model_validate(org).model_dump(),
    }


def _user_email(db: Session, user_id: int) -> str:
    row = db.get(User, user_id)
    return row.email if row else ""


def _user_display(db: Session, user_id: int) -> str:
    row = db.get(User, user_id)
    return row.display_name if row else ""


# Suppress unused-import warning for urlencode (kept for future state-tagging).
_ = urlencode
