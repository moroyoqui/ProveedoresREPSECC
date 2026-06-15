<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:

- Active feature plan: [specs/015-users-list-ux/plan.md](specs/015-users-list-ux/plan.md)
- Companion artifacts: [research.md](specs/015-users-list-ux/research.md), [data-model.md](specs/015-users-list-ux/data-model.md)
- Stack: Python 3.12 + FastAPI + SQLAlchemy 2.x + MySQL 8 (backend); React 18 + Vite + Tailwind + TanStack Query v5 (frontend); OAuth/OIDC via Authlib; local disk file storage; Tesseract OCR; Docker Compose on-prem with Caddy.
- New for 015: mejoras UX en la tabla de usuarios — eliminar columna "Último acceso", convertir botones de acción en íconos con tooltip, hacer el nombre clicable para abrir un panel de detalle de solo lectura. Solo frontend, sin cambios en el backend.
- Sibling feature specs (plans): [001 ready](specs/001-repse-compliance-tracker/plan.md), [003 ready](specs/003-document-catalog-admin/plan.md), [006 ready](specs/006-supplier-compliance-view/plan.md), [008 ready](specs/008-multi-upload-doc-viewer/plan.md), [009 ready](specs/009-proveedor-portal-viewer/plan.md), [010 ready](specs/010-sector-giro-catalog/plan.md), [011 ready](specs/011-supplier-contact-repse/plan.md), [012 ready](specs/012-uuid-file-storage/plan.md), [013 ready](specs/013-portal-upload-separation/plan.md), [014 ready](specs/014-user-supplier-assign/plan.md), [015 ready](specs/015-users-list-ux/plan.md). Pending: [002](specs/002-compliance-alerts/spec.md), [004](specs/004-compliance-reports/spec.md), [005](specs/005-compliance-dashboard/spec.md).
<!-- SPECKIT END -->

CLAUDE.md
Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.
Tradeoff: These guidelines bias toward caution over speed. For trivial tasks, use judgment.
1. Think Before Coding
Don't assume. Don't hide confusion. Surface tradeoffs.
Before implementing:
State your assumptions explicitly. If uncertain, ask.
If multiple interpretations exist, present them - don't pick silently.
If a simpler approach exists, say so. Push back when warranted.
If something is unclear, stop. Name what's confusing. Ask.
2. Simplicity First
Minimum code that solves the problem. Nothing speculative.
No features beyond what was asked.
No abstractions for single-use code.
No "flexibility" or "configurability" that wasn't requested.
No error handling for impossible scenarios.
If you write 200 lines and it could be 50, rewrite it.
Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.
3. Surgical Changes
Touch only what you must. Clean up only your own mess.
When editing existing code:
Don't "improve" adjacent code, comments, or formatting.
Don't refactor things that aren't broken.
Match existing style, even if you'd do it differently.
If you notice unrelated dead code, mention it - don't delete it.
When your changes create orphans:
Remove imports/variables/functions that YOUR changes made unused.
Don't remove pre-existing dead code unless asked.
The test: Every changed line should trace directly to the user's request.
4. Goal-Driven Execution
Define success criteria. Loop until verified.
Transform tasks into verifiable goals:
"Add validation" → "Write tests for invalid inputs, then make them pass"
"Fix the bug" → "Write a test that reproduces it, then make it pass"
"Refactor X" → "Ensure tests pass before and after"
For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```
Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.
---
These guidelines are working if: fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.