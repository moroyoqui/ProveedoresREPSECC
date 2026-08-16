"""Envío vía la API transaccional de Brevo (sib_api_v3_sdk).

Alternativa al relay SMTP (``smtp_client``): usa la API key de la cuenta en vez
de credenciales SMTP dedicadas. El transporte lo elige ``mailer.send_email``
según haya o no ``BREVO_API_KEY``.

El remitente sale de ``SMTP_FROM_EMAIL`` / ``SMTP_FROM_NAME``, las mismas
variables que usa el camino SMTP, para no duplicar configuración.
"""

from __future__ import annotations

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from repse.alerts.smtp_client import SmtpError
from repse.config import Settings, get_settings
from repse.logging import get_logger

log = get_logger(__name__)


class BrevoError(SmtpError):
    """Fallo de entrega vía API de Brevo.

    Hereda de ``SmtpError`` para que ``service.run_daily_alerts`` marque la
    notificación como ``failed`` sin distinguir el transporte.
    """


def send_email(
    to_email: str,
    subject: str,
    html: str,
    text: str,
    *,
    settings: Settings | None = None,
) -> None:
    """Envía un correo por la API de Brevo. Lanza ``BrevoError`` si falla."""
    settings = settings or get_settings()
    api_key = settings.brevo_api_key.get_secret_value()
    if not api_key:
        raise BrevoError("Brevo not configured (BREVO_API_KEY empty)")

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = api_key
    api = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    sender = {"email": settings.smtp_from_email}
    if settings.smtp_from_name:
        sender["name"] = settings.smtp_from_name

    email = sib_api_v3_sdk.SendSmtpEmail(
        sender=sender,
        to=[{"email": to_email}],
        subject=subject,
        html_content=html,
        # Se conserva la parte de texto que ya genera el render: los mensajes
        # sólo-HTML puntúan peor en los filtros anti-spam.
        text_content=text,
        reply_to={"email": settings.smtp_reply_to} if settings.smtp_reply_to else None,
    )

    # El SDK no acepta timeout en el constructor: va por llamada. Sin él, un
    # proveedor que no responde bloquea el hilo del barrido diario.
    try:
        api.send_transac_email(email, _request_timeout=settings.smtp_timeout_seconds)
    except ApiException as exc:
        raise BrevoError(f"Brevo API error: {exc}") from exc
