"""Audit log read routes (T100 spec 001 — contracts/audit.md).

Acceso restringido a admin y manager (viewer queda fuera por la política del
contrato: la bitácora puede contener metadata sensible).
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from repse.audit.models import AuditLog
from repse.auth.dependencies import CurrentUser, require_role
from repse.db.session import get_db
from repse.users.models import Role, User

router = APIRouter()


@router.get("")
def list_audit_log(
    actor_user_id: int | None = Query(None),
    entity_type: str | None = Query(None, max_length=64),
    entity_id: int | None = Query(None),
    action: str | None = Query(None, max_length=64),
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user: CurrentUser = Depends(require_role(Role.ADMIN.value, Role.MANAGER.value)),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    if actor_user_id is not None:
        stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)
    if entity_type is not None:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    if since is not None:
        stmt = stmt.where(AuditLog.created_at >= since)
    if until is not None:
        stmt = stmt.where(AuditLog.created_at <= until)

    rows = db.execute(stmt.limit(limit + 1)).scalars().all()
    has_more = len(rows) > limit
    rows = rows[:limit]

    actor_ids = {r.actor_user_id for r in rows if r.actor_user_id is not None}
    users_by_id: dict[int, User] = {}
    if actor_ids:
        users_by_id = {
            u.id: u
            for u in db.execute(select(User).where(User.id.in_(actor_ids))).scalars().all()
        }

    items: list[dict] = []
    for row in rows:
        if row.actor_user_id is None:
            actor_payload: dict | None = None
        else:
            u = users_by_id.get(int(row.actor_user_id))
            actor_payload = (
                {
                    "id": u.id,
                    "display_name": u.display_name,
                    "email": u.email,
                }
                if u is not None
                else {"id": row.actor_user_id, "display_name": "(usuario eliminado)", "email": None}
            )
        items.append(
            {
                "id": row.id,
                "actor": actor_payload,
                "action": row.action,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "metadata": row.metadata_ or {},
                "created_at": row.created_at,
            }
        )

    return {"items": items, "next_cursor": None, "has_more": has_more}
