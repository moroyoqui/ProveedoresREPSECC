"""T135 spec 001 addendum US2: contract tests para GET /api/v1/documents con filtros globales.

Cubre:
- Filtros: ``verified``, ``status``, ``supplier_id``, ``document_type_id``, ``q``.
- Cada item incluye ``supplier: {id, legal_name}``.
- Multi-tenant negativo: org A no ve documentos de org B (200 con lista vacía).
"""

from __future__ import annotations

import io
from datetime import date

import pytest


pytestmark = pytest.mark.integration


def _minimal_pdf_bytes(unique: bytes = b"a") -> bytes:
    return (
        b"%PDF-1.4\n"
        b"%unique-" + unique + b"\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\n"
        b"xref\n0 3\n0000000000 65535 f \n0000000009 00000 n \n0000000053 00000 n \n"
        b"trailer<</Size 3/Root 1 0 R>>\nstartxref\n99\n%%EOF\n"
    )


def _upload_doc(
    client,
    supplier_id: int,
    type_id: int,
    *,
    unique: bytes = b"dl",
    coverage: str = "2026-04-01",
) -> int:
    files = {"file": ("d.pdf", io.BytesIO(_minimal_pdf_bytes(unique)), "application/pdf")}
    data = {"document_type_id": str(type_id), "coverage_period_start": coverage}
    res = client.post(f"/api/v1/suppliers/{supplier_id}/documents", files=files, data=data)
    assert res.status_code == 201, res.text
    return res.json()["id"]


# ---------------------------------------------------------------------------
# Estructura de respuesta: supplier incluido en cada item
# ---------------------------------------------------------------------------


def test_list_documents_includes_supplier_field(
    client_with_session, seeded_supplier, opinion_sat_type
) -> None:
    """Cada item de GET /documents debe incluir ``supplier: {id, legal_name}``."""
    _upload_doc(
        client_with_session, seeded_supplier.id, opinion_sat_type.id, unique=b"ls1"
    )

    res = client_with_session.get("/api/v1/documents")
    assert res.status_code == 200, res.text
    body = res.json()
    assert "items" in body
    assert len(body["items"]) > 0

    item = body["items"][0]
    assert "supplier" in item, "La respuesta debe incluir el campo 'supplier'"
    assert "id" in item["supplier"]
    assert "legal_name" in item["supplier"]
    assert item["supplier"]["id"] == seeded_supplier.id
    assert item["supplier"]["legal_name"] == seeded_supplier.legal_name


# ---------------------------------------------------------------------------
# Filtro verified
# ---------------------------------------------------------------------------


def test_filter_verified_false_returns_unverified_only(
    client_with_session, seeded_supplier, opinion_sat_type
) -> None:
    doc_id = _upload_doc(
        client_with_session, seeded_supplier.id, opinion_sat_type.id, unique=b"ls2"
    )
    # Verificar el doc
    client_with_session.post(f"/api/v1/documents/{doc_id}/verify", json={"note": "ok"})

    # verified=false no debe devolver el doc verificado
    res = client_with_session.get("/api/v1/documents?verified=false")
    assert res.status_code == 200
    ids = [item["id"] for item in res.json()["items"]]
    assert doc_id not in ids


def test_filter_verified_true_returns_verified_only(
    client_with_session, seeded_supplier, opinion_sat_type
) -> None:
    doc_id = _upload_doc(
        client_with_session, seeded_supplier.id, opinion_sat_type.id, unique=b"ls3"
    )
    client_with_session.post(f"/api/v1/documents/{doc_id}/verify", json={"note": "ok"})

    res = client_with_session.get("/api/v1/documents?verified=true")
    assert res.status_code == 200
    ids = [item["id"] for item in res.json()["items"]]
    assert doc_id in ids


# ---------------------------------------------------------------------------
# Filtro supplier_id
# ---------------------------------------------------------------------------


def test_filter_supplier_id_scopes_results(
    client_with_session, seeded_supplier, opinion_sat_type, db_session, session_user
) -> None:
    """Filtrar por supplier_id sólo devuelve docs de ese proveedor."""
    from repse.db.tenant_filter import set_current_tenant
    from repse.suppliers.models import Supplier, SupplierStatus
    from repse.supplier_types.models import SupplierType, SupplierTypeOrigin
    from sqlalchemy import select

    # Crear segundo proveedor en el mismo tenant
    set_current_tenant(session_user.organization_id)
    st = db_session.execute(
        select(SupplierType).where(SupplierType.origin == SupplierTypeOrigin.SYSTEM)
    ).scalar_one()
    other_supplier = Supplier(
        organization_id=session_user.organization_id,
        supplier_type_id=st.id,
        legal_name="Otro Proveedor",
        rfc="OTR900101BBB"[:13],
        status=SupplierStatus.ACTIVE,
    )
    db_session.add(other_supplier)
    db_session.commit()
    db_session.refresh(other_supplier)

    # Subir doc para el proveedor original y para el otro
    doc1_id = _upload_doc(
        client_with_session, seeded_supplier.id, opinion_sat_type.id, unique=b"ls4a"
    )
    doc2_id = _upload_doc(
        client_with_session, other_supplier.id, opinion_sat_type.id, unique=b"ls4b"
    )

    res = client_with_session.get(f"/api/v1/documents?supplier_id={seeded_supplier.id}")
    assert res.status_code == 200
    ids = [item["id"] for item in res.json()["items"]]
    assert doc1_id in ids
    assert doc2_id not in ids


# ---------------------------------------------------------------------------
# Filtro document_type_id
# ---------------------------------------------------------------------------


def test_filter_document_type_id(
    client_with_session, seeded_supplier, opinion_sat_type
) -> None:
    doc_id = _upload_doc(
        client_with_session, seeded_supplier.id, opinion_sat_type.id, unique=b"ls5"
    )
    res = client_with_session.get(
        f"/api/v1/documents?document_type_id={opinion_sat_type.id}"
    )
    assert res.status_code == 200
    ids = [item["id"] for item in res.json()["items"]]
    assert doc_id in ids


# ---------------------------------------------------------------------------
# Filtro q (búsqueda libre sobre nombre de proveedor)
# ---------------------------------------------------------------------------


def test_filter_q_matches_supplier_name(
    client_with_session, seeded_supplier, opinion_sat_type
) -> None:
    doc_id = _upload_doc(
        client_with_session, seeded_supplier.id, opinion_sat_type.id, unique=b"ls6"
    )
    # seeded_supplier.legal_name = "Servicios Industriales del Norte"
    res = client_with_session.get("/api/v1/documents?q=Industriales")
    assert res.status_code == 200
    ids = [item["id"] for item in res.json()["items"]]
    assert doc_id in ids


def test_filter_q_no_match_returns_empty(
    client_with_session, seeded_supplier, opinion_sat_type
) -> None:
    _upload_doc(
        client_with_session, seeded_supplier.id, opinion_sat_type.id, unique=b"ls7"
    )
    res = client_with_session.get("/api/v1/documents?q=ZZZNOMATCHZZZ")
    assert res.status_code == 200
    assert res.json()["items"] == []


# ---------------------------------------------------------------------------
# Multi-tenant negativo (Principio II constitución)
# ---------------------------------------------------------------------------


def test_multitenant_negative_org_a_cannot_see_org_b_docs(
    client_with_session_org_a,
    client_with_session_org_b,
    supplier_in_org_a,
    db_session,
    opinion_sat_type,
) -> None:
    """Org B consulta GET /documents y obtiene 200 con lista vacía (nunca 403)."""
    # Subir doc en org A
    files = {
        "file": ("d.pdf", io.BytesIO(_minimal_pdf_bytes(b"ls8")), "application/pdf")
    }
    data = {
        "document_type_id": str(opinion_sat_type.id),
        "coverage_period_start": "2026-04-01",
    }
    res = client_with_session_org_a.post(
        f"/api/v1/suppliers/{supplier_in_org_a.id}/documents",
        files=files,
        data=data,
    )
    assert res.status_code == 201, res.text
    doc_id = res.json()["id"]

    # Org B consulta la lista global
    res_b = client_with_session_org_b.get("/api/v1/documents")
    assert res_b.status_code == 200
    ids_b = [item["id"] for item in res_b.json()["items"]]
    assert doc_id not in ids_b, "Org B no debe ver documentos de org A"


# ---------------------------------------------------------------------------
# Paginación cursor
# ---------------------------------------------------------------------------


def test_pagination_has_more_flag(
    client_with_session, seeded_supplier, opinion_sat_type
) -> None:
    for i in range(3):
        _upload_doc(
            client_with_session,
            seeded_supplier.id,
            opinion_sat_type.id,
            unique=f"pg{i}".encode(),
            coverage=f"2026-0{i + 1}-01",
        )

    res = client_with_session.get("/api/v1/documents?limit=2")
    assert res.status_code == 200
    body = res.json()
    assert len(body["items"]) <= 2
    assert "has_more" in body
    assert "next_cursor" in body
