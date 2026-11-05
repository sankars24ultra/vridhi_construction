# Vridhi Constructions & Designs
## Construction ERP Implementation Plan and Prototype Specification

## 1. Document Purpose
This document describes the current browser prototype in `construction-erp-prototype.html`, the intended production system, and the work required to move from the prototype to a secure React, FastAPI, and PostgreSQL application. Prototype behavior and production requirements are labeled separately so sample data and browser-only controls are not mistaken for operational functionality.

## 2. Product Goal
Build a centralized, project-centric operations platform for Vridhi Constructions & Designs. Each purchase, vendor payment/installment, inventory movement, client billing event, employee timecard, approval, and cost record must be traceable to the correct project. Authorized leadership needs a company-wide portfolio and reliable project-level cost, margin, contract, and billing visibility.

### Technology direction
- **Frontend:** React SPA, Vite, Tailwind CSS, and TanStack Query.
- **Backend:** Python FastAPI, Pydantic v2, SQLAlchemy 2 async.
- **Database:** PostgreSQL, managed through Alembic migrations.
- **Initial currency:** INR (₹), stored with decimal-safe numeric types.

## 3. Current Prototype Inventory
The HTML prototype is a single-file browser UI. It includes an authentication demonstration and local interactions; it does not call a FastAPI service or persist data to PostgreSQL.

### 3.1 Brand and responsive shell
- Browser title and visible brand: **Vridhi Constructions & Designs**.
- Desktop/tablet shell includes the brand, workspace navigation, signed-in identity, project context, and sign-out action.
- On phones, navigation becomes a horizontally scrollable row, project cards become one column, the portfolio metric row remains one row with horizontal scrolling, role descriptions stack, and wide tables scroll inside their panel.
- The portfolio metric row contains five separate totals: Total Projects, Planning, Active, On Hold, and Completed.

### 3.2 Authentication and account recovery screens
- The app starts at a sign-in screen. Users may enter a username or work email and a password.
- First-run demo account displayed on the screen: username `alex.morgan`, password `FieldworkDemo!26`.
- Correct credentials open the app shell; incorrect credentials and inactive users are rejected with a generic message.
- Sign-out clears the in-memory identity and returns to sign-in.
- Forgot password requests a local demo reset code. A valid active username/email receives a six-digit code displayed in the browser, valid for 15 minutes. A reset form accepts the identity, code, new password, and confirmation; successful reset consumes the code and changes the browser-side password hash.
- Prototype password hashes use PBKDF2 through Web Crypto with a random salt and 210,000 SHA-256 iterations. This is only an interaction demonstration. Browser-side storage is not production authentication or a trusted security boundary.
- The prototype currently uses local storage keys prefixed with `fieldwork-` and a legacy demo password for continuity. Renaming the product brand does not rename these internal keys or reset existing prototype records.

### 3.3 Project portfolio home
- Initial authenticated view is **All Projects**; there is no active-project dropdown.
- Projects are grouped into **Planning**, **Active**, **On Hold**, and **Completed** sections.
- Each section shows its project count and project cards. A card displays name, location, status, contract value, actual cost, and (when On Hold) the hold reason.
- Summary metrics separately count Total Projects, Planning, Active, On Hold, and Completed.
- Selecting an accessible project card opens that project's Overview. Keyboard Enter/Space can open a focused card.
- The **Projects** navigation item returns to the portfolio.
- **New Project** opens a form requiring project name, location, approved budget, contract value, and start date. New records start in Planning and are assigned to their creator in the prototype.
- New Project also accepts an optional initial plan approval file and uploader comment. The Overview includes a Plan Documents history, newest first, showing filename/type, upload time, uploader, comment, and file action. Further uploads are available only while a project is Planning, Active, or On Hold; they require a document, comment, and revised project estimate. The upload dialog displays the current project contract value read-only and requires a new estimated value. A successful revised-plan upload updates the prototype's current contract estimate and records a Project Value History event containing change date, previous value, new estimate, user, linked document, and comment. The Overview shows that history newest first. An initial plan attached during project creation establishes the starting estimate rather than a change. The demo accepts PDF/PNG/JPG/DOC/DOCX up to 1 MB. Users may download documents; the uploader or demo Owner/Admin may delete after confirmation.
- Seed dataset: 15 sample projects total: 4 Planning, 7 Active, 2 On Hold, 2 Completed. This consists of three original Active projects and twelve additional samples. The four new Planning projects are Riverfront Logistics Hub, Eastfield Public School, Meadowbrook Health Clinic, and Orchid Cold Storage. Added Active projects are Suncrest Solar Park, Westgate Transit Terminal, Parkview Office Tower, and Lakeview Water Treatment Plant. On Hold samples are Harborfront Apartments and Old Town Market Hall. Completed samples are Central District Library and Greenline Bus Depot.
- Generated sample calculation: for the 12 additional projects, Completed samples set billed value to 94% of contract and actual cost to 82% of budget; Active samples set open commitments to 12% of budget; other generated billed/actual/commitment values are zero. Generated margin values are 20.2% for Active, 18.5% for Completed, and zero for Planning/On Hold. These are fixture formulas, not business/accounting rules.
- Sample project values are illustrative, shown as INR with Indian number grouping. The three original sample projects include purchase orders, inventory rows, billing rows, and timecards. Additional seeded projects primarily contain portfolio-level project data.

### 3.4 Project workspace and navigation
- After selecting a project, the workspace shows a current project label and context in the sidebar.
- Project modules shown in the sidebar are Overview, Procurement, Inventory, Progress Billing, and Attendance. Users with permitted administration access also see Users.
- The portfolio is the global landing view. Project modules require an explicitly selected, accessible project.
- The sample policy demonstrates role-level module visibility and project membership filtering; production authorization must be enforced by the API on every request.

### 3.5 Project Overview dashboard
- Header displays project name, location, status, and an On Hold reason when present.
- Project name is followed by the same compact lifecycle icon used on the portfolio: Planning uses a clock, Active an up-right arrow, On Hold a pause symbol, and Completed a check. Status is not repeated as subtitle text under the project name.
- A dedicated Project Status section displays the current status and full status-change history newest-first, including prior/new state, user comment, actor, timestamp, and On Hold reason or completion note where relevant. The Update Status action remains available from this section and the page header.
- KPI cards show Contract Value, Actual Cost, Open Commitments, and Projected Margin.
- Budget vs. actual section includes an illustrative six-month bar chart and budget/spend totals.
- Cost breakdown separates Materials, Labor, and Equipment & Other.
- Recent purchase-order table shows PO number, vendor/item, date, amount, and status.
- Project actions include Update Status, Export Report, and Quick Entry. Export currently only displays a prototype notice. Quick Entry opens the timecard dialog.
- Completed projects display a completion notice. All dashboard charts, status history, and financial values are sample/illustrative unless populated from a future API.

### 3.6 Project lifecycle and status changes
- Supported statuses: Planning, Active, On Hold, Completed.
- Project status dialog allows a status selection and requires a user comment for every status change. On Hold additionally requires a reason, which is displayed in the overview and portfolio card. Completed requires explicit confirmation and allows an optional completion note.
- The Project Overview status icon and dedicated history list use the same lifecycle status values as the portfolio; history is readable on mobile and sorted newest-first.
- Status changes are kept in browser local storage, but there is no backend audit record, authorization audit, or transition history yet.
- In production, each change needs actor, timestamp, previous status, new status, reason/note, and authorization checks. Completion should also support closeout prerequisites agreed with finance and operations.

### 3.7 Procurement view
- Shows project-level KPI cards for PO count, total ordered, total paid, and outstanding balance.
- Purchase order register is sorted on the UI by Order Date newest-first, regardless of the order returned by the API and regardless of payment state (Paid, Partially paid, or Pending). Payment status must not create separate groups or otherwise affect row order. It shows PO number with a compact adjacent payment-state icon, separate Vendor and Item columns, dedicated Order Date column, total, paid-to-date, pending balance, and icon-based Edit/Add Payment/History actions with accessible labels/tooltips. Search filters the rendered rows. Status is conveyed by an accessible icon/tooltip instead of stacked text below the PO number.
- New Purchase Order opens a form for vendor, item description, quantity, unit price, and order date. Total is quantity × unit price. Creating a PO also registers the item in the project's Inventory, linked to its source PO; the ordered quantity is visible immediately, while received, consumed, and available quantities remain zero until inventory receipts/movements occur. Editing a PO updates its linked inventory item and ordered quantity without erasing receipt/consumption history, and cannot lower the total below the sum already paid.
- Procurement UI ordering example (newest to oldest; payment state does not change ordering): 10/05 pipes — Paid — total ₹1,000, paid ₹1,000, balance ₹0; 10/04 cement — Paid — total ₹6,400, paid ₹6,400, balance ₹0; 10/01 cement — Partially paid — total ₹22,000, paid ₹20,000, balance ₹2,000; 10/01 bricks — Pending — total ₹12,000, paid ₹0, balance ₹12,000; 09/29 rope — Paid — total ₹5,000, paid ₹5,000, balance ₹0; 09/25 equipment — Partially paid — total ₹10,000, paid ₹5,000, balance ₹5,000. Rows sharing a date retain stable source order; payment state is not a tie-breaker.
- Each PO owns a payment ledger. Every payment captures amount, payment date, optional transaction/reference ID, optional bill/payment screenshot (image or PDF), comment, payment timestamp, and acting user. The ledger is append-only in the UI; each installment is preserved rather than overwriting the previous paid amount.
- Payment History opens a viewport-constrained per-PO modal with internal vertical scrolling as needed and no clipped right-side columns. Entries are sorted newest first with separate Amount, Date, Reference, Comment, Recorded By, and Attachment columns. Uploaded images can be previewed/opened; PDF or other supported receipts can be opened/downloaded.
- Cumulative paid is calculated as the sum of ledger entries; pending balance is `max(0, PO total - cumulative paid)`. A payment greater than the outstanding balance is rejected. The register and summary KPI recompute after each payment.
- Visual payment status: unpaid balance uses dark red, partial payment uses orange, and zero balance/fully paid uses green. PO rows display total, paid-to-date, and pending amount together without redundant Paid/Pending captions above amounts. Edit and Add Payment are disabled for a settled PO; the edit dialog rejects settled orders and the payment handler rejects a zero balance. Unpaid and partly paid orders remain editable, subject to the existing paid-to-date total constraint. Payment History remains available for all orders.
- In the browser demo, PO/payment data is stored in project local storage and receipt files are stored as data URLs with a 1 MB per-file limit. These are not bank transactions, accounting postings, server audit events, or protected documents.
- PO approval, vendor integrations, tax/withholding logic, and accounting synchronization remain unimplemented placeholders/future scope.

### 3.8 Inventory view
- Describes the distinction between received stock and consumed quantities to avoid treating open orders as actual cost.
- Project material table includes item ID, material, category, ordered quantity, received quantity, consumed quantity, and available quantity. Legacy inventory seed rows show no ordered quantity; items added through Procurement appear linked to their purchase order with ordered quantity populated and zero received/consumed/available until receipt and movement workflows are implemented.
- Allocate Stock and Record Receipt currently display prototype/planned-action messages. The UI does not yet mutate an inventory ledger or recalculate stock/cost; registering a PO item in the prototype is a catalog/ordered-quantity projection, not a receipt or actual inventory valuation.

### 3.9 Progress Billing view
- KPI cards show revised contract, billed-to-date amount, illustrative retainage, and amount awaiting payment.
- Billing applications table shows application ID, work completed, submission date, current due, and status.
- Buttons for Change Order, New Application, and Schedule of Values are placeholders; invoices, approvals, payments, and contract amendments are not persisted or processed by the prototype.

### 3.10 Attendance and labor view
- KPI cards show hours logged, labor cost, pending approval, and approved weekly hours.
- Timecard table shows employee, cost code, hours, labor cost, and approval status.
- Log Hours/Quick Entry dialog asks for employee, work date, cost code, hours, and hourly rate (INR). It adds a row to the current page and labels the entry Pending.
- Submitted timecards are not retained after reload, do not update the dashboard aggregates, and do not have a server approval workflow. Export and date controls are placeholders.
- Production rules must define regular/overtime calculations, breaks, time zones, corrections, duplicate detection, supervisor approval, and the rate captured for payroll costing.

### 3.11 User Administration view
- Only the prototype's Admin and Owner roles see Users in navigation. User administration can be opened without selecting a project.
- Role matrix displayed in the UI describes Owner, Managing Director, Admin, Supervisor, and Cashier.
- User directory displays name, email, role, assigned project names (or All Projects), active/inactive status, and actions.
- Add User requires name, unique email, unique username, role, project assignment for project-scoped roles, and a temporary password plus confirmation. Passwords are hashed before storing in local storage.
- Edit User changes name, email, username, role, and project membership; blank password fields mean keep the existing password. The current user cannot edit or deactivate their own account in this screen.
- Deactivate marks an account inactive; Reactivate restores it. Delete asks for confirmation and removes the user's project memberships in this prototype.
- Admin can create/manage Supervisor and Cashier accounts, but is blocked from granting Owner or Managing Director. Owner can assign all listed roles. The demo UI does not implement persistent role configuration or trustworthy authorization.
- Admin-issued password reset creates a local, 15-minute demo code displayed in a browser alert. This is not emailed and must never be used as a production reset mechanism.

## 4. Roles and Access Requirements
The following is the intended least-privilege policy. The prototype approximates it; the production API is authoritative.

| Role | Project scope | Intended capabilities |
|---|---|---|
| Owner | Company-wide | All projects and modules; administer users, roles, memberships, and system settings. Preserve at least one active Owner. |
| Managing Director (MD) | Company-wide | Portfolio and financial dashboards, plus explicitly granted approvals; no user administration or project mutation by default. |
| Admin | Explicit project assignments | Manage operational Supervisor/Cashier accounts and project assignments; cannot grant Owner/MD; no implicit company-wide project access. |
| Supervisor | Explicit project assignments | Project overview, procurement/inventory operations, and attendance/timecard review or approval; no billing administration by default. |
| Cashier | Explicit project assignments | Billing, invoices, receipts, and payment workflows; no inventory/procurement administration or labor approval by default. |

### Authorization invariants
- Authentication identifies the user; server-side user-project membership determines project access.
- Project list responses contain only projects the user may access, except roles explicitly granted company-wide access.
- Every project/module/detail/report/export API checks the authenticated user's membership and action permission. Guessing an ID, editing local storage, or hiding UI controls must not grant access.
- Admin cannot manage Owner, MD, Admin, or self accounts; only Owner grants Owner/MD roles. Prevent last-Owner lockout.
- Deactivation immediately blocks login and revokes active sessions. All changes to roles, memberships, account state, project status, and approvals are audit logged.

## 5. Data and Domain Model

### 5.1 Projects and memberships
`projects` should include ID, name, location, status, baseline budget, contract value (or a relation to contracts), start/estimated end dates, currency (INR default), lifecycle notes, created/updated actors and timestamps. Store status-change comments, On Hold reasons, and completion notes in an append-only status history with previous/new status, actor, and timestamp rather than relying on mutable text alone.

`project_memberships` should include user ID, project ID, grantor, grant time, revocation time, and (if required) project-specific role override. Use a normalized role/permission model. Company-wide access is explicit and audited.

`project_documents` should include document ID, project ID, private storage object key, original filename, validated MIME/content type, byte size, category (initial approval or revised plan), proposed estimate (where applicable), required comment, uploader user ID, uploaded timestamp, checksum, and soft-delete actor/time/reason. A plan revision may propose an updated estimate, but must create a separate audited project value/change-order history record with previous/new values, effective date, actor, source document ID, comment, approval state, and approval actor/time. Current approved contract value changes only after required commercial approval. Store metadata in PostgreSQL and bytes in private object storage; never put production documents in browser local storage.

### 5.2 Users, authentication, and audit
`users` should include unique username, verified unique email, name, active/inactive status, role grants, password hash, password algorithm/version metadata, and lifecycle timestamps. Never persist plaintext passwords.

Use server-side password hashing (Argon2id recommended), rate-limited login, generic failure messages, session expiration and revocation, verified-email invitations, and password-reset token records containing only token hashes, user, expiry, consumed time, and request metadata. Reset tokens must be cryptographically random, single-use, short-lived, rate-limited, and emailed to a verified address. Add audit events for sign-in success/failure, reset request/completion, role/project grant/revoke, deactivation, and deletion.

`audit_events` should capture actor, action, entity, entity ID, timestamp, correlation/request ID, and before/after changes for sensitive operations.

### 5.3 Operations data
- **Procurement:** `purchase_orders`, `purchase_order_lines`, approvals, vendors, and partial `receipts`.
- **Vendor payments:** append-only `purchase_order_payments` related to a PO, including payment amount/date, reference, comment, receipt object key, actor, and timestamp. Never overwrite prior installments; derive paid-to-date and balance from ledger entries.
- **Inventory:** `inventory_items` and append-only `inventory_transactions` for receipt, project allocation, issue/consumption, transfer, and return. Record project, cost code, item, quantity, unit cost/valuation, actor, and time.
- **Contracts/billing:** `contracts`, `schedule_of_values`, `change_orders`, `progress_billings`, `invoices`, `payments`, and retainage. Preserve approval and amendment history.
- **Attendance:** `employees`, `cost_codes`, and `timecards` containing project, employee, work date, cost code, regular/overtime hours, rate captured at approval, approval state, supervisor, and correction history.
- **Cost reporting:** either tested SQL views/query services or materialized reporting structures with explicit as-of time and metric definitions.

### 5.4 Integrity and money rules
- PostgreSQL foreign keys and `CHECK` constraints protect required relationships, valid status values, positive quantities/hours, nonnegative costs, and date order.
- Use `NUMERIC` in PostgreSQL and Python `Decimal` for monetary calculations. Store project currency explicitly; prototype display defaults to INR (₹) with Indian number grouping.
- Separate contract value, approved change orders, earned revenue, invoiced amount, cash received, retainage, actual cost, open commitments, and forecast cost.
- Actual material cost is recognized once, under a finance-approved inventory valuation method; open purchase orders remain commitments and are not actual expense.
- For every PO, paid-to-date is the sum of its payment ledger entries and outstanding balance is `MAX(0, PO total - paid-to-date)`. Payments are append-only; corrections use an audited reversal/adjustment. Reject overpayment atomically so simultaneous requests cannot exceed the balance.
- Keep each vendor installment distinguishable by payment date, reference, comment, paying user, and optional bill/receipt. PO edits cannot reduce the total below already-recorded payments without a separate credit/adjustment workflow.
- Define revenue recognition, overtime, cost-to-complete, and margin policies with finance before production dashboard acceptance.

### 5.5 PostgreSQL entities and SQLAlchemy 2.x models

This is the proposed production schema, not the standalone prototype's browser storage. Initial scope is one construction company managing multiple projects. Multi-company SaaS requires an additional `organizations` entity and tenant-scoped keys, uniqueness, and authorization throughout the schema.

Each table has a UUID `id` primary key unless a composite primary key is specified. Fields ending in `_id` below are foreign keys to the corresponding entity. Mutable records use `created_at` and `updated_at`; ledger and event records preserve their original actor and timestamp. The listed fields are the domain mapping, not complete executable model definitions or migrations.

| PostgreSQL table | SQLAlchemy model | Important fields and foreign keys |
|---|---|---|
| `users` | `User` | Unique username and email, password_hash, password algorithm/version, name, active |
| `roles` | `Role` | Unique code: Owner, Managing Director, Admin, Supervisor, Cashier |
| `permissions` | `Permission` | Unique code, such as `procurement.create` |
| `user_roles` | `UserRole` | user_id, role_id, granted_by_id, granted_at, revoked_at |
| `role_permissions` | `RolePermission` | role_id + permission_id, composite primary key |
| `auth_sessions` | `AuthSession` | user_id, unique token_hash, expires_at, revoked_at |
| `password_reset_tokens` | `PasswordResetToken` | user_id, unique token_hash, expires_at, consumed_at, request metadata |
| `user_invitations` | `UserInvitation` | user_id, invited_by_id, unique token_hash, expires_at, accepted_at |
| `projects` | `Project` | name, location, status, baseline_budget, currency, start_date, estimated_end_date, created_by_id |
| `project_memberships` | `ProjectMembership` | project_id, user_id, granted_by_id, granted_at, revoked_at |
| `project_status_history` | `ProjectStatusHistory` | project_id, previous_status, new_status, comment, hold_reason, completion_note, actor_id, occurred_at |
| `documents` | `Document` | Unique private object_key, filename, MIME, byte_size, checksum, uploaded_by_id, uploaded_at |
| `project_documents` | `ProjectDocument` | project_id, document_id, category, comment, deleted_at, deleted_by_id, deletion_reason |
| `project_value_revisions` | `ProjectValueRevision` | project_id, contract_id, source_project_document_id, previous_value, proposed_value, effective_date, approval_status, proposed_by_id |
| `project_value_revision_events` | `ProjectValueRevisionEvent` | revision_id, action, actor_id, occurred_at, comment |
| `vendors` | `Vendor` | name, contact details, tax_identifier, active |
| `inventory_items` | `InventoryItem` | Unique SKU, name, category, unit_of_measure, active |
| `project_inventory_items` | `ProjectInventoryItem` | project_id, item_id; unique project/item pair |
| `purchase_orders` | `PurchaseOrder` | project_id, vendor_id, unique number, order_date, currency, approval_status, created_by_id |
| `purchase_order_lines` | `PurchaseOrderLine` | purchase_order_id, item_id, cost_code_id, quantity, unit_price, description |
| `purchase_order_approval_events` | `PurchaseOrderApprovalEvent` | purchase_order_id, action, actor_id, occurred_at, comment |
| `purchase_order_payments` | `PurchaseOrderPayment` | purchase_order_id, amount, payment_date, reference, comment, receipt_document_id, recorded_by_id, recorded_at, reversal_of_id |
| `goods_receipts` | `GoodsReceipt` | purchase_order_id, received_at, received_by_id, delivery_reference |
| `goods_receipt_lines` | `GoodsReceiptLine` | receipt_id, purchase_order_line_id, quantity_accepted |
| `inventory_locations` | `InventoryLocation` | project_id, name; nullable project_id for a central warehouse |
| `inventory_transactions` | `InventoryTransaction` | item_id, project_id, cost_code_id, source_location_id, destination_location_id, type, quantity, unit_cost, receipt_line_id, actor_id, occurred_at, reversal_of_id |
| `cost_codes` | `CostCode` | Unique code, name, category, active |
| `project_cost_budgets` | `ProjectCostBudget` | project_id, cost_code_id, budget_amount; unique project/cost-code pair |
| `contracts` | `Contract` | project_id, unique number, original_value, currency, retainage_rate |
| `change_orders` | `ChangeOrder` | contract_id, value_revision_id, amount_delta, status, approved_by_id, approved_at |
| `schedule_of_values` | `ScheduleOfValue` | contract_id, cost_code_id, description, scheduled_amount |
| `progress_billings` | `ProgressBilling` | contract_id, period_start, period_end, status, submitted_at |
| `progress_billing_lines` | `ProgressBillingLine` | billing_id, schedule_of_value_id, current_work_amount, retainage_amount |
| `invoices` | `Invoice` | contract_id, progress_billing_id, unique number, issued_date, due_date, total |
| `client_payments` | `ClientPayment` | contract_id, amount, payment_date, reference, recorded_by_id, reversal_of_id |
| `client_payment_allocations` | `ClientPaymentAllocation` | payment_id, invoice_id, amount |
| `retainage_releases` | `RetainageRelease` | billing_line_id, amount, released_at, approved_by_id |
| `employees` | `Employee` | Unique employee_number, name, default_hourly_rate, active |
| `timecards` | `Timecard` | project_id, employee_id, cost_code_id, work_date, regular_hours, overtime_hours, captured_regular_rate, captured_overtime_rate, status, supervisor_id, supersedes_id |
| `timecard_approval_events` | `TimecardApprovalEvent` | timecard_id, action, actor_id, occurred_at, comment |
| `audit_events` | `AuditEvent` | actor_id, action, entity_type, entity_id, before/after JSONB, request_id, occurred_at |

### 5.6 ORM relationship map

`1:N` means one-to-many; `N:M` means many-to-many through an explicit association model. Grant and membership associations contain lifecycle metadata and should be mapped as association objects, not only bare secondary tables.

| ORM relationship | Cardinality and target |
|---|---|
| `User.role_grants` / `Role.user_grants` | 1:N `UserRole` on each side; User to Role is N:M |
| `Role.permissions` | N:M `Permission` through `RolePermission` |
| `User.project_memberships` / `Project.memberships` | 1:N `ProjectMembership` on each side; User to Project is N:M |
| `User.sessions`, `User.reset_tokens`, `User.invitations` | 1:N corresponding authentication entities |
| `Project.status_history`, `Project.documents` | 1:N `ProjectStatusHistory` and `ProjectDocument`; each project document references `Document` |
| `Project.value_revisions` | 1:N `ProjectValueRevision`, referencing `Contract` and optional source `ProjectDocument` |
| `ProjectValueRevision.events` | 1:N `ProjectValueRevisionEvent` |
| `Project.purchase_orders`, `Vendor.purchase_orders` | 1:N `PurchaseOrder` |
| `PurchaseOrder.lines`, `PurchaseOrder.payments`, `PurchaseOrder.receipts`, `PurchaseOrder.approval_events` | 1:N `PurchaseOrderLine`, `PurchaseOrderPayment`, `GoodsReceipt`, `PurchaseOrderApprovalEvent` |
| `GoodsReceipt.lines` | 1:N `GoodsReceiptLine`; each line references `PurchaseOrderLine` |
| `InventoryItem.purchase_lines`, `InventoryItem.transactions` | 1:N `PurchaseOrderLine` and `InventoryTransaction` |
| `Project.inventory_item_links` / `InventoryItem.project_links` | 1:N `ProjectInventoryItem` on each side; Project to InventoryItem is N:M |
| `InventoryLocation.incoming_transactions`, `InventoryLocation.outgoing_transactions` | 1:N `InventoryTransaction`, using destination_location_id and source_location_id respectively |
| `Project.cost_budgets`, `Project.contracts` | 1:N `ProjectCostBudget` and `Contract` |
| `Contract.change_orders`, `Contract.schedule_of_values`, `Contract.billings`, `Contract.invoices`, `Contract.client_payments` | 1:N corresponding commercial entities |
| `ProgressBilling.lines`, `ScheduleOfValue.billing_lines` | 1:N `ProgressBillingLine` |
| `ClientPayment.allocations`, `Invoice.payment_allocations` | 1:N `ClientPaymentAllocation` on each side; ClientPayment to Invoice is N:M with allocated amount |
| `ProgressBillingLine.retainage_releases` | 1:N `RetainageRelease` |
| `Employee.timecards`, `Project.timecards`, `CostCode.timecards` | 1:N `Timecard` |
| `Timecard.approval_events` | 1:N `TimecardApprovalEvent` |

### 5.7 SQLAlchemy mapping and database constraints

- Use SQLAlchemy 2.x `DeclarativeBase`, `Mapped[...]`, `mapped_column(...)`, and paired `relationship(back_populates=...)`. Use Alembic for versioned migrations and the planned async SQLAlchemy session layer for application transactions.
- UUID keys map to PostgreSQL UUID / Python `UUID`; foreign keys use `ForeignKey(...)`. Money maps to `Numeric(18, 2)` / Python `Decimal`; quantities to `Numeric(18, 4)`; business dates to `Date` / Python `date`; event timestamps to `DateTime(timezone=True)` / timezone-aware Python `datetime`. Use explicit decimal rounding policies, not binary floating-point arithmetic.
- Use constrained status codes, Boolean for flags, and JSONB for audit change payloads. `AuditEvent.entity_id` is a polymorphic identifier, not a normal foreign key to every possible target; enforce its meaning in the audit-writing service.
- Specify `foreign_keys` explicitly when a model has several references to `User` or `InventoryLocation`. Configure self-references such as payment reversals and timecard supersession with `remote_side` and explicit foreign keys.
- Active role grants and project memberships need partial unique indexes on their natural pairs where `revoked_at IS NULL`. Association links such as project/item, project/cost-code budget, and role/permission need unique constraints or composite primary keys.
- Create foreign-key and reporting indexes, including purchase_orders(project_id, order_date, id), purchase_order_payments(purchase_order_id, payment_date), inventory_transactions(project_id, item_id, occurred_at), and timecards(project_id, work_date, employee_id).
- Register procured items in `project_inventory_items` in the same transaction as PO creation, using an upsert on the unique project/item pair. Multiple POs for the same item must not create duplicate project catalog entries. PO lines remain the traceable source of ordered quantities; inventory registration is not a goods receipt.
- Derive ordered/open quantities from PO lines, lifecycle state, and accepted receipt lines. Derive on-hand stock from posted inventory transactions. Validate receipt lines against their parent PO and prohibit double posting a receipt line to inventory, using a unique source-posting constraint/idempotency key.
- For receipts, billing lines, revisions, allocations, and inventory postings, enforce matching project/contract/item scope using composite foreign keys where practical and transactional service checks otherwise. An ordinary UUID foreign key alone does not prove same-project ownership.
- Derive PO total from its lines and paid-to-date from net posted payments. Keep payment status computed rather than independently mutable. Lock the PO row for every payment, reversal, or edit, and reject overpayment, edits to a fully paid PO, and totals below paid-to-date within the transaction.
- Reversal records reference their originals, retain positive amounts/quantities, and use an explicit reversal type or reference to determine their negative net effect. Validate scope, prohibit reversing a reversal or double reversal, and preserve the original ledger entry. Corrections to approved timecards create linked replacements and audited events.
- Restrict deletion of financial and history records with restrictive foreign keys; do not cascade-delete ledgers when deleting a user/project/vendor/item. Prefer deactivation, soft deletion of document associations, and audited reversal/correction workflows. Preserve document metadata referenced by history even after authorized file removal.
- Approved contract value is original contract value plus approved change-order deltas. Plan estimates stay pending proposals until authorized approval. Apply an approved revision exactly once, checking its baseline against current approved value under a contract lock; retain proposal and approval events.
- Apply `CHECK` constraints for positive quantities/payments, nonnegative prices/hours, retainage rate between 0 and 1, and valid date ranges. Cross-row rules such as no overpayment, no excess invoice allocation, and no over-release of retainage require transactional checks, not only row-level constraints.
- Sort procurement UI rows by order_date descending without payment-state grouping. For paginated production responses, the API must also use a deterministic order such as order_date DESC, id DESC so sorting is correct across pages; same-date UI rows may preserve the returned order. Payment status is never a tie-breaker.
- Report queries aggregate each ledger independently before joining to avoid multiplying totals across multiple one-to-many relations. Reporting views/materialized views are derived outputs, not competing sources of financial truth.

## 6. Production API Outline

### Authentication
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/password-reset/request`
- `POST /api/v1/auth/password-reset/complete`
- Invitation/first-login password setup endpoint, plus session refresh/revocation if token-based authentication is selected.

### Users and roles
- `GET/POST /api/v1/users`
- `GET/PATCH/DELETE /api/v1/users/{user_id}`
- `PUT /api/v1/users/{user_id}/projects`
- Deactivation/reactivation endpoints or status patch, with session revocation and audit.
- Admin endpoints enforce the role matrix; Owner-only operations include granting Owner/MD and global settings.

### Projects and modules
- `GET /api/v1/me/projects` returns only authorized projects.
- `GET/POST /api/v1/projects`; `GET/PATCH /api/v1/projects/{project_id}`.
- `PATCH /api/v1/projects/{project_id}/status` requires a comment for every change, a reason for On Hold, and explicit confirmation for Completed.
- A plan upload with a revised estimate should create a pending value/change-order proposal when approvals are required; only after authorized approval should it update the approved contract value. Provide `GET /api/v1/projects/{project_id}/value-history` and an authorized plan-document upload endpoint that links its document to the estimate proposal. The UI should separately show approved contract value and proposed value while approval is pending.
- `GET/POST /api/v1/projects/{project_id}/purchase-orders`; receipt and approval operations.
- `PATCH /api/v1/projects/{project_id}/purchase-orders/{po_id}` updates PO details; reject totals below paid-to-date unless a separately modeled credit/adjustment is approved.
- `POST /api/v1/projects/{project_id}/purchase-orders/{po_id}/payments` appends a partial/full payment with date, reference, comment, and optional receipt; `GET /api/v1/projects/{project_id}/purchase-orders/{po_id}/payments` returns newest-first history. Reject overpayment atomically using the current balance and record actor/audit information.
- `POST /api/v1/projects/{project_id}/documents` for a file, category, and required comment; `GET /api/v1/projects/{project_id}/documents` returns newest first; `GET /api/v1/projects/{project_id}/documents/{document_id}` provides authorized file access; `DELETE /api/v1/projects/{project_id}/documents/{document_id}` removes or soft-deletes an authorized document. Uploads are allowed only in Planning, Active, or On Hold. Initial project creation with a plan may use a transaction plus upload compensation or a multipart project-creation endpoint.
- Inventory transaction endpoints for receive, allocate, issue, transfer, and return.
- Contract, schedule-of-values, change-order, progress-billing, invoice, payment, and retainage endpoints.
- `GET/POST /api/v1/projects/{project_id}/timecards`; `POST /api/v1/timecards/{id}/approve`.
- `GET /api/v1/reports/job-costing?project_id=...&as_of=...` and company portfolio reporting for authorized roles.

All writes use transactions, validate project ownership/membership, record actor and audit events, and return structured validation errors. Aggregate queries must avoid one-to-many join multiplication; detail APIs need pagination and filters.

## 7. Non-Functional Requirements
- **Security:** authentication, role-based permission checks plus project membership, least privilege, CSRF/session protection as applicable, input validation, output encoding, rate limits, secure secret handling, restricted CORS, audit retention, backup and restore.
- **Performance:** indexes on project ID, status, dates, employee, and common query dimensions; efficient dashboard aggregates; pagination; connection-pool sizing and load tests.
- **Reliability:** database transactions, migrations, recoverable backups, idempotent operations where practical, and monitoring/alerting.
- **Document storage:** store files in private encrypted object storage; validate file signatures, not only browser MIME/extension; allow-list formats; enforce configurable limits; calculate checksums; malware-scan uploads; use short-lived authorized download links or an authenticated streaming endpoint; back up objects and metadata together. Audit upload, download, and delete actions.
- **Usability/accessibility:** desktop, tablet, and phone layouts; keyboard navigation; visible focus; labels and actionable errors; internal scrolling for wide tables and the one-row portfolio KPI strip on narrow screens.
- **Localization:** INR display by default and explicit currency metadata for future multi-currency use; define timezone/date display rules.

## 8. Delivery Plan

### Phase 1: Validate prototype workflows and policy
Review all prototype screens and placeholder actions with Owner/MD, project managers, supervisors, cashiers, and finance. Approve the role matrix, project status lifecycle, financial definitions, approval thresholds, inventory costing, overtime policy, and reset/invitation policy.

### Phase 2: Foundation and identity
Create React/Vite, FastAPI, PostgreSQL, Alembic migrations, CI, development environment, user authentication, invitation/password setup, reset email delivery, session revocation, project membership authorization, and audit events. Test project isolation before operational modules.

### Phase 3: Projects and portfolio
Implement project create/read/update, project directory filtering, role-scoped project visibility, status changes with audit history, company portfolio, project navigation context, and project-specific overview data.

### Phase 4: Procurement and inventory
Implement vendor/PO lifecycle, approval, partial receiving, inventory ledger, allocations/issues/returns, cost-code attribution, and valuation tests.

### Phase 5: Contract and progress billing
Implement schedule of values, change-order approvals, progress billing, invoices, payments, and retainage. Reconcile all billing lifecycle totals.

### Phase 6: Attendance and labor costing
Implement manual supervisor time entry, rate capture, regular/overtime validation, approval, edits/corrections, duplicate handling, and project cost aggregation.

### Phase 7: Dashboard and reporting
Replace prototype figures with tested aggregate APIs for budget, actual costs, open commitments, billed/earned/paid values, margin, and forecast. Add company/project filters, as-of dates, exports, and role controls.

### Phase 8: Hardening and rollout
Run threat modeling, authorization tests, audit review, accessibility testing, performance and load tests, restore drills, and UAT. Pilot, reconcile against source finance records, fix discrepancies, and roll out in stages.

## 9. Acceptance Criteria
- The first unauthenticated visit displays sign-in; no project names or financial data are exposed before authentication.
- Username and verified email are unique login identities; wrong credentials and inactive users are rejected without revealing which part failed.
- New users require a username and initial password; only a salted server-side password hash is stored. Editing a user without entering a new password preserves the current hash.
- A production reset link is emailed to the verified address, is single-use and short-lived, and is never returned or logged in plaintext. Login and reset requests are throttled and audited.
- Users see only authorized projects and permitted modules; direct API requests and guessed IDs cannot bypass project membership.
- New project creation requires name, location, baseline budget, contract value, and start date, starts in Planning, and grants membership according to policy.
- Project creation may include an initial plan approval file and comment. Planning, Active, and On Hold projects accept revised plan documents with required comments; Completed projects reject new uploads.
- The plan upload form shows the current project contract value as disabled/read-only and requires a new estimated value. Each successful revised-plan upload adds a dated previous-value/new-estimate entry linked to the uploaded file and comment; entries display newest-first. Initial project setup starts value history from the original contract instead of creating a false change event. Production distinguishes a submitted proposal from the approved contract value and enforces required commercial approvals.
- Each project document list sorts newest-first and displays filename/type, upload time, uploader, and comment. Authorized users can download; only the uploader or a permitted Owner/Admin can delete. Guessed project/document IDs cannot bypass membership or role checks.
- Empty comments, unsupported types, oversized files, read/storage failures, and unauthorized upload/delete attempts produce actionable errors and do not leave orphaned document metadata or objects.
- Portfolio totals and project lists separately show Planning, Active, On Hold, and Completed; selecting a project opens its workspace and Projects returns to the portfolio.
- Every project status transition requires a user comment; On Hold additionally requires a reason; Completed requires explicit confirmation. Each transition is audited with actor, previous/new status, comment, and timestamp.
- Procurement, receipts, inventory movements, contracts, billing, payments, and timecards are persisted and traceable to project, cost code, and actor.
- A ₹100 purchase order paid in installments of ₹60, ₹20, and ₹20 shows balances of ₹40, ₹20, and ₹0 after each payment and preserves all three dated payment events in newest-first history, including references and receipts when provided.
- PO list displays total, paid-to-date, and pending balance together. Fully unpaid balance is highlighted dark red, partial payment uses orange, and zero balance/full payment uses green. PO payment totals and project procurement KPIs reconcile to payment ledger entries.
- PO payment-state icon appears directly beside its number; Order Date has a dedicated aligned column. Add Payment is disabled for settled POs and cannot be bypassed by submitting a payment against a zero balance. History separates reference and comment and supports viewing uploaded receipt attachments.
- Editing a PO below its paid-to-date amount and posting a payment above its current balance are rejected; the same balance rule is transaction-safe under concurrent payment submissions.
- Actual and committed costs are distinct; inventory receipts/issues cannot be double-counted; dashboard figures reconcile to ledger records.
- Supervisors can submit/approve permitted timecards; only approved hours affect labor actuals and decimal-safe calculations are used.
- User administration enforces the role matrix, project memberships, deactivation/session revocation, Owner safeguards, and audit history.
- Desktop, tablet, and mobile workflows are operable with keyboard and assistive technologies, with no unintended viewport overflow.

## 10. Known Prototype Gaps and Non-Functional Actions
The following items appear in the UI but are currently placeholders or only local demonstrations; they are not backend functionality:
- Purchase-order approval, advanced filters, goods-receipt workflows, accounting posting, vendor integrations, and bank payment execution. The prototype now supports local PO create/edit, partial payment entry, payment history, and receipt attachment demonstrations only.
- Inventory allocation, receiving, issue, transfer, and return processing.
- Change-order creation/approval, new progress billing, invoices, payments, retainage processing, and schedule-of-values editing.
- Report/time exports, advanced date filters, and true chart range changes.
- Attendance approval persistence, timecard storage across reload, and live updates to dashboard cost totals.
- Plan-document storage in the standalone prototype is browser-local only: files are encoded as data URLs in project local storage, capped at 1 MB, and are not encrypted at rest, scanned, backed up, or protected by server authorization. Production must use private object storage and server-side access checks.
- PO payment records and screenshot/PDF receipts in the standalone prototype are browser-local; receipt files are encoded as data URLs with a 1 MB limit and lack malware scanning, private storage, retention controls, accounting reconciliation, and server-side authorization. Production should store files in private object storage and payment events in an audited database ledger.
- Server-side user/project administration, invitations, email delivery, audit logs, real login sessions, and secure password reset delivery.
- Production database, API, migrations, integrations, backups, monitoring, and company-level financial aggregation.

Prototype project/account and status records may use local storage; some table interactions such as entered timecards are only held in the current page. Browser storage can be edited by the user and is not suitable for authorization or reliable business data.

### Current prototype implementation issues to resolve
- `users[].projectIds` and `projects[].memberUserIds` are separate local representations. Seeded Supervisor/Cashier assignments are not all copied to project membership arrays, while card access checks use project membership; consolidate to one canonical relation.
- Owner, MD, Supervisor, and Cashier demo profiles are listed but do not have initial password hashes; only Alex has the first-run demo password. Set credentials through the demo user editor before attempting their sign-in.
- User administration lists all local demo accounts to authorized demo roles; production must apply field-level and action-level authorization and avoid exposing unnecessary personal data.
- Project and user/status data is generally written to local storage; reset codes exist only in memory and disappear on reload; timecard additions only modify the current rendered table and disappear on reload.
- Financial KPI ratios, date labels, some amounts, chart bars, counts, and transaction data are static/illustrative. They are not calculated from a database ledger, and generated project values use fixture-only formulas.

## 11. Main Risks and Decisions
- **Financial policy:** agree on earned revenue, forecast cost, retainage, and margin definitions with finance.
- **Inventory valuation:** choose FIFO, weighted average, or another method and define return/transfer behavior.
- **Workforce compliance:** confirm local overtime, breaks, corrections, and payroll requirements.
- **Role design:** confirm whether Admin should have company-wide read access or only assigned projects; prototype policy is explicit project scope.
- **Authentication:** choose verified-email, invitation, MFA, session, password rotation, retention, and account-recovery policies.
- **Legacy prototype data:** decide whether to migrate or clear `fieldwork-*` local storage keys when replacing the demo with the production app.

## 12. Prototype Reference
Open [construction-erp-prototype.html](construction-erp-prototype.html) in a browser. It demonstrates Vridhi Constructions & Designs branding, login/reset interactions, a 15-project seeded portfolio, project navigation, role/user administration, sample INR dashboards, procurement/inventory/billing/attendance screens, and project status dialogs. Project/user/status changes are mostly retained in browser local storage; timecard rows and reset tokens are in-memory demonstrations. All data is illustrative; the standalone HTML prototype is not connected to a backend or database.

### 12.1 Exact project seed inventory
The twelve additional projects use INR values and all start assigned to the demo Admin in the prototype. For these additional samples, contract value and budget are separate sample values; billed/actual/committed values are derived as described in the seed logic, and operational sub-ledgers are empty.

| Project | Location | Status | Approved budget | Contract value |
|---|---|---:|---:|---:|
| Cedar Ridge Plaza | Austin, TX | Active | ₹24,50,000 | ₹31,80,000 |
| Northline Bridge | Round Rock, TX | Active | ₹56,80,000 | ₹74,00,000 |
| Juniper Residences | Georgetown, TX | Active | ₹39,20,000 | ₹51,50,000 |
| Riverfront Logistics Hub | Chennai, India | Planning | ₹1,85,00,000 | ₹2,28,00,000 |
| Eastfield Public School | Jaipur, India | Planning | ₹92,00,000 | ₹1,15,00,000 |
| Meadowbrook Health Clinic | Kochi, India | Planning | ₹1,28,00,000 | ₹1,56,00,000 |
| Orchid Cold Storage | Nashik, India | Planning | ₹76,00,000 | ₹94,00,000 |
| Suncrest Solar Park | Bikaner, India | Active | ₹3,42,00,000 | ₹4,18,00,000 |
| Westgate Transit Terminal | Surat, India | Active | ₹2,76,00,000 | ₹3,35,00,000 |
| Parkview Office Tower | Hyderabad, India | Active | ₹4,89,00,000 | ₹5,92,00,000 |
| Lakeview Water Treatment Plant | Mysuru, India | Active | ₹2,14,00,000 | ₹2,63,00,000 |
| Harborfront Apartments | Visakhapatnam, India | On Hold | ₹1,64,00,000 | ₹2,01,00,000 |
| Old Town Market Hall | Lucknow, India | On Hold | ₹87,00,000 | ₹1,08,00,000 |
| Central District Library | Indore, India | Completed | ₹64,00,000 | ₹78,00,000 |
| Greenline Bus Depot | Pune, India | Completed | ₹1,12,00,000 | ₹1,37,00,000 |

Sample hold reasons are `Awaiting revised permit approval` for Harborfront Apartments and `Client review of scope changes` for Old Town Market Hall.

### 12.2 Exact demo user seed inventory
- **Alex Morgan** (`alex.morgan`, `alex.morgan@fieldwork.example`): Admin; all 15 seeded projects in this browser demo; first-run password displayed by the login screen.
- **Jordan Ellis** (`jordan.ellis`, `jordan.ellis@fieldwork.example`): Owner; company-wide role in the demo matrix, but no initial password is seeded.
- **Priya Nair** (`priya.nair`, `priya.nair@fieldwork.example`): Managing Director; company-wide portfolio/dashboard role in the demo matrix, but no initial password is seeded.
- **Sam Rivera** (`sam.rivera`, `sam.rivera@fieldwork.example`): Supervisor; Cedar Ridge Plaza and Suncrest Solar Park.
- **Taylor Brooks** (`taylor.brooks`, `taylor.brooks@fieldwork.example`): Cashier; Cedar Ridge Plaza.

Passwords for the non-demo seeded accounts are not assigned in the source seed list; an administrator must set them through the Add User workflow before those accounts can sign in. Names and addresses are fictitious sample identities. The source seed assigns Supervisor/Cashier project IDs on user records, while portfolio authorization checks each project's `memberUserIds` array. These initial arrays are not fully synchronized; a seeded assignment can therefore appear in the user directory but not grant card access. Production must use one canonical server-side membership relation for both display and authorization.

### 12.3 Original project fixture detail
- **Cedar Ridge Plaza:** budget ₹24,50,000; contract ₹31,80,000; billed ₹12,75,000; actual ₹8,84,320; open commitments ₹3,42,600; projected margin 21.8%. Purchase orders: PO-2481 Lone Star Supply/Rebar #5 (₹42,600, In transit), PO-2479 Summit Concrete/ready-mix (₹31,200, Approved), PO-2474 Metro Electric/panel boards (₹18,940, Received), PO-2468 ProBuild Rentals/tower crane (₹12,500, Pending). Inventory examples include rebar, ready-mix, plywood, and copper wire. Billing rows PB-008 through PB-005 include one Submitted and three Paid examples. Four sample timecards use Concrete, Sitework, Electrical, and Framing cost codes.
- **Northline Bridge:** budget ₹56,80,000; contract ₹74,00,000; billed ₹28,40,000; actual ₹19,84,250; open commitments ₹7,26,400; projected margin 18.4%. Four purchase orders include structural beams, asphalt, pile-driver rental, and conduit, with Approved, In transit, Received, and Pending states. Inventory examples include structural beams, asphalt mix, concrete piles, and conduit. Billing rows PB-014 through PB-011 include one Submitted and three Paid examples. Four sample timecards use Concrete, Structural, Sitework, and Electrical cost codes.
- **Juniper Residences:** budget ₹39,20,000; contract ₹51,50,000; billed ₹18,95,000; actual ₹14,67,500; open commitments ₹5,18,200; projected margin 19.6%. Four purchase orders include foundation mix, lumber, switchgear, and scaffold rental. Inventory examples include dimensional lumber, concrete, roof sheathing, and switchgear. Billing rows PB-010 through PB-007 include one Submitted and three Paid examples. Four sample timecards use Framing, Concrete, Electrical, and Sitework cost codes.
- Dashboard cost breakdown uses illustrative ratios of 63% materials, 27% labor, and 10% equipment/other. Chart bars, some KPI values, and period labels are static illustrations rather than database-derived reports.

### 12.4 Browser persistence inventory
- `fieldwork-projects`: local sample project state, including status, hold reason, completion note, and project membership IDs.
- `fieldwork-users`: local demo user profile, role, username/email, project IDs, active state, and salted PBKDF2 hash/salt. Never migrate browser hashes as production credentials without a deliberate secure migration design.
- `resetCodes`: in-memory map only; demo reset codes disappear when the page reloads and are not delivered by email.
- Timecard additions are inserted into the current rendered table only and disappear on reload. Most other module actions display notices rather than mutate data.
- Internal storage keys retain the `fieldwork-` prefix for backwards compatibility despite the visible product rebrand. Decide whether production migration should import or discard local demo state.
