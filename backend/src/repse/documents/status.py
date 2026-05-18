"""Compute the visible status of a single Document.

'missing' is derived at query time, not stored on the row.
"""

from __future__ import annotations

from datetime import date

from repse.documents.models import Document, DocumentStatus


def compute_status(
    doc: Document, *, today: date, expiring_soon_threshold_days: int
) -> DocumentStatus:
    due = doc.due_date_effective or doc.due_date_calculated
    if due is None:
        return DocumentStatus.VALID
    if today > due:
        return DocumentStatus.EXPIRED
    if (due - today).days <= expiring_soon_threshold_days:
        return DocumentStatus.EXPIRING_SOON
    return DocumentStatus.VALID
