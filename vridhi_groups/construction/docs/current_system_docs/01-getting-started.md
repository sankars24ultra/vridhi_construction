# 1. Getting Started

[Documentation home](README.md)

## Who uses Vridhi?

Vridhi brings project purchasing, materials, client receipts, labor records, and
account administration into one workspace. A user's actual responsibilities are
defined by assigned projects and module/action permissions, not a job-title role.

## First installation versus everyday login

An empty database is seeded at backend startup, including an initial
`administrator` account and synthetic sample data. An installed machine connected
to an existing database uses that database's existing accounts; it does not create
a separate set of users merely because the computer changed.

Obtain the initial credential through your installation administrator. The
bootstrap configuration contains an Argon2id hash, not a recoverable plaintext
password. Existing users are not overwritten by first-run seeding. See
[operations](08-operations-and-troubleshooting.md) for installation details.

## Sign in

1. Start the configured database, backend, and frontend using the appropriate
   launcher, or ask support for the application URL.
2. Enter your username or work email, and password.
3. Select **Sign in**.
4. If you have only Users-page access, you can use Users without choosing a project.
   Project work requires an accessible project.

Wrong credentials receive a generic error. A correct password for an inactive
account produces: "Your account is disabled. Please contact your administrator
to reactivate it." Disabled/deleted accounts cannot obtain a valid application session.

There is no documented, implemented email-delivery recovery workflow here. Ask a
user manager with Reset Password permission to reset your password.

## Understand the screen

| Area | Purpose |
|---|---|
| Projects | Portfolio of projects accessible to your account |
| WORKSPACE picker | Switch projects; status appears beside each project |
| Left menu | Permitted modules for the current context |
| Breadcrumb / project context | Confirms which project you are working in |
| Day/Dark switch | Changes screen appearance; reports still print in day colors |
| Date and clock | Local browser date/time |
| Notes icon | Temporary personal notes available across modules |
| User badge | My Details: read-only account and permission summary |
| Sign out | Ends the session and clears that account's session notes |

The project picker closes after selection, outside click, or Escape. On phones,
the project picker is above the horizontally scrollable menu row. Swipe the menu
row to reach additional permitted modules; wide tables scroll inside their panels.

## Choose a project

Choose a card in Projects, or select a project from WORKSPACE. Confirm its name
before entering purchases, receipts, stock movements, or labor work. Switching
projects changes the data context and re-evaluates permissions.

Project lifecycle labels are Planning, Active, On Hold, Completed, and Cancelled.
They are business states, not permission levels. A financial action can also be
unavailable because of its record state, not merely because of access settings.

## Read versus write

- **Allow** lets you open a module; **Block** prevents access.
- **Export Report** is a separate read capability.
- **Write All** authorizes all applicable module actions.
- **Write Partial** authorizes only checked actions.
- Actions may be hidden or disabled when permission or record eligibility is missing.

See [permissions](04-users-and-permissions.md) before requesting broader access.

## Personal Notes

Open Notes, type reminders, and move between modules. Text, open/collapsed state,
and preferred panel width use account-specific browser session storage.

- Drag the panel's left edge to resize, or focus it and use arrow keys.
- Collapse does not erase the text; Clear asks for confirmation.
- Refresh in the same tab normally retains text.
- Successful sign-out clears the notes. Failed sign-out does not deliberately clear them.
- Closing the tab/session can remove notes; they are not shared or backed up in PostgreSQL.
- Notes do not appear in exported reports. Do not use them as permanent project records.

## A sensible first working session

1. Check My Details and confirm the assigned projects/permissions.
2. Select the correct project.
3. Review Overview, then the operational module you need.
4. Record a reference/comment when saving financial or stock activity.
5. Verify the resulting row and totals; use history where available.
6. Export a report if authorized, then sign out on a shared machine.
