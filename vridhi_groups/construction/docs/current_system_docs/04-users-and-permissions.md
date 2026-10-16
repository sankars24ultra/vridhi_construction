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
2. **Read: Export Report.** A separate grant; read access alone does not grant export.
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

## Users page: separate account permission

Users is independent of project context. Its directory lists all non-deleted
accounts rather than filtering by selected project.

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

Audit Access controls menu/list availability; Export Report controls its report.
The selected project must still be accessible to the account. An audit grant alone
does not assign every project. Global access includes both audit capabilities.

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
| Inventory reviewer | Inventory Allow; no writes; Export Report if needed |
| Multi-project site operator | Shared selected projects; review/reduce the broad preset before saving |
| User-support operator | No projects, Global off, Users Allow with only required lifecycle actions |
| Project activity reviewer | Assigned project, Audit Allow, export only if needed; operational writes not required |
| Installation administrator | Global baseline reviewed; all Users/Audit grants; protect credentials carefully |

## Troubleshooting missing menus/actions

Confirm the selected project, assigned memberships, module Allow/Block, Write
All/Partial selections, export grant and record state. Refresh after an
administrator saves permissions. If UI and API disagree, report the action,
project, time and error to support; do not bypass checks.
