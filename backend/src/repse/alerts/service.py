"""Alerts engine (T010 tz helpers + T015 evaluator + per-org daily sweep).

Reuses spec 001/006 domain: required document types are derived from the
supplier's SupplierType, and "expired" reuses the stored DocumentStatus
(maintained by the documents recalculation job). "Expiring soon" is computed
here against AlertConfig.expiring_lead_time_days, which is independent from the
org-level threshold used by the grid (spec 002 keeps its own window).

Note (US2/T035): "Faltante" alerts are not yet emitted here; this sweep covers
document-backed expiring_soon and expired. Missing-period enumeration is added
in the US2 phase.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from repse.alerts import recipients as recipients_mod
from repse.alerts.inapp import build_inapp_notifications, make_dedup_key
from repse.alerts.models import (
    AlertChannel,
    AlertConfig,
    AlertSilence,
    AlertType,
    Notification,
    NotificationStatus,
    RunStatus,
)
from repse.alerts.render import render_alert_email
from repse.alerts.smtp_client import SmtpError, send_email
from repse.config import get_settings
from repse.db.session import session_scope
from repse.db.tenant_filter import set_current_tenant, with_admin_scope
from repse.document_types.models import DocumentType
from repse.documents.models import Document, DocumentStatus
from repse.logging import get_logger
from repse.organizations.models import Organization, OrgStatus
from repse.supplier_types.models import (
    RequirementStatus,
    SupplierTypeDocumentRequirement,
)
from repse.suppliers.models import Supplier, SupplierStatus

log = get_logger(__name__)


# --- T010: per-tenant timezone helpers ----------------------------------------


def tenant_today(org: Organization) -> date:
    return datetime.now(ZoneInfo(org.timezone)).date()


def should_run_now(org: Organization, config: AlertConfig, now_utc: datetime) -> bool:
    """True when the local time has passed daily_run_at and we haven't run today."""
    tz = ZoneInfo(org.timezone)
    local_now = now_utc.astimezone(tz)
    if local_now.time() < config.daily_run_at:
        return False
    if config.last_run_at is None:
        return True
    last_local = config.last_run_at.replace(tzinfo=timezone.utc).astimezone(tz)
    return last_local.date() < local_now.date()


# --- candidate gathering ------------------------------------------------------


def _required_type_ids(db: Session, supplier_type_id: int, organization_id: int) -> set[int]:
    rows = db.execute(
        select(SupplierTypeDocumentRequirement.document_type_id).where(
            SupplierTypeDocumentRequirement.supplier_type_id == supplier_type_id,
            SupplierTypeDocumentRequirement.organization_id == organization_id,
            SupplierTypeDocumentRequirement.status == RequirementStatus.ACTIVE,
        )
    ).scalars()
    return set(rows)


def _active_silenced_doc_ids(db: Session, organization_id: int) -> set[int]:
    rows = db.execute(
        select(AlertSilence.document_id).where(
            AlertSilence.organization_id == organization_id,
            AlertSilence.ended_at.is_(None),
        )
    ).scalars()
    return set(rows)


def _docs_for_supplier(
    db: Session, organization_id: int, supplier_id: int, required_type_ids: set[int]
) -> list[tuple[Document, str]]:
    if not required_type_ids:
        return []
    return list(
        db.execute(
            select(Document, DocumentType.name)
            .join(DocumentType, DocumentType.id == Document.document_type_id)
            .where(
                Document.organization_id == organization_id,
                Document.supplier_id == supplier_id,
                Document.is_latest.is_(True),
                Document.deleted_at.is_(None),
                Document.document_type_id.in_(required_type_ids),
            )
        ).all()
    )


def _classify(
    rows: list[tuple[Document, str]],
    *,
    today: date,
    lead_days: int,
    silenced: set[int],
) -> dict[AlertType, list[tuple[Document, str]]]:
    """Split required latest docs into expiring_soon / expired buckets."""
    horizon = today + timedelta(days=lead_days)
    expiring: list[tuple[Document, str]] = []
    expired: list[tuple[Document, str]] = []
    for doc, type_name in rows:
        if doc.id in silenced:
            continue
        if doc.status == DocumentStatus.EXPIRED:
            expired.append((doc, type_name))
        elif doc.due_date_effective is not None and today < doc.due_date_effective <= horizon:
            expiring.append((doc, type_name))
    return {AlertType.EXPIRING_SOON: expiring, AlertType.EXPIRED: expired}


def _build_payload(
    supplier: Supplier, docs: list[tuple[Document, str]], today: date, base_url: str
) -> dict:
    documents = []
    for doc, type_name in docs:
        due = doc.due_date_effective
        documents.append(
            {
                "id": doc.id,
                "type_name": type_name,
                "period": doc.coverage_period_start.isoformat()
                if doc.coverage_period_start
                else None,
                "due_date": due.isoformat() if due else None,
                "days_until_due": (due - today).days if due else None,
                "link": f"{base_url}/suppliers/{supplier.id}/documents/{doc.id}",
            }
        )
    return {
        "supplier_id": supplier.id,
        "supplier_name": supplier.legal_name,
        "documents": documents,
    }


def _email_notification(
    *,
    organization_id: int,
    supplier_id: int,
    alert_type: AlertType,
    run_date: date,
    payload: dict,
    email: str,
) -> Notification:
    return Notification(
        organization_id=organization_id,
        supplier_id=supplier_id,
        recipient_user_id=None,
        recipient_email=email,
        channel=AlertChannel.EMAIL,
        alert_type=alert_type,
        payload_json=payload,
        run_date=run_date,
        dedup_key=make_dedup_key(
            supplier_id, alert_type, run_date, AlertChannel.EMAIL, email
        ),
        status=NotificationStatus.PENDING,
    )


def _persist_notifications(
    db: Session, organization_id: int, candidates: list[Notification]
) -> int:
    """Add only notifications whose dedup_key doesn't already exist (idempotency)."""
    if not candidates:
        return 0
    keys = [c.dedup_key for c in candidates]
    existing = set(
        db.execute(
            select(Notification.dedup_key).where(
                Notification.organization_id == organization_id,
                Notification.dedup_key.in_(keys),
            )
        ).scalars()
    )
    created = 0
    seen: set[str] = set()
    for c in candidates:
        if c.dedup_key in existing or c.dedup_key in seen:
            continue
        seen.add(c.dedup_key)
        db.add(c)
        created += 1
    db.flush()
    return created


def _send_pending_emails(db: Session, run_date: date) -> tuple[int, int]:
    settings = get_settings()
    pending = list(
        db.execute(
            select(Notification).where(
                Notification.channel == AlertChannel.EMAIL,
                Notification.status == NotificationStatus.PENDING,
                Notification.run_date == run_date,
            )
        ).scalars()
    )
    sent = 0
    failed = 0
    for notif in pending:
        subject, html, text = render_alert_email(notif.alert_type, notif.payload_json)
        notif.attempts = (notif.attempts or 0) + 1
        notif.last_attempted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        try:
            send_email(notif.recipient_email, subject, html, text, settings=settings)
        except SmtpError as exc:
            notif.status = NotificationStatus.FAILED
            notif.error_message = str(exc)[:2000]
            failed += 1
        else:
            notif.status = NotificationStatus.SENT
            notif.sent_at = datetime.now(timezone.utc).replace(tzinfo=None)
            sent += 1
    db.flush()
    return sent, failed


# --- T015: per-org sweep ------------------------------------------------------


def run_org_sweep(
    db: Session,
    org: Organization,
    config: AlertConfig,
    *,
    today: date | None = None,
    send: bool = True,
) -> dict:
    """Evaluate one tenant and persist (and optionally send) its notifications."""
    today = today or tenant_today(org)
    base_url = get_settings().app_base_url.rstrip("/")
    silenced = _active_silenced_doc_ids(db, org.id)
    suppliers = list(
        db.execute(
            select(Supplier).where(
                Supplier.organization_id == org.id,
                Supplier.status == SupplierStatus.ACTIVE,
            )
        ).scalars()
    )
    inapp_user_ids = recipients_mod.inapp_recipient_user_ids(db, org.id)

    candidates: list[Notification] = []
    for supplier in suppliers:
        required = _required_type_ids(db, supplier.supplier_type_id, org.id)
        rows = _docs_for_supplier(db, org.id, supplier.id, required)
        buckets = _classify(
            rows, today=today, lead_days=config.expiring_lead_time_days, silenced=silenced
        )
        for alert_type, docs in buckets.items():
            if not docs:
                continue
            payload = _build_payload(supplier, docs, today, base_url)
            for email in recipients_mod.resolve_recipients(db, org.id, supplier.id, config):
                candidates.append(
                    _email_notification(
                        organization_id=org.id,
                        supplier_id=supplier.id,
                        alert_type=alert_type,
                        run_date=today,
                        payload=payload,
                        email=email,
                    )
                )
            candidates.extend(
                build_inapp_notifications(
                    organization_id=org.id,
                    supplier_id=supplier.id,
                    alert_type=alert_type,
                    run_date=today,
                    payload=payload,
                    user_ids=inapp_user_ids,
                )
            )

    created = _persist_notifications(db, org.id, candidates)
    db.commit()

    sent = failed = 0
    if send:
        sent, failed = _send_pending_emails(db, today)
        db.commit()

    _mark_run(config, created=created, sent=sent, failed=failed)
    db.commit()
    return {"created": created, "emails_sent": sent, "emails_failed": failed}


def _mark_run(config: AlertConfig, *, created: int, sent: int, failed: int) -> None:
    config.last_run_at = datetime.now(timezone.utc).replace(tzinfo=None)
    config.last_run_status = (
        RunStatus.FAILED if (failed and not sent) else RunStatus.PARTIAL if failed else RunStatus.SUCCESS
    )
    config.last_run_summary = {
        "notifications_created": created,
        "emails_sent": sent,
        "emails_failed": failed,
    }


# --- daily entrypoint (called by the scheduler / CLI) -------------------------


def run_daily_alerts(*, now_utc: datetime | None = None, force: bool = False) -> dict[int, dict]:
    """Sweep every active/grace tenant whose local run time has arrived."""
    now_utc = now_utc or datetime.now(timezone.utc)
    with session_scope() as db, with_admin_scope():
        org_ids = list(
            db.execute(
                select(Organization.id).where(
                    Organization.status.in_([OrgStatus.ACTIVE, OrgStatus.GRACE])
                )
            ).scalars()
        )

    results: dict[int, dict] = {}
    for org_id in org_ids:
        try:
            with session_scope() as db:
                with with_admin_scope():
                    org = db.get(Organization, org_id)
                    config = db.execute(
                        select(AlertConfig).where(AlertConfig.organization_id == org_id)
                    ).scalar_one_or_none()
                if org is None or config is None or not config.enabled:
                    continue
                if not force and not should_run_now(org, config, now_utc):
                    continue
                set_current_tenant(org_id)
                try:
                    results[org_id] = run_org_sweep(db, org, config)
                finally:
                    set_current_tenant(None)
        except Exception:  # pragma: no cover - resilient daily job
            log.exception("alerts.sweep_failed", extra={"organization_id": org_id})
            results[org_id] = {"error": True}
    log.info("alerts.daily_sweep_completed", extra={"results": results})
    return results
