"""Full-system backup and restore.

A backup is a single ``.vbak`` file: an AES-256-GCM encrypted (scrypt passphrase key)
zip containing ``manifest.json``, ``database.dump`` (pg_dump custom format) and ``uploads/``.
Restore loads the dump into a staging database, verifies it, migrates it, then swaps it in.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import re
import secrets
import shutil
import struct
import subprocess
import sys
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4

import asyncpg
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from sqlalchemy.engine import make_url

from app.core.config import settings

ROOT = Path(__file__).resolve().parents[4]
BACKEND_DIR = Path(__file__).resolve().parents[2]
BACKUP_ROOT = settings.upload_directory.parent / "backups"
FORMAT_NAME = "vridhi-backup"
FORMAT_VERSION = 1
MAGIC = b"VRIDHIBK\x01"
CHUNK_SIZE = 1024 * 1024
TRANSIENT_TABLES = ("auth_sessions", "idempotency_records")
MIN_PASSPHRASE = 8
Progress = Callable[[str], None]


class BackupError(Exception):
    pass


def _noop(_: str) -> None:
    pass


def backup_dir(name: str) -> Path:
    path = BACKUP_ROOT / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def validate_passphrase(passphrase: str) -> None:
    if len(passphrase or "") < MIN_PASSPHRASE:
        raise BackupError(f"Passphrase must be at least {MIN_PASSPHRASE} characters")


def backup_filename(moment: datetime | None = None, prefix: str = "vridhi-backup") -> str:
    return f"{prefix}-{(moment or datetime.now()).astimezone().strftime('%Y%m%d-%H%M')}.vbak"


# ---------------------------------------------------------------- encryption

def _derive_key(passphrase: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return Scrypt(salt=salt, length=32, n=n, r=r, p=p).derive(passphrase.encode("utf-8"))


def encrypt_file(source: Path, target: Path, passphrase: str) -> None:
    salt, prefix = secrets.token_bytes(16), secrets.token_bytes(7)
    header = json.dumps({"kdf": "scrypt", "n": 2 ** 15, "r": 8, "p": 1, "salt": base64.b64encode(salt).decode(),
                         "nonce": base64.b64encode(prefix).decode(), "chunk": CHUNK_SIZE}).encode()
    cipher = AESGCM(_derive_key(passphrase, salt, 2 ** 15, 8, 1))
    size = source.stat().st_size
    with source.open("rb") as reader, target.open("wb") as writer:
        writer.write(MAGIC + struct.pack(">I", len(header)) + header)
        counter, remaining = 0, size
        while True:
            chunk = reader.read(CHUNK_SIZE)
            remaining -= len(chunk)
            final = remaining <= 0
            sealed = cipher.encrypt(prefix + struct.pack(">I", counter) + (b"\x01" if final else b"\x00"), chunk, header)
            writer.write(struct.pack(">I", len(sealed)) + sealed)
            counter += 1
            if final:
                break


def decrypt_file(source: Path, target: Path, passphrase: str) -> None:
    with source.open("rb") as reader, target.open("wb") as writer:
        if reader.read(len(MAGIC)) != MAGIC:
            raise BackupError("This is not a Vridhi backup file (.vbak)")
        try:
            header = reader.read(struct.unpack(">I", reader.read(4))[0])
            meta = json.loads(header)
            prefix = base64.b64decode(meta["nonce"])
            cipher = AESGCM(_derive_key(passphrase, base64.b64decode(meta["salt"]), meta["n"], meta["r"], meta["p"]))
        except (struct.error, ValueError, KeyError) as error:
            raise BackupError("Backup file header is damaged") from error
        counter = 0
        while True:
            length_bytes = reader.read(4)
            if len(length_bytes) < 4:
                raise BackupError("Backup file is incomplete (it may have been cut off while copying)")
            sealed = reader.read(struct.unpack(">I", length_bytes)[0])
            base = prefix + struct.pack(">I", counter)
            try:
                writer.write(cipher.decrypt(base + b"\x00", sealed, header))
            except InvalidTag:
                try:
                    writer.write(cipher.decrypt(base + b"\x01", sealed, header))
                except InvalidTag as error:
                    if counter == 0:
                        raise BackupError("Wrong passphrase, or the backup file is damaged") from error
                    raise BackupError("Backup file is damaged") from error
                if reader.read(1):
                    raise BackupError("Backup file has unexpected extra data")
                return
            counter += 1


def _machine_key() -> bytes:
    path = backup_dir("") / ".machine-key"
    if not path.exists():
        path.write_bytes(secrets.token_bytes(32))
        os.chmod(path, 0o600)
    return path.read_bytes()


def seal_secret(value: str) -> str:
    nonce = secrets.token_bytes(12)
    return base64.b64encode(nonce + AESGCM(_machine_key()).encrypt(nonce, value.encode(), b"vridhi-schedule")).decode()


def open_secret(value: str) -> str:
    raw = base64.b64decode(value)
    return AESGCM(_machine_key()).decrypt(raw[:12], raw[12:], b"vridhi-schedule").decode()


# ---------------------------------------------------------------- database tooling

@dataclass
class DbTarget:
    host: str
    port: int
    user: str
    password: str | None
    database: str

    def dsn(self, database: str | None = None) -> str:
        url = make_url(settings.database_url).set(drivername="postgresql", database=database or self.database)
        return url.render_as_string(hide_password=False)

    def sqlalchemy_url(self, database: str) -> str:
        return make_url(settings.database_url).set(database=database).render_as_string(hide_password=False)


def db_target() -> DbTarget:
    url = make_url(settings.database_url)
    return DbTarget(url.host or "localhost", url.port or 5432, url.username or "", url.password, url.database or "")


def database_mode() -> str:
    from dotenv import dotenv_values
    return (os.environ.get("DATABASE_MODE") or dotenv_values(ROOT / ".env").get("DATABASE_MODE") or "local").strip()


def _tool_major(path: str) -> int | None:
    try:
        output = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=15).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    match = re.search(r"(\d+)(?:\.\d+)?", output or "")
    return int(match.group(1)) if match else None


def find_pg_tool(name: str, server_major: int) -> list[str] | None:
    exe = name + (".exe" if os.name == "nt" else "")
    candidates = [shutil.which(name)]
    for major in range(server_major, server_major + 4):
        candidates += [f"/opt/homebrew/opt/postgresql@{major}/bin/{exe}", f"/usr/local/opt/postgresql@{major}/bin/{exe}",
                       f"/Applications/Postgres.app/Contents/Versions/{major}/bin/{exe}", f"/usr/lib/postgresql/{major}/bin/{exe}",
                       f"C:/Program Files/PostgreSQL/{major}/bin/{exe}"]
    for candidate in [c for c in candidates if c]:
        if Path(candidate).exists() and (_tool_major(candidate) or 0) >= server_major:
            return [candidate]
    return None


async def server_major(target: DbTarget) -> int:
    connection = await asyncpg.connect(target.dsn())
    try:
        return int(await connection.fetchval("SHOW server_version_num")) // 10000
    finally:
        await connection.close()


async def pg_command(name: str, target: DbTarget) -> tuple[list[str], dict[str, str], bool]:
    """Return (argv prefix, env, inside_docker) for pg_dump / pg_restore matching the server version."""
    major = await server_major(target)
    tool = find_pg_tool(name, major)
    env = {**os.environ}
    if tool:
        if target.password:
            env["PGPASSWORD"] = target.password
        return [*tool, "-h", target.host, "-p", str(target.port), "-U", target.user], env, False
    if database_mode() == "docker" and shutil.which("docker"):
        return ["docker", "compose", "exec", "-T", "postgres", name, "-U", target.user], env, True
    raise BackupError(f"{name} for PostgreSQL {major} was not found on this computer. Install the PostgreSQL {major} client tools.")


async def _run(argv: list[str], env: dict[str, str], stdin_path: Path | None = None, stdout_path: Path | None = None) -> None:
    stdin = stdin_path.open("rb") if stdin_path else subprocess.DEVNULL
    stdout = stdout_path.open("wb") if stdout_path else subprocess.DEVNULL
    try:
        process = await asyncio.create_subprocess_exec(*argv, stdin=stdin, stdout=stdout, stderr=subprocess.PIPE, env=env, cwd=ROOT)
        _, stderr = await process.communicate()
    finally:
        for handle in (stdin, stdout):
            if hasattr(handle, "close"):
                handle.close()
    if process.returncode:
        message = (stderr or b"").decode(errors="replace").strip().splitlines()
        raise BackupError(f"{Path(argv[0]).name if argv[0] != 'docker' else argv[5]} failed: {message[-1] if message else 'exit ' + str(process.returncode)}")


async def _table_counts(connection: asyncpg.Connection) -> dict[str, int]:
    tables = [row["tablename"] for row in await connection.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")]
    return {name: int(await connection.fetchval(f'SELECT count(*) FROM public."{name}"')) for name in tables if name not in TRANSIENT_TABLES}


# ---------------------------------------------------------------- create

def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def _upload_files() -> list[Path]:
    base = settings.upload_directory
    if not base.exists():
        return []
    return sorted(path for path in base.rglob("*") if path.is_file() and not path.name.startswith("."))


def _pack(work: Path, dump: Path, manifest: dict, out_zip: Path) -> None:
    files = {"database.dump": _sha256(dump)}
    uploads = _upload_files()
    total = 0
    for path in uploads:
        files["uploads/" + path.relative_to(settings.upload_directory).as_posix()] = _sha256(path)
        total += path.stat().st_size
    manifest["uploads"] = {"count": len(uploads), "bytes": total}
    manifest["database"] = {"file": "database.dump", "bytes": dump.stat().st_size}
    manifest["files"] = files
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, indent=2))
        archive.write(dump, "database.dump", compress_type=zipfile.ZIP_STORED)
        for path in uploads:
            archive.write(path, "uploads/" + path.relative_to(settings.upload_directory).as_posix())


async def create_backup(out_path: Path, passphrase: str, created_by: str, progress: Progress = _noop) -> dict:
    validate_passphrase(passphrase)
    target = db_target()
    work = backup_dir("work") / uuid4().hex
    work.mkdir(parents=True)
    try:
        progress("Exporting database")
        argv, env, docker = await pg_command("pg_dump", target)
        dump = work / "database.dump"
        connection = await asyncpg.connect(target.dsn())
        try:
            async with connection.transaction(isolation="repeatable_read", readonly=True):
                snapshot = await connection.fetchval("SELECT pg_export_snapshot()")
                excluded = [arg for table in TRANSIENT_TABLES for arg in ("--exclude-table-data", f"public.{table}")]
                await _run([*argv, "-d", target.database, "-Fc", "--no-owner", "--no-privileges", f"--snapshot={snapshot}", *excluded], env, stdout_path=dump)
                counts = await _table_counts(connection)
                revision = await connection.fetchval("SELECT version_num FROM alembic_version")
                server_version = await connection.fetchval("SHOW server_version")
        finally:
            await connection.close()
        progress("Packing documents")
        manifest = {"format": FORMAT_NAME, "format_version": FORMAT_VERSION, "app_name": settings.app_name,
                    "created_at": datetime.now(timezone.utc).isoformat(), "created_by": created_by,
                    "alembic_revision": revision, "postgres_version": server_version, "tables": counts,
                    "excluded_data": list(TRANSIENT_TABLES), "tool": "docker" if docker else "local"}
        archive = work / "backup.zip"
        await asyncio.to_thread(_pack, work, dump, manifest, archive)
        progress("Encrypting")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        partial = out_path.with_name(out_path.name + ".partial")
        await asyncio.to_thread(encrypt_file, archive, partial, passphrase)
        partial.replace(out_path)
        manifest["file_bytes"] = out_path.stat().st_size
        return manifest
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ---------------------------------------------------------------- open / validate

def known_revisions() -> set[str]:
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    return {script.revision for script in ScriptDirectory.from_config(config).walk_revisions()}


_SAFE_UPLOAD = re.compile(r"^uploads/(?!.*(?:^|/)\.\.(?:/|$))[A-Za-z0-9._/-]+$")


def _validate_archive(zip_path: Path) -> dict:
    try:
        archive = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as error:
        raise BackupError("Backup contents are damaged") from error
    with archive:
        try:
            manifest = json.loads(archive.read("manifest.json"))
        except (KeyError, ValueError) as error:
            raise BackupError("Backup manifest is missing or damaged") from error
        if manifest.get("format") != FORMAT_NAME:
            raise BackupError("This is not a Vridhi backup file")
        if int(manifest.get("format_version", 0)) > FORMAT_VERSION:
            raise BackupError("This backup was made by a newer version of Vridhi. Update the app before restoring it.")
        expected: dict = manifest.get("files") or {}
        names = {info.filename for info in archive.infolist() if not info.is_dir()} - {"manifest.json"}
        if names != set(expected) or "database.dump" not in names:
            raise BackupError("Backup contents do not match its manifest")
        for name in names:
            if name != "database.dump" and not _SAFE_UPLOAD.match(name):
                raise BackupError("Backup contains an unsafe file path")
            digest = hashlib.sha256()
            with archive.open(name) as handle:
                for block in iter(lambda: handle.read(CHUNK_SIZE), b""):
                    digest.update(block)
            if digest.hexdigest() != expected[name]:
                raise BackupError(f"Backup file check failed for {name}")
    if manifest.get("alembic_revision") not in known_revisions():
        raise BackupError("This backup was made by a newer version of Vridhi. Update the app before restoring it.")
    return manifest


def open_backup(path: Path, passphrase: str, work: Path) -> tuple[Path, dict]:
    """Decrypt and fully verify a backup file. Returns the decrypted zip path and manifest."""
    work.mkdir(parents=True, exist_ok=True)
    zip_path = work / "backup.zip"
    decrypt_file(path, zip_path, passphrase)
    return zip_path, _validate_archive(zip_path)


def preview(manifest: dict) -> dict:
    tables = manifest.get("tables") or {}
    keys = {"projects": "Projects", "users": "Users", "company_cash_entries": "Cashbook entries", "purchase_orders": "Purchase orders",
            "labor_workers": "Labour workers", "audit_events": "Audit events"}
    return {"created_at": manifest.get("created_at"), "created_by": manifest.get("created_by"), "app_name": manifest.get("app_name"),
            "revision": manifest.get("alembic_revision"), "needs_upgrade": manifest.get("alembic_revision") != current_head(),
            "highlights": [{"label": label, "count": tables.get(key, 0)} for key, label in keys.items()],
            "tables": len(tables), "rows": sum(tables.values()), "uploads": (manifest.get("uploads") or {}).get("count", 0),
            "upload_bytes": (manifest.get("uploads") or {}).get("bytes", 0)}


def current_head() -> str | None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    return ScriptDirectory.from_config(config).get_current_head()


# ---------------------------------------------------------------- restore

def _extract(zip_path: Path, work: Path, uploads_target: Path) -> Path:
    dump = work / "database.dump"
    if uploads_target.exists():
        shutil.rmtree(uploads_target)
    uploads_target.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as archive:
        for info in archive.infolist():
            if info.is_dir() or info.filename == "manifest.json":
                continue
            destination = dump if info.filename == "database.dump" else uploads_target / info.filename[len("uploads/"):]
            if destination != dump and uploads_target.resolve() not in destination.resolve().parents:
                raise BackupError("Backup contains an unsafe file path")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target, CHUNK_SIZE)
    return dump


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


async def _admin_connection(target: DbTarget) -> asyncpg.Connection:
    for database in ("postgres", "template1"):
        try:
            return await asyncpg.connect(target.dsn(database))
        except (asyncpg.InvalidCatalogNameError, asyncpg.InvalidAuthorizationSpecificationError):
            continue
    raise BackupError("Could not open the PostgreSQL maintenance database (postgres)")


async def _terminate(connection: asyncpg.Connection, database: str) -> None:
    await connection.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = $1 AND pid <> pg_backend_pid()", database)


async def _migrate(target: DbTarget, database: str) -> None:
    env = {**os.environ, "DATABASE_URL": target.sqlalchemy_url(database)}
    process = await asyncio.create_subprocess_exec(sys.executable, "-m", "alembic", "upgrade", "head", cwd=BACKEND_DIR, env=env,
                                                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    _, stderr = await process.communicate()
    if process.returncode:
        lines = (stderr or b"").decode(errors="replace").strip().splitlines()
        raise BackupError(f"Upgrading the restored data failed: {lines[-1] if lines else 'unknown error'}")


@dataclass
class RestoreResult:
    manifest: dict
    restored_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


async def restore_backup(zip_path: Path, manifest: dict, before_swap: Callable[[], object] | None = None, progress: Progress = _noop) -> RestoreResult:
    """Restore a verified backup. ``before_swap`` (async) runs right before the live database is replaced."""
    target = db_target()
    staging = f"{target.database}_restore_tmp"
    previous = f"{target.database}_before_restore"
    work = backup_dir("work") / uuid4().hex
    uploads_new = settings.upload_directory.with_name(settings.upload_directory.name + ".restore-tmp")
    uploads_old = settings.upload_directory.with_name(settings.upload_directory.name + ".before-restore")
    work.mkdir(parents=True)
    admin = await _admin_connection(target)
    swapped = False
    try:
        progress("Unpacking backup")
        dump = await asyncio.to_thread(_extract, zip_path, work, uploads_new)
        progress("Loading data into a staging database")
        await _terminate(admin, staging)
        await admin.execute(f"DROP DATABASE IF EXISTS {_quote(staging)}")
        await admin.execute(f"CREATE DATABASE {_quote(staging)}")
        argv, env, docker = await pg_command("pg_restore", target)
        await _run([*argv, "-d", staging, "--no-owner", "--no-privileges", "--exit-on-error"] + ([] if docker else [str(dump)]),
                   env, stdin_path=dump if docker else None)
        progress("Verifying restored data")
        check = await asyncpg.connect(target.dsn(staging))
        try:
            counts = await _table_counts(check)
        finally:
            await check.close()
        mismatched = [name for name, count in (manifest.get("tables") or {}).items() if counts.get(name) != count]
        if mismatched:
            raise BackupError(f"Restored data check failed for: {', '.join(sorted(mismatched)[:5])}")
        progress("Upgrading restored data to this version")
        await _migrate(target, staging)
        progress("Switching to restored data")
        if before_swap:
            await before_swap()
        await _terminate(admin, target.database)
        await admin.execute(f"DROP DATABASE IF EXISTS {_quote(previous)}")
        await _terminate(admin, target.database)
        await admin.execute(f"ALTER DATABASE {_quote(target.database)} RENAME TO {_quote(previous)}")
        try:
            await admin.execute(f"ALTER DATABASE {_quote(staging)} RENAME TO {_quote(target.database)}")
        except Exception:
            await admin.execute(f"ALTER DATABASE {_quote(previous)} RENAME TO {_quote(target.database)}")
            raise
        swapped = True
        if uploads_old.exists():
            shutil.rmtree(uploads_old)
        if settings.upload_directory.exists():
            settings.upload_directory.rename(uploads_old)
        uploads_new.rename(settings.upload_directory)
        await _terminate(admin, previous)
        await admin.execute(f"DROP DATABASE IF EXISTS {_quote(previous)}")
        shutil.rmtree(uploads_old, ignore_errors=True)
        return RestoreResult(manifest)
    finally:
        if not swapped:
            try:
                await _terminate(admin, staging)
                await admin.execute(f"DROP DATABASE IF EXISTS {_quote(staging)}")
            except Exception:
                pass
            shutil.rmtree(uploads_new, ignore_errors=True)
        await admin.close()
        shutil.rmtree(work, ignore_errors=True)


def cleanup_stale(max_age_hours: int = 24) -> None:
    cutoff = datetime.now().timestamp() - max_age_hours * 3600
    for name in ("work", "downloads", "restore"):
        folder = BACKUP_ROOT / name
        if not folder.exists():
            continue
        for item in folder.iterdir():
            if item.stat().st_mtime < cutoff:
                shutil.rmtree(item, ignore_errors=True) if item.is_dir() else item.unlink(missing_ok=True)

