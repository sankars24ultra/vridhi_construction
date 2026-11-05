# Vridhi: API Catalog and UI Data Contracts

## 1. Purpose and Scope

Proposed REST API for the production application in [construction-erp-plan.md](construction-erp-plan.md), aligned with [construction-erp-model-schema.md](construction-erp-model-schema.md). These endpoints are not implemented by the standalone HTML prototype. This document specifies API names, methods, inputs, response types, screen usage, authorization, and frontend refresh behavior. Generate the eventual OpenAPI specification from FastAPI/Pydantic models and test it against this contract.

Existing prototype screens: Login, Password Reset, All Projects, Project Overview, Procurement, Inventory, Progress Billing, Attendance, and Users. Screens marked **planned** below are production workflows, not claims that the prototype already implements them.

### 1.1 Backend API Count

The proposed production backend contains **112 API endpoints**, counting each distinct **HTTP method + concrete route** as one endpoint. This includes planned production workflows, not only the current prototype screens; it is not a count of implemented APIs.

| Module | Endpoints |
|---|---|
| Authentication and current user | 10 |
| Users, roles, and memberships | 13 |
| Projects, documents, and value history | 16 |
| Reference masters | 16 |
| Procurement and vendor payments | 11 |
| Inventory and goods receipts | 11 |
| Contracts, billing, and collections | 22 |
| Attendance and labor | 8 |
| Reports and audit | 5 |
| **Total** | **112** |

Section 4 contains **100 endpoint catalog rows**. Its four reference-master patterns (list, detail, create, update) each apply to four resources: vendors, inventory-items, cost-codes, and employees. Expanding those four rows into 16 endpoints adds 12, yielding **100 + 12 = 112**.

Path aliases P, PO, and C are expanded without adding endpoints. Different HTTP methods on the same route count separately; query filters, action payload variants, and different resource IDs do not. Screen-loading references outside Section 4 are not additional endpoints. The earlier 117 route-pattern count included such references and is not the endpoint total. Recalculate this summary whenever the endpoint catalog changes.

## 2. Shared Contract

- Base path: `/api/v1`. All paths in endpoint tables are relative to this prefix. `{project_id}` and all other resource IDs are UUID path parameters. Nested child IDs must belong to their parent project/contract/order; the server verifies this for every request.
- Requests/responses are JSON unless a row explicitly specifies multipart or CSV. Dates are ISO `YYYY-MM-DD`; timestamps are ISO 8601 UTC. Money, quantities, hours, and rates are decimal strings, not JSON floating-point numbers. Currency is a three-letter code, default INR.
- `?` denotes optional/nullable fields. Fields without `?` are required on creation; PATCH accepts only explicitly supplied mutable fields. Server-managed fields such as actor, totals, payment state, timestamps, role permissions, and receipt availability cannot be assigned by clients.
- Single-resource success responses return a DTO directly. Lists return `Page<T>`. POST creation returns 201, GET/PATCH/PUT and action POST normally return 200, logout and deletion return 204 with no body. Endpoint-specific exceptions are listed below.
- Pagination inputs `page`: integer >=1, `page_size`: integer 1-100 (default 25). List metadata: `items: T[]`, `page: int`, `page_size: int`, `total: int`. Only lists marked `Page<T>` accept these parameters. Use whitelisted filters and sorts; no arbitrary SQL expressions.
- PO list default order is `order_date DESC, id DESC`, never grouped by payment state. Payment history uses `payment_date DESC, recorded_at DESC, id DESC`. Documents/history use their event timestamp DESC plus id DESC. Stable tie-breaking is required across pages; do not sort random pages independently and call that global ordering.
- Auth choice for this specification: opaque server-side session in a Secure, HttpOnly cookie, with expiration/revocation. State-changing requests require CSRF protection. Login/bootstrap provides the CSRF mechanism; do not expose the session secret in JSON or localStorage. Cross-origin deployment requires an explicit credentialed CORS allowlist. A future bearer-token design must replace this section with a refresh/revocation contract.
- Role and project checks are server-authoritative. Do not return password hashes, reset/invitation token hashes, private object keys, or internal audit secrets. Return capabilities to guide UI controls, but always recheck at mutation time.
- POST payment, receipt, inventory movement, approval, and billing-posting requests require `Idempotency-Key`. Store operation keys/results with a documented retention window; retries with the same key/body return the original result, while a different body returns 409. This needs a supporting persistence mechanism beyond the 41 domain entities.
- Mutable DTOs include `version: int`. Updates/approvals provide `expected_version: int` and use atomic version checks; stale writes return 409. Add version columns to affected production models/migrations. A version check does not replace row locks for financial aggregates.
- Upload size/format limits are configured by the backend, not the prototype's 1 MB limit. Validate file signatures, malware-scan, and keep storage private. Multipart money/metadata fields follow the same string conventions. Failed database/object-storage operations require compensation.

### Authorization Legend

| Code | Meaning |
|---|---|
| Public | Unauthenticated, rate-limited; generic account-discovery responses |
| Auth | Active authenticated account; only its own profile/session unless explicitly stated |
| Project Read | Project membership plus module read permission; Owner/MD company-wide read only where granted |
| Project Write | Project membership plus the named action permission; Owner access follows explicit policy |
| User Admin | Owner, or assigned Admin limited to operational Supervisor/Cashier accounts; no self/last-Owner lockout |
| Finance | Explicit billing/vendor-payment permission and project scope; Cashier only where granted |
| Approver | Explicit approval permission, threshold and project scope; role name alone is insufficient |
| Company Read | Explicit company-wide reporting/catalog read permission |

Supervisor procurement permissions do not automatically grant vendor payment authorization. Managing Director has company-wide read and specifically granted approvals, not general mutation rights. Reference-master write permissions are configured explicitly.

## 3. Screen Loading Map

| Screen / trigger | APIs to load | Reason and refresh after mutation |
|---|---|---|
| Login | GET /auth/bootstrap; POST /auth/login; GET /me | CSRF bootstrap, authentication, profile/capabilities; then load authorized projects |
| Password Reset / invitation | POST reset request/complete or invitation accept | Account recovery/first password; return to Login, not automatic privileged login |
| App shell | GET /me; GET /me/projects | User, navigation permissions, project switcher; clear cache on logout/account change |
| All Projects | GET /me/projects; GET /reports/portfolio | Cards and portfolio KPIs over the same authorized/filter scope; invalidate after project/status/value approval |
| Create Project | POST /projects; optional POST project documents | Persist Planning project then optional initial approval file; retry failed upload without recreating project |
| Project Overview | GET project detail/dashboard, status-history, documents, value-history; GET purchase-orders?page_size=3 | Project totals, recent activity, approved/proposed values and plan files; load history lazily if collapsed |
| Change Status dialog | PATCH project status | Append actor/comment history; refresh detail, dashboard, portfolio and status history |
| Upload Plan dialog | GET project detail; POST project documents | Show approved value read-only; submit revised estimate; refresh documents/value proposals, not approved value until approval |
| Procurement | GET purchase-orders; GET procurement-summary | Rows and full filtered totals; loading one page must not define KPI totals |
| New/Edit PO dialog | GET vendors, inventory-items, cost-codes; GET PO detail when editing | Select references and line items; refresh register, summary, recent orders and project inventory after save |
| Add Payment / Payment History | GET PO detail/payments; POST payments; receipt-content GET on demand | Current balance and immutable installment ledger; refresh PO and summaries after payment |
| Inventory | GET project inventory, inventory-summary, locations | Ordered/received/available stock; use ledger history only on item detail |
| Receipt / movement dialog (**planned**) | GET PO/receipt detail or stock/locations; POST receipts or inventory-transactions | Actual goods acceptance and stock movement; refresh inventory, commitments and dashboard |
| Progress Billing | GET contracts, progress-billings, billing-summary | Contract and billing list; contract detail/history on selection |
| Billing/Invoice/Collection dialogs (**planned**) | GET schedule-of-values/invoices; POST billing, invoice, client-payment/allocation | Commercial posting and collections; refresh billing summary, balances and dashboard |
| Attendance | GET timecards, attendance-summary; GET employees/cost-codes | Date-filtered hours, approval state and rate-based costs; refresh after log/approve/correct |
| Users | GET users, roles, permissions; GET memberships on selection | User lifecycle and access management; refresh affected users/capabilities after writes |
| Catalogs, Approvals, Audit, Reports (**planned**) | Domain reference, approval-event, audit and report endpoints | Master maintenance, decision history and reconciliation; permission-gated screens |

In React/TanStack Query, include user scope, project_id, filters, page and selected contract/item in query keys. Cancel/ignore stale requests on project switch. Never reuse cached financial data across users. A failed widget displays its own error/retry state instead of silently showing zero.

## 4. Endpoint Catalog

### 4.1 Authentication and Current User

| API name / UI purpose | Method and path | Input | Response type / access |
|---|---|---|---|
| Bootstrap authentication / Login | GET /auth/bootstrap | None | AuthBootstrap; Public; sets pre-auth CSRF cookie |
| Login / Login form | POST /auth/login | JSON username, password; CSRF header | AuthenticatedSession; Public; sets session cookie |
| Logout / App shell | POST /auth/logout | CSRF header | 204; Auth; revokes current session |
| Current user / App shell | GET /me | None | Me; Auth |
| My sessions / Account settings (**planned**) | GET /me/sessions | Pagination | Page<Session>; Auth |
| Revoke session / Account settings (**planned**) | DELETE /me/sessions/{session_id} | Path session_id; CSRF | 204; Auth; own session only |
| Change password / Account settings (**planned**) | POST /me/password | current_password, new_password | Message; Auth; revoke other sessions |
| Request password reset / Reset screen | POST /auth/password-reset/request | identity (username/email) | 202 Message; Public; same response for known/unknown identity |
| Complete reset / Reset screen | POST /auth/password-reset/complete | token, new_password | Message; Public; single-use token, revoke sessions |
| Accept invitation / First login (**planned**) | POST /auth/invitations/accept | token, new_password | Message; Public; validates expiry and recipient |

### 4.2 Users, Roles, and Memberships

| API name / UI purpose | Method and path | Input | Response type / access |
|---|---|---|---|
| List users / Users | GET /users | Pagination; search?, role?, active? | Page<User>; User Admin; only manageable accounts |
| Invite user / Add User | POST /users | name, username, email, role_codes, project_ids | 201 User; User Admin; send invitation, never return token |
| User detail / Edit User | GET /users/{user_id} | user_id | User; User Admin |
| Edit user / Edit User | PATCH /users/{user_id} | name?, username?, email?, expected_version | User; User Admin; email change requires re-verification |
| Activate/deactivate / Users | PATCH /users/{user_id}/status | active, expected_version | User; User Admin; deactivation revokes sessions |
| Replace active role grants / Users | PUT /users/{user_id}/roles | role_codes, expected_version | User; User Admin; revoke old grants without erasing history |
| View project assignments / User access | GET /users/{user_id}/memberships | Pagination; active_only? | Page<Membership>; User Admin |
| Replace active assignments / User access | PUT /users/{user_id}/projects | project_ids, expected_version | User; User Admin; full desired set, preserve grant/revoke history |
| Send account reset / Users | POST /users/{user_id}/password-reset | None | 202 Message; User Admin; email link, no reset code in response |
| Retire account / Users | DELETE /users/{user_id} | expected_version query; CSRF | 204; User Admin; retained audit identity, not ledger cascade deletion |
| Available roles / User form | GET /roles | None | Role[]; User Admin; only assignable roles |
| Permission catalog / Access admin (**planned**) | GET /permissions | None | Permission[]; Owner |
| Replace role permissions / Access admin (**planned**) | PUT /roles/{role_id}/permissions | permission_codes, expected_version | Role; Owner; preserve critical Owner controls and audit |

### 4.3 Projects, Overview, Documents, and Value History

Use `P = /projects/{project_id}` below. Expand P literally when implementing/OpenAPI generation.

| API name / UI purpose | Method and path | Input | Response type / access |
|---|---|---|---|
| My projects / Portfolio and switcher | GET /me/projects | Pagination; search?, status? | Page<ProjectSummary>; Auth; authorized scope |
| Project register / Management (**planned**) | GET /projects | Pagination; search?, status? | Page<ProjectSummary>; authorized scope; same visibility rules as /me/projects |
| Create project / Create dialog | POST /projects | name, location, baseline_budget, currency?, start_date, estimated_end_date?, initial_contract_value | 201 ProjectDetail; project-create permission; create initial contract transactionally |
| Project detail / Overview and upload dialog | GET P | project_id | ProjectDetail; Project Read |
| Update project metadata / Project settings (**planned**) | PATCH P | name?, location?, estimated_end_date?, expected_version | ProjectDetail; Project Write; no direct contract/status overwrite |
| Change project status / Status dialog | PATCH P/status | status, comment, hold_reason?, completion_note?, confirm_complete?, expected_version | ProjectDetail; Project Write; completion requires confirmation |
| Status history / Overview | GET P/status-history | Pagination | Page<StatusEvent>; Project Read |
| Dashboard / Overview | GET P/dashboard | as_of? | ProjectDashboard; Project Read; redact unpermitted financial fields |
| Project documents / Overview | GET P/documents | Pagination; category? | Page<ProjectDocument>; Project Read |
| Upload initial/revised plan / Upload dialog | POST P/documents | Multipart file, category, comment, proposed_value? (required for revised_plan), contract_id, effective_date?, expected_contract_version | 201 DocumentUploadResult; Project Write; eligible project statuses only |
| Document detail / File list | GET P/documents/{document_id} | Project document association ID | ProjectDocument; Project Read |
| Download/open project document / File link | GET P/documents/{document_id}/content | document_id | DownloadLink; Project Read; short-lived URL after scan/access checks |
| Delete plan association / Delete dialog | DELETE P/documents/{document_id} | reason; expected_version query | 204; uploader or authorized Owner/Admin within project scope; preserve revision history |
| Value proposal/history / Overview | GET P/value-history | Pagination; approval_status? | Page<ValueRevision>; project commercial read permission |
| Value revision detail / Approval (**planned**) | GET P/value-revisions/{revision_id} | revision_id | ValueRevisionDetail; commercial read permission |
| Approve/reject revision / Approval (**planned**) | POST P/value-revisions/{revision_id}/decision | decision, comment, expected_version, expected_contract_version | ValueRevisionDetail; Approver; approved revision applies once |

Initial project upload is a separate request after creation; failure must not recreate the project. Upload returns a pending proposal for a revised plan, not an immediately approved contract increase. Document deletion retains metadata and approved value history; an unapproved proposal linked to the deleted file requires rejection/withdrawal policy. Generic document metadata and private storage fields are not exposed through an unrestricted global document endpoint.

### 4.4 Reference Masters

The following patterns apply separately to each exact resource: `/vendors`, `/inventory-items`, `/cost-codes`, and `/employees`.

| API name / UI purpose | Method and path | Input | Response type / access |
|---|---|---|---|
| Search master / PO, stock, timecard forms | GET /{resource} | Pagination; search?, active? | Page<Vendor>, Page<InventoryItem>, Page<CostCode>, or Page<Employee>; module reference-read permission |
| Read master / Detail (**planned**) | GET /{resource}/{id} | id | Corresponding master DTO; reference-read permission |
| Create master / Catalog form (**planned**) | POST /{resource} | VendorInput, InventoryItemInput, CostCodeInput, or EmployeeInput | 201 corresponding master DTO; explicit master-write permission |
| Update/deactivate master / Catalog form (**planned**) | PATCH /{resource}/{id} | Allowed master fields?, active?, expected_version | Corresponding master DTO; explicit master-write permission |

No deletion of master records referenced by financial/stock/labor records. Creating a catalog item does not grant access to projects or create stock. Item classification (stock/service/rental) must be added to the inventory master model before stock receipt validation is implemented.

### 4.5 Procurement and Vendor Payments

Use `PO = P/purchase-orders/{po_id}`.

| API name / UI purpose | Method and path | Input | Response type / access |
|---|---|---|---|
| PO list / Procurement, recent orders | GET P/purchase-orders | Pagination; search?, vendor_id?, payment_status?, date_from?, date_to? | Page<PurchaseOrderSummary>; Project Read |
| Procurement KPIs / Procurement | GET P/procurement-summary | Same filters as list, without pagination | ProcurementSummary; Project Read |
| Create PO / New PO dialog | POST P/purchase-orders | vendor_id, order_date, lines: POLineInput[], currency? | 201 PurchaseOrderDetail; Project Write; upsert project/item links |
| PO detail / Edit/payment dialog | GET PO | po_id | PurchaseOrderDetail; Project Read |
| Edit PO / Edit dialog | PATCH PO | vendor_id?, order_date?, lines?, expected_version | PurchaseOrderDetail; Project Write; lines replace full desired line set, retain posted references |
| Approval history / Approval (**planned**) | GET PO/approval-events | Pagination | Page<ApprovalEvent>; Project Read |
| Submit/approve/reject/cancel PO / Approval (**planned**) | POST PO/decision | action, comment, expected_version | PurchaseOrderDetail; action-specific submit/cancel/Approver permission |
| Payment ledger / Payment History | GET PO/payments | Pagination | Page<VendorPayment>; procurement/payment read permission |
| Record installment / Add Payment | POST PO/payments | Multipart amount, payment_date, reference?, comment?, receipt_file?, expected_version | 201 VendorPaymentResult; Finance; enforce outstanding balance |
| Reverse payment / Finance correction (**planned**) | POST PO/payments/{payment_id}/reversal | reason, payment_date, expected_version | 201 VendorPaymentResult; explicit finance reversal permission |
| View payment receipt / Payment History | GET PO/payments/{payment_id}/receipt-content | payment_id | DownloadLink; authorized payment read; 404 if no receipt |

Payment response includes refreshed PO totals/version. Fully paid PO edit is rejected server-side, not just disabled in the UI. Reject reducing quantity below accepted receipts, removing receipt-linked lines, and altering stock identity after posting. Amendments/cancellation of partially received orders require an audited lifecycle policy.

### 4.6 Inventory and Goods Receipts (Posting Workflows Planned)

| API name / UI purpose | Method and path | Input | Response type / access |
|---|---|---|---|
| Project inventory / Inventory | GET P/inventory | Pagination; search?, item_id?, location_id? | Page<ProjectStock>; Project Read |
| Inventory totals / Inventory | GET P/inventory-summary | location_id?, as_of? | InventorySummary; Project Read |
| Item stock detail / Inventory item (**planned**) | GET P/inventory/{item_id} | item_id, location_id? | ProjectStockDetail; Project Read |
| Stock ledger / Inventory item (**planned**) | GET P/inventory-transactions | Pagination; item_id?, type?, date_from?, date_to? | Page<InventoryTransaction>; Project Read |
| Locations / Movement form | GET /inventory-locations | Pagination; project_id?, search? | Page<InventoryLocation>; only authorized project/central warehouse scope |
| Create location / Inventory setup (**planned**) | POST /inventory-locations | project_id?, name | 201 InventoryLocation; explicit location-write permission |
| Receipt list / PO receipt history (**planned**) | GET PO/receipts | Pagination | Page<GoodsReceipt>; Project Read |
| Record receipt / Receipt dialog (**planned**) | POST PO/receipts | received_at, delivery_reference?, lines: ReceiptLineInput[], expected_version | 201 GoodsReceiptResult; Project Write; posts receipt and stock atomically |
| Receipt detail / Receipt history (**planned**) | GET PO/receipts/{receipt_id} | receipt_id | GoodsReceipt; Project Read |
| Allocate/issue/transfer/return / Inventory dialog (**planned**) | POST P/inventory-transactions | InventoryMovementInput | 201 InventoryTransaction; movement-specific Project Write; validate both locations/projects |
| Reverse movement / Correction (**planned**) | POST P/inventory-transactions/{transaction_id}/reversal | reason, occurred_at | 201 InventoryTransaction; explicit stock-reversal permission |

Do not allow ordinary receipt postings through the generic movement API: receipt stock comes from PO receipt lines. Reversing a goods receipt must coordinate accepted-quantity and stock effects atomically, reject already-consumed unavailable stock, and preserve original acceptance records. The current entity blueprint needs a defined receipt-correction/reversal linkage before shipping that operation; do not reverse stock alone while leaving open-order quantities incorrect. Transfers require source and destination authorization and location locking. Central-warehouse-only operations need a separately scoped warehouse route/policy if they are in scope.

### 4.7 Contracts, Billing, and Collections (Detailed Workflows Planned)

Use `C = P/contracts/{contract_id}`.

| API name / UI purpose | Method and path | Input | Response type / access |
|---|---|---|---|
| Contracts / Progress Billing selector | GET P/contracts | Pagination | Page<Contract>; billing read permission |
| Contract detail / Billing header | GET C | contract_id | Contract; billing read permission |
| Additional contract / Commercial setup | POST P/contracts | number, original_value, currency, retainage_rate | 201 Contract; explicit contract-create permission |
| Schedule of values / Billing form | GET C/schedule-of-values | Pagination | Page<ScheduleLine>; billing read permission |
| Replace schedule / Commercial setup | PUT C/schedule-of-values | lines: ScheduleLineInput[], expected_version | ContractSchedule; commercial-write permission; preserve billed line IDs |
| Change orders / Contract history | GET C/change-orders | Pagination; status? | Page<ChangeOrder>; billing read permission |
| Propose change / Change-order form | POST C/change-orders | amount_delta, comment, effective_date, expected_contract_version | 201 ChangeOrder; commercial-write permission |
| Decide change order / Approval | POST C/change-orders/{change_order_id}/decision | decision, comment, expected_version, expected_contract_version | ChangeOrder; Approver |
| Billing summary / Progress Billing | GET P/billing-summary | contract_id?, as_of? | BillingSummary; billing read permission |
| Progress billings / Progress Billing | GET P/progress-billings | Pagination; contract_id?, status?, period_from?, period_to? | Page<ProgressBillingSummary>; billing read permission |
| Create billing draft / New Billing | POST C/progress-billings | period_start, period_end, lines: BillingLineInput[] | 201 ProgressBillingDetail; Finance |
| Billing detail / Billing drawer | GET P/progress-billings/{billing_id} | billing_id | ProgressBillingDetail; billing read permission |
| Update billing draft / Billing form | PATCH P/progress-billings/{billing_id} | period_start?, period_end?, lines?, expected_version | ProgressBillingDetail; Finance; draft only |
| Submit/approve/reject billing / Approval | POST P/progress-billings/{billing_id}/decision | action, comment, expected_version | ProgressBillingDetail; Finance for submit, Approver for decisions |
| Invoice register / Collections | GET P/invoices | Pagination; contract_id?, outstanding_only?, date_from?, date_to? | Page<Invoice>; billing read permission |
| Issue billing invoice / Approved billing | POST P/progress-billings/{billing_id}/invoices | number, issued_date, due_date, expected_version | 201 Invoice; Finance; calculate amount server-side, prevent duplicate issue |
| Invoice detail / Collections | GET P/invoices/{invoice_id} | invoice_id | Invoice; billing read permission |
| Client payment register / Collections | GET C/client-payments | Pagination | Page<ClientPayment>; billing read permission |
| Record client receipt / Collections | POST C/client-payments | amount, payment_date, reference?, allocations?: AllocationInput[] | 201 ClientPayment; Finance; post allocations atomically |
| Allocate existing receipt / Collections | POST C/client-payments/{payment_id}/allocations | allocations: AllocationInput[], expected_version | ClientPayment; Finance |
| Reverse client receipt / Correction | POST C/client-payments/{payment_id}/reversal | reason, payment_date, expected_version | 201 ClientPayment; explicit finance reversal permission |
| Release retainage / Closeout | POST P/progress-billings/{billing_id}/lines/{line_id}/retainage-releases | amount, released_at, comment | 201 RetainageRelease; Approver |

No direct overwrite of an approved contract value. Manual change proposals and document revisions must share one approval/application service; a linked revision/change-order cannot apply twice. Issued invoice credit notes, tax treatment, retainage invoicing, and general-ledger integration require supplementary modeling before complete accounting workflows can ship.

### 4.8 Attendance and Labor

| API name / UI purpose | Method and path | Input | Response type / access |
|---|---|---|---|
| Timecards / Attendance | GET P/timecards | Pagination; date_from?, date_to?, employee_id?, status? | Page<Timecard>; attendance read permission |
| Attendance KPIs / Attendance | GET P/attendance-summary | date_from, date_to | AttendanceSummary; attendance read; redact cost if not permitted |
| Log time / Log Hours | POST P/timecards | employee_id, work_date, cost_code_id, regular_hours, overtime_hours | 201 Timecard; timecard-create permission; server assigns acting supervisor |
| Timecard detail / Review | GET P/timecards/{timecard_id} | timecard_id | Timecard; attendance read permission |
| Edit pending time / Review | PATCH P/timecards/{timecard_id} | work_date?, cost_code_id?, regular_hours?, overtime_hours?, expected_version | Timecard; timecard-write permission; pending only |
| Approval history / Review | GET P/timecards/{timecard_id}/approval-events | Pagination | Page<ApprovalEvent>; attendance read permission |
| Approve/reject time / Review | POST P/timecards/{timecard_id}/decision | decision, comment, expected_version; captured rates if authorized override | Timecard; timecard-approve permission; capture approved rates |
| Correct approved time / Correction | POST P/timecards/{timecard_id}/corrections | reason, work_date, cost_code_id, regular_hours, overtime_hours, expected_version | 201 Timecard; correction permission; creates pending replacement |

Employee selection does not imply employee login. Validate employee active status, nonoverlapping/allowed work hours, and overtime policy. Approved-time corrections preserve the original and must use an explicit reporting rule for pending replacements versus superseded approved costs.

### 4.9 Reports and Audit (Planned)

| API name / UI purpose | Method and path | Input | Response type / access |
|---|---|---|---|
| Portfolio KPIs / All Projects | GET /reports/portfolio | status?, search?, as_of? | PortfolioReport; authorized scope; company-wide only with Company Read |
| Project costing / Overview/report | GET /reports/job-costing | project_id, as_of?, cost_code_id? | JobCostReport; project finance/report-read permission |
| Export project report / Export | GET /reports/job-costing/export | Same filters, format=csv | text/csv download; report-export permission |
| Export attendance / Attendance Export | GET P/timecards/export | date_from, date_to; employee_id? | text/csv download; attendance-export permission |
| Audit trail / Audit console | GET /audit-events | Pagination; project_id?, entity_type?, entity_id?, action?, date_from?, date_to? | Page<AuditEvent>; explicit audit-read permission; filter authorized scope |

CSV uses the same scope/metric rules as JSON, protects against spreadsheet formula injection, and has server-enforced size limits. Large asynchronous exports require a future job/status/download contract, not an indefinitely running HTTP request. Audit project filtering requires a reliable scope field/index or validated scope mapping in the audit persistence design.

## 5. Input Types

These named schemas define the payloads used in the tables. Pydantic models must reject unsupported writable fields. PATCH is a partial schema plus expected_version; PUT represents a full desired collection and is not a partial update.

| Input type | Fields |
|---|---|
| VendorInput | name: string; email?, phone?, address?, tax_identifier?: string |
| InventoryItemInput | sku, name, category, unit_of_measure: string; classification: stock/service/rental |
| CostCodeInput | code, name, category: string |
| EmployeeInput | employee_number, name: string; default_hourly_rate: decimal string |
| POLineInput | id?: UUID for existing line; item_id, cost_code_id: UUID; description: string; quantity, unit_price: decimal string |
| ReceiptLineInput | purchase_order_line_id: UUID; quantity_accepted: decimal string |
| InventoryMovementInput | type: allocation/issue/transfer/return; item_id: UUID; cost_code_id?, source_location_id?, destination_location_id?: UUID; quantity: decimal string; occurred_at: timestamp; reason: string; expected_stock_versions?: map of location/item to version; valuation derived server-side |
| ScheduleLineInput | id?: UUID; cost_code_id: UUID; description: string; scheduled_amount: decimal string |
| BillingLineInput | schedule_of_value_id: UUID; current_work_amount: decimal string; retainage computed server-side |
| AllocationInput | invoice_id: UUID; amount: decimal string |

All referenced IDs are access-checked; existence alone is not authorization. Rates, amount limits, and cumulative work/retainage are validated against the applicable contract/policy. Dynamic capability names and allowed state transitions are returned by the server rather than duplicated as independent frontend policy.

## 6. Response Types

DTO names here are wire contracts, not raw SQLAlchemy serialization. Nested references use `Ref = {id: UUID, name: string}` unless explicitly expanded. Each mutable response has version; money objects carry currency at parent level. All collection endpoints use Page<T> unless listed as a bounded array.

### Identity and Projects

| Response type | Fields |
|---|---|
| Message | message: string; no identity/token details |
| AuthBootstrap | csrf_token: string; session secret never returned |
| AuthenticatedSession | user: Me; expires_at: timestamp; csrf_token: string |
| Me | id, username, email, name, active, role_codes: string[], capabilities: string[]; company_wide_read: boolean |
| User | Me fields; version; email_verified: boolean; assigned_project_ids: UUID[]; manageable_actions: string[] |
| Role | id, code, permission_codes: string[]; version |
| Permission | id, code, description? |
| Session | id, created_at, expires_at, revoked_at?; current: boolean; sanitized device description? |
| Membership | id; user: Ref; project: Ref; granted_at, revoked_at?; grantor: Ref |
| ProjectSummary | id, name, location, status, currency, baseline_budget; approved_contract_value?: decimal; pending_proposal_count; version; capabilities: string[] |
| ProjectDetail | ProjectSummary plus start_date, estimated_end_date?, contracts: ContractRef[]; current_status_note?; created_at, updated_at |
| ContractRef | id, number, currency; approved_value: decimal; version |
| StatusEvent | id, previous_status, new_status, comment, hold_reason?, completion_note?, occurred_at; actor: Ref |
| ProjectDocument | id (association ID), file_id, filename, mime_type, byte_size, category, comment, uploaded_at; uploader: Ref; scan_status: pending/clean/rejected; version; can_delete: boolean |
| DocumentUploadResult | document: ProjectDocument; value_revision?: ValueRevision; scan may be pending; file access blocked until clean |
| DownloadLink | url: short-lived signed HTTPS URL; expires_at: timestamp; filename, mime_type |
| ValueRevision | id, contract_id, previous_value, proposed_value, currency, effective_date, approval_status; proposer: Ref; source_document?: ProjectDocument; version |
| ValueRevisionDetail | ValueRevision plus events: ApprovalEvent[]; applied_change_order_id?: UUID; refreshed_contract: ContractRef |
| ApprovalEvent | id, action, comment, occurred_at; actor: Ref |

Document scan state needs a supporting metadata field/lifecycle in the production model. Deleted source documents in history use retained metadata with availability/deleted flags, not a live download link. Multiple contracts are explicit: project approved value aggregates compatible currency contracts, rather than arbitrarily selecting one.

### Operations

| Response type | Fields |
|---|---|
| Vendor | id, name, email?, phone?, address?, tax_identifier?, active, version |
| InventoryItem | id, sku, name, category, unit_of_measure, classification, active, version |
| CostCode | id, code, name, category, active, version |
| Employee | id, employee_number, name, active, version; default_hourly_rate? if permitted |
| PurchaseOrderSummary | id, number, order_date; vendor: Ref; item_names: string[]; currency, total, paid_to_date, balance, payment_status, approval_status, version; can_edit, can_add_payment, can_view_history: boolean |
| PurchaseOrderDetail | PurchaseOrderSummary plus lines: POLine[]; created_at, updated_at; permitted_actions: string[] |
| POLine | id; item: InventoryItem; cost_code: Ref; description, quantity, unit_price, line_total, accepted_quantity, open_quantity |
| VendorPayment | id, amount, payment_date, reference?, comment?, recorded_at; recorded_by: Ref; reversal_of_id?: UUID; receipt?: {filename, mime_type, available: boolean} |
| VendorPaymentResult | payment: VendorPayment; purchase_order: PurchaseOrderSummary |
| ProcurementSummary | order_count, currency, total_ordered, total_paid, outstanding_balance; applied_filters; as_of: timestamp |
| InventoryLocation | id, project_id?, name, version |
| ProjectStock | item: InventoryItem; ordered_quantity, open_order_quantity, received_quantity, consumed_quantity, available_quantity; location_id?; unit_of_measure; as_of: timestamp |
| ProjectStockDetail | ProjectStock plus locations: StockLocationBalance[]; transaction list loaded separately |
| StockLocationBalance | location: Ref; available_quantity; stock_version: int |
| InventorySummary | catalog_item_count, stocked_item_count, low_stock_item_count?; valuation_amount?: decimal; currency; as_of: timestamp; never sum incompatible units |
| InventoryTransaction | id, type; item: Ref; project_id?, cost_code_id?, source_location_id?, destination_location_id?, receipt_line_id?, reversal_of_id?; quantity, unit_cost?, occurred_at; actor: Ref |
| GoodsReceipt | id, purchase_order_id, received_at, delivery_reference?; receiver: Ref; lines: {id, purchase_order_line_id, quantity_accepted}[] |
| GoodsReceiptResult | receipt: GoodsReceipt; purchase_order: PurchaseOrderSummary; inventory_posting_ids: UUID[] |

Inventory quantity totals must define transfer/return/reversal effects; available quantity is a ledger/location balance, not simply received minus consumed when transfers exist. PO summary total is always based on every line, not item_names or a partial line preview.

### Billing, Attendance, and Reports

| Response type | Fields |
|---|---|
| Contract | id, project_id, number, currency, original_value, approved_change_total, approved_value, retainage_rate, version |
| ChangeOrder | id, contract_id, value_revision_id?, amount_delta, status, approved_at?, approver?: Ref; version; refreshed_contract: ContractRef |
| ScheduleLine | id, contract_id; cost_code: Ref; description, scheduled_amount, previously_billed_amount, remaining_amount |
| ContractSchedule | contract_id, lines: ScheduleLine[], total_scheduled, version |
| ProgressBillingSummary | id, contract_id, period_start, period_end, status, currency, current_work_total, retainage_total, net_billable, version |
| ProgressBillingDetail | ProgressBillingSummary plus lines: {id, schedule_of_value_id, current_work_amount, retainage_amount}[]; permitted_actions: string[] |
| Invoice | id, contract_id, progress_billing_id?, number, issued_date, due_date, currency, total, paid_to_date, balance; payment_allocations: {id, payment_id, amount}[] |
| ClientPayment | id, contract_id, amount, currency, payment_date, reference?, recorded_at; recorded_by: Ref; reversal_of_id?; allocated_amount, unallocated_amount, version; allocations: {id, invoice_id, amount}[] |
| RetainageRelease | id, billing_line_id, amount, released_at; approver: Ref; remaining_retained_amount |
| BillingSummary | currency, approved_contract_value, billed_work, invoiced_amount, cash_received, outstanding_invoices, retainage_held, retainage_released; as_of: timestamp |
| Timecard | id, project_id; employee: Ref; cost_code: Ref; supervisor: Ref; work_date, regular_hours, overtime_hours, status, captured_regular_rate?, captured_overtime_rate?, labor_cost?, supersedes_id?, version; permitted_actions: string[] |
| AttendanceSummary | date_from, date_to, regular_hours, overtime_hours, pending_count, approved_count; labor_cost?, currency |
| ProjectDashboard | project_id, as_of, currency; budget?, approved_contract_value?, actual_cost?, open_commitments?, invoiced_amount?, cash_received?, forecast_cost?, margin_percent?; cost_breakdown?: {cost_code_id, amount}[] |
| PortfolioReport | as_of, project_count, counts_by_status; totals_by_currency: {currency, budget?, approved_contract_value?, actual_cost?, open_commitments?}[]; applied_filters |
| JobCostReport | project_id, as_of, currency; totals: {budget, actual_cost, open_commitments, forecast_cost}; cost_codes: {id, name, budget, material_cost, labor_cost, commitment, forecast}[] |
| AuditEvent | id, actor?: Ref, action, entity_type, entity_id?, occurred_at, request_id?; before?, after?: sanitized JSON objects |

Financial fields unavailable to a user are omitted or null with an explicit capability, never silently returned as zero. Finance must approve metric definitions, as-of date behavior, forecasting method, and currency aggregation before these reports are acceptance-tested. No cross-currency sum without an agreed FX model.

## 7. Error Contract and HTTP Semantics

Every error returns `ErrorResponse = {error: {code: string, message: string, details?: FieldError[]}, request_id: string}`. FieldError is `{field: string, code: string, message: string}`. Never expose database traces, tokens, private keys, or passwords. Translate FastAPI validation errors into this envelope consistently.

| HTTP status | Example code / frontend behavior |
|---|---|
| 400 | invalid_filter or invalid_operation; show actionable request error |
| 401 | unauthenticated/session_expired; clear protected cache and return to Login |
| 403 | permission_denied/invalid_csrf; do not retry as another scope |
| 404 | not_found; also used for out-of-scope child resources to prevent enumeration |
| 409 | stale_version, already_applied, fully_paid_order, overpayment, insufficient_stock, idempotency_conflict; refetch affected resource before retry |
| 413 | upload_too_large; display configured limit |
| 415 | unsupported_file_type/media_type |
| 422 | validation_failed; attach errors to named form fields |
| 429 | rate_limited; honor Retry-After, including auth/reset endpoints |
| 503 | service_unavailable/upload_scan_pending; use documented retry policy, do not resubmit financial writes with a new idempotency key |

Empty lists return 200 Page<T> with items=[] and total=0, not 404. POST response Location headers identify newly created resources. Authorization failures cannot be corrected only by changing a disabled button in the frontend.

## 8. Backend and Frontend Acceptance Checklist

- Every listed endpoint has an OpenAPI operation_id, concrete request/response schemas, examples, documented statuses, and an explicit permission dependency. Expand P/PO/C and master patterns into concrete routes.
- Scope tests cover cross-project IDs, unauthorized roles, deactivated users, stale versions, last-Owner protection, duplicate requests, and poisoned reference IDs.
- Financial tests cover partial/full/reversed payments, fully paid edit rejection, receipt idempotency, stock concurrency, allocation limits, approved revisions applied once, and aggregate join multiplication.
- UI tests cover loading, empty, forbidden, error/retry, file-scanning, stale-data and success states; screen query invalidation is verified after each mutation.
- Frontend never submits actor IDs or trusts its own balance/contract totals as authoritative. Rate/cost access and export permissions match JSON response permissions.
- Resolve model additions called out here: versions, scan status, item classification, change-order comments/effective dates and approval-event persistence, idempotency storage, stock concurrency keys, and receipt-correction linkage. This catalog extends the blueprint; reconcile those fields in models/migrations before implementation.
- Native mobile, multi-tenant SaaS, general-ledger posting, tax/credit-note flows, asynchronous exports and full warehouse-only operations remain explicit future scope unless approved separately.