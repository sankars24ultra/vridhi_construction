# 6. Architecture and API Map

[Documentation home](README.md)

## Runtime architecture

```text
Browser
  React + TypeScript + Vite
  TanStack Query: loading/cache/mutations
  Session storage: workspace location, personal notes
  Local storage: preferred theme
        |
        | /api proxy in local development
        v
FastAPI /api/v1
  Session cookie + CSRF verification
  Project access + module/action authorization
  Pydantic request validation
  SQLAlchemy async transactions
        |                         |
        v                         v
PostgreSQL                  data/uploads
Business records            Original document/image bytes
Sessions and audit          Database stores file metadata
        |
        +--> data/logs: diagnostic JSONL, separate from audit_events
```

The backend binds locally through the launcher; Vite typically uses 5173 or 5174
and proxies to port 8000. Do not expose this development arrangement publicly
without configuring HTTPS, origin/cookie policy, service management and backups.

## Code map

| Area | Source |
|---|---|
| Navigation, session and selected project | [App.tsx](../../apps/frontend/src/App.tsx) |
| API client and DTO types | [api.ts](../../apps/frontend/src/lib/api.ts) |
| Screens | [features](../../apps/frontend/src/features/) |
| Shared export header | [ExportHeader.tsx](../../apps/frontend/src/components/ExportHeader.tsx) |
| Session notes | [SessionNotes.tsx](../../apps/frontend/src/components/SessionNotes.tsx) |
| App startup/router registration | [main.py](../../apps/backend/app/main.py) |
| Authentication and permission checks | [security.py](../../apps/backend/app/security.py) |
| SQLAlchemy mappings | [models.py](../../apps/backend/app/models.py) |
| Pydantic inputs/outputs | [schemas.py](../../apps/backend/app/schemas.py) |
| HTTP routes | [routes](../../apps/backend/app/api/routes/) |
| Business helpers and seed | [services](../../apps/backend/app/services/) |
| Schema evolution | [migrations](../../apps/backend/migrations/) |

## API families used by the application

All paths below are relative to `/api/v1`. This is a navigational summary, not
an exhaustive OpenAPI contract. Consult the running backend's `/docs` for exact
parameters, DTOs, status codes and operation availability.

| Family | Examples |
|---|---|
| Authentication | GET `/auth/bootstrap`; POST `/auth/login`; POST `/auth/logout`; GET `/me` |
| Projects | GET `/me/projects`; POST `/projects`; GET `/projects/{project_id}` |
| Overview | GET `/projects/{project_id}/dashboard` |
| Lifecycle | PATCH `/projects/{project_id}/status`; GET status-history |
| Project files/value | POST/GET documents; GET document file; GET value-history |
| Procurement | GET/POST purchase-orders; GET/PATCH specific order; POST/GET payments; GET procurement-summary |
| Inventory | GET inventory/summary/transactions; POST inventory transactions |
| Client money | GET cash-flow/billing-summary/progress-billings; POST progress-billings/cash-receipts |
| Labor | GET/POST workers, work-entries, payments, contracts; contract claims/addenda/decisions/files |
| User management | GET/POST `/users`; PUT `/users/{user_id}`; history/reset-password/status; DELETE account |
| Project audit | GET `/projects/{project_id}/audit-log`; POST `/projects/{project_id}/activities` |
| Diagnostics | GET `/health`, `/ready`; POST `/client-logs` |

Paths with "summary", "documents", etc. above are abbreviated family names, not
copy/paste URLs. Use the linked route files or OpenAPI for complete paths.

## Request lifecycle

1. Bootstrap obtains CSRF/session state; `/me` loads when authenticated.
2. Project listing supplies accessible projects and effective module profiles.
3. Navigation and action controls use the returned permissions.
4. API checks the session, project access and module/action independently.
5. Mutation validates data and business state; relevant operations use row locks,
   version checks or idempotency where implemented.
6. Business changes and audit records are committed; queries are refreshed.

Do not infer universal optimistic locking or idempotency from one endpoint:
coverage is endpoint-specific. For example, project status uses an expected
version; vendor payment code has idempotency handling.

## Authentication versus encryption

- User passwords: salted one-way Argon2id hashes.
- Session secret: signs CSRF values through itsdangerous.
- Session cookie: opaque random token; database stores a SHA-256 digest.
- Session cookie is HTTP-only; CSRF uses cookie/header validation.
- Database and upload bytes are not automatically encrypted by these mechanisms.
- Local HTTP has no transport encryption. HTTPS/TLS is a deployment responsibility.

## Export architecture

Reports are client-rendered with print CSS and the shared company header.
Audit Log and Procurement explicitly fetch multiple pages before printing;
other screens can print their rendered subsets. A browser print request cannot
prove that a PDF was saved. Notes and interactive navigation are print-hidden.

## Design versus implementation

The old prototype and original API proposal are not the live contract. In
particular, old role matrices, Attendance/Progress Billing menu names and planned
retention/scanning workflows should not be assumed to be current user-visible
features. See [evidence](09-evidence-and-acceptance.md).
