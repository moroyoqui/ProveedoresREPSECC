"""FastAPI app entrypoint with all Phase 3 routers wired up."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress

# Domain routers (Phase 3).
from fastapi import Depends, FastAPI
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.sessions import SessionMiddleware

from repse.alerts.routes import router as alerts_router
from repse.alerts.scheduler import schedule_daily_alerts
from repse.audit.routes import router as audit_router
from repse.auth.dependencies import require_backoffice
from repse.auth.routes import router as auth_router
from repse.compliance.routes import router as compliance_router
from repse.config import get_settings
from repse.dashboard.routes import router as dashboard_router
from repse.db.session import init_db
from repse.document_types.routes import router as document_types_router
from repse.documents.jobs import schedule_daily_recalculation
from repse.documents.routes import files_router as files_router
from repse.documents.routes import router as documents_router
from repse.errors import register_exception_handlers
from repse.giros.routes import router as giros_router
from repse.logging import configure_logging
from repse.middleware.rate_limit import limiter
from repse.middleware.request_context import RequestContextMiddleware
from repse.observability import metrics as metrics_mod
from repse.observability.sentry import init_sentry
from repse.organizations.routes import router as organizations_router
from repse.portal.routes_read import router as portal_read_router
from repse.portal.routes_write import router as portal_write_router
from repse.sectors.routes import router as sectors_router
from repse.supplier_types.routes import (
    requirements_router as supplier_type_requirements_router,
)
from repse.supplier_types.routes import (
    router as supplier_types_router,
)
from repse.suppliers.routes import router as suppliers_router
from repse.users.routes import router as users_router


@asynccontextmanager
async def lifespan(_app: FastAPI):  # type: ignore[no-untyped-def]
    settings = get_settings()
    configure_logging(level=settings.log_level)
    init_sentry(settings)
    init_db(settings)
    recalc_task: asyncio.Task[None] | None = None
    if settings.documents_recalc_enabled:
        recalc_task = asyncio.create_task(
            schedule_daily_recalculation(hour_utc=settings.documents_recalc_hour_utc)
        )
    alerts_task: asyncio.Task[None] | None = None
    if settings.alerts_scheduler_enabled:
        alerts_task = asyncio.create_task(schedule_daily_alerts())
    try:
        yield
    finally:
        for task in (recalc_task, alerts_task):
            if task is not None:
                task.cancel()
                with suppress(asyncio.CancelledError, Exception):  # pragma: no cover
                    await task


_settings = get_settings()

app = FastAPI(
    title="ProveedoresREPSECC API",
    version="0.1.0",
    docs_url="/api/v1/docs",
    redoc_url=None,
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

# Authlib OIDC stores transient state (oauth_state) in this signed Starlette
# session. Independent from our app cookie.
app.add_middleware(
    SessionMiddleware,
    secret_key=_settings.app_secret.get_secret_value(),
    session_cookie="oidc_state",
    https_only=not _settings.is_local,
    same_site="lax",
)
app.add_middleware(RequestContextMiddleware)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def _rate_limited(_, __):  # type: ignore[no-untyped-def]
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=429,
        content={"error": {"code": "rate_limited", "message": "Too many requests"}},
    )


if _settings.prometheus_enabled:
    metrics_mod.install(app)

register_exception_handlers(app)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


API_PREFIX = "/api/v1"

# Guard de audiencia (spec 013, FR-008): los routers administrativos excluyen
# el rol supplier; los del portal exigen rol supplier vía require_role.
_BACKOFFICE = [Depends(require_backoffice)]

app.include_router(auth_router, prefix=f"{API_PREFIX}/auth", tags=["auth"])
app.include_router(organizations_router, prefix=f"{API_PREFIX}/organization", tags=["organization"], dependencies=_BACKOFFICE)
app.include_router(users_router, prefix=f"{API_PREFIX}/users", tags=["users"], dependencies=_BACKOFFICE)
app.include_router(supplier_types_router, prefix=f"{API_PREFIX}/supplier-types", tags=["supplier-types"], dependencies=_BACKOFFICE)
app.include_router(supplier_type_requirements_router, prefix=f"{API_PREFIX}/supplier-type-requirements", tags=["supplier-type-requirements"], dependencies=_BACKOFFICE)
app.include_router(document_types_router, prefix=f"{API_PREFIX}/document-types", tags=["document-types"], dependencies=_BACKOFFICE)
app.include_router(sectors_router, prefix=f"{API_PREFIX}/sectors", tags=["sectors"], dependencies=_BACKOFFICE)
app.include_router(giros_router, prefix=f"{API_PREFIX}/giros", tags=["giros"], dependencies=_BACKOFFICE)
app.include_router(suppliers_router, prefix=f"{API_PREFIX}/suppliers", tags=["suppliers"], dependencies=_BACKOFFICE)
app.include_router(documents_router, prefix=f"{API_PREFIX}", tags=["documents"], dependencies=_BACKOFFICE)
app.include_router(compliance_router, prefix=f"{API_PREFIX}", tags=["compliance"], dependencies=_BACKOFFICE)
app.include_router(audit_router, prefix=f"{API_PREFIX}/audit-log", tags=["audit-log"], dependencies=_BACKOFFICE)
app.include_router(alerts_router, prefix=f"{API_PREFIX}/alerts", tags=["alerts"], dependencies=_BACKOFFICE)
app.include_router(dashboard_router, prefix=f"{API_PREFIX}/dashboard", tags=["dashboard"], dependencies=_BACKOFFICE)
app.include_router(files_router, prefix=f"{API_PREFIX}", tags=["files"])
app.include_router(portal_read_router, prefix=f"{API_PREFIX}/portal", tags=["portal-read"])
app.include_router(portal_write_router, prefix=f"{API_PREFIX}/portal", tags=["portal-write"])

__all__ = ["app"]
