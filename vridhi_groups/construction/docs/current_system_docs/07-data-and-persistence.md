# 7. Data Model and Persistence

[Documentation home](README.md)

## Main relationships

```text
User -- ProjectMembership -- Project
  |                           |
  +-- AuthSession             +-- Contract (client value)
  +-- Users/Audit profiles     +-- ProjectStatusHistory
                              +-- ProjectDocument / ProjectValueHistory
                              +-- PurchaseOrder -- Lines / Vendor payments
                              +-- ProjectInventoryItem / InventoryTransaction
                              +-- BillingEntry -- CashReceipt allocation
                              +-- LaborWorker -- WorkEntry / WagePayment
                              +-- LaborContract -- Addendum / Claim -- Payment

AuditEvent --> actor, entity type/ID, project ID, details, timestamp
```

## Record families

| Tables / models | Purpose |
|---|---|
| users | Identity, contact, password hash, global/Users/audit profiles, active/deleted status |
| auth_sessions | Token digests, expiry and revocation |
| project_memberships | Unique project/user links with permission JSON |
| projects | Name, location, lifecycle, budget, dates, version |
| contracts | Client contract value used in project summaries |
| project_status_history | Previous/new state, comment, actor, timestamp |
| project_documents | Original name, storage name, type, size, uploader, category/comment |
| project_value_history | Value revisions linked to plans and actors |
| vendors, inventory_items, cost_codes | Shared reference/catalog information |
| purchase_orders, purchase_order_lines | Ordered quantities and prices |
| purchase_order_payments | Vendor installments |
| project_inventory_items, inventory_transactions | Project material registration and movement |
| billing_entries, cash_receipts | Client billings and optional receipt allocations |
| labor_workers, labor_work_entries, labor_wage_payments | Direct labor earnings and payments |
| labor_contracts, labor_contract_documents | Subcontract agreements and supporting files |
| labor_contract_addenda | Proposed/decided contract changes |
| labor_progress_claims, labor_contract_payments | Claim certification and payment history |
| audit_events | Project/account activity and optional change details |
| idempotency_records | Retained request/result data for implemented duplicate protection |

Legacy RBAC tables and timecards also remain in the schema. Their presence does
not mean the UI still assigns Owner/Admin roles or exposes a separate Attendance
left menu.

## Money and quantities

Monetary storage uses decimal-capable PostgreSQL numeric columns and backend
Decimal calculations. API values are commonly serialized as decimal strings.
Do not perform financial reconciliation using binary floating-point equality
or combine quantities with different units without conversion.

## What is stored where?

| Location | Contents | Included in database backup? |
|---|---|---|
| PostgreSQL | Business records, hashes, sessions, permission JSON, audit | Yes, when database is backed up |
| `data/uploads/` | Plan documents, PO images, labor supporting files | No; back up separately |
| `data/logs/` | Daily backend/frontend diagnostic JSONL | No; apply a separate retention policy |
| Browser session storage | Personal notes, workspace location | No; temporary |
| Browser local storage | Theme preference | No |
| `.env` | Connection settings and service secrets | No; preserve securely, not in public docs |

Relative upload configuration is anchored to the construction project root, not
the terminal's current directory. Stored random filenames should not be renamed:
metadata refers to them. Original user filenames are download labels.

## Audit versus diagnostic logging

AuditEvent is the business review trail exposed by User History and project Audit
Log. It can include actor, action, entity, project and before/after details.
Not all event types populate detailed snapshots.

Diagnostic logs record request IDs, method/path, status and duration for support.
They are not a replacement for the user-facing audit table. Do not publish raw
diagnostic files without checking them for sensitive information.

## Deactivation and deletion

Deactivation sets the account inactive and revokes sessions. Activation restores
login eligibility without removing its prior permission configuration.

Delete sets inactive/deleted markers and revokes sessions; the directory excludes
the account. Historical project/audit foreign keys remain valid. This is not
physical erasure, anonymization, a reusable username promise, or a retention policy.

## Migrations and backups

Use Alembic for changes to existing schemas. Startup `create_all` can create
missing mapped tables; it cannot safely substitute for column/schema migrations.
The reviewed migration sequence includes project audit linkage after user
permissions and deletion-marker revisions. Use `alembic heads` rather than hardcoding
a revision number into operational automation.

A recoverable backup needs the database and original upload files from a
consistent period, plus secure configuration/redeployment instructions. Test a
restore into a separate environment; do not treat a Docker volume as a backup.
