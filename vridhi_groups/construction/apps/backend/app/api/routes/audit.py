import csv
import io
import json
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import AuditEvent, Project, User
from app.security import current_user, require_csrf, require_permission, require_project_access
from app.services.common import add_audit

router = APIRouter()
MODULES = {"overview": "Overview", "procurement": "Procurement", "inventory": "Inventory", "cashflow": "Cash flow", "labor": "Labor and Wages", "audit": "Audit Log"}


class ActivityCreate(BaseModel):
    module: Literal["overview", "procurement", "inventory", "cashflow", "labor", "audit"]
    activity: Literal["visit", "export"]


@router.post("/api/v1/projects/{project_id}/activities", status_code=204, dependencies=[Depends(require_csrf)])
async def record_activity(payload: ActivityCreate, request: Request, project: Project = Depends(require_project_access), user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> Response:
    await require_permission(payload.module, "read")(request, user, db)
    if payload.activity == "export":
        from app.models import ProjectMembership

        membership = await db.scalar(select(ProjectMembership).where(ProjectMembership.project_id == project.id, ProjectMembership.user_id == user.id))
        permission = (user.global_permissions or {}).get(payload.module, {}) if user.global_access else {}
        if membership and membership.permissions and payload.module in membership.permissions:
            permission = membership.permissions[payload.module]
        if payload.module == "audit":
            permission = {"read": {"export_report": True}} if user.global_access else user.audit_permissions or {}
        if not permission.get("read", {}).get("export_report", False):
            raise HTTPException(status_code=403, detail="Export Report permission is required")
    await add_audit(db, user, f"{payload.activity}_{payload.module}", "Project", project.id, {"module": MODULES[payload.module], "activity": payload.activity, "request_id": getattr(request.state, "request_id", None), "export_status": "requested" if payload.activity == "export" else None}, project_id=project.id)
    await db.commit()
    return Response(status_code=204)


def activity_label(action: str) -> str:
    for module, label in MODULES.items():
        if action == f"visit_{module}":
            return f"Visited {label}"
        if action == f"export_{module}":
            return f"Exported report from {label} (export requested)"
    return action.replace("_", " ").capitalize()


def csv_cell(value: str) -> str:
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value


@router.get("/api/v1/projects/{project_id}/audit-log", dependencies=[Depends(require_permission("audit", "read"))])
async def project_audit_log(project: Project = Depends(require_project_access), page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100), search: str = Query("", max_length=200), export: int = Query(0, ge=0, le=1), db: AsyncSession = Depends(get_db), start_time: datetime | None = None, end_time: datetime | None = None):
    if page_size not in {10, 20, 50, 100}:
        raise HTTPException(status_code=422, detail="Page size must be 10, 20, 50, or 100")
    filters = [AuditEvent.project_id == project.id]
    if any(value is not None and value.utcoffset() is None for value in (start_time, end_time)):
        raise HTTPException(status_code=422, detail="Date and time filters must include a timezone")
    if start_time and end_time and start_time > end_time:
        raise HTTPException(status_code=422, detail="From date and time must be before To date and time")
    if start_time:
        filters.append(AuditEvent.occurred_at >= start_time.astimezone(timezone.utc))
    if end_time:
        filters.append(AuditEvent.occurred_at <= end_time.astimezone(timezone.utc))
    if search.strip():
        term = f"%{search.strip()}%"
        activity_term = search.strip().lower().replace("visited ", "visit_").replace("exported report from ", "export_").replace(" ", "_")
        filters.append(or_(AuditEvent.action.ilike(term), AuditEvent.action.ilike(f"%{activity_term}%"), User.username.ilike(term), User.name.ilike(term), AuditEvent.entity_type.ilike(term), cast(AuditEvent.details, String).ilike(term)))
    query = select(AuditEvent, User.username, User.name).outerjoin(User, User.id == AuditEvent.actor_id).where(*filters).order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
    if not export:
        query = query.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(query)).all()
    items = [{"id": str(event.id), "username": username or "System", "name": name or "System", "occurred_at": event.occurred_at.isoformat(), "activity": activity_label(event.action), "action": event.action, "record_type": event.entity_type, "record_id": str(event.entity_id) if event.entity_id else None, "details": event.details} for event, username, name in rows]
    if export:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Project", "Username", "Full name", "Date and time (ISO timezone)", "Activity", "Record type", "Record ID", "Audit ID", "Details"])
        for item in items:
            writer.writerow([csv_cell(str(value or "")) for value in [project.name, item["username"], item["name"], item["occurred_at"], item["activity"], item["record_type"], item["record_id"], item["id"], json.dumps(item["details"], ensure_ascii=True) if item["details"] else ""]])
        return Response(content="\ufeff" + output.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="project-{project.id}-audit-log.csv"'})
    total = await db.scalar(select(func.count(AuditEvent.id)).outerjoin(User, User.id == AuditEvent.actor_id).where(*filters)) or 0
    return {"items": items, "page": page, "page_size": page_size, "total": total}