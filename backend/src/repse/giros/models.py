"""Giro — global reference catalog linked to a Sector (no TenantOwned)."""

from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from repse.db.base import Base, TimestampMixin


class Giro(Base, TimestampMixin):
    __tablename__ = "giros"
    __table_args__ = (
        UniqueConstraint("sector_id", "name", name="uq_giros_sector_name"),
        Index("ix_giros_sector_id", "sector_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sector_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("sectors.id", ondelete="RESTRICT", name="fk_giros_sector_id_sectors"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
