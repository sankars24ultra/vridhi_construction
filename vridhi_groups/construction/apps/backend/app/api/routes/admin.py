from decimal import Decimal
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, or_, select, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models import AuditEvent, AuthSession, Contract, Project, ProjectMembership, User
from pydantic import BaseModel, Field, StrictBool
from app.schemas import UserCreate, UserUpdate
from app.security import current_user, hash_password, require_csrf, require_permission, users_permission_profile
from app.services.common import add_audit, money, project_dto, user_dto

router = APIRouter()


def user_history_snapshot(user: User, memberships: list | None = None) -> dict:
    return {"username": user.username, "name": user.name, "email": user.email, "phone": user.phone, "active": user.active, "global_access": user.global_access, "global_permissions": user.global_permissions, "users_permissions": user.users_permissions, "audit_permissions": user.audit_permissions, "project_permissions": {str(link.project_id): link.permissions for link in memberships or []}}


@router.get("/api/v1/users/{user_id}/history")
async def user_history(user_id: UUID, page: int = Query(1, ge=1), page_size: int = Query(5, ge=1, le=50), search: str = Query("", max_length=200), user: User = Depends(require_permission("users", "read")), db: AsyncSession = Depends(get_db)) -> dict:
    if page_size not in {5, 10, 20, 50}:
        raise HTTPException(status_code=422, detail="Page size must be 5, 10, 20, or 50")
    filters = [or_((AuditEvent.entity_type == "User") & (AuditEvent.entity_id == user_id), AuditEvent.actor_id == user_id), ~AuditEvent.action.ilike("login%")]
    if search.strip():
        term = f"%{search.strip()}%"
        filters.append(or_(AuditEvent.action.ilike(term), AuditEvent.entity_type.ilike(term), User.name.ilike(term), User.username.ilike(term), cast(AuditEvent.details, String).ilike(term)))
    query = select(AuditEvent, User.name, User.username).outerjoin(User, User.id == AuditEvent.actor_id).where(*filters)
    rows = (await db.execute(query.order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    total = await db.scalar(select(func.count(AuditEvent.id)).outerjoin(User, User.id == AuditEvent.actor_id).where(*filters)) or 0
    return {"items": [{"id": str(event.id), "action": event.action, "entity_type": event.entity_type, "entity_id": str(event.entity_id) if event.entity_id else None, "occurred_at": event.occurred_at.isoformat(), "actor": name or username or "System", "details": event.details} for event, name, username in rows], "page": page, "page_size": page_size, "total": total}


class PasswordReset(BaseModel):
    password: str = Field(min_length=6, max_length=128)


class UserStatusUpdate(BaseModel):
    active: StrictBool


async def managed_user(user_id: UUID, actor: User, db: AsyncSession) -> User:
    if user_id == actor.id:
        raise HTTPException(status_code=422, detail="You cannot perform this action on your own account")
    target = await db.scalar(select(User).where(User.id == user_id, User.deleted_at.is_(None)).with_for_update())
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    return target


async def revoke_user_sessions(user_id: UUID, db: AsyncSession) -> None:
    from sqlalchemy import update

    await db.execute(update(AuthSession).where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None)).values(revoked_at=datetime.now(timezone.utc)))


@router.post("/api/v1/users/{user_id}/reset-password", dependencies=[Depends(require_csrf), Depends(require_permission("users", "write"))])
async def reset_user_password(user_id: UUID, payload: PasswordReset, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    target = await managed_user(user_id, user, db)
    target.password_hash = hash_password(payload.password)
    await revoke_user_sessions(target.id, db)
    await add_audit(db, user, "user_password_reset", "User", target.id)
    await db.commit()
    return {"status": "password_reset"}


@router.patch("/api/v1/users/{user_id}/status", dependencies=[Depends(require_csrf), Depends(require_permission("users", "write"))])
async def change_user_status(user_id: UUID, payload: UserStatusUpdate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    target = await managed_user(user_id, user, db)
    previous_active = target.active
    target.active = payload.active
    if not target.active:
        await revoke_user_sessions(target.id, db)
    await add_audit(db, user, "user_activated" if target.active else "user_deactivated", "User", target.id, {"before": {"active": previous_active}, "after": {"active": target.active}})
    await db.commit()
    return {"active": target.active}


@router.delete("/api/v1/users/{user_id}", dependencies=[Depends(require_csrf), Depends(require_permission("users", "write"))])
async def delete_user(user_id: UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    target = await managed_user(user_id, user, db)
    target.active = False
    target.deleted_at = datetime.now(timezone.utc)
    await revoke_user_sessions(target.id, db)
    await add_audit(db, user, "user_deleted", "User", target.id, {"username": target.username, "history_retained": True})
    await db.commit()
    return {"status": "deleted"}


@router.post("/api/v1/users", dependencies=[Depends(require_csrf), Depends(require_permission("users", "write"))], status_code=201)
async def create_user(payload: UserCreate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    username = payload.username.strip()
    email = payload.email.strip() if payload.email else None
    if await db.scalar(select(User.id).where(func.lower(User.username) == username.lower())):
        raise HTTPException(status_code=409, detail="Username is already in use")
    if email and await db.scalar(select(User.id).where(func.lower(User.email) == email.lower())):
        raise HTTPException(status_code=409, detail="Email is already in use")

    project_ids = set(payload.project_ids)
    if payload.global_access and not payload.global_permissions:
        raise HTTPException(status_code=422, detail="Set a permission profile for global access")
    if set(payload.project_permissions) - project_ids:
        raise HTTPException(status_code=422, detail="Permission settings must match assigned projects")
    if not project_ids and not payload.global_access and not (payload.users_permissions and payload.users_permissions.access == "allow"):
        raise HTTPException(status_code=422, detail="Assign at least one project to this user")
    if set(payload.project_permissions) != project_ids:
        raise HTTPException(status_code=422, detail="Set permissions for every assigned project")
    if project_ids:
        projects = list((await db.scalars(select(Project).where(Project.id.in_(project_ids)))).all())
        if len(projects) != len(project_ids):
            raise HTTPException(status_code=422, detail="One or more selected projects do not exist")
        rows = list((await db.scalars(select(ProjectMembership).where(ProjectMembership.user_id == user.id, ProjectMembership.project_id.in_(project_ids)))).all())
        actor_memberships = {row.project_id: row for row in rows}
        if not user.global_access and not project_ids.issubset(set(actor_memberships)):
            raise HTTPException(status_code=403, detail="You can only assign users to projects you can access")
    created_user = User(
        username=username,
        email=email,
        phone=payload.phone.strip() if payload.phone else None,
        name=payload.name.strip(),
        password_hash=hash_password(payload.password),
        role="User",
        global_access=payload.global_access,
        global_permissions=payload.global_permissions.model_dump() if payload.global_permissions else None,
        users_permissions=payload.users_permissions.model_dump() if payload.users_permissions else None,
        audit_permissions=payload.audit_permissions.model_dump() if payload.audit_permissions else None,
        active=True,
        memberships=[ProjectMembership(project_id=project_id, permissions=payload.project_permissions.get(project_id).model_dump() if project_id in payload.project_permissions else None) for project_id in project_ids],
    )
    db.add(created_user)
    try:
        await db.flush()
        await add_audit(db, user, "user_created", "User", created_user.id, {"after": user_history_snapshot(created_user, created_user.memberships)})
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return {**user_dto(created_user), "active": created_user.active, "assigned_project_ids": [str(project_id) for project_id in project_ids]}


@router.put("/api/v1/users/{user_id}", dependencies=[Depends(require_csrf), Depends(require_permission("users", "write"))])
async def update_user(user_id: UUID, payload: UserUpdate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    target = await db.scalar(select(User).options(selectinload(User.memberships)).where(User.id == user_id, User.deleted_at.is_(None)).with_for_update())
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == user.id:
        raise HTTPException(status_code=422, detail="You cannot edit your own account here")
    if payload.username.strip() != target.username:
        raise HTTPException(status_code=422, detail="Username cannot be changed after the account is created")
    before = user_history_snapshot(target, list(target.memberships))
    if payload.password and not (await users_permission_profile(user, db))["write"]["actions"]["reset_password"]:
        raise HTTPException(status_code=403, detail="Reset Password permission is required")
    username = payload.username.strip()
    email = payload.email.strip() if payload.email else None
    if await db.scalar(select(User.id).where(func.lower(User.username) == username.lower(), User.id != target.id)):
        raise HTTPException(status_code=409, detail="Username is already in use")
    if email and await db.scalar(select(User.id).where(func.lower(User.email) == email.lower(), User.id != target.id)):
        raise HTTPException(status_code=409, detail="Email is already in use")
    project_ids = set(payload.project_ids)
    if payload.global_access and not payload.global_permissions:
        raise HTTPException(status_code=422, detail="Set a permission profile for global access")
    if set(payload.project_permissions) - project_ids:
        raise HTTPException(status_code=422, detail="Permission settings must match assigned projects")
    if not project_ids and not payload.global_access and not (payload.users_permissions and payload.users_permissions.access == "allow"):
        raise HTTPException(status_code=422, detail="Assign at least one project to this user")
    if set(payload.project_permissions) != project_ids:
        raise HTTPException(status_code=422, detail="Set permissions for every assigned project")
    projects = list((await db.scalars(select(Project).where(Project.id.in_(project_ids)))).all()) if project_ids else []
    if len(projects) != len(project_ids):
        raise HTTPException(status_code=422, detail="One or more selected projects do not exist")
    if project_ids:
        actor_rows = list((await db.scalars(select(ProjectMembership).where(ProjectMembership.user_id == user.id, ProjectMembership.project_id.in_(project_ids)))).all())
        actor_memberships = {row.project_id: row for row in actor_rows}
        managed_ids = set(actor_memberships)
        if not user.global_access and not project_ids.issubset(managed_ids):
            raise HTTPException(status_code=403, detail="You can only assign users to projects you can access")
    target.name = payload.name.strip()
    target.username = username
    target.email = email
    target.phone = payload.phone.strip() if payload.phone else None
    target.global_access = payload.global_access
    target.global_permissions = payload.global_permissions.model_dump() if payload.global_permissions else None
    target.users_permissions = payload.users_permissions.model_dump() if payload.users_permissions else None
    target.audit_permissions = payload.audit_permissions.model_dump() if payload.audit_permissions else None
    if payload.password:
        target.password_hash = hash_password(payload.password)
        await revoke_user_sessions(target.id, db)
        await add_audit(db, user, "user_password_reset", "User", target.id)
    await db.execute(delete(ProjectMembership).where(ProjectMembership.user_id == target.id))
    if project_ids:
        db.add_all([ProjectMembership(user_id=target.id, project_id=assigned_project_id, permissions=payload.project_permissions[assigned_project_id].model_dump()) for assigned_project_id in project_ids])
    try:
        after = user_history_snapshot(target)
        after["project_permissions"] = {str(assigned_id): payload.project_permissions[assigned_id].model_dump() for assigned_id in project_ids}
        await add_audit(db, user, "user_updated", "User", target.id, {"before": before, "after": after})
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return {**user_dto(target), "active": target.active, "assigned_project_ids": [str(project_id) for project_id in project_ids]}


@router.get("/api/v1/users")
async def list_users(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), user: User = Depends(require_permission("users", "read")), db: AsyncSession = Depends(get_db)) -> dict:
    items = list((await db.scalars(select(User).options(selectinload(User.memberships).selectinload(ProjectMembership.project)).where(User.deleted_at.is_(None)).order_by(User.name).offset((page - 1) * page_size).limit(page_size))).all())
    total = await db.scalar(select(func.count(User.id)).where(User.deleted_at.is_(None))) or 0
    return {"items": [{**user_dto(item), "active": item.active, "version": item.version, "email_verified": bool(item.email), "assigned_project_ids": [str(link.project_id) for link in item.memberships], "assigned_projects": [link.project.name for link in item.memberships], "project_permissions": {str(link.project_id): link.permissions for link in item.memberships}, "manageable_actions": []} for item in items], "page": page, "page_size": page_size, "total": total}


@router.get("/api/v1/reports/portfolio")
async def portfolio_report(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    query = select(Project).order_by(Project.name)
    if not user.global_access:
        query = query.join(ProjectMembership).where(ProjectMembership.user_id == user.id)
    projects = list((await db.scalars(query)).unique().all())
    counts = {name: sum(project.status == name for project in projects) for name in ["Planning", "Active", "On Hold", "Completed"]}
    by_currency: dict[str, dict[str, Decimal]] = {}
    for project in projects:
        totals = by_currency.setdefault(project.currency, {"budget": Decimal("0"), "approved_contract_value": Decimal("0")})
        totals["budget"] += project.baseline_budget
        contract = await db.scalar(select(Contract).where(Contract.project_id == project.id))
        if contract:
            totals["approved_contract_value"] += contract.original_value
    return {"as_of": datetime.now(timezone.utc).isoformat(), "project_count": len(projects), "counts_by_status": counts, "totals_by_currency": [{"currency": currency_code, **{key: money(value) for key, value in values.items()}} for currency_code, values in by_currency.items()]}
