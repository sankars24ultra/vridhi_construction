#!/usr/bin/env python3
"""Create or restore a full Vridhi backup (.vbak) from the command line.

  python3 scripts/backup.py create [--out FILE]
  python3 scripts/backup.py restore FILE

Restore requires the app to be stopped (close the launcher first).
"""
import argparse
import asyncio
import getpass
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "backend"
VENV_PYTHON = BACKEND / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def ensure_backend_python():
    if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve() and not os.environ.get("VRIDHI_BACKUP_CHILD"):
        os.environ["VRIDHI_BACKUP_CHILD"] = "1"
        os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), *sys.argv])
    sys.path.insert(0, str(BACKEND))
    os.chdir(BACKEND)


def api_running() -> bool:
    state = ROOT / ".run" / "api.json"
    try:
        pid = int(json.loads(state.read_text())["pid"])
        os.kill(pid, 0)
        return True
    except (OSError, ValueError, KeyError):
        return False


def ask_passphrase(confirm: bool) -> str:
    passphrase = getpass.getpass("Backup passphrase: ")
    if confirm and getpass.getpass("Confirm passphrase: ") != passphrase:
        sys.exit("Passphrases do not match.")
    return passphrase


async def create(out: Path) -> None:
    from app.services import backup as service
    passphrase = ask_passphrase(confirm=True)
    service.validate_passphrase(passphrase)
    manifest = await service.create_backup(out, passphrase, getpass.getuser(), lambda step: print(f"  {step}..."))
    print(f"Backup saved: {out} ({manifest['file_bytes'] / 1024 / 1024:.1f} MB, {sum(manifest['tables'].values())} rows, "
          f"{manifest['uploads']['count']} documents). Copy it to Google Drive or another safe place.")


async def restore(path: Path) -> None:
    from app.services import backup as service
    if api_running():
        sys.exit("Stop the Vridhi app first (close the launcher), then run restore again.")
    passphrase = ask_passphrase(confirm=False)
    with tempfile.TemporaryDirectory(dir=service.backup_dir("work")) as work:
        zip_path, manifest = service.open_backup(path, passphrase, Path(work))
        info = service.preview(manifest)
        print(f"Backup from {info['created_at']} by {info['created_by']}: {info['rows']} rows, {info['uploads']} documents.")
        for item in info["highlights"]:
            print(f"  {item['label']}: {item['count']}")
        if input("This replaces ALL current data. Type RESTORE to continue: ").strip() != "RESTORE":
            sys.exit("Restore cancelled. Nothing was changed.")
        safety = service.backup_dir("safety") / service.backup_filename(prefix="vridhi-before-restore")
        print("  Creating a safety backup of the current data...")
        await service.create_backup(safety, passphrase, getpass.getuser())
        for old in safety.parent.glob("*.vbak"):
            if old != safety:
                old.unlink(missing_ok=True)
        await service.restore_backup(zip_path, manifest, progress=lambda step: print(f"  {step}..."))
        import asyncpg
        connection = await asyncpg.connect(service.db_target().dsn())
        try:
            await connection.execute("DELETE FROM auth_sessions; DELETE FROM idempotency_records")
            await connection.execute(
                "INSERT INTO audit_events (id, action, entity_type, entity_id, details, occurred_at) VALUES (gen_random_uuid(), 'backup_restored', 'SystemBackup', gen_random_uuid(), $1::json, now())",
                json.dumps({"file": path.name, "backup_created_at": manifest.get("created_at"), "backup_created_by": manifest.get("created_by"),
                            "restored_by": f"{getpass.getuser()} (command line)", "safety_backup": safety.name}))
        finally:
            await connection.close()
    print(f"Restore complete. Safety copy of the previous data: {safety}. Start the app and sign in again.")


def main():
    parser = argparse.ArgumentParser(description="Vridhi full-system backup and restore")
    commands = parser.add_subparsers(dest="command", required=True)
    create_parser = commands.add_parser("create", help="Create an encrypted backup file")
    create_parser.add_argument("--out", type=Path, help="Where to save the .vbak file (default: current folder)")
    restore_parser = commands.add_parser("restore", help="Restore all data from a .vbak file")
    restore_parser.add_argument("file", type=Path)
    args = parser.parse_args()
    cwd = Path.cwd()
    ensure_backend_python()
    from app.services.backup import BackupError, backup_filename
    try:
        if args.command == "create":
            out = args.out if args.out else Path(backup_filename())
            asyncio.run(create((out if out.is_absolute() else cwd / out).resolve()))
        else:
            source = args.file if args.file.is_absolute() else cwd / args.file
            asyncio.run(restore(source.resolve()))
    except BackupError as error:
        sys.exit(f"Error: {error}")


if __name__ == "__main__":
    main()
