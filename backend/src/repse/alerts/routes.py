"""Alerts API router (T017).

Mounted at /api/v1/alerts behind the back-office audience guard. Endpoints
(config, trigger-now) are added in the US phases; the notifications and silence
endpoints live on their own routers (US1/US2).
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()
