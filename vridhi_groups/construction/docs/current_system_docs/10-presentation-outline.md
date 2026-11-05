# 10. Training Presentation and Presenter Guide

[Documentation home](README.md) | [Illustrated PowerPoint](training-illustrated.pptx)

## Illustrated edition

The illustrated edition retains all 28 original explanation slides and 16
paired visual walkthrough slides. The 30 October 2026 update adds 18 Company
Cashbook training slides before the original closing checklist. The 31 October
2026 update adds 12 Project Archive slides after the Cashbook section. A new
opening Welcome slide, an actual Login-screen walkthrough and a final business
Thank you slide bring the deck to **88 slides total**, including 11 Backup & Restore slides (76-86) added on 31 October 2026.
Presenter notes are retained on the original training slides.
All previous slides remain. The presentation displays the edition date
16 December 2026 and the Cashbook training date 10 December 2026.
The explanation slides use the same Lucide icon shapes as the application;
the paired slides show the corresponding actual frontend screen or dialog.

Screenshots use isolated, synthetic training API responses, not live database
records. No real accounts, credentials or financial records were accessed or
changed. Screens are cropped where useful to focus on the relevant area;
sections below the crop continue in the actual application. Icons and images
are embedded, with no dependency on external files when presenting.

Visual walkthroughs follow these original explanation slides:

| Original slide | Sample screenshot |
|---|---|
| 4 | Workspace and top-bar controls |
| 5-12 | Projects, Overview, Procurement, Inventory, Cash flow, Labor and Wages, Users, Audit Log |
| 13 | New Project form |
| 14 | Project status dialog |
| 15 | Plan-document and value history |
| 18 | User wizard: account details |
| 19 | User wizard: project scope and standalone permissions |
| 21 | Audit date-range calendar and time controls |
| 22 | Printable report with company header and project status |

The slide numbering in the illustrated deck includes the inserted walkthroughs.
The table below refers to the preserved original 28-slide edition.

The illustrated deck now opens with **Welcome to Vridhi**, introducing workspace
orientation, connected operations and company financial visibility.
Slide 5 shows the actual Login screen with an empty form and client-facing
callouts for username/email, password visibility and Sign in. It follows the
sign-in explanation on slide 4. No credentials are displayed.
Slide 88 closes with **Thank you** and **Building trust. Creating futures.**,
reinforcing clear records, teamwork and confident business decisions before
inviting questions and next steps.

### Company Cashbook update: illustrated slides 46-63

| Illustrated slide | Topic |
|---|---|
| 46 | Cashbook purpose, four tabs and separate Company Audit Log |
| 47 | Cashbook screen and financial context |
| 48 | Starting balances, categories, direction and transaction workflow |
| 49 | Cash transaction form walkthrough |
| 50 | Worked example: cash versus spending versus outstanding principal |
| 51 | New Loan and Loan Repayment rules |
| 52 | Borrowing summary, lender statuses, filters and history |
| 53 | Loan Repayment popup: principal and interest |
| 54 | Shared Overview projection and Global-access approval |
| 55 | Project results, refresh, filtering and approval history |
| 56 | Approval popup and immutable saved basis |
| 57 | Owner capital boundaries and Mark as invalid correction |
| 58 | Owner Capital screen |
| 59 | Mark as invalid confirmation popup |
| 60 | Independent Cashbook/Audit permissions and Global-only actions |
| 61 | Company Audit Log screen, visits, search and time filtering |
| 62 | Exact activity details and separate popup report |
| 63 | Report scopes and safe training exercise |

### Project Archive update: illustrated slides 64-75

| Illustrated slide | Topic |
|---|---|
| 64 | Archive purpose: what it does and when to use it |
| 65 | Projects Dashboard: Current Projects tab, counts and pagination |
| 66 | Archived Projects tab: Completed and Cancelled only |
| 67 | Eligibility, permission, reason and common blockers |
| 68 | Archive popup listing blockers |
| 69 | Archive popup: reason and confirm |
| 70 | Archived Overview: read-only banner, status badge and actions |
| 71 | UnArchive popup: status unchanged |
| 72 | Archive permission and audit events |
| 73 | Audit Log with archive activity and the eye icon |
| 74 | Activity details popup |
| 75 | Reports and safe practice exercise |

The Project Archive section adds approximately 15-20 minutes of training. Its
companion [feature and training guide](13-project-archive.md) contains the
blocker list, step-by-step procedures, FAQ and exercise. The same update
refreshed the Projects (slides 8-9) and Audit Log (slides 22-23) screenshots and
callouts for the Current/Archived tabs and the eye-icon View column, and added
an archive item to the closing checklist.

The original closing checklist is now slide 76. New screenshots use the current
frontend with isolated synthetic API responses. No live business records were
accessed or changed; different fixtures are not a reconciled ledger.
Current UI wording is **Download Report** and **Mark as invalid**. Historical
screenshots in the preserved project-module section reflect their capture date.
The Company Cashbook section adds approximately 20-30 minutes of training.
Its companion [feature and training guide](12-company-cashbook-training.md)
contains the full workflows, calculation example, permission matrix and limitations.

The deck is an editable, widescreen PowerPoint with presenter notes. It uses
schematic diagrams and editable tables/cards, not screenshots of live financial
records. Examples are illustrative. It can be used for an approximately 35-50
minute introduction, with additional time for demonstrations.

## Slide-by-slide guide

| # | Slide | Teaching point / suggested demonstration |
|---|---|---|
| 1 | Vridhi: Project operations, connected | What this application is and who the training is for |
| 2 | One project, connected records | Purchasing, stock, labor, client receipts and audit work together |
| 3 | Sign in and orient yourself | Initial administrator versus existing accounts; do not distribute credentials in slides |
| 4 | Your workspace at a glance | Picker, permitted menus, theme, clock, My Details, Notes and Sign out |
| 5 | Projects | Dedicated menu abstract: portfolio and project selection |
| 6 | Overview | Dedicated menu abstract: health, history, plans and consolidated cost |
| 7 | Procurement | Dedicated menu abstract: ordered value, vendor payments and PO actions |
| 8 | Inventory | Dedicated menu abstract: receipts, consumption, available stock and ledger |
| 9 | Cash flow | Dedicated menu abstract: client billing, receipts and allocations |
| 10 | Labor and Wages | Dedicated menu abstract: direct workers versus subcontract claims |
| 11 | Users | Dedicated menu abstract: standalone all-user directory and account lifecycle |
| 12 | Audit Log | Dedicated menu abstract: project activities, search, pagination, eye-icon details and export |
| 13 | New Project: from form to workspace | Required fields, initial status and optional plan |
| 14 | Change project status safely | Allowed transitions, comment, hold reason, completion confirmation |
| 15 | Plan documents and project value | Original-file download versus report; estimate changes on upload |
| 16 | Purchasing to stock: two separate events | PO -> receipt -> use; vendor payment is a separate money event |
| 17 | Labor: choose the correct cost path | Direct earned/paid versus contract certified/paid |
| 18 | Add/Edit User: two steps | Immutable username, optional contacts, no role dropdown |
| 19 | Project permissions and access scopes | Individual, shared selected projects, global baseline/overrides |
| 20 | Standalone Users and Audit permissions | Action-specific grants and project-independent Users menu |
| 21 | Investigate a time interval | Shortcuts, range calendar, analog time, Apply and Clear |
| 22 | Download Report: how PDF is created | Browser print -> Save as PDF, day colors and company header |
| 23 | Know what your report includes | Explicit full-fetch reports versus rendered/filtered/paginated sections |
| 24 | Understand the financial numbers | Ordered/earned/certified cost differs from cash and stock |
| 25 | My Details, Notes and mobile work | Temporary notes, resize, sign-out cleanup and mobile navigation |
| 26 | Architecture and safe storage | React -> FastAPI -> PostgreSQL; uploads and logs separate |
| 27 | First run, backup and support | Private bootstrap credential, migrations, restore and request context |
| 28 | Practice checklist and next steps | Safe training scenario and where to find each guide |

## Suggested training exercise

Use a non-production training database. Create a sample Planning project, move it
to Active with a meaningful comment, and add a purchase order. Receive part of a
material, record some use, then inspect the stock ledger. Record client billing
and an allocated receipt. Add a worker/work entry or subcontract claim using
the appropriate path. Review audit activity and export one report.

Demonstrate a read-only account afterward to show that a visible module is not
the same as permission to edit, pay, download files or export.

Report headers show the company logo and name, report title, date and, for
project reports, the project status; no company address is printed. Do not present these
slides as production certification or include actual credentials in speaker notes.
