# Vridhi Constructions & Designs

Local-first React and FastAPI construction ERP under active implementation. The API and frontend bind to loopback addresses. The recommended database is your installed PostgreSQL service on `localhost:5432`; Docker PostgreSQL on `localhost:5433` remains an opt-in alternative. Product and architecture references are kept in [`docs/`](docs/).

## Local setup

Double-click `Start-Vridhi-Mac.command` on macOS or
`Start-Vridhi-Windows.cmd` on Windows.
Install **Python 3.12, 3.13 or 3.14** and **PostgreSQL** manually first, and start
PostgreSQL. `uv`, global Node.js/npm, Docker and `pg_isready` are not required
for the normal local launch.

The shared Python bootstrap:

1. Reuses Node.js 22.12+ (22.x) or 24.x with npm, or downloads a private Node.js
   24 LTS runtime into `.tools/`. Official HTTPS downloads are SHA-256 checked
   against Node.js's published checksums before extraction.
2. Creates/uses `apps/backend/.venv` and installs `requirements-runtime.txt`.
   Test packages and global Python packages are not needed.
3. Asks for database host, port, username, hidden password and application database
   when `.env` does not exist. It generates a random session secret and preserves
   existing configuration. Credentials are not printed in startup messages.
   First-run database names use letters, digits and underscores (maximum 63
   characters, starting with a letter or underscore), for example `vridhi_dev`.
4. Verifies the actual database connection without PostgreSQL CLI tools. If the
   database is missing, asks approval to create only that database using the
   configured account (which needs CREATEDB permission). Otherwise ask your DBA
   to create it. No existing data is reset.
5. Applies migrations and installs frontend packages with `npm ci --include=dev`
   when manifests, Node version/platform or required install markers change.
   Lockfile URLs use public npm with integrity hashes.
6. Starts API/Vite on loopback, verifies readiness, then opens the browser.
   Healthy services tracked by this bootstrap are reused. Changed source or
   configuration requires an explicit restart. Untracked listeners are not adopted
   and no process is killed automatically.

Internet access to `nodejs.org`, PyPI (or an approved configured mirror), and npm
is required for uncached setup. Trusted TLS certificates/proxy settings must
work; verification is never disabled. If Node downloads are blocked, install
Node.js 24 LTS manually. Offline Python-only first-run setup is not supported.
Targets are current macOS (Apple Silicon/Intel) and Windows (x64/ARM64), subject
to the installed Python/Node release's OS support, not every historical OS version.

Services keep running after the launcher closes. Logs: `.run/startup.log`,
`.run/api.log`, `.run/frontend.log`. Process IDs: `.run/api.pid` and
`.run/frontend.pid`. Stop a specific owned PID using `kill PID` on macOS or
`taskkill /PID PID` on Windows, confirm the listener stopped, then relaunch.
Do not copy `.tools/`, `.venv/`, `.run/` or `node_modules/` between machines.

Read-only prerequisite checks: `./Start-Vridhi-Mac.command --check` or
`Start-Vridhi-Windows.cmd --check`. `--no-browser` starts normally without opening a tab.
Resolve OS downloaded-file restrictions before running; the macOS command also
needs execute permission.

Existing `DATABASE_MODE=docker` configurations remain an optional path requiring
Docker installed/running. New configurations use manually installed PostgreSQL.
Manual startup alternatives follow:

1. Copy `.env.example` to `.env`, set `DATABASE_MODE=local`, and adjust `DATABASE_URL` for your installed PostgreSQL user, password and database. Example format: `postgresql+asyncpg://YOUR_USER:YOUR_PASSWORD@localhost:5432/vridhi_dev`. Ensure the database exists and the user can create tables/migrations in it. Set a local `SESSION_SECRET`; keep `.env` out of Git. On an empty database, the initial username is `administrator`, with Global access and all Users permissions. The initial password is stored only as an Argon2id hash, not plaintext. An optional `INITIAL_PASSWORD_HASH` setting accepts an encoded Argon2 hash; single-quote its value in `.env` to preserve dollar signs. `DEMO_PASSWORD` is no longer supported and should be removed from older environment files. Change the initial password before sharing the installation. Existing accounts are not modified. Create, Edit, and Reset Password store only salted Argon2id hashes in PostgreSQL's `users.password_hash` field. Database connection credentials and the session signing secret are separate service secrets, not user passwords, and still require secure configuration.
2. Confirm PostgreSQL accepts connections at the host/port in `.env`. PostgreSQL CLI tools are optional for launcher use. For Docker mode instead, set `DATABASE_MODE=docker`, configure `POSTGRES_PASSWORD`, and the launcher starts Compose PostgreSQL on host port 5433.
3. In `apps/backend`, create `.venv` with `python -m venv .venv`, activate it, install `python -m pip install -r requirements-runtime.txt`, apply `python -m alembic upgrade head`, then run `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`. The runtime list excludes test packages.
4. In `apps/frontend`, run `npm ci`, then `npm run dev`. Open `http://127.0.0.1:5173`. Vite proxies `/api` to FastAPI. If port 5173 is occupied, start with `npm run dev -- --port 5174`; the local API allows both loopback origins.
5. API docs are at `http://127.0.0.1:8000/docs`; readiness is `/api/v1/ready`.

At API startup, SQLAlchemy automatically creates missing mapped tables, then seeds an empty database. It does not alter existing columns. Use `python -m alembic upgrade head` in the backend environment for schema changes. The initial account password is Argon2id-hashed.

To switch the existing setup from Docker PostgreSQL, edit `.env` and change `DATABASE_MODE=docker` (or an absent mode inferred from port 5433) to `DATABASE_MODE=local`, then point `DATABASE_URL` to your installed server on port 5432. This only changes which database the app connects to: it does not copy or delete data. The existing Docker volume remains untouched. If you need those records in local PostgreSQL, export/import them separately with `pg_dump`/`pg_restore`.

PostgreSQL and dependency installation are separate concerns. Runtime packages
must be accessible through PyPI or an approved pip mirror/cache; frontend packages
must be accessible through npm. The bootstrap upgrades pip for modern certificate
support. Configure approved proxy, CA and package-index settings where required;
never disable TLS verification. Docker PostgreSQL remains separate from a local
PostgreSQL server, using port 5433 and its own named volume.

## Persistence and backups

Normal `docker compose down` preserves `vridhi_pgdata`; removing Docker volumes or resetting Docker Desktop can delete it. The named volume is persistence, not backup. Local uploaded files belong under `data/uploads/`, outside frontend static assets. Back up PostgreSQL and uploaded files separately; they do not synchronize to an installed database or cloud service.

## Current implementation boundary

The frontend and backend are separate local processes in one monorepo. Implemented vertical slice: backend sessions, portfolio/project detail, project status history, procurement create/edit and payment ledger, ordered inventory registration/read model, starter billing entries, timecards, local user listing, dashboard and portfolio summary. Seed data and calculations are development samples.

Not yet implemented: invitation/reset delivery, complete project/value document APIs, full role/permission and membership administration, payment receipts and idempotency persistence, goods-receipt/movement workflows, approved change-order lifecycle, complete contract/invoice/client payment models, full attendance approval/correction, audit console, exports, production storage scanning, robust automated migrations, and comprehensive authorization granularity. The source design describes 112 API method/routes; this codebase is a smaller first slice and must not be represented as all 112 production APIs implemented.

## Checks

Backend runtime dependencies are declared in `apps/backend/requirements-runtime.txt`
and mirrored in `apps/backend/pyproject.toml`. The standard `requirements.txt`
includes the runtime list. For backend testing, install `requirements-dev.txt`,
which also includes runtime dependencies. Frontend dependencies are separate:
use `apps/frontend/package.json` and its lockfile with `npm ci`; Python requirements
do not install JavaScript packages. PostgreSQL and Node.js must be installed
separately. Training-presentation generation tools are not application dependencies.

From the backend directory, using the intended Python environment:

```sh
python -m pip install -r requirements.txt
# For development/testing instead:
python -m pip install -r requirements-dev.txt
```

```sh
cd apps/frontend && npm run build
cd ../backend && uv run pytest
```