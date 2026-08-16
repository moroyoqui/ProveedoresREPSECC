"""Selección del transporte de correo.

Con ``BREVO_API_KEY`` definida se usa la API transaccional de Brevo; sin ella,
el relay SMTP de siempre (Mailpit en local, cualquier servidor en otros
entornos). Los llamantes no distinguen: misma firma y misma excepción base.
"""

from __future__ import annotations

from repse.alerts import brevo_client, smtp_client
from repse.alerts.smtp_client import SmtpError
from repse.config import Settings, get_settings

__all__ = ["SmtpError", "send_email"]


def send_email(
    to_email: str,
    subject: str,
    html: str,
    text: str,
    *,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    sender = (
        brevo_client.send_email
        if settings.brevo_api_key.get_secret_value()
        else smtp_client.send_email
    )
    sender(to_email, subject, html, text, settings=settings)
