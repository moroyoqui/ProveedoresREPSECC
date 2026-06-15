"""Schemas for User (contracts/users.md spec 001)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from repse.users.models import Role, UserStatus


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    display_name: str
    role: Role
    status: UserStatus
    supplier_id: int | None = None
    supplier_name: str | None = None
    last_login_at: datetime | None = None


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(..., min_length=1, max_length=255)
    role: Role
    password: str | None = Field(None, min_length=8, max_length=128)
    supplier_id: int | None = None

    @model_validator(mode="after")
    def _supplier_required_for_supplier_role(self) -> "UserCreate":
        if self.role == Role.SUPPLIER and self.supplier_id is None:
            raise ValueError("supplier_id is required when role is 'supplier'")
        if self.role != Role.SUPPLIER and self.supplier_id is not None:
            raise ValueError("supplier_id must be null for non-supplier roles")
        return self


class UserPatch(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=255)
    role: Role | None = None
    status: UserStatus | None = None
    password: str | None = Field(None, min_length=8, max_length=128)
    supplier_id: int | None = None
