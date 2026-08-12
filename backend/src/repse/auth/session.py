"""Stateless session cookie signed with `itsdangerous`.

Cookie: `session` (HttpOnly, Secure, SameSite=Lax, Path=/, max-age 12h).
Payload: {user_id, organization_id, role, expires_at}.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from repse.config import Settings

COOKIE_NAME = "session"
COOKIE_TTL_SECONDS = 12 * 60 * 60  # 12 h
COOKIE_KWARGS = {
    "httponly": True,
    "secure": True,
    "samesite": "lax",
    "path": "/",
}


@dataclass(frozen=True)
class SessionPayload:
    user_id: int
    organization_id: int
    role: str  # "admin" | "manager" | "viewer" | "supplier"
    expires_at: datetime
    supplier_id: int | None = None


class SessionManager:
    def __init__(self, settings: Settings) -> None:
        self._serializer = URLSafeTimedSerializer(
            settings.app_secret.get_secret_value(), salt="repse.session"
        )
        self._is_local = settings.is_local

    def issue(self, response: Response, payload: SessionPayload) -> None:
        token = self._serializer.dumps(
            {
                "user_id": payload.user_id,
                "organization_id": payload.organization_id,
                "role": payload.role,
                "expires_at": payload.expires_at.isoformat(),
                "supplier_id": payload.supplier_id,
            }
        )
        response.set_cookie(
            COOKIE_NAME,
            token,
            max_age=COOKIE_TTL_SECONDS,
            secure=not self._is_local,  # allow http on localhost dev
            **{k: v for k, v in COOKIE_KWARGS.items() if k != "secure"},
        )

    def revoke(self, response: Response) -> None:
        response.delete_cookie(COOKIE_NAME, path="/")

    def read(self, request: Request) -> SessionPayload | None:
        raw = request.cookies.get(COOKIE_NAME)
        if not raw:
            return None
        try:
            payload = self._serializer.loads(raw, max_age=COOKIE_TTL_SECONDS)
        except (BadSignature, SignatureExpired):
            return None
        if not isinstance(payload, dict):
            return None
        try:
            raw_sid = payload.get("supplier_id")
            return SessionPayload(
                user_id=int(payload["user_id"]),
                organization_id=int(payload["organization_id"]),
                role=str(payload["role"]),
                expires_at=datetime.fromisoformat(str(payload["expires_at"])),
                supplier_id=int(raw_sid) if raw_sid is not None else None,
            )
        except (KeyError, ValueError, TypeError):
            return None


def fresh_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=COOKIE_TTL_SECONDS)
