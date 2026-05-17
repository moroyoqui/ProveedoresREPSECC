# ProveedoresREPSECC Constitution

## Core Principles

### I. Secure by Default (NON-NEGOTIABLE)
All endpoints require authentication and authorization unless explicitly marked public; secrets must never be committed to the repository and are loaded from environment variables or a managed secret store; passwords are hashed with a modern algorithm (bcrypt/argon2); all traffic is served over HTTPS in any non-local environment; user input is validated and sanitized at every system boundary.

### II. Multi-Tenant Data Isolation
Every persisted record belongs to a tenant (organization/account); all queries are scoped by tenant identifier and enforced at the data-access layer, not only the UI; cross-tenant access is forbidden unless an explicit, audited admin path exists; tests must cover the negative case (tenant A cannot read tenant B).

### III. Test-First for Critical Paths
Authentication, authorization, billing, and tenant isolation logic must have automated tests before merge; bug fixes start with a failing regression test; the CI pipeline runs the test suite on every pull request and must pass before merge.


### IV. Simplicity and Iteration (YAGNI)
Start with the simplest design that satisfies the current requirement; do not add abstractions, services, or configurability for hypothetical future needs; prefer boring, well-supported technology over novel choices; any added complexity must be justified in the corresponding plan.md.

## Governance

This constitution supersedes ad-hoc practices. All pull requests and reviews must verify compliance with the principles above; deviations require an explicit PR justification. Amendments must bump the version and dates below and align related templates/checklists in this repo. Runtime development guidance lives in `CLAUDE.md`.

**Version**: 1.0.0 | **Ratified**: 2026-05-16 | **Last Amended**: 2026-05-16
