"""Compliance cell validation entity (US6 spec 008).

Stores explicit, type-level validations made by a supervisor from the document
viewer. A row in this table means a supervisor formally approved the full set of
documents for a given supplier / document-type / period combination.

This is distinct from ``documents.verified`` which tracks individual-file
authentication by an admin or supervisor.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from repse.db.base import Base, TimestampMixin
from repse.db.tenant_filter import TenantOwned


class ComplianceCellValidation(Base, TimestampMixin, TenantOwned):
    """OBSOLETA desde spec 017 — no leer ni escribir.

    El estado "validado" de una celda dejó de vivir aquí: ahora se deriva del
    documento vigente (`documents.verified`), que es la única fuente de verdad.
    La migración 0013 trasladó el contenido aprovechable y la tabla quedó inerte
    como red de seguridad; su retirada definitiva es una migración posterior.

    Si necesitas saber si una celda está validada, mira su documento vigente.
    """

    __tablename__ = "compliance_cell_validations"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "supplier_id",
            "document_type_id",
            "coverage_period_start",
            name="uq_cell_validation",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    supplier_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False
    )
    document_type_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("document_types.id", ondelete="RESTRICT"), nullable=False
    )
    coverage_period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    validated_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    validated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
