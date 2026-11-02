# Company Cashbook

Implemented: 30 October 2026. Currency: INR only.

For operator workflows, a permission matrix, a worked cash example and practice
exercises, see the [Company Cashbook feature and training guide](12-company-cashbook-training.md).
The [illustrated training deck](training-illustrated.pptx) covers
Company Cashbook on slides 46-63.

## What belongs here

Archiving a project does not remove its latest approved projected profit/loss,
cashbook movements or approval history from Company Cashbook. The project is
read-only: no new project-linked cash entries, invalidation of linked entries,
or result approvals until it is UnArchived through Overview. Archive requires
an up-to-date approved snapshot and resolved outstanding items. A changed
calculation basis needs a new approval even if the net amount is unchanged.

The **Company Cashbook** left menu is independent of the selected project. It
records cash crossing the company's financial boundary, including:

- Owner/partner principal invested and owner withdrawals.
- Loans received from external lenders, principal repayments and loan interest
  (recorded from the separate **Borrowings** tab).
- Company-only purchases, labor, furniture, plumbing, building maintenance,
  rent, utilities, transport and miscellaneous spending.
- Actual cash sent to a project or returned from a project.
- Other company receipts.
- Existing starting cash/bank balances when beginning this register.

This is not an automatically consolidated bank ledger. Project client receipts,
vendor payments and labor records stay in their project modules. They are **not**
automatically imported here. Do not copy them as additional company expenses.
Company-account-to-company-account transfers are not supported in this version;
do not record them as income or spending.

## First use

Required transaction fields are marked with `*`. The form's **Record transaction**
button stays disabled until they are complete, including a linked project for
project transfers and a company account for Bank transfer, UPI or Cheque.

1. A Global-access account already has access, and this is the recommended
   setup for company finances. Other users start blocked. Only when someone
   needs company-wide finances, an authorized account administrator opens
   **Users → Add/Edit → Permissions → Company Cashbook** and grants View,
   Record and/or Export.
2. Record the existing balance once for each company account using **Starting
   balance (+)** (positive) or **Starting balance (−)** (negative). Use the date
   this register begins. Explain the source in the description.
3. Use consistent account and owner/partner names. These are descriptive names,
   not linked bank connections or verified legal ownership records.
4. Record actual money movements with date, category, transaction type, amount, party,
   company account, payment mode, purpose and optional payment reference.
   Company account is required for Bank transfer, UPI and Cheque. For Cash and
   Other it is optional; blank entries are saved under the account **Cash** or
   **Others** respectively and shown as separate account balances.
5. Link a project only for cash received from or funded to a project. Only INR
   projects are available. Future-dated transactions are rejected.

Starting balances are not owner capital: do not enter the same existing money
twice. Multiple starting entries are allowed for different accounts; the operator
must ensure they are not duplicated.

### Categories and transaction types

**Category** is the top level and **Transaction type** is the second level.
Categories group related transaction types. **Each transaction type has its own
money direction**: Money in increases company cash and Money out reduces it.
Selecting a type automatically uses its configured direction; the operator
cannot override it on an individual entry.

| Category | Transaction types (built in) |
|---|---|
| Owner capital | Capital contribution |
| Owner withdrawal | Owner withdrawal |
| Company spending | Company purchases, Company labor, Furniture, Plumbing, Building maintenance, Rent, Utilities, Transport, Miscellaneous |
| Project cash received / Project funding | Project transfer |
| Other receipt | Other company receipt |
| Starting balance (+) / (−) | Opening balance |
| Paid | Paid to Pending, Paid to Shop, Paid to Electricity, Paid to Wifi |
| Salary | Salary to Contractors, Salary to Manager, Salary to Security, Salary to Driver |
| Borrowings (Borrowings tab only) | Loan received, Loan repayment – principal, Loan interest |

All built-in types under Paid and Salary are **Money out**. They reduce company
cash and are included in company spending, without creating project costs,
payroll records or payable settlements automatically.
### Borrowings and interest

Loans have their own tab and forms instead of **New cash transaction**. The
Borrowings category is not offered in the general form, and the API rejects
borrowing entries sent to `/entries`. Borrowing types are fixed so lender
balances stay consistent.

- **New Loan** (dialog submit button **Save**) stores one Money-in *Loan received* entry. Enter the lender,
  amount, date, payment mode, account and purpose. Existing lender names are
  suggested; matching is case-insensitive and reuses the existing name.
- **Loan Repayment** (also available per lender row, tooltip *Loan Repayment*; the dialog's submit button is **Save**) selects a lender with an
  outstanding balance and accepts **Principal repaid** and/or **Interest paid**.
  It stores up to two Money-out entries: *Loan repayment – principal* and
  *Loan interest*. Principal cannot exceed the lender's outstanding principal.
  Once principal is fully repaid, the lender's repayment action is disabled and
  the lender is excluded from the repayment dropdown. The main repayment button
  is disabled when no lenders have outstanding principal. Further repayments,
  including interest-only payments, are rejected for settled lenders.

Loan principal received and repaid changes cash balances but is excluded from
company spending. Loan interest reduces cash and is included in company spending
and the spending breakdown.

The Borrowings tab shows **Outstanding principal**, **Total borrowed**, **Principal
repaid** and **Interest paid** together in a single full-width summary strip above
the Borrowings & interest panel. It also lists these figures per lender, from the beginning of
the register through the selected end date, excluding entries marked as invalid.
Payment statuses use red for **Unpaid**, amber for **Partially paid**, and green
for **Paid**, with matching dark-mode colors and text labels.
The **Payment status** column is **Unpaid** when no principal has been repaid,
**Partially paid** when some principal has been repaid and a balance remains,
and **Paid** when no principal remains outstanding. Interest-only payments do
not change this principal-based status. Status is aggregated by lender, not by
individual loan. The lender table shows 5 rows per page by default, with 10 and
20 available. Search lenders by name (case-insensitive) and filter by payment
status together. Search, payment-status filter and clear icon appear beside
**New Loan** and **Loan Repayment** in one line in the section heading toolbar.
The actions are icon-only with hover/focus tooltips: green for recording a loan
and red for recording a repayment, with dark-mode equivalents. Read-only users still have the search and filter controls.
The always-visible **Clear filters** icon with a hover/focus tooltip (disabled until a
search or status is set) resets both. These controls affect
only the lender table, not the totals above or the transaction register.
Exports retain the search/status selection and include the payment-status column.
The view
action opens a **Borrowing details** popup without changing tabs or register
filters. It shows the lender's totals and paginated loan, principal repayment
and interest history through the selected end date. Entries marked as invalid are labelled
and excluded from totals. The eye icon (tooltip **View transaction details**)
opens a separate **Transaction details** popup on top, showing who recorded the
entry and any invalidation reason. Closing it returns to Borrowing details. Read-only
cashbook users can also view this history. Users with Download Report permission
see an **Download Report** button that prints that lender's totals and full
history (all pages) as a branded report. This uses the cashbook export endpoint
with a `lender` filter and is recorded in cashbook history. To correct a borrowing entry, mark it as invalid in the register and record it
again from the Borrowings tab. Each part of a repayment is marked invalid separately.
This is a cashbook principal balance, not a full loan schedule or accounting
liability balance.

Endpoint: `POST /api/v1/company-cashbook/borrowings` (cashbook write permission,
CSRF). The body contains `request_id`, `action` (`loan` or `repayment`),
`transaction_date`, `lender`, `principal`, `interest`, `description`, `account`,
`payment_mode` and `reference`. It returns the created entry IDs, and a
duplicate `request_id` returns 409.

Changing the category in **New cash transaction** refreshes the
transaction type list to that category's types.

### Custom categories and transaction types

Global-access cashbook administrators can select the folder-plus icon beside
Category (**New category**) or the list-plus icon beside Transaction type
(**New transaction type**). Each opens a separate popup; **Add** saves the option
permanently for all cashbook users and returns to the transaction form with it
selected. Cancel, Close or Escape returns without adding; fields already entered
are preserved.

- **New category** asks for the category name, its first transaction type and
  that first type's direction. New categories use the company-spending reporting
  group (not project transfers, owner capital or starting balances). Names
  matching an existing category are rejected.
- **New transaction type** asks for a name and **Money direction** and is added
  under the currently selected category (shown in the popup). Duplicate names
  within the same category are rejected, even if the direction differs.

For example, Salary to Driver is Money out; a new Salary refund type can be
Money in under the same Salary category. A payment of INR 1,000 and refund of
INR 100 appear separately in Money out / Money in and produce net Salary
spending of INR 900. Opposite-direction types offset category totals (including
owner and project-transfer totals), rather than being added as positive spending.
Starting-balance types still affect opening balance, not period cash movement.
Project-transfer types still require a linked project.

Direction is copied from the type and stored permanently with each entry.
Existing entries and custom types retain their previous direction through the
database migration. Voiding excludes the entry from all active cash totals;
history and exports retain its original direction.

Users with Record permission can use saved options but cannot create them.
Custom names appear in the register, details and print/export, and can be found
using register search. The register **Category** filter lists built-in and
custom categories; the **Transaction type** filter lists the types of the
selected category (or all types). Option creation is recorded in cashbook
history. Existing posted transactions are unchanged.

## Understanding the numbers

The Company left menu includes **Company Audit Log**, which shows
Company Cashbook activity with dates, actors, actions, details and pagination.
The duplicate History tab has been removed from Company Cashbook. The Company
Audit Log menu uses its own **Company Audit Log** user permission (Global access
always includes it). See Users and Permissions. No project selection is required, and refreshing
keeps the dedicated audit page open. This log does not include unrelated
project or user-administration activity.

The activity popup separates the activity, performer and timestamp from the
record fields. Details use a two-column layout on desktop and a single column
on mobile, with dark-mode styling. Nested activity details use labeled rows
instead of raw JSON.

In **Company Cashbook history**, the eye icon (tooltip **View activity details**)
uses the activity's record ID to load the exact saved entry and show it in an
**Activity entry** popup. That entry can be a cash transaction, borrowing
transaction, voided transaction, project profit/loss approval or added
category/type. The entry is loaded with Company Cashbook read permission and is
checked again on every open. Without that permission, for example a user who has
only Company Audit Log access, the popup says "You don't have permission to view
this activity's entry". Visits and report requests have no saved entry, so the
popup shows their recorded activity details instead. Record IDs are not shown
below the icon. Search matches usernames, names, activities, recorded details and IDs.
The time-range filter reuses the Project Audit Log calendar/time picker; clear
filters resets the search and time range. History filters are independent of
the cashbook's financial date range.

History defaults to **10 rows**, with **20, 50 and 100** also available.
**Download Report** prints/saves all matching activities, not just the current
page, with Date & time, Username and Activity only. Details are excluded.
The Company Audit Log report uses the standard company logo/header, exported
date, A4 landscape layout and table formatting used by other report pages,
with **Company Audit Log** as the report title above the activity table.
Use **Download Report** inside the activity popup to print/save that single
activity's summary and displayed entry/details. The popup button requires the
current log's Download Report permission; saved entries additionally require
Company Cashbook read access. Export requests are recorded in history.
The list report uses the separate Company Audit Log Download Report
permission in the dedicated menu. Global access includes it. Report requests
are recorded; browser print/save completion cannot be observed.

Opening **Cash Transactions**, **Borrowings**, **Project Profit & Loss**,
**Owner Capital**, or **Company Audit Log** records a visit with
the username, timestamp and page name. Refreshing records a new visit; changing
filters or pagination does not. Visits require only the corresponding page's
view permission. If recording fails, an error and Retry action are displayed.
Visit tracking starts when this feature is installed; earlier unrecorded visits
cannot be reconstructed.

Date range defaults to the beginning of the register through today.
The active cashbook tab is remembered for the current browser session. Refreshing
keeps Cash transactions, Borrowings, Project profit & loss or Owner capital
selected instead of returning to Cash transactions. A previously saved History
tab selection now opens Cash Transactions.

| Number | Meaning |
|---|---|
| Opening balance | Net posted cash before the selected From date, plus starting entries dated within the range |
| Starting entries in range | Positive minus negative starting entries dated within the range (already included in Opening balance; shown in the help line) |
| Money in | All posted Money-in types in the range, excluding starting balances |
| Money out | All posted Money-out types in the range, excluding starting balances |
| Closing recorded balance | Opening balance + money in − money out |
| Company spending | Company spending, Loan interest, Paid and Salary payments minus their money-in entries; excludes loan principal, project funding and owner withdrawals |
| Cumulative financial summary | Cumulative net category totals from the beginning through the selected end date; opposite-direction types offset each category |
| Outstanding borrowings | Loan principal received less principal repaid, by lender, through the selected end date; loan interest is separate company spending |
| Account balances | Cumulative signed cash entries by account through the selected end date |

Entries marked as invalid never contribute to totals. A negative recorded balance is allowed
but flagged for investigation. It can indicate missing starting balances, omitted
receipts or duplicate payments. Cash values are stored as PostgreSQL decimals and
calculated to two decimal places. They are recorded balances, not bank-reconciled
balances.

The top summary cards are ordered Closing recorded balance, Opening balance,
Money in, Money out and Outstanding borrowings. The cumulative summary groups
cash flows first, then spending and owner movements, project flows, borrowings
and project approvals.

Search, category, transaction type, direction and posted/marked-as-invalid filters apply only to the
transaction register. Summary cards still describe the entire date range. The
filters are right-aligned on one line beside the register title on wide screens.
The clear-filter icon appears at the right end only when a filter is applied;
no space is reserved for it otherwise. On narrower screens the filter bar moves
below the title (still right-aligned); on mobile it scrolls horizontally rather
than wrapping individual controls. The
register footer shows totals for **all matching rows**, not just the current page,
and includes starting entries when those rows match.

Register filters and pagination update in place, keeping the previous rows visible
while the requested rows load instead of clearing the page. History pagination
also retains its rows while loading. Success notifications can be dismissed and
automatically disappear after five seconds.
The register Date column shows only the transaction date; the record reference
(CC-…) appears in the View and Mark as invalid popup titles. Register rows keep party/purpose and mode/account to two compact lines, with
payment mode (and reference, if present) first and account second. View
opens a transaction-details popup with the full text, linked project, payment
reference, recorder and invalidation information, without expanding the row. View and
Mark as invalid appear side by side as eye and prohibition icons with hover/focus tooltips.
Popup field labels are bold uppercase to distinguish them from values.
The Mark as invalid confirmation shows the same transaction details for review,
requires a reason, and uses a **Mark as invalid** confirmation button.
Its compact layout and short reason field fit desktop screens without scrolling;
smaller screens retain scrolling when needed to keep every field accessible.
The register's **Recorded by** column identifies who entered each transaction.
Printed reports retain full text and project names.

Company spending breakdown and Recorded cash by account each have independent
pagination: 10 items by default, with 20 and 50 available. Changing the date range
resets both to page 1. The pagination bars stay at the bottom of their panels,
aligned when side by side. Totals and spending proportions still use the full lists;
printed/exported reports include all categories and accounts, not just one page.
Amounts use green for receipts, red for spending/withdrawals, blue for recorded
account balances (red when negative), and amber for not-yet-approved counts.
The same colours apply to the compact Cumulative financial summary, with dark-mode equivalents.

The chevron at the top right of the Cumulative financial summary collapses or expands its figures. Each browser remembers the choice. Download Report prints the summary as it is shown: when collapsed, only the heading is printed; when expanded, all figures are printed.

## Project profit & loss

This tab reuses the **Projected profit** from Project Overview. Both pages use
the same server-side calculation:

**Contract value − recorded purchase-order costs − wage work − certified contractor claims.**

- This preserves Overview's existing cost convention: all purchase-order line
  quantity × price amounts, wage-work quantity × rate, and Certified claims.
  Inventory receipts/issues and vendor/wage payments are not counted again.
- Billing, cash receipts, owner capital, project transfers, company overhead,
  depreciation and GST adjustments do not change this projection.
- This is a **projection**, not final earned or statutory accounting profit.
  Incomplete costs can overstate it; review the breakdown before approving.
- Live projections use all current records, just like Overview; **From/Through
  do not recalculate a historical projection**. Through filters saved approvals
  and cash transfers. Approval is allowed only with Through set to today.
- The results tab refreshes every 15 seconds while visible and has a manual
  **Refresh calculations** action, available as an amber-highlighted
  icon-and-text button (tooltip *Refresh calculations*) in the Project projected
  profit / loss toolbar.

The projected amount is **not included in approved company totals until approved**:

1. A **Global-access user** finds a project using the project-name search, opens
   **Review & approve**, checks the **Total project amount** (contract value),
   the Overview breakdown and enters an approval note.
   The search only filters project rows; the company totals still include all
   approved projects. Other pages and their permissions are unchanged.
   Search project names (case-insensitive) or filter by **Approval status** and
   **Approved user** (including **Not approved**). A clear-filter icon appears
   when any project filter is applied. **Total project amount** shows the same
   contract value used in the calculation. The
   project list shows 10 rows per page by default, with 20 and 50 also available.
   Changing project filters resets pagination; company totals remain unchanged.
   The Cumulative financial summary labels the approval counts **Project approvals**.
   Each row's **Actions** column offers **Review and approve**, **Calculation
   breakdown** and **Approval history**; approval is only shown to Global-access
   users when needed. These actions use icons with hover/focus tooltips. The
   approval popup displays the calculation breakdown in two columns.
   The approved amount, last approval date and approving user have separate
   columns. In Approval history, each record has its own Project, As of, amount,
   note, approver, approved-on date and status columns. Its calculator icon opens
   the saved breakdown in a popup, including the approved projection and reviewer.
   Both the main Approval history and project-specific history support search
   (project, note, approver, as-of date or amount), an **Approved by** filter,
   and a clear-filter icon. Pagination defaults to **5** records with **10, 20,
   50** options; changing search or filters returns to the first page.
   The main history search and filters sit at the right of its title bar.
   Download Report includes all matching approval records, not just the current page.
2. The server rechecks the shared Overview figure and rejects stale reviews.
3. Approval saves an immutable snapshot, reviewer, timestamp, as-of date and note.
   The amount is not editable. Repeated identical request IDs are idempotent.
4. When the projected amount changes, it becomes **Pending approval**; the last
   approved projection remains in company totals until reapproved.
   Same-day reapprovals preserve all earlier snapshots.
5. Only the latest approval per project through the selected Through date counts.
   Projects without approval show **Not approved**, not an assumed approved zero.
   A calculated zero can be explicitly approved as break-even.

Old manual declarations are preserved as **Legacy manual declaration history**,
excluded from approved projection totals. New manual declaration requests are
rejected. Existing projects need an initial projection approval.

## Corrections and history

Posted cash transactions cannot be overwritten or deleted. Use **Mark as invalid**, provide
a reason (at least five characters), then enter the correct replacement. Invalid entries
are irreversible and preserve the original record. Result approvals cannot be
edited or marked invalid; correct source records and approve the revised calculation.
Legacy declaration invalidations do not affect approved actual totals.
Cash rows can be filtered to Posted, Marked as invalid or All.

The **Company Audit Log** menu includes actor, recorded timestamp, saved details, invalidation reasons
and export requests. It covers company cashbook events across all dates, separate
from the project-specific Audit Log. Transaction rows also show who recorded them.
Repeated submissions use unique request IDs; the server rejects duplicates.

## Owner capital and export

**Owner capital** shows contributions and withdrawals in the date range, plus net
capital movements so far by owner name. It does not infer equity percentages.
Only Capital received so far and Withdrawals so far appear above the owner table,
inside the same section. Selected-period movements remain in the table rather
than being repeated as separate summary figures.

**Download Report** fetches all matching transaction rows (including rows beyond the
visible page) before opening Print / Save as PDF. The active cash, results or
capital view, its date context and summaries are printed. History has its own
on-screen pagination and is not included in this financial report export.
An audit event confirms export was requested, not that the browser saved a file.

## Access and technical notes

- View exposes all company transactions/history and all INR project names and
  declared results, regardless of project memberships.
- Record permits transactions and marking records as invalid, not result approval.
- Only Global-access users can approve projected results. Existing non-global
  Record/All-write grants cannot approve; there is no new Users-page permission.
- Export is independent of Record. All mutation endpoints require CSRF.
- Global access includes all three grants. Other accounts default to blocked;
  turning Global access off in the user editor resets Company Cashbook to
  Block.
- An administrator cannot delegate cashbook grants they do not have.
- Cashbook-only accounts need no project assignment.
- Migration `0020_project_result_approval` adds immutable automatic-result approvals.
- Migration `0019_company_cashbook` adds account grants and the
  `company_cash_entries` / `company_project_results` tables. Run migrations before
  starting the updated backend. Existing records are not imported or reset.
- API base: `/api/v1/company-cashbook`; GET register/summaries, POST `/entries`,
  POST `/results`, POST `/{entries|results}/{id}/void`, GET `/history`, POST `/export`.
- Regression tests: `python -m pytest tests/test_company_cashbook.py`. Set
  `VRIDHI_TEST_POSTGRES=1` to also run the opt-in PostgreSQL HTTP integration test;
  it runs the full migration chain in a random transactional schema and rolls
  back all test tables/data.
