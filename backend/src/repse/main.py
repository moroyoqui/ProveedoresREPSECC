"""FastAPI app entrypoint.

The full lifespan (DB engine, scheduler, OIDC clients, observability) is wired
up in Phase 2. For Phase 1 this is intentionally minimal: just enough to verify
that the container boots and the reverse proxy is reachable.
"""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(
    title="ProveedoresREPSECC API",
    version="0.1.0",
    docs_url="/api/v1/docs",
    redoc_url=None,
    openapi_url="/api/v1/openapi.json",
)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    """Liveness probe consumed by docker-compose healthcheck and ops."""
    return {"status": "ok"}
