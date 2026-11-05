import asyncio
import hashlib
import json
import os
import subprocess
import zipfile
from pathlib import Path

import pytest

from app.services import backup as service


def test_encrypt_round_trip_and_wrong_passphrase(tmp_path):
    source = tmp_path / "plain.bin"
    source.write_bytes(os.urandom(service.CHUNK_SIZE * 2 + 123))
    sealed, opened = tmp_path / "sealed.vbak", tmp_path / "opened.bin"
    service.encrypt_file(source, sealed, "correct horse")
    service.decrypt_file(sealed, opened, "correct horse")
    assert opened.read_bytes() == source.read_bytes()
    with pytest.raises(service.BackupError, match="Wrong passphrase"):
        service.decrypt_file(sealed, opened, "wrong passphrase")


def test_empty_file_round_trip(tmp_path):
    source = tmp_path / "empty"
    source.write_bytes(b"")
    service.encrypt_file(source, tmp_path / "s", "passphrase")
    service.decrypt_file(tmp_path / "s", tmp_path / "o", "passphrase")
    assert (tmp_path / "o").read_bytes() == b""


@pytest.mark.parametrize("damage", ["truncate", "flip", "extra", "not_backup"])
def test_damaged_files_are_rejected(tmp_path, damage):
    source = tmp_path / "plain.bin"
    source.write_bytes(os.urandom(service.CHUNK_SIZE + 10))
    sealed = tmp_path / "sealed.vbak"
    service.encrypt_file(source, sealed, "passphrase")
    data = bytearray(sealed.read_bytes())
    if damage == "truncate":
        data = data[: -service.CHUNK_SIZE // 2]
    elif damage == "flip":
        data[-5] ^= 0xFF
    elif damage == "extra":
        data += b"junk"
    else:
        data[:4] = b"PK\x03\x04"
    sealed.write_bytes(bytes(data))
    with pytest.raises(service.BackupError):
        service.decrypt_file(sealed, tmp_path / "out", "passphrase")


def make_archive(path: Path, revision: str, files: dict[str, bytes], manifest_files: dict | None = None, **extra) -> None:
    hashes = {name: hashlib.sha256(content).hexdigest() for name, content in files.items()}
    manifest = {"format": service.FORMAT_NAME, "format_version": 1, "alembic_revision": revision, "tables": {"users": 1},
                "files": manifest_files if manifest_files is not None else hashes, **extra}
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        for name, content in files.items():
            archive.writestr(name, content)


def test_archive_validation(tmp_path):
    head = service.current_head()
    good = tmp_path / "good.zip"
    make_archive(good, head, {"database.dump": b"dump", "uploads/a.pdf": b"pdf"})
    assert service._validate_archive(good)["alembic_revision"] == head

    newer = tmp_path / "newer.zip"
    make_archive(newer, "9999_future", {"database.dump": b"dump"})
    with pytest.raises(service.BackupError, match="newer version"):
        service._validate_archive(newer)

    tampered = tmp_path / "tampered.zip"
    make_archive(tampered, head, {"database.dump": b"dump"}, manifest_files={"database.dump": "0" * 64})
    with pytest.raises(service.BackupError, match="check failed"):
        service._validate_archive(tampered)

    unsafe = tmp_path / "unsafe.zip"
    make_archive(unsafe, head, {"database.dump": b"dump", "uploads/../../evil.sh": b"x"})
    with pytest.raises(service.BackupError, match="unsafe"):
        service._validate_archive(unsafe)

    missing = tmp_path / "missing.zip"
    make_archive(missing, head, {"database.dump": b"dump"}, manifest_files={"database.dump": hashlib.sha256(b"dump").hexdigest(), "uploads/x": "0"})
    with pytest.raises(service.BackupError, match="do not match"):
        service._validate_archive(missing)


def test_passphrase_minimum():
    with pytest.raises(service.BackupError):
        service.validate_passphrase("short")


def test_backup_and_restore_permissions():
    from types import SimpleNamespace
    from app.security import backup_grants
    assert backup_grants(SimpleNamespace(global_access=True, backup_permissions=None)) == {"read": True, "create": True, "restore": True}
    assert backup_grants(SimpleNamespace(global_access=False, backup_permissions={"access": "allow"})) == {"read": True, "create": True, "restore": False}
    assert backup_grants(SimpleNamespace(global_access=False, backup_permissions=None)) == {"read": False, "create": False, "restore": False}


@pytest.mark.parametrize("actor,details,expected", [
    ("current.username", {"restored_by": "original.username"}, "original.username"),
    (None, {"restored_by": "operator (command line)"}, "operator (command line)"),
    ("current.username", None, "current.username"),
    (None, None, "System"),
])
def test_status_last_restore(actor, details, expected):
    from datetime import datetime, timezone
    from unittest.mock import AsyncMock, MagicMock, patch
    from uuid import uuid4
    from app.api.routes.backup import backup_status
    from app.models import AuditEvent, User

    performed_at = datetime(2026, 10, 31, 21, 17, tzinfo=timezone.utc)
    event = AuditEvent(occurred_at=performed_at, details=details)
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(first=MagicMock(return_value=(event, actor))))
    with patch("app.api.routes.backup.load_schedule", return_value={"enabled": False, "time": "21:00"}), patch("app.api.routes.backup.pending_meta", return_value=None):
        status = asyncio.run(backup_status(User(id=uuid4(), global_access=True), db))
    assert status["last_restore"] == {"performed_at": performed_at.isoformat(), "performed_by": expected}
    query = str(db.execute.call_args.args[0])
    assert "ORDER BY audit_events.occurred_at DESC" in query


def test_status_without_restore():
    from unittest.mock import AsyncMock, MagicMock, patch
    from uuid import uuid4
    from app.api.routes.backup import backup_status
    from app.models import User

    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(first=MagicMock(return_value=None)))
    with patch("app.api.routes.backup.load_schedule", return_value={"enabled": False, "time": "21:00"}), patch("app.api.routes.backup.pending_meta", return_value=None):
        status = asyncio.run(backup_status(User(id=uuid4(), global_access=True), db))
    assert status["last_restore"] is None


def test_schedule_due_time():
    from datetime import datetime
    from app.api.routes.backup import due_time
    schedule = {"time": "21:00"}
    assert due_time(schedule, datetime(2026, 5, 2, 9, 0)) == datetime(2026, 5, 1, 21, 0)
    assert due_time(schedule, datetime(2026, 5, 2, 21, 30)) == datetime(2026, 5, 2, 21, 0)


@pytest.mark.skipif(os.environ.get("VRIDHI_TEST_POSTGRES") != "1", reason="PostgreSQL round-trip requires opt-in")
def test_full_round_trip_on_cloned_database(tmp_path, monkeypatch):
    import asyncpg
    from sqlalchemy.engine import make_url
    from app.core.config import settings

    source = service.db_target()
    test_db = "vridhi_backup_roundtrip_test"
    test_url = make_url(settings.database_url).set(database=test_db).render_as_string(hide_password=False)
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    (uploads / "plan.pdf").write_bytes(b"%PDF original")
    monkeypatch.setattr(settings, "database_url", test_url)
    monkeypatch.setattr(settings, "upload_directory", uploads)
    monkeypatch.setattr(service, "BACKUP_ROOT", tmp_path / "backups")

    async def scenario():
        admin = await service._admin_connection(source)
        try:
            for name in (test_db, f"{test_db}_restore_tmp", f"{test_db}_before_restore"):
                await service._terminate(admin, name)
                await admin.execute(f'DROP DATABASE IF EXISTS "{name}"')
            await admin.execute(f'CREATE DATABASE "{test_db}"')
        finally:
            await admin.close()
        dump_argv, env, _ = await service.pg_command("pg_dump", source)
        restore_argv, _, _ = await service.pg_command("pg_restore", source)
        clone = tmp_path / "clone.dump"
        await service._run([*dump_argv, "-d", source.database, "-Fc", "--no-owner", "--no-privileges"], env, stdout_path=clone)
        await service._run([*restore_argv, "-d", test_db, "--no-owner", "--no-privileges", str(clone)], env)

        target = tmp_path / "out.vbak"
        manifest = await service.create_backup(target, "round-trip-pass", "tester")
        assert manifest["uploads"]["count"] == 1 and manifest["tables"]["users"] >= 1

        connection = await asyncpg.connect(service.db_target().dsn())
        try:
            before = await connection.fetchval("SELECT count(*) FROM audit_events")
            await connection.execute("DELETE FROM audit_events")
        finally:
            await connection.close()
        (uploads / "plan.pdf").write_bytes(b"changed")
        (uploads / "extra.jpg").write_bytes(b"new file")

        zip_path, opened = service.open_backup(target, "round-trip-pass", tmp_path / "open")
        await service.restore_backup(zip_path, opened)

        connection = await asyncpg.connect(service.db_target().dsn())
        try:
            assert await connection.fetchval("SELECT count(*) FROM audit_events") == before
            assert await connection.fetchval("SELECT version_num FROM alembic_version") == service.current_head()
        finally:
            await connection.close()
        assert (uploads / "plan.pdf").read_bytes() == b"%PDF original"
        assert not (uploads / "extra.jpg").exists()

        admin = await service._admin_connection(source)
        try:
            names = {row["datname"] for row in await admin.fetch("SELECT datname FROM pg_database")}
            assert f"{test_db}_restore_tmp" not in names and f"{test_db}_before_restore" not in names
            await service._terminate(admin, test_db)
            await admin.execute(f'DROP DATABASE IF EXISTS "{test_db}"')
        finally:
            await admin.close()

    asyncio.run(scenario())
