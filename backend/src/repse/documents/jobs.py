"""Background jobs related to Documents (T093 spec 001).

Scheduler diario que dispara ``recalc_for_organization`` para cada
``Organization`` ``active`` o ``grace``. Se usa ``asyncio`` puro (sin
dependencia externa) — el spec menciona "APScheduler simple" como opción, pero
para un cron diario de un solo job no aporta valor frente a un loop nativo.

Se invoca desde ``main.lifespan`` (``schedule_daily_recalculation``); el loop
duerme hasta la siguiente medianoche UTC y corre la recalculación.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from repse.db.session import session_scope
from repse.db.tenant_filter import with_admin_scope
from repse.documents.recalculator import recalc_for_organization
from repse.organizations.models import Organization, OrgStatus

logger = logging.getLogger(__name__)


def run_daily_recalculation() -> dict[int, int]:
    """Recalcula el status de documentos en todas las orgs activas/grace.

    Devuelve un dict ``{organization_id: changed_count}``.
    Síncrono, pensado para invocación directa desde un cron OS, scripts de ops
    o el loop async definido abajo.
    """
    results: dict[int, int] = {}
    with session_scope() as db, with_admin_scope():
        orgs = (
            db.execute(
                select(Organization).where(
                    Organization.status.in_([OrgStatus.ACTIVE, OrgStatus.GRACE])
                )
            )
            .scalars()
            .all()
        )
        org_ids = [o.id for o in orgs]

    for org_id in org_ids:
        try:
            with session_scope() as db:
                changed = recalc_for_organization(
                    db, organization_id=org_id, audit=True
                )
            results[org_id] = changed
        except Exception:  # pragma: no cover - resilient cron
            logger.exception(
                "documents.recalc_failed", extra={"organization_id": org_id}
            )
            results[org_id] = -1

    logger.info("documents.daily_recalc_completed", extra={"results": results})
    return results


def _seconds_until_next_run(now: datetime, hour_utc: int = 5) -> float:
    """Retorna segundos hasta la próxima ejecución diaria a ``hour_utc``."""
    today_run = now.replace(hour=hour_utc, minute=0, second=0, microsecond=0)
    if now >= today_run:
        next_run = today_run + timedelta(days=1)
    else:
        next_run = today_run
    return max(60.0, (next_run - now).total_seconds())


async def schedule_daily_recalculation(hour_utc: int = 5) -> None:
    """Loop async que corre ``run_daily_recalculation`` cada 24 h a ``hour_utc``.

    Diseñado para ejecutarse como background task lanzada desde el ``lifespan``
    de FastAPI. ``CancelledError`` termina el loop limpiamente al shutdown.
    """
    logger.info("documents.recalc_scheduler_started", extra={"hour_utc": hour_utc})
    while True:
        delay = _seconds_until_next_run(datetime.now(timezone.utc), hour_utc)
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            logger.info("documents.recalc_scheduler_stopped")
            raise
        try:
            await asyncio.to_thread(run_daily_recalculation)
        except Exception:  # pragma: no cover - resilient cron
            logger.exception("documents.recalc_scheduler_iteration_failed")
