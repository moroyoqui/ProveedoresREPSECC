"""Unit tests for document status computation (no DB)."""

from datetime import date

import pytest

import repse.giros.models  # noqa: F401  — mapper config: Supplier.relationship("Giro")
import repse.sectors.models  # noqa: F401  — mapper config: Supplier.relationship("Sector")
from repse.documents.models import Document, DocumentStatus
from repse.documents.status import compute_status


def _doc(due_effective: date | None = None, due_calculated: date | None = None) -> Document:
    """Build a Document stub without touching the DB."""
    doc = Document(
        due_date_effective=due_effective,
        due_date_calculated=due_calculated,
    )
    return doc


@pytest.mark.parametrize(
    "due_effective, due_calculated, today, threshold, expected",
    [
        # Sin vencimiento -> Valid
        (None, None, date(2026, 5, 17), 15, DocumentStatus.VALID),
        # Override prevalece sobre calculado
        (date(2026, 5, 31), date(2026, 4, 30), date(2026, 5, 17), 15, DocumentStatus.EXPIRING_SOON),
        # Vencido
        (date(2026, 5, 1), None, date(2026, 5, 17), 15, DocumentStatus.EXPIRED),
        # Por vencer (≤ 15 días)
        (date(2026, 5, 20), None, date(2026, 5, 17), 15, DocumentStatus.EXPIRING_SOON),
        # Vigente (> 15 días)
        (date(2026, 6, 30), None, date(2026, 5, 17), 15, DocumentStatus.VALID),
        # Justo en el umbral inferior (15 días = expiring_soon)
        (date(2026, 6, 1), None, date(2026, 5, 17), 15, DocumentStatus.EXPIRING_SOON),
    ],
)
def test_compute_status(
    due_effective: date | None,
    due_calculated: date | None,
    today: date,
    threshold: int,
    expected: DocumentStatus,
) -> None:
    doc = _doc(due_effective=due_effective, due_calculated=due_calculated)
    assert compute_status(doc, today=today, expiring_soon_threshold_days=threshold) == expected
