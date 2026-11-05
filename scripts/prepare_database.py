"""Check configured PostgreSQL; create only the named database after user approval."""

import argparse
import asyncio
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/backend"))

import asyncpg
from sqlalchemy.engine import make_url
from app.core.config import settings
from dotenv import dotenv_values


async def prepare(create=False):
    mode = dotenv_values(ROOT / ".env").get("DATABASE_MODE", "local")
    if mode == "docker":
        if not shutil.which("docker"):
            raise RuntimeError("Existing configuration selects Docker, but Docker is missing. Use your manual PostgreSQL connection in .env or install/start Docker.")
        subprocess.run(["docker", "compose", "up", "-d", "postgres"], cwd=ROOT, check=True)
    elif mode != "local":
        raise RuntimeError("DATABASE_MODE must be local or docker.")
    url = make_url(settings.database_url)
    if url.drivername != "postgresql+asyncpg" or not url.database:
        raise RuntimeError("DATABASE_URL must be a postgresql+asyncpg URL with an application database name.")
    dsn = url.set(drivername="postgresql").render_as_string(hide_password=False)
    # Docker startup can take longer; local PostgreSQL is managed by the user.
    for attempt in range(30 if mode == "docker" else 1):
        try:
            connection = await asyncpg.connect(dsn, timeout=5)
            break
        except (OSError, asyncpg.CannotConnectNowError):
            if mode != "docker" or attempt == 29:
                raise RuntimeError("PostgreSQL is not accepting connections. Start the server and check host/port in .env.") from None
            await asyncio.sleep(2)
        except asyncpg.InvalidCatalogNameError:
            if not create:
                print("Configured application database does not exist.")
                return 3
            admin_dsn = url.set(drivername="postgresql", database="postgres").render_as_string(hide_password=False)
            admin = await asyncpg.connect(admin_dsn, timeout=10)
            try:
                identifier = '"' + url.database.replace('"', '""') + '"'
                await admin.execute(f"CREATE DATABASE {identifier}")
            finally:
                await admin.close()
            connection = await asyncpg.connect(dsn, timeout=10)
            break
    try:
        await connection.execute("SELECT 1")
    finally:
        await connection.close()
    print("PostgreSQL connection verified. No existing data was reset.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--create", action="store_true")
    args = parser.parse_args()
    try:
        sys.exit(asyncio.run(prepare(args.create)))
    except (asyncpg.PostgresError, OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        # Never echo a DSN or raw connection exception that may include credentials.
        detail = str(error) if isinstance(error, RuntimeError) else type(error).__name__
        print(f"Database setup failed: {detail}. Check credentials/permissions in .env or contact your DBA.", file=sys.stderr)
        sys.exit(1)
