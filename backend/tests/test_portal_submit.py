"""Integration tests for POST /api/v1/portal/submit/{document_type_id}
and GET /api/v1/portal/submission/{document_type_id} (US6 — T035).

Negative cases must fail until T036/T037 are implemented.
Positive cases verify the happy path once implementation is complete.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

_PAST_PERIOD = date(2026, 1, 1)  # January 2026 — well before May 2026 (today)


# ---------------------------------------------------------------------------
# Helpers (shared with test_portal_upload pattern)
# ---------------------------------------------------------------------------


def _make_supplier_and_client(app, db_session, session_user):
    """Create a supplier + supplier-role user; return (client, user, supplier)."""
    from fastapi.testclient import TestClient
    from sqlalchemy import select

    from repse.auth.session import SessionManager, fresh_expiry
    from repse.config import get_settings
    from repse.db.tenant_filter import set_current_tenant, with_admin_scope
    from repse.supplier_types.models import SupplierType, SupplierTypeOrigin
    from repse.suppliers.models import Supplier, SupplierStatus
    from repse.users.models import Role, User, UserStatus

    with with_admin_scope():
        set_current_tenant(session_user.organization_id)
        st = db_session.execute(
            select(SupplierType).where(
                SupplierType.organization_id == session_user.organization_id,
                SupplierType.origin == SupplierTypeOrigin.SYSTEM,
            )
        ).scalar_one()
        supplier = Supplier(
            organization_id=session_user.organization_id,
            supplier_type_id=st.id,
            legal_name="Proveedor Submit Test",
            rfc="PST9901012Y3",
            contact_email="submit@pst.mx",
            status=SupplierStatus.ACTIVE,
        )
        db_session.add(supplier)
        db_session.flush()
        user = User(
            organization_id=session_user.organization_id,
            email="sup-submit@pst.mx",
            display_name="Supplier Submit",
            role=Role.SUPPLIER,
            status=UserStatus.ACTIVE,
            supplier_id=supplier.id,
        )
        db_session.add(user)
        db_session.flush()
        db_session.commit()

    sm = SessionManager(get_settings())
    token = sm._serializer.dumps(  # type: ignore[attr-defined]
        {
            "user_id": user.id,
            "organization_id": session_user.organization_id,
            "role": "supplier",
            "supplier_id": supplier.id,
            "expires_at": fresh_expiry().isoformat(),
        }
    )
    c = TestClient(app)
    c.cookies.set("session", token)
    return c, user, supplier


def _get_monthly_doc_type(db_session, session_user):
    """Return the first active monthly document type for the session org."""
    from sqlalchemy import select

    from repse.db.tenant_filter import set_current_tenant, with_admin_scope
    from repse.document_types.models import DocumentType, Periodicity
    from repse.supplier_types.models import (
        RequirementStatus,
        SupplierType,
        SupplierTypeDocumentRequirement,
        SupplierTypeOrigin,
    )

    with with_admin_scope():
        set_current_tenant(session_user.organization_id)
        st = db_session.execute(
            select(SupplierType).where(
                SupplierType.organization_id == session_user.organization_id,
                SupplierType.origin == SupplierTypeOrigin.SYSTEM,
            )
        ).scalar_one()
        row = db_session.execute(
            select(SupplierTypeDocumentRequirement, DocumentType)
            .join(
                DocumentType,
                DocumentType.id == SupplierTypeDocumentRequirement.document_type_id,
            )
            .where(
                SupplierTypeDocumentRequirement.supplier_type_id == st.id,
                SupplierTypeDocumentRequirement.organization_id == session_user.organization_id,
                SupplierTypeDocumentRequirement.status == RequirementStatus.ACTIVE,
                DocumentType.periodicity == Periodicity.MONTHLY,
            )
        ).first()
    return row[1] if row else None


def _add_document(db_session, session_user, supplier, doc_type, status="expired"):
    """Insert one document row for the given supplier/doc_type/period."""
    from repse.db.tenant_filter import set_current_tenant, with_admin_scope
    from repse.documents.models import Document, DocumentStatus, OcrStatus

    with with_admin_scope():
        set_current_tenant(session_user.organization_id)
        doc = Document(
            organization_id=session_user.organization_id,
            supplier_id=supplier.id,
            document_type_id=doc_type.id,
            coverage_period_start=_PAST_PERIOD,
            coverage_period_end=date(2026, 1, 31),
            due_date_calculated=date(2026, 2, 15),
            due_date_effective=date(2026, 2, 15),
            status=DocumentStatus(status),
            version=1,
            is_latest=True,
            file_path="dummy/path.pdf",
            file_name_original="doc.pdf",
            file_size_bytes=100,
            file_mime_type="application/pdf",
            file_sha256="c" * 64,
            ocr_status=OcrStatus.NOT_RUN,
            uploaded_by=session_user.id,
        )
        db_session.add(doc)
        db_session.commit()
    return doc


def _add_pending_submission(db_session, session_user, supplier, doc_type, status="pending", rejection_reason=None):
    """Insert one portal_submission row."""
    from repse.db.tenant_filter import set_current_tenant, with_admin_scope
    from repse.portal.models import PortalSubmission, PreSubmissionStatus, SubmissionStatus

    with with_admin_scope():
        set_current_tenant(session_user.organization_id)
        sub = PortalSubmission(
            organization_id=session_user.organization_id,
            supplier_id=supplier.id,
            document_type_id=doc_type.id,
            coverage_period_start=_PAST_PERIOD,
            submitted_at=datetime.now(timezone.utc).replace(tzinfo=None),
            submitted_by=session_user.id,
            status=SubmissionStatus(status),
            rejection_reason=rejection_reason,
            pre_submission_status=PreSubmissionStatus.MISSING,
        )
        db_session.add(sub)
        db_session.commit()
    return sub


# ---------------------------------------------------------------------------
# Negative tests — POST /portal/submit/{document_type_id}
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_submit_rejects_when_no_documents_uploaded(app, db_session, session_user):
    """No documents in cell → 409 no_documents_uploaded."""
    client, _, _ = _make_supplier_and_client(app, db_session, session_user)
    doc_type = _get_monthly_doc_type(db_session, session_user)
    assert doc_type is not None

    resp = client.post(
        f"/api/v1/portal/submit/{doc_type.id}",
        json={"coverage_period_start": _PAST_PERIOD.isoformat()},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["details"]["code"] == "no_documents_uploaded"


@pytest.mark.integration
def test_submit_rejects_when_already_submitted(app, db_session, session_user):
    """Pending submission already exists for cell → 409 already_submitted."""
    client, user, supplier = _make_supplier_and_client(app, db_session, session_user)
    doc_type = _get_monthly_doc_type(db_session, session_user)
    assert doc_type is not None

    _add_document(db_session, session_user, supplier, doc_type, status="expired")
    _add_pending_submission(db_session, session_user, supplier, doc_type, status="pending")

    resp = client.post(
        f"/api/v1/portal/submit/{doc_type.id}",
        json={"coverage_period_start": _PAST_PERIOD.isoformat()},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["details"]["code"] == "already_submitted"


@pytest.mark.integration
def test_submit_rejects_validated_cell(app, db_session, session_user):
    """Cell validated by accounting → 409 cell_not_submittable."""
    from repse.compliance.models import ComplianceCellValidation
    from repse.db.tenant_filter import set_current_tenant, with_admin_scope

    client, user, supplier = _make_supplier_and_client(app, db_session, session_user)
    doc_type = _get_monthly_doc_type(db_session, session_user)
    assert doc_type is not None

    _add_document(db_session, session_user, supplier, doc_type, status="valid")

    with with_admin_scope():
        set_current_tenant(session_user.organization_id)
        db_session.add(
            ComplianceCellValidation(
                organization_id=session_user.organization_id,
                supplier_id=supplier.id,
                document_type_id=doc_type.id,
                coverage_period_start=_PAST_PERIOD,
                validated_by=user.id,
                validated_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )
        db_session.commit()

    resp = client.post(
        f"/api/v1/portal/submit/{doc_type.id}",
        json={"coverage_period_start": _PAST_PERIOD.isoformat()},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["details"]["code"] == "cell_not_submittable"


@pytest.mark.integration
def test_submit_rejects_expiring_soon_cell(app, db_session, session_user):
    """Latest document is expiring_soon → 409 cell_not_submittable."""
    client, _, supplier = _make_supplier_and_client(app, db_session, session_user)
    doc_type = _get_monthly_doc_type(db_session, session_user)
    assert doc_type is not None

    _add_document(db_session, session_user, supplier, doc_type, status="expiring_soon")

    resp = client.post(
        f"/api/v1/portal/submit/{doc_type.id}",
        json={"coverage_period_start": _PAST_PERIOD.isoformat()},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["details"]["code"] == "cell_not_submittable"


# ---------------------------------------------------------------------------
# Positive test — POST /portal/submit/{document_type_id}
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_submit_ok_creates_submission(app, db_session, session_user):
    """Cell with documents in expired state → 201 SubmissionOut."""
    client, _, supplier = _make_supplier_and_client(app, db_session, session_user)
    doc_type = _get_monthly_doc_type(db_session, session_user)
    assert doc_type is not None

    _add_document(db_session, session_user, supplier, doc_type, status="expired")

    resp = client.post(
        f"/api/v1/portal/submit/{doc_type.id}",
        json={"coverage_period_start": _PAST_PERIOD.isoformat()},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["supplier_id"] == supplier.id
    assert body["document_type_id"] == doc_type.id
    assert body["status"] == "pending"
    assert "submission_id" in body
    assert "submitted_at" in body


# ---------------------------------------------------------------------------
# Tests — GET /portal/submission/{document_type_id}
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_get_submission_returns_null_when_no_submission(app, db_session, session_user):
    """No submission for cell → response is null."""
    client, _, _ = _make_supplier_and_client(app, db_session, session_user)
    doc_type = _get_monthly_doc_type(db_session, session_user)
    assert doc_type is not None

    resp = client.get(
        f"/api/v1/portal/submission/{doc_type.id}",
        params={"coverage_period_start": _PAST_PERIOD.isoformat()},
    )
    assert resp.status_code == 200
    assert resp.json() is None


@pytest.mark.integration
def test_get_submission_returns_rejection_reason(app, db_session, session_user):
    """Rejected submission → returns rejection_reason."""
    client, _, supplier = _make_supplier_and_client(app, db_session, session_user)
    doc_type = _get_monthly_doc_type(db_session, session_user)
    assert doc_type is not None

    _add_pending_submission(
        db_session,
        session_user,
        supplier,
        doc_type,
        status="rejected",
        rejection_reason="El RFC no coincide.",
    )

    resp = client.get(
        f"/api/v1/portal/submission/{doc_type.id}",
        params={"coverage_period_start": _PAST_PERIOD.isoformat()},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body is not None
    assert body["status"] == "rejected"
    assert body["rejection_reason"] == "El RFC no coincide."
