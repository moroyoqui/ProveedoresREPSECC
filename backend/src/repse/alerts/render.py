"""Email rendering for alerts (T012). Jinja2 HTML (inline CSS) + plain-text fallback.

A single parameterized template serves both alert types; US1/US2 may specialize
the copy without changing this loader.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from repse.alerts.models import AlertType

_TEMPLATES_DIR = Path(__file__).parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)

_SUBJECTS = {
    AlertType.EXPIRING_SOON: "Documentos por vencer — {supplier_name}",
    AlertType.EXPIRED: "Documentos vencidos — {supplier_name}",
}


def render_alert_email(alert_type: AlertType, ctx: dict) -> tuple[str, str, str]:
    """Return (subject, html_body, text_body) for an aggregated supplier alert.

    ``ctx`` shape: {supplier_name, documents:[{type_name, period, due_date,
    days_until_due, link}], alert_type}.
    """
    subject = _SUBJECTS[alert_type].format(supplier_name=ctx["supplier_name"])
    render_ctx = {**ctx, "alert_type": alert_type.value, "subject": subject}
    html = _env.get_template("alert.html.j2").render(**render_ctx)
    text = _env.get_template("alert.txt.j2").render(**render_ctx)
    return subject, html, text
