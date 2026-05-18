"""FastAPI app entrypoint.

Wires up logging, error envelope, request-context middleware, rate limiting,
metrics, and Sentry. Domain routers are added in Phase 3 onwards.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from repse.config import get_settings
from repse.db.session import init_db
from repse.errors import RateLimited, register_exception_handlers
from repse.logging import configure_logging
from repse.middleware.rate_limit import limiter
from repse.middleware.request_context import RequestContextMiddleware
from repse.observability import metrics as metrics_mod
from repse.observability.sentry import init_sentry


@asynccontextmanager
async def lifespan(_app: FastAPI):  # type: ignore[no-untyped-def]
    settings = get_settings()
    configure_logging(level=settings.log_level)
    init_sentry(settings)
    init_db(settings)
    yield


app = FastAPI(
    title="ProveedoresREPSECC API",
    version="0.1.0",
    docs_url="/api/v1/docs",
    redoc_url=None,
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

# Middleware order matters: request context first so everything downstream logs
# with request_id; metrics wraps to record latency; rate limit per slowapi.
app.add_middleware(RequestContextMiddleware)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def _rate_limited(_, __):  # type: ignore[no-untyped-def]
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=429,
        content={
            "error": {"code": "rate_limited", "message": "Too many requests"},
        },
    )


# Metrics + observability
if get_settings().prometheus_enabled:
    metrics_mod.install(app)

# Error envelope
register_exception_handlers(app)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    """Liveness probe used by docker-compose and the reverse proxy."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Domain routers (Phase 3+):
#   from repse.auth.routes import router as auth_router
#   app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
#   ... etc.
# ---------------------------------------------------------------------------

# Re-export so tests can simply `from repse.main import app`.
__all__ = ["app"]
