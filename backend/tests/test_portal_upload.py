"""Integration tests for POST /api/v1/portal/upload (US5 — T030).

Negative cases must fail until T031 is implemented.
Positive case verifies the happy path once T031 is complete.
"""
from __future__ import annotations

import io
import os
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Module-level fixtures (small-upload variant of the app)
# ---------------------------------------------------------------------------


@pytest.fixture()
def app_small_upload(engine, connection, monkeypatch):
    """App fixture with upload_max_bytes=1 for the file_too_large test."""
    from repse import config as cfg_mod

    # Capture the original function BEFORE the monkeypatch so the dependency
    # override below is keyed by the exact callable the routes captured at
    # import time.
    real_get_settings = cfg_mod.get_settings

    settings = cfg_mod.Settings(
        app_secret="x" * 32,
        db_pass="x",
        app_base_url="http://testserver",
        upload_root=os.path.abspath("./var/test-uploads"),
        upload_max_bytes=1,
    )
    monkeypatch.setattr(cfg_mod, "get_settings", lambda: settings)

    from repse.db import session as db_session_mod
    from sqlalchemy.orm import sessionmaker

    db_session_mod._engine = engine
    db_session_mod._SessionLocal = sessionmaker(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    from repse.main import app

    # Depends(get_settings) captured the original function at import time, so
    # monkeypatching the module attribute is not enough for route dependencies.
    app.dependency_overrides[real_get_settings] = lambda: settings
    yield app
    app.dependency_overrides.pop(real_get_settings, None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_supplier_and_client(app, db_session, session_user):
    """Create a supplier + supplier-role user; return (client, user, supplier)."""
    from fastapi.testclient import TestClient
    from sqlalchemy import select

    from repse.auth.session import SessionManager, fresh_expiry
    from repse.config import get_settings
    from repse.db.tenant_filter import set_current_tenant, with_admin_scope
    from repse.suppliers.models import Supplier, SupplierStatus
    from repse.supplier_types.models import SupplierType, SupplierTypeOrigin
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
            legal_name="Proveedor Upload Test",
            rfc="PUT9901011Y3",
            contact_email="upload@put.mx",
            status=SupplierStatus.ACTIVE,
        )
        db_session.add(supplier)
        db_session.flush()
        user = User(
            organization_id=session_user.organization_id,
            email="sup-upload@put.mx",
            display_name="Supplier Upload",
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
    """Return the first active monthly document type for the session org's system supplier type."""
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
                SupplierTypeDocumentRequirement.organization_id
                == session_user.organization_id,
                SupplierTypeDocumentRequirement.status == RequirementStatus.ACTIVE,
                DocumentType.periodicity == Periodicity.MONTHLY,
            )
        ).first()
    return row[1] if row else None


_PAST_PERIOD = date(2026, 1, 1)  # January 2026 — well before May 2026 (today)
_VALID_PDF = b"%PDF-1.4 tiny"

# ---------------------------------------------------------------------------
# Negative tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_upload_rejects_future_period(app, db_session, session_user):
    """coverage_period_start in the future → 422 future_period."""
    client, _, _ = _make_supplier_and_client(app, db_session, session_user)
    doc_type = _get_monthly_doc_type(db_session, session_user)
    assert doc_type is not None

    today = date.today()
    next_month = date(today.year + 1, 1, 1) if today.month == 12 else date(today.year, today.month + 1, 1)
    resp = client.post(
        "/api/v1/portal/upload",
        files={"file": ("test.pdf", io.BytesIO(_VALID_PDF), "application/pdf")},
        data={
            "document_type_id": str(doc_type.id),
            "coverage_period_start": next_month.isoformat(),
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["details"]["code"] == "future_period"


@pytest.mark.integration
def test_upload_rejects_submitted_cell(app, db_session, session_user):
    """Cell with a pending portal_submission → 409 upload_not_allowed."""
    from repse.db.tenant_filter import set_current_tenant, with_admin_scope
    from repse.portal.models import PortalSubmission, PreSubmissionStatus, SubmissionStatus

    client, user, supplier = _make_supplier_and_client(app, db_session, session_user)
    doc_type = _get_monthly_doc_type(db_session, session_user)
    assert doc_type is not None

    with with_admin_scope():
        set_current_tenant(session_user.organization_id)
        db_session.add(
            PortalSubmission(
                organization_id=session_user.organization_id,
                supplier_id=supplier.id,
                document_type_id=doc_type.id,
                coverage_period_start=_PAST_PERIOD,
                submitted_at=datetime.now(timezone.utc).replace(tzinfo=None),
                submitted_by=user.id,
                status=SubmissionStatus.PENDING,
                pre_submission_status=PreSubmissionStatus.MISSING,
            )
        )
        db_session.commit()

    resp = client.post(
        "/api/v1/portal/upload",
        files={"file": ("test.pdf", io.BytesIO(_VALID_PDF), "application/pdf")},
        data={
            "document_type_id": str(doc_type.id),
            "coverage_period_start": _PAST_PERIOD.isoformat(),
        },
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["details"]["code"] == "upload_not_allowed"


@pytest.mark.integration
def test_upload_rejects_validated_cell(app, db_session, session_user):
    """Cell with a ComplianceCellValidation → 409 upload_not_allowed."""
    from repse.compliance.models import ComplianceCellValidation
    from repse.db.tenant_filter import set_current_tenant, with_admin_scope

    client, user, supplier = _make_supplier_and_client(app, db_session, session_user)
    doc_type = _get_monthly_doc_type(db_session, session_user)
    assert doc_type is not None

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
        "/api/v1/portal/upload",
        files={"file": ("test.pdf", io.BytesIO(_VALID_PDF), "application/pdf")},
        data={
            "document_type_id": str(doc_type.id),
            "coverage_period_start": _PAST_PERIOD.isoformat(),
        },
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["details"]["code"] == "upload_not_allowed"


@pytest.mark.integration
def test_upload_rejects_expiring_soon_cell(app, db_session, session_user):
    """Latest document has status=expiring_soon → 409 upload_not_allowed."""
    from repse.db.tenant_filter import set_current_tenant, with_admin_scope
    from repse.documents.models import Document, DocumentStatus, OcrStatus

    client, user, supplier = _make_supplier_and_client(app, db_session, session_user)
    doc_type = _get_monthly_doc_type(db_session, session_user)
    assert doc_type is not None

    with with_admin_scope():
        set_current_tenant(session_user.organization_id)
        db_session.add(
            Document(
                organization_id=session_user.organization_id,
                supplier_id=supplier.id,
                document_type_id=doc_type.id,
                coverage_period_start=_PAST_PERIOD,
                coverage_period_end=date(2026, 1, 31),
                due_date_calculated=date(2026, 2, 15),
                due_date_effective=date(2026, 2, 15),
                status=DocumentStatus.EXPIRING_SOON,
                version=1,
                is_latest=True,
                file_path="dummy/path.pdf",
                file_name_original="doc.pdf",
                file_size_bytes=100,
                file_mime_type="application/pdf",
                file_sha256="a" * 64,
                ocr_status=OcrStatus.NOT_RUN,
                uploaded_by=user.id,
            )
        )
        db_session.commit()

    resp = client.post(
        "/api/v1/portal/upload",
        files={"file": ("test.pdf", io.BytesIO(_VALID_PDF), "application/pdf")},
        data={
            "document_type_id": str(doc_type.id),
            "coverage_period_start": _PAST_PERIOD.isoformat(),
        },
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["details"]["code"] == "upload_not_allowed"


@pytest.mark.integration
def test_upload_rejects_when_max_files_reached(app, db_session, session_user):
    """Document count at the per-cell limit → 409 max_files_reached."""
    from repse.db.tenant_filter import set_current_tenant, with_admin_scope
    from repse.documents.models import Document, DocumentStatus, OcrStatus
    from repse.portal.routes_write import _MAX_FILES_PER_CELL

    client, user, supplier = _make_supplier_and_client(app, db_session, session_user)
    doc_type = _get_monthly_doc_type(db_session, session_user)
    assert doc_type is not None

    with with_admin_scope():
        set_current_tenant(session_user.organization_id)
        for i in range(_MAX_FILES_PER_CELL):
            db_session.add(
                Document(
                    organization_id=session_user.organization_id,
                    supplier_id=supplier.id,
                    document_type_id=doc_type.id,
                    coverage_period_start=_PAST_PERIOD,
                    coverage_period_end=date(2026, 1, 31),
                    due_date_calculated=date(2026, 2, 15),
                    due_date_effective=date(2026, 2, 15),
                    status=DocumentStatus.EXPIRED,
                    version=i + 1,
                    is_latest=(i == _MAX_FILES_PER_CELL - 1),
                    file_path=f"dummy/path-{i}.pdf",
                    file_name_original=f"doc-{i}.pdf",
                    file_size_bytes=100,
                    file_mime_type="application/pdf",
                    file_sha256=("b" * 63 + str(i % 10)),
                    ocr_status=OcrStatus.NOT_RUN,
                    uploaded_by=user.id,
                )
            )
        db_session.commit()

    resp = client.post(
        "/api/v1/portal/upload",
        files={"file": ("test.pdf", io.BytesIO(_VALID_PDF), "application/pdf")},
        data={
            "document_type_id": str(doc_type.id),
            "coverage_period_start": _PAST_PERIOD.isoformat(),
        },
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["details"]["code"] == "max_files_reached"


@pytest.mark.integration
def test_upload_rejects_invalid_file_type(app, db_session, session_user):
    """File with unsupported MIME type → 422 invalid_file_type."""
    client, _, _ = _make_supplier_and_client(app, db_session, session_user)
    doc_type = _get_monthly_doc_type(db_session, session_user)
    assert doc_type is not None

    resp = client.post(
        "/api/v1/portal/upload",
        files={"file": ("script.sh", io.BytesIO(b"#!/bin/bash"), "text/plain")},
        data={
            "document_type_id": str(doc_type.id),
            "coverage_period_start": _PAST_PERIOD.isoformat(),
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["details"]["code"] == "invalid_file_type"


@pytest.mark.integration
def test_upload_rejects_oversized_file(app_small_upload, db_session, session_user):
    """File exceeding upload_max_bytes → 422 file_too_large."""
    client, _, _ = _make_supplier_and_client(app_small_upload, db_session, session_user)
    doc_type = _get_monthly_doc_type(db_session, session_user)
    assert doc_type is not None

    resp = client.post(
        "/api/v1/portal/upload",
        files={"file": ("test.pdf", io.BytesIO(b"AB"), "application/pdf")},
        data={
            "document_type_id": str(doc_type.id),
            "coverage_period_start": _PAST_PERIOD.isoformat(),
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["details"]["code"] == "file_too_large"


# ---------------------------------------------------------------------------
# Positive test
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_upload_ok_missing_cell(app, db_session, session_user):
    """Missing cell + valid PDF → 201 UploadOut."""
    from repse.documents.models import DocumentStatus

    client, _, supplier = _make_supplier_and_client(app, db_session, session_user)
    doc_type = _get_monthly_doc_type(db_session, session_user)
    assert doc_type is not None

    fake_doc = SimpleNamespace(
        id=9001,
        document_type_id=doc_type.id,
        coverage_period_start=_PAST_PERIOD,
        coverage_period_end=date(2026, 1, 31),
        status=DocumentStatus.EXPIRED,
        file_name_original="test.pdf",
        file_size_bytes=len(_VALID_PDF),
        version=1,
        created_at=datetime(2026, 1, 20, 10, 0, 0),
    )

    with patch("repse.portal.routes_write.upload_document", return_value=fake_doc):
        resp = client.post(
            "/api/v1/portal/upload",
            files={"file": ("test.pdf", io.BytesIO(_VALID_PDF), "application/pdf")},
            data={
                "document_type_id": str(doc_type.id),
                "coverage_period_start": _PAST_PERIOD.isoformat(),
            },
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == 9001
    assert body["document_type_id"] == doc_type.id
    assert body["version"] == 1
    assert body["file_name_original"] == "test.pdf"
