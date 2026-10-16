# 10. Training Presentation and Presenter Guide

[Documentation home](README.md) | [Illustrated PowerPoint](vridhi-system-training-illustrated.pptx) | [Original PowerPoint](vridhi-system-training.pptx)

## Illustrated edition

The illustrated edition retains all 28 original explanation slides and adds 16
paired visual walkthrough slides (44 slides total), with presenter notes.
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
| 22 | Printable report with company header |

The slide numbering in the illustrated deck includes the inserted walkthroughs.
The table below refers to the preserved original 28-slide edition.

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
| 12 | Audit Log | Dedicated menu abstract: project activities, search, pagination and export |
| 13 | New Project: from form to workspace | Required fields, initial status and optional plan |
| 14 | Change project status safely | Allowed transitions, comment, hold reason, completion confirmation |
| 15 | Plan documents and project value | Original-file download versus report; estimate changes on upload |
| 16 | Purchasing to stock: two separate events | PO -> receipt -> use; vendor payment is a separate money event |
| 17 | Labor: choose the correct cost path | Direct earned/paid versus contract certified/paid |
| 18 | Add/Edit User: two steps | Immutable username, optional contacts, no role dropdown |
| 19 | Project permissions and access scopes | Individual, shared selected projects, global baseline/overrides |
| 20 | Standalone Users and Audit permissions | Action-specific grants and project-independent Users menu |
| 21 | Investigate a time interval | Shortcuts, range calendar, analog time, Apply and Clear |
| 22 | Export Report: how PDF is created | Browser print -> Save as PDF, day colors and company header |
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

Before distribution, replace the report-header company-address placeholder in
the application if official external PDFs are required. Do not present these
slides as production certification or include actual credentials in speaker notes.
