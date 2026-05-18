"""slowapi-backed rate limiting (research.md §8 spec 001).

In-memory storage is fine for a single instance (default deployment).
Multi-replica deployments switch the storage_uri to redis://... later.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=[])


def auth_limit() -> str:
    return "10/minute"


def upload_limit() -> str:
    return "60/minute"
