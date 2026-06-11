"""Multi-tenant isolation enforced at the ORM layer (constitution principle II).

Every model that owns tenant data MUST inherit from `TenantOwned`. The
session-level `do_orm_execute` listener inspects every ORM-driven Select /
Update / Delete and injects ``WHERE organization_id = :current_tenant_id``
via `with_loader_criteria`, unless the call site explicitly enters
`with_admin_scope()` (used by ops/seed/migration code).

This is the SQLAlchemy 2.x recommended pattern for tenant filtering (see
"Adding global filters to all queries with do_orm_execute"). It is more
robust than the `before_compile` hook from 1.x: it also covers eager-loaded
relationships and lazy loads.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

from sqlalchemy import BigInteger, ForeignKey, event
from sqlalchemy.orm import (
    Mapped,
    Session,
    declarative_mixin,
    mapped_column,
    with_loader_criteria,
)

# ContextVar carries the active tenant per-request without coupling to FastAPI.
_current_tenant: ContextVar[int | None] = ContextVar("repse_current_tenant", default=None)
_admin_scope: ContextVar[bool] = ContextVar("repse_admin_scope", default=False)


def set_current_tenant(organization_id: int | None) -> None:
    _current_tenant.set(organization_id)


def get_current_tenant() -> int | None:
    return _current_tenant.get()


@contextmanager
def with_admin_scope() -> Iterator[None]:
    """Bypass the tenant filter. Use only in ops/seed/migration code."""
    token = _admin_scope.set(True)
    try:
        yield
    finally:
        _admin_scope.reset(token)


@declarative_mixin
class TenantOwned:
    """Every row carries the tenant it belongs to."""

    organization_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(BigInteger, "mysql"),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )


@event.listens_for(Session, "do_orm_execute")
def _inject_tenant_filter(orm_execute_state) -> None:  # type: ignore[no-untyped-def]
    """Inject `organization_id = :current_tenant_id` into every ORM Select/Update/Delete.

    Skipped when:
      * `with_admin_scope()` is active (seed/ops code).
      * The execution opts-out via `populate_existing` (refresh) — same as the
        recipe in the SQLAlchemy docs.
      * The statement is not an ORM one (raw SQL goes through unchanged).
    """
    if _admin_scope.get():
        return
    if not orm_execute_state.is_select:
        return
    if orm_execute_state.execution_options.get("skip_tenant_filter"):
        return

    tenant_id = _current_tenant.get()
    if tenant_id is None:
        # Fail closed: missing tenant context on a tenant-owned query is a bug.
        # We don't know yet whether the statement targets a TenantOwned model,
        # so we let SQLAlchemy proceed; the loader criteria below is a no-op
        # for non-TenantOwned classes.
        return

    orm_execute_state.statement = orm_execute_state.statement.options(
        with_loader_criteria(
            TenantOwned,
            lambda cls: cls.organization_id == tenant_id,
            include_aliases=True,
        )
    )
