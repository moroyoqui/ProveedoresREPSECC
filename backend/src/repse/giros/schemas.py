"""Pydantic schemas for the Giro catalog."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GiroIn(BaseModel):
    sector_id: int
    name: str = Field(..., min_length=2, max_length=120)


class GiroPatch(BaseModel):
    sector_id: int | None = None
    name: str | None = Field(None, min_length=2, max_length=120)


class GiroBrief(BaseModel):
    id: int
    name: str


class GiroOut(BaseModel):
    id: int
    sector_id: int
    sector_name: str
    name: str
