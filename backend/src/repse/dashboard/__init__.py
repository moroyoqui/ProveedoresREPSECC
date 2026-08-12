"""Tenant-aggregated compliance dashboard (spec 005).

Read-only module: aggregates compliance state across all suppliers of a tenant
reusing the document status logic from ``documents.status`` and the requirement
rules from ``compliance``. Exposes a single endpoint
``GET /api/v1/dashboard/compliance`` with an in-process 60s cache invalidated by
a per-tenant version counter.
"""
