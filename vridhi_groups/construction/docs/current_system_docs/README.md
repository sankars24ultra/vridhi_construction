# Vridhi: Current System Documentation

Source-reviewed edition: 16 October 2026.

This set explains the React/FastAPI application currently implemented in this
workspace, not just the original HTML prototype. It is written for operators,
account administrators, support staff, and developers joining the project.
Examples are illustrative; project counts, balances, and usernames vary by database.

## Start here

| Reader / question | Read next |
|---|---|
| New operator: how do I sign in and get started? | [Getting started](01-getting-started.md) |
| What does each left menu do? | [Module guide](02-module-guide.md) |
| How do I create projects and complete everyday tasks? | [Workflow walkthroughs](03-workflow-walkthroughs.md) |
| How do user access and permissions work? | [Users and permissions](04-users-and-permissions.md) |
| How do reports export, and what do financial numbers mean? | [Reports and calculations](05-reports-and-calculations.md) |
| How do the frontend, API, and database fit together? | [Architecture and API map](06-architecture-and-api-map.md) |
| Where is information stored? | [Data and persistence](07-data-and-persistence.md) |
| How do I install, back up, or troubleshoot the application? | [Operations guide](08-operations-and-troubleshooting.md) |
| What does this documentation verify, and what still needs checking? | [Evidence and acceptance checklist](09-evidence-and-acceptance.md) |
| Can I train someone using slides? | [Illustrated training presentation](vridhi-system-training-illustrated.pptx), [original text deck](vridhi-system-training.pptx), and [slide outline](10-presentation-outline.md) |

## The system in one minute

1. Sign in to your account.
2. Open **Projects** or the **WORKSPACE** selector and choose an accessible project.
3. Work in **Overview**, **Procurement**, **Inventory**, **Cash flow**, or
   **Labor and Wages**, according to your permissions.
4. Open **Audit Log** to review that project's recorded activities, if permitted.
5. Open **Users** to manage accounts, if permitted. This directory is independent
   of project selection.
6. Use **Notes** for temporary personal reminders, and **Export report** for the
   module's print/Save as PDF report.

## Important interpretation

- Access is based on permission profiles, not the old Owner/Admin/Cashier role names.
- A menu being visible does not mean every write action is allowed.
- Global access exposes all projects, but project-specific profiles can override
  project-module permissions. Users and Audit permissions are separate.
- Save as PDF uses the browser print dialog; it is not an automatic server PDF download.
- An audit export event means export was requested, not that a file was saved.
- The application is local-first. Network/production deployment requires additional
  configuration and validation.
- This edition is a source review, not a new full-suite test run or production certification.

## Relationship to the older documents

The documents in [initial_level_docs](../initial_level_docs/) remain unchanged.
They are historical design/prototype references, not a checklist of features still
missing. This set takes precedence when teaching the current UI. The live API
schema at `/docs`, the implementation, and future tested releases remain the
authority when behavior changes.

No password, hash, session token, or database credential is published in this set.
