# Vridhi Deployment Strategy

## 1. Scope and Recommended Architecture

Use one Git repository (a monorepo) containing two applications:

- Frontend: React SPA, Vite, Tailwind CSS, and TanStack Query.
- Backend: FastAPI, Pydantic v2, SQLAlchemy 2.x async, and Alembic.
- Database: PostgreSQL, accessed by the backend only.
- Documents: private object storage; optionally MinIO for S3-compatible local development.

These are separate runtime processes, not necessarily separate repositories or physical servers. Keep the backend a modular monolith with domain boundaries, not 112 independently deployed API services. The planned endpoint count includes future workflows; implement working vertical slices incrementally.

This is a strategy document, not generated application infrastructure. Example commands and configuration become runnable only after the repository is scaffolded. Existing design references: [construction-erp-plan.md](construction-erp-plan.md), [construction-erp-model-schema.md](construction-erp-model-schema.md), [construction-erp-api-contracts.md](construction-erp-api-contracts.md), and [construction-erp-ui-api-mapping.md](construction-erp-ui-api-mapping.md).

## 2. Does Docker PostgreSQL Use My Installed Database?

**No. A PostgreSQL container starts a separate PostgreSQL server and database cluster. It does not automatically write into the PostgreSQL instance installed on your Mac.**

| Concept | What it means |
|---|---|
| Docker image | PostgreSQL software and initialization logic; pulling/building an image alone does not run a database |
| Container | Running instance of that image, with its own PostgreSQL server |
| Named volume | Persistent storage attached to the container's PostgreSQL data directory |
| Locally installed PostgreSQL | A different server with its own data directory, users, databases, and lifecycle |
| Port mapping | Network access to the container; it does not connect or synchronize two databases |

On macOS, Docker Desktop normally stores named volumes within its Linux VM's managed storage. They are on your machine, but **not inside your locally installed PostgreSQL database**. Changes appear in whichever server your backend connection URL selects.

Recommended local choices:

1. **Docker PostgreSQL:** consistent version and setup for developers; use a named volume for persistence. Your installed PostgreSQL is not needed by the application.
2. **Installed PostgreSQL:** create a dedicated application database/user on that server and configure the backend URL accordingly. Do not start the Compose database service.

Do not mount an existing installed PostgreSQL data directory into a container or let two servers write the same directory. Version, permissions, platform, and concurrent-access differences can corrupt data. Move data between servers using supported dump/restore or migration procedures, not by assuming shared storage.

## 3. Repository Layout

```text
vridhi-erp/
├── apps/
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── app/           # Router, providers, app shell
│   │   │   ├── features/      # Projects, procurement, inventory, etc.
│   │   │   ├── components/    # Shared UI components
│   │   │   └── lib/           # API client, query keys, formatting
│   │   ├── package.json
│   │   ├── package-lock.json
│   │   └── vite.config.ts
│   └── backend/
│       ├── app/
│       │   ├── main.py
│       │   ├── core/          # Settings, security, permissions
│       │   ├── db/            # Async sessions, model registration
│       │   └── modules/       # Domain routers, schemas, models, services
│       ├── migrations/       # Alembic revisions
│       ├── tests/
│       ├── alembic.ini
│       ├── pyproject.toml
│       └── uv.lock
├── docs/                     # Plan, entities, API and UI contracts
├── prototype/                # Existing standalone HTML prototype
├── compose.yaml
├── .env.example              # Infrastructure template, no real secrets
├── .gitignore
└── README.md
```

Suggested backend module files: router.py, schemas.py, models.py, service.py. Module examples: identity, projects, procurement, inventory, billing, attendance, reports. Database transactions and authorization belong in the backend service layer, not frontend calculations.

Commit Alembic revisions, package/uv lockfiles, test fixtures with synthetic data, and environment templates. Ignore actual .env files, virtual environments, node_modules, build output, logs, uploaded files, database data and backups. Do not relocate the current documents/prototype until repository scaffolding is explicitly performed.

## 4. Local Development Topology

Run infrastructure in Docker and application code directly on the Mac initially. This makes hot reload, debugging and incremental changes straightforward.

| Process | Local address | Responsibility |
|---|---|---|
| Vite | http://localhost:5173 | Development SPA with hot reload |
| FastAPI | http://localhost:8000 | API; interactive documentation at /docs |
| Docker PostgreSQL | localhost:5433 | Host-accessible database; container itself listens on 5432 |
| Installed PostgreSQL, if used instead | Usually localhost:5432 | Alternative database; verify the actual configured port |
| Optional MinIO | localhost:9000; console often 9001 | Private development object storage; host-bound ports only |

Use 5433 for Docker's host port to avoid conflicting with an installed PostgreSQL server on 5432. Verify port availability; use another port if occupied. Never expose PostgreSQL publicly just to let the browser reach it: the browser talks only to the API.

```mermaid
flowchart LR
    Browser[Browser at localhost 5173] --> Vite[Vite dev server]
    Vite -->|Proxy API requests| API[FastAPI on localhost 8000]
    API -->|localhost 5433| DockerDB[Container PostgreSQL on 5432]
    DockerDB --> Volume[Named Docker volume]
    API --> Objects[Optional private MinIO storage]
    Installed[Installed PostgreSQL on localhost 5432]
    Alternative[Alternative connection instead of Docker DB] -.-> Installed
```

## 5. Docker PostgreSQL Example

Use the official PostgreSQL image rather than building a custom database image unless extensions require one. Example compose.yaml configuration, intentionally pinned to PostgreSQL major version 17:

```yaml
services:
  postgres:
    image: postgres:17
    environment:
      POSTGRES_DB: vridhi_dev
      POSTGRES_USER: vridhi_dev
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD in your local .env}
    ports:
      - "127.0.0.1:5433:5432"
    volumes:
      - vridhi_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  vridhi_pgdata:
```

The data path above is for this selected image version. Check official image guidance before changing major versions; newer image layouts may differ. Do not upgrade a populated database just by changing the major image tag. Plan and test pg_upgrade or dump/restore. Pin an approved patch/digest for production reproducibility and update through a controlled process.

POSTGRES_DB/USER/PASSWORD initialize a new empty volume only. Editing these environment values does not automatically rename an existing database/user or reset its password. The example user is the image's initialization superuser and is suitable only for isolated development. Production needs separate administrative/migration credentials and a least-privilege runtime role.

### Persistence Behavior

| Operation | Database data behavior |
|---|---|
| Stop/restart container | Named-volume data survives |
| Recreate container using the same volume | Data survives |
| Normal `docker compose down` | Containers/network removed; named volume retained |
| Remove named volumes or reset Docker Desktop storage | Data may be permanently lost |
| Change Compose project name or volume identity | May attach a different empty volume; old volume may still exist |
| Delete/copy image | Does not back up or contain the named-volume database data |

Do not use volume-removal options as routine shutdown commands. A volume provides persistence, not a backup. Keep synthetic local data and test restoration regularly.

## 6. Backend Connection Configuration

Connection URL forms below contain placeholders, not credentials. SQLAlchemy's async driver example is asyncpg; install/configure it through backend dependencies. Load DATABASE_URL from backend settings explicitly; placing a value in a root .env does not automatically make FastAPI load it.

| Backend location / database choice | URL form |
|---|---|
| Backend on Mac -> Docker PostgreSQL | postgresql+asyncpg://USER:PASSWORD@localhost:5433/vridhi_dev |
| Backend on Mac -> installed PostgreSQL | postgresql+asyncpg://USER:PASSWORD@localhost:5432/vridhi_dev |
| Backend container on same Compose network -> postgres service | postgresql+asyncpg://USER:PASSWORD@postgres:5432/vridhi_dev |
| Backend container -> installed Mac PostgreSQL | postgresql+asyncpg://USER:PASSWORD@host.docker.internal:5432/vridhi_dev |

Inside a container, localhost refers to that container, not the Mac or the postgres service. The last option needs installed PostgreSQL listen/access rules and firewall configuration; it is not automatic. Prefer the shared Compose network if both API and database are containerized. Avoid publishing the database port entirely for a container-only production topology.

URL-encode special characters in credentials, or construct SQLAlchemy URLs using its structured URL API. Keep credentials out of frontend environment variables, logs and Git. For installed PostgreSQL, create the dedicated development database/user with appropriate privileges rather than using unrelated existing customer databases.

## 7. Frontend Proxy and Authentication

React calls relative paths such as /api/v1/me. Configure Vite to forward /api to FastAPI, keeping the prefix unchanged:

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

The browser remains on the frontend origin. Use credentialed requests and the documented CSRF bootstrap/header flow. Keep localhost versus 127.0.0.1 consistent across browser URLs and cookie settings. Configure the backend's trusted development origins for CSRF independently of CORS.

Use environment-specific cookie configuration: HttpOnly, explicit SameSite policy, appropriate path and expiry; local plain-HTTP development may need Secure disabled, but production always uses Secure with HTTPS. Do not configure a cookie domain that prevents it being accepted on the browser's development origin. A proxy simplifies origins but does not replace CSRF protection or authorization.

VITE_* values are bundled into browser code and therefore public. Production should normally retain relative /api requests behind the same-origin reverse proxy. TanStack Query caches server data; it is not a persistent replacement for the database or secure session storage.

## 8. Local Startup Workflow

Prerequisites: Docker Desktop (for container infrastructure), Node.js supported by the selected Vite release, the agreed Python interpreter/environment, and backend/frontend dependency tooling. Select and configure the backend virtual environment before running Python commands. Python and framework version support should be pinned in repository tooling.

After scaffolding, use this workflow:

1. Create local environment files from templates; enter credentials directly in your terminal/editor, not into chat. Set the backend URL for exactly one database choice.
2. Install locked frontend/backend dependencies. A proposed convention is npm ci in apps/frontend and uv sync in apps/backend.
3. Start infrastructure from the repository root: `docker compose up -d postgres`. Optional MinIO needs a separate service/configuration and private bucket initialization.
4. Verify database readiness: `docker compose exec postgres pg_isready -U vridhi_dev -d vridhi_dev`.
5. From apps/backend, apply migrations: `uv run alembic upgrade head`. Run a separate idempotent development seed command once it exists, not automatic production demo seeding.
6. From apps/backend, start API: `uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`.
7. From apps/frontend, start UI: `npm run dev`. Open http://localhost:5173 and test API contracts at http://localhost:8000/docs.
8. Stop application processes when finished and use `docker compose stop postgres` or ordinary `docker compose down` for infrastructure shutdown, without removing volumes.

If using installed PostgreSQL, skip Compose startup and readiness commands; verify the installed service and database connection instead. Alembic still manages the same schema. Do not run multiple migration processes concurrently.

## 9. Backups and Moving Between Databases

Use PostgreSQL logical dumps for development migration between Docker and installed PostgreSQL. Named-volume copying is not a portable live backup strategy.

Example database dump from the proposed container (run in the repository root):

```sh
docker compose exec -T postgres pg_dump -U vridhi_dev -d vridhi_dev -Fc > vridhi-dev.dump
```

This creates a binary dump file containing potentially sensitive data; keep it out of Git. To restore into a separately created empty database on your installed server, use a compatible pg_restore client:

```sh
pg_restore --host=localhost --port=5432 --username=LOCAL_USER \
  --dbname=EMPTY_TARGET_DB --no-owner --no-privileges vridhi-dev.dump
```

Use your actual target identity/database, with credentials handled through approved local PostgreSQL mechanisms. Do not restore into an important existing database or use destructive cleanup options without an explicit backup/recovery plan. Validate schema, row counts, sequences, access privileges and application workflows after restoration. Logical dumps do not include cluster-wide roles; manage those separately.

Database backups do not include uploaded object bytes. Back up private object storage and database metadata together, with retention, encryption and restore drills. Production backups require automated schedules and agreed recovery-point/recovery-time objectives, not just a local command. Data never synchronizes automatically between the container server and installed server.

## 10. Production Deployment

Two applications do not require two physical servers. A small initial deployment can use one host with a reverse proxy serving built React assets and forwarding /api to FastAPI. A managed PostgreSQL service and managed private object storage reduce operational workload when affordable.

```mermaid
flowchart LR
    Browser[User browser] -->|HTTPS| Proxy[Reverse proxy or gateway]
    Proxy --> Static[Built React static assets]
    Proxy -->|API routes| API[FastAPI modular monolith]
    API --> DB[Private PostgreSQL]
    API --> Objects[Private object storage]
    DB --> Backup[Encrypted database backups]
    Objects --> ObjectBackup[Object backups and retention]
```

- Build frontend with npm run build; deploy generated static assets. Configure SPA history fallback for application routes, but never rewrite missing /api routes to HTML. Vite's dev server is not the production server.
- Build a separate backend image with locked dependencies. Do not package secrets or mutable uploads into it. Run without reload; size workers/connection pools against database capacity and measure load.
- Use HTTPS, Secure/HttpOnly cookies, CSRF validation, trusted proxy configuration, restricted CORS where needed, and private database networking. Redact secrets and financial personal data from logs.
- Apply migrations as a controlled release step once, before compatible app rollout; never have every worker run migrations on startup. Prefer backward-compatible expand/contract changes and test rollback/recovery strategies.
- Add health/readiness endpoints to the backend contract before deployment: process health differs from readiness to serve DB-dependent requests. These operational endpoints are additional to the documented 112 domain endpoints if introduced.
- Configure service restart policies, resource limits, database connection pooling, error monitoring, structured request IDs, uptime alerts and storage/backup monitoring.
- Separate dev, staging and production databases, buckets and secrets. Test new releases in staging with synthetic/anonymized data.
- Use a least-privilege runtime DB role, separate migration/admin credentials, and approved secret management. Protect object downloads through short-lived authorized links and malware-scanning lifecycle checks.
- For fully containerized deployments, use separate frontend/proxy, API and database services; do not combine all processes and database data inside one application image. Image deployment is not a database migration or backup.

## 11. Implementation Order and Validation

Start with login -> project access -> procurement -> payments -> inventory registration/receipts. Deliver frontend screens and their backend models, migrations and tests together. Then add document/value approvals, billing, attendance and reporting. Do not wait for all 112 planned endpoints to exist before integrating the UI.

Before calling a local setup complete, verify:

- Migrations work on an empty database and upgrades preserve existing test data.
- Creating a record survives API/container restart using the same named volume.
- API connects to the intended server/port, not another local database accidentally.
- Frontend proxy, session cookies, CSRF and permission-restricted project access work end to end.
- Partial/full payments reconcile and fully paid Edit/Add Payment restrictions hold server-side.
- PO creation adds inventory catalog links but only actual receipts add received stock.
- Document bytes stay private and backup/restore includes both objects and metadata.
- Automated tests, build/type checks, dependency lockfile installs and restore drills pass before release.