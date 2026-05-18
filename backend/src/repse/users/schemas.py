"""Schemas for User (contracts/users.md spec 001)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from repse.users.models import Role, UserStatus


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    display_name: str
    role: Role
    status: UserStatus
    last_login_at: datetime | None = None


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(..., min_length=1, max_length=255)
    role: Role


class UserPatch(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=255)
    role: Role | None = None
    status: UserStatus | None = None
