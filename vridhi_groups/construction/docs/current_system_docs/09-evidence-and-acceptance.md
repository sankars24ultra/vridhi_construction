# 9. Evidence, Boundaries and Acceptance Checklist

[Documentation home](README.md)

## How this edition was prepared

Reviewed current frontend screens/components, API routes, permission resolver,
database models, configuration, startup and audit/report handlers on 16 October
2026. The original documents were read for structure and historical context,
not treated as proof that a feature is missing.

This task creates documentation and a presentation. It does not run an end-to-end
operational test of every feature or certify financial/security correctness.
Prior conversation test counts are not presented here as a fresh test result.

## Primary evidence

| Topic | Current source |
|---|---|
| Menus and top bar | [App.tsx](../../apps/frontend/src/App.tsx) |
| Project form, status and plans | [Overview.tsx](../../apps/frontend/src/features/projects/Overview.tsx), [projects.py](../../apps/backend/app/api/routes/projects.py) |
| Procurement | [Procurement.tsx](../../apps/frontend/src/features/procurement/Procurement.tsx), [procurement.py](../../apps/backend/app/api/routes/procurement.py) |
| Inventory | [Inventory.tsx](../../apps/frontend/src/features/inventory/Inventory.tsx), same procurement route module |
| Cash flow | [CashFlow.tsx](../../apps/frontend/src/features/billing/CashFlow.tsx), [operations.py](../../apps/backend/app/api/routes/operations.py) |
| Labor | [LaborWages.tsx](../../apps/frontend/src/features/labor/LaborWages.tsx), [labor.py](../../apps/backend/app/api/routes/labor.py) |
| Accounts | [UsersView.tsx](../../apps/frontend/src/features/admin/UsersView.tsx), [admin.py](../../apps/backend/app/api/routes/admin.py) |
| Permissions | [security.py](../../apps/backend/app/security.py) |
| Audit and time filters | [AuditLog.tsx](../../apps/frontend/src/features/admin/AuditLog.tsx), [AuditDateRange.tsx](../../apps/frontend/src/components/AuditDateRange.tsx), [audit.py](../../apps/backend/app/api/routes/audit.py) |
| Reports | [ExportHeader.tsx](../../apps/frontend/src/components/ExportHeader.tsx), [App.css](../../apps/frontend/src/App.css), module export handlers |
| Notes | [SessionNotes.tsx](../../apps/frontend/src/components/SessionNotes.tsx) |
| Storage/schema | [models.py](../../apps/backend/app/models.py), [config.py](../../apps/backend/app/core/config.py) |

## Boundaries to communicate honestly

- Current permissions are not the initial prototype's role matrix.
- Audit records are available, but a complete snapshot is not populated for every
  business action or legacy record.
- A visit is a tracked module navigation, not every API request or every click.
- Export completion cannot be proven by browser print events.
- Audit/Procurement full-row preparation must not be generalized to all reports.
- Retention figures are placeholders in the present cash summary, not a complete
  retention-release business workflow.
- Current value revisions update the project estimate; do not teach them as a
  separate approved change-order engine.
- Client data, uploaded files and operational backups are not automatically
  encrypted by password hashing.
- The shared report header still has a company-address placeholder.
- Current records and sample data are not an audited financial baseline.

These are scope notes observed during source review, not permission to silently
change behavior and not a new claim that the entire original plan is unfinished.

## Suggested acceptance scenarios

Run against a safe test database with known fixtures:

1. Fresh database: migrations, seed administrator, private bootstrap credential,
   normal sign-in, then change/reset password appropriately.
2. Users-only account: no projects/global access, directory reachable, each
   lifecycle grant enforced independently.
3. Project-only account: only assigned projects; blocked modules unavailable in UI/API.
4. Shared selected projects: one profile on checked projects; no unintended assignment.
5. Global with override: overridden module restrictions hold on the selected project.
6. Status transitions: allowed/denied next states, required comment/confirmation,
   stale-version conflict.
7. PO create/edit/pay: combined create/edit permission, separate payment permission,
   balance checks and duplicate-submission handling where implemented.
8. Stock: receipt/use unit handling, insufficient quantity and ledger trace.
9. Client receipts: allocation limits, unallocated receipts and summary reconciliation.
10. Labor: direct earnings/payments, certified claims, changes and downloads.
11. Audit: correct project scope, readable activity, newest order, pagination,
    local time range and export scope.
12. Report preview: every menu, white output in Dark mode, company header,
    pagination/filter coverage, restricted overview sections empty.
13. Notes: navigation/refresh, resize, account isolation, sign-out cleanup,
    print exclusion.
14. Mobile: workspace selector does not cover menus; menus/tables scroll and
    popovers/dialogs remain usable.
15. Restore: recover database plus uploads and open known linked documents.

Record actual outcomes and evidence before estimating production completion.
