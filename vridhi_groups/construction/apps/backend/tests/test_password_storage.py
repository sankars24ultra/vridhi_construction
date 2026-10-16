from argon2 import extract_parameters

from app.core.config import settings
from app.security import hash_password, verify_password


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