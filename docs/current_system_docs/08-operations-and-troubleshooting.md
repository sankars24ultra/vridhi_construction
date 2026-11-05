# 8. Installation, Operations and Troubleshooting

[Documentation home](README.md)

## Local startup

Manual prerequisites: Python 3.12, 3.13 or 3.14 and installed/running PostgreSQL.
The launcher prepares a private Node.js 24 LTS runtime if needed, a backend virtual
environment and locked frontend dependencies. `uv` and PostgreSQL CLI tools are
not needed. Internet/trusted certificates are required for uncached downloads.

1. Use [Start-Vridhi-Mac.command](../../Start-Vridhi-Mac.command) on macOS or
   [Start-Vridhi-Windows.cmd](../../Start-Vridhi-Windows.cmd) on Windows.
2. On first launch, enter database connection details when prompted (password hidden).
   Existing `.env` settings are preserved. Creating a missing application database
   needs explicit approval and a database account with CREATEDB permission.
3. Apply migrations before using an existing database with updated code.
4. Leave the API/frontend services running while working.
5. Open the URL printed by the launcher.

Local PostgreSQL normally uses 5432. The optional Compose database exposes 5433.
These are separate database instances; changing connection configuration does not
transfer accounts or project data.

Manual development commands, from the construction project root:

```sh
cd apps/backend
# First activate the Python environment containing the runtime dependencies.
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```sh
cd apps/frontend
npm ci
npm run dev
```

Use the URL Vite prints (normally 5173; 5174 may be used when occupied).
`/api/v1/health` checks process liveness; `/api/v1/ready` checks database readiness.
The live API explorer is `http://127.0.0.1:8000/docs`.

For a read-only prerequisite check, use the platform launcher with `--check`.
`--no-browser` starts services without opening a tab. Logs are `.run/startup.log`,
`.run/api.log` and `.run/frontend.log`; owned process IDs are in `.run/*.pid`.
The launcher reuses only tracked healthy services and does not kill untracked
listeners. If source/configuration changes, stop the indicated owned PID before
relaunching. Do not transfer `.tools/`, `.venv/`, `.run/` or `node_modules/`
between machines. The optional existing Docker mode still needs Docker.

### Temporary macOS launcher

[startup_mac.command](../../startup_mac.command) uses already installed backend
packages and the Node.js on PATH, without downloading Node or installing packages.
It is a local workaround for a blocked Node download, not a fresh-machine installer.
It warns when using a Node version outside the normal launcher's supported range.
Existing database checks, migrations, port safeguards and readiness checks still
apply. PostgreSQL must be running. Use `./startup_mac.command --check` for read-only
installed-dependency checks or `--no-browser` for startup without opening a tab.
It shares the normal launcher's logs, tracked services and explicit restart rules.

## Initial account and passwords

An empty database seeds `administrator` with global/module settings and sample
data. Obtain its initial credential privately; no plaintext bootstrap password
belongs in these guides. An encoded Argon2id `INITIAL_PASSWORD_HASH` can override
the first-run hash. Keep dollar signs intact when setting it in `.env`.

Existing accounts are not reset by startup. Reset passwords through authorized
Users actions. All Create/Edit/Reset paths hash passwords before database storage.
Changing a configuration value is not a mechanism for recovering an existing
account's password.

## Uploads and service settings

Use the single project-local [uploads directory](../../data/uploads/).
Relative `UPLOAD_DIRECTORY=data/uploads` resolves from the construction root.
Do not reintroduce a parent-level duplicate folder or move files without updating
the matching metadata. The default upload maximum is 10 MB; supported types vary
by plan, PO image and labor attachment endpoint.

Keep `.env` private. Database passwords/session-signing secrets are service
credentials and cannot be replaced with a user-password hash.

## Backup / restore

Use **Company > Backup & Restore** ([guide](14-backup-and-restore.md)):

1. Create a backup (or turn on the daily 9:00 PM backup) with a passphrase of at
   least 8 characters, and store the passphrase separately.
2. Save the `.vbak` file and copy it off this computer (Google Drive, Gmail, USB).
3. To recover, a Global access user restores the file from the same page. The
   current data is first saved to `data/backups/safety/`.

If the app cannot start, use the command line from the construction folder:

```bash
python3 scripts/backup.py create [--out FILE]
python3 scripts/backup.py restore FILE   # stop the app first
```

Backup needs PostgreSQL client tools (`pg_dump`/`pg_restore`) of the same or a
newer major version than the server; Homebrew `postgresql@16` is detected
automatically, and Docker mode uses the container's tools. Keep `.env` private and
separate from backups. Deleting Docker volumes can destroy their contents; a
persistent volume is not an independent backup.

## Troubleshooting

| Symptom | Check / response |
|---|---|
| PostgreSQL connection refused | Confirm the configured host/port, not just that PostgreSQL is installed. Local Homebrew PostgreSQL normally uses 5432; the optional Docker server uses 5433. Changing servers requires valid credentials and does not transfer data. |
| API unavailable | Database readiness, backend process, intended port and Vite proxy |
| 405 on a newly added action | Confirm running backend loaded current routes; stale non-reloading process may need restart |
| Invalid/expired CSRF token | Refresh session/bootstrap and retry; retain unsaved work; do not disable validation |
| 401 | Session missing/expired/revoked or account disabled; sign in again where appropriate |
| Disabled-account message | Ask an authorized manager to reactivate account |
| Missing menu | Selected project, membership, module Access, standalone Users/Audit grants |
| Missing action | Partial action grants and record eligibility (paid PO, active worker, stock) |
| Empty project picker | No assigned/global projects; Users-only accounts can still use Users |
| User absent from directory | Deleted marker or search filter; Users is no longer project-filtered |
| Cannot edit username | Intentional immutable account identity |
| Conflict / changed record | Refresh and review the latest state before resubmitting |
| Missing document | Check metadata and configured uploads directory together |
| PDF misses rows | Check module export scope, filters, page size, collapsed sections and print preview |
| Unexpected dark PDF | Verify current shared print styles are loaded; refresh; inspect preview |
| Notes disappear | Session storage is temporary; sign-out/tab closure/storage restrictions can remove it |

## Change and release checks

Run the frontend build in `apps/frontend` and backend tests in the configured
backend environment. Use targeted tests first, then the appropriate broader suite.
Restart non-reloading services after code changes. Do not stop unrelated processes.

The initial migration contains a fixed schema snapshot, not the current ORM
metadata. Later revisions add their own tables/columns. Keep this separation when
adding models so that migrating a completely empty PostgreSQL database remains
supported; do not stamp an uncreated schema as migrated to bypass errors.

Before production: configure HTTPS, secure cookies, restricted origins, deployment
service supervision, least-privilege database access, backup/restore testing,
file handling/retention policy and representative operational acceptance tests.
This guide does not claim those deployment tasks are already completed.
