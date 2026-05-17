<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:

- Active feature plan: [specs/003-document-catalog-admin/plan.md](specs/003-document-catalog-admin/plan.md)
- Companion artifacts: [research.md](specs/003-document-catalog-admin/research.md), [data-model.md](specs/003-document-catalog-admin/data-model.md), [contracts/](specs/003-document-catalog-admin/contracts/), [quickstart.md](specs/003-document-catalog-admin/quickstart.md)
- Stack inherited from [spec 001](specs/001-repse-compliance-tracker/plan.md): Python 3.12 + FastAPI + SQLAlchemy 2.x + MySQL 8 (backend); React 18 + Vite + Tailwind (frontend); OAuth/OIDC via Authlib; local disk file storage; Tesseract OCR; Docker Compose on-prem with Caddy.
- New for 003: optimistic concurrency via `If-Match`, async recalculation of compliance via FastAPI BackgroundTask, system type "Sin clasificar" immutable. Industry-template wizard removed from scope (2026-05-17) and postponed.
- Sibling feature specs (plans): [001 ready](specs/001-repse-compliance-tracker/plan.md), [002 ready](specs/002-compliance-alerts/plan.md). Pending: [004-compliance-reports](specs/004-compliance-reports/spec.md), [005-compliance-dashboard](specs/005-compliance-dashboard/spec.md).
<!-- SPECKIT END -->
