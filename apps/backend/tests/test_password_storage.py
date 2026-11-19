from unittest.mock import AsyncMock, MagicMock

import pytest
from argon2 import extract_parameters

from app.core.config import settings
from app.models import User
from app.security import hash_password, verify_password
from app.services import seed


def test_password_storage_uses_salted_argon2id():
    password = "test-only-password"
    first_hash = hash_password(password)
    second_hash = hash_password(password)
    assert first_hash.startswith("$argon2id$")
    assert first_hash != password
    assert first_hash != second_hash
    assert verify_password(first_hash, password)
    assert not verify_password(first_hash, "incorrect")


def test_bootstrap_configuration_contains_only_a_hash():
    extract_parameters(settings.initial_password_hash)
    assert not hasattr(settings, "demo_password")


@pytest.mark.asyncio
async def test_bootstrap_creates_only_administrator_and_preserves_existing_data(monkeypatch):
    db = MagicMock()
    db.scalar = AsyncMock(side_effect=[0, 1])
    db.commit = AsyncMock()
    session_factory = MagicMock()
    session_factory.return_value.__aenter__.return_value = db
    monkeypatch.setattr(seed, "SessionLocal", session_factory)

    await seed.seed_local_data()
    await seed.seed_local_data()

    db.add.assert_called_once()
    owner = db.add.call_args.args[0]
    assert isinstance(owner, User)
    assert owner.username == "administrator"
    assert owner.global_access is True
    assert owner.password_hash == settings.initial_password_hash
    assert set(owner.global_permissions) == set(seed.RBAC_RESOURCES)
    assert not owner.memberships
    db.add_all.assert_not_called()
    db.delete.assert_not_called()
    db.commit.assert_awaited_once()
