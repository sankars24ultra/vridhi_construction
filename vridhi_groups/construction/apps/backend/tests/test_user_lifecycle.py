import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.routes.admin import PasswordReset, UserStatusUpdate, change_user_status, delete_user, reset_user_password
from app.security import project_write_action


def context():
    actor = SimpleNamespace(id=uuid4())
    target = SimpleNamespace(id=uuid4(), username="test.user", active=True, password_hash="old")
    database = SimpleNamespace(scalar=AsyncMock(return_value=target), execute=AsyncMock(), commit=AsyncMock(), rollback=AsyncMock())
    return actor, target, database


def test_reset_hashes_password_and_revokes_sessions():
    actor, target, database = context()
    with patch("app.api.routes.admin.hash_password", return_value="hashed"), patch("app.api.routes.admin.add_audit", new_callable=AsyncMock):
        asyncio.run(reset_user_password(target.id, PasswordReset(password="new-secret"), actor, database))
    assert target.password_hash == "hashed"
    database.execute.assert_awaited_once()
    database.commit.assert_awaited_once()


@pytest.mark.parametrize("active", [True, False])
def test_status_changes_and_deactivation_revokes_sessions(active):
    actor, target, database = context()
    with patch("app.api.routes.admin.add_audit", new_callable=AsyncMock):
        assert asyncio.run(change_user_status(target.id, UserStatusUpdate(active=active), actor, database)) == {"active": active}
    assert target.active is active
    assert database.execute.await_count == (0 if active else 1)


def test_self_account_is_protected():
    actor, target, database = context()
    with pytest.raises(HTTPException) as error:
        asyncio.run(delete_user(actor.id, actor, database))
    assert error.value.status_code == 422
    database.execute.assert_not_awaited()


def test_delete_preserves_history_and_revokes_sessions():
    actor, target, database = context()
    with patch("app.api.routes.admin.add_audit", new_callable=AsyncMock) as audit:
        asyncio.run(delete_user(target.id, actor, database))
    assert target.active is False
    assert target.deleted_at is not None
    database.execute.assert_awaited_once()
    assert str(database.execute.call_args.args[0]).startswith("UPDATE auth_sessions")
    assert audit.call_args.args[-1] == {"username": "test.user", "history_retained": True}


def test_delete_unreferenced_user():
    actor, target, database = context()
    with patch("app.api.routes.admin.add_audit", new_callable=AsyncMock):
        assert asyncio.run(delete_user(target.id, actor, database)) == {"status": "deleted"}
    assert database.execute.await_count == 1
    database.commit.assert_awaited_once()


@pytest.mark.parametrize("method,path,action", [("POST", "/api/v1/users/id/reset-password", "reset_password"), ("PATCH", "/api/v1/users/id/status", "activate_deactivate"), ("DELETE", "/api/v1/users/id", "delete_user")])
def test_lifecycle_routes_require_users_management(method, path, action):
    assert project_write_action("users", method, path) == action


def test_password_reset_rejects_short_password():
    with pytest.raises(ValueError):
        PasswordReset(password="short")