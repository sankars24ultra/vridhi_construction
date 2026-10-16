import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Response

from app.api.routes.system import login


@pytest.mark.parametrize("password_matches,expected_status", [(True, 403), (False, 401)])
def test_disabled_account_cannot_login(password_matches, expected_status):
    account = SimpleNamespace(active=False, password_hash="stored-hash")
    database = SimpleNamespace(scalar=AsyncMock(return_value=account), add=MagicMock(), commit=AsyncMock())
    response = Response()
    with patch("app.api.routes.system.verify_password", return_value=password_matches):
        with pytest.raises(HTTPException) as error:
            asyncio.run(login({"username": "disabled-user", "password": "test-password"}, response, database))
    assert error.value.status_code == expected_status
    if password_matches:
        assert error.value.detail == "Your account is disabled. Please contact your administrator to reactivate it."
    database.add.assert_not_called()
    database.commit.assert_not_awaited()
    assert "set-cookie" not in response.headers