"""Document entity (uploaded compliance documents).

Includes the visible audit trail (Agregado/Actualizado/Validado) from FR-011a
spec 001 and the OCR best-effort fields from FR-008a/FR-009b.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    CHAR,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from repse.db.base import Base, TimestampMixin
from repse.db.tenant_filter import TenantOwned


class DocumentStatus(StrEnum):
    VALID = "valid"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED = "expired"
    # 'missing' is derived (not stored).


class OcrStatus(StrEnum):
    NOT_RUN = "not_run"
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class Document(Base, TimestampMixin, TenantOwned):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("organization_id", "file_sha256", name="uq_documents_org_sha256"),
        Index(
            "ix_documents_org_supplier_type_period",
            "organization_id", "supplier_id", "document_type_id", "coverage_period_start",
        ),
        Index("ix_documents_org_due", "organization_id", "due_date_effective"),
        Index("ix_documents_org_status", "organization_id", "status"),
        Index("ix_documents_org_last_updated", "organization_id", "last_updated_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    supplier_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False
    )
    document_type_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("document_types.id", ondelete="RESTRICT"), nullable=False
    )

    coverage_period_start: Mapped[date | None] = mapped_column(Date)
    coverage_period_end: Mapped[date | None] = mapped_column(Date)
    due_date_calculated: Mapped[date | None] = mapped_column(Date)
    due_date_effective: Mapped[date | None] = mapped_column(Date)
    due_date_override_reason: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, native_enum=False, length=20), nullable=False
    )

    # Manual validation (FR-012a spec 001).
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    verified_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL")
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    verified_note: Mapped[str | None] = mapped_column(String(500))

    # Versioning (FR-011 spec 001).
    version: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1")
    is_latest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    # Visible audit (FR-011a spec 001) — humans only.
    last_updated_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL")
    )
    last_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))

    # File metadata.
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_name_original: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_mime_type: Mapped[str] = mapped_column(String(127), nullable=False)
    file_sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)

    # OCR best-effort (FR-008a spec 001).
    ocr_status: Mapped[OcrStatus] = mapped_column(
        Enum(OcrStatus, native_enum=False, length=16),
        nullable=False,
        default=OcrStatus.NOT_RUN,
        server_default=OcrStatus.NOT_RUN.value,
    )
    ocr_extracted_rfc: Mapped[str | None] = mapped_column(String(13))
    ocr_extracted_issued_at: Mapped[date | None] = mapped_column(Date)
    ocr_extracted_valid_until: Mapped[date | None] = mapped_column(Date)
    ocr_raw_text: Mapped[str | None] = mapped_column(Text)

    uploaded_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
