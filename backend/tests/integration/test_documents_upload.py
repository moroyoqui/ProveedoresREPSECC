"""Duplicate-file detection by sha256.

Contrato vigente (specs 009 FR-027 / 012): el duplicado solo se rechaza dentro
de la misma celda (supplier + tipo + período); el mismo contenido en otro
período se acepta — la unicidad en disco la garantiza el sufijo UUID.
"""

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

    # Mismo contenido en la MISMA celda → 409 duplicate_file.
    same_cell = client_with_session.post(
        f"/api/v1/suppliers/{seeded_supplier.id}/documents",
        files={"file": ("b.pdf", io.BytesIO(payload), "application/pdf")},
        data=data,
    )
    assert same_cell.status_code == 409
    assert same_cell.json()["error"]["details"]["code"] == "duplicate_file"

    # Mismo contenido en OTRO período → 201 (specs 009/012: sin dedup global).
    other_period = client_with_session.post(
        f"/api/v1/suppliers/{seeded_supplier.id}/documents",
        files={"file": ("b.pdf", io.BytesIO(payload), "application/pdf")},
        data={**data, "coverage_period_start": "2026-05-01"},
    )
    assert other_period.status_code == 201
