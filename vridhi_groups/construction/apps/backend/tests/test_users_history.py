import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.routes.admin import create_user, update_user, user_history
from app.schemas import UserCreate, UserUpdate
from app.security import require_permission


def test_users_only_account_requires_no_projects():
    actor = SimpleNamespace(id=uuid4(), global_access=True)
    database = MagicMock()
    database.scalar = AsyncMock(return_value=None)
    database.flush = AsyncMock(side_effect=lambda: setattr(database.add.call_args.args[0], "id", uuid4()))
    database.commit = AsyncMock()
    payload = UserCreate(name="User manager", username="user.manager", password="test-secret", users_permissions={"access": "allow", "read": {"export_report": True}, "write": {"mode": "partial", "actions": {"history": True}}})
    with patch("app.api.routes.admin.hash_password", return_value="hashed"), patch("app.api.routes.admin.add_audit", new_callable=AsyncMock):
        result = asyncio.run(create_user(payload, actor, database))
    assert result["assigned_project_ids"] == []
    assert result["global_access"] is False
    assert result["users_permissions"]["write"]["actions"]["history"] is True
    database.scalars.assert_not_called()


def test_username_cannot_be_changed_on_update():
    target = SimpleNamespace(id=uuid4(), username="original.user")
    actor = SimpleNamespace(id=uuid4())
    database = SimpleNamespace(scalar=AsyncMock(return_value=target))
    payload = UserUpdate(name="User Name", username="renamed.user")
    with pytest.raises(HTTPException) as error:
        asyncio.run(update_user(target.id, payload, actor, database))
    assert error.value.status_code == 422
    assert "Username cannot be changed" in error.value.detail


@pytest.mark.parametrize("method,path,action", [("POST", "/api/v1/users/id/reset-password", "reset_password"), ("PATCH", "/api/v1/users/id/status", "activate_deactivate"), ("DELETE", "/api/v1/users/id", "delete_user"), ("GET", "/api/v1/users/id/history", "history")])
def test_each_users_action_requires_its_own_grant(method, path, action):
    actor = SimpleNamespace(id=uuid4(), global_access=False, global_permissions=None, users_permissions={"access": "allow", "read": {}, "write": {"mode": "partial", "actions": {"add_user": True}}})
    request = Request({"type": "http", "method": method, "path": path, "query_string": b"", "headers": []})
    database = MagicMock()
    dependency = require_permission("users", "read" if method == "GET" else "write")
    with pytest.raises(HTTPException) as error:
        asyncio.run(dependency(request, actor, database))
    assert error.value.status_code == 403
    actor.users_permissions["write"]["actions"][action] = True
    assert asyncio.run(dependency(request, actor, database)) is actor


def test_history_returns_details_and_page_metadata():
    user_id = uuid4()
    event = SimpleNamespace(id=uuid4(), action="user_updated", entity_type="User", entity_id=user_id, occurred_at=datetime.now(timezone.utc), details={"after": {"name": "Updated"}})
    database = SimpleNamespace(execute=AsyncMock(return_value=MagicMock(all=lambda: [(event, "Administrator", "admin")])), scalar=AsyncMock(return_value=12))
    result = asyncio.run(user_history(user_id, page=2, page_size=5, search="updated", user=SimpleNamespace(), db=database))
    assert result["total"] == 12
    assert result["page"] == 2
    assert result["page_size"] == 5
    assert result["items"][0]["actor"] == "Administrator"
    assert result["items"][0]["details"] == {"after": {"name": "Updated"}}


def test_history_rejects_unsupported_page_size():
    with pytest.raises(HTTPException) as error:
        asyncio.run(user_history(uuid4(), page=1, page_size=7, search="", user=SimpleNamespace(), db=MagicMock()))
    assert error.value.status_code == 422