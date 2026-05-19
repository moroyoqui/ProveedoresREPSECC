<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:

- Active feature plan: [specs/007-grid-refresh-color-legend/plan.md](specs/007-grid-refresh-color-legend/plan.md)
- Companion artifacts: [research.md](specs/007-grid-refresh-color-legend/research.md), [data-model.md](specs/007-grid-refresh-color-legend/data-model.md), [quickstart.md](specs/007-grid-refresh-color-legend/quickstart.md)
- Stack inherited from [spec 001](specs/001-repse-compliance-tracker/plan.md): Python 3.12 + FastAPI + SQLAlchemy 2.x + MySQL 8 (backend); React 18 + Vite + Tailwind (frontend); OAuth/OIDC via Authlib; local disk file storage; Tesseract OCR; Docker Compose on-prem with Caddy.
- New for 007: Refresco automático del ComplianceGrid al cerrar UploadDialog (invalidar clave ["supplier-compliance", supplierId] en React Query); leyenda de colores con 7 estados en recuadro con borde. Solo frontend, sin cambios de backend.
- Sibling feature specs (plans): [001 ready](specs/001-repse-compliance-tracker/plan.md), [003 ready](specs/003-document-catalog-admin/plan.md), [006 ready](specs/006-supplier-compliance-view/plan.md). Pending: [002](specs/002-compliance-alerts/spec.md), [004](specs/004-compliance-reports/spec.md), [005](specs/005-compliance-dashboard/spec.md).
<!-- SPECKIT END -->
