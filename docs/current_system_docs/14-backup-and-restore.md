# 14. Backup & Restore

[Documentation home](README.md) | [Permissions](04-users-and-permissions.md#backup--restore-separate-account-permission-restore-is-global-only) |
[Data and persistence](07-data-and-persistence.md#what-is-stored-where) |
[Operations](08-operations-and-troubleshooting.md#backup--restore)

Feature update: 31 October 2026.

## 1. Purpose

**Company > Backup & Restore** saves the whole system into one encrypted file
(`.vbak`). If the computer fails, is replaced or the data is damaged, importing that
file brings everything back exactly as it was when the backup was made.

Backup status and any waiting daily backup appear first. **Create backup** and
**Daily backup** sit side by side on desktop, with **Restore from backup**
full-width below them. Cards and form fields stack on smaller screens.
The status strip also shows the last successful restore date/time and the username
that performed it (or the command-line operator). It shows **Never** if no
successful restore is recorded. Failed attempts do not replace this information.

The application runs on this computer, so a backup kept only on this computer does
not protect against disk failure or theft. **Always move the file somewhere else**,
such as Google Drive, a Gmail draft to yourself or a USB drive.

## 2. What a backup contains

| Included | Not included |
|---|---|
| All projects, archived projects and their modules | Sign-in sessions (everyone signs in again after a restore) |
| Company Cashbook, borrowings and approvals | Duplicate-request records (temporary) |
| Users, passwords (hashed) and all permissions | Diagnostic logs in `data/logs/` |
| Project and Company Audit Logs, User History | Theme, notes and other browser-only settings |
| Every uploaded document and image (`data/uploads/`) | `.env` connection settings and secrets |

Each file also records who created it, when, the database version, record counts
and a checksum for every part. A damaged or edited file is rejected before
anything is changed.

## 3. Passphrase

- Every backup is encrypted (AES-256-GCM, scrypt key) with a passphrase of at
  least **8 characters**.
- The passphrase is needed to restore. **It cannot be recovered or reset.** Store
  it separately from the file (for example in a password manager), never in the
  same Drive folder or email.
- A wrong passphrase and a damaged file show the same message:
  *Wrong passphrase, or the backup file is damaged.*

## 4. Who can use it

| Action | Who |
|---|---|
| Open Backup & Restore, create and save a backup | Global access, or users with **Backup & Restore permissions: Allow** |
| Daily backup settings | Global access only |
| Restore from backup | Global access only |

Backup is blocked by default. You can only grant it if you have it yourself. A
user with only this permission needs no project assignment. See
[Users and permissions](04-users-and-permissions.md).

## 5. Create a backup now

1. Open **Company > Backup & Restore**.
2. Under **Create backup**, enter and confirm the passphrase, then select
   **Create backup**. Progress is shown while the database and documents are packed.
3. When ready, select **Save to…**:
   - Chrome / Edge open a **Save as** dialog: choose the folder (for example a
     Google Drive for desktop folder or a USB drive). The page confirms when the
     file is saved.
   - Other browsers download the file to the Downloads folder; then select
     **I've saved it**.
4. Upload the file to Google Drive or email it to yourself, then delete the local
   copy if it is not in a safe place.

The file is named `vridhi-backup-YYYYMMDD-HHMM.vbak`. It can be downloaded only
once; the server copy is deleted after saving, so no backups pile up on this
computer. An unsaved backup is discarded after 24 hours.

## 6. Daily backup

Global access users can turn on **Prepare a backup every day** (default **9:00 PM**)
and set the passphrase used for daily files.

Select **Time** to open the same analog clock used in the Audit Log filter.
Choose the hour, then minutes and AM/PM, and select **OK**. **Cancel** leaves the
time unchanged. Select **Save settings** to apply the schedule.

- At the chosen time the system prepares `vridhi-daily-backup-….vbak`.
- If the computer is off or the app is closed at that time, the backup is prepared
  the **next time the app starts**.
- Users with backup permission then see a banner on every page:
  **Daily backup ready… Save backup / Later**. Saving removes the waiting copy.
  **Later** hides it until this browser tab is closed.
- Only the latest waiting daily backup is kept; a newer one replaces it.
- The health strip on the page turns amber when no backup has been saved yet, when
  nothing has been saved for 2 days, or when the last daily backup failed.

The daily passphrase is stored on this computer, encrypted with a machine key in
`data/backups/.machine-key`. Remember it: it is required to restore daily files.

## 7. Restore from a backup

Restore **replaces all current data** with the file contents.

1. Sign in with a Global access account and open **Backup & Restore**.
2. Under **Restore from backup**, choose the `.vbak` file, enter its passphrase and
   select **Check backup**.
3. Review the summary: created date and by whom, projects, users, audit events,
   documents and database version.
4. Type `RESTORE` and select **Restore all data**.
5. While the restore runs (usually under a minute) other users see a maintenance
   message. When it finishes, everyone is signed out; select **Go to sign in**.

Safety measures:

- Before replacing anything, the current data is saved as
  `data/backups/safety/vridhi-before-restore-….vbak` using the **same passphrase**
  as the restored file. Only the latest safety copy is kept.
- The file is restored into a separate staging database and checked against its
  record counts. The live data is swapped only after every check passes; if
  anything fails, current data is untouched.
- Backups from an older app version are upgraded automatically. A backup made by
  a newer app version is refused; update the app first.
- Only one backup or restore can run at a time.

### Recover on a new computer

1. Install and start the app with `scripts/bootstrap.py` (see
   [Getting started](01-getting-started.md)) and complete first sign-in.
2. Sign in as the Global access user and restore the file as above. After restore,
   sign in with the accounts and passwords **from the backup**.

## 8. Command line (when the app cannot start)

Run from the construction folder:

```bash
python3 scripts/backup.py create [--out FILE]   # app may be running
python3 scripts/backup.py restore FILE          # close the app first
```

The passphrase is asked for interactively. Restore refuses to run while the app is
running, creates the same safety copy, signs everyone out and records the restore
in the Company Audit Log.

## 9. Audit trail

All events appear in the **Company Audit Log** and its Download Report:

| Event | Recorded when |
|---|---|
| Backup created | A manual or daily backup file was prepared (daily ones show actor *System*) |
| Backup saved | The user confirmed the file was saved |
| Backup failed | Preparing the file failed |
| Backup schedule updated | Daily backup time / on-off / passphrase changed |
| Data restored from backup | A restore completed (records the file, creator and safety copy) |
| Restore failed / Restore rejected | A restore stopped; current data was kept |

## 10. Troubleshooting

| Message / symptom | What to do |
|---|---|
| *Wrong passphrase, or the backup file is damaged* | Check the passphrase (case-sensitive). Download the file again from Drive / Gmail. |
| *This backup was made by a newer version* | Update the application, then restore. |
| *Another backup or restore is already running* | Wait for it to finish and try again. |
| *pg_dump for PostgreSQL N was not found on this computer* | Install PostgreSQL client tools of the same or newer major version as the server (Homebrew `postgresql@16`), or run in Docker mode. |
| Save dialog does not appear | The browser has no Save-as support; the file is in Downloads. Select **I've saved it**. |
| Daily banner keeps reappearing | Save the file with **Save backup**; **Later** only hides it until the tab is closed. |
| Signed out unexpectedly | A restore was performed. Sign in again with the restored accounts. |

Docker mode (`DATABASE_MODE=docker`) uses `docker compose exec` for the database
tools when they are not installed locally.
