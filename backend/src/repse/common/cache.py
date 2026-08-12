"""In-process TTL cache with per-tenant version invalidation (spec 005).

On-prem deployment runs a single backend process (Docker Compose), so an
in-memory cache satisfies the dashboard's 60s freshness requirement (FR-021)
without introducing Redis (constitution IV / YAGNI).

Invalidation uses a per-tenant version counter: the cache key includes
``version[organization_id]``; mutating events (FR-021a) call
``bump_tenant_version`` which makes every prior key for that tenant stale in
O(1), without tracking individual keys.
"""

from __future__ import annotations

import time
from threading import Lock
from typing import Any, Generic, Hashable, TypeVar

T = TypeVar("T")


class TenantVersionedTTLCache(Generic[T]):
    def __init__(self, *, ttl_seconds: float = 60.0) -> None:
        self._ttl = ttl_seconds
        self._store: dict[tuple[Any, ...], tuple[float, T]] = {}
        self._versions: dict[int, int] = {}
        self._lock = Lock()

    def version(self, organization_id: int) -> int:
        return self._versions.get(organization_id, 0)

    def bump(self, organization_id: int) -> None:
        """Invalidate all cached entries for the tenant (FR-021a)."""
        with self._lock:
            self._versions[organization_id] = self._versions.get(organization_id, 0) + 1

    def _key(
        self, organization_id: int, filters_key: Hashable
    ) -> tuple[Any, ...]:
        return (organization_id, self.version(organization_id), filters_key)

    def get(self, organization_id: int, filters_key: Hashable) -> T | None:
        key = self._key(organization_id, filters_key)
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            stored_at, value = entry
            if time.monotonic() - stored_at > self._ttl:
                self._store.pop(key, None)
                return None
            return value

    def set(self, organization_id: int, filters_key: Hashable, value: T) -> None:
        key = self._key(organization_id, filters_key)
        with self._lock:
            self._store[key] = (time.monotonic(), value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._versions.clear()


# Shared dashboard cache instance + tenant-version bump used by mutation points.
dashboard_cache: TenantVersionedTTLCache[Any] = TenantVersionedTTLCache(ttl_seconds=60.0)


def bump_tenant_version(organization_id: int) -> None:
    """Invalidate the tenant's dashboard cache (call on FR-021a events)."""
    dashboard_cache.bump(organization_id)
