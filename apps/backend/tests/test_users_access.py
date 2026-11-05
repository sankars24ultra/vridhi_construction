import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.security import require_permission, user_permission_matrix


def permission_db(profiles):
    database = SimpleNamespace(scalars=AsyncMock(return_value=MagicMock(all=lambda: [SimpleNamespace(permissions=profile) for profile in profiles])))
    return database


def test_global_users_access_does_not_require_selected_project():
    user = SimpleNamespace(id=uuid4(), global_access=True, global_permissions={"users": {"access": "allow", "read": {"export_report": True}, "write": {"mode": "all"}}})
    request = Request({"type": "http", "method": "GET", "path": "/api/v1/users", "query_string": b"", "headers": []})
    assert asyncio.run(require_permission("users", "read")(request, user, permission_db([]))) is user


def test_project_users_grant_is_independent_of_project_selection():
    user = SimpleNamespace(id=uuid4(), global_access=False, global_permissions=None)
    database = permission_db([{"users": {"access": "allow", "read": {"export_report": True}, "write": {"mode": "partial", "actions": {}}}}])
    matrix = asyncio.run(user_permission_matrix(user, database))
    assert matrix["users"]["read"] is True
    assert matrix["users"]["write"] is False
    assert matrix["users"]["export_report"] is True
    assert matrix["users"]["reset_password"] is False
    request = Request({"type": "http", "method": "PUT", "path": "/api/v1/users/user-id", "query_string": b"", "headers": []})
    with pytest.raises(HTTPException) as error:
        asyncio.run(require_permission("users", "write")(request, user, database))
    assert error.value.status_code == 403


def test_no_users_grant_denies_directory_access():
    user = SimpleNamespace(id=uuid4(), global_access=False, global_permissions=None)
    request = Request({"type": "http", "method": "GET", "path": "/api/v1/users", "query_string": b"", "headers": []})
    with pytest.raises(HTTPException) as error:
        asyncio.run(require_permission("users", "read")(request, user, permission_db([{"users": {"access": "block"}}])))
    assert error.value.status_code == 403