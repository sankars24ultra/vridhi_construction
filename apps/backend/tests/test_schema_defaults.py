import importlib.util
from pathlib import Path
from unittest.mock import Mock

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.models import User


def test_global_access_default_is_postgresql_boolean_literal():
    ddl = str(CreateTable(User.__table__).compile(dialect=postgresql.dialect()))
    assert "global_access BOOLEAN DEFAULT false NOT NULL" in ddl
    assert "false()" not in ddl


def test_initial_schema_leaves_later_changes_to_their_migrations(monkeypatch):
    path = Path(__file__).resolve().parents[1] / "migrations/versions/0001_initial_schema.py"
    spec = importlib.util.spec_from_file_location("initial_schema", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    operations = Mock()
    monkeypatch.setattr(migration, "op", operations)
    migration.upgrade()
    tables = {
        call.args[0]: call.args[1:]
        for call in operations.create_table.call_args_list
    }
    assert not {"cash_receipts", "labor_workers", "labor_contracts", "rbac_roles", "project_value_history"} & tables.keys()
    columns = {
        name: {item.name for item in items if isinstance(item, sa.Column)}
        for name, items in tables.items()
    }
    assert "global_access" not in columns["users"]
    assert "phone" not in columns["users"]
    assert "deleted_at" not in columns["users"]
    assert "permissions" not in columns["project_memberships"]
    assert "image_storage_name" not in columns["purchase_orders"]
    assert "payment_mode" not in columns["purchase_order_payments"]
    assert not {"project_id", "details"} & columns["audit_events"]
    assert not {"reference", "notes", "recorded_by_id"} & columns["inventory_transactions"]
    assert any(
        isinstance(item, sa.UniqueConstraint)
        and item.name == "inventory_transactions_purchase_order_line_id_key"
        for item in tables["inventory_transactions"]
    )
    migration.downgrade()
    assert {call.args[0] for call in operations.drop_table.call_args_list} == tables.keys()
