"""Contract tests for document upload (T037 spec 001)."""

from __future__ import annotations

import io

import pytest


pytestmark = pytest.mark.integration


def _minimal_pdf_bytes() -> bytes:
    # Smallest valid PDF (1.4) — opens in any reader and Tesseract returns
    # empty text without error.
    return (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\n"
        b"xref\n0 3\n0000000000 65535 f \n0000000009 00000 n \n0000000053 00000 n \n"
        b"trailer<</Size 3/Root 1 0 R>>\nstartxref\n99\n%%EOF\n"
    )


def test_upload_document_creates_with_audit_added(client_with_session, seeded_supplier, opinion_sat_type) -> None:
    files = {"file": ("opinion.pdf", io.BytesIO(_minimal_pdf_bytes()), "application/pdf")}
    data = {
        "document_type_id": str(opinion_sat_type.id),
        "coverage_period_start": "2026-04-01",
    }
    res = client_with_session.post(
        f"/api/v1/suppliers/{seeded_supplier.id}/documents",
        files=files,
        data=data,
    )
    assert res.status_code == 201
    body = res.json()
    assert body["supplier_id"] == seeded_supplier.id
    assert body["document_type_id"] == opinion_sat_type.id
    assert body["version"] == 1
    assert body["is_latest"] is True
    assert body["audit"]["added"]["user"]["id"] > 0
    assert body["audit"]["last_updated"] is None
    assert body["audit"]["validated"] is None
    # monthly periodicity: due = end of next month
    assert body["due_date_calculated"] == "2026-05-31"
    assert body["due_date_effective"] == "2026-05-31"


def test_upload_rejects_unsupported_mime(client_with_session, seeded_supplier, opinion_sat_type) -> None:
    files = {"file": ("notes.exe", io.BytesIO(b"\x00\x00\x00"), "application/x-msdownload")}
    data = {"document_type_id": str(opinion_sat_type.id), "coverage_period_start": "2026-04-01"}
    res = client_with_session.post(
        f"/api/v1/suppliers/{seeded_supplier.id}/documents",
        files=files,
        data=data,
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "validation_error"
