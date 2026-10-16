import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from fastapi import Cookie, Depends, Header, HTTPException, Request, Response, status
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db import get_db
from app.models import AuthSession, User

password_hasher = PasswordHasher()
csrf_signer = URLSafeTimedSerializer(settings.session_secret, salt="vridhi-csrf-v1")
RBAC_RESOURCES = ("overview", "procurement", "inventory", "cashflow", "users")
USERS_ACTIONS = ("add_user", "reset_password", "activate_deactivate", "delete_user", "history")


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except Exception:
        return False


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def user_permission_matrix(user: User, db: AsyncSession) -> dict[str, dict[str, bool]]:
    matrix = {resource: {"read": False, "write": False} for resource in (*RBAC_RESOURCES, "labor")}
    users = await users_permission_profile(user, db)
    matrix["users"] = {"read": users["access"] == "allow", "write": users["write"]["actions"]["add_user"], "export_report": users["read"]["export_report"], **users["write"]["actions"]}
    audit = getattr(user, "audit_permissions", None) or {}
    matrix["audit"] = {"read": bool(user.global_access or audit.get("access") == "allow"), "write": False, "export_report": bool(user.global_access or audit.get("access") == "allow" and audit.get("read", {}).get("export_report", False))}
    return matrix


async def users_permission_profile(user: User, db: AsyncSession) -> dict:
    from app.models import ProjectMembership

    if user.global_access:
        return {"access": "allow", "read": {"export_report": True}, "write": {"mode": "partial", "actions": {action: True for action in USERS_ACTIONS}}}
    account_profile = getattr(user, "users_permissions", None)
    if account_profile is not None:
        allowed = account_profile.get("access") == "allow"
        write = account_profile.get("write", {})
        return {"access": "allow" if allowed else "block", "read": {"export_report": allowed and account_profile.get("read", {}).get("export_report", False)}, "write": {"mode": "partial", "actions": {action: allowed and (write.get("mode") == "all" or write.get("actions", {}).get(action, False)) for action in USERS_ACTIONS}}}
    global_profile = (user.global_permissions or {}).get("users") if user.global_access else None
    profiles = [global_profile] if global_profile else []
    memberships = (await db.scalars(select(ProjectMembership).where(ProjectMembership.user_id == user.id))).all()
    profiles.extend((link.permissions or {}).get("users", {}) for link in memberships)
    permitted = [profile for profile in profiles if profile.get("access") == "allow"]
    return {
        "access": "allow" if permitted else "block",
        "read": {"export_report": any(profile.get("read", {}).get("export_report", False) for profile in permitted)},
        "write": {"mode": "partial", "actions": {action: any(profile.get("write", {}).get("mode") == "all" or profile.get("write", {}).get("actions", {}).get(action, False) for profile in permitted) for action in USERS_ACTIONS}},
    }


def issue_csrf(response: Response) -> str:
    value = csrf_signer.dumps(secrets.token_urlsafe(24))
    response.set_cookie("vridhi_csrf", value, httponly=False, secure=settings.cookie_secure, samesite="lax", path="/")
    return value


async def require_csrf(
    request: Request,
    csrf_cookie: str | None = Cookie(default=None, alias="vridhi_csrf"),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> None:
    if not csrf_cookie or not csrf_header or not hmac.compare_digest(csrf_cookie, csrf_header):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")
    try:
        csrf_signer.loads(csrf_cookie, max_age=3600)
    except BadSignature as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Expired CSRF token") from error


async def current_user(
    session_cookie: str | None = Cookie(default=None, alias="vridhi_session"),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not session_cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    query = select(AuthSession, User).join(User, User.id == AuthSession.user_id).where(
        AuthSession.token_hash == token_digest(session_cookie),
        AuthSession.revoked_at.is_(None),
        AuthSession.expires_at > datetime.now(timezone.utc),
        User.active.is_(True),
        User.deleted_at.is_(None),
    )
    row = (await db.execute(query)).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    return row[1]


async def require_project_access(project_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    from uuid import UUID

    try:
        parsed_id = UUID(project_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail="Project not found") from error
    from app.models import Project, ProjectMembership

    project = await db.get(Project, parsed_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    membership = await db.scalar(select(ProjectMembership.id).where(ProjectMembership.project_id == parsed_id, ProjectMembership.user_id == user.id))
    if membership is None and not user.global_access:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def require_permission(resource: str, action: str):
    if action not in {"read", "write"}:
        raise ValueError("RBAC action must be 'read' or 'write'")

    async def permission_dependency(request: Request, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> User:
        project_id = request.path_params.get("project_id") or request.query_params.get("project_id")
        from app.models import ProjectMembership

        membership = await db.scalar(select(ProjectMembership).where(ProjectMembership.project_id == project_id, ProjectMembership.user_id == user.id)) if project_id and resource != "users" else None
        module_permissions = user.global_permissions.get(resource) if user.global_access and user.global_permissions else None
        if resource == "users":
            module_permissions = await users_permission_profile(user, db)
        if resource == "audit":
            module_permissions = {"access": "allow", "read": {"export_report": True}} if user.global_access else getattr(user, "audit_permissions", None)
        if membership and membership.permissions and resource in membership.permissions:
            module_permissions = membership.permissions[resource]
        allowed = bool(module_permissions and module_permissions.get("access") == "allow")
        if allowed and resource == "users" and request.url.path.endswith("/history"):
            allowed = module_permissions.get("write", {}).get("actions", {}).get("history", False)
        if allowed and resource == "labor" and "/file" in request.url.path:
            action_key = "download_history_files" if "/addenda/" in request.url.path else "download_contract_files"
            write = module_permissions.get("write", {})
            allowed = write.get("mode") == "all" or write.get("actions", {}).get(action_key, False)
        if allowed and request.method == "GET" and request.query_params.get("export") == "1":
            allowed = module_permissions.get("read", {}).get("export_report", False)
        if action == "write" and allowed:
            body = None
            if resource == "inventory" and request.method == "POST":
                try:
                    body = await request.json()
                except Exception:
                    body = None
            action_key = project_write_action(resource, request.method, request.url.path, body)
            write = module_permissions.get("write", {})
            if write.get("mode") == "partial" and (not action_key or not write.get("actions", {}).get(action_key, False)):
                allowed = False
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Permission denied: {action} access to {resource}")
        return user

    return permission_dependency


def project_write_action(resource: str, method: str, path: str, body: dict | None = None) -> str | None:
    if resource == "overview":
        if path.endswith("/status"):
            return "update_status"
        if path.endswith("/documents") and method == "POST":
            return "upload_plan_document"
    if resource == "procurement":
        if path.endswith("/purchase-orders"):
            return "new_purchase_order" if method == "POST" else None
        if "/purchase-orders/" in path and method == "PATCH":
            return "new_purchase_order"
        if path.endswith("/payments") and method == "POST":
            return "add_payment"
    if resource == "inventory" and path.endswith("/inventory/transactions") and method == "POST":
        return "receive_stock" if (body or {}).get("transaction_type") == "receipt" else "use_stock" if (body or {}).get("transaction_type") == "issue" else None
    if resource == "cashflow":
        if path.endswith("/cash-receipts") and method == "POST":
            return "record_receipt"
        if path.endswith("/progress-billings") and method == "POST":
            return "new_application"
    if resource == "labor":
        if path.endswith("/labor/contracts") and method == "POST":
            return "new_labor_contract"
        if "/labor/contracts/" in path and path.endswith("/addenda") and method == "POST":
            return "new_labor_contract"
        if "/labor/addenda/" in path and path.endswith("/decision"):
            return "new_labor_contract"
        if "/labor/contracts/" in path and path.endswith("/claims"):
            return "log_weekly_work"
        if "/labor/claims/" in path and path.endswith("/decision"):
            return "log_weekly_work"
        if "/labor/claims/" in path and path.endswith("/payments"):
            return "pay_weekly_work"
        if path.endswith("/labor/workers") and method == "POST":
            return "add_worker"
        if path.endswith("/labor/work-entries") and method == "POST":
            return "log_weekly_work"
        if path.endswith("/labor/payments") and method == "POST":
            return "pay_weekly_work"
        if "/labor/workers/" in path and path.endswith("/status"):
            return "deactivate_worker"
        if "/labor/workers/" in path and method == "PUT":
            return "edit_worker"
    if resource == "users":
        if path.endswith("/reset-password") and method == "POST":
            return "reset_password"
        if path.endswith("/status") and method == "PATCH":
            return "activate_deactivate"
        if "/users/" in path and method == "DELETE":
            return "delete_user"
        if path.endswith("/users") and method == "POST" or "/users/" in path and method == "PUT":
            return "add_user"
    return None


def new_session(user_id, response: Response) -> str:
    raw = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.session_days)
    response.set_cookie("vridhi_session", raw, httponly=True, secure=settings.cookie_secure, samesite="lax", path="/", max_age=settings.session_days * 86400)
    return raw