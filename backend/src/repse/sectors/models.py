"""Sector — global reference catalog (no TenantOwned; see research.md Decisión 1)."""

from __future__ import annotations

from sqlalchemy import BigInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from repse.db.base import Base, TimestampMixin


class Sector(Base, TimestampMixin):
    __tablename__ = "sectors"
    __table_args__ = (UniqueConstraint("name", name="uq_sectors_name"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
