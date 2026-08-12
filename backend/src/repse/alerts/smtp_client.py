"""Generic SMTP sender (T011). aiosmtplib + tenacity, no vendor SDK.

Exposes a synchronous ``send_email`` suitable for the threaded daily sweep
(``asyncio.run`` per message). Retries are short (transient hiccups only) so a
single message never blocks the batch for long; permanent failures (auth,
rejected recipient) fail fast and are marked ``failed`` for the retry CLI.
"""

from __future__ import annotations

import asyncio
from email.message import EmailMessage

import aiosmtplib
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from repse.config import Settings, get_settings
from repse.logging import get_logger

log = get_logger(__name__)

_RETRYABLE = (
    aiosmtplib.SMTPConnectError,
    aiosmtplib.SMTPServerDisconnected,
    asyncio.TimeoutError,
)


class SmtpError(Exception):
    """Raised when an email could not be delivered after retries."""


def _build_message(settings: Settings, to_email: str, subject: str, html: str, text: str) -> EmailMessage:
    msg = EmailMessage()
    from_name = settings.smtp_from_name
    msg["From"] = f"{from_name} <{settings.smtp_from_email}>" if from_name else settings.smtp_from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    if settings.smtp_reply_to:
        msg["Reply-To"] = settings.smtp_reply_to
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    return msg


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(_RETRYABLE),
    reraise=True,
)
async def _send_async(settings: Settings, msg: EmailMessage) -> None:
    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username or None,
        password=settings.smtp_password.get_secret_value() or None,
        start_tls=settings.smtp_use_starttls,
        use_tls=settings.smtp_use_ssl,
        timeout=settings.smtp_timeout_seconds,
    )


def send_email(
    to_email: str,
    subject: str,
    html: str,
    text: str,
    *,
    settings: Settings | None = None,
) -> None:
    """Send one email synchronously. Raises ``SmtpError`` on permanent failure."""
    settings = settings or get_settings()
    if not settings.smtp_host:
        raise SmtpError("SMTP not configured (SMTP_HOST empty)")
    msg = _build_message(settings, to_email, subject, html, text)
    try:
        asyncio.run(_send_async(settings, msg))
    except Exception as exc:
        raise SmtpError(str(exc)) from exc
