"""Contract tests for auth endpoints (T034-T035 spec 001).

These exercise the HTTP shape against a real DB but mock the OIDC provider.
The provider is mocked at the Authlib level so we never touch the network.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.integration


def test_me_without_session_returns_401(client) -> None:
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401
    body = res.json()
    assert body["error"]["code"] == "unauthenticated"


def test_logout_revokes_cookie(client_with_session) -> None:
    res = client_with_session.post("/api/v1/auth/logout")
    assert res.status_code == 204
    set_cookie = res.headers.get("set-cookie", "")
    assert "session=" in set_cookie
    assert "Max-Age=0" in set_cookie or "expires=" in set_cookie.lower()


def test_me_returns_profile_with_organization(client_with_session, session_user) -> None:
    res = client_with_session.get("/api/v1/auth/me")
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == session_user.id
    assert body["role"] in {"admin", "manager", "viewer"}
    assert body["organization"]["id"] == session_user.organization_id
