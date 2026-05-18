"""Append-only audit log helper (contracts/audit.md spec 001).

System actions (OCR, recalculation, jobs) call `write_system_event` with
actor_user_id=None per FR-011e of spec 001.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class AuditEvent:
    organization_id: int
    actor_user_id: int | None
    action: str
    entity_type: str
    entity_id: int | None
    metadata: dict[str, Any]


def write_event(db: Session, event: AuditEvent) -> None:
    """Insert an audit row. The model lives in `repse.audit.models` (Phase 3)."""
    from repse.audit.models import AuditLog  # local import; model created in Phase 3

    row = AuditLog(
        organization_id=event.organization_id,
        actor_user_id=event.actor_user_id,
        action=event.action,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        metadata_=event.metadata,
    )
    db.add(row)


def write_system_event(
    db: Session,
    *,
    organization_id: int,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Audit a system-originated event (no human actor, FR-011e spec 001)."""
    write_event(
        db,
        AuditEvent(
            organization_id=organization_id,
            actor_user_id=None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata or {},
        ),
    )


def redact_pii(value: str) -> str:
    """Hash + domain redaction for emails before they enter audit metadata.

    Implements the constitution's 'minimal PII' principle plus research §8 of
    spec 002. Non-email strings pass through unchanged (callers must filter).
    """
    import hashlib

    if "@" not in value:
        return value
    local, _, domain = value.partition("@")
    digest = hashlib.sha256(local.encode("utf-8")).hexdigest()[:6]
    return f"{digest}@{domain}"
