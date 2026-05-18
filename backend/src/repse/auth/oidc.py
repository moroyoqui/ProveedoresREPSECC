"""OIDC clients for Google and Microsoft (Entra) via Authlib.

Discovery documents are fetched lazily so the app boots without network.
"""

from __future__ import annotations

from authlib.integrations.starlette_client import OAuth

from repse.config import Settings


GOOGLE_METADATA_URL = "https://accounts.google.com/.well-known/openid-configuration"


def microsoft_metadata_url(tenant: str) -> str:
    # `common` allows any Entra tenant; `consumers` only personal Microsoft.
    return f"https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration"


def build_oauth(settings: Settings) -> OAuth:
    oauth = OAuth()

    if settings.oidc_google_client_id and settings.oidc_google_client_secret.get_secret_value():
        oauth.register(
            name="google",
            client_id=settings.oidc_google_client_id,
            client_secret=settings.oidc_google_client_secret.get_secret_value(),
            server_metadata_url=GOOGLE_METADATA_URL,
            client_kwargs={"scope": "openid email profile"},
        )

    if (
        settings.oidc_microsoft_client_id
        and settings.oidc_microsoft_client_secret.get_secret_value()
    ):
        oauth.register(
            name="microsoft",
            client_id=settings.oidc_microsoft_client_id,
            client_secret=settings.oidc_microsoft_client_secret.get_secret_value(),
            server_metadata_url=microsoft_metadata_url(settings.oidc_microsoft_tenant),
            client_kwargs={"scope": "openid email profile"},
        )

    return oauth
