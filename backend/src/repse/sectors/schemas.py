"""Pydantic schemas for the Sector catalog."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SectorIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)


class SectorOut(BaseModel):
    id: int
    name: str
