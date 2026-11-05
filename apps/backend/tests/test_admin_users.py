import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.routes.admin import create_user
from app.models import Project, ProjectMembership, User
from app.schemas import ProjectPermissions, UserCreate


def test_owner_creates_user_with_hashed_password_and_project_membership():
    project = Project(id=uuid4(), name="Build site")
    owner = User(id=uuid4(), role="Owner")
    db = MagicMock()
    db.scalar = AsyncMock(side_effect=[None, None])
    db.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[project])))
    db.flush = AsyncMock(side_effect=lambda: setattr(next(item for item in db.add.call_args_list[0].args if isinstance(item, User)), "id", uuid4()))
    db.commit = AsyncMock()
    project_permissions = ProjectPermissions.model_validate({
        module: {"access": "allow", "read": {"export_report": True}, "write": {"mode": "partial", "actions": {"add_worker": True, "add_user": True}}}
        for module in ("overview", "procurement", "inventory", "cashflow", "labor", "users")
    })
    payload = UserCreate(name="New User", email=None, username="new.user", password="secret", role="Supervisor", project_ids=[project.id], project_permissions={project.id: project_permissions})

    with patch("app.api.routes.admin.hash_password", return_value="argon-hash") as hash_password, patch("app.api.routes.admin.add_audit", new_callable=AsyncMock) as add_audit:
        result = asyncio.run(create_user(payload, owner, db))

    created_user = next(item for item in db.add.call_args_list[0].args if isinstance(item, User))
    assert result["username"] == "new.user"
    assert created_user.password_hash == "argon-hash"
    assert created_user.role == "Supervisor"
    assert len(created_user.memberships) == 1
    assert created_user.memberships[0].project_id == project.id
    assert created_user.memberships[0].permissions["labor"]["write"]["actions"]["add_worker"] is True
    hash_password.assert_called_once_with("secret")
    add_audit.assert_awaited_once()
    db.commit.assert_awaited_once()


def test_admin_cannot_assign_owner_role():
    admin = User(id=uuid4(), role="Admin")
    payload = UserCreate(name="New User", email="new@example.com", username="new.user", password="secret", role="Owner")
    db = MagicMock()

    with pytest.raises(HTTPException) as error:
        asyncio.run(create_user(payload, admin, db))

    assert error.value.status_code == 403
    db.add.assert_not_called()


def test_project_scoped_user_requires_project_assignment():
    owner = User(id=uuid4(), role="Owner")
    payload = UserCreate(name="New User", email="new@example.com", username="new.user", password="secret", role="Cashier")
    db = MagicMock()
    db.scalar = AsyncMock(side_effect=[None, None])

    with pytest.raises(HTTPException) as error:
        asyncio.run(create_user(payload, owner, db))

    assert error.value.status_code == 422
    db.add.assert_not_called()


def test_user_create_rejects_password_shorter_than_six_characters():
    with pytest.raises(ValueError):
        UserCreate(name="New User", email=None, username="new.user", password="short", role="Owner")