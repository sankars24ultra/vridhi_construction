import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

SPEC = importlib.util.spec_from_file_location("prepare_database", Path(__file__).resolve().parents[1] / "prepare_database.py")
database = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(database)


class DatabaseSetupTests(unittest.TestCase):
    def setUp(self):
        self.connection = SimpleNamespace(execute=AsyncMock(), close=AsyncMock())
        self.settings = patch.object(database, "settings", SimpleNamespace(database_url="postgresql+asyncpg://test:example@localhost:5432/vridhi_test"))
        self.mode = patch.object(database, "dotenv_values", return_value={"DATABASE_MODE": "local"})
        self.settings.start()
        self.mode.start()
        self.addCleanup(self.settings.stop)
        self.addCleanup(self.mode.stop)

    def test_existing_database_is_only_probed(self):
        with patch.object(database.asyncpg, "connect", new_callable=AsyncMock, return_value=self.connection) as connect:
            self.assertEqual(asyncio.run(database.prepare()), 0)
            self.connection.execute.assert_awaited_once_with("SELECT 1")
            self.connection.close.assert_awaited_once()
            self.assertEqual(connect.await_count, 1)

    def test_missing_database_requires_parent_confirmation(self):
        with patch.object(database.asyncpg, "connect", new_callable=AsyncMock, side_effect=database.asyncpg.InvalidCatalogNameError):
            self.assertEqual(asyncio.run(database.prepare()), 3)
            self.connection.execute.assert_not_awaited()

    def test_creation_only_with_explicit_flag(self):
        admin = SimpleNamespace(execute=AsyncMock(), close=AsyncMock())
        with patch.object(database.asyncpg, "connect", new_callable=AsyncMock, side_effect=[database.asyncpg.InvalidCatalogNameError(), admin, self.connection]):
            self.assertEqual(asyncio.run(database.prepare(create=True)), 0)
            admin.execute.assert_awaited_once_with('CREATE DATABASE "vridhi_test"')
            admin.close.assert_awaited_once()
            self.connection.execute.assert_awaited_once_with("SELECT 1")

    def test_database_identifier_is_quoted(self):
        admin = SimpleNamespace(execute=AsyncMock(), close=AsyncMock())
        with patch.object(database, "settings", SimpleNamespace(database_url='postgresql+asyncpg://test@localhost/test"name')), patch.object(database.asyncpg, "connect", new_callable=AsyncMock, side_effect=[database.asyncpg.InvalidCatalogNameError(), admin, self.connection]):
            asyncio.run(database.prepare(create=True))
            admin.execute.assert_awaited_once_with('CREATE DATABASE "test""name"')

    def test_server_down_is_clear_and_does_not_attempt_create(self):
        with patch.object(database.asyncpg, "connect", new_callable=AsyncMock, side_effect=ConnectionRefusedError) as connect:
            with self.assertRaisesRegex(RuntimeError, "not accepting connections"):
                asyncio.run(database.prepare(create=True))
            self.assertEqual(connect.await_count, 1)

    def test_bad_credentials_do_not_trigger_creation(self):
        with patch.object(database.asyncpg, "connect", new_callable=AsyncMock, side_effect=database.asyncpg.InvalidPasswordError) as connect:
            with self.assertRaises(database.asyncpg.InvalidPasswordError):
                asyncio.run(database.prepare(create=True))
            self.assertEqual(connect.await_count, 1)

    def test_invalid_driver_rejected(self):
        with patch.object(database, "settings", SimpleNamespace(database_url="sqlite:///db")), patch.object(database.asyncpg, "connect", new_callable=AsyncMock) as connect:
            with self.assertRaisesRegex(RuntimeError, "postgresql"):
                asyncio.run(database.prepare())
            connect.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
