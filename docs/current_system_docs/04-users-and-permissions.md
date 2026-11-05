# 4. Users, Access and Permissions

[Documentation home](README.md)

## The access model

Business-role labels such as Owner, Admin, Cashier, Supervisor and Managing
Director are not the current authorization model. Access comes from account
profiles and project memberships. A legacy database role field remains for
compatibility; it is not a reason to expect broad access.

### Three project-access patterns

| Pattern | Effect |
|---|---|
| Individual project permissions | Assign projects and configure each project's modules separately |
| Shared access for selected projects | Apply one profile to the checked projects only |
| Global access | Use one baseline profile across all available projects |

Switching on Shared access initializes all read/export/write actions for the five
operational modules; Users is excluded from that project preset. Review the
separate Users section. Shared access is saved as membership profiles, not a
live link that grants future unselected projects.

Global access automatically grants all Users and Audit Log actions. Project
modules still use the global profile and any explicit membership overrides.
A project override replaces that module's baseline settings; global does not
mean the API ignores saved project overrides.

## Module configuration

1. **Access: Allow / Block.** Block denies the page, not just its write buttons.
2. **Read: Download Report.** A separate grant; read access alone does not grant export.
3. **Write: All / Partial.** All permits applicable module actions; Partial permits
   only checked actions. With no checks, there is no partial write access.

| Project module | Configurable actions |
|---|---|
| Overview | Quick Entry, Upload Plan Document, Update Status |
| Procurement | Create / Edit Purchase Order; Add Payment |
| Inventory | Receive Stock; Use Stock |
| Cash flow | New Application; Record Receipt |
| Labor and Wages | New Labor Contract; Add Worker; Log Weekly Work; Pay Weekly Work; Edit Worker; Deactivate Worker; Download Contract Files; Download History Files |

Record eligibility still matters. A paid PO may not be editable; a missing active
worker or unavailable stock can disable an otherwise authorized operation.
Cross-module shortcuts may need the destination module's actual write permission.

## Project archive action

Overview includes one **Archive / UnArchive Project** action (`archive_project`).
Configure it in either the project permission profile or the **Global Permission**
profile; project-specific overrides still take precedence. With Write set to
Partial, Update Status or Upload Plan alone does not grant archiving. Write All
includes it, consistent with other Overview actions.

Archived project business records are read-only even for users with Global access.
Only the separately authorized UnArchive action can restore normal write behavior.
Project access and read/report/file-download permissions remain in force. Project
financial checks do not bypass the Global-only Company Cashbook result approval.

## Dashboard permissions

Add/Edit user includes **Dashboard permissions**, independently of project modules:

- **Access Allow** shows the Projects Dashboard, listing only projects the account
  can access. **Block** hides that dashboard and its Projects menu entry.
- Blocked users can still select assigned projects from the project selector and
  use only their allowed modules. They are routed to an accessible project module
  on sign-in; accounts with no accessible project see guidance rather than a dashboard.
- **Write: New Project** enables creation only when Dashboard Access is Allow.
  Without it, New Project is disabled and the creation API returns 403.
- Global access includes both permissions. Non-global accounts default to Block,
  including existing accounts with no Dashboard profile. Grant Allow explicitly
  where continued dashboard access is wanted.
- A user administrator cannot grant Dashboard rights they do not hold. Changes
  appear in user details and account history.
- A non-global project creator receives read-only Overview access to the project
  they created. Creation does not grant Procurement, Cash Flow or other operational
  write permissions; an authorised administrator assigns further project access.

The project listing API remains available for the assigned-project selector;
Dashboard Block does not remove existing project memberships. Apply migration
`0026_dashboard_permission` before starting the updated backend.

## Users page: separate account permission

Users is independent of project context. Its directory lists all non-deleted
accounts rather than filtering by selected project.

When adding a user, a valid username is checked against the server when the field
loses focus and again before **Next** opens Access permissions. The form shows
checking, available, already-in-use or lookup-error feedback. An unavailable
username or failed check keeps the form on Account details. The **Next** button is
disabled when the username is already in use and becomes available again when
the username is changed. Checks ignore letter case and include inactive and
deleted accounts, whose usernames remain reserved.
Changing the username clears the previous feedback; late results cannot advance
a changed or closed form. The lookup requires Add/Edit users permission.
User creation still validates uniqueness, since availability does not reserve a
username. Editing an existing user keeps its username read-only.

| Grant | What it enables |
|---|---|
| Access | Open directory and read user information |
| Export user directory | Print/Save as PDF the directory |
| Add/Edit users | Create or edit accounts, assignments and settings |
| Reset Password | Reset credentials; required for password changes through Edit too |
| Activate/Deactivate | Restore or block login; deactivation revokes active sessions |
| Delete | Remove from directory and block login while retaining historical references |
| History | Read account activity/change history |

View is read-only and follows directory access. Reset/Status/Delete cannot target
your own account. Delete is a retained-record soft deletion, not a database purge
and not a promise that the old username becomes reusable.

Account managers should be trusted administrators: assigning broader user
permissions is itself a privileged capability. Do not grant Add/Edit merely
because someone needs to view the directory.

## Audit Log: separate account permission, project-specific data

Audit Access controls menu/list availability; Download Report controls its report.
The selected project must still be accessible to the account. An audit grant alone
does not assign every project. Global access includes both audit capabilities.

## Company Audit Log: separate account permission, company-wide data

**Company Audit Log permissions** (View: Allow/Block) control the Company Audit
Log menu, which lists all Company Cashbook activity (entries, declarations,
approvals, voids and report requests) across all dates. It is blocked by default
and independent of Company Cashbook access: a user can review the audit log
without seeing the cashbook, and Cashbook users do not see the log unless it is
allowed. Global access always includes it. You cannot grant it unless you have
it. Accounts that already had Company Cashbook access when this permission was
introduced kept the audit log. A user with only this permission needs no project
assignment.

The audit log's **View activity details** icon shows the logged event, including
visits to the company finance tabs. There is no open-entry action.
**Download Report** is a separate checkbox under Company Audit Log permissions;
it defaults to off for non-global users. Global access includes report downloads.
You cannot grant a report permission that you do not have. Company Cashbook no
longer has a duplicate History tab; use the dedicated Company Audit Log menu
with its own View and Download Report permissions.

## Backup & Restore: separate account permission, Restore is Global only

**Backup & Restore permissions** (Backup: Allow/Block) show the Company
**Backup & Restore** menu and allow creating and saving a full encrypted backup of
all company data. It is blocked by default, needs no project assignment, and you
cannot grant it unless you have it. Global access always includes it.

Daily backup settings and **Restore from backup** are always **Global access only**
and cannot be granted, because a restore replaces every user's data. See
[Backup & Restore](14-backup-and-restore.md).

## Editing accounts safely

- Username is immutable in both the editor and API.
- Work email and contact number are optional.
- Email, when present, must be valid and unique; username uniqueness is checked
  case-insensitively.
- New/replacement passwords require at least six characters; use a stronger
  organizational policy for real deployments.
- Passwords are salted Argon2id hashes in PostgreSQL, not reversible encrypted text.
- Reset and deactivation revoke existing sessions.
- View shows account/contact/access information but never password hashes or tokens.
- History shows readable field/permission changes; login events are excluded there.

## Example profiles

| Need | Suggested configuration |
|---|---|
| Procurement entry clerk | Assigned project; Procurement Allow, Create/Edit checked; payment/export only if required |
| Inventory reviewer | Inventory Allow; no writes; Download Report if needed |
| Multi-project site operator | Shared selected projects; review/reduce the broad preset before saving |
| User-support operator | No projects, Global off, Users Allow with only required lifecycle actions |
| Project activity reviewer | Assigned project, Audit Allow, export only if needed; operational writes not required |
| Installation administrator | Global baseline reviewed; all Users/Audit grants; protect credentials carefully |

## Troubleshooting missing menus/actions

Confirm the selected project, assigned memberships, module Allow/Block, Write
All/Partial selections, export grant and record state. Refresh after an
administrator saves permissions. If UI and API disagree, report the action,
project, time and error to support; do not bypass checks.
