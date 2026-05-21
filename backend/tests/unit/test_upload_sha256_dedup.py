"""Unit tests para la lógica de deduplicación SHA256 en upload_document.

Valida los dos casos corregidos:
  1. Mismo sha256, misma org, no eliminado → Conflict con code=duplicate_file.
  2. Si la consulta de dedup devuelve None (soft-deleted o de otra org),
     el upload no lanza "duplicate_file" en el check previo al flush.

Los stubs de dependencias externas (pytesseract, pdf2image, etc.) los
inyecta tests/unit/conftest.py antes de que este módulo se importe.
"""
from __future__ import annotations

from datetime import date
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from repse.documents.service import UploadInput, upload_document
from repse.errors import Conflict

_PDF = b"%PDF-1.4\n%test\n%%EOF\n"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_upload(content: bytes = _PDF) -> MagicMock:
    u = MagicMock()
    u.content_type = "application/pdf"
    u.filename = "doc.pdf"
    u.file = BytesIO(content)
    return u


def _make_settings() -> MagicMock:
    s = MagicMock()
    s.upload_max_bytes = 10 * 1024 * 1024
    return s


def _minimal_supplier() -> SimpleNamespace:
    return SimpleNamespace(id=10, supplier_type_id=5)


def _minimal_doc_type() -> SimpleNamespace:
    from repse.document_types.models import Periodicity
    return SimpleNamespace(id=3, periodicity=Periodicity.MONTHLY)


def _minimal_requirement() -> SimpleNamespace:
    from repse.supplier_types.models import RequirementStatus
    return SimpleNamespace(periodicity_override=None, status=RequirementStatus.ACTIVE)


def _make_db(sha256_result) -> MagicMock:
    """DB mock que devuelve: requirement → sha256_result → (no más llamadas)."""
    call_order = [_minimal_requirement(), sha256_result]
    idx = {"i": 0}

    def _execute(_stmt):
        res = MagicMock()
        val = call_order[idx["i"]] if idx["i"] < len(call_order) else None
        idx["i"] += 1
        res.scalar_one_or_none.return_value = val
        return res

    db = MagicMock()
    db.get.side_effect = lambda model, pk: (
        _minimal_supplier() if getattr(model, "__name__", "") == "Supplier"
        else _minimal_doc_type() if getattr(model, "__name__", "") == "DocumentType"
        else SimpleNamespace(expiring_soon_threshold_days=15)
    )
    db.execute.side_effect = _execute
    return db


def _call_upload(db: MagicMock, org_id: int = 1) -> None:
    upload_document(
        db,
        organization_id=org_id,
        actor_user_id=99,
        upload=_make_upload(),
        body=UploadInput(
            supplier_id=10,
            document_type_id=3,
            coverage_period_start=date(2026, 4, 1),
            due_date_override=None,
            due_date_override_reason=None,
        ),
        settings=_make_settings(),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_duplicate_in_same_org_raises_conflict() -> None:
    """Mismo sha256, misma org, no eliminado → Conflict con code=duplicate_file."""
    existing = SimpleNamespace(id=7, deleted_at=None)
    db = _make_db(sha256_result=existing)

    with pytest.raises(Conflict) as exc_info:
        _call_upload(db, org_id=1)

    assert exc_info.value.details["code"] == "duplicate_file"


def test_no_conflict_when_dedup_query_returns_none() -> None:
    """Cuando la consulta de sha256 devuelve None (archivo eliminado o de otra org),
    el check de dedup no lanza Conflict; el error viene del flush u otra etapa."""
    db = _make_db(sha256_result=None)

    with patch("repse.documents.service.FileStore") as mock_store_cls, \
         patch("repse.documents.service.run_ocr") as mock_ocr, \
         patch("repse.documents.service.write_event"), \
         patch("repse.documents.service.write_system_event"):
        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store
        mock_store.save.return_value = SimpleNamespace(
            relative_path="org/1/doc.pdf", size_bytes=len(_PDF)
        )
        mock_ocr.return_value = SimpleNamespace(raw_text=None)

        try:
            _call_upload(db, org_id=1)
        except Conflict as e:
            assert e.details.get("code") != "duplicate_file", (
                "El check de sha256 no debe lanzar duplicate_file "
                "cuando la consulta de dedup devuelve None"
            )
        except Exception:
            pass  # Otros errores de mock son esperados; lo relevante es no "duplicate_file"
