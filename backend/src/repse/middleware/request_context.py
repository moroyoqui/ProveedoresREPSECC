"""Bind a request_id, tenant_id and user_id to structlog's contextvars.

Every log line emitted during the request inherits these fields, satisfying
constitution principle IV (observability).
"""

from __future__ import annotations

from uuid import uuid4

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from repse.db.tenant_filter import get_current_tenant

REQUEST_ID_HEADER = "X-Request-ID"


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid4().hex
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
        )
        try:
            response: Response = await call_next(request)
        finally:
            # Late-bound: tenant set by auth dependency during the request.
            if (tenant_id := get_current_tenant()) is not None:
                structlog.contextvars.bind_contextvars(tenant_id=tenant_id)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
