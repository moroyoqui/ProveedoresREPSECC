"""Multi-tenant isolation enforced at the ORM layer (constitution principle II).

Every model that owns tenant data MUST inherit from `TenantOwned`. The
`before_compile` event listener inspects every `Select`/`Update`/`Delete` and
injects ``WHERE organization_id = :current_tenant_id`` automatically, unless
the call site explicitly enters ``with_admin_scope()`` (used by ops/admin code).
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

from sqlalchemy import BigInteger, ForeignKey, event
from sqlalchemy.orm import Mapped, declarative_mixin, mapped_column
from sqlalchemy.sql import Delete, Select, Update
from sqlalchemy.sql.expression import ClauseElement

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


def _stmt_targets_tenant_owned(stmt: ClauseElement) -> tuple[bool, object | None]:
    """Inspect the statement and return (is_tenant_owned, target_table).

    Walks the FROM clause looking for a table whose mapped class has the
    `TenantOwned` mixin.
    """
    try:
        # SQLAlchemy 2 exposes `get_final_froms()` on Select; for Update/Delete
        # the entity description is on `entity_description`.
        if isinstance(stmt, Select):
            froms = stmt.get_final_froms()
        else:
            descr = getattr(stmt, "entity_description", None)
            froms = [descr["entity"]] if descr else []
    except Exception:
        return False, None

    for f in froms:
        cls = getattr(f, "entity", f)
        if isinstance(cls, type) and issubclass(cls, TenantOwned):
            return True, cls
    return False, None


@event.listens_for(Select, "before_compile", retval=True)
@event.listens_for(Update, "before_compile", retval=True)
@event.listens_for(Delete, "before_compile", retval=True)
def _inject_tenant_filter(stmt: ClauseElement) -> ClauseElement:
    if _admin_scope.get():
        return stmt
    is_tenant, target = _stmt_targets_tenant_owned(stmt)
    if not is_tenant or target is None:
        return stmt
    tenant_id = _current_tenant.get()
    if tenant_id is None:
        # Fail closed: missing tenant context on a tenant-owned query is a bug.
        raise RuntimeError(
            f"Tenant filter active but no current_tenant set when querying {target.__name__}"
        )
    return stmt.where(target.organization_id == tenant_id)  # type: ignore[union-attr]
