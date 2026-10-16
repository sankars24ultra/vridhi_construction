import json
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.logging_setup import frontend_logger
from app.models import AuthSession, User
from app.schemas import SessionRead, UserRead
from app.security import current_user, hash_password, issue_csrf, new_session, require_csrf, token_digest, user_permission_matrix, verify_password
from app.services.common import add_audit, user_dto
from app.core.config import settings


router = APIRouter()


@router.post("/api/v1/client-logs", status_code=204, dependencies=[Depends(require_csrf)])
async def client_logs(request: Request) -> Response:
    content = await request.body()
    if len(content) > 16384:
        raise HTTPException(status_code=413, detail="Log batch too large")
    try:
        payload = json.loads(content)
    except (ValueError, UnicodeDecodeError) as error:
        raise HTTPException(status_code=422, detail="Invalid log batch") from error
    if not isinstance(payload, list) or len(payload) > 30:
        raise HTTPException(status_code=422, detail="Invalid log batch")
    for entry in payload:
        if not isinstance(entry, dict) or entry.get("event") not in {"api_response", "api_network_error", "javascript_error", "unhandled_rejection", "console_error", "console_warn"}:
            continue
        safe = {"event": entry["event"]}
        for key in ("method", "status", "duration_ms", "request_id"):
            value = entry.get(key)
            if isinstance(value, (str, int, float)) and len(str(value)) <= 80:
                safe[key] = value
        frontend_logger.info(safe)
    return Response(status_code=204)


@router.get("/api/v1/health")
async def health() -> dict:
    return {"status": "ok", "service": "vridhi-local"}


@router.get("/api/v1/ready")
async def ready(db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(select(1))
    return {"status": "ready", "database": "connected"}


@router.get("/api/v1/auth/bootstrap")
async def auth_bootstrap(response: Response, session_cookie: str | None = Cookie(default=None, alias="vridhi_session"), db: AsyncSession = Depends(get_db)) -> dict:
    authenticated = False
    if session_cookie:
        session = await db.scalar(
            select(AuthSession)
            .join(User, User.id == AuthSession.user_id)
            .where(
                AuthSession.token_hash == token_digest(session_cookie),
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > datetime.now(timezone.utc),
                User.active.is_(True),
                User.deleted_at.is_(None),
            )
        )
        authenticated = session is not None
    return {"csrf_token": issue_csrf(response), "authenticated": authenticated}


@router.post("/api/v1/auth/login", response_model=SessionRead, dependencies=[Depends(require_csrf)])
async def login(payload: dict, response: Response, db: AsyncSession = Depends(get_db)) -> SessionRead:
    identity = str(payload.get("username", "")).strip().lower()
    password = str(payload.get("password", ""))
    user = await db.scalar(select(User).where((User.username == identity) | (User.email == identity), User.deleted_at.is_(None)))
    if not user or not verify_password(user.password_hash, password):
        raise HTTPException(status_code=401, detail="Invalid username/email or password")
    if not user.active:
        raise HTTPException(status_code=403, detail="Your account is disabled. Please contact your administrator to reactivate it.")
    raw_token = secrets.token_urlsafe(48)
    expires = datetime.now(timezone.utc) + timedelta(days=settings.session_days)
    response.set_cookie("vridhi_session", raw_token, httponly=True, secure=settings.cookie_secure, samesite="lax", path="/", max_age=settings.session_days * 86400)
    db.add(AuthSession(user_id=user.id, token_hash=token_digest(raw_token), expires_at=expires))
    await add_audit(db, user, "login_success", "User", user.id)
    await db.commit()
    csrf_token = issue_csrf(response)
    return SessionRead(user=UserRead.model_validate(user), expires_at=expires, csrf_token=csrf_token)


@router.post("/api/v1/auth/logout", status_code=204, dependencies=[Depends(require_csrf)])
async def logout(response: Response, user: User = Depends(current_user), db: AsyncSession = Depends(get_db), session_cookie: str | None = Cookie(default=None, alias="vridhi_session")) -> Response:
    session = await db.scalar(select(AuthSession).where(AuthSession.token_hash == token_digest(session_cookie or ""), AuthSession.revoked_at.is_(None)))
    if session:
        session.revoked_at = datetime.now(timezone.utc)
        await add_audit(db, user, "logout", "User", user.id)
        await db.commit()
    response.delete_cookie("vridhi_session", path="/")
    response.delete_cookie("vridhi_csrf", path="/")
    response.status_code = 204
    return response


@router.get("/api/v1/me")
async def me(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    permissions = await user_permission_matrix(user, db)
    return {**user_dto(user), "permissions": permissions, "company_wide_read": user.global_access}