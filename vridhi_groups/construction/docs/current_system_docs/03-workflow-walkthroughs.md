# 3. Everyday Workflow Walkthroughs

[Documentation home](README.md)

## A. Create a new project

Prerequisite: the API must authorize Overview write access for project creation.
Creation is a project-independent request; a Global account with Overview write
access is the straightforward administrative path.

1. Open **Projects**, then **New Project**.
2. Enter project name and location.
3. Enter approved budget and contract value as nonnegative currency amounts.
4. Choose the start date and initial status: **Planning** or **Active**.
5. Optionally choose/paste/drop an initial plan file and enter its comment.
6. Submit once and wait for confirmation.
7. Open the created project; check its name, value, status and optional document.
8. Configure team memberships and module permissions in Users.

Approved budget is the spending baseline; contract value is client-side value.
They are not interchangeable. Supported plan types are PDF, PNG, JPG/JPEG and
DOCX, with a 10 MB configured limit. An initial file is optional.

## B. Change project status

Prerequisites: Overview access and Update Status write permission.

1. Select the project and open Overview.
2. Select **Update status** in the header or Project Status section.
3. Choose one of the offered next states.
4. Enter a required comment explaining the change.
5. For On Hold, also enter the hold reason.
6. For Completed, tick the completion confirmation.
7. Save and review the new state and status-history entry.

| Current status | Allowed next status |
|---|---|
| Planning | Active, On Hold, Cancelled |
| Active | On Hold, Completed, Cancelled |
| On Hold | Active, Completed, Cancelled |
| Completed | None |
| Cancelled | Planning |

If another user changed the project first, refresh and retry after reviewing
their change. The API checks the expected project version to prevent stale updates.
The history stores the submitted comment; put the essential explanation there,
even when a separate hold-reason field is shown.

## C. Upload a revised plan

1. In Overview, select Upload Plan Document.
2. Confirm the displayed current project value.
3. Enter the new estimated value and choose a supported nonempty file.
4. Add an optional explanatory comment and submit.
5. Check Plan documents and Project value history.

Uploads are permitted in Planning, Active and On Hold, not Completed or Cancelled.
The current implementation updates the contract estimate when the revised plan
is saved; do not assume a separate approval queue for this project-value update.
Download retrieves the original file; Export Report produces a report, not that file.

## D. Order materials and pay the vendor

1. Open Procurement for the correct project.
2. Choose New purchase order.
3. Select/enter the vendor and line-item information; enter quantity and unit price.
4. Review the calculated total and any initial payment.
5. Save and verify the generated PO number and register totals.
6. To change an eligible order, use its Edit action.
7. To pay an installment, use Add Payment, enter date/method/reference, and save.
8. Review Payment history and the remaining balance.

An initial payment cannot exceed the order total. Subsequent payments cannot
exceed the remaining balance. Create and Edit share one permission; Add Payment
is independent. Fully paid records remain restricted.

## E. Receive and use material

1. Open Inventory and locate the material.
2. Choose Receive; enter the receipt quantity and supporting references/cost.
3. Select a PO line when applicable and save.
4. Confirm received and available stock increased as expected.
5. Choose Use when material is consumed on site; enter quantity and notes.
6. Confirm available stock decreased and review Stock ledger.

Record only actual receipts and consumption. A purchase order alone is not proof
that material arrived. Check units carefully and do not use more stock than allowed.

## F. Bill the client and record receipts

1. Open Cash flow and choose New application.
2. Enter the billed amount and application details; save.
3. When money arrives, choose Record receipt.
4. Enter receipt date, positive amount, payment method and reference/comment.
5. Allocate to the intended application if settling a particular bill.
6. Verify cash received and billed outstanding separately.

Vendor payments belong to Procurement; worker/subcontract payments belong to
Labor and Wages. They are not client receipts.

## G. Record labor

### Direct-worker path

Add an active worker -> log work quantity/unit/rate -> verify earnings ->
record wage payment -> review earned/paid/payable and history.

### Contract path

Create labor contract -> attach/link baseline documents -> submit progress claim
-> review/certify or reject -> pay an eligible certified claim -> review ledger.
Use a contract change/addendum when the agreed scope/value needs revision;
review it rather than overwriting historical records.

Never add direct wages and subcontract payments to cost a second time if their
underlying work/claims are already included. See [calculations](05-reports-and-calculations.md).

## H. Create an account

1. Open Users without needing a project selection.
2. Select Add user.
3. Step 1: enter full name, optional work email/contact number, unique username,
   password and confirmation. Passwords require at least six characters.
4. Step 2: choose selected projects/per-project permissions, shared selected-project
   access, or Global access.
5. Configure standalone Users and Audit Log access separately where applicable.
6. Review each action grant before saving.

A Users-only account is valid: allow Users, select no project, leave Global off.
There is no role dropdown. For editing, username cannot change; leave password
blank to keep it. Changing it requires Reset Password authorization.

## I. Investigate activity

1. Select the project and open Audit Log.
2. Search by username/activity or open the calendar filter icon.
3. Choose a range or Today/Yesterday/Last 7 days/This month.
4. Set From/To time using the analog clock; select hour, minute and AM/PM, then OK.
5. Apply the complete date/time range.
6. Inspect Record, Reference and expanded changes; export if needed.

Times are entered/displayed locally and sent as timezone-aware values. To includes
the selected ending minute. Closing the draft filter without Apply leaves the
previous interval in place. Clear filters restores the unfiltered list.

## J. Export

Choose Export report -> wait for preparation -> choose Save as PDF in the browser
print dialog -> inspect preview -> save. Use the module-specific scope notes in
[Reports and calculations](05-reports-and-calculations.md); not every module
automatically fetches all table pages.
