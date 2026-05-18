"""Contract test for POST /api/v1/suppliers (T036 spec 001)."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.integration


def test_create_supplier_assigns_sin_clasificar_when_no_type(client_with_session) -> None:
    res = client_with_session.post(
        "/api/v1/suppliers",
        json={
            "legal_name": "Servicios Industriales del Norte SA de CV",
            "rfc": "SIN9001022Y3",
            "contact_email": "juanp@sin.mx",
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["rfc"] == "SIN9001022Y3"
    assert body["supplier_type"]["origin"] == "system"
    assert body["supplier_type"]["name"] == "Sin clasificar"


def test_create_supplier_rejects_duplicate_rfc(client_with_session) -> None:
    payload = {
        "legal_name": "Empresa A",
        "rfc": "ABC9001022Y3",
        "contact_email": "a@example.mx",
    }
    first = client_with_session.post("/api/v1/suppliers", json=payload)
    assert first.status_code == 201

    second = client_with_session.post(
        "/api/v1/suppliers",
        json={**payload, "legal_name": "Empresa A duplicada"},
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "rfc_exists"


def test_create_supplier_validates_rfc_format(client_with_session) -> None:
    res = client_with_session.post(
        "/api/v1/suppliers",
        json={
            "legal_name": "Empresa con RFC inválido",
            "rfc": "BAD",  # invalid format
            "contact_email": "x@example.mx",
        },
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "validation_error"
