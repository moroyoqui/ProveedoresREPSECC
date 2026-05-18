"""FastAPI app entrypoint with all Phase 3 routers wired up."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.sessions import SessionMiddleware

from repse.config import get_settings
from repse.db.session import init_db
from repse.errors import register_exception_handlers
from repse.logging import configure_logging
from repse.middleware.rate_limit import limiter
from repse.middleware.request_context import RequestContextMiddleware
from repse.observability import metrics as metrics_mod
from repse.observability.sentry import init_sentry

# Domain routers (Phase 3).
from repse.auth.routes import router as auth_router
from repse.compliance.routes import router as compliance_router
from repse.documents.routes import router as documents_router
from repse.document_types.routes import router as document_types_router
from repse.organizations.routes import router as organizations_router
from repse.suppliers.routes import router as suppliers_router
from repse.supplier_types.routes import (
    requirements_router as supplier_type_requirements_router,
    router as supplier_types_router,
)
from repse.users.routes import router as users_router


@asynccontextmanager
async def lifespan(_app: FastAPI):  # type: ignore[no-untyped-def]
    settings = get_settings()
    configure_logging(level=settings.log_level)
    init_sentry(settings)
    init_db(settings)
    yield


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

app.include_router(auth_router, prefix=f"{API_PREFIX}/auth", tags=["auth"])
app.include_router(organizations_router, prefix=f"{API_PREFIX}/organization", tags=["organization"])
app.include_router(users_router, prefix=f"{API_PREFIX}/users", tags=["users"])
app.include_router(supplier_types_router, prefix=f"{API_PREFIX}/supplier-types", tags=["supplier-types"])
app.include_router(supplier_type_requirements_router, prefix=f"{API_PREFIX}/supplier-type-requirements", tags=["supplier-type-requirements"])
app.include_router(document_types_router, prefix=f"{API_PREFIX}/document-types", tags=["document-types"])
app.include_router(suppliers_router, prefix=f"{API_PREFIX}/suppliers", tags=["suppliers"])
app.include_router(documents_router, prefix=f"{API_PREFIX}", tags=["documents"])
app.include_router(compliance_router, prefix=f"{API_PREFIX}", tags=["compliance"])

__all__ = ["app"]
