"""Schemas for Organization (contracts/organizations.md spec 001)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from repse.organizations.models import OrgStatus


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    legal_name: str
    rfc: str
    contact_email: EmailStr
    expiring_soon_threshold_days: int
    timezone: str
    status: OrgStatus


class OrganizationPatch(BaseModel):
    legal_name: str | None = Field(None, min_length=2, max_length=255)
    contact_email: EmailStr | None = None
    expiring_soon_threshold_days: int | None = Field(None, ge=1, le=90)
    timezone: str | None = Field(None, max_length=64)
