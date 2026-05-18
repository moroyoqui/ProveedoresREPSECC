"""Prometheus metrics exposed at /metrics (research.md §7 spec 001)."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

REQUEST_COUNT = Counter(
    "repse_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

REQUEST_LATENCY = Histogram(
    "repse_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        path = request.url.path
        method = request.method
        with REQUEST_LATENCY.labels(method=method, path=path).time():
            response: Response = await call_next(request)
        REQUEST_COUNT.labels(method=method, path=path, status=str(response.status_code)).inc()
        return response


router = APIRouter()


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def install(app: FastAPI) -> None:
    app.add_middleware(PrometheusMiddleware)
    app.include_router(router)
