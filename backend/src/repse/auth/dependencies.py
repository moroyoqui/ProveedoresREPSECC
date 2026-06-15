"""FastAPI dependencies that resolve current_user / current_tenant / require_role.

These power every protected endpoint. `current_user` validates the session
cookie and propagates the tenant into the `TenantOwned` filter context.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import structlog
from fastapi import Depends, Request

from repse.auth.session import SessionManager, SessionPayload
from repse.config import Settings, get_settings
from repse.db.tenant_filter import set_current_tenant
from repse.errors import Forbidden, Unauthenticated


@dataclass(frozen=True)
class CurrentUser:
    user_id: int
    organization_id: int
    role: str
    supplier_id: int | None = None


def _session_manager(settings: Settings = Depends(get_settings)) -> SessionManager:
    return SessionManager(settings)


async def current_user(
    request: Request,
    sessions: SessionManager = Depends(_session_manager),
) -> CurrentUser:
    # Async on purpose: set_current_tenant() must run in the request task's
    # context so the tenant contextvar propagates to sync dependencies and
    # handlers (threadpool runs receive a COPY of the context; a set made
    # inside a sync dependency would be lost for the handler).
    payload: SessionPayload | None = sessions.read(request)
    if payload is None:
        raise Unauthenticated("Missing or invalid session")
    set_current_tenant(payload.organization_id)
    structlog.contextvars.bind_contextvars(
        user_id=payload.user_id,
        tenant_id=payload.organization_id,
        role=payload.role,
    )
    return CurrentUser(
        user_id=payload.user_id,
        organization_id=payload.organization_id,
        role=payload.role,
        supplier_id=payload.supplier_id,
    )


def current_tenant(user: CurrentUser = Depends(current_user)) -> int:
    return user.organization_id


async def require_backoffice(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    """Guard de routers administrativos (spec 013, FR-008): cualquier rol
    autenticado excepto supplier; los proveedores solo acceden a /portal."""
    if user.role == "supplier":
        raise Forbidden("Role 'supplier' not allowed on back-office endpoints")
    return user


def require_role(*roles: str):  # type: ignore[no-untyped-def]
    allowed = set(roles)

    def _check(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        if user.role not in allowed:
            raise Forbidden(f"Role '{user.role}' not allowed; expected one of {sorted(allowed)}")
        return user

    return _check


def require_any_role(roles: Iterable[str]):  # type: ignore[no-untyped-def]
    return require_role(*roles)
