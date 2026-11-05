from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from app.api.routes.admin import router
from app.db import get_db
from app.security import current_user


def availability_app(database, *, can_add=True):
    app = FastAPI()
    app.include_router(router)
    actor = SimpleNamespace(
        id=uuid4(), global_access=False,
        users_permissions={"access": "allow", "write": {"mode": "partial", "actions": {"add_user": can_add}}},
    )
    app.dependency_overrides[current_user] = lambda: actor
    app.dependency_overrides[get_db] = lambda: database
    return app


@pytest.mark.parametrize("existing_id,available", [(None, True), (uuid4(), False)])
async def test_username_lookup_matches_creation_rules(existing_id, available):
    database = SimpleNamespace(scalar=AsyncMock(return_value=existing_id))
    app = availability_app(database)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/users/username-availability", params={"username": "Existing.User"})
    assert response.status_code == 200
    assert response.json() == {"username": "Existing.User", "available": available}
    statement = database.scalar.call_args.args[0]
    assert "lower(users.username)" in str(statement)
    assert "existing.user" in statement.compile().params.values()
    # Inactive and soft-deleted usernames remain reserved, as with user creation.
    assert "deleted_at" not in str(statement)
    assert "active" not in str(statement)


@pytest.mark.parametrize("username", ["ab", "bad name", "bad/name", "a" * 81, ""])
async def test_invalid_username_is_rejected_without_lookup(username):
    database = SimpleNamespace(scalar=AsyncMock())
    app = availability_app(database)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/users/username-availability", params={"username": username})
    assert response.status_code == 422
    database.scalar.assert_not_awaited()


async def test_read_only_users_cannot_check_usernames():
    database = SimpleNamespace(scalar=AsyncMock())
    app = availability_app(database, can_add=False)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/users/username-availability", params={"username": "valid.user"})
    assert response.status_code == 403
    database.scalar.assert_not_awaited()


async def test_username_check_requires_authentication():
    app = FastAPI()
    app.include_router(router)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/users/username-availability", params={"username": "valid.user"})
    assert response.status_code == 401
