"""Opt-in error tracking. If SENTRY_DSN is empty, this is a no-op."""

from __future__ import annotations

import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from repse.config import Settings


def init_sentry(settings: Settings) -> None:
    if not settings.sentry_dsn:
        return
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env.value,
        release=f"repse@{__import__('repse').__version__}",
        send_default_pii=False,  # constitution: minimal PII
        traces_sample_rate=0.1 if not settings.is_local else 0.0,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            AsyncioIntegration(),
        ],
    )
