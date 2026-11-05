# Company Cashbook: Feature and Training Guide

[Documentation home](README.md) | [Detailed reference](11-company-cashbook.md) |
[Illustrated training deck](training-illustrated.pptx)

Updated: 30 October 2026. Audience: finance operators, reviewers and account
administrators. Currency: INR. Examples below are illustrative, not live records.

## 1. Purpose and boundaries

Company Cashbook records actual money entering or leaving the company:
capital contributions, withdrawals, company spending, other receipts, starting
balances and company/project transfers. External loans and repayments have a
dedicated Borrowings workflow.

Company Cashbook is independent of the selected project. Viewing it exposes
company-wide finances and INR project information, not just assigned projects.

Do not duplicate project client receipts, vendor payments or labor payments
here as additional company expenses. Project modules remain the source of those
records; they are not automatically imported into Cashbook.

This is a recorded-cash register, not bank reconciliation, statutory accounts,
a complete general ledger or an automatic profit-distribution system.
Transfers between the company's own accounts are not supported.

## 2. Features at a glance

| Area | Features |
|---|---|
| Cash Transactions | Record dated receipts/payments; starting balances; category/type/direction; party, account, purpose, reference and optional project linkage |
| Summary | Opening and closing recorded cash, money in/out, outstanding borrowing principal; collapsible cumulative financial summary |
| Register | Search; category/type/direction/status filters; pagination; recorder; transaction-details popup; Mark as invalid |
| Spending/accounts | Net spending by category and recorded balance by account; independent pagination |
| Borrowings | New Loan; principal/interest repayment; lender totals, payment status, search/filter, history and lender report |
| Project Profit & Loss | Shared Overview calculation; refresh; Global-access approval; immutable snapshots; approval search/filter/history/breakdown |
| Owner Capital | Contributions, withdrawals and net movements by descriptive owner name |
| Company Audit Log | Separate left-menu page and permissions; visits and saved activities; search/time filter; details; summary and single-activity reports |
| Reports | Branded browser Print / Save as PDF with relevant filters and complete fetched row sets |

Cashbook has four tabs: **Cash Transactions**, **Borrowings**,
**Project Profit & Loss**, and **Owner Capital**. The duplicate History tab has
been removed. Use **Company Audit Log** for company activity.

## 3. Permissions before training

| Permission | Enables | Does not enable |
|---|---|---|
| Company Cashbook: View | Company-wide cashbook, financial summaries, saved entry details and INR project figures | Recording, report downloads or approval |
| Company Cashbook: Record | Record transactions/loans/repayments and mark incorrect records invalid | Projected-result approval; category/type creation |
| Company Cashbook: Download Report | Cashbook and lender reports | Company Audit Log reports |
| Company Audit Log: View | Company-wide Cashbook activity list and recorded-event details | Access to the underlying saved cash entry |
| Company Audit Log: Download Report | Activity-list and single-activity popup reports | Underlying entry access without Cashbook View |
| Global access | All Cashbook/Audit capabilities, projected-result approvals, custom category/type creation | A reason to skip review or duplicate checks |

Non-global accounts start blocked. Grant only the capabilities needed.
Account managers cannot delegate Cashbook/Audit grants they do not have.
Cashbook-only and Company-Audit-only users do not need a project assignment.
Adding/editing users still requires the separate Users permission.

## 4. Set up starting balances

1. Establish the date the register begins.
2. Record the existing balance once for each account with **Starting balance (+)**
   or **Starting balance (-)**, as appropriate.
3. Use a consistent account name and explain the source in Purpose.
4. Verify the opening balance and per-account figures.

Do not record the same starting balance again as owner capital. Multiple starting
entries are supported; preventing duplicates remains the operator's responsibility.

## 5. Record a cash transaction

1. Open **Company Cashbook -> Cash Transactions -> Record transaction**.
2. Enter the actual date; future-dated transactions are rejected.
3. Choose **Category**, then **Transaction type**.
4. Check the type's money direction. It is configured on the type and cannot
   be overridden for an individual entry.
5. Enter amount, party, payment mode, purpose and company account as required.
6. Link the intended INR project for a project transfer.
7. Add a payment reference when available, save once, then inspect the row,
   recorder and resulting totals.

Bank transfer, UPI and Cheque require a company account. Cash/Other can omit it;
blank account values are saved as **Cash**/**Others**, respectively.
Borrowing entries must use Borrowings rather than this form.

### Categories and custom types

Built-in groups include Owner capital, Owner withdrawal, Company spending,
Project cash received / Project funding, Other receipt, Starting balance,
Paid and Salary. Borrowing types are fixed.

Global-access users can add a category (including its first type/direction)
or a transaction type under the selected category. Record users can use saved
options but cannot create them. New custom categories use the company-spending
reporting group.

A Money-in refund offsets spending within its reporting group. For example,
Salary payment INR 1,000 minus Salary refund INR 100 gives net Salary spending
INR 900, while the two movements remain separately visible in Money out/Money in.

## 6. Understand the numbers

| Figure | Basis |
|---|---|
| Opening balance | Net posted cash before From, plus signed starting entries inside the range |
| Money in / Money out | Posted movements inside the range, excluding starting balances |
| Closing recorded balance | Opening balance + money in - money out |
| Company spending | Net company spending, Paid, Salary and loan interest; not loan principal, owner withdrawals or project funding |
| Outstanding principal | Loan principal received minus principal repaid through Through |
| Account balances | Cumulative signed posted entries per account through Through |
| Approved projected profit/loss | Latest approved projection per project through Through; separate from cash |

Entries marked invalid do not contribute to active totals.
Register search and category/type/direction/status filters do not narrow summary
cards. Cumulative figures run from the beginning through the selected end date.

**Cash example:** starting balance INR 100,000 + capital INR 50,000 + new loan
INR 20,000 - rent INR 10,000 - principal repayment INR 5,000 - interest INR 500
= closing recorded balance **INR 154,500**. Company spending is **INR 10,500**;
outstanding principal is **INR 15,000**. This assumes no other records or balances.

The cumulative summary can be collapsed; its state is remembered. The financial
report preserves that collapsed/expanded choice. Spending and account panels
each start at 10 items, with 20 and 50 available.

## 7. Borrowings: receive and repay

### New Loan

1. Open Borrowings and choose the **New Loan** icon.
2. Enter lender, date, principal, payment mode, account and purpose.
3. Select **Save** and verify outstanding principal and the lender row.

Lender matching is case-insensitive. Use the existing suggested name to avoid
unintended separate lender balances.

### Loan Repayment

1. Choose **Loan Repayment** in the toolbar or on the lender row.
2. Select a lender with outstanding principal.
3. Enter principal repaid and/or interest paid, plus payment details.
4. Save and review the lender's totals and individual transactions.

Repayment creates up to two Money-out records: principal and interest. Principal
cannot exceed outstanding principal and does not count as company spending.
Interest counts as company spending.

Once principal is fully settled, further repayments (including interest-only
repayments) are blocked for that lender. This is not a full loan schedule or
accrued-interest engine.

The summary strip shows Outstanding principal, Total borrowed, Principal repaid
and Interest paid. Lender status is **Unpaid**, **Partially paid** or **Paid**,
based on principal only. Search and status filters affect lender rows, not totals.
Lender pagination starts at 5, with 10 and 20 available.

The eye icon opens Borrowing details. Its transaction eye icon opens the exact
transaction in a second popup. The lender report includes the full matching
history, not just the visible page.

## 8. Project projected profit/loss and approval

**Projection = contract value - PO line costs - recorded wage work -
certified contractor claims.**

This is the same basis as Project Overview. Paid vendor/wage/contractor amounts
and inventory movements are not counted again. Company overhead, GST adjustments,
owner capital and project transfers do not change this projection.
Incomplete cost recording can overstate profit.

1. Open **Project Profit & Loss**; search/filter the project list as needed.
2. Select **Refresh calculations** to retrieve current figures.
3. A Global-access reviewer sets Through to today and selects **Review and approve**.
4. Check total project amount, material/labor cost breakdown and projected amount.
5. Enter an approval note and approve.
6. Review saved approval details, reviewer, timestamp and breakdown.

The live calculation uses all current source records, not a historical From/Through
cost reconstruction. Through filters saved approvals and transfers.
The visible results tab refreshes every 15 seconds.

Only approved projections count in company totals. If the projection or its calculation basis changes,
the project needs approval again; the previous approved amount stays in totals
until replaced. Not approved is not an assumed approved zero. Break-even can
be explicitly approved. Approval snapshots cannot be edited or marked invalid.

Archived projects keep their approved projections and cashbook history in these
totals. They cannot receive linked cash entries or new approvals while archived.
Resolve outstanding items and approve the current calculation before archiving;
UnArchive through Overview with its action permission before further corrections.

Project list pagination starts at 10 (20/50 available). Approval history starts
at 5 (10/20/50 available), with search, Approved by filter and breakdown popup.
Filters do not reduce the approved company totals. Legacy manual declarations
remain reference-only and do not enter approved totals.

## 9. Owner capital

Record a **Capital contribution** for actual capital received and an
**Owner withdrawal** for actual money paid back. Use consistent owner names.

Owner Capital shows Capital received so far and Withdrawals so far above the
owner table. Table movements use the selected dates; cumulative totals run
through the selected end date.

Names and net movements do not establish ownership percentages, legal equity
or an automatic settlement obligation. A partner joining/exit register,
profit-share calculation and settlement workflow are not implemented.

## 10. Correct a record: Mark as invalid

1. Find the incorrect entry in Cash Transactions.
2. Select the prohibition icon, **Mark as invalid**.
3. Review its full details and CC reference.
4. Enter a reason of at least five characters and confirm **Mark as invalid**.
5. Record the correct replacement through the appropriate transaction/loan form.
6. Verify balances and Company Audit Log.

This is irreversible: the original record remains with the reason, actor and
timestamp, but is excluded from active totals. It is not deletion or an
automatically generated opposite financial entry.
For repayments, principal and interest records must be corrected separately.
Status filters offer Posted, Marked as invalid and All records.
Internal API/database identifiers still use `void`; UI labels use Mark as invalid.

## 11. Company Audit Log

Open the separate **Company Audit Log** left menu. No project selection is required.
It covers company Cashbook activity, not unrelated project or user-administration
activities. Those retain their separate logs.

- Newest first; dates/times displayed in the browser's local timezone.
- Search usernames, activity, recorded details and IDs.
- Apply the calendar/time filter or clear filters.
- Pagination: 10 by default; 20, 50 and 100 available.
- Visits to all four Cashbook tabs and Company Audit Log are recorded.
- Saved transactions, approvals, corrections, custom options and report requests
  have recorded events.
- Older visits before visit tracking was installed cannot be reconstructed.

**View activity details** opens a readable summary of activity, performer and time.
For supported record events it loads the exact saved entry by ID and checks
Cashbook View access again. Without access, an explicit permission message is
displayed. Visits/report requests show recorded event details instead.
Entry details describe the current saved record, not necessarily every field's
historical value at the time of the event.

## 12. Download Report: choose the correct scope

| Location | Printed content | Required download grant |
|---|---|---|
| Cashbook header | Active financial tab, date context, relevant summaries and complete matching fetched rows | Company Cashbook |
| Borrowing details | Selected lender totals and all matching history rows | Company Cashbook |
| Company Audit Log | All matching activities: Date & time, Username, Activity only; no activity details | Company Audit Log |
| Activity popup | Selected activity summary plus displayed entry or event details; no activity list | Company Audit Log; Cashbook View also required for a saved entry |

Use **Download Report -> browser print dialog -> Save as PDF**. Reports use the
shared company header and light print colors even in Dark mode.
Check date/filter scope, all pages, paper/scaling and preview before saving.
The header shows the company logo and name; no company address is printed.
An audit event confirms a report request, not that a PDF was saved.

## 13. Training exercise and troubleshooting

Use an isolated training database and synthetic names:

1. Confirm grants; record the cash example in section 6.
2. Reconcile closing cash, spending and outstanding principal separately.
3. Review a project projection with a Global-access account and save an approval.
4. Change an underlying training cost, refresh and observe pending approval.
5. Mark an erroneous duplicate invalid with a meaningful reason.
6. Search its activity and export the summary list, then the single activity.
7. Repeat with read-only and audit-only accounts to demonstrate access boundaries.

| Symptom | Check |
|---|---|
| Missing Company Cashbook/Audit menu | Separate View grant; refresh after account changes |
| Download Report absent | Correct page's download permission, not Record permission |
| Approval unavailable | Global access, Through=today, changed/unapproved projection |
| Repayment disabled | No outstanding principal; settled lenders reject more repayments |
| Balance differs from bank | Starting entries, account spelling, date range, duplicates and invalid records |
| Popup denies entry access | Company Audit View does not replace Company Cashbook View |
| Activity not recorded | Visible error/Retry, API availability; no retrospective visit reconstruction |

## Sources and scope of this guide

Read alongside [permissions](04-users-and-permissions.md),
[reports](05-reports-and-calculations.md), [operations](08-operations-and-troubleshooting.md)
and the [cashbook reference](11-company-cashbook.md).
The training slides include current frontend captures with synthetic API responses;
they do not expose live company data. Fixtures illustrate controls and may not
reconcile across separate screens. Worked examples are explicitly independent.
This guide is not an audited accounting opinion or a production certification.
