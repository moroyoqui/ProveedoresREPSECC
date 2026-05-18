<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:

- Active feature plan: [specs/006-supplier-compliance-view/plan.md](specs/006-supplier-compliance-view/plan.md)
- Companion artifacts: [research.md](specs/006-supplier-compliance-view/research.md), [data-model.md](specs/006-supplier-compliance-view/data-model.md), [contracts/](specs/006-supplier-compliance-view/contracts/), [quickstart.md](specs/006-supplier-compliance-view/quickstart.md)
- Stack inherited from [spec 001](specs/001-repse-compliance-tracker/plan.md): Python 3.12 + FastAPI + SQLAlchemy 2.x + MySQL 8 (backend); React 18 + Vite + Tailwind (frontend); OAuth/OIDC via Authlib; local disk file storage; Tesseract OCR; Docker Compose on-prem with Caddy.
- New for 006: endpoint GET /api/v1/suppliers/{id}/compliance?year=YYYY; módulo backend compliance/; componentes React ComplianceGrid + ComplianceCell; siete estados de celda (validated/submitted/expired/missing/pending/future/not_required); sección separada para documentos sin periodicidad (none). Sin nuevas tablas ni dependencias.
- Sibling feature specs (plans): [001 ready](specs/001-repse-compliance-tracker/plan.md), [003 ready](specs/003-document-catalog-admin/plan.md). Pending: [002](specs/002-compliance-alerts/spec.md), [004](specs/004-compliance-reports/spec.md), [005](specs/005-compliance-dashboard/spec.md).
<!-- SPECKIT END -->
