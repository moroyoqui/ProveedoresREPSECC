<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:

- Active feature plan: [specs/002-compliance-alerts/plan.md](specs/002-compliance-alerts/plan.md)
- Companion artifacts: [research.md](specs/002-compliance-alerts/research.md), [data-model.md](specs/002-compliance-alerts/data-model.md), [contracts/](specs/002-compliance-alerts/contracts/), [quickstart.md](specs/002-compliance-alerts/quickstart.md)
- Stack inherited from [spec 001](specs/001-repse-compliance-tracker/plan.md): Python 3.12 + FastAPI + SQLAlchemy 2.x + MySQL 8 (backend); React 18 + Vite + Tailwind (frontend); OAuth/OIDC via Authlib; local disk file storage; Tesseract OCR; Docker Compose on-prem with Caddy.
- New for 002: APScheduler in-process daily run, aiosmtplib for SMTP (provider-agnostic), Jinja2 email templates, in-app notifications via DB polling, tenacity for retries, idempotency via DB unique constraint.
- Sibling feature specs (drafted, plans pending): [003-document-catalog-admin](specs/003-document-catalog-admin/spec.md), [004-compliance-reports](specs/004-compliance-reports/spec.md), [005-compliance-dashboard](specs/005-compliance-dashboard/spec.md).
<!-- SPECKIT END -->
