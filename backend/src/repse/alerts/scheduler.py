"""Alerts scheduler (T016).

Native asyncio loop launched from main.lifespan — same approach as
``documents.jobs.schedule_daily_recalculation`` (that module already documents
why APScheduler adds no value for a single daily cron). The loop ticks every few
minutes; ``run_daily_alerts`` decides which tenants' local run time has arrived
(``should_run_now``) and stays idempotent via the notifications unique key.
"""

from __future__ import annotations

import asyncio

from repse.alerts.service import run_daily_alerts
from repse.logging import get_logger

log = get_logger(__name__)

_TICK_SECONDS = 300  # 5 min — fine-grained enough to honor per-tenant daily_run_at


async def schedule_daily_alerts(tick_seconds: int = _TICK_SECONDS) -> None:
    """Background loop. Cancelled cleanly on app shutdown."""
    log.info("alerts.scheduler_started", extra={"tick_seconds": tick_seconds})
    while True:
        try:
            await asyncio.sleep(tick_seconds)
        except asyncio.CancelledError:
            log.info("alerts.scheduler_stopped")
            raise
        try:
            await asyncio.to_thread(run_daily_alerts)
        except Exception:  # pragma: no cover - resilient cron
            log.exception("alerts.scheduler_iteration_failed")
