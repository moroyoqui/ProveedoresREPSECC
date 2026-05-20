<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:

- Active feature plan: [specs/009-proveedor-portal-viewer/plan.md](specs/009-proveedor-portal-viewer/plan.md)
- Companion artifacts: [research.md](specs/009-proveedor-portal-viewer/research.md), [data-model.md](specs/009-proveedor-portal-viewer/data-model.md), [contracts/portal-compliance.md](specs/009-proveedor-portal-viewer/contracts/portal-compliance.md)
- Stack: Python 3.12 + FastAPI + SQLAlchemy 2.x + MySQL 8 (backend); React 18 + Vite + Tailwind + TanStack Query v5 (frontend); OAuth/OIDC via Authlib; local disk file storage; Tesseract OCR; Docker Compose on-prem with Caddy.
- New for 009: Rol `supplier` en el User model + FK `users.supplier_id → suppliers.id`; SessionPayload extendido con `supplier_id`; nuevo módulo `repse/portal/` con `GET /api/v1/portal/compliance`; frontend: PortalPage, redirección por rol, nav mínima para proveedores, selector de empresa en CreateUserDialog.
- Sibling feature specs (plans): [001 ready](specs/001-repse-compliance-tracker/plan.md), [003 ready](specs/003-document-catalog-admin/plan.md), [006 ready](specs/006-supplier-compliance-view/plan.md), [008 ready](specs/008-multi-upload-doc-viewer/plan.md). Pending: [002](specs/002-compliance-alerts/spec.md), [004](specs/004-compliance-reports/spec.md), [005](specs/005-compliance-dashboard/spec.md).
<!-- SPECKIT END -->
