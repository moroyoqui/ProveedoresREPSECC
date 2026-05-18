"""User entity (members of an organization)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, Enum, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from repse.db.base import Base, TimestampMixin
from repse.db.tenant_filter import TenantOwned


class Role(StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    VIEWER = "viewer"


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class OidcProvider(StrEnum):
    GOOGLE = "google"
    MICROSOFT = "microsoft"


class User(Base, TimestampMixin, TenantOwned):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_users_email"),
        UniqueConstraint("oidc_provider", "oidc_subject", name="uq_users_oidc"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    oidc_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    oidc_provider: Mapped[OidcProvider | None] = mapped_column(
        Enum(OidcProvider, native_enum=False, length=16), nullable=True
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False, length=16), nullable=False)
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, native_enum=False, length=16),
        nullable=False,
        default=UserStatus.ACTIVE,
        server_default=UserStatus.ACTIVE.value,
    )
    last_login_at: Mapped[datetime | None]
