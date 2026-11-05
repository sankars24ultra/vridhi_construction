from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI, HTTPException

from app.api.routes.admin import create_user, update_user, validate_dashboard_grant
from app.api.routes.projects import router, create_project
from app.db import get_db
from app.models import User, Project
from app.schemas import UserCreate, UserUpdate
from app.security import current_user, dashboard_grants, require_csrf, user_permission_matrix


def profile(access="allow", create=False):
    return {"access": access, "read": {"export_report": False}, "write": {"mode": "partial", "actions": {"new_project": create}}}


@pytest.mark.parametrize("global_access,permissions,expected", [
    (False, None, {"read": False, "write": False}),
    (False, profile("block", True), {"read": False, "write": False}),
    (False, profile(), {"read": True, "write": False}),
    (False, profile(create=True), {"read": True, "write": True}),
    (True, profile("block"), {"read": True, "write": True}),
])
async def test_dashboard_matrix(global_access, permissions, expected):
    user = User(id=uuid4(), global_access=global_access, dashboard_permissions=permissions, users_permissions={"access": "block"})
    assert dashboard_grants(user) == expected
    matrix = await user_permission_matrix(user, MagicMock())
    assert matrix["dashboard"] == expected


@pytest.mark.parametrize("permissions,expected", [(None, 403), (profile(), 403), (profile("block", True), 403), (profile(create=True), 422)])
async def test_create_endpoint_requires_dashboard_write_before_parsing(permissions, expected):
    app = FastAPI()
    app.include_router(router)
    user = User(id=uuid4(), global_access=False, dashboard_permissions=permissions)
    app.dependency_overrides[current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: MagicMock()
    app.dependency_overrides[require_csrf] = lambda: None
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/projects")
    assert response.status_code == expected


def test_cannot_delegate_dashboard_rights_not_held():
    actor = User(global_access=False, dashboard_permissions=profile())
    with pytest.raises(HTTPException) as error:
        validate_dashboard_grant(actor, profile(create=True))
    assert error.value.status_code == 403
    validate_dashboard_grant(actor, profile())
    validate_dashboard_grant(actor, profile("block"))
    validate_dashboard_grant(User(global_access=True), profile(create=True))


async def test_delegated_creator_gets_read_only_overview_for_new_project():
    actor = User(id=uuid4(), global_access=False, dashboard_permissions=profile(create=True))
    form = {"name": "New site", "location": "Test location", "baseline_budget": "100", "contract_value": "200", "start_date": "2026-01-01"}
    request = SimpleNamespace(form=AsyncMock(return_value=form))
    database = MagicMock()
    async def flush():
        project = database.add.call_args.args[0]
        project.id = uuid4()
    database.flush = AsyncMock(side_effect=flush)
    database.commit = AsyncMock()
    database.refresh = AsyncMock()
    with patch("app.api.routes.projects.add_audit", new_callable=AsyncMock), patch("app.api.routes.projects.project_dto", return_value={"name": "New site"}):
        await create_project(request, actor, database)
    created = database.add.call_args.args[0]
    assert isinstance(created, Project)
    assert created.memberships[0].permissions == {"overview": {"access": "allow", "read": {"export_report": False}, "write": {"mode": "partial", "actions": {}}}}


async def test_dashboard_only_user_creation_persists_profile_and_audit():
    actor = User(id=uuid4(), global_access=True)
    database = MagicMock(scalar=AsyncMock(return_value=None), commit=AsyncMock())
    async def flush():
        database.add.call_args.args[0].id = uuid4()
    database.flush = AsyncMock(side_effect=flush)
    payload = UserCreate(name="Dashboard User", username="dashboard.user", password="test-pass-123", dashboard_permissions=profile(create=True))
    with patch("app.api.routes.admin.add_audit", new_callable=AsyncMock) as audit:
        result = await create_user(payload, actor, database)
    assert result["dashboard_permissions"] == profile(create=True)
    assert result["assigned_project_ids"] == []
    assert audit.call_args.args[-1]["after"]["dashboard_permissions"] == profile(create=True)


@pytest.mark.parametrize("include_profile", [True, False])
async def test_dashboard_update_and_omitted_profile_preservation(include_profile):
    actor = User(id=uuid4(), global_access=True)
    target = User(id=uuid4(), name="Dashboard User", username="dashboard.user", global_access=False, dashboard_permissions=profile(create=True), memberships=[])
    database = MagicMock(scalar=AsyncMock(side_effect=[target, None]), scalars=AsyncMock(), execute=AsyncMock(), commit=AsyncMock())
    payload = UserUpdate(name="Dashboard User", username="dashboard.user", **({"dashboard_permissions": profile()} if include_profile else {}))
    with patch("app.api.routes.admin.add_audit", new_callable=AsyncMock):
        await update_user(target.id, payload, actor, database)
    assert target.dashboard_permissions == profile(create=not include_profile)
