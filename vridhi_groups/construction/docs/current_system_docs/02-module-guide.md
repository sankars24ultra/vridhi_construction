# 2. Left-Menu Module Guide

[Documentation home](README.md) | [Walkthroughs](03-workflow-walkthroughs.md)

## Menu and scope map

| Menu | Project required? | Main purpose |
|---|---|---|
| Projects | No | Choose a project; view portfolio; start New Project |
| Overview | Yes | Project health, costs, status and plan documents |
| Procurement | Yes | Purchase orders and vendor payments |
| Inventory | Yes | Ordered/received/used materials and stock ledger |
| Cash flow | Yes | Client billing applications and cash receipts |
| Labor and Wages | Yes | Direct workers and subcontract labor |
| Users | No | All-user directory, account lifecycle and permissions |
| Audit Log | Yes | Recorded activity for the selected project |

Only permitted project modules appear. Users requires its own page permission;
Audit Log requires separate audit access plus access to the selected project.

## Projects

**Abstract:** the portfolio is the entry point to project work.

Cards summarize accessible projects, including status, location, contract value,
and actual cost. Status grouping helps locate a project. WORKSPACE provides
another way to switch context. New Project opens the project form; its API requires
Overview write authorization, so button visibility alone does not guarantee creation.

New projects accept name, location, approved budget, contract value, start date,
Planning/Active initial status, and an optional initial plan file/comment.

## Overview

**Abstract:** a consolidated project snapshot, not a complete accounting statement.

- Contract value, actual cost, open procurement commitments and projected margin.
- Cost composition and monthly cost visualization.
- Client cash information when Cash flow access is available.
- Recent purchase orders when Procurement access is available.
- Plan documents, downloadable through the Download icon.
- Current project status and status-change history.
- Project value history associated with revised plans.

Permissioned actions: Export Report, Quick Entry, Upload Plan Document, Update
Status. Quick Entry currently opens purchase-order creation; the actual save
also requires Procurement create/edit permission.

Users allowed only Overview can still export it. Restricted Procurement/Cash flow
sections remain empty; they should not trigger forbidden data requests.

## Procurement

**Abstract:** records what the project has ordered and what it owes vendors.

KPIs show order count, total ordered, total paid, and outstanding balance. The
register is newest order date first, with search, payment-state filters, and
pagination (10, 20, 50, 100, 200).

- Create a PO with vendor, line items, quantities/prices and supported optional image.
- Edit eligible POs using the same **Create / Edit Purchase Order** grant.
- Add installments through the independent **Add Payment** grant.
- Review payment history even when no write action is granted.
- Fully paid orders keep the existing edit/payment restrictions.
- Optional PO images accept PNG/JPG/WEBP up to 10 MB.

Do not treat a PO as a stock receipt. Material receipt/use is recorded in Inventory.

## Inventory

**Abstract:** tracks physical material flow separately from purchasing money.

Project material rows show ordered, open-to-receive, received, consumed, and
available quantities, with vendor/unit/cost information. Search, material filtering,
pagination and Stock ledger help trace movement.

- **Receive Stock** records a receipt, optionally against an eligible PO line.
- **Use Stock** records site consumption.
- Receive and Use have separate action grants.
- Stock ledger records type, quantity, cost, reference, notes, recorder and timestamp.
- Stock value is the remaining-stock valuation, not total PO value.

Quantities in different units must not be interpreted as a single meaningful
physical quantity simply because the UI aggregates them.

## Cash flow

**Abstract:** tracks money billed to and received from the client, not vendor payments.

KPIs: approved contract value, billed to client, cash received and billed outstanding.
Separate registers show billing applications and receipts, with independent search
and pagination (10, 20, 50, 100).

- **New Application** records a billing application amount and description.
- **Record Receipt** records a dated amount, payment method, reference/comment,
  and optional allocation to a billing application.
- An allocated receipt cannot exceed that application's outstanding amount.
- An unallocated receipt increases cash received but does not automatically settle
  a specific application's balance.

Do not assume a complete retention-release or invoice-approval engine: the current
summary exposes zero retention values rather than a full retention workflow.

## Labor and Wages

**Abstract:** supports two distinct ways of recording labor cost.

| Direct workers | Subcontract labor |
|---|---|
| Add/edit worker and trade/contact details | Create unit-rate or lump-sum contract |
| Log work quantity, unit, rate and description | Link baseline plan and supporting contract file |
| Record wage payments | Submit progress claims and contract changes |
| Review earned, paid and payable totals | Review/certify claims and approve/reject changes |
| Activate/deactivate workers | Pay eligible certified claims; view history/files |

The screen contains contracts, review items, change history, contract files,
workers, work records and wage payments. Searches and pagination are section-specific.

Permissions cover new contracts, add/edit/deactivate worker, log/pay work, and
contract/history-file downloads. Approval/review actions are mapped to the
related contract/work action, not to business-role names.

## Users

**Abstract:** a standalone, all-user account directory, not the current project's members.

- Search by account details and see contact, status and access scope.
- View opens read-only account details and permission summaries.
- Add/Edit is a two-step wizard; username is read-only on edit.
- Separate actions: Reset Password, Activate/Deactivate, Delete, History.
- Lifecycle changes are confirmed and depend on individual grants.
- Self-account lifecycle actions are blocked.
- Delete hides and disables the account while retaining historical records.

User History starts at 5 rows (10, 20, 50 available), includes readable change
descriptions, and excludes login success/failure activities. It differs from
project Audit Log: it includes actions by or affecting the selected user.

## Audit Log

**Abstract:** a project-scoped investigation trail for recorded user activities.

Columns, in order:
**Username | Date and time | User activity | Record | Details | Reference**.

- Newest first, with timestamp/ID ordering.
- Search and date/time range filter; 10 rows by default, then 20, 50, 100.
- Expand View changes for readable recorded details.
- Visits such as "Visited Inventory" and exports such as "Exported report from
  Inventory (export requested)" are recorded.
- Record identifies the entity type; Reference is its internal record ID.
- Export prepares all matching records for the selected project, not just one page.

Not every legacy event has detailed before/after values. This is application
activity tracking, not a recording of every click, failed request, or saved PDF.
