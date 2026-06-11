<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:

- Active feature plan: [specs/012-uuid-file-storage/plan.md](specs/012-uuid-file-storage/plan.md)
- Companion artifacts: [research.md](specs/012-uuid-file-storage/research.md), [data-model.md](specs/012-uuid-file-storage/data-model.md)
- Stack: Python 3.12 + FastAPI + SQLAlchemy 2.x + MySQL 8 (backend); React 18 + Vite + Tailwind + TanStack Query v5 (frontend); OAuth/OIDC via Authlib; local disk file storage; Tesseract OCR; Docker Compose on-prem with Caddy.
- New for 012: UUID4 suffix en nombre de archivo almacenado en disco. Cambio de 1 línea en `FileStore.save()` (`storage.py`). Sin migración de BD ni de archivos existentes.
- Sibling feature specs (plans): [001 ready](specs/001-repse-compliance-tracker/plan.md), [003 ready](specs/003-document-catalog-admin/plan.md), [006 ready](specs/006-supplier-compliance-view/plan.md), [008 ready](specs/008-multi-upload-doc-viewer/plan.md), [009 ready](specs/009-proveedor-portal-viewer/plan.md), [010 ready](specs/010-sector-giro-catalog/plan.md), [011 ready](specs/011-supplier-contact-repse/plan.md). Pending: [002](specs/002-compliance-alerts/spec.md), [004](specs/004-compliance-reports/spec.md), [005](specs/005-compliance-dashboard/spec.md).
<!-- SPECKIT END -->
