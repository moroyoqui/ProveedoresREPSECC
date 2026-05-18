"""T039 spec 001: duplicate-file detection by sha256 within a tenant."""

from __future__ import annotations

import io

import pytest


pytestmark = pytest.mark.integration


def _minimal_pdf() -> bytes:
    return b"%PDF-1.4\n%test\n%%EOF\n"


def test_duplicate_file_rejected(client_with_session, seeded_supplier, opinion_sat_type) -> None:
    payload = _minimal_pdf()
    data = {"document_type_id": str(opinion_sat_type.id), "coverage_period_start": "2026-04-01"}

    first = client_with_session.post(
        f"/api/v1/suppliers/{seeded_supplier.id}/documents",
        files={"file": ("a.pdf", io.BytesIO(payload), "application/pdf")},
        data=data,
    )
    assert first.status_code == 201

    second = client_with_session.post(
        f"/api/v1/suppliers/{seeded_supplier.id}/documents",
        files={"file": ("b.pdf", io.BytesIO(payload), "application/pdf")},
        data={**data, "coverage_period_start": "2026-05-01"},
    )
    assert second.status_code == 409
    body = second.json()
    assert body["error"]["code"] == "duplicate_file"
    assert "existing_document_id" in body["error"]["details"]
