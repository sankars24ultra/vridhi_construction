# 13. Project Archive: Feature and Training Guide

[Documentation home](README.md) | [Module guide](02-module-guide.md#current-projects-and-archived-projects) |
[Permissions](04-users-and-permissions.md#project-archive-action) |
[Illustrated PowerPoint](training-illustrated.pptx) (slides 64-75)

Feature update: 31 October 2026. Screens in the deck use isolated synthetic
training data; project names, amounts, users and dates are illustrative.

## 1. Purpose

Project Archive moves finished work out of the daily project list without deleting
anything. An archived project:

- appears only in **Projects > Archived Projects** and is hidden from the
  **WORKSPACE** selector;
- keeps its status (**Completed** or **Cancelled**) and all of its history;
- becomes **read-only** in every project module;
- keeps contributing its latest approved projected profit / loss to Company
  Cashbook totals, exactly once.

Archive is reversible. **UnArchive project** returns the project to Current
Projects with the same status.

| Archive is | Archive is not |
|---|---|
| A visibility and read-only setting | A project status |
| Reversible with UnArchive | Deletion or data purge |
| Recorded in the project Audit Log | A replacement for the Company Cashbook approval |

## 2. Projects Dashboard tabs

Projects has two tabs, each showing its count:

| Tab | Contains | Summary tiles | Status groups |
|---|---|---|---|
| **Current Projects** (default) | Every non-archived project | Total, Planning, Active, On Hold, Completed, Cancelled | All six statuses |
| **Archived Projects** | Archived projects only | Total, Completed, Cancelled | Completed and Cancelled only |

- Planning, Active and On Hold never appear in Archived Projects, because only
  Completed or Cancelled projects can be archived.
- The **Completed** tile uses the green success colour on both tabs.
- Search applies to the active tab. Summary tiles count every matching project
  across all pages, not only the visible page.
- Both tabs show **10 projects per page** by default.
- The selected tab is remembered when the page is refreshed.
- Archived project cards show **Archived · Read-only**. Select a card to open its
  Overview, reports and Audit Log.

## 3. Eligibility and blockers

**Archive project** appears in the Overview header only when the project is
Completed or Cancelled and the user holds the Archive action (see section 7).
Before archiving, the server checks the project and lists every outstanding item.
The popup shows only the items that need attention; it shows no extra message
when nothing is outstanding.

| Blocker shown in the popup | Resolve it in |
|---|---|
| Only Completed or Cancelled projects can be archived. | Overview > **Project status** |
| Outstanding vendor payments | Procurement (pay or close the purchase orders) |
| Outstanding client billing | Cash flow (record or allocate client receipts) |
| Outstanding worker payments | Labor and Wages > direct workers |
| Unpaid certified claim / claim awaiting certification | Labor and Wages > contracts and claims |
| Contract addendum awaiting approval | Labor and Wages > contracts |
| Remaining inventory / unreceived ordered inventory | Inventory and Procurement |
| Approve the projected profit / loss in Company Cashbook | Company Cashbook > Project Profit & Loss (Global access) |
| The approved profit / loss is out of date | Refresh calculations, review and approve again |
| Company Cashbook approval currently supports INR projects only | Not available for non-INR projects |

The approval becomes out of date when any source record used in the projection
changes after approval. The check runs again when the user confirms, so a screen
left open cannot bypass a new blocker.

## 4. Archive a project

1. Open the project and go to **Overview**.
2. Select **Archive project** (last header button, with its own highlight colour).
3. Check the project details at the top of the popup: **Selected project**,
   **Location** and **Status**.
4. Read the summary: *Move this project to Archived Projects. All business records
   become read-only; approved profit / loss is retained.*
5. If **Resolve these items before archiving** appears, close the popup, fix each
   item in its module, then reopen the popup. **Archive project** stays disabled
   while any blocker remains.
6. Enter a **Reason** (required, up to 500 characters). The box is compact and can
   be resized vertically for longer notes.
7. Select **Archive project**. The project moves to Archived Projects and leaves
   the WORKSPACE selector.

If another user changed the project meanwhile, the message *Project changed.
Refresh and try again.* appears. Refresh and repeat the steps.

## 5. Working with an archived project

The Overview shows a banner above the page title:

> **Archived project · Read-only**
> Archived by *username* on *date, time*
> Reason: *entered reason*
> Financial history and approved profit / loss remain in Company Cashbook.

- The last line is shown only to users who can view Company Cashbook.
- The project status appears as a coloured badge beside the project name. The
  location is shown once, under the title.
- Only **Download Report** and **UnArchive project** remain in the header.
  Project status, Quick entry, plan uploads and every create, edit, payment or
  delete action are hidden, and the API rejects them. Read-only applies to Global
  users and to project-linked Company Cashbook entries and approvals.
- Viewing pages, Audit Log, reports and permitted file downloads remain available.

## 6. UnArchive a project

1. Open **Projects > Archived Projects** and select the project.
2. In Overview, select **UnArchive project**.
3. Confirm the project details, enter a **Reason** (required) and select
   **UnArchive project**.

The project returns to Current Projects and the WORKSPACE selector with its status
unchanged, and normal permissions apply again. Use this for genuine follow-up
work, such as warranty repairs, then archive the project again when finished.

## 7. Permissions

| Requirement | Detail |
|---|---|
| Action | **Archive / UnArchive Project** (`archive_project`) under the Overview module |
| Where to grant | Project permission profile or **Global Permission**; project overrides take precedence |
| Partial Write | Update Status or Upload Plan alone does not grant archiving; Write All includes it |
| Same grant | One action covers both Archive and UnArchive |
| Profit / loss approval | Separate Global-only Company Cashbook action; archive permission does not bypass it |

Users without the action do not see the Archive or UnArchive button, and the API
rejects direct requests. See [Users and permissions](04-users-and-permissions.md#project-archive-action).

## 8. Audit trail

Every archive-related attempt is recorded in the project **Audit Log**. Type
*Archive* in the search box to find them.

| User activity | When it is recorded | Details captured |
|---|---|---|
| **Archived project** | Archive succeeded | Reason, project status, archived time before and after |
| **UnArchived project** | UnArchive succeeded | Reason, project status, previous archive time and reason |
| **Archive request blocked** | User confirmed while blockers remained | Reason, project status and every blocker |

Audit Log columns are **Username | Date and time | User activity | Record | Details
| View**. The **eye icon** in View opens the **Activity details** popup with user,
date and time, activity, record and the full change list. Rows without recorded
details show a dash. Audit ID and Reference appear only in the popup footer and in
the printed report.

## 9. Reports

- **Download Report** remains available for archived projects.
- The report header shows the company logo and name, report title, date and the
  project status pill beside the project name. No company address is printed.
- On the Overview report, the archive banner prints directly below the header,
  with a gap before the summary cards.
- Use the browser print dialog and **Save as PDF**. The export request in the
  Audit Log does not prove a file was saved.

## 10. FAQ and troubleshooting

| Question / symptom | Answer |
|---|---|
| I cannot see **Archive project**. | The project must be Completed or Cancelled, and you need the Archive action. Change the status first, or ask an account manager. |
| **Archive project** is disabled in the popup. | Blockers are listed. Resolve each one and reopen the popup. |
| The profit / loss approval is out of date. | A cost, claim or contract changed after approval. In Company Cashbook, refresh calculations, review and approve again. |
| Where did the project go after archiving? | Projects > **Archived Projects**. It is not in the WORKSPACE selector. |
| Can I edit an archived project? | No. UnArchive it first (with a reason), make the change, then archive it again. |
| Does archiving change company profit totals? | No. The latest approved projection continues to count once. |
| Why don't I see the Company Cashbook line on the banner? | It appears only for users with Company Cashbook view access. |
| Can a Planning, Active or On Hold project be archived? | No. The server rejects it, and Archived Projects shows only Completed and Cancelled groups. |
| How do I find who archived a project? | The Overview banner shows the user, date and reason; the Audit Log shows every attempt. |

## 11. Training exercise

Use a training database with synthetic data only. Never archive a live project
for practice.

1. Open an **Active** project and confirm that **Archive project** is not offered.
2. Mark a training project **Completed** and open **Archive project**. Note each
   blocker and the module that resolves it.
3. Resolve the blockers and approve the projected profit / loss in Company Cashbook.
4. Archive with a meaningful reason. Confirm the project appears only in Archived
   Projects and is missing from the WORKSPACE selector.
5. Open the archived Overview: check the banner, the status badge and that edit
   actions are absent. Download the Overview report and check the header and banner.
6. In Audit Log, search *Archive* and open each entry with the eye icon.
7. UnArchive with a reason and confirm the status is unchanged.
8. Repeat step 2 with a user who lacks the Archive action and confirm the button
   is hidden.

## 12. Presentation slides

The illustrated deck covers this feature on slides 64-75:

| Slide | Topic |
|---|---|
| 64 | Purpose: what archiving does and when to use it |
| 65 | Projects Dashboard: Current Projects tab |
| 66 | Archived Projects tab |
| 67 | Eligibility and common blockers |
| 68 | Archive popup with blockers |
| 69 | Archive popup: reason and confirm |
| 70 | Archived project: read-only Overview and banner |
| 71 | UnArchive popup |
| 72 | Permissions and audit trail |
| 73 | Audit Log: archive activity |
| 74 | Activity details popup |
| 75 | Reports and safe practice exercise |

Allow approximately 15-20 minutes for this section, plus demonstration time.
