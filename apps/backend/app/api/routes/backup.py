import asyncio
import json
import secrets
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal, engine, get_db
from app.logging_setup import backend_logger
from app.models import AuditEvent, User
from app.security import backup_grants, require_backup, require_csrf
from app.services import backup as service

router = APIRouter(prefix="/api/v1/backup", tags=["backup"])
ENTITY = "SystemBackup"
maintenance = {"active": False, "message": ""}
operation_lock = asyncio.Lock()
jobs: dict[str, dict] = {}
restore_uploads: dict[str, dict] = {}


# ---------------------------------------------------------------- helpers

async def record_event(action: str, actor_id: UUID | None, details: dict, entity_id: UUID | None = None) -> None:
    async with SessionLocal() as db:
        if actor_id and not await db.scalar(select(User.id).where(User.id == actor_id)):
            actor_id = None
        db.add(AuditEvent(actor_id=actor_id, action=action, entity_type=ENTITY, entity_id=entity_id or uuid4(), details=details))
        await db.commit()


def schedule_path() -> Path:
    return service.backup_dir("") / "schedule.json"


def load_schedule() -> dict:
    defaults = {"enabled": False, "time": "21:00", "passphrase": None, "last_run_at": None, "last_saved_at": None, "last_error": None}
    try:
        return {**defaults, **json.loads(schedule_path().read_text())}
    except (OSError, ValueError):
        return defaults


def save_schedule(data: dict) -> None:
    path = schedule_path()
    path.with_suffix(".tmp").write_text(json.dumps(data, indent=2))
    path.with_suffix(".tmp").replace(path)


def pending_meta() -> dict | None:
    meta_path = service.backup_dir("pending") / "pending.json"
    try:
        meta = json.loads(meta_path.read_text())
    except (OSError, ValueError):
        return None
    return meta if (service.backup_dir("pending") / meta["file"]).exists() else None


def file_size_label(size: int) -> str:
    for unit in ("bytes", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "bytes" else f"{size:.1f} {unit}"
        size /= 1024
    return str(size)


def job_view(job: dict) -> dict:
    return {key: job.get(key) for key in ("id", "kind", "status", "step", "error", "file_name", "file_bytes", "created_at", "finished_at")}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------- status and settings

@router.get("/status")
async def backup_status(user: User = Depends(require_backup("read")), db: AsyncSession = Depends(get_db)) -> dict:
    schedule = load_schedule()
    pending = pending_meta()
    last_saved = schedule.get("last_saved_at")
    stale = bool(schedule["enabled"] and (not last_saved or datetime.fromisoformat(last_saved) < utc_now() - timedelta(days=2)))
    active = next((job_view(job) for job in jobs.values() if job["owner_id"] == str(user.id) and job["kind"] == "backup" and job["status"] in {"running", "ready"}), None)
    restored = (await db.execute(
        select(AuditEvent, User.username)
        .outerjoin(User, User.id == AuditEvent.actor_id)
        .where(AuditEvent.entity_type == ENTITY, AuditEvent.action == "backup_restored")
        .order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
        .limit(1)
    )).first()
    last_restore = None
    if restored:
        event, username = restored
        last_restore = {"performed_at": event.occurred_at.isoformat(), "performed_by": (event.details or {}).get("restored_by") or username or "System"}
    return {
        "can_restore": backup_grants(user)["restore"],
        "schedule": {"enabled": schedule["enabled"], "time": schedule["time"], "passphrase_set": bool(schedule.get("passphrase")),
                     "last_run_at": schedule.get("last_run_at"), "last_error": schedule.get("last_error")},
        "last_saved_at": last_saved,
        "last_restore": last_restore,
        "stale": stale,
        "pending": {k: pending[k] for k in ("id", "file", "created_at", "file_bytes")} if pending else None,
        "active_job": active,
        "busy": operation_lock.locked(),
    }


class ScheduleUpdate(BaseModel):
    enabled: bool
    time: str = Field(default="21:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    passphrase: str | None = Field(default=None, max_length=256)


@router.put("/schedule", dependencies=[Depends(require_csrf)])
async def update_schedule(payload: ScheduleUpdate, user: User = Depends(require_backup("restore"))) -> dict:
    schedule = load_schedule()
    if payload.passphrase:
        try:
            service.validate_passphrase(payload.passphrase)
        except service.BackupError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        schedule["passphrase"] = service.seal_secret(payload.passphrase)
    if payload.enabled and not schedule.get("passphrase"):
        raise HTTPException(status_code=422, detail="Set a passphrase for daily backups")
    changes = {"enabled": payload.enabled, "time": payload.time, "passphrase_changed": bool(payload.passphrase)}
    schedule.update(enabled=payload.enabled, time=payload.time)
    save_schedule(schedule)
    await record_event("backup_schedule_updated", user.id, changes)
    return {"status": "saved"}


# ---------------------------------------------------------------- on-demand backup

class BackupCreate(BaseModel):
    passphrase: str = Field(min_length=service.MIN_PASSPHRASE, max_length=256)


async def run_backup_job(job: dict, passphrase: str, actor: dict) -> None:
    async with operation_lock:
        try:
            path = service.backup_dir("downloads") / job["id"] / job["file_name"]
            manifest = await service.create_backup(path, passphrase, actor["username"], lambda step: job.update(step=step))
            job.update(status="ready", step="Ready to save", path=str(path), file_bytes=manifest["file_bytes"], finished_at=utc_now().isoformat())
            await record_event("backup_created", UUID(actor["id"]), {"file": job["file_name"], "size": file_size_label(manifest["file_bytes"]),
                                                                    "tables": len(manifest["tables"]), "rows": sum(manifest["tables"].values()),
                                                                    "documents": manifest["uploads"]["count"], "type": "Manual"})
        except Exception as error:
            message = str(error) if isinstance(error, service.BackupError) else "Backup failed. See the backend log for details."
            backend_logger.error({"event": "backup_failed", "error_type": type(error).__name__, "error": str(error)[:300]})
            job.update(status="failed", error=message, finished_at=utc_now().isoformat())
            await record_event("backup_failed", UUID(actor["id"]), {"error": message, "type": "Manual"})


@router.post("/jobs", status_code=202, dependencies=[Depends(require_csrf)])
async def start_backup(payload: BackupCreate, user: User = Depends(require_backup("create"))) -> dict:
    if operation_lock.locked():
        raise HTTPException(status_code=409, detail="Another backup or restore is already running. Try again in a moment.")
    for old in [key for key, job in jobs.items() if job["owner_id"] == str(user.id) and job["kind"] == "backup" and job["status"] != "running"]:
        discard_job(old)
    job_id = uuid4().hex
    job = {"id": job_id, "kind": "backup", "status": "running", "step": "Starting", "owner_id": str(user.id),
           "file_name": service.backup_filename(), "created_at": utc_now().isoformat()}
    jobs[job_id] = job
    job["task"] = asyncio.create_task(run_backup_job(job, payload.passphrase, {"id": str(user.id), "username": user.username}))
    return job_view(job)


def owned_job(job_id: str, user: User) -> dict:
    job = jobs.get(job_id)
    if not job or job["owner_id"] != str(user.id) or job["kind"] != "backup":
        raise HTTPException(status_code=404, detail="Backup not found. Create a new backup.")
    return job


def discard_job(job_id: str) -> None:
    job = jobs.pop(job_id, None)
    if job and job.get("path"):
        shutil.rmtree(Path(job["path"]).parent, ignore_errors=True)


@router.get("/jobs/{job_id}")
async def backup_job(job_id: str, user: User = Depends(require_backup("create"))) -> dict:
    return job_view(owned_job(job_id, user))


@router.get("/jobs/{job_id}/download")
async def download_backup(job_id: str, user: User = Depends(require_backup("create"))):
    job = owned_job(job_id, user)
    if job["status"] != "ready" or not Path(job["path"]).exists():
        raise HTTPException(status_code=409, detail="Backup is not ready")
    return FileResponse(job["path"], media_type="application/octet-stream", filename=job["file_name"])


class SavedConfirmation(BaseModel):
    method: Literal["save_dialog", "download"] = "save_dialog"


@router.post("/jobs/{job_id}/saved", dependencies=[Depends(require_csrf)])
async def confirm_backup_saved(job_id: str, payload: SavedConfirmation, user: User = Depends(require_backup("create"))) -> dict:
    job = owned_job(job_id, user)
    if job["status"] != "ready":
        raise HTTPException(status_code=409, detail="Backup is not ready")
    discard_job(job_id)
    mark_saved()
    await record_event("backup_saved", user.id, {"file": job["file_name"], "size": file_size_label(job["file_bytes"]), "type": "Manual",
                                                 "method": "Save dialog" if payload.method == "save_dialog" else "Browser download"})
    return {"status": "saved"}


@router.delete("/jobs/{job_id}", dependencies=[Depends(require_csrf)])
async def discard_backup(job_id: str, user: User = Depends(require_backup("create"))) -> dict:
    owned_job(job_id, user)
    discard_job(job_id)
    return {"status": "discarded"}


def mark_saved() -> None:
    schedule = load_schedule()
    schedule["last_saved_at"] = utc_now().isoformat()
    save_schedule(schedule)


# ---------------------------------------------------------------- scheduled (pending) backup

@router.get("/pending/download")
async def download_pending(user: User = Depends(require_backup("create"))):
    pending = pending_meta()
    if not pending:
        raise HTTPException(status_code=404, detail="No daily backup is waiting to be saved")
    return FileResponse(service.backup_dir("pending") / pending["file"], media_type="application/octet-stream", filename=pending["file"])


@router.post("/pending/saved", dependencies=[Depends(require_csrf)])
async def confirm_pending_saved(payload: SavedConfirmation, user: User = Depends(require_backup("create"))) -> dict:
    pending = pending_meta()
    if not pending:
        raise HTTPException(status_code=404, detail="No daily backup is waiting to be saved")
    clear_pending()
    mark_saved()
    await record_event("backup_saved", user.id, {"file": pending["file"], "size": file_size_label(pending["file_bytes"]), "type": "Daily",
                                                 "method": "Save dialog" if payload.method == "save_dialog" else "Browser download"})
    return {"status": "saved"}


def clear_pending() -> None:
    shutil.rmtree(service.backup_dir("pending"), ignore_errors=True)


def due_time(schedule: dict, now: datetime) -> datetime:
    hour, minute = (int(part) for part in schedule["time"].split(":"))
    today = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return today if now >= today else today - timedelta(days=1)


async def run_scheduled_backup() -> None:
    schedule = load_schedule()
    now = datetime.now().astimezone()
    if not schedule["enabled"] or not schedule.get("passphrase") or maintenance["active"] or operation_lock.locked():
        return
    last_run = datetime.fromisoformat(schedule["last_run_at"]) if schedule.get("last_run_at") else None
    if last_run and last_run >= due_time(schedule, now):
        return
    async with operation_lock:
        name = service.backup_filename(prefix="vridhi-daily-backup")
        staging = service.backup_dir("work") / f"scheduled-{uuid4().hex}.vbak"
        try:
            manifest = await service.create_backup(staging, service.open_secret(schedule["passphrase"]), "Daily schedule")
            clear_pending()
            pending = service.backup_dir("pending")
            staging.replace(pending / name)
            meta = {"id": uuid4().hex, "file": name, "created_at": utc_now().isoformat(), "file_bytes": manifest["file_bytes"]}
            (pending / "pending.json").write_text(json.dumps(meta))
            schedule = load_schedule()
            schedule.update(last_run_at=now.isoformat(), last_error=None)
            save_schedule(schedule)
            await record_event("backup_created", None, {"file": name, "size": file_size_label(manifest["file_bytes"]), "tables": len(manifest["tables"]),
                                                        "rows": sum(manifest["tables"].values()), "documents": manifest["uploads"]["count"], "type": "Daily"})
        except Exception as error:
            staging.unlink(missing_ok=True)
            message = str(error) if isinstance(error, service.BackupError) else "Daily backup failed. See the backend log for details."
            backend_logger.error({"event": "scheduled_backup_failed", "error_type": type(error).__name__, "error": str(error)[:300]})
            schedule = load_schedule()
            schedule.update(last_run_at=now.isoformat(), last_error=message)
            save_schedule(schedule)
            await record_event("backup_failed", None, {"error": message, "type": "Daily"})


async def scheduler_loop() -> None:
    await asyncio.sleep(20)
    while True:
        try:
            service.cleanup_stale()
            await run_scheduled_backup()
        except asyncio.CancelledError:
            raise
        except Exception as error:
            backend_logger.error({"event": "backup_scheduler_error", "error_type": type(error).__name__})
        await asyncio.sleep(60)


# ---------------------------------------------------------------- restore (Global access only)

@router.post("/restore/uploads", dependencies=[Depends(require_csrf)])
async def upload_restore_file(file: UploadFile = File(...), passphrase: str = Form(..., max_length=256), user: User = Depends(require_backup("restore"))) -> dict:
    if operation_lock.locked():
        raise HTTPException(status_code=409, detail="Another backup or restore is already running. Try again in a moment.")
    for key in [key for key, item in restore_uploads.items() if item["owner_id"] == str(user.id)]:
        discard_upload(key)
    upload_id = uuid4().hex
    folder = service.backup_dir("restore") / upload_id
    folder.mkdir(parents=True)
    source = folder / "upload.vbak"
    with source.open("wb") as handle:
        while chunk := await file.read(service.CHUNK_SIZE):
            handle.write(chunk)
    try:
        zip_path, manifest = await asyncio.to_thread(service.open_backup, source, passphrase, folder)
    except service.BackupError as error:
        shutil.rmtree(folder, ignore_errors=True)
        await record_event("backup_restore_rejected", user.id, {"file": file.filename or "backup", "reason": str(error)})
        raise HTTPException(status_code=422, detail=str(error)) from error
    source.unlink(missing_ok=True)
    restore_uploads[upload_id] = {"owner_id": str(user.id), "zip": str(zip_path), "manifest": manifest, "file": file.filename or "backup.vbak",
                                  "passphrase": passphrase, "folder": str(folder)}
    return {"upload_id": upload_id, "file": file.filename, "preview": service.preview(manifest)}


def discard_upload(upload_id: str) -> None:
    item = restore_uploads.pop(upload_id, None)
    if item:
        shutil.rmtree(item["folder"], ignore_errors=True)


@router.delete("/restore/uploads/{upload_id}", dependencies=[Depends(require_csrf)])
async def cancel_restore(upload_id: str, user: User = Depends(require_backup("restore"))) -> dict:
    item = restore_uploads.get(upload_id)
    if not item or item["owner_id"] != str(user.id):
        raise HTTPException(status_code=404, detail="Restore file not found")
    discard_upload(upload_id)
    return {"status": "cancelled"}


class RestoreApply(BaseModel):
    confirm: str


async def run_restore_job(job: dict, item: dict, actor: dict) -> None:
    manifest = item["manifest"]
    summary = {"file": item["file"], "backup_created_at": manifest.get("created_at"), "backup_created_by": manifest.get("created_by")}
    async with operation_lock:
        maintenance.update(active=True, message="System restore in progress. Please wait.")
        try:
            job.update(step="Creating a safety backup of the current data")
            safety_dir = service.backup_dir("safety")
            safety = safety_dir / service.backup_filename(prefix="vridhi-before-restore")
            await service.create_backup(safety, item["passphrase"], actor["username"])
            for old in safety_dir.glob("*.vbak"):
                if old != safety:
                    old.unlink(missing_ok=True)

            async def before_swap():
                await engine.dispose()

            await service.restore_backup(Path(item["zip"]), manifest, before_swap, lambda step: job.update(step=step))
            await engine.dispose()
            async with SessionLocal() as db:
                from sqlalchemy import delete
                from app.models import AuthSession, IdempotencyRecord
                await db.execute(delete(AuthSession))
                await db.execute(delete(IdempotencyRecord))
                await db.commit()
            await record_event("backup_restored", UUID(actor["id"]), {**summary, "restored_by": actor["username"], "safety_backup": safety.name,
                                                                     "rows": sum((manifest.get("tables") or {}).values()),
                                                                     "documents": (manifest.get("uploads") or {}).get("count", 0)})
            job.update(status="done", step="Restore complete", finished_at=utc_now().isoformat())
        except Exception as error:
            message = str(error) if isinstance(error, service.BackupError) else "Restore failed. Your current data was not changed."
            backend_logger.error({"event": "restore_failed", "error_type": type(error).__name__, "error": str(error)[:300]})
            job.update(status="failed", error=message, finished_at=utc_now().isoformat())
            try:
                await engine.dispose()
                await record_event("backup_restore_failed", UUID(actor["id"]), {**summary, "error": message})
            except Exception:
                pass
        finally:
            maintenance.update(active=False, message="")
            shutil.rmtree(item["folder"], ignore_errors=True)


@router.post("/restore/uploads/{upload_id}/apply", status_code=202, dependencies=[Depends(require_csrf)])
async def apply_restore(upload_id: str, payload: RestoreApply, user: User = Depends(require_backup("restore"))) -> dict:
    item = restore_uploads.get(upload_id)
    if not item or item["owner_id"] != str(user.id):
        raise HTTPException(status_code=404, detail="Restore file not found. Upload it again.")
    if payload.confirm != "RESTORE":
        raise HTTPException(status_code=422, detail="Type RESTORE to confirm")
    if operation_lock.locked():
        raise HTTPException(status_code=409, detail="Another backup or restore is already running. Try again in a moment.")
    restore_uploads.pop(upload_id)
    job_id, token = uuid4().hex, secrets.token_urlsafe(24)
    job = {"id": job_id, "kind": "restore", "status": "running", "step": "Starting", "owner_id": str(user.id), "token": token,
           "file_name": item["file"], "created_at": utc_now().isoformat()}
    jobs[job_id] = job
    job["task"] = asyncio.create_task(run_restore_job(job, item, {"id": str(user.id), "username": user.username}))
    return {**job_view(job), "token": token}


@router.get("/restore-jobs/{job_id}")
async def restore_job_status(job_id: str, token: str) -> dict:
    job = jobs.get(job_id)
    if not job or job["kind"] != "restore" or not secrets.compare_digest(job["token"], token):
        raise HTTPException(status_code=404, detail="Restore job not found")
    return job_view(job)
